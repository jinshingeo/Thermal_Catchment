# TAVI — Thermal Accessibility Vulnerability Index
**열환경 기반 대중교통 역세권 보행 접근성 취약성 지수**

> 석사 논문 연구 | 성동구 지하철역 폭염 시 도보 Catchment 분석

---

## 연구 개요

### 연구 질문
> 폭염 시간대에 열환경(UTCI)을 소프트 제약으로 적용했을 때,  
> 지하철역까지의 30분 도보 Catchment는 얼마나 감소하는가?  
> 그 감소 패턴은 어떤 공간 환경 요인으로 설명되는가?

### 핵심 개념: TAVI
**Thermal Accessibility Vulnerability Index** — 열환경이 대중교통 접근성에 가하는 취약성을 정량화한 지수

```
Classic Catchment:  역에서 30분 이내 도달 가능한 노드 집합 (순수 이동시간)
Thermal Catchment:  effective_cost = base_time × (1 + α × penalty(UTCI)) ≤ 30분
reduction_pct (%) = (Classic − Thermal) / Classic × 100   ← TAVI의 핵심 측정값
```

### 핵심 기여
- 기존 보행 접근성 연구: 물리적 네트워크 거리만 반영
- 본 연구: 열환경(UTCI)을 링크별 소프트 제약으로 내재화 → **시간대별 접근성 감소** 실증
- UTCI 국제 기준(ISO 7933)에 따른 패널티 체계로 재현 가능한 방법론 제시

---

## 연구 지역

| 역 | 노선 | 13시 감소율 | 특성 |
|----|------|------------|------|
| **응봉역** | 경의중앙선 | **-63.9%** | 교량 노출, 그늘 부족 — 최고 취약 |
| 서울숲역 | 수인분당선 | -51.2% | 공원 인접이나 노출 링크 많음 |
| 옥수역 | 3호선/중앙선 | -50.7% | 한강변 경사 지형 |
| 뚝섬역 | 2호선 | -49.3% | |
| 행당역 | 5호선 | -41.2% | |
| 성수역 | 2호선 | -38.2% | 서울숲 그늘 효과 |
| **왕십리역** | 2호선 외 | **-29.2%** | 대형 환승역 — 최저 취약 |

> 같은 성동구 내에서도 응봉(63.9%) vs 왕십리(29.2%) — **2배 이상 격차**

---

## 선행연구와의 위치

| 연구 | 접근성 분석 | 열환경 | 네트워크 |
|------|------------|--------|---------|
| Kar et al. (2023) *Annals of AAG* | STP/PPA | ❌ | ✅ |
| Kar et al. (2024) *CEUS* | STP + 소프트 제약 | ❌ | ✅ |
| Colaninno et al. (2024) *EPB* | 보행 노출 | ✅ UTCI | ❌ |
| Basu et al. (2024) *Cities* | 보행 접근성 | ✅ UTCI | 부분 |
| **본 연구 (TAVI)** | **Catchment** | **✅ UTCI** | **✅** |

---

## 데이터

| 데이터 | 출처 | 상태 |
|--------|------|------|
| 보행 네트워크 (성동구) | OpenStreetMap (osmnx) | ✅ 완료 |
| S-DoT 환경정보 (2025.07.28~08.03) | 서울 열린데이터광장 | ✅ 완료 (57개 센서) |
| ASOS 풍속·일사량 | 기상청 서울 108 | ✅ 완료 |
| 건물 footprint | OSM | ✅ 완료 |
| NDVI (Sentinel-2) | Google Earth Engine | ⏳ 수집 예정 |
| 불투수면 비율 | 환경부 토지피복도 | ⏳ 수집 예정 |
| 건물 높이 / SVF | 국토부 건물 DB | ⏳ 수집 예정 |
| 인구 취약성 (Plan B) | KOSIS | ⏳ 선택 사항 |

---

## 분석 파이프라인

