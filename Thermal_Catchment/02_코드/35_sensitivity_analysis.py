"""
민감도 분석 — UTCI 임계값 35 / 38 / 41°C 비교
=================================================
동일한 파이프라인을 세 가지 임계값으로 실행하여
임계값 선택이 결과에 얼마나 민감한지 확인합니다.

출력 (→ 03_결과물/):
  sensitivity_results.csv      — 집계구별 임계값별 TARR 비교
  figures/fig10_sensitivity.png
"""

import os, json, time
import numpy as np
import pandas as pd
import networkx as nx
import osmnx as ox
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
DATA_DIR = os.path.join(PROJ_DIR, '01_데이터')

NET_PATH   = '/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml'
UTCI_PATH  = os.path.join(RES_DIR, 'link_utci_solweig.csv')
POP_PATH   = os.path.join(RES_DIR, 'residential_population.csv')
STOPS_PATH = os.path.join(DATA_DIR, '네트워크', 'transit_stops_seongdong.csv')
CLASSIC_PATH = os.path.join(RES_DIR, 'catchment_classic_30min.json')

WALK_SPEED  = 4.5 * 1000 / 3600
TIME_BUDGET = 30 * 60
TARGET_HOUR = 14          # 폭염 피크
THRESHOLDS  = [35, 38, 41]
T0_SEC      = 30 * 60


# ── 한국어 폰트 ───────────────────────────────────────────────────────────
def set_korean_font():
    for path in ['/System/Library/Fonts/Supplemental/AppleGothic.ttf',
                 '/Library/Fonts/NanumGothic.ttf']:
        if os.path.exists(path):
            fm.fontManager.addfont(path)
            plt.rcParams['font.family'] = fm.FontProperties(fname=path).get_name()
            break
    plt.rcParams['axes.unicode_minus'] = False

set_korean_font()


# ── 1. 공통 데이터 로드 ───────────────────────────────────────────────────
print("데이터 로드 중...")
G = ox.load_graphml(NET_PATH)
for u, v, data in G.edges(data=True):
    data['travel_time'] = data.get('length', 0) / WALK_SPEED

utci_df = pd.read_csv(UTCI_PATH, encoding='utf-8-sig')
utci_h  = utci_df[utci_df['hour'] == TARGET_HOUR].copy()

pop_df  = pd.read_csv(POP_PATH, encoding='utf-8-sig')
origin_nodes = ox.nearest_nodes(G, X=pop_df['lon'].values, Y=pop_df['lat'].values)
pop_df['node_id'] = origin_nodes
pop_df['code'] = pop_df['집계구코드'].astype(float).astype(int).astype(str)

stops_df = pd.read_csv(STOPS_PATH, encoding='utf-8-sig')
stops_df['node_id'] = stops_df['node_id'].astype(int)
node_to_stops = {}
for _, row in stops_df.iterrows():
    nid = int(row['node_id'])
    node_to_stops.setdefault(nid, []).append(str(row['stop_id']))
stop_nodes_set = set(stops_df['node_id'].astype(int).unique())

with open(CLASSIC_PATH, encoding='utf-8') as f:
    classic = json.load(f)


# ── 2. 캐치먼트 + 중력모형 함수 ──────────────────────────────────────────
def get_hot_edges(threshold):
    return set(zip(
        utci_h[utci_h['utci_final'] >= threshold]['u'].astype(str),
        utci_h[utci_h['utci_final'] >= threshold]['v'].astype(str)
    ))

def build_thermal_graph(threshold):
    hot = get_hot_edges(threshold)
    G_t = G.copy()
    to_rm = [(u,v) for u,v in G_t.edges()
              if (str(u),str(v)) in hot or (str(v),str(u)) in hot]
    G_t.remove_edges_from(to_rm)
    return G_t, len(to_rm)

def gravity_score(catchment_dict):
    if not catchment_dict:
        return 0.0
    return sum(np.exp(-0.5*(t/T0_SEC)**2) for t in catchment_dict.values())

def compute_catchment(graph, origin_node):
    try:
        dist_map = nx.single_source_dijkstra_path_length(
            graph, origin_node, cutoff=TIME_BUDGET, weight='travel_time')
    except nx.NetworkXError:
        return {}
    return {sid: round(t,1)
            for node, t in dist_map.items()
            if node in stop_nodes_set and node in node_to_stops
            for sid in node_to_stops[node]}


# ── 3. 임계값별 계산 ─────────────────────────────────────────────────────
results = {}   # threshold → {code: tarr}

