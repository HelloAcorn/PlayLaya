"""2048 비트보드: 64비트 정수 하나에 16칸, 칸마다 4비트 지수(0=빈칸, k=2**k).
grid[r][c]는 4*(4r+c) 비트에 있음. 행 이동은 65536 크기 테이블 조회, 위/아래는 전치 후 좌/우.
(PlayJev playjev/teachers/2048.py의 비트보드/휴리스틱을 단순화해 가져옴, Apache-2.0)"""
from __future__ import annotations

ROW_MASK = 0xFFFF
EMPTY_W, MERGES_W, MONO_W, MONO_P, SUM_W, SUM_P, LOST = 270.0, 700.0, 47.0, 4.0, 11.0, 3.5, 200000.0


def _row_cells(row: int) -> list[int]:
    return [(row >> 0) & 0xF, (row >> 4) & 0xF, (row >> 8) & 0xF, (row >> 12) & 0xF]


def _pack(cells: list[int]) -> int:
    return cells[0] | (cells[1] << 4) | (cells[2] << 8) | (cells[3] << 12)


def _slide_left(cells: list[int]) -> tuple[list[int], int]:
    out = [c for c in cells if c]
    res, gain, i = [], 0, 0
    while i < len(out):
        if i + 1 < len(out) and out[i] == out[i + 1]:
            v = min(out[i] + 1, 15)
            res.append(v); gain += 1 << v; i += 2
        else:
            res.append(out[i]); i += 1
    return res + [0] * (4 - len(res)), gain


def _heur(line: list[int]) -> float:
    s = 0.0; empty = 0; merges = 0; prev = 0; counter = 0
    for rank in line:
        s += rank ** SUM_P
        if rank == 0:
            empty += 1
        else:
            if prev == rank:
                counter += 1
            elif counter > 0:
                merges += 1 + counter; counter = 0
            prev = rank
    if counter > 0:
        merges += 1 + counter
    mono_l = mono_r = 0.0
    for i in range(1, 4):
        a, b = line[i - 1], line[i]
        if a > b:
            mono_l += a ** MONO_P - b ** MONO_P
        else:
            mono_r += b ** MONO_P - a ** MONO_P
    return LOST + EMPTY_W * empty + MERGES_W * merges - MONO_W * min(mono_l, mono_r) - SUM_W * s


def _reverse(row: int) -> int:
    return ((row >> 12) | ((row >> 4) & 0x00F0) | ((row << 4) & 0x0F00) | ((row << 12) & 0xF000)) & ROW_MASK


def _build():
    left = [0] * 65536; right = [0] * 65536; gl = [0] * 65536; gr = [0] * 65536; heur = [0.0] * 65536
    for row in range(65536):
        cells = _row_cells(row)
        moved, g = _slide_left(cells)
        left[row] = _pack(moved); gl[row] = g; heur[row] = _heur(cells)
    for row in range(65536):
        rv = _reverse(row)
        right[row] = _reverse(left[rv]); gr[row] = gl[rv]
    return left, right, gl, gr, heur


LEFT, RIGHT, GAIN_L, GAIN_R, HEUR = _build()


def transpose(x: int) -> int:
    a1 = x & 0xF0F00F0FF0F00F0F
    a2 = x & 0x0000F0F00000F0F0
    a3 = x & 0x0F0F00000F0F0000
    a = a1 | (a2 << 12) | (a3 >> 12)
    b1 = a & 0xFF00FF0000FF00FF
    b2 = a & 0x00FF00FF00000000
    b3 = a & 0x00000000FF00FF00
    return b1 | (b2 >> 24) | (b3 << 24)


def _rows(b: int):
    return b & 0xFFFF, (b >> 16) & 0xFFFF, (b >> 32) & 0xFFFF, b >> 48


def _apply(b: int, T, G) -> tuple[int, int]:
    r0, r1, r2, r3 = _rows(b)
    return (T[r0] | (T[r1] << 16) | (T[r2] << 32) | (T[r3] << 48)), G[r0] + G[r1] + G[r2] + G[r3]


def move(b: int, action: str) -> tuple[int, int]:
    """(새 보드, 이번 수로 얻은 점수). 보드가 그대로면 그 수는 불법."""
    if action == "left":
        return _apply(b, LEFT, GAIN_L)
    if action == "right":
        return _apply(b, RIGHT, GAIN_R)
    t = transpose(b)
    if action == "up":
        nb, g = _apply(t, LEFT, GAIN_L)
    elif action == "down":
        nb, g = _apply(t, RIGHT, GAIN_R)
    else:
        raise ValueError(action)
    return transpose(nb), g


def heuristic(b: int, H=HEUR) -> float:
    t = transpose(b)
    r0, r1, r2, r3 = _rows(b); c0, c1, c2, c3 = _rows(t)
    return H[r0] + H[r1] + H[r2] + H[r3] + H[c0] + H[c1] + H[c2] + H[c3]


def empty_shifts(b: int) -> list[int]:
    return [s for s in range(0, 64, 4) if not (b >> s) & 0xF]


def to_grid(b: int) -> list[list[int]]:
    return [[(1 << e) if (e := (b >> (4 * (4 * r + c))) & 0xF) else 0 for c in range(4)] for r in range(4)]


def from_grid(grid) -> int:
    b = 0; shift = 0
    for row in grid:
        for v in row:
            if v:
                b |= (v.bit_length() - 1) << shift
            shift += 4
    return b


def max_tile(b: int) -> int:
    return 1 << max((b >> s) & 0xF for s in range(0, 64, 4))
