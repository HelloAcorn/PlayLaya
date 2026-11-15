"""순수 파이썬 2048 환경과 텍스트 상태창 렌더링. 시드가 같으면 같은 수열에서 같은 게임이 나옴."""
from __future__ import annotations

import random

import board as B

ACTIONS = ("up", "down", "left", "right")


class Game2048:
    def __init__(self, seed: int):
        self.seed = seed
        self.rng = random.Random(seed)
        self.board = 0
        self.score = 0
        self.moves = 0
        self._spawn(); self._spawn()

    def _spawn(self) -> None:
        cells = B.empty_shifts(self.board)
        if not cells:
            return
        s = self.rng.choice(cells)
        self.board |= (2 if self.rng.random() < 0.1 else 1) << s  # 4가 10%, 2가 90%

    def legal(self) -> dict[str, tuple[int, int]]:
        """보드를 바꾸는 수만: action -> (새 보드, 얻는 점수)."""
        out = {}
        for a in ACTIONS:
            nb, g = B.move(self.board, a)
            if nb != self.board:
                out[a] = (nb, g)
        return out

    def done(self) -> bool:
        return not self.legal()

    def step(self, action: str) -> dict:
        legal = self.legal()
        if action not in legal:
            raise ValueError(f"illegal move {action}")
        nb, g = legal[action]
        self.board = nb; self.score += g; self.moves += 1
        self._spawn()
        return {"gain": g, "score": self.score, "max_tile": B.max_tile(self.board), "done": self.done()}

    def max_tile(self) -> int:
        return B.max_tile(self.board)

    def empty(self) -> int:
        return len(B.empty_shifts(self.board))


def render_state(g: Game2048) -> str:
    """상태창: 모델 입력의 전부. 학습과 추론에서 글자 하나까지 같아야 함."""
    rows = [" ".join(f"{v if v else '.':>5}" for v in row) for row in B.to_grid(g.board)]
    return (f"Move: {g.moves} | Score: {g.score} | Empty: {g.empty()} | Max tile: {g.max_tile()}\n"
            "Board (4x4, . = empty):\n" + "\n".join(rows))
