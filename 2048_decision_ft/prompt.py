# The system sentence and the plain "Answer:" layout are from OmniJev/PlayJev
# playjev/model.py (Apache License 2.0). License text: docs/licenses/PlayJev-LICENSE.txt
# Upstream file has no copyright header. The grant is the PlayJev LICENSE.
# Modified: <state> is a text board, and the option sentences are the short phrases below.
# The image placeholder, chat template, and PlayJevModel runtime are not included.
"""PlayJev의 openjev-letters-v1 문구를 그대로 쓰되, 화면 대신 텍스트 상태창을 state로 넣음.
베이스 모델용 plain 템플릿: 끝이 "Answer:"이고 정답 슬롯은 공백 붙은 글자 토큰 " A", " B", ..."""
from __future__ import annotations

SYSTEM_PROMPT = ("Apply the question to the state. Choose exactly one of the listed options. "
                 "Respond with only its uppercase letter, with no explanation or reasoning.")
INSTRUCTIONS = "Which move should the player make next?"
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
OPTION_DESC = {"up": "slide all tiles up", "down": "slide all tiles down",
               "left": "slide all tiles left", "right": "slide all tiles right"}


def options_block(options) -> str:
    return "\n".join(f"{LETTERS[i]}. {o}: {OPTION_DESC.get(o, '')}".rstrip(": ") for i, o in enumerate(options))


def user_text(state: str, options) -> str:
    letters = ", ".join(LETTERS[: len(options)])
    return (f"<state>\n{state.strip()}\n</state>\n\nQuestion: {INSTRUCTIONS}\n\n"
            f"Options:\n{options_block(options)}\n\nAnswer with one letter: {letters}.")


def build_prompt(state: str, options) -> str:
    return f"{SYSTEM_PROMPT}\n\n{user_text(state, options)}\nAnswer:"
