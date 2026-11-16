"""2048 보드를 PlayJev 학습 분포에 맞게 한 장의 JPEG 로 그린다.

PlayJev 는 페이지 전체가 아니라 games/2048/pj_hook.js 의 canvas() 로 500×500 보드만 그리고,
games/_shared/pj_shim.js 의 frame() 이 긴 변을 448px 로 줄인 뒤 JPEG 품질 0.85 로 뽑는다.
점수/제목은 프레임에 없다. 한 수에 프레임 하나.

기본값은 PIL 이다. 브라우저를 띄우지 않는다.
--renderer playwright 는 같은 훅의 canvas()/frame() 을 헤드리스 Chromium 에서 부른다.
차이는 모듈 맨 아래 DIFFERENCES 에 적었다.
"""
from __future__ import annotations

import base64
import functools
import io
import os
import socket
import struct
import tempfile
import threading
import zlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import config as C

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
FONT_WOFF = REPO / "docs" / "games" / "2048" / "style" / "fonts" / "ClearSans-Bold-webfont.woff"
GAME_DIR = REPO / "docs" / "games" / "2048"
SHIM_JS = HERE / "vendor" / "pj_shim.js"
HOOK_JS = HERE / "vendor" / "pj_2048_hook.js"
FALLBACK_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

# pj_hook.js 와 같은 기하. CSS 의 106.25px 빈칸이 아니라 타일 박스 107px 을 빈칸에도 칠한다.
BOARD = 500
PAD = 15
STEP = 121.25
CELL = 107
_BILINEAR = getattr(getattr(Image, "Resampling", Image), "BILINEAR")

# style/main.css 데스크톱 타일. 2/4 글자색은 body 의 #776e65 를 상속한다.
_FG = (0x77, 0x6E, 0x65)
_LIGHT = (0xF9, 0xF6, 0xF2)
_TILE = {
    2: ((0xEE, 0xE4, 0xDA), _FG, 55),
    4: ((0xED, 0xE0, 0xC8), _FG, 55),
    8: ((0xF2, 0xB1, 0x79), _LIGHT, 55),
    16: ((0xF5, 0x95, 0x63), _LIGHT, 55),
    32: ((0xF6, 0x7C, 0x5F), _LIGHT, 55),
    64: ((0xF6, 0x5E, 0x3B), _LIGHT, 55),
    128: ((0xED, 0xCF, 0x72), _LIGHT, 45),
    256: ((0xED, 0xCC, 0x61), _LIGHT, 45),
    512: ((0xED, 0xC8, 0x50), _LIGHT, 45),
    1024: ((0xED, 0xC5, 0x3F), _LIGHT, 35),
    2048: ((0xED, 0xC2, 0x2E), _LIGHT, 35),
}
_SUPER = ((0x3C, 0x3A, 0x32), _LIGHT, 30)  # .tile-super
_BOARD = (0xBB, 0xAD, 0xA0)                 # .game-container
# .grid-cell 는 rgba(238, 228, 218, 0.35). 캔버스는 보드색 위에 이 색을 덮는다.
_EMPTY_SRC = (238, 228, 218)
_EMPTY_A = 0.35

DIFFERENCES = (
    "기본 렌더러는 PIL 이다. Playwright 는 --renderer playwright 일 때만 쓴다. "
    "둘 다 점수판 없는 500px 보드를 긴 변 448px, JPEG 품질 0.85 로 맞춘다. "
    "PIL 은 Clear Sans Bold(이 저장소 woff)를 FreeType 으로 그리고 칸 좌표를 정수 픽셀로 맞춘다. "
    "브라우저 캔버스는 121.25px 칸의 소수 경계를 안티앨리어싱하고 글자를 Chromium 이 래스터한다. "
    "모서리 둥글기와 그림자는 PlayJev 훅의 canvas() 도 그리지 않으므로 PIL 도 사각형만 그린다. "
    "JPEG 인코더는 Pillow 와 브라우저가 다르다. "
    "보드는 파이썬 엔진의 격자다. PlayJev 가 공개한 에피소드를 JS RNG 로 재현하지는 않는다."
)

_font_path: str | None = None
_font_warned = False
_fonts: dict[int, ImageFont.ImageFont] = {}


