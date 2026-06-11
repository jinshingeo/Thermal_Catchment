"""
파일럿 테스트 — Track 1 & 2 (v2 프롬프트), 8종 테스트 케이스
mlx-vlm + Qwen2-VL-7B-Instruct-4bit (Apple Silicon 네이티브)

실행: python pilot_test.py
결과: 03_결과물/pilot_8cases.json  (구조화 저장)
"""

import json, re
from pathlib import Path
from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config

MODEL   = "mlx-community/Qwen2-VL-7B-Instruct-4bit"
IMG_DIR = Path("/Users/jin/이화여대 수업/응용지리정보체계론_텀프로젝트/01_데이터/거리영상")
OUT_DIR = Path("/Users/jin/이화여대 수업/응용지리정보체계론_텀프로젝트/03_결과물")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SVF_MAP      = {"open": 0.85, "semi": 0.55, "enclosed": 0.25}
HEATWAVE_MET = {"tair": 35.8, "rh": 61, "wind": 2.4, "ghi": 750}

# ── 8종 테스트 케이스 (워드 문서 확정 파일명) ─────────────────────────────
# thesis: 석사 논문 SOLWEIG 산출값 / expected: 이 연구의 기대 분류
TEST_CASES = [
    {
        "no": 1, "title": "완전 개활지",
        "filename": "287287152_4081270724_front.jpg",
        "thesis":   {"svf": 0.904, "canopy": 0.006, "mrt": 58.8, "hw": "primary"},
        "expected": {"svf_cat": "Open", "mrt_cat": "High"},
        "note": "기본 정확도 — 논문·VLLM 일치 기대",
    },
    {
        "no": 2, "title": "수목 밀집 가로수길",
        "filename": "13070402056_13070402072_front.jpg",
        "thesis":   {"svf": 0.599, "canopy": 0.041, "mrt": 54.3, "hw": "primary"},
        "expected": {"svf_cat": "Semi", "mrt_cat": "Moderate"},
        "note": "캐노피 인식 — canopy_ratio 논문 대비 확인",
    },
    {
        "no": 3, "title": "고층 건물 협곡",
        "filename": "3856575393_4652841532_front.jpg",
        "thesis":   {"svf": 0.351, "canopy": 0.045, "mrt": 50.1, "hw": "residential"},
        "expected": {"svf_cat": "Enclosed", "mrt_cat": "Low"},
        "note": "도시 협곡 인식 — 논문·VLLM 일치 기대",
    },
    {
        "no": 4, "title": "고가도로·교각 아래",
        "filename": "287287152_7838649559_front.jpg",
        "thesis":   {"svf": 0.223, "canopy": 0.218, "mrt": 48.9, "hw": "secondary_link"},
        "expected": {"svf_cat": "Enclosed", "mrt_cat": "Low"},
        "note": "핵심케이스 — 고가 구조물을 VLLM이 포착하는지 확인",
    },
    {
        "no": 5, "title": "일반 주거 골목",
        "filename": "4179264033_3846735363_front.jpg",
        "thesis":   {"svf": None, "canopy": None, "mrt": 55.0, "hw": "footway"},
        "expected": {"svf_cat": "Semi", "mrt_cat": "Moderate"},
        "note": "Semi 분별력 — 중간 케이스 올바른 분류 확인",
    },
    {
        "no": 6, "title": "아케이드·캐노피형 상가",
        "filename": "436839040_4179354303_back.jpg",
        "thesis":   {"svf": 0.815, "canopy": 0.003, "mrt": 57.3, "hw": "tertiary"},
        "expected": {"svf_cat": "Enclosed", "mrt_cat": "Low"},
        "note": "핵심케이스 — 논문 SVF=0.815(개활지) vs VLLM 인공그늘 인식",
    },
    {
        "no": 7, "title": "넓은 도로+한쪽만 건물",
        "filename": "732242060_4179011702_front.jpg",
        "thesis":   {"svf": 0.503, "canopy": 0.051, "mrt": 52.9, "hw": "primary"},
        "expected": {"svf_cat": "Open", "mrt_cat": "Moderate"},
        "note": "비대칭 캐니언 — H/W 과소추정 테스트",
    },
    {
        "no": 8, "title": "수목+건물 혼합 그늘",
        "filename": "3856575251_3856575248_front.jpg",
        "thesis":   {"svf": None, "canopy": None, "mrt": 54.4, "hw": "footway"},
        "expected": {"svf_cat": "Semi", "mrt_cat": "Moderate"},
        "note": "혼합 그늘 — shading_source=mixed 및 Moderate 분류 확인",
    },
]

# ── 프롬프트 v2 ───────────────────────────────────────────────────────────
PROMPT_T1 = """You are analyzing a street-level image to extract physical parameters for urban thermal radiation modeling (SOLWEIG framework).

Location: Seoul, South Korea. Daytime street image.

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

Respond with ONLY a JSON object:
{
  "svf_category": "Open or Semi or Enclosed",
  "svf_confidence": "High or Medium or Low",
  "svf_evidence": "one sentence describing overhead view",
  "canopy_ratio": <float 0.0-1.0>,
  "canopy_confidence": "High or Medium or Low",
  "canopy_evidence": "one sentence describing tree coverage"
}"""

