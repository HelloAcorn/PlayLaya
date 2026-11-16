"""이미지 평가. 점수/수/최대 타일 집계는 evaluate.play 와 같은 함수라 텍스트 경로와 칸이 같다.

시드 기본값 100000, 100판, 수 상한 3000. 모델 수는 그 판에서 전문가 argmax 와 얼마나 같은지(teacher agreement),
검증 jsonl 이 있으면 텍스트 학습과 같은 에피소드 분할에서 KL(teacher || model) 을 같이 적는다.
결과: results/<run>/eval.json (results/ 는 gitignore).

  python evaluate.py --input image --policies model --model OmniJev/PlayJev-0.8B --run playjev_zeroshot --data data/clone.jsonl
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import board as B
import config as C
from evaluate import play
from frame import DIFFERENCES


def flag_passed(*flags: str) -> bool:
    argv = sys.argv[1:]
    return any(s == f or s.startswith(f + "=") for f in flags for s in argv)


def default_run(a) -> str:
    if a.adapter:
        p = Path(a.adapter)
        return p.parent.name if p.name in ("best", "final") else p.name
    return "playjev_zeroshot"


def apply_eval_defaults(a):
    if not flag_passed("--games"):
        a.games = C.IMAGE_EVAL_GAMES
    if not flag_passed("--batch"):
        a.batch = C.IMAGE_EVAL_BATCH
    if not getattr(a, "dtype", None):
        a.dtype = C.IMAGE_DTYPE
    if not flag_passed("--model"):
        cfg_path = Path(a.adapter) / "adapter_config.json" if a.adapter else None
        if cfg_path is not None and cfg_path.exists():
            a.model = json.loads(cfg_path.read_text(encoding="utf-8"))["base_model"]
        elif a.adapter and Path(C.MODEL_PATH).exists():
            a.model = C.MODEL_PATH
        elif a.adapter:
            a.model = C.IMAGE_BASE_MODEL
        else:
            a.model = C.PLAYJEV_MODEL
    if not getattr(a, "run", None):
        a.run = default_run(a)


def val_metrics(a, policy) -> dict | None:
    """학습 train_image.evaluate 와 같은 검증 분할, 같은 시드 섞기."""
    if not a.data:
        return None
    from torch.utils.data import DataLoader

    from frame import FrameRenderer
    from train import load_records, split
    from train_image import ImageSFT, evaluate, make_collate

    paths = a.data if isinstance(a.data, list) else [a.data]
    recs = load_records(paths)
    tr, va = split(recs, C.VAL_FRACTION)
    if not va:
        va = tr[-max(4, len(tr) // 20):]
    va = va[: C.EVAL_SAMPLES]
    renderer = FrameRenderer(a.renderer)
    renderer.open()
    try:
        loader = DataLoader(ImageSFT(va, False, a.seed, renderer), batch_size=max(1, a.batch), shuffle=False,
                            collate_fn=make_collate(policy.processor, C.IMAGE_MAX_LEN))
        report = evaluate(policy.model, loader, policy.slot_ids, policy.device, policy.dtype)
    finally:
        renderer.close()
    report["data"] = paths
    report["seed"] = a.seed
    return report


def main(a):
    apply_eval_defaults(a)
    seeds = [a.seed_base + i for i in range(a.games)]
    results = {}
    image_pol = None
    if "model" in a.policies:
        from image_policy import ImagePolicy
        image_pol = ImagePolicy(a.model, a.adapter, device=a.device, dtype=a.dtype, renderer=a.renderer)

    def model_probs(live, legal):
        out = []
        for s in range(0, len(live), a.batch):
            frames = [image_pol.frames.render(B.to_grid(g.board)) for g in live[s:s + a.batch]]
            out.extend(image_pol.probs(frames, legal[s:s + a.batch]))
        return out

    try:
        for pol in a.policies:
            r = play(pol, seeds, a.max_moves, a.adapter, a.model, a.batch,
                     agreement=(pol == "model"), detail=True,
                     model_probs=model_probs if pol == "model" else None)
            r["input"] = "image"
            results[pol] = r
            print(json.dumps({k: v for k, v in r.items() if k not in ("scores", "max_tiles", "moves")},
                             ensure_ascii=False), flush=True)
        if {"random", "expert"} <= results.keys():
            lo, hi = results["random"]["mean_score"], results["expert"]["mean_score"]
            for r in results.values():
                r["vs_expert"] = (r["mean_score"] - lo) / (hi - lo) if hi != lo else float("nan")
        val = val_metrics(a, image_pol) if image_pol is not None and a.data else None
    finally:
        if image_pol is not None:
            image_pol.close()

    print("\npolicy   mean_score  mean_moves  max_tile  reach2048  expert_agreement  vs_expert")
    for pol, r in results.items():
        print(f"{pol:<8} {r['mean_score']:>10.0f} {r['mean_moves']:>11.1f} {r['mean_max_tile']:>9.0f} "
              f"{r['reach_2048']:>10.2f} {r.get('expert_agreement', float('nan')):>17.3f} "
              f"{r.get('vs_expert', float('nan')):>10.2f}")
    if val:
        print(f"val n={val['n']} kl={val['val_kl']:.4f} agreement={val['val_agreement']:.3f} loss={val['val_loss']:.4f}")
    else:
        print("val KL skipped (pass --data data/clone.jsonl to score the same validation split as training)")

    C.RESULTS_DIR.mkdir(exist_ok=True)
    out = Path(a.out) if a.out else C.RESULTS_DIR / a.run / "eval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "input": "image",
        "run": a.run,
        "model": a.model,
        "adapter": a.adapter,
        "dtype": a.dtype,
        "renderer": a.renderer,
        "renderer_note": DIFFERENCES,
        "seed_base": a.seed_base,
        "games": a.games,
        "max_moves": a.max_moves,
        "args": {k: v for k, v in vars(a).items()},
        "results": results,
        "val": val,
    }
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"saved {out}")
