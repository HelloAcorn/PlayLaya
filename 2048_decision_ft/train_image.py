"""이미지 입력 LoRA. 손실은 텍스트 train.py 와 같은 soft CE (전문가 분포 vs 합법 수 글자 softmax).

전체 0.8B 를 8GB 에 올리지 않는다. 언어 모델 Linear 만 LoRA (fp32), 비전 타워는 얼리고
출력을 detach, gradient checkpointing, micro_batch 1 + grad accumulation.
가중치는 float16, 순전파는 fp16 autocast. 정답 슬롯 판독은 fp32.

  python train.py --input image --dry-run
  python train.py --input image --data data/clone.jsonl --out ckpt/image_run1
"""
from __future__ import annotations

import json
import math
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset, Subset

import board as B
import config as C
from evaluate import play
from frame import FrameRenderer, grid_from_state
from game_metrics import Guard, loss_targets, metrics_row, record_game_metrics
from image_policy import forward_slots, freeze_vision, load_image_model, prepare, slot_ids_for, to_device
from lora import inject, is_vision_path, save_adapter
from playjev_prompt import build_image_prompt
from train import load_records, soft_ce, training_split

# step 0 의 train loss 만 짧게 잰다. 이후 점은 직전 게임 평가 이후 마이크로배치 손실의 평균이다.
_PROBE = 32


def flag_passed(*flags: str) -> bool:
    argv = sys.argv[1:]
    return any(s == f or s.startswith(f + "=") for f in flags for s in argv)


def apply_image_defaults(a):
    """텍스트 argparse 기본값(배치 8, 로컬 CausalLM 경로)을 이미지 학습에 그대로 쓰지 않는다.
    사용자가 플래그를 준 경우에만 그 값을 유지한다."""
    if not flag_passed("--model"):
        if Path(C.MODEL_PATH).exists():
            a.model = C.MODEL_PATH
        else:
            a.model = C.IMAGE_BASE_MODEL
    if not flag_passed("--micro_batch", "--micro-batch"):
        a.micro_batch = C.IMAGE_MICRO_BATCH
    if not flag_passed("--batch"):
        a.batch = C.IMAGE_BATCH
    if not getattr(a, "dtype", None):
        a.dtype = C.IMAGE_DTYPE


def shuffled(legal, seed: int, epoch: int, index: int) -> list[str]:
    opts = list(legal)
    # random.Random 은 튜플 시드를 받지 않는다. 문자열이라 프로세스마다 같다 (텍스트 경로의 hash() 와 다름).
    random.Random(f"{seed}:{epoch}:{index}").shuffle(opts)
    return opts


class ImageSFT(Dataset):
    def __init__(self, recs, train: bool, seed: int, renderer: FrameRenderer):
        self.recs, self.train, self.seed, self.renderer, self.epoch = recs, train, seed, renderer, 0

    def __len__(self):
        return len(self.recs)

    def __getitem__(self, i):
        r = self.recs[i]
        opts = shuffled(r["legal"], self.seed, self.epoch if self.train else 0, i)
        grid = r["grid"] if r.get("grid") else grid_from_state(r["state"])
        return (self.renderer.render(grid), build_image_prompt(opts),
                [r["probs"][o] for o in opts], opts.index(r["action"]))


def _pad_norm(rows):
    width = max(4, max(len(t) for t in rows))
    out = torch.zeros(len(rows), width)
    for i, t in enumerate(rows):
        out[i, : len(t)] = torch.tensor(t, dtype=torch.float32)
    return out / out.sum(-1, keepdim=True).clamp_min(1e-12)


def make_collate(processor, max_len: int, label: str = "soft"):
    def collate(items):
        images, prompts, probs, best = zip(*items)
        enc = prepare(processor, prompts, images)
        if enc["input_ids"].shape[1] > max_len:
            raise RuntimeError(f"prompt length {enc['input_ids'].shape[1]} > {max_len}; 정답 슬롯이 잘릴 수 있어 중단")
        teacher = _pad_norm(probs)
        chosen = _pad_norm([loss_targets(p, i, label) for p, i in zip(probs, best)])
        batch = {"targets": chosen, "teacher": teacher,
                 "n_opts": torch.tensor([len(p) for p in probs]), "best": torch.tensor(best)}
        for key, val in enc.items():
            batch[key] = val
        return batch
    return collate


