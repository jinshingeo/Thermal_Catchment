"""
건물 폴리곤 기반 합성 DSM 생성
================================
LiDAR 미확보 시 건물 폴리곤 + 층수 속성으로 DSM 생성 (Lindberg et al., 2018)

SOLWEIG 입력 3종 생성:
  DSM  = 건물 높이 래스터 (지표면 0 + 건물 높이)
  DEM  = 지표면 0 (성동구는 상대적으로 평탄 → 0으로 설정)
  CDSM = 수목 캐노피 높이 래스터 (가로수 데이터로 근사, 없으면 0)

해상도: 2m (SOLWEIG 권장 최소 해상도)

참고문헌:
  Lindberg, F., et al. (2018). Urban Multi-scale Environmental Predictor (UMEP).
  Environmental Modelling & Software, 99, 70–87.
  → "Building footprint polygons with height attributes can be used to generate
     a building DSM as an alternative when airborne LiDAR data is unavailable."

한계:
  - 수목 CDSM 미반영 (가로수 데이터로 부분 보완)
  - 지붕 형태 무시 (평지붕 가정)
  - 층수×3m 추정값으로 실제 높이와 오차 가능
"""

import os
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.transform import from_bounds
from rasterio.features import rasterize
from shapely.geometry import Point, box
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)               # Thermal_Catchment/
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
os.makedirs(RES_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)
BULD_PATH = '/Users/jin/석사논문/TAVI/03_건물데이터/(도로명주소)건물_서울/TL_SPBD_BULD_11_202603.shp'
GREEN_PATH= '/Users/jin/Green_Space_2SFCA/코드/data/도시숲전체_면_서울_최종_중분류.shp'
OUT_DIR   = os.path.join(BASE, 'dsm_raster')
FIG_DIR   = os.path.join(RES_DIR, 'figures')
os.makedirs(OUT_DIR, exist_ok=True)

RESOLUTION = 2.0   # m — 픽셀 크기
CRS        = 'EPSG:5186'
TREE_HEIGHT = 8.0  # m — 가로수 캐노피 평균 높이 추정값

# 성동구 범위 (EPSG:5186)
BBOX_WGS = gpd.GeoDataFrame(
    geometry=[Point(127.010, 37.530), Point(127.070, 37.570)], crs='EPSG:4326'
).to_crs(CRS)
XMIN = BBOX_WGS.geometry[0].x - 100   # 여유 100m
YMIN = BBOX_WGS.geometry[0].y - 100
XMAX = BBOX_WGS.geometry[1].x + 100
YMAX = BBOX_WGS.geometry[1].y + 100


# ── 래스터 파라미터 계산 ────────────────────────────────────────────────
width  = int((XMAX - XMIN) / RESOLUTION)
height = int((YMAX - YMIN) / RESOLUTION)
transform = from_bounds(XMIN, YMIN, XMAX, YMAX, width, height)
print(f"래스터 크기: {width} × {height} 픽셀 ({RESOLUTION}m 해상도)")
print(f"범위: ({XMIN:.0f}, {YMIN:.0f}) ~ ({XMAX:.0f}, {YMAX:.0f})")


# ── 건물 데이터 로드 ────────────────────────────────────────────────────
print("\n건물 데이터 로드 중...")
buld_raw = gpd.read_file(BULD_PATH)
buld = buld_raw[buld_raw['SIG_CD'] == '11200'][['GRO_FLO_CO', 'geometry']].copy()
buld['height_m'] = buld['GRO_FLO_CO'].clip(lower=1) * 3
buld = buld.to_crs(CRS)
buld['geometry'] = buld.geometry.buffer(0)
buld = buld[buld.geometry.is_valid].copy()
# 성동구 bbox로 한정
study_box = box(XMIN, YMIN, XMAX, YMAX)
buld = buld[buld.geometry.intersects(study_box)].copy()
print(f"  건물: {len(buld):,}개 | 높이 범위: {buld.height_m.min():.0f}~{buld.height_m.max():.0f}m")


# ── 가로수 데이터 로드 ──────────────────────────────────────────────────
print("가로수 데이터 로드 중...")
green_raw = gpd.read_file(GREEN_PATH)
green = green_raw.cx[XMIN:XMAX, YMIN:YMAX].copy() if green_raw.crs.to_epsg() == 5186 \
    else green_raw.to_crs(CRS).cx[XMIN:XMAX, YMIN:YMAX].copy()
trees = green[green['U2_NAM'] == '가로수'].copy()
trees = trees[trees.geometry.intersects(study_box)].copy()
print(f"  가로수: {len(trees):,}개")


