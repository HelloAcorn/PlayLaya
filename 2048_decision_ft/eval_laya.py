"""Zero-shot convaiinnovations/laya on 2048. No fine-tune.

The English checkpoint's answer shifts with option order, so each position asks the same
choice under every rotation and the move is the argmax of the averaged probabilities.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path

import laya

import config as C
from game2048 import ACTIONS, Game2048, render_state
from prompt import INSTRUCTIONS, OPTION_DESC


def questions_for(legal: tuple[str, ...]) -> dict:
    crit = {m: OPTION_DESC[m] for m in legal}
    k = len(legal)
    return {
        f"r{r}": {
            "type": "choice",
            "instructions": INSTRUCTIONS,
            "criteria": crit,
            "option_order": [(i + r) % k for i in range(k)],
        }
        for r in range(k)
    }


def pick(answers: dict, legal: tuple[str, ...]) -> str:
    totals = {m: 0.0 for m in legal}
    n = 0
    for ans in answers.values():
        n += 1
        for m, p in ans["probabilities"].items():
            totals[m] += p
    return max(totals, key=lambda m: (totals[m] / n, -legal.index(m)))


def play(games: int, max_moves: int, seed_base: int, batch: int) -> dict:
    board = [Game2048(seed_base + i) for i in range(games)]
    agent = laya.load("convaiinnovations/laya", device="cuda")
    qcache: dict[tuple[str, ...], dict] = {}
    t0 = time.time()
    ply = 0
    while True:
        live = [g for g in board if not g.done() and g.moves < max_moves]
        if not live:
            break
        groups: dict[tuple[str, ...], list] = defaultdict(list)
        for g in live:
            groups[tuple(a for a in ACTIONS if a in g.legal())].append(g)
        for legal, gs in groups.items():
            if len(legal) == 1:
                for g in gs:
                    g.step(legal[0])
                continue
            qs = qcache.setdefault(legal, questions_for(legal))
            for s in range(0, len(gs), batch):
                chunk = gs[s:s + batch]
                results = agent.predict_batch([render_state(g) for g in chunk], qs, batch_size=batch)
                for g, res in zip(chunk, results):
                    if res["usage"].get("truncated") or res["usage"].get("options"):
                        raise RuntimeError(f"state or options truncated: {res['usage']}")
                    g.step(pick(res["answers"], legal))
        ply += 1
        if ply % 25 == 0:
            done = sum(g.done() or g.moves >= max_moves for g in board)
            print(json.dumps({"ply": ply, "done": done, "sec": round(time.time() - t0, 1)}), flush=True)
    scores = [g.score for g in board]
    tiles = [g.max_tile() for g in board]
    return {
        "model": "convaiinnovations/laya",
        "trained": False,
        "games": games,
        "seed_base": seed_base,
        "max_moves": max_moves,
        "mean_score": statistics.fmean(scores),
        "median_score": statistics.median(scores),
        "mean_max_tile": statistics.fmean(tiles),
        "best_tile": max(tiles),
        "mean_moves": statistics.fmean(g.moves for g in board),
        **{f"reach_{t}": sum(x >= t for x in tiles) / len(tiles) for t in (128, 256, 512, 1024, 2048)},
        "scores": scores,
        "sec": round(time.time() - t0, 1),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--games", type=int, default=100)
    p.add_argument("--max_moves", type=int, default=C.EVAL_MAX_MOVES)
    p.add_argument("--seed_base", type=int, default=C.EVAL_SEED_BASE)
    p.add_argument("--batch", type=int, default=8)
    a = p.parse_args()
    res = play(a.games, a.max_moves, a.seed_base, a.batch)
    C.RESULTS_DIR.mkdir(exist_ok=True)
    out = C.RESULTS_DIR / "laya_zeroshot_100.json"
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "scores"}, ensure_ascii=False), flush=True)
    print(f"saved {out}", flush=True)
