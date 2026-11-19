"""녹화 JSON 작성. GPU 와 가중치는 쓰지 않는다.

  python test_record_image_replays.py

docs/games/2048/replays/fixture_player.json 은 이 스텁으로 만든 짧은 판이다.
페이지 기본 경로는 my_model.json 이고, 그 픽스처를 읽지 않는다.
my_model.json 은 공개된 모델 녹화다. 스텁은 그 경로를 덮어쓰지 않는지만 본다.
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
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

import board as B  # noqa: E402
from game2048 import Game2048  # noqa: E402
from record_image_replays import (  # noqa: E402
    EVAL_SEEDS, build_payload, check_seeds, choose_seeds, record_games, stub_probs, write_replay,
)

FIXTURE = REPO / "docs" / "games" / "2048" / "replays" / "fixture_player.json"
PUBLISHED = REPO / "docs" / "games" / "2048" / "replays" / "my_model.json"
PAGE = REPO / "docs" / "games" / "2048"
FIXTURE_SEEDS = [11, 29]
FIXTURE_MOVES = 8
# model_replay.js hardcodes this order and indexes each move's p vector with it.
PLAYER_DIRS = ("up", "down", "left", "right")


class RecordReplayTest(unittest.TestCase):
    def test_seeds_avoid_eval_block(self):
        seeds = choose_seeds(40, random.Random(0))
        self.assertEqual(len(seeds), 40)
        self.assertEqual(len(set(seeds)), 40)
        self.assertTrue(EVAL_SEEDS.isdisjoint(seeds))
        self.assertTrue(EVAL_SEEDS.issuperset(range(100000, 100010)))

    def test_explicit_eval_seed_rejected(self):
        with self.assertRaises(SystemExit):
            check_seeds([100003])
        with self.assertRaises(SystemExit):
            check_seeds([4, 4])
        self.assertEqual(check_seeds([11, 29]), [11, 29])

    def test_stub_game_matches_engine_and_batch(self):
        one = record_games(stub_probs, FIXTURE_SEEDS, FIXTURE_MOVES, batch=1)
        two = record_games(stub_probs, FIXTURE_SEEDS, FIXTURE_MOVES, batch=2)
        self.assertEqual(one, two)
        self.assertTrue(EVAL_SEEDS.isdisjoint(g["seed"] for g in one))
        for g in one:
            game = Game2048(g["seed"])
            self.assertEqual(_flat(game), g["start"])
            self.assertGreater(len(g["moves"]), 0)
            for mv in g["moves"]:
                self.assertIn(mv["m"], game.legal())
                game.step(mv["m"])
                self.assertEqual(_flat(game), mv["g"])
                self.assertEqual(game.score, mv["s"])
                self.assertEqual(len(mv["p"]), 4)
                self.assertLess(abs(sum(mv["p"]) - 1), 0.001)
                self.assertEqual(mv["m"], ("up", "down", "left", "right")[max(range(4), key=mv["p"].__getitem__)])
            self.assertEqual(g["score"], game.score)
            self.assertEqual(g["max_tile"], game.max_tile())
            self.assertEqual(g["done"], game.done())

    def test_writer_roundtrip_is_compact(self):
        games = record_games(stub_probs, [11], 3, batch=1)
        payload = build_payload(games, "Qwen/Qwen3.5-0.8B-Base", "ckpt/base_image/best")
        self.assertNotIn("fixture", payload)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "nested" / "my_model.json"
            write_replay(path, payload)
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("\n", text[:-1])
            self.assertEqual(json.loads(text), payload)

    def test_fixture_is_the_stub_game_not_the_live_file(self):
        got = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertTrue(got["fixture"])
        self.assertEqual(got["model"], "stub")
        fresh = build_payload(
            record_games(stub_probs, FIXTURE_SEEDS, FIXTURE_MOVES, batch=1),
            "stub", None, fixture=True)
        self.assertEqual(got, fresh)
        self.assertTrue(PUBLISHED.is_file())
        published = json.loads(PUBLISHED.read_text(encoding="utf-8"))
        self.assertNotEqual(published, got)
        self.assertFalse(published.get("fixture"))
        self.assertNotEqual(published.get("model"), "stub")
        self.assertEqual(published.get("dirs"), list(PLAYER_DIRS))
        games = published["games"]
        self.assertEqual(len(games), 10)
        self.assertEqual(len({g["seed"] for g in games}), 10)
        for g in games:
            self.assertIsInstance(g["seed"], int)
            self.assertIsInstance(g["score"], int)
            self.assertIsInstance(g["max_tile"], int)
            self.assertGreater(g["max_tile"], 0)
            frames = _player_frames(g)
            actions = [f for f in frames if f.get("m")]
            self.assertGreater(len(actions), 0)
            self.assertEqual(len(actions), len(g["moves"]))
            for mv in actions:
                self.assertIn(mv["m"], PLAYER_DIRS)
                self.assertEqual(len(mv["g"]), 16)
                self.assertEqual(len(mv["p"]), 4)
                self.assertIsInstance(mv["s"], int)
            self.assertEqual(g["score"], actions[-1]["s"])
            self.assertEqual(g["max_tile"], max(actions[-1]["g"]))

    def test_page_fetches_my_model_not_the_fixture(self):
        html = (PAGE / "index.html").read_text(encoding="utf-8")
        js = (PAGE / "js" / "model_replay.js").read_text(encoding="utf-8")
        css = (PAGE / "style" / "model_replay.css").read_text(encoding="utf-8")
        self.assertIn("내 모델 플레이 보기", html)
        self.assertIn("js/model_replay.js", html)
        self.assertIn("style/model_replay.css", html)
        self.assertIn('class="restart-button"', html)
        self.assertIn("js/application.js", html)
        self.assertIn("my_model.json", js)
        self.assertNotIn("fixture_player", html + js + css)
        self.assertIn("Hugging Face", html)
        self.assertIn("아직 녹화된 판이 없습니다", html)

    def test_cli_stub_writes_and_refuses_default_out(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "stub.json"
            subprocess.check_call(
                [sys.executable, str(ROOT / "record_image_replays.py"),
                 "--stub", "--games", "2", "--max_moves", "4", "--seeds", "11", "29",
                 "--out", str(out)],
                cwd=ROOT)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(data["fixture"])
            self.assertEqual([g["seed"] for g in data["games"]], [11, 29])
            self.assertTrue(all(len(g["moves"]) <= 4 for g in data["games"]))
        before = PUBLISHED.read_bytes()
        try:
            refused = subprocess.run(
                [sys.executable, str(ROOT / "record_image_replays.py"), "--stub", "--games", "1", "--max_moves", "2"],
                cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("my_model.json", refused.stderr)
            self.assertIn("--out", refused.stderr)
            self.assertEqual(PUBLISHED.read_bytes(), before)
        finally:
            if PUBLISHED.read_bytes() != before:
                PUBLISHED.write_bytes(before)

    def test_missing_adapter_exits_before_loading_a_model(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "should-not-exist.json"
            refused = subprocess.run(
                [sys.executable, str(ROOT / "record_image_replays.py"),
                 "--adapter", str(Path(d) / "no-such-adapter"), "--games", "1",
                 "--out", str(out)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("어댑터가 없습니다", refused.stderr)
            self.assertFalse(out.exists())


def _flat(game: Game2048) -> list[int]:
    return [v for row in B.to_grid(game.board) for v in row]


def _player_frames(game: dict) -> list[dict]:
    """Same frames model_replay.js framesOf keeps: a 16-cell start, then moves with a 16-cell grid."""
    frames = []
    start = game.get("start")
    if start and len(start) == 16:
        frames.append({"g": start, "m": None, "s": 0, "p": None})
    for move in game.get("moves") or []:
        grid = move.get("g") if isinstance(move, dict) else None
        if grid and len(grid) == 16:
            frames.append(move)
    return frames


if __name__ == "__main__":
    unittest.main(verbosity=2)
