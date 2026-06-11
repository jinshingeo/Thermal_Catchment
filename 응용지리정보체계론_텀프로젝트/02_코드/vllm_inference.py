"""
VLLM 배치 추론 — Qwen2-VL-7B, 두 트랙 프롬프트 실행 (v2)
=====================================================
Track 1 (고도화): SOLWEIG 파라미터 추출 → SVF 범주형 + 캐노피
Track 2 (대체):  기상 맥락 + 영상 → MRT 범주 (Low/Moderate/High)

프롬프트 v2 변경사항:
  Track 1: 알베도 제거 / shade_structure → SVF에 통합 / SVF 범주형(Open/Semi/Enclosed)
  Track 2: svf_estimate 연속값 제거 → sky_openness 범주형 / HIGH 기준 단순화

── 코랩 실행 준비 ──────────────────────────────────────────────────────────
!pip install -q transformers accelerate bitsandbytes qwen-vl-utils

from google.colab import drive
drive.mount('/content/drive')

# 드라이브에 이미지 업로드 후 IMG_DIR, META_CSV, OUT_DIR 경로 수정
# 예시:
#   IMG_DIR  = Path("/content/drive/MyDrive/거리영상")
#   META_CSV = Path("/content/drive/MyDrive/kakao_metadata.csv")
#   OUT_DIR  = Path("/content/drive/MyDrive/결과물")
────────────────────────────────────────────────────────────────────────────
"""

import os, json, time, logging, re
from pathlib import Path
import pandas as pd
from PIL import Image
import torch
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig

# ── 경로 설정 (코랩에서는 드라이브 경로로 교체) ───────────────────────────
IMG_DIR  = Path("/Users/jin/이화여대 수업/응용지리정보체계론_텀프로젝트/01_데이터/거리영상")
META_CSV = Path("/Users/jin/이화여대 수업/응용지리정보체계론_텀프로젝트/01_데이터/kakao_metadata.csv")
OUT_DIR  = Path("/Users/jin/이화여대 수업/응용지리정보체계론_텀프로젝트/03_결과물")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 폭염 기간 기상 평균 (S-DoT 성수권역)
HEATWAVE_MET = {
    "tair": 35.8, "rh": 61.0, "wind": 2.4, "ghi": 750.0, "solar_alt": 55.0,
}

MODEL_ID           = "Qwen/Qwen2-VL-7B-Instruct"
DIRECTION_PRIORITY = ["back"]   # 실제 진행 방향 시점 (파일명 라벨 기준)
MAX_NEW_TOKENS     = 1024

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUT_DIR / "vllm_run.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)


# ── 모델 로드 (4-bit 양자화 — T4 16GB 안정 실행) ─────────────────────────
def load_model():
    bnb_cfg = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_cfg,
        device_map="auto",
    )
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    logger.info("모델 로드 완료: %s (4-bit)", MODEL_ID)
    return model, processor


# SVF 범주 → 대표값 매핑 (Oke 1987 H/W 기반)
SVF_MAP = {"open": 0.85, "semi": 0.55, "enclosed": 0.25}

# ── 프롬프트 v2 ───────────────────────────────────────────────────────────
PROMPT_TRACK1 = """You are analyzing a street-level image to extract physical parameters for urban thermal radiation modeling (SOLWEIG framework).

Location: Pedestrian network link in Seongsu-dong / Eungbong-dong, Seoul, South Korea.

Describe what you SEE first, then give your estimate.

Parameter 1: Sky View Factor (SVF)
Include ALL overhead obstructions: buildings, bridges, elevated roads, awnings, AND tree canopy.

Categories (choose one):
  Open     = sky covers more than half the overhead view
             (wide road, park, riverside, one-sided buildings)
  Semi     = buildings or structures on both sides, sky still partially visible
             (typical residential street, narrow road with low buildings)
  Enclosed = overhead view heavily blocked by buildings, bridges, or dense structures
             (dense urban canyon, under overpass, arcade street)

Visual evidence: [what you see overhead and on both sides]
SVF category: [Open / Semi / Enclosed]

Parameter 2: Tree Canopy Coverage over the walkway — 0.0(no trees) to 1.0(complete cover)
Visual evidence: [describe tree density and spread]
Canopy ratio: [0.00–1.00]

Output strictly as JSON (no other text):
{
  "svf_category": "Open or Semi or Enclosed",
  "svf_confidence": "<High|Medium|Low>",
  "svf_evidence": "<one sentence describing overhead view>",
  "canopy_ratio": <float 0.0-1.0>,
  "canopy_confidence": "<High|Medium|Low>",
  "canopy_evidence": "<one sentence describing tree coverage>"
}"""


