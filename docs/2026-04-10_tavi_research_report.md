# TAVI 연구 레포트 — v1 (2026-04-10)

> 분석 버전: TAVI_v1  
> 작성자: jinshingeo

---

## 1. 오늘 완료한 작업

### 1-1. 전체 역 Thermal Catchment 분석 (`12_catchment_all_stations.py`)

성동구 내 지하철역 7개 × 4시간대 × Classic/Thermal catchment 계산 완료.

**결과 테이블 (reduction_pct, %)**

| 역 | 노선 | 07시 | 10시 | 13시 | 16시 |
|----|------|------|------|------|------|
| 왕십리역 | 2호선/수분당/중앙 | 21.4 | 22.1 | 29.2 | 29.2 |
| 행당역 | 5호선 | 30.5 | 31.0 | 41.2 | 41.2 |
| 응봉역 | 경의중앙선 | 54.5 | 56.0 | **63.9** | 63.7 |
| 뚝섬역 | 2호선 | 38.5 | 39.3 | 49.3 | 49.3 |
| 성수역 | 2호선 | 27.5 | 27.5 | 38.2 | 38.1 |
| 서울숲역 | 수인분당선 | 39.8 | 40.1 | 51.2 | 51.1 |
| 옥수역 | 3호선/중앙선 | 41.8 | 41.8 | 50.7 | 50.7 |

**주요 발견:**
1. 응봉역(63.9%) vs 왕십리역(29.2%) — 동일 성동구 내 2배 이상 격차
2. 10시~13시 구간에서 대부분 역이 급증 → UTCI 38°C 임계 시간대 반영
3. 10시→13시 증가폭: 응봉(+7.9%p), 서울숲(+11.1%p) — 서울숲이 오히려 상승폭 큼

### 1-2. 생성된 시각화

| 파일 | 설명 |
|------|------|
| `catchment_heatmap_all_stations.png` | 역 × 시간대 reduction_pct 히트맵 |
| `catchment_timeseries_all_stations.png` | 시간대별 감소율 꺾은선 (역별 색상) |
| `catchment_all_stations_13h.png` | 13시 7개 역 catchment 지도 (7-panel) |

### 1-3. 저장된 데이터

| 파일 | 내용 |
|------|------|
| `catchment_all_stations_table.csv` | Plan A 종속변수 테이블 (역×시간대별 reduction_pct) |
| `catchment_all_stations_summary.json` | 역별 전체 결과 요약 |

---

## 2. 연구 파라미터

```
WALK_SPEED  = 4.5 km/h (1.25 m/s)
TIME_BUDGET = 30분 (1800초)
ALPHA       = 0.15
UTCI 패널티: <26°C→0, 26~32→1, 32~38→2, 38~46→3, >46→4
effective_cost = base_time × (1 + 0.15 × penalty)
```

---

## 3. TAVI 프레임워크 현황

```
[완료] UTCI 계산 (v3_asos) ─────────────────── STP 연구에서 계승
[완료] IDW 링크 보간 ──────────────────────── STP 연구에서 계승
[완료] Thermal Catchment (2개 역) ──────────── 11_thermal_catchment.py
[완료] 전체 역 Catchment 분석 ─────────────── 12_catchment_all_stations.py ← 오늘
[대기] Plan A: 공간환경 변수 수집 + 회귀분석
[대기] Plan B: 인구취약성 데이터 + TAVI 지수
```

---

## 4. 다음 작업 (TODO)

### 즉시 가능 (데이터 없어도 가능)
- [ ] α 민감도 분석 (0.1 / 0.15 / 0.2 / 0.3) — reduction_pct 변화 범위 확인
- [ ] 링크별 Thermal Score 지도 — Kar et al. Fig.4 스타일 (성동구 전체 도로망)

### 데이터 수집 필요
- [ ] **NDVI** — Sentinel-2 여름철 (Google Earth Engine 또는 Copernicus)
- [ ] **불투수면 비율** — 환경부 토지피복도 (국가공간정보포털 무료)
- [ ] **건물 높이** — 국토부 건물 DB (V-World API) 또는 OSM buildings
- [ ] **가로수 위치** — 성동구 공공데이터포털
- [ ] **하천까지 거리** — OSM 수계 레이어 (자동 계산 가능)

### Plan B 추가 (선택)
- [ ] **고령인구 비율** — KOSIS 2020 인구총조사 (동별)
- [ ] **자가용 미보유 가구** — 주택총조사

---

## 5. 논문 구조 초안

```
1. Introduction
   - 도시 폭염과 보행 접근성 문제
   - 기존 연구의 한계: 열환경 ≠ 물리적 이동 제약
   - 연구 질문 + TAVI 제안

2. Literature Review
   - STP 기반 접근성 (Miller 1991, Kar et al. 2024)
   - 열환경 + 보행 (Colaninno 2024, Basu 2024)
   - 연구 공백: 두 분야의 결합 부재

3. Study Area & Data
   - 성동구 7개 역세권
   - S-DoT + ASOS UTCI (v3_asos)
   - 공간환경 변수 (Plan A)

4. Methodology
   - Thermal Catchment 모델
   - effective_cost 공식
   - TAVI 정의 (Plan A: reduction_pct, Plan B: H×E×V)

5. Results
   - 역별 reduction_pct 히트맵
   - 13시 공간 분포 지도
   - Plan A: 회귀 결과

6. Discussion
   - 응봉역의 극단값 원인 분석
   - 정책 시사점 (그늘 설치, 냉각 쉼터)

7. Conclusion
```
