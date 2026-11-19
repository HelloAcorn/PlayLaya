"""CPU 스모크. 프레임을 그리고, PlayJev plain 프롬프트를 고정하고, 텍스트 경로가 그대로인지 확인한다.

  python test_image.py
프로세서(transformers)가 있고 허브에 닿으면 Qwen3.5-0.8B-Base 프로세서로 한 배치도 만든다.
GPU 학습은 하지 않는다.
"""
from __future__ import annotations

import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import board as B  # noqa: E402
import config as C  # noqa: E402
from evaluate import play  # noqa: E402
from frame import (  # noqa: E402
    DIFFERENCES, EMPTY, draw_board, grid_from_state, render_frame, scale_long_side,
)
from game2048 import Game2048, render_state  # noqa: E402
from gen_data import record  # noqa: E402
from PIL import Image  # noqa: E402
from playjev_prompt import (  # noqa: E402
    ACTION_DESC, FRAME_PLACEHOLDER, SYSTEM_PROMPT, build_image_prompt, image_messages,
)
from prompt import OPTION_DESC, SYSTEM_PROMPT as TEXT_SYSTEM, build_prompt  # noqa: E402

TILE2 = (0xEE, 0xE4, 0xDA)
TEXT_PROMPT = (
    "Apply the question to the state. Choose exactly one of the listed options. "
    "Respond with only its uppercase letter, with no explanation or reasoning.\n"
    "\n"
    "<state>\n"
    "S\n"
    "</state>\n"
    "\n"
    "Question: Which move should the player make next?\n"
    "\n"
    "Options:\n"
    "A. up: slide all tiles up\n"
    "\n"
    "Answer with one letter: A.\n"
    "Answer:"
)
IMAGE_PROMPT = (
    "Apply the question to the state. Choose exactly one of the listed options. "
    "Respond with only its uppercase letter, with no explanation or reasoning.\n"
    "\n"
    "<state>\n"
    "<|vision_start|><|image_pad|><|vision_end|>\n"
    "</state>\n"
    "\n"
    "Question: Which move should the player make next?\n"
    "\n"
    "Options:\n"
    "A. up: slide every tile as far up as it can go and merge equal tiles that meet\n"
    "B. down: slide every tile as far down as it can go and merge equal tiles that meet\n"
    "\n"
    "Answer with one letter: A, B.\n"
    "Answer:"
)


