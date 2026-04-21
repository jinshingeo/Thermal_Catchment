# 연구 방향 업데이트 — 2026-04-21

## 연구 제목 (잠정)

**Thermal Catchment Area: A Heat-Adjusted Spatial Accessibility Framework and Its Application to Subway Station Catchments in Seoul**

---

## 핵심 변경사항 요약

| 항목 | 이전 방향 (TAVI_v2) | 현재 방향 |
|------|-------------------|---------|
| 메인 기여 | TAVI 지수 (H×E×V) | Thermal Catchment Area 개념 제안 |
| H×E×V 프레임 | 논문 구조의 핵심 | 제거 (후속 연구로 이관) |
| V 컴포넌트 | 논문 포함 | 제거 (코드는 보존) |
| TAVI 지수 | 메인 산출물 | 제거 (코드는 보존) |
| 케이스 시설 | 지하철역 (주요 분석 대상) | 지하철역 (단순 케이스 스터디) |
| 비교 분석 | 없음 | Classic vs Thermal 2SFCA 비교 |

---

## 연구 구조

### 메인 기여 (방법론 제안)

> **Thermal Catchment Area**
> "기존 Catchment는 물리적 이동 제약만 반영한다.
> 우리는 UTCI 기반 열환경 임계값을 적용하여
> 보행 불가 링크를 제거한 Thermal Catchment Area를 제안한다."
> → 어떤 시설에도, 어떤 도시에도 적용 가능한 범용 개념

### 케이스 스터디 (개념 검증)

- 대상: 서울 성동구 지하철역 7개 (왕십리·행당·응봉·뚝섬·성수·서울숲·옥수)
- 왜 지하철: 폭염 취약 집단의 이동 의존 수단
- 왜 성동구: 하천·녹지·밀집 도심 공존 → 공간 변이 큼

---

## 방법론

### Thermal Catchment 계산

```
Classic Catchment:
  전체 네트워크에서 Dijkstra → 시간예산(15분) 내 도달 노드셋

Thermal Catchment:
  UTCI ≥ 38°C 링크 제거 → 축소된 네트워크에서 Dijkstra → 도달 노드셋

reduction_pct = (Classic - Thermal) / Classic × 100
```

### 왜 하드 컷인가 (기존 소프트 패널티 방식과의 차별점)

기존 연구들의 소프트 패널티 방식:
- Basu et al. (2024): 경로 선택 확률 감소 (행동 모델)
- Aydin et al. (2026): PTT(지각 이동시간) 증가 = 이동속도 감소 방식

하드 컷 정당성:
- UTCI 38°C = "very strong heat stress" (Bröde et al., 2012) — 의학적 임계값
- 소프트 패널티는 "더 오래 걸리지만 도달 가능" 전제 → 극한 열환경에서 비현실적
- 하드 컷 = 보수적(conservative) 추정 → 실제 손실은 이보다 더 클 수 있음
- 공공보건 기관의 열 경보 방식과 일치 (연속 그라디언트가 아닌 범주적 경보)

논문 핵심 문장:
> "Unlike soft-penalty approaches that assume continuous mobility under heat stress,
> we propose a threshold-based hard cut consistent with clinical heat stress
> classifications and categorical public health advisories."

### UTCI 계산 방식

- MRT: Lindberg et al.(2008) 단순화 공식 기반
  - `MRT = Tair + 0.5 × √(GHI × cos_z) × SVF` (주간)
  - `MRT = Tair - 2.0 × SVF` (야간)
- UTCI: pythermalcomfort 라이브러리 (Bröde et al. 2012 표준 다항식)
- 캐노피 보정: Chen & Ng(2012) 기반 (-2.5°C × canopy_ratio)
- 기상 입력: Open-Meteo Archive API (2025-07-28~08-03 7일 평균)

**방어 논리:**
- MRT는 단순화 → 절댓값 과소추정 가능 (보수적 추정)
- 공간 상대 패턴은 SVF가 결정 → 링크 간 순위 유효
- 선행연구 대비: Dong·Wang은 Landsat LST 사용 (UTCI 아님) → 네 방식이 더 정교
- 한계 명시 + 임계값 민감도 분석으로 방어

### 2SFCA 비교 분석

- Classic Catchment 기반 2SFCA vs Thermal Catchment 기반 2SFCA
- "기존 방법이 접근성을 과대평가한다"는 주장의 수치 근거 제공
- 논문에서 Discussion 또는 Application 섹션에 위치

---

## 선행연구 대비 차별점

| 차별점 | 내용 |
|--------|------|
| 새로운 공간 단위 | Thermal Catchment Area = 기존 어디에도 없는 신규 정의 |
| 하드 컷 방식 | 소프트 패널티(기존) vs 이진 임계값(본 연구) |
| 대중교통 맥락 | 녹지·POI(기존) vs 지하철 역세권(본 연구) |
| 처방적 분석 | link_criticality — 코드 보존, 활용 여부 추후 결정 |
| 범용성 | 병원·공원·학교 등 어떤 시설에도 적용 가능 |
| 재현 가능성 | SVF + 기상데이터만으로 어느 도시에서도 재현 가능 |

---

## 논문 구조 (안)

```
1. Introduction
   기존 Catchment의 한계 → Thermal Catchment 제안
   소프트 패널티 vs 하드 컷 논의

2. Methods
   2-1. Thermal Catchment Area 계산 (범용 프레임워크)
   2-2. UTCI 계산 (SVF 기반 MRT → pythermalcomfort)
   2-3. Classic vs Thermal 2SFCA 비교

3. Case Study: 서울 성동구 지하철역 7개
   데이터, 파라미터, 적용 결과

4. Results
   4-1. reduction_pct 패턴 (역별 공간 변이)
   4-2. Classic vs Thermal 2SFCA 비교 수치
   4-3. 민감도 분석 (임계값 35/38/41°C, 시간예산 10/15/20분)

5. Discussion
   개념의 일반화 가능성
   한계 및 향후 연구 (V 통합, 다도시 적용 등)

6. Conclusion
```

---

## 남은 작업 목록

| 우선순위 | 항목 | 상태 |
|---------|------|------|
| ★★★ | 일별 승하차 데이터 수집 (OA-12914) | 미완 |
| ★★★ | 폭염일 vs 비폭염일 승하차 검증 분석 | 미완 |
| ★★ | Classic vs Thermal 2SFCA 비교 코드 | 미완 |
| ★★ | 민감도 분석 (임계값·시간예산) | 미완 |
| ★ | LST 공간 패턴 검증 (지도 교수 협의 후) | 보류 |
| ★ | 영어 논문 초안 작성 | 미완 |

---

## 보존 코드 (이번 논문 미사용, 후속 연구용)

- `25_vulnerability_component.py` — V 컴포넌트 (취약인구 비율)
- `26_tavi_index.py` — TAVI 지수 (reduction_pct × vulnerability_ratio)
- `27_link_criticality.py` — 링크 임계성 분석

---

## 투고 목표

- 1순위: Landscape and Urban Planning (SCI Q1, IF ~8)
- 2순위: Urban Climate (SCI Q1, IF ~6)
- 일정: 2026년 7월 중순
