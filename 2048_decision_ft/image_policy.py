"""이미지 모델 로딩과 글자 슬롯 판독.

판독 자리는 PlayJev playjev/model.py 의 PlayJevModel._forward 와 같다 (Apache-2.0,
docs/licenses/PlayJev-LICENSE.txt). 이 파일은 그 자리를 다시 쓴 것이고 PlayJevModel 은
복사하지 않았다. AutoProcessor + AutoModelForImageTextToText, plain 프롬프트,
마지막 위치에서 합법 수 글자 토큰(' A' ..)만 softmax.
전체 어휘 로짓은 만들지 않고, 그 행만 fp32 로 캐스팅한다 (bf16 로짓이 동점이 되는 문제를 피하려고).

dtype 기본값은 float16 이다. PlayJev 자체 로더는 bfloat16 이지만 RTX 2070 SUPER(Turing)에는
bf16 텐서코어가 없어 그 dtype 이 매우 느리다. --dtype bfloat16 으로 맞출 수 있다.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("USE_TF", "0")

import torch

import config as C
from frame import FrameRenderer
from lora import is_vision_path
from playjev_prompt import LETTERS, build_image_prompt

_PIXEL_KEYS = ("pixel_values", "image_grid_thw", "mm_token_type_ids", "pixel_values_videos", "video_grid_thw")


def resolve_dtype(name: str, device: torch.device) -> torch.dtype:
    """CPU 에서는 fp32. CUDA 에서는 요청한 dtype. Turing 에서 bfloat16 이면 한 줄 경고."""
    if device.type != "cuda":
        return torch.float32
    dt = getattr(torch, name)
    if dt == torch.bfloat16:
        major, _ = torch.cuda.get_device_capability(device)
        if major < 8:
            print("[image] 이 GPU 는 bf16 텐서코어가 없습니다 (Turing 이하). "
                  "학습/평가는 --dtype float16 이 훨씬 빠릅니다.", flush=True)
    return dt


def load_image_model(model_path: str, device: str, dtype_name: str):
    from transformers import AutoModelForImageTextToText, AutoProcessor

    dev = torch.device(device)
    dt = resolve_dtype(dtype_name, dev)
    local = Path(model_path).exists()
    processor = AutoProcessor.from_pretrained(model_path, local_files_only=local)
    tok = processor.tokenizer
    tok.padding_side = "left"  # 마지막 위치가 모든 행에서 정답 슬롯
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    kw = dict(device_map={"": device}, local_files_only=local)
    try:
        model = AutoModelForImageTextToText.from_pretrained(model_path, dtype=dt, **kw)
    except TypeError:
        model = AutoModelForImageTextToText.from_pretrained(model_path, torch_dtype=dt, **kw)
    model.config.use_cache = False
    if getattr(model, "generation_config", None) is not None:
        model.generation_config.use_cache = False
    model.eval()
    return processor, model, dt


def slot_ids_for(tok, k: int = 4) -> list[int]:
    ids = []
    for letter in LETTERS[:k]:
        text = f" {letter}"  # plain 템플릿. chat 템플릿의 맨 글자 토큰이 아니다.
        enc = tok.encode(text, add_special_tokens=False)
        if len(enc) != 1:
            raise ValueError(f"slot {text!r} is not one token")
        ids.append(enc[0])
    if len(set(ids)) != len(ids):
        raise ValueError("answer slot tokens collide")
    return ids


def find_vision(model):
    cands = []
    for name, mod in model.named_modules():
        if name and is_vision_path(name):
            cands.append((name, mod))
    if not cands:
        return None
    # 가장 위쪽 모듈 (이름이 가장 짧은 것) 을 얼린다.
    return min(cands, key=lambda nm: len(nm[0]))[1]


def _detach(x):
    if torch.is_tensor(x):
        return x.detach()
    # ModelOutput 는 dict 의 서브클래스다. 평범한 dict 로 다시 만들면 pooler_output 속성이 사라져
    # Qwen3.5 get_image_features 가 깨진다. 그 객체는 키만 떼어 내고 타입은 유지한다.
    if type(x) is not dict and hasattr(x, "keys") and hasattr(x, "__setitem__"):
        for k in list(x.keys()):
            try:
                x[k] = _detach(x[k])
            except Exception:
                pass
        return x
    if isinstance(x, dict):
        return {k: _detach(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)):
        t = type(x)
        return t(_detach(i) for i in x)
    return x


def freeze_vision(model):
    """비전 타워 가중치는 학습하지 않고, 역전파도 타워 안에서 멈춘다.

    얼린 가중치로도 활성화는 남는데, 8GB 에서는 그 그래프가 부담이다.
    언어 모델 LoRA 만 갱신하므로 비전 출력은 상수로 둔다.
    """
    vis = find_vision(model)
    if vis is None:
        print("[image] 비전 타워를 찾지 못했습니다. 이름에 visual/vision 이 없는 Linear 는 LoRA 대상이 됩니다.", flush=True)
        return None
    for p in vis.parameters():
        p.requires_grad_(False)

    def _eval(mod, _inputs):
        mod.eval()  # model.train() 이 드롭아웃을 켜도 비전은 eval

    vis.register_forward_pre_hook(_eval)
    vis.register_forward_hook(lambda _m, _i, out: _detach(out))
    n = sum(p.numel() for p in vis.parameters())
    print(f"[image] froze {vis.__class__.__name__} ({n / 1e6:.1f}M params), outputs detached", flush=True)
    return vis


def prepare(processor, prompts, images):
    return processor(text=list(prompts), images=list(images), return_tensors="pt", padding=True)


def to_device(enc, device: torch.device):
    out = {}
    for k, v in enc.items():
        out[k] = v.to(device) if hasattr(v, "to") else v
    return out


def forward_slots(model, enc, slot_ids: torch.Tensor, n_opts: torch.Tensor, device: torch.device,
                  dtype: torch.dtype) -> torch.Tensor:
    """PlayJevModel._forward 와 같은 자리(model.model, 마지막 토큰)에서 K개 글자 로짓만."""
    kw = {k: enc[k] for k in _PIXEL_KEYS if k in enc and enc[k] is not None}
    use_amp = device.type == "cuda" and dtype in (torch.float16, torch.bfloat16)
    amp = torch.float16 if dtype == torch.float16 else torch.bfloat16
    inner = model.model if hasattr(model, "model") else model
    with torch.autocast(device_type=device.type, dtype=amp, enabled=use_amp):
        out = inner(input_ids=enc["input_ids"], attention_mask=enc["attention_mask"],
                    use_cache=False, return_dict=True, **kw)
    h = out.last_hidden_state[:, -1, :].float()
    w = model.get_output_embeddings().weight.index_select(0, slot_ids).float()
    logits = h @ w.T
    mask = torch.arange(logits.shape[1], device=logits.device)[None, :] < n_opts[:, None]
    return logits.masked_fill(~mask, float("-inf"))


class ImagePolicy:
    def __init__(self, model_path: str, adapter: str | None = None, device: str = C.DEVICE,
                 dtype: str | None = None, renderer: str = C.IMAGE_RENDERER):
        self.device = torch.device(device)
        self.dtype_name = dtype or C.IMAGE_DTYPE
        self.processor, self.model, self.dtype = load_image_model(model_path, device, self.dtype_name)
        if adapter:
            from lora import load_adapter
            load_adapter(self.model, adapter)
            self.model.eval()
        self.slot_ids = torch.tensor(slot_ids_for(self.processor.tokenizer, 4), device=self.device)
        self.frames = FrameRenderer(renderer)
        self.frames.open()

    def close(self):
        self.frames.close()

    @torch.no_grad()
    def probs(self, images, options: list[list[str]]) -> list[list[float]]:
        prompts = [build_image_prompt(o) for o in options]
        enc = to_device(prepare(self.processor, prompts, images), self.device)
        n_opts = torch.tensor([len(o) for o in options], device=self.device)
        logits = forward_slots(self.model, enc, self.slot_ids, n_opts, self.device, self.dtype)
        p = torch.softmax(logits, -1)
        return [p[i, : len(o)].tolist() for i, o in enumerate(options)]

    def choose(self, grid, legal: list[str]) -> str:
        p = self.probs([self.frames.render(grid)], [legal])[0]
        return legal[max(range(len(legal)), key=p.__getitem__)]