class ImagePathTest(unittest.TestCase):
    def test_constants_match_playjev_frame(self):
        self.assertEqual(C.FRAME_LONG_SIDE, 448)
        self.assertEqual(C.JPEG_QUALITY, 85)
        self.assertIn("PIL", DIFFERENCES)

    def test_board_colors_and_glyph(self):
        im = draw_board([[2, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
        self.assertEqual(im.size, (500, 500))
        self.assertEqual(im.getpixel((20, 20)), TILE2)          # 타일 2, 글자에서 먼 모서리
        self.assertEqual(im.getpixel((140, 20)), EMPTY)         # 빈칸, 보드색 위에 0.35 합성
        self.assertEqual(EMPTY, (205, 192, 180))
        ink = 0
        for y in range(40, 100):
            for x in range(40, 100):
                if im.getpixel((x, y)) != TILE2:
                    ink += 1
        self.assertGreater(ink, 30)  # Clear Sans "2"

    def test_model_frame_is_448_jpeg_roundtrip(self):
        a = render_frame([[2, 0, 0, 4], [0, 8, 0, 0], [0, 0, 16, 0], [0, 0, 0, 0]])
        b = render_frame([[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [2, 0, 0, 0]])
        self.assertEqual(a.size, (448, 448))
        self.assertEqual(a.mode, "RGB")
        self.assertNotEqual(a.tobytes(), b.tobytes())
        wide = scale_long_side(Image.new("RGB", (100, 40), (1, 2, 3)), 448)
        self.assertEqual(wide.size, (448, round(40 * 448 / 100)))
        self.assertEqual(max(wide.size), 448)

    def test_grid_roundtrip_from_text_state(self):
        g = Game2048(0)
        self.assertEqual(grid_from_state(render_state(g)), B.to_grid(g.board))

    def test_image_prompt_is_playjev_plain(self):
        self.assertEqual(build_image_prompt(["up", "down"]), IMAGE_PROMPT)
        self.assertIn(FRAME_PLACEHOLDER, IMAGE_PROMPT)
        self.assertTrue(IMAGE_PROMPT.endswith("Answer:"))
        self.assertNotIn("Move:", IMAGE_PROMPT)
        right = build_image_prompt(["right", "up"])
        self.assertIn("A. right:", right)
        self.assertIn("B. up:", right)
        self.assertNotIn("\nC.", right)
        user = image_messages(["up", "down"])[1]["content"]
        self.assertTrue(IMAGE_PROMPT.startswith(SYSTEM_PROMPT))
        self.assertIn(user, IMAGE_PROMPT)
        self.assertNotIn("\nAnswer:", user)

    def test_text_prompt_unchanged(self):
        self.assertEqual(build_prompt("S", ["up"]), TEXT_PROMPT)
        self.assertEqual(TEXT_SYSTEM, SYSTEM_PROMPT)
        self.assertNotEqual(OPTION_DESC["up"], ACTION_DESC["up"])
        g = Game2048(1)
        rec = record(0, 1, g, {"up": 1.0}, "STATE")
        self.assertNotIn("grid", rec)
        self.assertNotIn("input", rec)
        self.assertEqual(rec["completion"], "A")
        self.assertEqual(rec["messages"][1]["content"].splitlines()[0], "<state>")

    def test_text_eval_summary_keys(self):
        r = play("random", [100000], max_moves=4)
        self.assertEqual(r["policy"], "random")
        for key in ("mean_score", "mean_moves", "mean_max_tile", "best_tile", "reach_256", "reach_2048"):
            self.assertIn(key, r)
        self.assertNotIn("max_tile_distribution", r)
        detailed = play("random", [100000], max_moves=4, detail=True)
        self.assertIn("max_tile_distribution", detailed)
        self.assertEqual(sum(detailed["max_tile_distribution"].values()), 1)

    def test_option_shuffle_is_stable(self):
        def order(i):
            opts = ["up", "down", "left", "right"]
            random.Random(f"0:0:{i}").shuffle(opts)
            return tuple(opts)
        self.assertEqual(order(3), order(3))
        self.assertGreater(len({order(i) for i in range(12)}), 1)

    def test_image_labels_match_text_labels(self):
        with tempfile.TemporaryDirectory() as d:
            text = str(Path(d) / "t.jsonl")
            image = str(Path(d) / "i.jsonl")
            base = [sys.executable, str(ROOT / "gen_data.py"), "--episodes", "1", "--max_moves", "6", "--seed_base", "7"]
            subprocess.check_call(base + ["--out", text], cwd=ROOT)
            subprocess.check_call(base + ["--input", "image", "--out", image], cwd=ROOT)
            tr = [json.loads(line) for line in Path(text).read_text(encoding="utf-8").splitlines()]
            ir = [json.loads(line) for line in Path(image).read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(tr), len(ir))
        self.assertGreater(len(tr), 0)
        for a, b in zip(tr, ir):
            for key in ("state", "legal", "probs", "action", "played", "result", "completion"):
                self.assertEqual(a[key], b[key], key)
            self.assertEqual(b["input"], "image")
            self.assertEqual(b["grid"], grid_from_state(b["state"]))
            self.assertIn(FRAME_PLACEHOLDER, b["messages"][1]["content"])
            self.assertNotIn("vision_start", a["messages"][1]["content"])

    def test_processor_if_available(self):
        try:
            import transformers  # noqa: F401
            from transformers import AutoProcessor
        except ImportError as e:
            self.skipTest(f"transformers not installed ({e})")
        try:
            proc = AutoProcessor.from_pretrained(C.IMAGE_BASE_MODEL)
        except Exception as e:
            self.skipTest(f"processor weights not reachable ({type(e).__name__}: {e})")
        proc.tokenizer.padding_side = "left"
        im = render_frame([[2, 0, 0, 0], [0, 4, 0, 0], [0, 0, 0, 0], [0, 0, 0, 8]])
        prompt = build_image_prompt(["up", "left"])
        enc = proc(text=[prompt], images=[im], return_tensors="pt", padding=True)
        self.assertEqual(enc["input_ids"].shape[0], 1)
        self.assertGreater(enc["input_ids"].shape[1], 8)
        ids = enc["input_ids"][0].tolist()
        # 자리표시자가 패치 토큰으로 늘어나야 한다. 문자열 그대로 한 칸이면 안 된다.
        self.assertGreater(len(ids), len(proc.tokenizer.encode(prompt, add_special_tokens=False)))
        # Qwen3.5 는 image_grid_thw 가 있으면 mm_token_type_ids 가 없으면 M-RoPE 에서 예외를 낸다.
        self.assertIn("mm_token_type_ids", enc)
        self.assertEqual(list(enc["mm_token_type_ids"].shape), list(enc["input_ids"].shape))

    def test_detach_keeps_vision_model_output(self):
        try:
            from transformers.utils.generic import ModelOutput
        except ImportError as e:
            self.skipTest(f"transformers not installed ({e})")
        from dataclasses import dataclass

        import torch

        from image_policy import _detach

        @dataclass
        class Out(ModelOutput):
            pooler_output: torch.Tensor | None = None

        t = torch.ones(2, requires_grad=True)
        got = _detach(Out(pooler_output=t))
        self.assertIsInstance(got, ModelOutput)
        self.assertTrue(hasattr(got, "pooler_output"))
        self.assertFalse(got.pooler_output.requires_grad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
