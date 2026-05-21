"""
성동구 OSM 베이스맵 — 3D 지도 동일 시점
plot_surface로 OSM 타일을 z=0 지면에 렌더링 → 3D 지도들과 정확히 정렬
"""

import os, warnings
import numpy as np
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import contextily as ctx
from pyproj import Transformer
from scipy.ndimage import zoom as scipy_zoom
warnings.filterwarnings('ignore')

matplotlib.rcParams['font.family'] = 'Apple SD Gothic Neo'
matplotlib.rcParams['axes.unicode_minus'] = False

JBG_PATH = '/Users/jin/석사논문/통계지역경계/집계구.shp'
OUT_DIR  = '/Users/jin/석사논문/TAVI/Thermal_Catchment/03_결과물/figures/3d_maps'

# ── 3D 지도와 완전히 동일한 파라미터 ────────────────────────────────────
ELEV    = 35
AZIM    = -65
FIGSIZE = (12, 12)
DPI     = 150
Z_MAX   = 1500

# ── 성동구 로드 ──────────────────────────────────────────────────────────
jbg = gpd.read_file(JBG_PATH)
if jbg.crs is None:
    jbg = jbg.set_crs('EPSG:5179', allow_override=True)
jbg = jbg[jbg['TOT_REG_CD'].astype(str).str.startswith('11040')].to_crs('EPSG:5186')
xmin, ymin, xmax, ymax = jbg.total_bounds
cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
X_RANGE = xmax - xmin
Y_RANGE = ymax - ymin

# ── OSM 타일 다운로드 (Web Mercator) ────────────────────────────────────
print("OSM 타일 다운로드...")
jbg_3857 = jbg.to_crs('EPSG:3857')
b = jbg_3857.total_bounds
pad = 600  # 여백 (m) — 지도 경계 밖까지 조금 더 받아서 클립

img, ext = ctx.bounds2img(
    b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad,
    zoom=14,
    source=ctx.providers.OpenStreetMap.Mapnik,
    ll=False  # Web Mercator 좌표 입력
)
print(f"  타일 크기: {img.shape}  |  extent: {[round(e) for e in ext]}")

# ── 타일 좌표 → 로컬 좌표 (EPSG:5186, 중심 기준) 변환 ───────────────────
img_h, img_w = img.shape[:2]

# extent = (xmin_wm, xmax_wm, ymin_wm, ymax_wm) — contextily 반환 형식
xs_wm = np.linspace(ext[0], ext[1], img_w)
ys_wm = np.linspace(ext[3], ext[2], img_h)   # y 축 반전 (이미지 top→bottom)
XX_wm, YY_wm = np.meshgrid(xs_wm, ys_wm)

tr = Transformer.from_crs('EPSG:3857', 'EPSG:5186', always_xy=True)
XX_5, YY_5 = tr.transform(XX_wm.ravel(), YY_wm.ravel())
XX_loc = (XX_5 - cx).reshape(img_h, img_w)
YY_loc = (YY_5 - cy).reshape(img_h, img_w)

# ── plot_surface 용 다운샘플링 ───────────────────────────────────────────
N = 250  # NxN 격자
fh = N / img_h
fw = N / img_w
XX_ds  = scipy_zoom(XX_loc, (fh, fw), order=1)
YY_ds  = scipy_zoom(YY_loc, (fh, fw), order=1)
img_ds = scipy_zoom(img.astype(float), (fh, fw, 1), order=1)
img_ds = np.clip(img_ds / 255.0, 0, 1)
ZZ     = np.zeros_like(XX_ds)
print(f"  다운샘플 격자: {XX_ds.shape}")

# ── 3D figure (make_ax 동일 설정) ────────────────────────────────────────
fig = plt.figure(figsize=FIGSIZE, dpi=DPI, facecolor='white')
ax  = fig.add_subplot(111, projection='3d')
ax.set_xlim(xmin - cx, xmax - cx)
ax.set_ylim(ymin - cy, ymax - cy)
ax.set_zlim(0, Z_MAX)
ax.set_box_aspect([X_RANGE, Y_RANGE, Z_MAX * 0.7])
ax.view_init(elev=ELEV, azim=AZIM)
ax.set_axis_off()
for pane in [ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane]:
    pane.fill = False
    pane.set_edgecolor('none')
ax.grid(False)

# ── OSM 타일을 z=0 지면에 렌더링 ─────────────────────────────────────────
print("plot_surface 렌더링...")
ax.plot_surface(
    XX_ds, YY_ds, ZZ,
    facecolors=img_ds,
    shade=False,
    rcount=N,
    ccount=N,
    zorder=0,
)

out_path = os.path.join(OUT_DIR, 'basemap_3d.png')
plt.savefig(out_path, dpi=DPI, bbox_inches='tight', facecolor='white')
plt.close()
print(f"저장 완료: {out_path}")
