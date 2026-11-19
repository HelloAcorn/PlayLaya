"""게임 평가 지표, 조기 종료, 버킷 균형, 곡선.

torch 를 불러오지 않는다. 그림은 plot_curves 안에서만 matplotlib 를 연다.
"""
from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path

BUCKETS = ("le128", "256", "512", "ge1024")
CSV_COLUMNS = (
    "step", "train_loss", "val_loss", "val_kl", "val_agreement",
    "mean_score", "median_score", "min_score", "max_score", "mean_moves",
    "teacher_agreement", "max_tile_distribution",
)


def tile_bucket(tile: int) -> str:
    """최대 타일. 2048 타일은 2의 거듭제곱이라 256/512 는 그 값 하나다."""
    if tile <= 128:
        return "le128"
    if tile <= 256:
        return "256"
    if tile <= 512:
        return "512"
    return "ge1024"


def bucket_caps(target: int, caps_arg) -> dict[str, int]:
    """0 은 그 버킷을 막지 않는다. target 만 있으면 네 버킷이 target 을 나눠 갖는다.
    나머지는 높은 타일 쪽에 붙여 후반이 더 짧아지지 않게 한다.
    """
    if not caps_arg:
        if not target:
            return {b: 0 for b in BUCKETS}
        base, extra = divmod(int(target), len(BUCKETS))
        start = len(BUCKETS) - extra
        return {b: base + (1 if i >= start else 0) for i, b in enumerate(BUCKETS)}
    if len(caps_arg) == 1:
        return {b: int(caps_arg[0]) for b in BUCKETS}
    if len(caps_arg) != 4:
        raise SystemExit("--bucket_cap 은 정수 1개(전 버킷) 또는 4개(<=128 256 512 >=1024)")
    return dict(zip(BUCKETS, (int(x) for x in caps_arg)))


def should_keep(bucket: str, counts: dict, caps: dict, n: int, target: int) -> bool:
    cap = caps.get(bucket, 0)
    if cap and counts.get(bucket, 0) >= cap:
        return False
    if target and n >= target:
        return False
    return True


def finished_collecting(n: int, target: int, counts: dict, caps: dict) -> bool:
    if target and n >= target:
        return True
    limited = [b for b in BUCKETS if caps.get(b, 0)]
    return bool(limited) and all(counts.get(b, 0) >= caps[b] for b in limited)


def loss_targets(probs, index: int, label: str) -> list[float]:
    """soft: 전문가 분포. hard: 그 argmax 한 칸만 1. 둘 다 같은 soft CE 식에 들어간다."""
    soft = [float(x) for x in probs]
    if label == "soft":
        return soft
    if label == "hard":
        hard = [0.0] * len(soft)
        hard[index] = 1.0
        return hard
    raise ValueError(f"unknown label {label}")


def uniform_ce(records) -> float:
    """합법 수에 균일한 정책의 평균 교차 엔트로피. soft_ce 와 같이 자연로그."""
    if not records:
        raise ValueError("no records")
    return sum(math.log(max(1, len(r["legal"]))) for r in records) / len(records)


def tail_mean(values, window: int) -> float | None:
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    tail = vals[-max(1, window):]
    return sum(tail) / len(tail)


def overfit_ok(last_loss, uniform: float, factor: float) -> bool:
    """손실이 균일 정책보다 factor 배 아래로 내려왔는지. factor 0.6 이면 균일의 60% 미만."""
    return last_loss is not None and uniform > 0 and last_loss < factor * uniform


class Guard:
    """10판 평균이 최고보다 30% 넘게 낮은 평가가 연속 2번이거나,
    검증 KL 이 K번 연속 줄지 않으면 멈춘다. 첫 평가(step 0)는 기준선이다.
    """

    def __init__(self, score_drop: float = 0.30, score_patience: int = 2, kl_patience: int = 4):
        self.score_drop = float(score_drop)
        self.score_patience = int(score_patience)
        self.kl_patience = int(kl_patience)
        self.best_score = None
        self.best_kl = None
        self.below = 0
        self.kl_stall = 0

    def update(self, mean_score: float, val_kl: float) -> tuple[bool, str | None]:
        if self.best_score is None:
            self.best_score = float(mean_score)
            self.best_kl = float(val_kl)
            return True, None
        is_best = float(mean_score) > self.best_score
        if is_best:
            self.best_score = float(mean_score)
            self.below = 0
        elif self.score_patience and mean_score < self.best_score * (1.0 - self.score_drop):
            self.below += 1
        else:
            self.below = 0
        if float(val_kl) < self.best_kl:
            self.best_kl = float(val_kl)
            self.kl_stall = 0
        elif self.kl_patience:
            self.kl_stall += 1
        reasons = []
        if self.score_patience and self.below >= self.score_patience:
            reasons.append("score")
        if self.kl_patience and self.kl_stall >= self.kl_patience:
            reasons.append("val_kl")
        return is_best, "+".join(reasons) or None