for thr in THRESHOLDS:
    print(f"\n임계값 {thr}°C 처리 중...")
    G_t, n_rm = build_thermal_graph(thr)
    print(f"  제거 링크: {n_rm:,}개 ({n_rm/G.number_of_edges()*100:.1f}%)")

    tarr_dict = {}
    t0 = time.time()
    for _, row in pop_df.iterrows():
        code = row['code']
        a_c  = gravity_score(classic.get(code, {}))
        a_t  = gravity_score(compute_catchment(G_t, int(row['node_id'])))
        tarr = (a_c - a_t) / a_c * 100 if a_c > 0 else 0.0
        tarr_dict[code] = round(tarr, 2)
    results[thr] = tarr_dict
    print(f"  평균 TARR: {np.mean(list(tarr_dict.values())):.1f}%  ({time.time()-t0:.0f}초)")


# ── 4. 결과 정리 & 저장 ───────────────────────────────────────────────────
df = pd.DataFrame({'집계구코드': pop_df['code'].values})
for thr in THRESHOLDS:
    df[f'tarr_{thr}c'] = df['집계구코드'].map(results[thr])

out_path = os.path.join(RES_DIR, 'sensitivity_results.csv')
df.to_csv(out_path, index=False, encoding='utf-8-sig')
print(f"\n저장: {out_path}")


# ── 5. 시각화 ─────────────────────────────────────────────────────────────
print("시각화 중...")
fig, axes = plt.subplots(1, 3, figsize=(16, 5))

colors = ['#2c7bb6', '#d7191c', '#1a9641']
labels = ['UTCI ≥ 35°C\n(Strong Heat Stress)',
          'UTCI ≥ 38°C\n(Very Strong) ← 기준',
          'UTCI ≥ 41°C\n(Extreme Heat Stress)']

# 히스토그램 비교
ax = axes[0]
for thr, color, label in zip(THRESHOLDS, colors, labels):
    col = f'tarr_{thr}c'
    ax.hist(df[col], bins=30, alpha=0.6, color=color, label=f'{thr}°C')
ax.set_xlabel('TARR (%)', fontsize=11)
ax.set_ylabel('집계구 수', fontsize=11)
ax.set_title('TARR 분포 비교\n(폭염 피크 14시)', fontsize=11, fontweight='bold')
ax.legend(fontsize=9)
ax.grid(alpha=0.3)

# 완전차단 집계구 수
ax = axes[1]
blocked = [( df[f'tarr_{thr}c'] >= 99.9).sum() for thr in THRESHOLDS]
bars = ax.bar([f'{t}°C' for t in THRESHOLDS], blocked, color=colors, edgecolor='white')
for bar, val in zip(bars, blocked):
    pct = val / len(df) * 100
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
            f'{val}개\n({pct:.1f}%)', ha='center', va='bottom', fontsize=10, fontweight='bold')
ax.set_ylabel('완전차단 집계구 수', fontsize=11)
ax.set_title('임계값별 완전차단 집계구\n(TARR ≈ 100%)', fontsize=11, fontweight='bold')
ax.set_ylim(0, max(blocked)*1.25)
ax.grid(axis='y', alpha=0.3)

# 평균 TARR 비교
ax = axes[2]
mean_tarr = [df[f'tarr_{thr}c'].mean() for thr in THRESHOLDS]
bars = ax.bar([f'{t}°C' for t in THRESHOLDS], mean_tarr, color=colors, edgecolor='white')
for bar, val in zip(bars, mean_tarr):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
            f'{val:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')
ax.set_ylabel('평균 TARR (%)', fontsize=11)
ax.set_title('임계값별 평균 TARR\n(집계구 570개)', fontsize=11, fontweight='bold')
ax.set_ylim(0, max(mean_tarr)*1.2)
ax.grid(axis='y', alpha=0.3)

fig.suptitle('UTCI 임계값 민감도 분석 — 성동구 집계구 기점 (14시 폭염 피크)',
             fontsize=13, fontweight='bold')
plt.tight_layout()
path = os.path.join(FIG_DIR, 'fig10_sensitivity.png')
fig.savefig(path, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"저장: {path}")

print("\n=== 민감도 분석 완료 ===")
for thr, mean_t, blk in zip(THRESHOLDS, mean_tarr, blocked):
    print(f"  {thr}°C: 평균 TARR {mean_t:.1f}%  완전차단 {blk}개 ({blk/len(df)*100:.1f}%)")
