"""평가: 학습 시드와 겹치지 않는 시드로 N판을 두고 점수/최대 타일/도달률을 비교. 수는 argmax.
vs_expert = (모델 - 무작위) / (전문가 - 무작위)  (PlayJev README의 'vs teacher'와 같은 정의)
--input image 는 같은 집계를 results/<run>/eval.json 에 쓴다. 기본값 text 의 출력 파일 형식은 그대로다.

  python evaluate.py --policies random expert model --adapter ckpt/run1/best --games 16
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from pathlib import Path

import config as C
from expert import Expert
from game2048 import Game2048, render_state


def play(policy: str, seeds: list[int], max_moves: int, adapter=None, model_path=C.MODEL_PATH, batch=C.EVAL_BATCH,
         agreement=False, detail=False, model_probs=None) -> dict:
    games = [Game2048(s) for s in seeds]
    ex = Expert(); rng = random.Random(7)
    lm = None
    # model_probs 가 있으면 이미지 정책이 수를 고른다. 텍스트 호출은 이 인자를 넘기지 않는다.
    if policy == "model" and model_probs is None:
        from policy import LMPolicy
        lm = LMPolicy(model_path, adapter)
    agree = []; t0 = time.time()
    while True:
        live = [g for g in games if not g.done() and g.moves < max_moves]
        if not live:
            break
        legal = [[a for a in ("up", "down", "left", "right") if a in g.legal()] for g in live]
        if policy == "random":
            acts = [rng.choice(l) for l in legal]
        elif policy == "expert":
            acts = [ex.act(g.board) for g in live]
        else:
            if model_probs is not None:
                ps = model_probs(live, legal)
                acts = [l[max(range(len(l)), key=p.__getitem__)] for p, l in zip(ps, legal)]
            else:
                acts = []
                for s in range(0, len(live), batch):
                    ps = lm.probs([render_state(g) for g in live[s:s + batch]], legal[s:s + batch])
                    acts += [l[max(range(len(l)), key=p.__getitem__)] for p, l in zip(ps, legal[s:s + batch])]
            if agreement:
                agree += [ex.act(g.board) == a for g, a in zip(live, acts)]
        for g, act in zip(live, acts):
            g.step(act)
    scores = [g.score for g in games]; tiles = [g.max_tile() for g in games]
    res = {"policy": policy, "games": len(games), "mean_score": statistics.fmean(scores),
           "median_score": statistics.median(scores), "mean_max_tile": statistics.fmean(tiles),
           "best_tile": max(tiles), "mean_moves": statistics.fmean(g.moves for g in games),
           **{f"reach_{t}": sum(x >= t for x in tiles) / len(tiles) for t in (256, 512, 1024, 2048)},
           "sec": round(time.time() - t0, 1)}
    if agree:
        res["expert_agreement"] = sum(agree) / len(agree)
    if detail:
        dist = {}
        for t in tiles:
            dist[str(t)] = dist.get(str(t), 0) + 1
        res["max_tile_distribution"] = dict(sorted(dist.items(), key=lambda kv: int(kv[0])))
        res["scores"] = scores
        res["max_tiles"] = tiles
        res["moves"] = [g.moves for g in games]
    return res


def main(a):
    if a.input == "image":
        from eval_image import main as image_main
        return image_main(a)
    seeds = [a.seed_base + i for i in range(a.games)]
    results = {}
    for pol in a.policies:
        r = play(pol, seeds, a.max_moves, a.adapter, a.model, a.batch, a.agreement)
        results[pol] = r; print(json.dumps(r, ensure_ascii=False), flush=True)
    if {"random", "expert"} <= results.keys():
        lo, hi = results["random"]["mean_score"], results["expert"]["mean_score"]
        for pol, r in results.items():
            r["vs_expert"] = (r["mean_score"] - lo) / (hi - lo) if hi != lo else float("nan")
    print("\npolicy   mean_score  max_tile  reach512  reach1024  reach2048  vs_expert")
    for pol, r in results.items():
        print(f"{pol:<8} {r['mean_score']:>10.0f} {r['mean_max_tile']:>9.0f} {r['reach_512']:>9.2f} "
              f"{r['reach_1024']:>10.2f} {r['reach_2048']:>10.2f} {r.get('vs_expert', float('nan')):>10.2f}")
    C.RESULTS_DIR.mkdir(exist_ok=True)
    out = Path(a.out or C.RESULTS_DIR / f"eval_{int(time.time())}.json")
    # 이미지 전용 플래그는 텍스트 결과 파일에 넣지 않는다. 예전에 저장하던 args 키만 남긴다.
    args_out = {k: v for k, v in vars(a).items()
                if k not in ("input", "renderer", "dtype", "run", "seed", "data", "device")}
    out.write_text(json.dumps({"args": args_out, "results": results}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"saved {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--policies", nargs="+", default=["random", "expert", "model"], choices=["random", "expert", "model"])
    p.add_argument("--adapter", default=None, help="LoRA 폴더 (예: ckpt/run1/best). 없으면 베이스 모델 제로샷")
    p.add_argument("--model", default=C.MODEL_PATH)
    p.add_argument("--games", type=int, default=C.EVAL_GAMES)
    p.add_argument("--max_moves", type=int, default=C.EVAL_MAX_MOVES)
    p.add_argument("--seed_base", type=int, default=C.EVAL_SEED_BASE)
    p.add_argument("--batch", type=int, default=C.EVAL_BATCH)
    p.add_argument("--agreement", action="store_true", help="모델 수가 전문가 argmax와 같은 비율도 계산")
    p.add_argument("--out", default=None)
    p.add_argument("--input", choices=("text", "image"), default="text")
    p.add_argument("--renderer", choices=("pil", "playwright"), default=C.IMAGE_RENDERER)
    p.add_argument("--dtype", default=None, help="image dtype. 기본 float16. bfloat16 은 PlayJev 로더와 같음")
    p.add_argument("--run", default=None, help="image 결과를 results/<run>/eval.json 에 저장")
    p.add_argument("--seed", type=int, default=C.SEED, help="image 검증셋 선택지 섞기 시드 (학습 --seed 와 같게)")
    p.add_argument("--data", nargs="*", default=None, help="image 검증 KL 에 쓸 jsonl (학습과 같은 파일)")
    p.add_argument("--device", default=C.DEVICE)
    main(p.parse_args())
