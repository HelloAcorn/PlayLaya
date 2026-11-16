# Copyright holders of OmniJev/PlayJev. Licensed under the Apache License, Version 2.0.
# Vendored from playjev/model.py (plain-template builders only).
# https://github.com/OmniJev/PlayJev/blob/main/playjev/model.py
# License text: docs/licenses/PlayJev-LICENSE.txt
# Modified: the chat template, temporal frame stacking, and PlayJevModel runtime are not copied.
# 2048 option sentences below are from games/2048/pj_hook.js, not from the shorter phrases in prompt.py.
"""PlayJev plain 프롬프트 (openjev-letters-v1 문구, 프레임이 state).

한 수에 프레임 하나. <state> 안에는 이미지 자리표시자만 있고 텍스트 보드는 넣지 않는다.
끝이 'Answer:' 라서 정답 슬롯은 공백 붙은 글자 토큰 ' A', ' B', ... 이다.
"""
from __future__ import annotations

from typing import Sequence

PROMPT_VERSION = "playjev-letters-v1"  # openjev-letters-v1 wording, frames as the state

# Frozen OpenJev system sentence (beat the "You are a System One decision model" wording by 3 to 6 points).
SYSTEM_PROMPT = (
    "Apply the question to the state. Choose exactly one of the listed options. "
    "Respond with only its uppercase letter, with no explanation or reasoning."
)
DEFAULT_INSTRUCTIONS = "Which move should the player make next?"
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
FRAME_PLACEHOLDER = "<|vision_start|><|image_pad|><|vision_end|>"  # the processor expands <|image_pad|> to one token per merged patch
PLAIN_ANSWER_CUE = "Answer:"

# games/2048/pj_hook.js 의 actions. 텍스트 경로(prompt.py)의 짧은 문장과 다르다.
ACTION_DESC = {
    "up": "slide every tile as far up as it can go and merge equal tiles that meet",
    "down": "slide every tile as far down as it can go and merge equal tiles that meet",
    "left": "slide every tile as far left as it can go and merge equal tiles that meet",
    "right": "slide every tile as far right as it can go and merge equal tiles that meet",
}


def options_block(options: Sequence[dict]) -> str:
    """Lettered `name: description` lines, exactly as OpenJev renders a Choice question."""
    if len(options) > len(LETTERS):
        raise ValueError(f"{len(options)} options exceed the {len(LETTERS)} letter slots")
    lines = []
    for letter, opt in zip(LETTERS, options):
        desc = (opt.get("description") or "").strip()
        lines.append(f"{letter}. {opt['name']}: {desc}" if desc else f"{letter}. {opt['name']}")
    return "\n".join(lines)


def render_suffix(options: Sequence[dict], instructions: str = DEFAULT_INSTRUCTIONS) -> str:
    letters = ", ".join(LETTERS[: len(options)])
    return f"Question: {instructions}\n\nOptions:\n{options_block(options)}\n\nAnswer with one letter: {letters}."


def render_state(n_placeholders: int, text: str | None = None) -> str:
    """The state block: frame placeholders first, then a text body if the state has one. A state may be
    frames (a game), text (a document, a question stem), or both; it may not be empty."""
    parts = [FRAME_PLACEHOLDER] * n_placeholders
    if text and text.strip():
        parts.append(text.strip())
    if not parts:
        raise ValueError("a state needs at least one frame or a text body")
    return "<state>\n" + "\n".join(parts) + "\n</state>"


def build_plain_prompt(options: Sequence[dict], instructions: str = DEFAULT_INSTRUCTIONS, n_placeholders: int = 1,
                       state_text: str | None = None) -> str:
    return (f"{SYSTEM_PROMPT}\n\n{render_state(n_placeholders, state_text)}\n\n"
            f"{render_suffix(options, instructions)}\n{PLAIN_ANSWER_CUE}")


def action_options(names: Sequence[str]) -> list[dict]:
    """합법 수 이름만, 주어진 순서대로. 학습 때 이 순서를 샘플마다 섞는다."""
    out = []
    for name in names:
        if name not in ACTION_DESC:
            raise ValueError(f"unknown 2048 action {name}")
        out.append({"name": name, "description": ACTION_DESC[name]})
    return out


def build_image_prompt(names: Sequence[str]) -> str:
    """프로세서에 넘기기 직전의 plain 문자열. 프레임은 하나."""
    return build_plain_prompt(action_options(names), DEFAULT_INSTRUCTIONS, n_placeholders=1, state_text=None)


def image_messages(names: Sequence[str]) -> list[dict]:
    """텍스트 경로의 messages 와 같은 역할. 'Answer:' 큐는 넣지 않는다 (학습은 build_image_prompt 를 씀)."""
    opts = action_options(names)
    user = render_state(1) + "\n\n" + render_suffix(opts)
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]
