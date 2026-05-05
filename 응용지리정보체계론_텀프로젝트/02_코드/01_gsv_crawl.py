"""
GSV 크롤링 — 성동구 보행 네트워크 링크별 4방향 이미지 수집
- 링크 중심점 좌표 추출 (OSM graphml)
- GSV Metadata API로 여름(6~8월) 이미지 필터링
- 4방향(0°·90°·180°·270°) 이미지 다운로드
- 저장: 01_데이터/거리영상/{u}_{v}_{heading}.jpg
"""

import os
import time
import json
import requests
import osmnx as ox
import pandas as pd
from shapely.geometry import LineString

# ── 설정 ──────────────────────────────────────────────────────────────────────
API_KEY    = "YOUR_API_KEY"   # 본인 Google Maps API 키 입력
NET_PATH   = "/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml"
OUT_DIR    = "/Users/jin/석사논문/TAVI/응용지리정보체계론_텀프로젝트/01_데이터/거리영상"
META_CSV   = "/Users/jin/석사논문/TAVI/응용지리정보체계론_텀프로젝트/01_데이터/gsv_metadata.csv"

HEADINGS       = [0, 90, 180, 270]
IMG_SIZE       = "640x640"
FOV            = 90
PITCH          = 0
SUMMER_MONTHS  = {"08"}   # 8월 — 폭염 피크 + 수목 완전 성장
SLEEP_SEC      = 0.05   # API 호출 간격 (초)

META_URL  = "https://maps.googleapis.com/maps/api/streetview/metadata"
IMAGE_URL = "https://maps.googleapis.com/maps/api/streetview"

os.makedirs(OUT_DIR, exist_ok=True)

# ── 네트워크 로드 & 링크 중심점 추출 ──────────────────────────────────────────
print("네트워크 로드 중...")
G = ox.load_graphml(NET_PATH)
nodes_gdf, edges_gdf = ox.graph_to_gdfs(G)

# 링크 중심점 (WGS84)
edges_gdf = edges_gdf.to_crs(epsg=4326)
edges_gdf["center"] = edges_gdf.geometry.interpolate(0.5, normalized=True)
edges_gdf["lat"] = edges_gdf["center"].y
edges_gdf["lon"] = edges_gdf["center"].x

links = edges_gdf.reset_index()[["u", "v", "lat", "lon"]]
print(f"총 링크 수: {len(links)}")

# ── 기존 메타데이터 로드 (재시작 지원) ────────────────────────────────────────
if os.path.exists(META_CSV):
    done_df   = pd.read_csv(META_CSV)
    done_keys = set(zip(done_df["u"], done_df["v"]))
    print(f"이미 완료된 링크: {len(done_keys)}개 — 이어서 진행")
else:
    done_df   = pd.DataFrame()
    done_keys = set()

# ── 크롤링 ────────────────────────────────────────────────────────────────────
records = []

for _, row in links.iterrows():
    u, v, lat, lon = int(row["u"]), int(row["v"]), row["lat"], row["lon"]

    if (u, v) in done_keys:
        continue

    # 1) Metadata API — 이미지 존재 여부 + 촬영 날짜 확인
    meta_params = {"location": f"{lat},{lon}", "key": API_KEY}
    meta_r = requests.get(META_URL, params=meta_params, timeout=10)
    meta   = meta_r.json()
    time.sleep(SLEEP_SEC)

    status = meta.get("status", "")
    date   = meta.get("date", "")          # "YYYY-MM" 형식
    pano   = meta.get("pano_id", "")
    month  = date.split("-")[1] if "-" in date else ""

    rec = {"u": u, "v": v, "lat": lat, "lon": lon,
           "status": status, "date": date, "pano_id": pano,
           "summer": month in SUMMER_MONTHS, "downloaded": False}

    # 여름 이미지 아니면 메타데이터만 기록하고 스킵
    if status != "OK" or month not in SUMMER_MONTHS:
        records.append(rec)
        continue

    # 2) 4방향 이미지 다운로드
    all_ok = True
    for heading in HEADINGS:
        fname = f"{u}_{v}_{heading}.jpg"
        fpath = os.path.join(OUT_DIR, fname)

        if os.path.exists(fpath):
            continue

        img_params = {
            "size":    IMG_SIZE,
            "location": f"{lat},{lon}",
            "heading":  heading,
            "fov":      FOV,
            "pitch":    PITCH,
            "key":      API_KEY,
        }
        img_r = requests.get(IMAGE_URL, params=img_params, timeout=15)
        time.sleep(SLEEP_SEC)

        if img_r.status_code == 200:
            with open(fpath, "wb") as f:
                f.write(img_r.content)
        else:
            print(f"  [WARN] {u}-{v} heading={heading} 다운로드 실패")
            all_ok = False

    rec["downloaded"] = all_ok
    records.append(rec)

    if len(records) % 100 == 0:
        print(f"  진행: {len(records)}개 처리")

# ── 메타데이터 저장 ───────────────────────────────────────────────────────────
new_df = pd.DataFrame(records)
result_df = pd.concat([done_df, new_df], ignore_index=True) if not done_df.empty else new_df
result_df.to_csv(META_CSV, index=False, encoding="utf-8-sig")

n_ok       = result_df["status"].eq("OK").sum()
n_summer   = result_df["summer"].eq(True).sum()
n_done     = result_df["downloaded"].eq(True).sum()

print(f"\n완료")
print(f"  전체 링크:      {len(result_df)}")
print(f"  GSV 있음:       {n_ok}")
print(f"  여름 이미지:    {n_summer}")
print(f"  다운로드 완료:  {n_done}  ({n_done * 4}장)")
print(f"  메타데이터 저장: {META_CSV}")
