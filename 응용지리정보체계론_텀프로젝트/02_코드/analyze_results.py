"""
VLLM 배치 결과 후처리 — Track 1 SOLWEIG MRT 산출 + Track 2 비교
=================================================================
Track 1: vllm svf_category → SVF 수치 → SOLWEIG 공식 → MRT
         → 석사논문 SOLWEIG MRT와 MAE / 상관계수 비교

Track 2: vllm mrt_category (Low/Moderate/High)
         → 석사논문 MRT를 동일 범주로 변환해 Accuracy / Recall(High) 비교

SOLWEIG 공식 출처: 석사논문 39_utci_sdot_solweig.py (thesis와 동일 구현)
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import (
    mean_absolute_error, accuracy_score,
    classification_report, confusion_matrix,
)

# ── 경로 ──────────────────────────────────────────────────────────────────
BASE       = Path("/Users/jin/이화여대 수업/응용지리정보체계론_텀프로젝트")
VLLM_T1    = BASE / "03_결과물/vllm_track1_results.jsonl"
VLLM_T2    = BASE / "03_결과물/vllm_track2_results.jsonl"
THESIS_MRT = Path("/Users/jin/석사논문/TAVI/Thermal_Catchment/03_결과물/link_utci_sdot_solweig.csv")
OUT_DIR    = BASE / "03_결과물"

# ── SOLWEIG 물리 상수 (thesis 39_utci_sdot_solweig.py와 동일) ─────────────
ALPHA_K      = 0.70
EPSILON_P    = 0.97
FP           = 0.308
SIGMA        = 5.67e-8
EPSILON_WALL = 0.90
DELTA_T_WALL = 10.0

# ── 폭염 기간 고정 기상값 (HEATWAVE_MET, 13시 기준) ──────────────────────
TAIR  = 35.8
GHI   = 750.0
RH    = 61.0
COS_Z = float(np.sin(np.radians(55.0)))  # solar_alt=55° → cos(zenith)=sin(alt)

# ── SVF 범주 → 수치 매핑 (Oke 1987 기반) ─────────────────────────────────
SVF_MAP = {"open": 0.85, "semi": 0.55, "enclosed": 0.25}


def mrt_to_cat(mrt: float) -> str:
    if mrt < 45:  return "Low"
    if mrt < 55:  return "Moderate"
    return "High"


def split_radiation(ghi: float, cos_z: float):
    """Erbs et al. (1982) 직산 분리 — thesis와 동일"""
    if ghi <= 10 or cos_z < 0.01:
        return 0.0, float(ghi)
    kt = min(ghi / (1367.0 * cos_z), 1.0)
    if kt <= 0.22:
        kd = 1.0 - 0.09 * kt
    elif kt <= 0.80:
        kd = max(0.9511 - 0.1604*kt + 4.388*kt**2
                 - 16.638*kt**3 + 12.336*kt**4, 0.1)
    else:
        kd = 0.165
    return float(ghi * (1 - kd)), float(ghi * kd)


def compute_mrt(tair: float, ghi: float, rh: float, svf: float, cos_z: float) -> float:
    """SOLWEIG MRT — thesis 39_utci_sdot_solweig.py compute_mrt()와 동일"""
    tair_k  = tair + 273.15
    k_dir, k_dif = split_radiation(ghi, cos_z)
    k_abs   = k_dir * FP + k_dif * svf * 0.5
    ea      = (rh / 100.0) * 6.112 * np.exp(17.67 * tair / (tair + 243.5))
    eps_sky = float(np.clip(0.575 * ea ** (1.0 / 7.0), 0.70, 1.00))
    l_sky   = eps_sky * SIGMA * tair_k ** 4
    dt      = DELTA_T_WALL if ghi > 50 else 0.0
    l_wall  = EPSILON_WALL * SIGMA * (tair_k + dt) ** 4
    l_mean  = l_sky * svf + l_wall * (1.0 - svf)
    mrt_k   = ((ALPHA_K * k_abs + l_mean) / (EPSILON_P * SIGMA)) ** 0.25
    return float(mrt_k - 273.15)


def load_jsonl(path: Path) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return pd.DataFrame(rows)


# ── 석사논문 MRT 로드 (13시 평균) ─────────────────────────────────────────
def load_thesis_mrt() -> pd.DataFrame:
    df = pd.read_csv(THESIS_MRT, encoding="utf-8-sig")
    df13 = df[df["hour"] == 13].copy()
    df13["u"] = df13["u"].astype(str)
    df13["v"] = df13["v"].astype(str)
    return df13[["u", "v", "svf", "mrt"]].rename(
        columns={"svf": "thesis_svf", "mrt": "thesis_mrt"}
    )


# ── Track 1 분석 ─────────────────────────────────────────────────────────
def analyze_track1(thesis: pd.DataFrame):
    print("\n" + "="*60)
    print("TRACK 1 — VLLM SVF → SOLWEIG MRT vs 석사논문 MRT")
    print("="*60)

    t1 = load_jsonl(VLLM_T1)
    t1["u"] = t1["u"].astype(str)
    t1["v"] = t1["v"].astype(str)

    # SVF 범주 → 수치
    t1["vllm_svf"] = t1["svf_category"].str.lower().map(SVF_MAP)
    t1 = t1.dropna(subset=["vllm_svf"])

    # SOLWEIG MRT 산출 (고정 기상값)
    t1["vllm_mrt"] = t1["vllm_svf"].apply(
        lambda svf: compute_mrt(TAIR, GHI, RH, svf, COS_Z)
    )
    t1["vllm_mrt_cat"] = t1["vllm_mrt"].apply(mrt_to_cat)

    # thesis 조인
    merged = t1.merge(thesis, on=["u", "v"], how="inner")
    merged["thesis_mrt_cat"] = merged["thesis_mrt"].apply(mrt_to_cat)

    print(f"\n매칭 링크 수: {len(merged):,}개 / 전체 VLLM T1 {len(t1):,}개")

    # SVF 비교
    print("\n[SVF 비교]")
    mae_svf = mean_absolute_error(merged["thesis_svf"], merged["vllm_svf"])
    corr_svf = merged[["thesis_svf", "vllm_svf"]].corr().iloc[0, 1]
    print(f"  MAE(SVF):  {mae_svf:.4f}")
    print(f"  Corr(SVF): {corr_svf:.4f}")
    print(f"  VLLM SVF 분포: {merged['vllm_svf'].value_counts().to_dict()}")

    # MRT 비교
    print("\n[MRT 비교]")
    mae_mrt = mean_absolute_error(merged["thesis_mrt"], merged["vllm_mrt"])
    corr_mrt = merged[["thesis_mrt", "vllm_mrt"]].corr().iloc[0, 1]
    print(f"  VLLM MRT 범위: {merged['vllm_mrt'].min():.1f}~{merged['vllm_mrt'].max():.1f}°C  "
          f"(고정값이므로 3개 값만 존재)")
    print(f"  논문 MRT 범위: {merged['thesis_mrt'].min():.1f}~{merged['thesis_mrt'].max():.1f}°C")
    print(f"  MAE(MRT):  {mae_mrt:.2f}°C")
    print(f"  Corr(MRT): {corr_mrt:.4f}")

    # 범주 정확도
    acc = accuracy_score(merged["thesis_mrt_cat"], merged["vllm_mrt_cat"])
    print(f"\n[MRT 범주 Accuracy]: {acc:.3f}")
    print(classification_report(
        merged["thesis_mrt_cat"], merged["vllm_mrt_cat"],
        labels=["Low", "Moderate", "High"], zero_division=0
    ))

    # Hard Cut (MRT≥55°C) 탐지
    print("[Hard Cut (MRT≥55°C) 탐지]")
    n_true_high = (merged["thesis_mrt_cat"] == "High").sum()
    n_pred_high = (merged["vllm_mrt_cat"] == "High").sum()
    n_hit       = ((merged["thesis_mrt_cat"] == "High") & (merged["vllm_mrt_cat"] == "High")).sum()
    recall_high = n_hit / n_true_high if n_true_high > 0 else 0
    print(f"  논문 High: {n_true_high}개 | VLLM High: {n_pred_high}개 | 일치: {n_hit}개")
    print(f"  Hard Cut Recall: {recall_high:.3f}")

    # SVF 범주별 MRT 오차
    print("\n[SVF 범주별 MRT MAE]")
    for cat in ["Open", "Semi", "Enclosed"]:
        sub = merged[merged["svf_category"].str.lower() == cat.lower()]
        if len(sub) == 0:
            continue
        mae = mean_absolute_error(sub["thesis_mrt"], sub["vllm_mrt"])
        print(f"  {cat:10s}: n={len(sub):4d}  MAE={mae:.2f}°C  "
              f"논문MRT 평균={sub['thesis_mrt'].mean():.1f}°C")

    # 저장
    out = OUT_DIR / "track1_comparison.csv"
    merged.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n저장: {out}")
    return merged


# ── Track 2 분석 ─────────────────────────────────────────────────────────
def analyze_track2(thesis: pd.DataFrame):
    print("\n" + "="*60)
    print("TRACK 2 — VLLM mrt_category vs 석사논문 MRT 범주")
    print("="*60)

    t2 = load_jsonl(VLLM_T2)
    t2["u"] = t2["u"].astype(str)
    t2["v"] = t2["v"].astype(str)
    t2 = t2.dropna(subset=["mrt_category"])
    t2["vllm_mrt_cat"] = t2["mrt_category"].str.capitalize()

    merged = t2.merge(thesis, on=["u", "v"], how="inner")
    merged["thesis_mrt_cat"] = merged["thesis_mrt"].apply(mrt_to_cat)

    print(f"\n매칭 링크 수: {len(merged):,}개 / 전체 VLLM T2 {len(t2):,}개")

    acc = accuracy_score(merged["thesis_mrt_cat"], merged["vllm_mrt_cat"])
    print(f"\n[MRT 범주 Accuracy]: {acc:.3f}")
    print(classification_report(
        merged["thesis_mrt_cat"], merged["vllm_mrt_cat"],
        labels=["Low", "Moderate", "High"], zero_division=0
    ))

    print("[Confusion Matrix]  (행=논문, 열=VLLM)")
    labels = ["Low", "Moderate", "High"]
    cm = confusion_matrix(merged["thesis_mrt_cat"], merged["vllm_mrt_cat"], labels=labels)
    cm_df = pd.DataFrame(cm, index=labels, columns=labels)
    print(cm_df.to_string())

    print("\n[Hard Cut (MRT≥55°C) 탐지]")
    n_true = (merged["thesis_mrt_cat"] == "High").sum()
    n_pred = (merged["vllm_mrt_cat"] == "High").sum()
    n_hit  = ((merged["thesis_mrt_cat"] == "High") & (merged["vllm_mrt_cat"] == "High")).sum()
    recall = n_hit / n_true if n_true > 0 else 0
    prec   = n_hit / n_pred if n_pred > 0 else 0
    print(f"  논문 High: {n_true}개 | VLLM High: {n_pred}개 | 일치: {n_hit}개")
    print(f"  Hard Cut Recall: {recall:.3f}  Precision: {prec:.3f}")

    out = OUT_DIR / "track2_comparison.csv"
    merged.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n저장: {out}")
    return merged


# ── 메인 ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    thesis = load_thesis_mrt()
    print(f"석사논문 MRT 로드: {len(thesis):,}링크 (13시)")

    results = {}
    if VLLM_T1.exists():
        results["track1"] = analyze_track1(thesis)
    else:
        print(f"\n[SKIP] Track 1 결과 없음: {VLLM_T1}")

    if VLLM_T2.exists():
        results["track2"] = analyze_track2(thesis)
    else:
        print(f"\n[SKIP] Track 2 결과 없음: {VLLM_T2}")

    print("\n\n" + "="*60)
    print("완료. 결과 파일:")
    for f in ["track1_comparison.csv", "track2_comparison.csv"]:
        p = OUT_DIR / f
        if p.exists():
            print(f"  {p}")