def woff_to_ttf(data: bytes) -> bytes:
    """WOFF1(zlib)을 sfnt 로 푼다. fontTools 없이 Clear Sans Bold 를 PIL 에 넘기려고."""
    if data[:4] != b"wOFF":
        raise ValueError("not a WOFF font")
    num_tables = struct.unpack(">H", data[12:14])[0]
    flavor = struct.unpack(">I", data[4:8])[0]
    entries = []
    off = 44
    for _ in range(num_tables):
        tag, offset, comp, orig, checksum = struct.unpack(">4sIIII", data[off:off + 20])
        blob = data[offset:offset + comp]
        if comp != orig:
            blob = zlib.decompress(blob)
        if len(blob) != orig:
            raise ValueError(f"woff table {tag!r} decompressed to {len(blob)}, expected {orig}")
        entries.append((tag, checksum, blob))
        off += 20
    entries.sort(key=lambda e: e[0])
    n = len(entries)
    max_power, log2 = 1, 0
    while max_power * 2 <= n:
        max_power *= 2
        log2 += 1
    out = struct.pack(">IHHHH", flavor, n, max_power * 16, log2, n * 16 - max_power * 16)
    table_offset = 12 + n * 16
    recs = b""
    blobs = []
    for tag, checksum, blob in entries:
        pad = (4 - (len(blob) % 4)) % 4
        recs += struct.pack(">4sIII", tag, checksum, table_offset, len(blob))
        blobs.append(blob + b"\x00" * pad)
        table_offset += len(blob) + pad
    return out + recs + b"".join(blobs)


def clear_sans_path() -> str | None:
    """프로세스 동안 한 번만 woff 를 풀어 /tmp 에 둔다. 없으면 None (호출자가 대체 폰트를 씀)."""
    global _font_path, _font_warned
    if _font_path is not None:
        return _font_path or None
    if FONT_WOFF.exists():
        fd, path = tempfile.mkstemp(prefix="clearsans-", suffix=".ttf")
        os.write(fd, woff_to_ttf(FONT_WOFF.read_bytes()))
        os.close(fd)
        _font_path = path
        return path
    if not _font_warned:
        print(f"[frame] {FONT_WOFF} 가 없어 대체 폰트를 씁니다", flush=True)
        _font_warned = True
    _font_path = ""
    return None


def _font(size: int) -> ImageFont.ImageFont:
    if size not in _fonts:
        path = clear_sans_path()
        if path is None:
            if FALLBACK_FONT.exists():
                _fonts[size] = ImageFont.truetype(str(FALLBACK_FONT), size)
            else:
                _fonts[size] = ImageFont.load_default()
        else:
            _fonts[size] = ImageFont.truetype(path, size)
    return _fonts[size]


def _blend(bg: tuple[int, int, int], fg: tuple[int, int, int], a: float) -> tuple[int, int, int]:
    return tuple(int(round(fg[i] * a + bg[i] * (1 - a))) for i in range(3))


EMPTY = _blend(_BOARD, _EMPTY_SRC, _EMPTY_A)


def _fill(draw: ImageDraw.ImageDraw, x: float, y: float, w: float, h: float, color) -> None:
    """canvas fillRect 와 같이 [x, x+w) × [y, y+h). 소수 좌표는 내림한다 (안티앨리어싱 없음)."""
    x0, y0 = int(x), int(y)  # x, y are non-negative
    x1, y1 = int(x + w), int(y + h)
    if x1 > x0 and y1 > y0:
        draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=color)


def tile_style(value: int) -> tuple[tuple[int, int, int], tuple[int, int, int], int]:
    return _TILE.get(value, _SUPER)


def draw_board(grid) -> Image.Image:
    """500×500 RGB. PlayJev canvas() 와 같은 배치. JPEG/축소 전."""
    im = Image.new("RGB", (BOARD, BOARD), _BOARD)
    draw = ImageDraw.Draw(im)
    for y in range(4):
        for x in range(4):
            px, py = PAD + x * STEP, PAD + y * STEP
            v = int(grid[y][x] or 0)
            if not v:
                _fill(draw, px, py, CELL, CELL, EMPTY)
                continue
            bg, fg, size = tile_style(v)
            _fill(draw, px, py, CELL, CELL, bg)
            # 훅: textBaseline middle, (px + CELL/2, py + CELL/2 + 2)
            draw.text((px + CELL / 2, py + CELL / 2 + 2), str(v), fill=fg, font=_font(size), anchor="mm")
    return im


def scale_long_side(im: Image.Image, long_side: int = C.FRAME_LONG_SIDE) -> Image.Image:
    """긴 변을 long_side 로. 비율 유지, bilinear. pj_shim.js frame() / playjev.env._resize_jpeg 와 같은 식."""
    w, h = im.size
    m = max(w, h)
    if m == long_side:
        return im
    s = long_side / m
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    return im.resize((nw, nh), _BILINEAR)


