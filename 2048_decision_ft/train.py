"""LoRA SFT. 손실 = 전문가 soft target과 '합법 수 글자' softmax 사이의 교차 엔트로피 (PlayJev train_sft와 같은 방식).
다음 토큰 손실이나 텍스트 정답은 학습하지 않음. 선택지 순서는 샘플마다 무작위로 섞어 글자 위치 편향을 없앰.
정밀도: 베이스 fp16 고정, LoRA 가중치 fp32, fp16 autocast + GradScaler, 판독은 fp32.
--input image 는 화면 한 장 경로(train_image.py)다. 기본값 text 의 학습 루프는 그대로다.

  python train.py --data data/clone.jsonl --out ckpt/run1
  python train.py --data data/clone.jsonl --out ckpt/smoke --max_steps 2 --limit 64
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import random
import time
import zlib
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

import config as C
from lora import inject, save_adapter
from policy import load_base, slot_ids_for, slot_logits
from prompt import build_prompt


def load_records(patterns: list[str]) -> list[dict]:
    recs = []
    for pat in patterns:
        for path in sorted(glob.glob(pat)):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        r = json.loads(line); r["_src"] = Path(path).name; recs.append(r)
    if not recs:
        raise SystemExit(f"no records in {patterns}")
    return recs


def split(recs, frac):
    """에피소드 단위 분리: 같은 게임의 이웃 상태가 학습/검증에 갈라지지 않게."""
    tr, va = [], []
    for r in recs:
        key = f"{r['_src']}:{r['seed']}".encode()
        (va if (zlib.crc32(key) % 1000) < frac * 1000 else tr).append(r)
    return tr, va


class SFTData(Dataset):
    def __init__(self, recs, train: bool, seed: int):
        self.recs, self.train, self.seed, self.epoch = recs, train, seed, 0

    def __len__(self):
        return len(self.recs)

    def __getitem__(self, i):
        r = self.recs[i]
        opts = list(r["legal"])
        random.Random(hash((self.seed, self.epoch if self.train else 0, i))).shuffle(opts)
        return build_prompt(r["state"], opts), [r["probs"][o] for o in opts], opts.index(r["action"])


def make_collate(tok, max_len):
    def collate(items):
        prompts, targets, best = zip(*items)
        enc = tok(list(prompts), return_tensors="pt", padding=True, truncation=True, max_length=max_len)
        k = max(len(t) for t in targets)
        tgt = torch.zeros(len(items), 4)
        for i, t in enumerate(targets):
            tgt[i, : len(t)] = torch.tensor(t)
        tgt = tgt / tgt.sum(-1, keepdim=True)
        return {"input_ids": enc["input_ids"], "attention_mask": enc["attention_mask"], "targets": tgt,
                "n_opts": torch.tensor([len(t) for t in targets]), "best": torch.tensor(best)}
    return collate


def soft_ce(logits, targets):
    logp = F.log_softmax(logits, -1)
    return -(targets * logp.masked_fill(targets == 0, 0.0)).sum(-1)


def forward(model, batch, slot_ids, device):
    with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
        return slot_logits(model, batch["input_ids"].to(device), batch["attention_mask"].to(device), slot_ids,
                           batch["n_opts"].to(device))


@torch.no_grad()
def evaluate(model, loader, slot_ids, device):
    model.eval(); ce = []; agree = []
    for batch in loader:
        logits = forward(model, batch, slot_ids, device)
        ce += soft_ce(logits, batch["targets"].to(device)).tolist()
        agree += (logits.argmax(-1).cpu() == batch["best"]).tolist()
    model.train()
    return {"val_loss": sum(ce) / max(1, len(ce)), "val_agreement": sum(agree) / max(1, len(agree)), "n": len(ce)}


def main(a):
    if a.input == "image" or a.dry_run or a.smoke:
        if (a.dry_run or a.smoke) and a.input != "image":
            raise SystemExit("[dry-run] 이 스모크는 --input image 용입니다. 텍스트 스모크는 --max_steps 2 --limit 32")
        from train_image import main as image_main
        return image_main(a)
    torch.manual_seed(a.seed); random.seed(a.seed)
    device = torch.device(a.device)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    log = open(out / "log.jsonl", "a", encoding="utf-8")

    def emit(rec):
        rec["time"] = time.time(); print(json.dumps(rec, ensure_ascii=False), flush=True)
        log.write(json.dumps(rec, ensure_ascii=False) + "\n"); log.flush()

    recs = load_records(a.data)
    tr, va = split(recs, C.VAL_FRACTION)
    if not va:  # 스모크처럼 에피소드가 너무 적을 때
        va = tr[-max(4, len(tr) // 20):]; tr = tr[: len(tr) - len(va)]
    if a.limit:
        tr, va = tr[: a.limit], va[: max(4, a.limit // 4)]
    va = va[: a.eval_samples]
    emit({"event": "data", "records": len(recs), "train": len(tr), "val": len(va)})

    tok, model = load_base(a.model, a.device)
    n_lora = inject(model, C.LORA_TARGETS, a.r, a.alpha, a.dropout)
    if a.grad_ckpt:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.train()
    params = [p for p in model.parameters() if p.requires_grad]
    emit({"event": "model", "lora_layers": n_lora, "trainable_M": round(sum(p.numel() for p in params) / 1e6, 2)})
    slot_ids = torch.tensor(slot_ids_for(tok, 4), device=device)

    collate = make_collate(tok, C.MAX_LEN)
    train_ds = SFTData(tr, True, a.seed)
    train_loader = DataLoader(train_ds, batch_size=a.micro_batch, shuffle=True, drop_last=True, collate_fn=collate)
    val_loader = DataLoader(SFTData(va, False, a.seed), batch_size=a.micro_batch, shuffle=False, collate_fn=collate)

    accum = max(1, a.batch // a.micro_batch)
    total = a.max_steps or max(1, len(train_loader) // accum) * a.epochs
    warm = max(1, int(C.WARMUP * total))
    opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=C.WEIGHT_DECAY)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / warm if s < warm else 0.5 * (1 + math.cos(math.pi * (s - warm) / max(1, total - warm))))
    scaler = torch.amp.GradScaler("cuda", init_scale=2.0 ** 10, enabled=device.type == "cuda")  # 기본 65536은 첫 스텝들을 inf로 건너뜀
    cfg = {"base_model": a.model, "targets": list(C.LORA_TARGETS), "r": a.r, "alpha": a.alpha}
    emit({"event": "start", "total_steps": total, "accum": accum, **evaluate(model, val_loader, slot_ids, device)})

    step, best, t0, run = 0, -1.0, time.time(), []
    while step < total:
        for i, batch in enumerate(train_loader):
            logits = forward(model, batch, slot_ids, device)
            loss = soft_ce(logits, batch["targets"].to(device)).mean()
            scaler.scale(loss / accum).backward(); run.append(loss.item())
            if (i + 1) % accum:
                continue
            scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(params, 1.0)
            scaler.step(opt); scaler.update(); opt.zero_grad(set_to_none=True); sched.step(); step += 1
            if step % 10 == 0 or step == total or step <= 3:
                emit({"event": "train", "step": step, "loss": sum(run) / len(run), "lr": sched.get_last_lr()[0],
                      "grad_scale": scaler.get_scale(), "sec": round(time.time() - t0, 1)}); run = []
            if step % a.eval_every == 0 or step == total:
                ev = evaluate(model, val_loader, slot_ids, device); emit({"event": "eval", "step": step, **ev})
                if ev["val_agreement"] > best:
                    best = ev["val_agreement"]; save_adapter(model, out / "best", {**cfg, "step": step, **ev})
            if step >= total:
                break
        train_ds.epoch += 1
    save_adapter(model, out / "final", {**cfg, "step": step})
    emit({"event": "done", "step": step, "best_val_agreement": best, "out": str(out)})


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", nargs="+", default=[str(C.DATA_DIR / "*.jsonl")])
    p.add_argument("--out", default=str(C.CKPT_DIR / "run1"))
    p.add_argument("--model", default=C.MODEL_PATH)
    p.add_argument("--device", default=C.DEVICE)
    p.add_argument("--epochs", type=int, default=C.EPOCHS)
    p.add_argument("--max_steps", type=int, default=0)
    p.add_argument("--limit", type=int, default=0, help="스모크용: 학습 샘플 수 제한")
    p.add_argument("--lr", type=float, default=C.LR)
    p.add_argument("--batch", type=int, default=C.BATCH)
    p.add_argument("--micro_batch", type=int, default=C.MICRO_BATCH)
    p.add_argument("--r", type=int, default=C.LORA_R)
    p.add_argument("--alpha", type=float, default=C.LORA_ALPHA)
    p.add_argument("--dropout", type=float, default=C.LORA_DROPOUT)
    p.add_argument("--grad_ckpt", action="store_true", default=C.GRAD_CKPT)
    p.add_argument("--eval_every", type=int, default=C.EVAL_EVERY)
    p.add_argument("--eval_samples", type=int, default=C.EVAL_SAMPLES)
    p.add_argument("--seed", type=int, default=C.SEED)
    p.add_argument("--input", choices=("text", "image"), default="text")
    p.add_argument("--dry-run", action="store_true", help="이미지 스모크: 프레임/프롬프트/프로세서만 확인하고 학습하지 않음")
    p.add_argument("--smoke", action="store_true", help="--dry-run 과 같음")
    p.add_argument("--renderer", choices=("pil", "playwright"), default=C.IMAGE_RENDERER)
    p.add_argument("--dtype", default=None, help="image 가중치 dtype. 기본 float16. PlayJev 로더와 맞추려면 bfloat16")
    p.add_argument("--freeze-vision", action=argparse.BooleanOptionalAction, default=True,
                   help="image: 비전 타워를 얼리고 언어 모델만 LoRA (8GB 기본값)")
    p.add_argument("--no-grad-ckpt", action="store_true", help="image gradient checkpointing 을 끈다. 기본은 켜짐")
    main(p.parse_args())