def _logits(model, batch, slot_ids, device, dtype):
    enc = to_device(batch, device)
    return forward_slots(model, enc, slot_ids, enc["n_opts"], device, dtype)


def _kl(logits, targets):
    """KL(teacher || model). teacher 질량 0 인 칸은 빼지 않는다."""
    logp = F.log_softmax(logits, -1)
    safe = targets.clamp_min(1e-12)
    term = targets * (torch.log(safe) - logp)
    return torch.where(targets > 0, term, torch.zeros_like(term)).sum(-1)


@torch.no_grad()
def evaluate(model, loader, slot_ids, device, dtype):
    was = model.training
    model.eval()
    ce, agree, kl = [], [], []
    for batch in loader:
        logits = _logits(model, batch, slot_ids, device, dtype)
        tgt = batch["targets"].to(device)
        # KL 은 항상 전문가 soft 분포. hard 학습이어도 검증 KL 은 텍스트 경로와 같은 대상을 본다.
        teacher = batch["teacher"].to(device) if "teacher" in batch else tgt
        ce += soft_ce(logits, tgt).tolist()
        agree += (logits.argmax(-1).cpu() == batch["best"]).tolist()
        kl += _kl(logits, teacher).tolist()
    if was:
        model.train()
    n = max(1, len(ce))
    return {"val_loss": sum(ce) / n, "val_agreement": sum(agree) / n, "val_kl": sum(kl) / n, "n": len(ce)}


def dry_run(a) -> None:
    """프레임과 프롬프트를 만들고, 프로세서가 있으면 한 배치의 shape 만 찍는다. 옵티마이저 스텝은 없다."""
    from frame import render_frame
    from playjev_prompt import build_image_prompt as prompt_of

    grid = [[2, 0, 0, 4], [0, 0, 0, 0], [0, 8, 0, 0], [16, 0, 0, 0]]
    im = render_frame(grid, a.renderer)
    prompt = prompt_of(["up", "down", "left"])
    ckpt = not a.no_grad_ckpt
    print(f"[dry-run] renderer={a.renderer} frame={im.size} mode={im.mode}", flush=True)
    print(f"[dry-run] model={a.model} dtype={a.dtype} lora_r={a.r} freeze_vision={a.freeze_vision} "
          f"micro_batch={a.micro_batch} batch={a.batch} grad_ckpt={ckpt}", flush=True)
    print("[dry-run] prompt:\n" + prompt, flush=True)
    if max(im.size) != C.FRAME_LONG_SIDE:
        raise SystemExit(f"frame long side is {max(im.size)}, expected {C.FRAME_LONG_SIDE}")
    try:
        from transformers import AutoProcessor
        local = Path(a.model).exists()
        proc = AutoProcessor.from_pretrained(a.model, local_files_only=local)
        proc.tokenizer.padding_side = "left"
        enc = prepare(proc, [prompt], [im])
        shapes = {k: list(v.shape) for k, v in enc.items() if hasattr(v, "shape")}
        print(f"[dry-run] processor ok {shapes}", flush=True)
    except Exception as e:
        print(f"[dry-run] processor not loaded ({type(e).__name__}: {e})", flush=True)
    print("[dry-run] no optimizer step", flush=True)


def image_move_probs(model, processor, slot_ids, device, dtype, frames, options):
    """학습 중인 가중치로 합법 수 확률. 호출하는 쪽에서 eval / no_grad 를 잡는다."""
    prompts = [build_image_prompt(o) for o in options]
    enc = to_device(prepare(processor, prompts, frames), device)
    n_opts = torch.tensor([len(o) for o in options], device=device)
    logits = forward_slots(model, enc, slot_ids, n_opts, device, dtype)
    p = torch.softmax(logits, -1)
    return [p[i, : len(o)].tolist() for i, o in enumerate(options)]


def _step(scaler, opt, params, sched, device):
    scaler.unscale_(opt)
    torch.nn.utils.clip_grad_norm_(params, 1.0)
    scaler.step(opt)
    scaler.update()
    opt.zero_grad(set_to_none=True)
    sched.step()


