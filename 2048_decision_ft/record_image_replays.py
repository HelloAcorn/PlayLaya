"""이미지 모델이 둔 2048 을 페이지용 JSON 한 파일로 남긴다.

모델은 이미지 평가와 같이 올린다. `eval_image.apply_eval_defaults` 가
어댑터의 adapter_config.json 에서 base_model 을 읽고, dtype 기본값은 float16 이다.
수는 `ImagePolicy.probs` 의 argmax. 살아 있는 판을 같이 두고, 프레임은 `--batch`
장씩 넣는다 (평가의 model_probs 와 같은 자르기. 8GB 기본값은 1).

시드를 생략하면 실행마다 새로 뽑아 JSON 에 적는다. 학습 평가 시드 100000-100009 는
쓰지 않는다. `--seeds` 를 주면 그 시드만 둔다.

  python -u record_image_replays.py --adapter ckpt\\base_image\\best --games 10 --out ..\\docs\\games\\2048\\replays\\my_model.json

GPU 없이 형식만 보려면 `--stub --out` 으로 다른 경로를 준다.
`--stub` 은 기본 출력(my_model.json)을 거절한다. 그 출력은 파인튜닝한 모델의 판이 아니다.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import board as B
import config as C
from game2048 import ACTIONS, Game2048

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO / "docs" / "games" / "2048" / "replays" / "my_model.json"
EVAL_SEEDS = frozenset(range(C.BASE_EVAL_SEED_BASE, C.BASE_EVAL_SEED_BASE + C.BASE_EVAL_GAMES))
_STUB_W = {"up": 0.5, "left": 0.3, "down": 0.15, "right": 0.05}


def flat(grid) -> list[int]:
    return [int(v) for row in grid for v in row]


def dir_probs(legal: list[str], probs: list[float]) -> list[float]:
    """ACTIONS 순서. 불법 수는 0. 합법 수 확률은 소수 넷째 자리."""
    vec = [0.0] * len(ACTIONS)
    index = {a: i for i, a in enumerate(ACTIONS)}
    for action, p in zip(legal, probs):
        vec[index[action]] = round(float(p), 4)
    return vec


def choose_seeds(n: int, rng: random.Random) -> list[int]:
    if n < 1:
        raise SystemExit("판 수는 1 이상이어야 합니다.")
    seeds = []
    while len(seeds) < n:
        s = rng.randrange(1, 2**31 - 1)
        if s in EVAL_SEEDS or s in seeds:
            continue
        seeds.append(s)
    return seeds


def check_seeds(seeds: list[int]) -> list[int]:
    if not seeds:
        raise SystemExit("시드가 비어 있습니다.")
    bad = [s for s in seeds if s in EVAL_SEEDS]
    if bad:
        raise SystemExit(f"평가 시드 {bad} 는 녹화에 쓰지 않습니다 (100000-100009).")
    if len(set(seeds)) != len(seeds):
        raise SystemExit("시드가 겹칩니다.")
    return list(seeds)


def stub_probs(_live, legal: list[list[str]]) -> list[list[float]]:
    """GPU 없는 형식 확인용. 위, 왼쪽, 아래, 오른쪽 순으로 가중. 모델이 아니다."""
    out = []
    for leg in legal:
        raw = [_STUB_W[a] for a in leg]
        z = sum(raw)
        out.append([w / z for w in raw])
    return out


def record_games(probs_fn, seeds: list[int], max_moves: int, batch: int, progress=None) -> list[dict]:
    """probs_fn(live, legal) -> 판마다 합법 수 확률. legal 은 ACTIONS 에서 거른 순서.

    살아 있는 판을 한 수씩 같이 두고, probs_fn 에는 batch 판씩 넘긴다.
    """
    batch = max(1, int(batch))
    games = [Game2048(s) for s in seeds]
    starts = [flat(B.to_grid(g.board)) for g in games]
    log = {g.seed: [] for g in games}
    ply = 0
    while True:
        live = [g for g in games if not g.done() and g.moves < max_moves]
        if not live:
            break
        legal = [[a for a in ACTIONS if a in g.legal()] for g in live]
        ps: list = []
        for s in range(0, len(live), batch):
            chunk_legal = legal[s:s + batch]
            chunk_p = probs_fn(live[s:s + batch], chunk_legal)
            if len(chunk_p) != len(chunk_legal):
                raise ValueError("policy returned a different number of rows than games")
            ps.extend(chunk_p)
        for g, leg, p in zip(live, legal, ps):
            if len(p) != len(leg):
                raise ValueError("probs length does not match legal moves")
            move = leg[max(range(len(leg)), key=p.__getitem__)]
            g.step(move)
            log[g.seed].append({
                "m": move,
                "s": int(g.score),
                "g": flat(B.to_grid(g.board)),
                "p": dir_probs(leg, p),
            })
        ply += 1
        if progress and (ply == 1 or ply % 25 == 0):
            progress(f"[replay] ply {ply} live {len(live)}/{len(games)}")
    return [{
        "seed": g.seed,
        "score": int(g.score),
        "max_tile": int(g.max_tile()),
        "done": bool(g.done()),
        "start": start,
        "moves": log[g.seed],
    } for g, start in zip(games, starts)]


def build_payload(games: list[dict], model: str | None, adapter: str | None, fixture: bool = False) -> dict:
    payload = {"model": model, "adapter": adapter, "dirs": list(ACTIONS), "games": games}
    if fixture:
        payload["fixture"] = True
    return payload


def write_replay(path: Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def image_probs(policy):
    def fn(live, legal):
        frames = [policy.frames.render(B.to_grid(g.board)) for g in live]
        return policy.probs(frames, legal)
    return fn


def resolve_model(a):
    """평가와 같은 베이스 모델. --games 를 생략하면 녹화 기본값 10판 (평가 기본 100판이 아님)."""
    from eval_image import apply_eval_defaults, flag_passed

    games_set = flag_passed("--games")
    apply_eval_defaults(a)
    if not games_set:
        a.games = 10
    return a


def main(a) -> None:
    out = Path(a.out)
    if a.stub:
        if not flag_passed_out():
            raise SystemExit("--stub 은 기본 출력(docs/games/2048/replays/my_model.json)을 덮어쓰지 않습니다. "
                             "--out 으로 다른 경로를 지정하세요.")
        seeds = check_seeds(a.seeds) if a.seeds else choose_seeds(a.games, random.SystemRandom())
        games = record_games(stub_probs, seeds, a.max_moves, a.batch or C.IMAGE_EVAL_BATCH)
        payload = build_payload(games, "stub", None, fixture=True)
    else:
        if not (Path(a.adapter) / "adapter_config.json").is_file():
            raise SystemExit(f"어댑터가 없습니다: {a.adapter}\n"
                             "ckpt\\base_image\\best\\adapter_config.json 이 있는 폴더를 --adapter 로 주세요.")
        from image_policy import ImagePolicy

        resolve_model(a)
        seeds = check_seeds(a.seeds) if a.seeds else choose_seeds(a.games, random.SystemRandom())
        policy = ImagePolicy(a.model, a.adapter, device=a.device, dtype=a.dtype, renderer=a.renderer)
        try:
            games = record_games(image_probs(policy), seeds, a.max_moves, a.batch,
                                 progress=lambda line: print(line, flush=True))
        finally:
            policy.close()
        payload = build_payload(games, a.model, a.adapter)
    write_replay(out, payload)
    print(json.dumps(
        [{"seed": g["seed"], "score": g["score"], "max_tile": g["max_tile"], "moves": len(g["moves"])}
         for g in payload["games"]],
        ensure_ascii=False))
    print(out)


def flag_passed_out() -> bool:
    argv = sys.argv[1:]
    return any(s == "--out" or s.startswith("--out=") for s in argv)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="이미지 2048 모델을 두고 페이지용 JSON 으로 저장")
    p.add_argument("--adapter", default=str(C.CKPT_DIR / "base_image" / "best"),
                   help="LoRA 폴더. 기본 ckpt/base_image/best")
    p.add_argument("--model", default=None, help="비우면 어댑터 adapter_config.json 의 base_model (평가와 같음)")
    p.add_argument("--games", type=int, default=10)
    p.add_argument("--seeds", nargs="*", type=int, default=None,
                   help="주면 이 시드만 둔다. 비우면 매번 새로 뽑고, 100000-100009 는 제외")
    p.add_argument("--out", default=str(DEFAULT_OUT))
    p.add_argument("--batch", type=int, default=C.IMAGE_EVAL_BATCH,
                   help="한 번에 넣는 판 수. 8GB 평가는 1")
    p.add_argument("--max_moves", type=int, default=C.BASE_EVAL_MAX_MOVES)
    p.add_argument("--dtype", default=None, help="기본 float16")
    p.add_argument("--device", default=C.DEVICE)
    p.add_argument("--renderer", choices=("pil", "playwright"), default=C.IMAGE_RENDERER)
    p.add_argument("--stub", action="store_true",
                   help="모델을 올리지 않고 형식만 쓴다. 기본 출력 경로는 거절")
    main(p.parse_args())
