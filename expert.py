"""전문가(교사) 정책: 깊이 2 expectimax(수 -> 스폰 기대값 -> 수 -> 휴리스틱), 빈칸이 적으면 한 단계 더.
루트 수 가치에 온도 softmax를 씌워 soft target을 만듦. 보드를 안 바꾸는 수는 확률 0."""
from __future__ import annotations

import math

import board as B
import config as C
from game2048 import ACTIONS

_MOVES = ACTIONS


def _best_reply_heur(b: int) -> float:
    best = 0.0
    for a in _MOVES:
        nb, _ = B.move(b, a)
        if nb != b:
            v = B.heuristic(nb)
            if v > best:
                best = v
    return best


def _chance(b: int, depth: int) -> float:
    cells = B.empty_shifts(b)
    if not cells:
        return 0.0
    tot = 0.0
    for s in cells:
        if depth <= 1:
            tot += 0.9 * _best_reply_heur(b | (1 << s)) + 0.1 * _best_reply_heur(b | (2 << s))
        else:
            tot += 0.9 * _player(b | (1 << s), depth) + 0.1 * _player(b | (2 << s), depth)
    return tot / len(cells)


def _player(b: int, depth: int) -> float:
    best = 0.0
    for a in _MOVES:
        nb, _ = B.move(b, a)
        if nb != b:
            v = _chance(nb, depth - 1)
            if v > best:
                best = v
    return best


class Expert:
    def __init__(self, depth: int = C.EXPERT_DEPTH, deep_empty: int = C.EXPERT_DEEP_EMPTY,
                 temperature: float = C.EXPERT_TEMPERATURE):
        self.depth, self.deep_empty, self.temperature = depth, deep_empty, temperature

    def values(self, b: int) -> dict[str, float]:
        depth = self.depth + 1 if len(B.empty_shifts(b)) <= self.deep_empty else self.depth
        out = {}
        for a in _MOVES:
            nb, _ = B.move(b, a)
            if nb != b:
                out[a] = _chance(nb, depth - 1)
        return out

    def probs(self, b: int) -> dict[str, float]:
        """합법 수에 대한 soft target. 합법 수가 없으면 빈 dict."""
        vals = self.values(b)
        if not vals:
            return {}
        alive = {k: v for k, v in vals.items() if v > 0.0} or vals  # 0 = 모든 스폰에서 끝나는 수
        vmax = max(alive.values())
        w = {k: math.exp((v - vmax) / self.temperature) for k, v in alive.items()}
        s = sum(w.values())
        return {k: (w.get(k, 0.0) / s) for k in vals}

    def act(self, b: int) -> str:
        p = self.probs(b)
        return max(p, key=p.get)
