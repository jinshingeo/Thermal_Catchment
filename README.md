# Thermal Catchment Area
**열노출을 반영한 보행 환경 접근성 공간 단위 제안**

> 석사 논문 연구 | 서울 성동구 | 업데이트: 2026-06-01
>
> 2026년 한국지도학회 춘계학술대회 발표 완료 (2026.05.30)

---

## 연구 개요

### 핵심 아이디어

기존 Catchment Area는 특정 지점에서 일정 시간 내에 도달할 수 있는 공간 범위를 **물리적 거리와 시간만으로** 산정한다. 폭염 시 보행자는 고열 노출 구간을 회피하거나 이동을 포기하게 되며, 기존 분석에서 접근 가능하다고 간주된 경로가 실제로는 이동 불가일 수 있다.

본 연구는 MRT 임계값 초과 링크를 네트워크에서 완전 제거(Hard Cut)하여 폭염 시 실질적으로 접근 가능한 공간 범위인 **Thermal Catchment Area**를 새로운 공간 접근성 단위로 제안한다.

```
Classic Catchment:  전체 네트워크 → Dijkstra → 15분 시간예산 내 도달 노드셋
Thermal Catchment:  MRT ≥ 55°C 링크 제거 → 축소 네트워크 → Dijkstra → 도달 노드셋

TARR (%) = (S_classic − S_thermal) / S_classic × 100
```

### 연구 차별점

| | 기존 연구 | 본 연구 |
|--|---------|--------|
| 열환경 반영 방식 | 소프트 패널티 (속도 감소) | **Hard Cut (이동 불가)** |
| 결과 단위 | 접근성 점수 감소 | **접근 가능 공간 자체 감소** |
| 열환경 지표 | UTCI·LST 직접 사용 | **MRT (폭염 조건에서 공간 분화 가능)** |
| 측정 패러다임 | '접근성이 낮아진다' | **'접근 가능 공간이 사라진다'** |

> UTCI는 폭염 조건에서 98.9% 포화(극한더위 등급 집중)로 공간 분화 불가 → UTCI=38°C 역산값인 **MRT ≥ 55°C**를 임계값으로 사용

---

## 연구 질문

1. 폭염 조건에서 보행 열환경을 링크 단위로 공간 분화할 수 있는가?
2. 폭염 시 보행 접근 가능 공간이 얼마나, 어디서 감소하는가?

---

## 연구 지역 및 데이터

**서울특별시 성동구** / 2025.07.28–08.03 폭염일 7일 평균 / 13시 기준

한강·중랑천 수변, 서울숲 대형 녹지, 왕십리·성수 업무지구, 아파트 단지가 혼재하는 도시 형태 이질성이 높은 지역으로, 열환경 공간 변이 분석에 적합하다.

| 입력 변수 | 데이터 출처 | 처리 방법 |
|---------|-----------|---------|
| Tair · RH · 풍속 | S-DoT (서울시 도시 데이터 센서) | IDW 보간 → 링크별 할당 |
| 일사량 (GHI) | Open-Meteo archive | 폭염일 7일 평균 |
| 건물높이 | 도로명주소 건물 SHP | 지상층수 × 3m |
| 도시숲 캐노피 | 서울시 녹지 SHP | 10m 고정 가정 |
| 보행 네트워크 | OpenStreetMap | network_type='walk' 추출 |

---

## 방법론

### (1) MRT 산출 — 링크별 열환경 공간 분화

SOLWEIG(Solar and LongWave Environmental Irradiance Geometry; Lindberg & Grimmond 2011) 복사 교환 수식 기반 간소화 구현으로 성동구 보행 네트워크 전 링크의 MRT를 산출한다.

- SVF(Sky View Factor): Oke(1987) H/W Canyon 공식 확장 적용 (캐노피 높이 추가 반영)
- 단파(K) + 장파(L) 합산 → Stefan-Boltzmann 역산 → 링크별 MRT