def metrics_row(step: int, train_loss, val: dict, games: dict, seeds: list[int]) -> dict:
    scores = [float(s) for s in games["scores"]]
    return {
        "step": int(step),
        "train_loss": None if train_loss is None else float(train_loss),
        "val_loss": float(val["val_loss"]),
        "val_kl": float(val["val_kl"]),
        "val_agreement": float(val["val_agreement"]),
        "mean_score": float(games["mean_score"]),
        "median_score": float(games["median_score"]),
        "min_score": min(scores),
        "max_score": max(scores),
        "mean_moves": float(games["mean_moves"]),
        "teacher_agreement": None if games.get("expert_agreement") is None else float(games["expert_agreement"]),
        "max_tile_distribution": games["max_tile_distribution"],
        "scores": scores,
        "moves": [int(m) for m in games["moves"]],
        "max_tiles": [int(t) for t in games["max_tiles"]],
        "seeds": [int(s) for s in seeds],
    }


def events_from_log(path, name: str) -> list[dict]:
    found = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("event") == name:
                found.append(rec)
    return found


def load_metrics(path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _replace(tmp: Path, dest: Path) -> None:
    os.replace(tmp, dest)


def _write_csv(path: Path, rows: list[dict]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in rows:
            dist = r.get("max_tile_distribution") or {}
            flat = {k: r.get(k) for k in CSV_COLUMNS}
            flat["max_tile_distribution"] = json.dumps(dist, ensure_ascii=False, sort_keys=True)
            w.writerow({k: "" if flat[k] is None else flat[k] for k in CSV_COLUMNS})
    _replace(tmp, path)


def append_metrics(jsonl_path, row: dict) -> None:
    jsonl_path = Path(jsonl_path)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
    _write_csv(jsonl_path.with_name("metrics.csv"), load_metrics(jsonl_path))


def _nan(v):
    return float("nan") if v is None else float(v)


def series(rows: list[dict]) -> dict:
    return {
        "step": [int(r["step"]) for r in rows],
        "mean_score": [_nan(r["mean_score"]) for r in rows],
        "median_score": [_nan(r["median_score"]) for r in rows],
        "min_score": [_nan(r["min_score"]) for r in rows],
        "max_score": [_nan(r["max_score"]) for r in rows],
        "train_loss": [_nan(r["train_loss"]) for r in rows],
        "val_loss": [_nan(r["val_loss"]) for r in rows],
        "val_agreement": [_nan(r.get("val_agreement")) for r in rows],
        "teacher_agreement": [_nan(r.get("teacher_agreement")) for r in rows],
    }


def plot_curves(jsonl_path, png_path) -> None:
    """score_curve.png 를 매번 다시 그린다. 위: 10판 평균(최소-최대 띠, 중앙값). 아래: 손실과 일치."""
    rows = load_metrics(jsonl_path)
    if not rows:
        return
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = series(rows)
    fig, (ax_s, ax_l) = plt.subplots(2, 1, figsize=(8, 7), sharex=True, layout="constrained")
    ax_s.plot(s["step"], s["mean_score"], label="mean score")
    ax_s.fill_between(s["step"], s["min_score"], s["max_score"], alpha=0.2, label="min/max")
    ax_s.plot(s["step"], s["median_score"], linestyle="--", label="median")
    ax_s.set_ylabel("score")
    ax_s.legend(loc="best")
    ax_l.plot(s["step"], s["train_loss"], label="train loss")
    ax_l.plot(s["step"], s["val_loss"], label="val loss")
    ax_l.set_xlabel("step")
    ax_l.set_ylabel("loss")
    ax_a = ax_l.twinx()
    ax_a.plot(s["step"], s["teacher_agreement"], linestyle=":", label="teacher agreement")
    ax_a.plot(s["step"], s["val_agreement"], linestyle=":", label="val agreement")
    ax_a.set_ylabel("agreement")
    ax_a.set_ylim(-0.05, 1.05)
    h1, l1 = ax_l.get_legend_handles_labels()
    h2, l2 = ax_a.get_legend_handles_labels()
    ax_l.legend(h1 + h2, l1 + l2, loc="best")
    png_path = Path(png_path)
    tmp = png_path.with_name(png_path.stem + ".tmp.png")
    fig.savefig(tmp, dpi=120)
    plt.close(fig)
    _replace(tmp, png_path)


def record_game_metrics(out_dir, row: dict) -> Path:
    out_dir = Path(out_dir)
    jsonl = out_dir / "metrics.jsonl"
    append_metrics(jsonl, row)
    plot_curves(jsonl, out_dir / "score_curve.png")
    return jsonl
