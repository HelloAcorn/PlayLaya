# PlayVLA

이 프로젝트는 [PlayJev](https://github.com/OmniJev/PlayJev)를 공부하고 참고해서 만든 재구현이에요. PlayJev의 `LICENSE`를 확인했고, 본문은 Apache License 2.0이에요. 여기서 그 파일을 가져오거나 고친 부분도 같은 라이선스를 따릅니다. 전문은 [`docs/licenses/PlayJev-LICENSE.txt`](docs/licenses/PlayJev-LICENSE.txt)에 있고, 가져온 목록은 [`THIRD_PARTY_NOTICES`](THIRD_PARTY_NOTICES)에 있어요. PlayJev 저장소에는 NOTICE 파일이 없어요.

이 저장소 루트에는 자체 LICENSE 파일이 없어요. 원작 브라우저 게임은 각 `docs/games/<게임>/`의 LICENSE를 따르고, PlayJev에서 가져온 코드만 Apache-2.0입니다.

게임별 decision LLM 파인튜닝 코드를 게임마다 한 폴더씩 모아 둔 저장소예요. 출력은 다음 행동이에요. 2048은 텍스트 상태창과, PlayJev와 같은 화면 한 장을 넣는 이미지 경로를 같이 둡니다.

| 폴더 | 게임 | 설명 |
|---|---|---|
| [2048_decision_ft](2048_decision_ft/) | 2048 | expectimax 전문가를 따라 배우는 텍스트 LoRA, 그리고 PlayJev 형식의 이미지 학습/평가. Laya 평가/리플레이 |

사이트: https://helloacorn.github.io/playjev-notes/ (`docs/`, GitHub Pages). 게임 10개를 브라우저에서 두면서, 각 판의 텍스트 상태창과 글자 선택지를 같이 볼 수 있어요. 파인튜닝 코드는 아직 2048만 있어요.

저장소: https://github.com/HelloAcorn/playjev-notes

새 게임은 `<게임>_decision_ft/` 폴더로 추가하고, 실행 방법은 각 폴더의 README를 보면 돼요.

## PlayJev에서 가져오거나 맞춘 것

- **이미지 프롬프트.** `2048_decision_ft/playjev_prompt.py`는 `playjev/model.py`의 plain 템플릿만 가져왔어요. openjev-letters-v1 문장, `<state>` 안의 이미지 자리, `Answer:`로 끝나는 선택지예요. 2048 선택지 문장은 `games/2048/pj_hook.js`의 긴 설명이에요.
- **텍스트 프롬프트.** `2048_decision_ft/prompt.py`는 같은 시스템 문장과 `Answer:` 배치를 쓰고, `<state>`에는 화면 대신 2048 텍스트 상태창을 넣어요. 선택지 설명은 짧은 문장으로 바꿨어요.
- **프레임.** `2048_decision_ft/vendor/pj_shim.js`는 `games/_shared/pj_shim.js` 그대로예요. `vendor/pj_2048_hook.js`는 `games/2048/pj_hook.js`에 `setGrid`만 더했어요. `frame.py`는 그 훅의 500×500 보드와 shim의 긴 변 448px, JPEG 품질 0.85를 PIL로 다시 그린 것이고, `--renderer playwright`는 위 JS를 불러요.
- **2048 교사.** `board.py`는 `playjev/teachers/2048.py`의 64비트 니블 보드와 줄 휴리스틱을 단순화해 가져왔어요. 위/아래는 전치 후 좌/우로 움직이고, 수도 같이 돌려요. `expert.py`의 깊이 2 expectimax는 같은 교사 설계이고, 탐색 코드는 다시 썼어요.
- **사이트.** `docs/site.css`는 `demo/demo.css`를 고친 거예요. 파일 아래쪽 `PlayVLA additions`가 여기서 더한 규칙이에요. `docs/pj_silence.js`는 `demo/pj_silence.js` 그대로이고, 앞에 출처 주석만 붙였어요. `docs/site.js`는 데모의 테마와 상단 바를 따라 새로 쓴 페이지 스크립트예요.
- **게임 10개.** `docs/games/`는 PlayJev `demo/games/`에 정리된 원작 사본이에요. 라이선스는 원작자 것이고, PlayJev가 넣은 패치(소리 요청을 막는 스크립트, Pacman의 읽기 전용 getter, Sokoban의 Microban 레벨 등)는 Apache-2.0이에요. 이 저장소는 학습용 `pj_hook.js`를 빼서 키보드로 두게 했고, 앞 페이지가 상태를 읽도록 작은 연결만 더했어요. 게임마다 `CHANGES.md`에 적혀 있어요.

이미지 경로의 손실(전문가 soft target과 글자 분포의 교차 엔트로피)은 PlayJev `train_sft.py`와 같은 방식이에요.