```
T_mrt = [1/σ × (K_sw + L_lw)]^0.25 − 273.15

K_sw = α_p[(1−SVF)·K_dif + shadow·K_dir·cosθ + SVF·K_dif]
L_lw = ε_p[SVF·L_sky + (1−SVF)·L_wall]
```

폭염일 13시 기준 링크별 MRT: **범위 42–63°C**, 한강·대로변(SVF 높음) > 고층 이면도로(SVF 낮음)

### (2) 보행 회피 임계값 추정 — UTCI → MRT 역산

폭염 조건(Tair=36°C, RH=60%, va=2.37 m/s)에서 UTCI 직접 사용 불가(98.9% 포화) → UTCI 극한더위 기준(≥38°C; Bröde et al. 2012)에서 MRT를 역산:

```
MRT* = f⁻¹_UTCI(38°C | Tair=36°C, RH=60, va=2.37) ≈ 55°C
```

**MRT ≥ 55°C 링크를 보행 불가로 처리** (전체 링크의 30.1% 해당, 13시 기준)

### (3) Thermal Catchment & TARR 산출

```python
# MRT 임계값 초과 링크 제거 (Hard Cut)
hot_edges = set(links[links['mrt'] >= 55][['u','v']].itertuples(index=False))
G_thermal = G.copy()
G_thermal.remove_edges_from(hot_edges)

# 집계구 중심점 → Dijkstra → 15분 내 도달 정류장 셋
S_classic  = reachable_stops(G,        origin, budget=15min)
S_thermal  = reachable_stops(G_thermal, origin, budget=15min)

TARR = (len(S_classic) - len(S_thermal)) / len(S_classic) * 100
```

직접 차단(MRT ≥ 55°C 링크 자체) 및 **간접 고립**(차단 링크 뒤에 갇혀 우회로 없음) 모두 반영.

### (4) Monte Carlo — 임계값 불확실성 검토

MRT 임계값(55°C)에 내재한 불확실성이 취약 집계구 분류 결과에 미치는 영향을 정량화.

```
임계값 ~ N(55°C, 4²)  →  2,000회 샘플링 → 집계구별 TARR 분포
```

> σ=4°C는 기상 관측 불확실성 ±4°C 가정 (95% 범위 47–63°C)

---

## 핵심 결과

### 집계구별 TARR 분포

| 지표 | 값 |
|------|-----|
| 전체 평균 TARR | **68.0%** |
| 표준편차 | 23.6% |
| 중앙값 | 67.5% |
| TARR = 0% (손실 없음) | 1개 집계구 (0.2%) |
| TARR ≥ 50% | **429개 집계구 (76.1%)** |
| TARR = 100% (완전 차단) | 75개 집계구 (13.3%) |

폭염 피크 시 접근 가능 정류장: Classic 평균 **54.0개** → Thermal 평균 **17.0개**

### 공간 패턴

- **고TARR**: 응봉·서울숲 인근 — 한강변·개방공간 (SVF 높음 → MRT 높음)
- **저TARR**: 성수·왕십리 — 고층 건물 밀집 (도시 그늘 → MRT 낮음)
- 같은 역세권 내에서도 도시 형태에 따라 접근성 손실의 공간적 편차가 뚜렷함

---

## 코드 파이프라인

```
Thermal_Catchment/02_코드/
  15_svf_per_link.py       SVF + 도시숲 캐노피 링크별 계산
  19_solweig_utci.py       SOLWEIG 기반 링크별 MRT 산출       ← 핵심
  40_catchment_mrt.py      MRT Hard Cut → Thermal Catchment  ← 핵심
  31_catchment_from_jibgaegu.py  집계구 단위 TARR 산출        ← 핵심
  48_monte_carlo_mrt.py    임계값 불확실성 Monte Carlo 검증
  63_tarr_choropleth.py    TARR 코로플레스 지도
  65_catchment_contrast_map.py  Classic vs Thermal 비교 지도
```

---

## 디렉토리 구조