def make_prompt_track2(met: dict) -> str:
    return f"""You are an urban thermal comfort specialist. Classify the Mean Radiant Temperature (MRT) for a pedestrian at this Seoul street location.

Weather context (heatwave period):
  Tair={met['tair']:.1f}°C | RH={met['rh']:.0f}% | Wind={met['wind']:.1f}m/s | GHI={met['ghi']:.0f}W/m²

Key principle: At GHI={met['ghi']:.0f}W/m², any walking path WITHOUT shade will exceed MRT 55°C (Hard Cut threshold).
The primary question is: IS THE WALKING PATH SHADED?

MRT Categories:
  High     (MRT ≥ 55°C): Direct sun reaches the walking path — no effective shade from any source
  Moderate (45–55°C)   : Intermittent sun and shade — partial coverage by trees, buildings, or structures
  Low      (< 45°C)    : Walking path continuously in shade — consistently covered

Step 1 — Observe: sky openness, shade sources (trees/buildings/structures), surface type
Step 2 — Assess: Does direct sunlight reach where a pedestrian walks?
Step 3 — Classify MRT category

Output strictly as JSON (no other text):
{{
  "mrt_category": "<Low|Moderate|High>",
  "confidence": "<High|Medium|Low>",
  "solar_exposure": "<Direct|Partial|Shaded>",
  "sky_openness": "<open|semi|enclosed>",
  "shading_source": "<none|tree|building|structure|mixed>",
  "key_observations": ["<obs1>", "<obs2>"],
  "reasoning": "<one sentence>"
}}"""


# ── 추론 ──────────────────────────────────────────────────────────────────
def infer(model, processor, prompt: str, img_path: Path) -> dict | None:
    image = Image.open(img_path).convert("RGB")
    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "image": image},
            {"type": "text",  "text": prompt},
        ],
    }]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=[text], images=[image], return_tensors="pt").to(model.device)

    with torch.no_grad():
        out_ids = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)

    generated = out_ids[0][inputs["input_ids"].shape[1]:]
    raw = processor.decode(generated, skip_special_tokens=True).strip()

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        logger.warning("JSON 파싱 실패:\n%s", raw[:200])
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        logger.warning("JSON 디코드 실패:\n%s", match.group()[:200])
        return None


def find_image(u: str, v: str) -> Path | None:
    for d in DIRECTION_PRIORITY:
        p = IMG_DIR / f"{u}_{v}_{d}.jpg"
        if p.exists():
            return p
    return None


# ── 메인 ──────────────────────────────────────────────────────────────────
def run(track: int = 2, limit: int | None = None):
    model, processor = load_model()

    meta  = pd.read_csv(META_CSV)
    links = meta[meta["downloaded"] == True].copy()
    if limit:
        links = links.head(limit)

    out_path  = OUT_DIR / f"vllm_track{track}_results.jsonl"
    done_keys = set()
    if out_path.exists():
        with open(out_path) as f:
            for line in f:
                r = json.loads(line)
                done_keys.add((str(r["u"]), str(r["v"])))
        logger.info("이미 완료: %d링크 — 이어서 진행", len(done_keys))

    prompt_fn = (lambda: PROMPT_TRACK1) if track == 1 else (lambda: make_prompt_track2(HEATWAVE_MET))
    n_success = n_skip = n_fail = 0

    with open(out_path, "a", encoding="utf-8") as fout:
        for _, row in links.iterrows():
            u, v = str(row["u"]), str(row["v"])
            if (u, v) in done_keys:
                n_skip += 1
                continue

            img = find_image(u, v)
            if img is None:
                logger.warning("이미지 없음: u=%s v=%s", u, v)
                n_fail += 1
                continue

            result = infer(model, processor, prompt_fn(), img)
            record = {"u": u, "v": v, "img": img.name, "track": track}
            if result:
                record.update(result)
                n_success += 1
            else:
                record["error"] = "parse_fail"
                n_fail += 1

            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            fout.flush()

            total = n_success + n_fail
            if total % 50 == 0:
                logger.info("[%d/%d] 성공=%d 실패=%d 스킵=%d",
                            total, len(links), n_success, n_fail, n_skip)

    logger.info("=== Track %d 완료 === 성공=%d 실패=%d 스킵=%d", track, n_success, n_fail, n_skip)
    logger.info("결과: %s", out_path)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--track", type=int, default=2, choices=[1, 2])
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()
    run(track=args.track, limit=args.limit)
