"""SFT 데이터 생성. 전문가가 직접 두거나(--policy expert), 학습한 모델이 두고 전문가가 라벨만 다는 DAgger(--policy model).
한 줄 = 한 상태. prompt/completion(chat 형식)과 soft target(probs)을 함께 저장.

  python gen_data.py --episodes 40 --out data/clone.jsonl
  python gen_data.py --episodes 20 --policy model --adapter ckpt/run1/final --out data/dagger1.jsonl
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import board as B
import config as C
from expert import Expert
from game2048 import ACTIONS, Game2048, render_state
from prompt import SYSTEM_PROMPT, user_text


def _flag(*flags: str) -> bool:
    import sys
    argv = sys.argv[1:]
    return any(s == f or s.startswith(f + "=") for f in flags for s in argv)


def record(ep: int, seed: int, g: Game2048, probs: dict, state: str) -> dict:
    legal = [a for a in ACTIONS if a in probs]
    best = max(probs, key=probs.get)
    return {
        "episode": ep, "seed": seed, "t": g.moves, "state": state, "legal": legal,
        "probs": {a: round(probs[a], 6) for a in legal}, "action": best,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": user_text(state, legal)}],
        "completion": "ABCD"[legal.index(best)],  # 고정 순서(up,down,left,right 중 합법 수) 기준 글자
    }


def main(a):
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    ex = Expert(); rng = random.Random(a.seed_base + 12345)
    pol = None
    image_pol = None
    image_messages = None
    # 텍스트(--input text)는 아래 분기를 타지 않는다. 기록 필드와 두는 수가 이전과 같다.
    if a.input == "image":
        from playjev_prompt import image_messages as image_messages
        if not _flag("--model"):
            if a.adapter and (Path(a.adapter) / "adapter_config.json").exists():
                a.model = json.loads((Path(a.adapter) / "adapter_config.json").read_text(encoding="utf-8"))["base_model"]
            elif Path(C.MODEL_PATH).exists():
                a.model = C.MODEL_PATH
            else:
                a.model = C.IMAGE_BASE_MODEL
        if a.policy == "model":
            from image_policy import ImagePolicy
            image_pol = ImagePolicy(a.model, a.adapter, device=a.device, dtype=a.dtype or C.IMAGE_DTYPE,
                                    renderer=a.renderer)
    elif a.policy == "model":
        from policy import LMPolicy
        pol = LMPolicy(a.model, a.adapter)
    n = 0; t0 = time.time()
    try:
        with open(out, "a" if a.append else "w", encoding="utf-8") as f:
            for ep in range(a.episodes):
                seed = a.seed_base + ep
                g = Game2048(seed)
                eps = rng.uniform(*a.eps)
                while not g.done() and g.moves < a.max_moves:
                    state = render_state(g)
                    probs = ex.probs(g.board)
                    rec = record(ep, seed, g, probs, state)
                    legal = rec["legal"]
                    if a.input == "image":
                        # 라벨(probs/action/state/legal)은 텍스트 기록과 같다. 프레임은 학습 때 grid 로 다시 그린다.
                        rec["input"] = "image"
                        rec["grid"] = B.to_grid(g.board)
                        rec["messages"] = image_messages(legal)
                    if rng.random() < eps:
                        played = rng.choice(legal)
                    elif image_pol is not None:
                        played = image_pol.choose(B.to_grid(g.board), legal)
                    elif pol is not None:
                        p = pol.probs([state], [legal])[0]
                        played = legal[max(range(len(legal)), key=p.__getitem__)]
                    else:
                        played = rec["action"]
                    res = g.step(played)
                    rec["played"] = played
                    rec["result"] = res  # 둔 수의 결과: 얻은 점수, 누적 점수, 최대 타일, 종료 여부
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n"); n += 1
                print(f"[gen] ep {ep} seed {seed} eps {eps:.2f} moves {g.moves} score {g.score} max {g.max_tile()} "
                      f"| total {n} records {time.time() - t0:.0f}s", flush=True)
    finally:
        if image_pol is not None:
            image_pol.close()
    print(f"[gen] wrote {n} records to {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--episodes", type=int, default=C.TRAIN_EPISODES)
    p.add_argument("--out", default=str(C.DATA_DIR / "clone.jsonl"))
    p.add_argument("--seed_base", type=int, default=C.TRAIN_SEED_BASE)
    p.add_argument("--eps", type=float, nargs=2, default=C.EPS_RANDOM, help="에피소드별 무작위 수 비율 범위")
    p.add_argument("--max_moves", type=int, default=C.MAX_MOVES)
    p.add_argument("--policy", choices=("expert", "model"), default="expert")
    p.add_argument("--model", default=C.MODEL_PATH)
    p.add_argument("--adapter", default=None)
    p.add_argument("--append", action="store_true")
    p.add_argument("--input", choices=("text", "image"), default="text")
    p.add_argument("--renderer", choices=("pil", "playwright"), default=C.IMAGE_RENDERER,
                   help="image DAgger 가 프레임을 그리는 방법. 전문가 생성은 보드만 저장하고 학습 때 다시 그린다")
    p.add_argument("--device", default=C.DEVICE)
    p.add_argument("--dtype", default=None, help="image 모델 dtype. 기본 float16 (Turing)")
    main(p.parse_args())
