# STP 연구에서 TAVI로 — 연구 방향 전환 맥락
**작성일**: 2026-04-10  
**작성자**: jinshingeo

---

## 1. 출발점: 성동구_STP연구 (2026년 3월~4월 초)

### 초기 연구 질문
> "폭염 시간대에 열환경을 반영했을 때 보행 STP의 PPA가 얼마나 감소하는가?"

### 방법론 (v3_asos까지)
- **데이터**: S-DoT 57개 센서 온습도 + ASOS 풍속·일사량 → UTCI 계산
- **분석**: 응봉동 단일 출발지 → Dijkstra → Classic PPA vs Thermal PPA
- **모델**: 속도계수 변환 (UTCI → 0.2~1.0 보행속도 계수)
- **비교**: 응봉동(열취약) vs 성수동(열완충) — 2개 지역 비교

### 완성된 결과 (v3_asos, 2026-04-01)
- Classic PPA: 2,529노드 (45.7%)
- 13시 응봉동 Thermal PPA: 11.1% (-82.4%)
- 13시 성수동 Thermal PPA: 6.3% (-69.2%)
- 3D STP 프리즘 시각화 완성

---

## 2. 전환점: 교수님 미팅 (2026-04-09)

### 교수님 피드백 요약

| 지적 사항 | 내용 |
|----------|------|
| STP 구현 | "코드로 STP 프리즘 자체를 만들어야 한다" |
| 링크 스코어 | Kar et al.(2024) Fig.4처럼 전체 도로망 링크별 시각화 필요 |
| 링크 가중치 | 각 링크에 열환경 가중치 부여 방안 |
| 극단값 민감도 | STP가 동심원이 아닌 모양으로 줄어드는 조건 |
| 변수 선택 | 열 노출 완화 변수(나무, 그늘막) → PCA/SVM |

### 미팅 후 추가 방향 논의
교수님 피드백 이후 연구 방향을 재검토하면서 더 큰 문제의식으로 확장:

**기존 한계**: 단일 출발지(아파트 단지) → PPA 계산 → 두 지역 비교  
→ "그래서 이게 누구에게 어떤 정책적 시사점이 있나?"라는 질문에 답하기 어려움

**새 방향**: 전체 역세권 접근 가능 주민 수 / 역까지 도달 못하는 주민 범위  
→ "폭염 시 어느 역에서, 어떤 주민들이 대중교통 접근성을 잃는가?"

---

## 3. 전환 논리: STP → TAVI

### 왜 Catchment 기반으로 바꿨나

**PPA (기존)**
```
단일 출발지 A → B까지 30분 내 이동 가능한 공간
= "이 사람이 갈 수 있는 곳"
```

**Thermal Catchment (새)**
```
역 → 역방향 Dijkstra → 30분 내 역에 도달 가능한 모든 노드
= "이 역을 이용할 수 있는 주민 범위"
```

**차이**: PPA는 한 개인의 이동 가능 공간. Catchment는 역 서비스 권역.  
정책 관점에서 Catchment가 훨씬 직관적이고 활용 가능함.

### 왜 TAVI라는 이름인가

Colaninno et al. (2024)의 H×E×V (Hazard × Exposure × Vulnerability) 프레임워크에서 영감:

| 요소 | 정의 | 본 연구에서의 측정값 |
|------|------|---------------------|
| **H** (Hazard) | 열 위험도 | 역 catchment zone 평균 UTCI |
| **E** (Exposure) | 노출 정도 | reduction_pct (접근성 감소율) |
| **V** (Vulnerability) | 취약성 | 고령인구 비율, 차 없는 가구 비율 (Plan B) |

→ **TAVI = Thermal Accessibility Vulnerability Index**  
→ "기존에 없는 신규 제안 용어" — 기존 TVI(Thermal Vulnerability Index)나 TAI(Transit Accessibility Index)와 구분되며, 접근성+열환경+취약성의 세 개념을 결합한 최초의 명시적 지수.

---

## 4. 연구 방향 확정 (2026-04-10)

### Plan A (우선 실행)
**공간환경이 Catchment 감소를 설명한다**

- 종속변수: reduction_pct (역별 × 시간대별)
- 독립변수: NDVI, 불투수면, 건물높이, 하천거리, 가로수 밀도
- 분석: OLS 회귀 or GWR (공간 이질성 반영)
- 결과: "어떤 공간 조건이 역세권 접근성 감소를 유발하는가"

### Plan B (Plan A 완성 후 확장)
**H×E×V 프레임워크로 TAVI 지수 산출**

- H: 링크 평균 UTCI → catchment zone 집계
- E: reduction_pct
- V: 고령인구 + 자가용 미보유 가구 + 수급자 비율 (동별)
- 결과: 성동구 동별 TAVI 지도 + "누가 가장 위험한가"

---

## 5. STP 연구에서 계승한 것들

| 항목 | STP 연구에서 | TAVI에서 |
|------|------------|---------|
| UTCI 계산 파이프라인 | v3_asos (완성) | 동일 데이터 재사용 |
| 링크별 UTCI | `link_utci_by_hour_v3.csv` | 동일 파일 사용 |
| 보행 네트워크 | `seongdong_walk_network.graphml` | 동일 네트워크 사용 |
| 열 패널티 모델 | 속도계수 (0.2~1.0) | **penalty(0~4) × α로 전환** |
| 응봉 vs 성수 비교 | 2개 지역 PPA | 2개 역 Catchment → 7개 역으로 확장 |
| 3D STP 코드 | 10_stp_prism_v2.py | 참고용 보관 (TAVI 본체는 아님) |

---

## 6. 데이터 흐름

```
성동구_STP연구/
  └── 02_기상데이터/link_utci_by_hour_v3.csv  ──┐
  └── 01_네트워크/seongdong_walk_network.graphml ┤ (symlink 또는 경로 참조)
                                                 ↓
TAVI/
  └── 04_분석결과/11_thermal_catchment.py       (응봉·성수 2개 역)
  └── 04_분석결과/12_catchment_all_stations.py  (7개 역 전체)
  └── 04_분석결과/catchment_all_stations_table.csv  ← Plan A 종속변수
```

> 대용량 데이터(graphml, csv)는 TAVI 레포에 복사하지 않고  
> 경로 참조로 성동구_STP연구 폴더를 공유 사용.

---

## 7. 참고 문헌

- Colaninno, N., et al. (2024). Pedestrian thermal comfort and heat exposure. *Environment and Planning B*.
- Kar, A., et al. (2024). Inclusive accessibility. *CEUS*, 114, 102202.
- Miller, H. J. (1991). Modelling accessibility using STP in GIS. *IJGIS*, 5(3).
