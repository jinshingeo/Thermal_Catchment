"""
교수님 논의용 열환경 입력변수 개별 지도 (7종)
=============================================
저장: 03_결과물/figures/교수님논의/

지도 목록:
  01_기온.png       Tair IDW (링크별, 13시)
  02_상대습도.png   RH IDW (링크별, 13시)
  03_풍속.png       va IDW (링크별, 13시) — 공간 균일
  04_일사량.png     GHI (링크별, 13시)    — 공간 균일
  05_SVF.png        Sky View Factor (링크별, 시간 무관)
  06_MRT.png        Mean Radiant Temperature (링크별, 13시)
  07_UTCI.png       UTCI (링크별, 13시)

분석 기간: 폭염일 2025.07.28~08.03 평균
"""

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import contextily as ctx
import matplotlib
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures', '교수님논의')
DATA_DIR = os.path.join(PROJ_DIR, '01_데이터')
os.makedirs(FIG_DIR, exist_ok=True)

NET_PATH  = '/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml'
UTCI_PATH = os.path.join(RES_DIR, 'link_utci_sdot_solweig.csv')
SVF_PATH  = os.path.join(RES_DIR, 'link_svf_canopy.csv')
JBG_SHP   = os.path.join(DATA_DIR, '행정경계', '통계지역경계(2016년+기준)', '집계구.shp')

HOUR = 13
PERIOD = '2025.07.28~08.03 평균'


# ── 데이터 로드 ────────────────────────────────────────────────────────
print("데이터 로드 중...")
_, edges_gdf = ox.graph_to_gdfs(ox.load_graphml(NET_PATH).to_undirected())
edges_wm = edges_gdf.to_crs(epsg=3857).reset_index()
edges_wm['u_str'] = edges_wm['u'].astype(str)
edges_wm['v_str'] = edges_wm['v'].astype(str)

utci_df = pd.read_csv(UTCI_PATH, encoding='utf-8-sig')
utci_df['u_str'] = utci_df['u'].astype(str)
utci_df['v_str'] = utci_df['v'].astype(str)
h13 = utci_df[utci_df['hour'] == HOUR].copy()

svf_df = pd.read_csv(SVF_PATH, encoding='utf-8-sig')
svf_df['u_str'] = svf_df['u'].astype(str)
svf_df['v_str'] = svf_df['v'].astype(str)

jbg = gpd.read_file(JBG_SHP, encoding='cp949')
jbg = jbg[jbg['TOT_REG_CD'].astype(str).str.startswith('11040')].copy()
jbg = jbg.set_crs(epsg=5179, allow_override=True).to_crs(epsg=3857)

print(f"  링크 수: {len(edges_wm):,}  |  13시 UTCI 행: {len(h13):,}")


def merge_to_edges(df, col, key_u='u_str', key_v='v_str'):
    """링크 GeoDataFrame에 값 컬럼 병합 (양방향)"""
    sub = df[[key_u, key_v, col]].copy()
    m = edges_wm.merge(sub, on=[key_u, key_v], how='left')
    m2 = edges_wm.merge(
        sub.rename(columns={key_u: key_v, key_v: key_u}),
        on=[key_u, key_v], how='left'
    )
    m[col] = m[col].fillna(m2[col])
    return m


