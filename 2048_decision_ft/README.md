# 2048 의사결정 LLM 파인튜닝 (텍스트 상태창 → 수 하나)

PlayJev가 **화면 픽셀**을 넣고 수 하나를 고르게 했다면, 여기서는 같은 계약을 **텍스트 상태창**으로 바꿉니다.
입력은 2048 보드 상태창, 출력은 다음 수(up/down/left/right) 하나입니다. 베이스 모델도 PlayJev와 같은
`Qwen3.5-0.8B-Base`(PlayJev 폴더에 받아 둔 로컬 체크포인트)를 쓰고, 언어 모델 부분만 올립니다.

화면 한 장을 넣는 경로는 아래 [이미지 입력](#이미지-입력-playjev-프레임)이다. 이 위의 텍스트 명령은 그대로다.

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
| `prompt.py` | 텍스트 프롬프트 (PlayJev 문구 + 텍스트 state). 문구는 바꾸지 않음 |
| `playjev_prompt.py` | 이미지 plain 프롬프트. PlayJev `model.py` 에서 가져옴 (Apache-2.0) |
| `frame.py` | 보드 → 448px JPEG. 기본 PIL, `--renderer playwright` 는 브라우저 |
| `image_policy.py` | `AutoProcessor` + `AutoModelForImageTextToText`, 글자 슬롯 판독 |
| `train_image.py` | 이미지 LoRA. `train.py --input image` 가 호출 |
| `eval_image.py` | 이미지 평가. `evaluate.py --input image` 가 호출. `results/<run>/eval.json` |
| `gen_data.py` | 전문가 플레이(또는 DAgger) → JSONL. `--input text`(기본) 또는 `image` |
| `lora.py` | 최소 LoRA 구현 (peft 없이). 이미지 어댑터는 비전 타워를 건너뜀 |
| `policy.py` | 텍스트 모델 로딩, 글자 슬롯 판독 (학습/평가 공용) |
| `train.py` | 텍스트 LoRA SFT. `--input image` 이면 이미지 학습 |
| `evaluate.py` | 무작위/전문가/모델 N판 비교. `--input image` 이면 이미지 평가 |
| `requirements.txt` | 이미지 경로에 새로 필요한 Pillow, Playwright 버전 |
| `test_image.py` | CPU 스모크 (프레임, 프롬프트, 텍스트 경로 회귀) |

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

## 이미지 입력 (PlayJev 프레임)

텍스트 경로와 **같은 expectimax soft label**, 같은 DAgger 루프를 쓰고, 입력만 PlayJev 처럼 보드 한 장으로 바꾼다.
같은 `data/clone.jsonl` 로 두 경로를 학습하면 검증 분할(파일 이름 + 시드)이 같다.

한 수에 프레임 하나. 프롬프트는 PlayJev `playjev/model.py` 의 plain 템플릿이다.
`<state>` 안에 `<|vision_start|><|image_pad|><|vision_end|>` 만 있고, 선택지는 합법 수뿐이며
`A. up: ...` 형식이다. 문장은 2048 `pj_hook.js` 의 긴 설명이다 (텍스트 경로의 짧은 문장과 다르다).
끝은 `Answer:` 이고, 판독은 마지막 위치에서 ` A`~` D` 토큰 softmax 다. 학습 때 선택지 순서는 샘플마다 섞는다.

로딩은 `AutoProcessor` + `AutoModelForImageTextToText`. 프롬프트 빌더는 `playjev_prompt.py` 에
PlayJev 코드를 가져와 두었다 (Apache-2.0, `docs/licenses/PlayJev-LICENSE.txt`).

### 프레임을 어떻게 그리는가

PlayJev 는 페이지 전체가 아니라 `pj_hook.js` 의 `canvas()` 로 **500×500 보드만** 그린 뒤,
`pj_shim.js` 의 `frame()` 이 긴 변을 448px 로 줄이고 (비율 유지, 스무딩 켜짐) JPEG 품질 0.85 로 저장한다.
점수와 제목은 프레임에 없다.

**기본값은 PIL** (`--renderer pil`) 이다. 브라우저가 필요 없다.
CSS 타일 색을 칠하고, 이 저장소의 Clear Sans Bold(woff)를 풀어 숫자를 그린 다음, 448px bilinear 축소와
JPEG 0.85 왕복을 한다. 모서리 둥글기와 그림자는 PlayJev 훅도 그리지 않으므로 PIL 도 사각형만 그린다.

PIL 과 브라우저 프레임이 다른 점:

- 칸 간격이 121.25px 라 브라우저 캔버스는 소수 픽셀 경계를 안티앨리어싱한다. PIL 은 정수 픽셀로 맞춘다.
- 글자 래스터라이저가 FreeType 이라 Chromium 과 픽셀이 다르다. 폰트 파일은 같다.
- JPEG 인코더가 Pillow 와 브라우저에서 다르다.

`--renderer playwright` 는 Playwright 로 `docs/games/2048` 을 열고, 가져와 둔
`vendor/pj_shim.js` 와 `vendor/pj_2048_hook.js` 의 `canvas()` / `frame()` 을 부른다.
추가한 것은 `setGrid` 하나다. JS 게임의 RNG 로 판을 다시 두지 않고, 파이썬 보드를 같은 그리기로 칠한다.
글자와 JPEG 는 설치된 Chromium 을 따른다. 학습 기본값으로는 느리다.

```powershell
pip install -r requirements.txt
# playwright 를 쓸 때만
python -m playwright install chromium
```

Qwen3.5 프로세서는 `torchvision` 을 불러온다. 설치된 torch 와 같은 빌드를 쓴다.
PlayJev 스택은 `torch==2.10.0` + `torchvision==0.25.0` (cu128) 이다. 여기 requirements 에는
그 휠을 고정하지 않는다. CPU 휠을 깔면 기존 GPU torch 가 바뀐다.

### 가중치

제로샷 기준선은 [OmniJev/PlayJev-0.8B](https://huggingface.co/OmniJev/PlayJev-0.8B) 다.
이미지 학습의 시작점은 텍스트와 같은 `Qwen/Qwen3.5-0.8B-Base` 다.
`config.py` 의 `MODEL_PATH` 폴더가 이미 있으면 학습은 그 로컬 체크포인트를 쓴다.

```powershell
huggingface-cli download OmniJev/PlayJev-0.8B --local-dir models\PlayJev-0.8B
huggingface-cli download Qwen/Qwen3.5-0.8B-Base --local-dir models\Qwen3.5-0.8B-Base

python -c "from huggingface_hub import snapshot_download; snapshot_download('OmniJev/PlayJev-0.8B', local_dir=r'models\PlayJev-0.8B')"
python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3.5-0.8B-Base', local_dir=r'models\Qwen3.5-0.8B-Base')"
```

### dtype 과 8GB

RTX 2070 SUPER(Turing, sm_75)에는 bf16 텐서코어가 없다. PlayJev 로더는 bfloat16 이지만
여기서는 **float16 가중치 + fp16 autocast + fp32 LoRA + fp32 슬롯 판독**이 기본이다.
`--dtype bfloat16` 이면 PlayJev 와 같은 dtype 으로 올린다. 이 카드에서는 매우 느리다.

0.8B 전체를 미세조정하지 않는다. 언어 모델 Linear 만 LoRA (`lora.py`, 비전 타워의 `q_proj` 는 제외).
비전 타워는 얼리고 출력은 detach 한다. gradient checkpointing 은 기본으로 켜져 있고,
micro batch 1, 유효 배치 8 (`--batch 8`) 이다. `--no-freeze-vision` 이나 `--no-grad-ckpt` 는 메모리가 부족해지기 쉽다.

### 명령

CPU 에서 프레임·프롬프트만 확인 (GPU 학습 없음):

```powershell
python test_image.py
python train.py --input image --dry-run --model Qwen/Qwen3.5-0.8B-Base
```

`--dry-run` / `--smoke` 는 옵티마이저 스텝을 하지 않는다. 프로세서 파일을 받을 수 있으면 한 배치의 shape 을 찍고, 못 받으면 그 사실만 알리고 끝난다.

데이터는 텍스트와 같은 파일이면 된다. `--input image` 로 만들면 `grid` 와 이미지 `messages` 가 더 붙지만, `probs` / `action` / `state` 는 같다.

```powershell
python gen_data.py --episodes 40 --out data\clone.jsonl
```

제로샷 (PlayJev-0.8B, 시드 100000, 100판, 수 상한 3000). 결과 `results\playjev_zeroshot\eval.json`:

```powershell
python evaluate.py --input image --policies model --model models\PlayJev-0.8B --games 100 --max_moves 3000 --seed_base 100000 --run playjev_zeroshot --data data\clone.jsonl
```

`--model` 을 생략하면 허브의 `OmniJev/PlayJev-0.8B` 를 받는다. `--data` 가 있으면 학습과 같은 검증 분할에서 KL(teacher || model) 과 일치율을 같이 적는다. 없으면 판 지표만 나온다.

GPU 에서 아주 짧은 학습 (가중치가 있어야 한다):

```powershell
python gen_data.py --episodes 1 --max_moves 40 --out data\smoke.jsonl
python train.py --input image --data data\smoke.jsonl --out ckpt\image_smoke --model models\Qwen3.5-0.8B-Base --max_steps 2 --limit 8 --micro_batch 1 --batch 2
```

전체 LoRA (micro batch 1, 유효 배치 8, 비전 고정, gradient checkpointing):

```powershell
python train.py --input image --data data\clone.jsonl --out ckpt\image_run1 --model models\Qwen3.5-0.8B-Base
```

로컬 `MODEL_PATH` 가 있으면 `--model` 을 빼도 그 베이스를 쓴다.

텍스트 런과 나란히 보기. 시드·판 수·수 상한을 같게 준다. 무작위/전문가 점수는 같은 시드에서 같다.
텍스트 결과는 예전과 같이 `results\eval_<시각>.json` (또는 `--out`) 이고, 이미지 결과는 `results\<run>\eval.json` 이다.
이미지 쪽에는 평균 점수, 평균 수, 최대 타일 분포, 플레이 중 전문가 일치, 검증 KL 이 들어 있다.

```powershell
python evaluate.py --policies random expert model --adapter ckpt\run1\best --games 100 --max_moves 3000 --seed_base 100000 --agreement --out results\text_run1.json
python evaluate.py --input image --policies random expert model --adapter ckpt\image_run1\best --games 100 --max_moves 3000 --seed_base 100000 --run image_run1 --data data\clone.jsonl
```

이미지 DAgger (모델이 두고 전문가가 라벨):

```powershell
python gen_data.py --input image --episodes 20 --policy model --adapter ckpt\image_run1\best --model models\Qwen3.5-0.8B-Base --eps 0.05 0.05 --seed_base 50000 --out data\dagger_image.jsonl
```

`results/` 는 gitignore 다. GPU 학습, 100판 평가, Playwright Chromium 프레임은 이 저장소를 만든 환경에서 돌리지 않았다.
`python test_image.py` 가 CPU 에서 프레임과 프롬프트를 확인하고, 프로세서를 받을 수 있으면 한 배치도 만든다.
층을 2개로 줄인 무작위 Qwen3.5 로 순전파와 LoRA 역전파(비전 기울기는 없음)까지 CPU 에서 확인했다.
