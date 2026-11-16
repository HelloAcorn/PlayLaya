"""모든 설정값을 한 곳에 둡니다. 커맨드라인 인자로 대부분 덮어쓸 수 있어요."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ---- 베이스 모델 (PlayJev가 받아 둔 로컬 체크포인트, 텍스트 경로만 씀)
MODEL_PATH = r"C:\workspace\PlayJev\models\Qwen3.5-0.8B-Base"
DEVICE = "cuda:0"
DTYPE = "float16"          # RTX 2070 SUPER(Turing)는 bf16이 매우 느림. PlayJev plan.md 측정과 같음

# ---- 경로
DATA_DIR = ROOT / "data"
CKPT_DIR = ROOT / "ckpt"
RESULTS_DIR = ROOT / "results"

# ---- 데이터 생성 (전문가 = expectimax)
TRAIN_EPISODES = 40        # 에피소드당 약 1천~2천 수 -> 4만~8만 샘플
TRAIN_SEED_BASE = 0
EVAL_SEED_BASE = 100_000   # 평가 시드는 학습 시드와 겹치지 않게
EPS_RANDOM = (0.02, 0.30)  # 에피소드마다 이 범위에서 무작위 수 비율을 뽑음 (PlayJev clone 라운드와 같은 발상)
MAX_MOVES = 5000
EXPERT_DEPTH = 2           # 플레이어 수 깊이 (수, 스폰, 수, 휴리스틱)
EXPERT_DEEP_EMPTY = 4      # 빈칸이 이 이하일 때 한 단계 더 탐색
EXPERT_TEMPERATURE = 1200.0  # 루트 수 가치에 대한 softmax 온도 -> soft target
VAL_FRACTION = 0.05        # 에피소드 단위로 검증셋 분리

# ---- LoRA
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LORA_TARGETS = ("q_proj", "k_proj", "v_proj", "o_proj",       # full attention 층
                "in_proj_qkv", "in_proj_z", "out_proj",       # linear attention(gated delta) 층
                "gate_proj", "up_proj", "down_proj")          # MLP

# ---- 학습
EPOCHS = 1
LR = 2e-4
BATCH = 32                 # 유효 배치
MICRO_BATCH = 8            # GPU 한 번에 올리는 배치 (8GB 카드 기준)
WARMUP = 0.03
WEIGHT_DECAY = 0.0
GRAD_CKPT = False
EVAL_EVERY = 200           # optimizer step 단위
EVAL_SAMPLES = 512
MAX_LEN = 512
SEED = 0

# ---- 평가
EVAL_GAMES = 16
EVAL_MAX_MOVES = 3000
EVAL_BATCH = 16

# ---- 이미지 경로 (텍스트 기본값은 위와 같다. --input image 일 때만 씀)
# PlayJev-0.8B 는 제로샷 기준선. 학습은 텍스트와 같이 Qwen3.5-0.8B-Base 에서 시작한다.
# MODEL_PATH 가 로컬에 있으면 그 체크포인트를 쓰고, 없으면 허깅페이스 id 를 받는다.
IMAGE_BASE_MODEL = "Qwen/Qwen3.5-0.8B-Base"
PLAYJEV_MODEL = "OmniJev/PlayJev-0.8B"
# RTX 2070 SUPER(Turing, sm_75)에는 bf16 텐서코어가 없다. PlayJev 로더는 bfloat16 이지만
# 이 카드에서는 fp16 가중치 + fp16 autocast + fp32 LoRA 가 맞다. --dtype bfloat16 으로 되돌릴 수 있다.
IMAGE_DTYPE = "float16"
IMAGE_RENDERER = "pil"       # pil(기본, 빠름) | playwright(브라우저 canvas)
FRAME_LONG_SIDE = 448        # pj_shim.js frameSize. 긴 변, 비율 유지
JPEG_QUALITY = 85            # pj_shim.js frameQuality 0.85
IMAGE_MICRO_BATCH = 1
IMAGE_BATCH = 8
IMAGE_EVAL_BATCH = 1
IMAGE_EVAL_GAMES = 100       # 텍스트 평가 기본 16판은 그대로. 이미지 비교만 100판
IMAGE_MAX_LEN = 1024         # 448 프레임의 시각 토큰 + plain 프롬프트. 정답 슬롯이 잘리면 안 됨

# ---- 베이스 모델 이미지 런 (run_base_image.py). train.py --input image 만 치면 10판 평가는 꺼져 있다.
BASE_EPISODES = 60             # 상한. 버킷이 차면 그 전에 멈춘다.
BASE_TARGET_STATES = 8000
BASE_BUCKET_CAP = 2000         # <=128, 256, 512, >=1024 각각. 합이 target 과 같다.
BASE_EPS = 0.02
BASE_GEN_MAX_MOVES = 5000      # 1024 구간을 채우려고 평가 수 상한(3000)보다 길다
BASE_EVAL_MAX_MOVES = 3000
BASE_EVAL_GAMES = 10
BASE_EVAL_SEED_BASE = 100_000  # 100000..100009. 학습 시드(0부터)와 안 겹친다
BASE_GAME_EVAL_EVERY = 100     # 10판이 약 5분. 100 optimizer step 마다 한 번.
BASE_MAX_STEPS = 2000          # 8천 샘플, 유효 배치 8 이면 에폭당 약 950 step. 두 에폭 남짓.
BASE_OVERFIT_LIMIT = 1000
BASE_OVERFIT_STEPS = 400       # 1천 샘플, 배치 8 이면 에폭당 125 step. 약 3 에폭.
BASE_OVERFIT_FACTOR = 0.6      # 마지막 손실이 mean(log n_legal) 의 이 배수보다 낮아야 본학습
BASE_KL_PATIENCE = 4
BASE_SCORE_PATIENCE = 2
BASE_SCORE_DROP = 0.30
BASE_SEED_BASE = 0