PROMPT_T2 = """You are an urban thermal comfort specialist. Classify the Mean Radiant Temperature (MRT) for a pedestrian at this Seoul street location.

Weather context (heatwave period):
  Tair={tair}°C | RH={rh}% | Wind={wind}m/s | GHI={ghi}W/m²

Key principle: At GHI={ghi}W/m², any walking path WITHOUT shade will exceed MRT 55°C (Hard Cut threshold).
The primary question is: IS THE WALKING PATH SHADED?

MRT Categories:
  High     (MRT ≥ 55°C): Direct sun reaches the walking path — no effective shade from any source
  Moderate (45–55°C)   : Intermittent sun and shade — partial coverage by trees, buildings, or structures
  Low      (< 45°C)    : Walking path continuously in shade — consistently covered

Step 1 — Observe: sky openness, shade sources (trees/buildings/structures), surface type
Step 2 — Assess: Does direct sunlight reach where a pedestrian walks?
Step 3 — Classify MRT category

Respond with ONLY a JSON object:
{{
  "mrt_category": "Low or Moderate or High",
  "confidence": "High or Medium or Low",
  "solar_exposure": "Direct or Partial or Shaded",
  "sky_openness": "open or semi or enclosed",
  "shading_source": "none or tree or building or structure or mixed",
  "key_observations": ["obs1", "obs2"],
  "reasoning": "one sentence"
}}"""


def parse_json(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def infer(model, processor, config, prompt: str, img_path: Path) -> dict | None:
    formatted = apply_chat_template(processor, config, prompt, num_images=1)
    output = generate(model, processor, formatted, [str(img_path)], max_tokens=700, verbose=False)
    raw = output.text if hasattr(output, "text") else str(output)
    return parse_json(raw), raw


def run_case(model, processor, config, case: dict) -> dict:
    img_path = IMG_DIR / case["filename"]
    if not img_path.exists():
        return {"error": f"이미지 없음: {case['filename']}"}

    t1_result, t1_raw = infer(model, processor, config, PROMPT_T1, img_path)
    t2_prompt = PROMPT_T2.format(**HEATWAVE_MET)
    t2_result, t2_raw = infer(model, processor, config, t2_prompt, img_path)

    return {
        "track1": t1_result or {"error": "parse_fail", "raw": t1_raw[:150]},
        "track2": t2_result or {"error": "parse_fail", "raw": t2_raw[:150]},
    }


def print_case(case: dict, res: dict):
    t = case["thesis"]
    print(f"\n{'='*65}")
    print(f"케이스 {case['no']}: {case['title']}")
    print(f"파일: {case['filename']}")
    t_svf = f"{t['svf']:.3f}" if t["svf"] is not None else "N/A"
    t_can = f"{t['canopy']:.3f}" if t["canopy"] is not None else "N/A"
    print(f"[논문]  SVF={t_svf}  canopy={t_can}  MRT={t['mrt']}°C  hw={t['hw']}")
    print(f"[기대]  SVF≈{case['expected']['svf_cat']}  MRT≈{case['expected']['mrt_cat']}")

    r1 = res.get("track1", {})
    if "svf_category" in r1:
        svf_num = SVF_MAP.get(r1["svf_category"].lower(), "?")
        print(f"[T1]    SVF={r1['svf_category']}({svf_num})  canopy={r1.get('canopy_ratio','?')}  conf={r1.get('svf_confidence','?')}")
        print(f"        {r1.get('svf_evidence','')}")
    else:
        print(f"[T1]    오류: {r1}")

    r2 = res.get("track2", {})
    if "mrt_category" in r2:
        print(f"[T2]    MRT={r2['mrt_category']}  exposure={r2.get('solar_exposure','?')}  shade={r2.get('shading_source','?')}  sky={r2.get('sky_openness','?')}")
        print(f"        {r2.get('reasoning','')}")
    else:
        print(f"[T2]    오류: {r2}")

    print(f"[비고]  {case['note']}")


def print_summary(all_data: list):
    print(f"\n\n{'='*65}")
    print("=== 8종 케이스 종합 비교 ===")
    header = f"{'No':>3}  {'제목':<18}  {'논문SVF':>7}  {'VLLM_SVF':>10}  {'논문MRT':>7}  {'VLLM_MRT':>9}  {'일치':>4}"
    print(header)
    print("-" * 65)

    for item in all_data:
        c, r = item["case"], item["results"]
        t = c["thesis"]
        t_svf = f"{t['svf']:.3f}" if t["svf"] is not None else "N/A"
        t_mrt = f"{t['mrt']:.1f}" if t["mrt"] is not None else "N/A"

        r1 = r.get("track1", {})
        r2 = r.get("track2", {})
        svf_cat = r1.get("svf_category", "?")
        svf_num = SVF_MAP.get(svf_cat.lower(), "?")
        v_svf = f"{svf_cat}({svf_num})" if svf_num != "?" else "?"
        v_mrt = r2.get("mrt_category", "?")

        exp_mrt = c["expected"]["mrt_cat"]
        match = "✅" if v_mrt.lower() == exp_mrt.lower() else "⚠️"
        print(f"{c['no']:>3}  {c['title'][:16]:<18}  {t_svf:>7}  {v_svf:>10}  {t_mrt:>7}  {v_mrt:>9}  {match:>4}")


def main():
    print(f"모델 로드 중: {MODEL}")
    model, processor = load(MODEL)
    config = load_config(MODEL)

    all_data = []
    for case in TEST_CASES:
        print(f"\n[{case['no']}/8] 추론 중: {case['title']}  ({case['filename']})")
        results = run_case(model, processor, config, case)
        print_case(case, results)
        all_data.append({"case": case, "results": results})

    print_summary(all_data)

    out_path = OUT_DIR / "pilot_8cases.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")


if __name__ == "__main__":
    main()
