"""Qwen3.5-0.8B-Base 에서 이미지 2048 LoRA 를 돌리는 드라이버.

순서: 전문가 데이터(버킷 균형) -> 1천 상태 과적합 확인 -> 본학습.
본학습은 100 step 마다 시드 100000..100009 로 10판을 두고 곡선을 갱신한다.
10판은 약 5분이라 그보다 촘촘히 두지 않는다.
PlayJev-0.8B 가 아니라 원본 베이스에서 시작한다.
끝나면 out/.done 을 쓴다. 과적합이 안 되면 종료 코드 2 이고 .done 은 없다.

  python -u run_base_image.py --out ckpt/base_image --model C:\\workspace\\PlayJev\\models\\Qwen3.5-0.8B-Base

8GB RTX 2070 SUPER: fp16, 언어 모델 LoRA, 비전 타워 고정, gradient checkpointing,
micro batch 1, 유효 배치 8.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import config as C  # noqa: E402
from game_metrics import events_from_log, overfit_ok, tail_mean, uniform_ce  # noqa: E402
from train import load_records, training_split  # noqa: E402


def assert_base_model(name: str) -> None:
    low = name.replace("\\", "/").lower()
    leaf = low.rstrip("/").split("/")[-1]
    if "playjev-0.8b" in low and "qwen3.5-0.8b-base" not in leaf:
        raise SystemExit("이 런은 Qwen/Qwen3.5-0.8B-Base 에서 시작한다. PlayJev-0.8B 는 제로샷 기준선이다.")


def resolve_base(explicit: str | None) -> str:
    if explicit:
        name = explicit
    else:
        local = Path(C.MODEL_PATH)
        if local.exists() and "qwen3.5-0.8b-base" in local.name.lower():
            name = str(local)
        else:
            name = C.IMAGE_BASE_MODEL
    assert_base_model(name)
    return name


def _log(path: Path, msg: str) -> None:
    line = time.strftime("%Y-%m-%d %H:%M:%S") + " " + msg
    print(line, flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()


def _run(cmd: list[str], log) -> None:
    _log(log, "run " + " ".join(cmd))
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def main(a) -> int:
    out = Path(a.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    progress = out / "progress.log"
    done = out / ".done"
    if done.exists() and not a.force:
        _log(progress, f"already done ({done}). pass --force to run again")
        return 0
    if a.force and done.exists():
        done.unlink()

    model = resolve_base(a.model)
    data = Path(a.data)
    if not data.is_absolute():
        data = ROOT / data
    paired = Path(a.paired_text) if a.paired_text else None
    if paired is not None and not paired.is_absolute():
        paired = ROOT / paired
    caps = [C.BASE_BUCKET_CAP] if a.bucket_cap is None else list(a.bucket_cap)
    _log(progress, f"base model {model} (not PlayJev-0.8B)")
    _log(progress, "budget: fp16, LoRA on the language model, vision frozen, grad checkpointing, "
                   f"micro_batch 1, batch 8, game_eval_every {a.game_eval_every} "
                   f"(10 games ~5 min), max_steps {a.max_steps}")

    py = sys.executable
    if a.regen or not data.exists():
        cmd = [py, "-u", str(ROOT / "gen_data.py"),
               "--input", "image", "--policy", "expert",
               "--episodes", str(a.episodes), "--max_moves", str(a.gen_max_moves),
               "--eps", str(a.eps), str(a.eps), "--seed_base", str(a.seed_base),
               "--target_states", str(a.target_states),
               "--bucket_cap", *[str(c) for c in caps],
               "--out", str(data)]
        if paired is not None:
            cmd += ["--paired_text", str(paired)]
        _run(cmd, progress)
    else:
        _log(progress, f"reuse {data}")

    if not a.skip_overfit:
        subset, _va = training_split(load_records([str(data)]), a.overfit_limit, C.EVAL_SAMPLES)
        uniform = uniform_ce(subset)
        threshold = a.overfit_factor * uniform
        over = out / "overfit"
        _log(progress, f"overfit check: {len(subset)} states, uniform {uniform:.4f}, "
                       f"need last loss < {threshold:.4f} within {a.overfit_steps} steps")
        _run([py, "-u", str(ROOT / "train.py"),
              "--input", "image", "--data", str(data), "--out", str(over),
              "--model", model, "--dtype", "float16", "--label", a.label,
              "--limit", str(a.overfit_limit), "--max_steps", str(a.overfit_steps),
              "--micro_batch", "1", "--batch", "8", "--game_eval_every", "0",
              "--epochs", "1", "--device", a.device], progress)
        losses = [r["loss"] for r in events_from_log(over / "log.jsonl", "train")]
        last = tail_mean(losses, 20)
        if not overfit_ok(last, uniform, a.overfit_factor):
            info = {"ok": False, "last_loss": last, "uniform": uniform, "threshold": threshold,
                    "factor": a.overfit_factor, "steps": a.overfit_steps}
            (out / "overfit_failed.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
            _log(progress, f"ABORT overfit last_loss={last} threshold={threshold:.4f}")
            return 2
        _log(progress, f"overfit ok last_loss={last:.4f} < {threshold:.4f}")

    _log(progress, "main training")
    _run([py, "-u", str(ROOT / "train.py"),
          "--input", "image", "--data", str(data), "--out", str(out),
          "--model", model, "--dtype", "float16", "--label", a.label,
          "--max_steps", str(a.max_steps), "--epochs", "1",
          "--micro_batch", "1", "--batch", "8",
          "--game_eval_every", str(a.game_eval_every),
          "--game_eval_games", str(a.game_eval_games),
          "--game_eval_seed_base", str(a.game_eval_seed_base),
          "--game_eval_max_moves", str(a.game_eval_max_moves),
          "--kl_patience", str(a.kl_patience),
          "--score_patience", str(a.score_patience),
          "--score_drop", str(a.score_drop),
          "--device", a.device], progress)
    done_ev = events_from_log(out / "log.jsonl", "done")
    last_done = done_ev[-1] if done_ev else {}
    marker = {"ok": True, "stop": last_done.get("stop", "max_steps"),
              "step": last_done.get("step"), "best_mean_score": last_done.get("best_mean_score"),
              "model": model, "data": str(data)}
    done.write_text(json.dumps(marker, indent=1, ensure_ascii=False), encoding="utf-8")
    _log(progress, f"done {marker}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="베이스 Qwen3.5-0.8B 이미지 2048 학습")
    p.add_argument("--out", default=str(C.CKPT_DIR / "base_image"))
    p.add_argument("--data", default=str(C.DATA_DIR / "base_image.jsonl"))
    p.add_argument("--paired_text", default=str(C.DATA_DIR / "base_image_text.jsonl"))
    p.add_argument("--model", default=None, help="비우면 로컬 Qwen3.5-0.8B-Base 또는 허브 id. PlayJev-0.8B 는 거절")
    p.add_argument("--device", default=C.DEVICE)
    p.add_argument("--label", choices=("soft", "hard"), default="soft")
    p.add_argument("--episodes", type=int, default=C.BASE_EPISODES)
    p.add_argument("--seed_base", type=int, default=C.BASE_SEED_BASE)
    p.add_argument("--eps", type=float, default=C.BASE_EPS)
    p.add_argument("--gen_max_moves", type=int, default=C.BASE_GEN_MAX_MOVES)
    p.add_argument("--target_states", type=int, default=C.BASE_TARGET_STATES)
    p.add_argument("--bucket_cap", type=int, nargs="*", default=None,
                   help="비우면 버킷마다 BASE_BUCKET_CAP (기본 2000)")
    p.add_argument("--regen", action="store_true")
    p.add_argument("--skip_overfit", action="store_true")
    p.add_argument("--overfit_limit", type=int, default=C.BASE_OVERFIT_LIMIT)
    p.add_argument("--overfit_steps", type=int, default=C.BASE_OVERFIT_STEPS)
    p.add_argument("--overfit_factor", type=float, default=C.BASE_OVERFIT_FACTOR)
    p.add_argument("--max_steps", type=int, default=C.BASE_MAX_STEPS)
    p.add_argument("--game_eval_every", type=int, default=C.BASE_GAME_EVAL_EVERY)
    p.add_argument("--game_eval_games", type=int, default=C.BASE_EVAL_GAMES)
    p.add_argument("--game_eval_seed_base", type=int, default=C.BASE_EVAL_SEED_BASE)
    p.add_argument("--game_eval_max_moves", type=int, default=C.BASE_EVAL_MAX_MOVES)
    p.add_argument("--kl_patience", type=int, default=C.BASE_KL_PATIENCE)
    p.add_argument("--score_patience", type=int, default=C.BASE_SCORE_PATIENCE)
    p.add_argument("--score_drop", type=float, default=C.BASE_SCORE_DROP)
    p.add_argument("--force", action="store_true")
    sys.exit(main(p.parse_args()))
