"""최소 LoRA 구현 (peft가 PlayJev venv에 없어서 직접 씀). 베이스 가중치는 얼리고 A, B만 학습."""
from __future__ import annotations

import json
import math
from pathlib import Path

import torch
import torch.nn as nn


class LoRALinear(nn.Module):
    def __init__(self, base: nn.Linear, r: int, alpha: float, dropout: float):
        super().__init__()
        self.base = base
        for p in self.base.parameters():
            p.requires_grad_(False)
        dev = base.weight.device
        self.lora_A = nn.Parameter(torch.empty(r, base.in_features, device=dev, dtype=torch.float32))
        self.lora_B = nn.Parameter(torch.zeros(base.out_features, r, device=dev, dtype=torch.float32))
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))
        self.scale = alpha / r
        self.drop = nn.Dropout(dropout) if dropout > 0 else nn.Identity()

    def forward(self, x):
        y = self.base(x)
        d = (self.drop(x).to(self.lora_A.dtype) @ self.lora_A.T) @ self.lora_B.T
        return y + (d * self.scale).to(y.dtype)


def inject(model: nn.Module, targets, r: int, alpha: float, dropout: float) -> int:
    """베이스 전체를 얼린 뒤 대상 Linear만 LoRA로 감쌈 (임베딩, 노름 등은 학습 안 함)."""
    for p in model.parameters():
        p.requires_grad_(False)
    n = 0
    for name, mod in list(model.named_modules()):
        for child_name, child in list(mod.named_children()):
            if child_name in targets and isinstance(child, nn.Linear):
                setattr(mod, child_name, LoRALinear(child, r, alpha, dropout)); n += 1
    if n == 0:
        raise ValueError(f"no Linear layer matched {targets}")
    return n


def lora_state_dict(model: nn.Module) -> dict:
    return {k: v.detach().cpu() for k, v in model.state_dict().items() if "lora_" in k}


def save_adapter(model: nn.Module, path, cfg: dict) -> None:
    path = Path(path); path.mkdir(parents=True, exist_ok=True)
    torch.save(lora_state_dict(model), path / "adapter.pt")
    (path / "adapter_config.json").write_text(json.dumps(cfg, indent=1, ensure_ascii=False), encoding="utf-8")


def load_adapter(model: nn.Module, path) -> dict:
    path = Path(path)
    cfg = json.loads((path / "adapter_config.json").read_text(encoding="utf-8"))
    inject(model, cfg["targets"], cfg["r"], cfg["alpha"], 0.0)
    sd = torch.load(path / "adapter.pt", map_location="cpu")
    missing, unexpected = model.load_state_dict(sd, strict=False)
    bad = [k for k in missing if "lora_" in k]
    if bad or unexpected:
        raise ValueError(f"adapter mismatch: missing {bad[:3]} unexpected {unexpected[:3]}")
    return cfg