def jpeg_roundtrip(im: Image.Image, quality: int = C.JPEG_QUALITY) -> Image.Image:
    """한 번 압축했다가 연다. PlayJev 는 JPEG 바이트를 디코드해서 모델에 넣는다."""
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def as_model_image(im: Image.Image, *, already_jpeg: bool = False) -> Image.Image:
    im = im.convert("RGB")
    if max(im.size) != C.FRAME_LONG_SIDE:
        im = scale_long_side(im, C.FRAME_LONG_SIDE)
        already_jpeg = False
    if already_jpeg:
        return im
    return jpeg_roundtrip(im, C.JPEG_QUALITY)


def grid_from_state(state: str) -> list[list[int]]:
    """텍스트 상태창의 마지막 4줄. 이미지 학습이 텍스트 jsonl 을 그대로 읽을 수 있게."""
    rows = []
    for line in state.splitlines():
        parts = line.split()
        if len(parts) == 4 and all(p == "." or p.isdigit() for p in parts):
            rows.append([0 if p == "." else int(p) for p in parts])
    if len(rows) != 4:
        raise ValueError("state has no 4x4 board")
    return rows


def render_frame(grid, backend: str = "pil") -> Image.Image:
    """모델에 넣을 RGB. backend='playwright' 는 호출마다 브라우저를 띄운다."""
    if backend == "pil":
        return as_model_image(draw_board(grid))
    if backend == "playwright":
        with FrameRenderer("playwright") as r:
            return r.render(grid)
    raise ValueError(f"renderer must be pil or playwright, got {backend}")


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


class _Server:
    def __init__(self, directory: Path):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        handler = functools.partial(_Quiet, directory=str(directory))
        self.httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{port}"

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class _Playwright2048:
    """한 페이지를 유지하고 setGrid → pj.frame() 만 반복한다."""

    def open(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise RuntimeError(
                "playwright 가 없습니다. pip install playwright==1.65.2 && python -m playwright install chromium"
            ) from e
        if not SHIM_JS.exists() or not HOOK_JS.exists():
            raise RuntimeError(f"vendored shim/hook missing: {SHIM_JS}, {HOOK_JS}")
        self.server = _Server(GAME_DIR)
        self._pw = sync_playwright().start()
        try:
            self.browser = self._pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-gpu", "--mute-audio", "--disable-dev-shm-usage"])
        except Exception as e:
            self.server.close()
            self._pw.stop()
            raise RuntimeError(
                "Chromium 을 띄우지 못했습니다. python -m playwright install chromium"
            ) from e
        self.page = self.browser.new_page(viewport={"width": 700, "height": 900})
        self.page.add_init_script(SHIM_JS.read_text(encoding="utf-8"))
        self.page.add_init_script(HOOK_JS.read_text(encoding="utf-8"))
        self.page.goto(self.server.base_url + "/index.html", wait_until="load")
        self.page.evaluate("() => pj.start(1)")

    def render(self, grid) -> Image.Image:
        # pj.frame() 은 이미 448 JPEG data URL 이다. 다시 압축하지 않는다.
        url = self.page.evaluate("(g) => { pj.hook.setGrid(g); return pj.frame(); }", grid)
        if not url:
            raise RuntimeError("pj.frame() returned empty")
        raw = base64.b64decode(url.split(",", 1)[1])
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        return as_model_image(im, already_jpeg=max(im.size) == C.FRAME_LONG_SIDE)

    def close(self):
        browser = getattr(self, "browser", None)
        if browser is not None:
            browser.close()
        pw = getattr(self, "_pw", None)
        if pw is not None:
            pw.stop()
        server = getattr(self, "server", None)
        if server is not None:
            server.close()


class FrameRenderer:
    """PIL 은 상태가 없다. Playwright 는 open/close 로 페이지를 재사용한다."""

    def __init__(self, backend: str = C.IMAGE_RENDERER):
        if backend not in ("pil", "playwright"):
            raise ValueError(f"renderer must be pil or playwright, got {backend}")
        self.backend = backend
        self._pw = None

    def open(self):
        if self.backend == "playwright" and self._pw is None:
            self._pw = _Playwright2048()
            self._pw.open()
        return self

    def close(self):
        if self._pw is not None:
            self._pw.close()
            self._pw = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *exc):
        self.close()

    def render(self, grid) -> Image.Image:
        if self.backend == "pil":
            return as_model_image(draw_board(grid))
        if self._pw is None:
            self.open()
        return self._pw.render(grid)


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    backend = "pil"
    if args and args[0] in ("pil", "playwright"):
        backend = args.pop(0)
    dest = Path(args[0] if args else "frame_smoke.jpg")
    demo = [[2, 4, 8, 16], [32, 64, 128, 256], [512, 1024, 2048, 4096], [0, 0, 0, 2]]
    image = render_frame(demo, backend)
    image.save(dest, quality=C.JPEG_QUALITY)
    print(f"{dest} {image.size} {image.mode} backend={backend}")