```
① S-DoT 실측 온습도 + ASOS 풍속·일사량
   → UTCI 계산 (pythermalcomfort, v3_asos)

② IDW 보간 (p=2)
   57개 센서 → 15,608개 링크 × 24시간 UTCI 매핑

③ Thermal Catchment (역방향 Dijkstra)
   effective_cost = base_time × (1 + α × penalty(UTCI))
   cutoff = 30분 → Classic / Thermal node set 산출

④ reduction_pct 계산
   7개 역 × 4시간대 (7·10·13·16시) → 히트맵

⑤ Plan A: 공간환경 변수 추출 + 회귀분석
   NDVI, 불투수면, 건물높이, 하천거리 → OLS/GWR
```

---

## 핵심 결과 (2026-04-10 기준)

| 역 | 07시 | 10시 | 13시 | 16시 |
|----|------|------|------|------|
| 왕십리역 | -21.4% | -22.1% | -29.2% | -29.2% |
| 행당역 | -30.5% | -31.0% | -41.2% | -41.2% |
| 응봉역 | -54.5% | -56.0% | **-63.9%** | -63.7% |
| 뚝섬역 | -38.5% | -39.3% | -49.3% | -49.3% |
| 성수역 | -27.5% | -27.5% | -38.2% | -38.1% |
| 서울숲역 | -39.8% | -40.1% | -51.2% | -51.1% |
| 옥수역 | -41.8% | -41.8% | -50.7% | -50.7% |

---

## 디렉토리 구조

```
TAVI/
├── 01_네트워크/
│   ├── 01_download_network.py
│   └── 02_check_bridges.py
├── 02_기상데이터/
│   ├── 01_sdot_utci.ipynb
│   ├── 02_utci_link_interpolation.ipynb
│   └── 03_utci_v3_asos.ipynb
├── 03_건물데이터/
│   └── 01_download_buildings.py
├── 04_분석결과/
│   ├── 02_utci_link_interpolation_v3.py
│   ├── 11_thermal_catchment.py        # 2개 역 상세 분석
│   ├── 12_catchment_all_stations.py   # 7개 역 전체 분석 (현재)
│   ├── catchment_all_stations_table.csv
│   └── figures/
├── 05_시각화/
├── docs/
│   ├── 2026-04-10_tavi_research_report.md
│   └── 2026-04-10_stp_to_tavi_evolution.md
├── 선행연구/
├── CLAUDE.md
├── ROADMAP.ipynb
└── README.md
```

---

## 실행 방법

```bash
pip install osmnx networkx geopandas matplotlib numpy pyproj pythermalcomfort pandas contextily scipy

# 1. UTCI v3 계산
jupyter nbconvert --to notebook --execute 02_기상데이터/03_utci_v3_asos.ipynb

# 2. IDW 링크 보간
cd 04_분석결과 && python 02_utci_link_interpolation_v3.py

# 3. Thermal Catchment (2개 역 상세)
python 11_thermal_catchment.py

# 4. 전체 역 Catchment 분석
python 12_catchment_all_stations.py
```

---

## 버전 히스토리

| 버전 | 날짜 | 핵심 내용 |
|------|------|----------|
| STP_v3_asos | 2026-04-01 | ASOS 실측 UTCI 기반 PPA 분석 완성 (성동구_STP연구) |
| TAVI_v1 | **2026-04-10** | 연구 방향 전환 — Catchment 기반 TAVI 프레임워크 수립, 7개 역 전체 분석 |

---

## 참고 문헌
- Miller, H. J. (1991). Modelling accessibility using space-time prism concepts within GIS. *IJGIS*, 5(3), 287–301.
- Kar, A., et al. (2024). Inclusive accessibility: Analyzing socio-economic disparities. *CEUS*, 114, 102202.
- Colaninno, N., et al. (2024). Pedestrian thermal comfort and heat exposure. *EPB*.
