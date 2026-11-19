"""베이스 이미지 런의 지표, 곡선, 버킷, 조기 종료.

  python test_base_image.py

프로세서를 받을 수 있으면 층을 줄인 무작위 Qwen3.5 로 한 수를 두고
학습과 같은 record_game_metrics 에 넣는다. GPU 학습은 하지 않는다.
"""
from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from game_metrics import (  # noqa: E402
    CSV_COLUMNS, Guard, bucket_caps, loss_targets, overfit_ok, record_game_metrics,
    series, tile_bucket, uniform_ce,
)


def _row(step, score, loss):
    games = {
        "scores": [score - 10, score, score + 10],
        "mean_score": score, "median_score": score, "mean_moves": 12.0,
        "expert_agreement": 0.4, "max_tile_distribution": {"16": 1, "32": 2},
        "moves": [10, 12, 14], "max_tiles": [16, 32, 32],
    }
    val = {"val_loss": loss, "val_kl": loss / 2, "val_agreement": 0.5}
    from game_metrics import metrics_row
    return metrics_row(step, loss, val, games, [100000, 100001, 100002])


class BaseImageTest(unittest.TestCase):
    def test_buckets_and_caps(self):
        self.assertEqual(tile_bucket(128), "le128")
        self.assertEqual(tile_bucket(256), "256")
        self.assertEqual(tile_bucket(512), "512")
        self.assertEqual(tile_bucket(1024), "ge1024")
        self.assertEqual(bucket_caps(8000, None), {"le128": 2000, "256": 2000, "512": 2000, "ge1024": 2000})
        self.assertEqual(bucket_caps(5, None)["ge1024"], 2)
        self.assertEqual(sum(bucket_caps(5, None).values()), 5)

    def test_hard_label_is_one_hot(self):
        soft = loss_targets([0.1, 0.7, 0.2], 1, "soft")
        self.assertEqual(soft, [0.1, 0.7, 0.2])
        hard = loss_targets([0.1, 0.7, 0.2], 1, "hard")
        self.assertEqual(hard, [0.0, 1.0, 0.0])

    def test_overfit_threshold(self):
        rows = [{"legal": ["up", "down", "left", "right"]}, {"legal": ["up", "left"]}]
        uniform = uniform_ce(rows)
        self.assertAlmostEqual(uniform, (math.log(4) + math.log(2)) / 2)
        self.assertTrue(overfit_ok(uniform * 0.5, uniform, 0.6))
        self.assertFalse(overfit_ok(uniform * 0.6, uniform, 0.6))
        self.assertFalse(overfit_ok(None, uniform, 0.6))

    def test_early_stop(self):
        score = Guard(0.30, 2, 100)
        self.assertEqual(score.update(100, 1.0), (True, None))
        self.assertIsNone(score.update(70, 1.0)[1])  # 정확히 30% 는 아직 아니다
        self.assertIsNone(score.update(69, 1.0)[1])
        self.assertEqual(score.update(50, 1.0)[1], "score")

        kl = Guard(0.30, 0, 3)
        kl.update(10, 1.0)
        kl.update(10, 1.0)
        self.assertIsNone(kl.update(10, 0.5)[1])  # 줄었으면 횟수를 되돌린다
        self.assertIsNone(kl.update(10, 0.5)[1])
        self.assertIsNone(kl.update(10, 0.5)[1])
        self.assertEqual(kl.update(10, 0.5)[1], "val_kl")

    def test_metrics_and_plot(self):
        with tempfile.TemporaryDirectory() as d:
            record_game_metrics(d, _row(0, 100, 1.2))
            record_game_metrics(d, _row(100, 180, 0.8))
            rows = [json.loads(line) for line in Path(d, "metrics.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([r["step"] for r in rows], [0, 100])
            self.assertEqual(series(rows)["mean_score"], [100.0, 180.0])
            with Path(d, "metrics.csv").open(encoding="utf-8", newline="") as f:
                got = list(csv.DictReader(f))
            self.assertEqual(list(got[0].keys()), list(CSV_COLUMNS))
            self.assertEqual([r["step"] for r in got], ["0", "100"])
            self.assertEqual(json.loads(got[1]["max_tile_distribution"]), {"16": 1, "32": 2})
            png = Path(d, "score_curve.png")
            self.assertGreater(png.stat().st_size, 1000)
            from PIL import Image
            with Image.open(png) as im:
                self.assertGreater(im.size[0], 400)
                self.assertGreater(im.size[1], 400)

    def test_balanced_generation_pairs_text(self):
        with tempfile.TemporaryDirectory() as d:
            image = str(Path(d) / "i.jsonl")
            text = str(Path(d) / "t.jsonl")
            subprocess.check_call([
                sys.executable, str(ROOT / "gen_data.py"),
                "--input", "image", "--episodes", "2", "--max_moves", "12", "--seed_base", "3",
                "--eps", "0", "0", "--target_states", "6", "--bucket_cap", "2",
                "--out", image, "--paired_text", text,
            ], cwd=ROOT)
            ir = [json.loads(line) for line in Path(image).read_text(encoding="utf-8").splitlines()]
            tr = [json.loads(line) for line in Path(text).read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(ir), 2)
        self.assertEqual(len(ir), len(tr))
        for a, b in zip(ir, tr):
            for key in ("state", "legal", "probs", "action", "played", "seed"):
                self.assertEqual(a[key], b[key], key)
            self.assertIn("grid", a)
            self.assertNotIn("grid", b)
            self.assertNotIn("vision_start", b["messages"][1]["content"])
            self.assertLessEqual(max(max(row) for row in a["grid"]), 128)

    def test_driver_rejects_playjev_weights(self):
        from run_base_image import assert_base_model, resolve_base
        assert_base_model(r"C:\workspace\PlayJev\models\Qwen3.5-0.8B-Base")
        assert_base_model("Qwen/Qwen3.5-0.8B-Base")
        with self.assertRaises(SystemExit):
            assert_base_model("OmniJev/PlayJev-0.8B")
        self.assertEqual(resolve_base("Qwen/Qwen3.5-0.8B-Base"), "Qwen/Qwen3.5-0.8B-Base")

    def test_tiny_model_writes_a_real_row(self):
        try:
            import torch
            from transformers import AutoConfig, AutoModelForImageTextToText, AutoProcessor
        except ImportError as e:
            self.skipTest(f"transformers/torch missing ({e})")
        try:
            proc = AutoProcessor.from_pretrained("Qwen/Qwen3.5-0.8B-Base", local_files_only=True)
            cfg = AutoConfig.from_pretrained("Qwen/Qwen3.5-0.8B-Base", local_files_only=True)
        except Exception as e:
            self.skipTest(f"processor not cached ({type(e).__name__}: {e})")
        from evaluate import play
        from frame import render_frame
        from game_metrics import metrics_row
        from image_policy import forward_slots, slot_ids_for
        from train_image import image_move_probs, soft_ce

        cfg.text_config.num_hidden_layers = 2
        cfg.text_config.layer_types = ["linear_attention", "full_attention"]
        cfg.vision_config.depth = 1
        model = AutoModelForImageTextToText.from_config(cfg).float().eval()
        model.config.use_cache = False
        proc.tokenizer.padding_side = "left"
        device = torch.device("cpu")
        slots = torch.tensor(slot_ids_for(proc.tokenizer, 4))

        def model_probs(live, legal):
            import board as B
            frames = [render_frame(B.to_grid(g.board)) for g in live]
            return image_move_probs(model, proc, slots, device, torch.float32, frames, legal)

        games = play("model", [100000], 1, agreement=True, detail=True, model_probs=model_probs)
        frame = render_frame([[2, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
        from playjev_prompt import build_image_prompt
        from image_policy import prepare, to_device
        enc = to_device(prepare(proc, [build_image_prompt(["up", "left"])], [frame]), device)
        logits = forward_slots(model, enc, slots, torch.tensor([2]), device, torch.float32)
        target = torch.tensor([[0.25, 0.75, 0.0, 0.0]])
        loss = float(soft_ce(logits, target)[0].detach())
        self.assertTrue(math.isfinite(loss))
        val = {"val_loss": loss, "val_kl": loss, "val_agreement": 0.0}
        row = metrics_row(0, loss, val, games, [100000])
        with tempfile.TemporaryDirectory() as d:
            record_game_metrics(d, row)
            saved = json.loads(Path(d, "metrics.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(saved["step"], 0)
            self.assertEqual(saved["seeds"], [100000])
            self.assertEqual(saved["mean_score"], games["mean_score"])
            self.assertTrue(math.isfinite(saved["train_loss"]))
            self.assertGreater(Path(d, "score_curve.png").stat().st_size, 1000)
            with Path(d, "metrics.csv").open(encoding="utf-8", newline="") as f:
                got = list(csv.DictReader(f))
            self.assertEqual(got[0]["step"], "0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
