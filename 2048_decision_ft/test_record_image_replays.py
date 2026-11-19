"""녹화 JSON 작성. GPU 와 가중치는 쓰지 않는다.

  python test_record_image_replays.py

docs/games/2048/replays/fixture_player.json 은 이 스텁으로 만든 짧은 판이다.
페이지 기본 경로는 my_model.json 이고, 그 픽스처를 읽지 않는다.
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
PAGE = REPO / "docs" / "games" / "2048"
FIXTURE_SEEDS = [11, 29]
FIXTURE_MOVES = 8


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
        self.assertFalse((PAGE / "replays" / "my_model.json").exists())

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
        refused = subprocess.run(
            [sys.executable, str(ROOT / "record_image_replays.py"), "--stub", "--games", "1", "--max_moves", "2"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("my_model.json", refused.stderr)
        self.assertFalse((PAGE / "replays" / "my_model.json").exists())

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