def draw_map(edges, col, title, subtitle, cmap_name, vmin, vmax,
             unit, fname, uniform_val=None, uniform_color='#F4A460',
             cbar_label=None, thresh_line=None):
    """
    개별 변수 지도 출력.
    uniform_val: 공간 균일값일 때 그 숫자 (None이면 공간 변이 있음)
    thresh_line: 컬러바에 임계선 표시할 값 (e.g. MRT 55°C)
    """
    fig, ax = plt.subplots(figsize=(9, 9))

    # 배경
    jbg.plot(ax=ax, color='#f7f7f7', edgecolor='#999999',
             linewidth=0.6, alpha=0.5, zorder=1)

    if uniform_val is not None:
        # 공간 균일: 모든 링크 단색
        edges.plot(ax=ax, color=uniform_color, linewidth=1.4,
                   alpha=0.85, zorder=3)
        ax.text(0.5, 0.06,
                f'전 링크 동일값: {uniform_val:.1f} {unit}',
                transform=ax.transAxes, ha='center', va='bottom',
                fontsize=13, fontweight='bold', color='#333333',
                bbox=dict(boxstyle='round,pad=0.4', fc='white',
                          alpha=0.88, ec='#aaaaaa'))
    else:
        norm   = mcolors.Normalize(vmin=vmin, vmax=vmax)
        cmap   = plt.get_cmap(cmap_name)
        colors = [cmap(norm(v)) if not (isinstance(v, float) and np.isnan(v))
                  else '#cccccc' for v in edges[col]]
        edges.plot(ax=ax, color=colors, linewidth=1.4, alpha=0.88, zorder=3)

        sm = cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, fraction=0.035, pad=0.01, shrink=0.75)
        cbar.set_label(cbar_label or f'{col} ({unit})', fontsize=12)

        if thresh_line is not None:
            cbar.ax.axhline(y=norm(thresh_line), color='white',
                            linewidth=2.5, linestyle='--')
            cbar.ax.text(1.12, norm(thresh_line),
                         f'{thresh_line}{unit}\n(임계값)',
                         transform=cbar.ax.transAxes,
                         fontsize=9, va='center', color='#CC0000')

    # 성동구 경계 강조
    jbg.boundary.plot(ax=ax, color='#333333', linewidth=0.8,
                      alpha=0.8, zorder=5)

    try:
        ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik,
                        zoom=13, alpha=0.25)
    except Exception:
        pass

    ax.set_title(title, fontsize=15, fontweight='bold', pad=10)
    ax.text(0.5, -0.02, subtitle, transform=ax.transAxes,
            ha='center', fontsize=10, color='#555555')
    ax.set_axis_off()

    plt.tight_layout()
    out = os.path.join(FIG_DIR, fname)
    fig.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  저장: {fname}")


# ══════════════════════════════════════════════════════════════════════
print("\n지도 생성 중...")

# 01 기온
e = merge_to_edges(h13, 'Tair_idw')
draw_map(e, 'Tair_idw',
         title='기온 (Tair) — 링크별 공간분포',
         subtitle=f'S-DoT 57개 센서 IDW 보간 | {HOUR:02d}시 | {PERIOD}',
         cmap_name='RdYlBu_r', vmin=31, vmax=41, unit='°C',
         cbar_label='기온 (°C)', fname='01_기온.png')

# 02 상대습도
e = merge_to_edges(h13, 'RH_idw')
draw_map(e, 'RH_idw',
         title='상대습도 (RH) — 링크별 공간분포',
         subtitle=f'S-DoT 57개 센서 IDW 보간 | {HOUR:02d}시 | {PERIOD}',
         cmap_name='YlGnBu', vmin=44, vmax=78, unit='%',
         cbar_label='상대습도 (%)', fname='02_상대습도.png')

# 03 풍속 — 공간 균일
va_val = h13['va_idw'].mean()
e = merge_to_edges(h13, 'va_idw')
draw_map(e, 'va_idw',
         title='풍속 (va) — 링크별 공간분포',
         subtitle=f'S-DoT 57개 센서 IDW 보간 | {HOUR:02d}시 | {PERIOD}\n'
                  f'※ 센서 간 편차 없어 전 링크 동일값으로 보간됨',
         cmap_name='PuBu', vmin=0, vmax=5, unit='m/s',
         cbar_label='풍속 (m/s)', fname='03_풍속.png',
         uniform_val=va_val, uniform_color='#7bbcce')

