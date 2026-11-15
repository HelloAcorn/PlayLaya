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