def main(a):
    apply_image_defaults(a)
    if a.dry_run or a.smoke:
        dry_run(a)
        return
    torch.manual_seed(a.seed)
    random.seed(a.seed)
    device = torch.device(a.device)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log = open(out / "log.jsonl", "a", encoding="utf-8")
    holder = [None]  # FrameRenderer. finally 가 예외가 나도 브라우저를 닫게.

    def emit(rec):
        rec["time"] = time.time()
        rec["input"] = "image"
        print(json.dumps(rec, ensure_ascii=False), flush=True)
        log.write(json.dumps(rec, ensure_ascii=False) + "\n")
        log.flush()

    try:
        _train(a, device, out, emit, holder)
    finally:
        if holder[0] is not None:
            holder[0].close()
        log.close()


def _train(a, device, out, emit, holder):
    label = getattr(a, "label", "soft")
    game_every = int(getattr(a, "game_eval_every", 0) or 0)
    recs = load_records(a.data)
    tr, va = training_split(recs, a.limit, a.eval_samples)
    emit({"event": "data", "records": len(recs), "train": len(tr), "val": len(va),
          "renderer": a.renderer, "label": label, "model": a.model})
    if not tr:
        raise SystemExit("no training rows")
    if game_every:
        import matplotlib  # 평가마다 곡선을 다시 그린다. 없으면 학습을 시작하지 않는다.
        del matplotlib

    processor, model, dtype = load_image_model(a.model, a.device, a.dtype)
    skip = is_vision_path if a.freeze_vision else None
    if a.freeze_vision:
        freeze_vision(model)
    n_lora = inject(model, C.LORA_TARGETS, a.r, a.alpha, a.dropout, skip=skip)
    use_ckpt = not a.no_grad_ckpt
    if use_ckpt:
        if hasattr(model, "enable_input_require_grads"):
            model.enable_input_require_grads()
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.train()
    params = [p for p in model.parameters() if p.requires_grad]
    emit({"event": "model", "lora_layers": n_lora, "trainable_M": round(sum(p.numel() for p in params) / 1e6, 2),
          "dtype": str(dtype).replace("torch.", ""), "freeze_vision": bool(a.freeze_vision), "grad_ckpt": use_ckpt,
          "model": a.model, "label": label})
    slot_ids = torch.tensor(slot_ids_for(processor.tokenizer, 4), device=device)

    renderer = FrameRenderer(a.renderer)
    holder[0] = renderer
    try:
        renderer.open()
        collate = make_collate(processor, C.IMAGE_MAX_LEN, label)
        train_ds = ImageSFT(tr, True, a.seed, renderer)
        # 배치보다 샘플이 적으면(스모크) 마지막 배치를 버리지 않는다.
        drop = len(train_ds) >= a.micro_batch * 2
        train_loader = DataLoader(train_ds, batch_size=a.micro_batch, shuffle=True, drop_last=drop, collate_fn=collate)
        val_loader = DataLoader(ImageSFT(va, False, a.seed, renderer), batch_size=a.micro_batch,
                                shuffle=False, collate_fn=collate)
        accum = max(1, a.batch // a.micro_batch)
        if len(train_loader) == 0:
            raise SystemExit("train loader is empty; lower --micro_batch")
        if accum > len(train_loader):
            # ponytail: 스모크처럼 배치 수가 accum 보다 적으면 에폭을 한 스텝으로 묶는다.
            # 긴 학습에서는 len(loader) >> accum 이라 이 분기를 타지 않는다.
            print(f"[image] grad accum {accum} > {len(train_loader)} batches; using {len(train_loader)}", flush=True)
            accum = len(train_loader)
        total = a.max_steps or max(1, len(train_loader) // accum) * a.epochs
        warm = max(1, int(C.WARMUP * total))
        opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=C.WEIGHT_DECAY)
        sched = torch.optim.lr_scheduler.LambdaLR(
            opt, lambda s: (s + 1) / warm if s < warm else 0.5 * (1 + math.cos(math.pi * (s - warm) / max(1, total - warm))))
        scaler = torch.amp.GradScaler("cuda", init_scale=2.0 ** 10, enabled=device.type == "cuda" and dtype == torch.float16)
        cfg = {"base_model": a.model, "targets": list(C.LORA_TARGETS), "r": a.r, "alpha": a.alpha,
               "input": "image", "skip_visual": bool(a.freeze_vision), "dtype": a.dtype, "renderer": a.renderer,
               "label": label}
        start = {"event": "start", "total_steps": total, "accum": accum, "label": label, "model": a.model}
        if not game_every:
            start.update(evaluate(model, val_loader, slot_ids, device, dtype))
        emit(start)

        step, best, t0, run = 0, -1.0, time.time(), []
        window, best_score, stop = [], None, None
        guard = Guard(getattr(a, "score_drop", C.BASE_SCORE_DROP),
                      getattr(a, "score_patience", C.BASE_SCORE_PATIENCE),
                      getattr(a, "kl_patience", C.BASE_KL_PATIENCE))

        def model_probs(live, legal):
            # 8GB: 판이 여러 개여도 프레임은 한 장씩. 학습 그래프는 이미 비운 뒤다.
            out_p = []
            with torch.no_grad():
                for i in range(len(live)):
                    frame = renderer.render(B.to_grid(live[i].board))
                    out_p.extend(image_move_probs(
                        model, processor, slot_ids, device, dtype, [frame], [legal[i]]))
            return out_p

        def game_eval(at_step, train_loss):
            nonlocal best, best_score, stop
            was = model.training
            model.eval()
            try:
                val = evaluate(model, val_loader, slot_ids, device, dtype)
                seeds = [a.game_eval_seed_base + i for i in range(a.game_eval_games)]
                with torch.no_grad():
                    games = play("model", seeds, a.game_eval_max_moves, batch=1, agreement=True,
                                 detail=True, model_probs=model_probs)
                row = metrics_row(at_step, train_loss, val, games, seeds)
                record_game_metrics(out, row)
                is_best, reason = guard.update(row["mean_score"], row["val_kl"])
                if val["val_agreement"] > best:
                    best = val["val_agreement"]
                if is_best:
                    best_score = row["mean_score"]
                    save_adapter(model, out / "best", {**cfg, "step": at_step, "mean_score": best_score, **val})
                shown = {k: v for k, v in row.items() if k not in ("scores", "moves", "max_tiles")}
                emit({"event": "game_eval", **shown, "is_best": is_best})
                emit({"event": "eval", "step": at_step, **val})
                if reason and not getattr(a, "no_early_stop", False):
                    stop = reason
                    emit({"event": "stop", "step": at_step, "reason": reason, "best_mean_score": best_score})
            finally:
                if was:
                    model.train()

        if game_every:
            n_probe = min(_PROBE, len(train_ds))
            probe_loader = DataLoader(Subset(train_ds, range(n_probe)), batch_size=a.micro_batch,
                                      shuffle=False, collate_fn=collate)
            game_eval(0, evaluate(model, probe_loader, slot_ids, device, dtype)["val_loss"])

        while step < total and stop is None:
            for i, batch in enumerate(train_loader):
                logits = _logits(model, batch, slot_ids, device, dtype)
                loss = soft_ce(logits, batch["targets"].to(device)).mean()
                scaler.scale(loss / accum).backward()
                run.append(loss.item())
                if game_every:
                    window.append(loss.item())
                if (i + 1) % accum:
                    continue
                _step(scaler, opt, params, sched, device)
                step += 1
                if step % 10 == 0 or step == total or step <= 3:
                    emit({"event": "train", "step": step, "loss": sum(run) / len(run), "lr": sched.get_last_lr()[0],
                          "grad_scale": scaler.get_scale(), "sec": round(time.time() - t0, 1)})
                    run = []
                do_game = bool(game_every) and step % game_every == 0
                if do_game:
                    train_loss = sum(window) / len(window) if window else None
                    window = []
                    game_eval(step, train_loss)
                elif step % a.eval_every == 0 or step == total:
                    ev = evaluate(model, val_loader, slot_ids, device, dtype)
                    emit({"event": "eval", "step": step, **ev})
                    if ev["val_agreement"] > best:
                        best = ev["val_agreement"]
                        if not game_every:
                            save_adapter(model, out / "best", {**cfg, "step": step, **ev})
                if stop is not None or step >= total:
                    break
            train_ds.epoch += 1
        save_adapter(model, out / "final", {**cfg, "step": step})
        emit({"event": "done", "step": step, "best_val_agreement": best, "best_mean_score": best_score,
              "stop": stop or "max_steps", "out": str(out)})
    finally:
        renderer.close()
        holder[0] = None
