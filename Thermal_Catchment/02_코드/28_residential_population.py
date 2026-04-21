"""
거주인구 추정 — 생활인구 새벽시간대(01~05시) 평균
=================================================
방법론 출처:
  Shin & Park (2026). An Application of the Grid-Based Two-Step Floating
  Catchment Area Method to Assess the Spatial Accessibility of Green Spaces
  in Seoul, South Korea. ISPRS Int. J. Geo-Inf., 15, x.

  "we calculated the average population between 1:00 AM and 5:00 AM,
   a period when public transportation is generally not in operation"
   → 대중교통 비운행 시간대 = 대부분 자택 체류 → 거주인구 추정치

입력:
  01_데이터/인구/LOCAL_PEOPLE_202507/        — 2025년 7월 일별 생활인구 (집계구 단위)
  01_데이터/인구/LOCAL_PEOPLE_202508/        — 2025년 8월 일별 생활인구 (집계구 단위)
  01_데이터/행정경계/통계지역경계.../집계구.shp  — 집계구 경계

출력 (→ 03_결과물/):
  residential_population.csv   — 집계구별 거주인구 추정치 + 좌표
  residential_population.geojson
"""

import os
import glob
import numpy as np
import pandas as pd
import geopandas as gpd

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)                               # Thermal_Catchment/
DATA_DIR = os.path.join(PROJ_DIR, '01_데이터')
OUT_DIR  = os.path.join(PROJ_DIR, '03_결과물')

POP_DIR7 = os.path.join(DATA_DIR, '인구/LOCAL_PEOPLE_202507')
POP_DIR8 = os.path.join(DATA_DIR, '인구/LOCAL_PEOPLE_202508')
DONG_SHP = os.path.join(DATA_DIR, '행정경계/통계지역경계(2016년+기준)/집계구.shp')

os.makedirs(OUT_DIR, exist_ok=True)

# 성동구 집계구코드 접두사
# 이 데이터셋의 코드 체계: 성동구 = '1104', 동작구 = '1120' (표준코드와 다름)
SEONGDONG_PREFIX = '1104'

# 새벽 시간대 (01:00~05:00) — Shin & Park (2026) 방법
NIGHT_HOURS = [1, 2, 3, 4]   # 시간대구분 1=01시, 2=02시, 3=03시, 4=04시


# ── 1. 생활인구 CSV 로드 (7·8월 전체) ────────────────────────────────────
print("생활인구 데이터 로드 중...")

all_files = sorted(glob.glob(os.path.join(POP_DIR7, '*.csv'))) + \
            sorted(glob.glob(os.path.join(POP_DIR8, '*.csv')))
print(f"  파일 수: {len(all_files)}개 (7월 + 8월)")

dfs = []
for fpath in all_files:
    df = pd.read_csv(fpath, encoding='cp949', dtype={'집계구코드': str})
    # BOM 컬럼명 정리 (첫 컬럼 '?"기준일ID"' → '기준일ID')
    df.columns = [c.replace('?"', '').replace('"', '') if c.startswith('?"') else c
                  for c in df.columns]
    dfs.append(df)

pop_all = pd.concat(dfs, ignore_index=True)
print(f"  전체 행 수: {len(pop_all):,}")

# 성동구 필터
pop_sd = pop_all[pop_all['집계구코드'].str.startswith(SEONGDONG_PREFIX)].copy()
print(f"  성동구 행 수: {len(pop_sd):,}")


# ── 2. 새벽 시간대 필터 → 거주인구 추정 ──────────────────────────────────
print("\n거주인구 추정 (01:00~05:00 평균) — Shin & Park (2026) 방법...")

pop_night = pop_sd[pop_sd['시간대구분'].isin(NIGHT_HOURS)].copy()

# 집계구별 · 날짜별 새벽 평균 먼저 (하루 안에서 01~04시 평균)
pop_daily = (pop_night
             .groupby(['기준일ID', '집계구코드'])['총생활인구수']
             .mean()
             .reset_index()
             .rename(columns={'총생활인구수': 'pop_night_mean'}))