```
TAVI/
├── 01_네트워크/         OSM 보행 네트워크
├── 02_기상데이터/       기상 원시 데이터
├── 03_건물데이터/       건물높이, DSM
├── Thermal_Catchment/
│   ├── 01_데이터/       행정경계, 네트워크, 기상, 건물DSM, 인구
│   ├── 02_코드/         분석 스크립트 (15~65번)
│   └── 03_결과물/       JSON·CSV 결과, figures/
├── study_note/          개념별 학습노트 (MRT·UTCI·SVF·TARR 등)
├── writing/             논문 초고, 학회 발표 자료
├── 선행연구/            참고 문헌 PDF
└── README.md
```

---

## 선행연구 대비 위치

| 연구 | 열환경 지표 | 패널티 방식 | 분석 대상 | 새 공간 단위 |
|------|-----------|------------|---------|------------|
| Basu et al. (2024) *Cities* | UTCI | 소프트 (경로 확률) | 일반 보행권 | ❌ |
| Aydin et al. (2026) *SCS* | UTCI (CFD) | 소프트 (PTT 증가) | POI 접근성 | ❌ |
| Dong et al. (2024) *G&S* | LST (위성) | 없음 | UGS 접근성 | ❌ |
| Wang et al. (2025) *UC* | LST 기반 DI | 없음 | UGS 접근성 | ❌ |
| **본 연구** | **MRT (SOLWEIG)** | **Hard Cut (이진)** | **대중교통 역세권** | **✅** |

---

## 연구 한계 및 향후 연구 방향

**연구 한계**
- 성동구 단일 시범 연구 지역 (개념 검증에 초점)
- 집계구 중심점 출발 가정 — 실제 거주 분포와 괴리 가능
- 캐노피·수변 간소 반영, OSM 가용 한계 — MRT 과대 추정 가능성 (단, 같은 방향의 편향)

**향후 연구 방향**
- 서울 전역 또는 타 도시로 적용 확장
- SSP(공통사회경제경로) 기반 미래 폭염 시나리오 분석
- 노인 보행 속도 적용 등 사회적 취약성 고려

---

## 버전 히스토리

| 버전 | 날짜 | 핵심 내용 |
|------|------|----------|
| STP_v3 | 2026-04-01 | ASOS 기반 UTCI, 응봉동·성수동 PPA 비교 |
| TAVI_v1 | 2026-04-10 | 연구 방향 전환 — Catchment 기반 분석 수립 |
| TAVI_v2 | 2026-04-16 | SOLWEIG UTCI 통일, H×E×V 프레임 도입 |
| TAVI_v3 | 2026-04-21 | Thermal Catchment 개념 논문으로 확정, H×E×V 제거 |
| **TAVI_v4** | **2026-05-30** | **MRT 역산 임계값 55°C 확정, 집계구 단위 TARR 산출, 한국지도학회 춘계학술대회 발표** |

---

## 투고 목표

- 1순위: **Landscape and Urban Planning** (SCI Q1)
- 2순위: **Urban Climate** (SCI Q1)
- 일정: 2026년 7월 중순

---

## 참고 문헌 (핵심)

- Bröde et al. (2012). Deriving the operational procedure for the Universal Thermal Climate Index (UTCI). *IJB*, 56, 481–494.
- Lindberg & Grimmond (2011). The influence of vegetation and building morphology on shadow patterns and mean radiant temperatures in urban areas. *Theoretical and Applied Climatology*, 105, 311–323.
- Basu et al. (2024). Hot and bothered: Measuring the impact of heat on walkability. *Cities*, 155, 105468.
- Aydin et al. (2026). UTCI-adjusted pedestrian accessibility. *Sustainable Cities and Society*.
- Dong et al. (2024). Measuring urban thermal environment from accessibility-based perspective. *Geography and Sustainability*, 5, 329–342.
- Wang et al. (2025). Supply and demand analysis of urban thermal environments. *Urban Climate*, 60, 102356.
- Sevtsuk & Alhassan (2025). Perceived distance and pedestrian route choice. *Environment and Planning B*.