# 04 일사량 — 공간 균일
ghi_val = h13['GHI'].mean()
e = merge_to_edges(h13, 'GHI')
draw_map(e, 'GHI',
         title='일사량 (GHI) — 링크별 공간분포',
         subtitle=f'Open-Meteo archive (성동구 중심 단일 지점) | {HOUR:02d}시 | {PERIOD}\n'
                  f'※ 공간 보간 없이 전 링크 동일값 적용',
         cmap_name='YlOrRd', vmin=0, vmax=900, unit='W/m²',
         cbar_label='일사량 (W/m²)', fname='04_일사량.png',
         uniform_val=ghi_val, uniform_color='#F4A460')

# 05 SVF
svf_e = merge_to_edges(svf_df, 'svf')
draw_map(svf_e, 'svf',
         title='Sky View Factor (SVF) — 링크별 공간분포',
         subtitle='OSM 건물 + DEM 근사 | 시간 무관 (도시 형태 기반)',
         cmap_name='RdYlGn', vmin=0, vmax=1, unit='',
         cbar_label='SVF (0=완전 차폐, 1=완전 개방)',
         fname='05_SVF.png')

# 06 MRT
e = merge_to_edges(h13, 'mrt')
draw_map(e, 'mrt',
         title='평균복사온도 (MRT) — 링크별 공간분포',
         subtitle=f'SOLWEIG 약식 (Lindberg & Grimmond 2011) | {HOUR:02d}시 | {PERIOD}',
         cmap_name='plasma', vmin=42, vmax=67, unit='°C',
         cbar_label='MRT (°C)', fname='06_MRT.png',
         thresh_line=55.0)

# 07 UTCI
UTCI_BINS   = [-5, 26, 32, 38, 46, 70]
UTCI_COLORS = ['#4575b4', '#91bfdb', '#fee090', '#fc8d59', '#d73027']
UTCI_LABELS = ['< 26°C (no stress)', '26–32°C (moderate)',
               '32–38°C (strong)', '38–46°C (very strong)', '> 46°C (extreme)']

e = merge_to_edges(h13, 'utci_m3')
utci_norm = mcolors.BoundaryNorm(UTCI_BINS, len(UTCI_COLORS))
utci_cmap = mcolors.ListedColormap(UTCI_COLORS)

fig, ax = plt.subplots(figsize=(9, 9))
jbg.plot(ax=ax, color='#f7f7f7', edgecolor='#999999',
         linewidth=0.6, alpha=0.5, zorder=1)

colors = [utci_cmap(utci_norm(v)) if not (isinstance(v, float) and np.isnan(v))
          else '#cccccc' for v in e['utci_m3']]
e.plot(ax=ax, color=colors, linewidth=1.4, alpha=0.88, zorder=3)
jbg.boundary.plot(ax=ax, color='#333333', linewidth=0.8, alpha=0.8, zorder=5)

try:
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik,
                    zoom=13, alpha=0.25)
except Exception:
    pass

from matplotlib.patches import Patch
handles = [Patch(color=c, label=l)
           for c, l in zip(UTCI_COLORS, UTCI_LABELS)]
ax.legend(handles=handles, loc='lower left', fontsize=9,
          title='열 스트레스 분류 (Bröde et al. 2012)',
          title_fontsize=9, framealpha=0.9)

vals = e['utci_m3'].dropna()
ax.text(0.98, 0.06,
        f'mean = {vals.mean():.1f}°C\n'
        f'≥38°C: {(vals>=38).sum()/len(vals)*100:.1f}%',
        transform=ax.transAxes, ha='right', va='bottom',
        fontsize=11, fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.4', fc='white', alpha=0.88))

ax.set_title('UTCI — 링크별 공간분포', fontsize=15, fontweight='bold', pad=10)
ax.text(0.5, -0.02,
        f'pythermalcomfort (Bröde et al. 2012) | {HOUR:02d}시 | {PERIOD}',
        transform=ax.transAxes, ha='center', fontsize=10, color='#555555')
ax.set_axis_off()
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, '07_UTCI.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  저장: 07_UTCI.png")

print(f"\n=== 완료 ({FIG_DIR}) ===")
for f in sorted(os.listdir(FIG_DIR)):
    if f.endswith('.png'):
        print(f"  {f}")
