# PlayLaya

게임별 decision LLM 파인튜닝 코드를 게임마다 한 폴더씩 모아 둔 저장소예요. 입력은 텍스트 상태창, 출력은 다음 행동이에요.

| 폴더 | 게임 | 설명 |
|---|---|---|
| [2048_decision_ft](2048_decision_ft/) | 2048 | expectimax 전문가를 따라 배우는 LoRA 파인튜닝, 평가, Laya 평가/리플레이 |

사이트: https://helloacorn.github.io/PlayLaya/ (`docs/`, GitHub Pages). 게임 10개를 브라우저에서 두면서, 각 판의 텍스트 상태창과 글자 선택지를 같이 볼 수 있어요. 파인튜닝 코드는 아직 2048만 있어요.

새 게임은 `<게임>_decision_ft/` 폴더로 추가하고, 실행 방법은 각 폴더의 README를 보면 돼요.

