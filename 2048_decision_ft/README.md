# 2048 의사결정 LLM 파인튜닝 (텍스트 상태창 → 수 하나)

PlayJev가 **화면 픽셀**을 넣고 수 하나를 고르게 했다면, 여기서는 같은 계약을 **텍스트 상태창**으로 바꿉니다.
입력은 2048 보드 상태창, 출력은 다음 수(up/down/left/right) 하나입니다. 베이스 모델도 PlayJev와 같은
`Qwen3.5-0.8B-Base`(PlayJev 폴더에 받아 둔 로컬 체크포인트)를 쓰고, 언어 모델 부분만 올립니다.

## 왜 2048인가

- **상태창이 완전한 정보**: 4x4 숫자 16개 + 점수면 게임 상태가 전부 표현됩니다. 프레임이나 시간 정보가 필요 없습니다.
- **반사신경이 필요 없음**: 턴제라서 한 수 늦어도 손해가 없고, LLM이 한 수에 몇십~몇백 ms 써도 됩니다.
- **강한 전문가를 공짜로**: 순수 파이썬 expectimax가 한 판에 수 초~수십 초로 2048 타일을 만듭니다
  (평가 시드 4판에서 4판 모두 2048 도달, 평균 점수 약 41,000). 무작위는 평균 약 1,000점.
- **개선 여지가 큼**: PlayJev 픽셀 모델은 2048에서 vs teacher 0.21로 10개 게임 중 하위권이었습니다.
  같은 게임을 텍스트로 주면 얼마나 오르는지가 이 실험의 질문입니다.
- Sokoban/Snake는 PlayJev에서 이미 0.9~1.0이라 새로 배울 게 적고, Sokoban은 레벨 데이터와 솔버가 무겁습니다.

## 입력/출력 형식

PlayJev의 `openjev-letters-v1` 문구를 그대로 쓰고, `<state>` 안에 프레임 대신 상태창 텍스트를 넣습니다.
선택지는 **보드를 실제로 바꾸는 합법 수만** 보여 주고, 학습 때는 샘플마다 순서를 섞습니다.

```
Apply the question to the state. Choose exactly one of the listed options. Respond with only its uppercase letter, with no explanation or reasoning.

<state>
Move: 1 | Score: 0 | Empty: 13 | Max tile: 4
Board (4x4, . = empty):
    .     .     .     .
    4     .     .     .
    .     2     .     .
    2     .     .     .
</state>

Question: Which move should the player make next?

Options:
A. up: slide all tiles up
B. down: slide all tiles down
C. left: slide all tiles left
D. right: slide all tiles right

Answer with one letter: A, B, C, D.
Answer:
```

출력은 다음 토큰 하나(` A`~` D`)입니다. 모델은 텍스트를 생성하지 않고, 마지막 위치에서 글자 토큰들의
확률만 읽어 가장 높은 수를 둡니다(한 번의 순전파).

학습 정답은 전문가가 각 수의 기대 가치를 softmax한 **soft target**이고, 손실은 그 분포와 모델 글자 분포의
교차 엔트로피입니다(PlayJev `train_sft.py`와 같은 방식).

데이터 한 줄(JSONL) 필드:

| 필드 | 뜻 |
|---|---|
| `state` | 상태창 텍스트 (모델 입력) |
| `legal` | 합법 수 (고정 순서 up, down, left, right 중) |
| `probs` | 전문가 soft target |
| `action` | 전문가 최선 수 |
| `messages`, `completion` | 일반 chat SFT 도구용 형식 (선택지 고정 순서 기준 글자) |
| `played`, `result` | 실제로 둔 수와 그 결과(얻은 점수, 누적 점수, 최대 타일, 종료 여부) |

## 파일

| 파일 | 역할 |
|---|---|
| `config.py` | 모델 경로, 데이터 양, LoRA, 학습/평가 하이퍼파라미터 |
| `board.py` | 64비트 비트보드 2048 이동/점수/휴리스틱 테이블 |
| `game2048.py` | 시드 고정 2048 환경 + `render_state()` 상태창 |
| `expert.py` | expectimax 전문가, soft target 생성 |
| `prompt.py` | 프롬프트 템플릿 (PlayJev 문구 + 텍스트 state) |
| `gen_data.py` | 전문가 플레이(또는 DAgger) → JSONL |
| `lora.py` | 최소 LoRA 구현 (peft 없이) |
| `policy.py` | 모델 로딩, 글자 슬롯 판독 (학습/평가 공용) |
| `train.py` | LoRA SFT, 검증 손실/전문가 일치율, `best/`·`final/` 어댑터 저장 |
| `evaluate.py` | 무작위/전문가/모델 N판 비교, vs_expert 계산 |

## 실행 (PowerShell, 이 폴더에서)

PlayJev의 가상환경을 그대로 씁니다(torch 2.11 cu128, transformers 5.17).

```powershell
cd C:\workspace\PlayLaya\2048_decision_ft
$py = "C:\workspace\PlayJev\.venv\Scripts\python.exe"

# 1) 데이터: 전문가 40판 (약 6만 샘플, CPU로 십수 분)
& $py gen_data.py --episodes 40 --out data\clone.jsonl

# 2) 학습: LoRA r=16, 1 epoch
& $py train.py --data data\clone.jsonl --out ckpt\run1

# 3) 평가: 학습에 안 쓴 시드 16판, 무작위/전문가/모델 비교
& $py evaluate.py --policies random expert model --adapter ckpt\run1\best --games 16 --agreement

# (선택) 베이스 모델 제로샷 기준선
& $py evaluate.py --policies model --games 4

# (선택) DAgger 1라운드: 모델이 두고 전문가가 라벨, 시드는 겹치지 않게
& $py gen_data.py --episodes 20 --policy model --adapter ckpt\run1\best --eps 0.05 0.05 --seed_base 50000 --out data\dagger1.jsonl
& $py train.py --data data\clone.jsonl data\dagger1.jsonl --out ckpt\run2
```

스모크 테스트:

```powershell
& $py gen_data.py --episodes 2 --max_moves 200 --out data\smoke.jsonl
& $py train.py --data data\smoke.jsonl --out ckpt\smoke --max_steps 2 --limit 32 --batch 8 --micro_batch 4
& $py evaluate.py --policies random expert model --adapter ckpt\smoke\final --games 2 --max_moves 30
```

## 참고 / 주의

- GPU는 RTX 2070 SUPER(8GB)라 fp16으로 돌립니다. bf16은 이 카드에서 매우 느립니다.
- 이 PC venv에는 `flash-linear-attention`의 triton과 `causal_conv1d`가 없어 linear attention 층이
  PyTorch 참조 구현으로 돌아갑니다(정확하지만 느림). 상태창 프롬프트가 짧아(약 200토큰) 버틸 만합니다.
- `peft`/`trl`이 없어 LoRA는 `lora.py`에 직접 구현했습니다. 저장물은 `adapter.pt` + `adapter_config.json`입니다.
- 메모리가 부족하면 `--micro_batch 4` 또는 `--grad_ckpt`를 쓰세요.
