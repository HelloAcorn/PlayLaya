"""모델 로딩과 '글자 슬롯' 판독. 마지막 위치의 은닉 상태를 " A", " B", ... 토큰 행에만 투영해서
합법 수 위의 확률을 얻음(전체 어휘 logits를 만들지 않음). 학습과 평가가 같은 함수를 씀."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("USE_TF", "0")

import torch

import config as C
from prompt import LETTERS, build_prompt


def load_base(model_path: str = C.MODEL_PATH, device: str = C.DEVICE, dtype: str = C.DTYPE):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    local = Path(model_path).exists()
    tok = AutoTokenizer.from_pretrained(model_path, local_files_only=local)
    tok.padding_side = "left"  # 마지막 위치가 모든 행에서 정답 슬롯
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    # 비전 체크포인트지만 텍스트 상태만 쓰므로 언어 모델(Qwen3_5ForCausalLM)만 올림
    model = AutoModelForCausalLM.from_pretrained(model_path, dtype=getattr(torch, dtype),
                                                 device_map={"": device}, local_files_only=local)
    model.config.use_cache = False
    return tok, model


def slot_ids_for(tok, k: int = 4) -> list[int]:
    ids = []
    for letter in LETTERS[:k]:
        enc = tok.encode(f" {letter}", add_special_tokens=False)
        if len(enc) != 1:
            raise ValueError(f"slot ' {letter}' is not one token")
        ids.append(enc[0])
    return ids


def slot_logits(model, input_ids, attention_mask, slot_ids: torch.Tensor, n_opts: torch.Tensor) -> torch.Tensor:
    out = model.model(input_ids=input_ids, attention_mask=attention_mask, use_cache=False, return_dict=True)
    h = out.last_hidden_state[:, -1, :].float()
    w = model.get_output_embeddings().weight[slot_ids].float()
    logits = h @ w.T
    mask = torch.arange(logits.shape[1], device=logits.device)[None, :] < n_opts[:, None]
    return logits.masked_fill(~mask, float("-inf"))


class LMPolicy:
    def __init__(self, model_path: str = C.MODEL_PATH, adapter: str | None = None, device: str = C.DEVICE):
        self.device = torch.device(device)
        self.tok, self.model = load_base(model_path, device)
        if adapter:
            from lora import load_adapter
            load_adapter(self.model, adapter)
        self.model.eval()
        self.slot_ids = torch.tensor(slot_ids_for(self.tok, 4), device=self.device)

    @torch.no_grad()
    def probs(self, states: list[str], options: list[list[str]]) -> list[list[float]]:
        prompts = [build_prompt(s, o) for s, o in zip(states, options)]
        enc = self.tok(prompts, return_tensors="pt", padding=True).to(self.device)
        n_opts = torch.tensor([len(o) for o in options], device=self.device)
        logits = slot_logits(self.model, enc["input_ids"], enc["attention_mask"], self.slot_ids, n_opts)
        p = torch.softmax(logits, -1)
        return [p[i, : len(o)].tolist() for i, o in enumerate(options)]