# ── DSM 래스터화 ────────────────────────────────────────────────────────
print("\nDSM 래스터화 중 (건물 높이)...")
shapes_dsm = [
    (geom, float(h))
    for geom, h in zip(buld.geometry, buld.height_m)
    if geom is not None and not geom.is_empty
]
dsm_array = rasterize(
    shapes=shapes_dsm,
    out_shape=(height, width),
    transform=transform,
    fill=0.0,          # 건물 없는 곳 = 지표면 0m
    dtype='float32',
    merge_alg=rasterio.enums.MergeAlg.replace,
)
print(f"  DSM: 건물 있는 픽셀 {(dsm_array > 0).sum():,}개 / 전체 {width*height:,}개")
print(f"  높이 분포: max {dsm_array.max():.0f}m, mean(건물만) {dsm_array[dsm_array>0].mean():.1f}m")


# ── DEM 래스터화 (평탄 지형 가정) ──────────────────────────────────────
print("DEM 생성 중 (평탄 지형, 전체 0m)...")
dem_array = np.zeros((height, width), dtype='float32')
# 성동구는 중랑천·한강변 외 대부분 평탄 → 0m 근사 허용


# ── CDSM 래스터화 (가로수 캐노피) ──────────────────────────────────────
print("CDSM 래스터화 중 (가로수 캐노피)...")
if len(trees) > 0:
    shapes_cdsm = [
        (geom, TREE_HEIGHT)
        for geom in trees.geometry
        if geom is not None and not geom.is_empty
    ]
    cdsm_array = rasterize(
        shapes=shapes_cdsm,
        out_shape=(height, width),
        transform=transform,
        fill=0.0,
        dtype='float32',
    )
    print(f"  CDSM: 가로수 있는 픽셀 {(cdsm_array > 0).sum():,}개")
else:
    cdsm_array = np.zeros((height, width), dtype='float32')
    print("  CDSM: 가로수 없음 → 전체 0")


# ── 저장 ───────────────────────────────────────────────────────────────
from pyproj import CRS as ProjCRS
crs_wkt = ProjCRS.from_epsg(5186).to_wkt()

raster_meta = {
    'driver': 'GTiff',
    'dtype': 'float32',
    'width': width,
    'height': height,
    'count': 1,
    'crs': crs_wkt,
    'transform': transform,
    'nodata': -9999.0,
}

for name, arr in [('DSM', dsm_array), ('DEM', dem_array), ('CDSM', cdsm_array)]:
    path = os.path.join(OUT_DIR, f'{name}_seongdong_{int(RESOLUTION)}m.tif')
    with rasterio.open(path, 'w', **raster_meta) as dst:
        dst.write(arr, 1)
    print(f"저장: {path}")


# ── 시각화 ─────────────────────────────────────────────────────────────
print("\nDSM 시각화 생성 중...")
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

for ax, arr, title, cmap in [
    (axes[0], dsm_array,  'DSM (건물 높이)',      'hot_r'),
    (axes[1], dem_array,  'DEM (지표면, 0m)',     'terrain'),
    (axes[2], cdsm_array, 'CDSM (가로수 캐노피)', 'Greens'),
]:
    im = ax.imshow(arr, cmap=cmap, origin='upper',
                   extent=[XMIN, XMAX, YMIN, YMAX])
    plt.colorbar(im, ax=ax, label='높이 (m)', shrink=0.8)
    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.set_xlabel('X (EPSG:5186)', fontsize=9)
    ax.set_ylabel('Y (EPSG:5186)', fontsize=9)

fig.suptitle(f'성동구 합성 DSM/DEM/CDSM ({RESOLUTION}m 해상도)\n'
             f'건물 폴리곤 기반 (Lindberg et al., 2018)',
             fontsize=12, fontweight='bold')
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'synthetic_dsm_overview.png'), dpi=150, bbox_inches='tight')
plt.close()
print(f"시각화 저장: figures/synthetic_dsm_overview.png")

print("\n=== 완료 ===")
print(f"SOLWEIG 입력 파일 위치: {OUT_DIR}")
print(f"  DSM:  DSM_seongdong_{int(RESOLUTION)}m.tif")
print(f"  DEM:  DEM_seongdong_{int(RESOLUTION)}m.tif")
print(f"  CDSM: CDSM_seongdong_{int(RESOLUTION)}m.tif")
print("\n다음 단계: SOLWEIG 실행 (19_solweig_utci.py)")