# 전체 기간(7~8월) 평균 → 집계구별 거주인구 추정치
pop_res = (pop_daily
           .groupby('집계구코드')['pop_night_mean']
           .mean()
           .reset_index()
           .rename(columns={'pop_night_mean': 'residential_pop'}))

pop_res['residential_pop'] = pop_res['residential_pop'].round(1)
print(f"  집계구 수: {len(pop_res):,}개")
print(f"  거주인구 합계: {pop_res['residential_pop'].sum():,.0f}명")
print(f"  평균: {pop_res['residential_pop'].mean():.1f}명 / 최대: {pop_res['residential_pop'].max():.1f}명")


# ── 3. 집계구 경계 로드 & 공간 조인 ─────────────────────────────────────
print("\n집계구 경계 로드 중...")
dong_gdf = gpd.read_file(DONG_SHP, encoding='cp949')

# 집계구코드 컬럼 확인
print(f"  컬럼: {dong_gdf.columns.tolist()}")
print(f"  CRS: {dong_gdf.crs}")

# 성동구 필터 (집계구코드 접두사)
# shp의 코드 컬럼명 자동 탐지
code_col = None
for c in dong_gdf.columns:
    sample = str(dong_gdf[c].iloc[0]) if len(dong_gdf) > 0 else ''
    if sample.startswith('11') and len(sample) >= 10:
        code_col = c
        break

if code_col is None:
    # 가능한 컬럼명 후보
    for candidate in ['집계구코드', 'TOT_REG_CD', 'BJDONG_CD', 'ADM_CD']:
        if candidate in dong_gdf.columns:
            code_col = candidate
            break

print(f"  집계구코드 컬럼: {code_col}")
dong_gdf[code_col] = dong_gdf[code_col].astype(str)
dong_sd = dong_gdf[dong_gdf[code_col].str.startswith(SEONGDONG_PREFIX)].copy()
print(f"  성동구 집계구 수: {len(dong_sd):,}개")

# WGS84 변환 후 centroid 계산 (중간 재변환 없이 직접 계산)
if dong_sd.crs is None:
    dong_sd = dong_sd.set_crs(epsg=5179)
dong_sd = dong_sd.to_crs(epsg=4326)
dong_sd['lon'] = dong_sd.geometry.centroid.x
dong_sd['lat'] = dong_sd.geometry.centroid.y
dong_sd = dong_sd.rename(columns={code_col: '집계구코드'})

# 인구 합류
result_gdf = dong_sd.merge(pop_res, on='집계구코드', how='left')
result_gdf['residential_pop'] = result_gdf['residential_pop'].fillna(0)

# 인구 0인 집계구 제거 (Shin & Park 2026: "cells with zero population are masked")
result_gdf = result_gdf[result_gdf['residential_pop'] > 0].copy()
print(f"\n  인구 > 0 집계구: {len(result_gdf):,}개")
print(f"  최종 거주인구 합계: {result_gdf['residential_pop'].sum():,.0f}명")


# ── 4. 저장 ─────────────────────────────────────────────────────────────
out_cols = ['집계구코드', 'residential_pop', 'lon', 'lat', 'geometry']
out_cols = [c for c in out_cols if c in result_gdf.columns]

out_csv = os.path.join(OUT_DIR, 'residential_population.csv')
result_gdf[['집계구코드', 'residential_pop', 'lon', 'lat']].to_csv(
    out_csv, index=False, encoding='utf-8-sig')
print(f"\n저장: {out_csv}")

out_geojson = os.path.join(OUT_DIR, 'residential_population.geojson')
result_gdf[out_cols].to_crs(epsg=4326).to_file(out_geojson, driver='GeoJSON')
print(f"저장: {out_geojson}")

print("\n=== 완료 ===")
print("방법론 참고: Shin & Park (2026) ISPRS IJGI")
print("  → 생활인구 01:00~05:00 평균 = 거주인구 추정치")
print("다음 단계: 29_2sfca_comparison.py 실행")
