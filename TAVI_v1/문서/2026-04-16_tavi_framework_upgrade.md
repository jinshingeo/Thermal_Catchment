# TAVI 연구 방향 확정 보고서 — v2 (2026-04-16)

> 분석 버전: TAVI_v2  
> 작성자: jinshingeo  
> 투고 목표: SCI Q1 (Landscape and Urban Planning 또는 Urban Climate)

---

## 1. 오늘 확정된 핵심 결정사항

### 1-1. UTCI 산출 방식 통일

**변경 전**: 소프트 패널티(11번)는 IDW 보간 UTCI, 하드 컷(20번)은 SOLWEIG 기반 UTCI  
**변경 후**: 두 방식 모두 **SOLWEIG 기반 UTCI(`link_utci_solweig.csv`)로 통일**

```python
# 11_thermal_catchment.py 수정 내용
UTCI_PATH = 'link_utci_solweig.csv'      # IDW → SOLWEIG
utci_col  = 'utci_final'                  # utci_idw → utci_final
default   = utci_hourly_mean.get(hour)    # 33.0 고정 → 시간대별 평균값
```

근거: 두 catchment 방식의 결과 차이가 UTCI 데이터 차이에서 오는지, 모델링 방식 차이에서 오는지 분리 불가능했기 때문. 통일 후 순수하게 방법론 차이만 비교 가능.

---

### 1-2. 방법론 단순화 — 소프트 패널티 폐기

**변경 전**: 소프트 패널티(α=0.15) + 하드 컷 두 가지 병행  
**변경 후**: **하드 컷(UTCI ≥ 38°C 링크 제거) 단일 방법론으로**

```
폐기 이유:
  α = 0.15 — 문헌 근거 없는 임의 설정값
  SCI 심사에서 "왜 0.15인가?" 방어 불가능

채택 이유:
  38°C 임계값 — Bröde et al.(2012) 국제 기준 명확
  "very strong heat stress" 시작점 = 보행 회피 기준으로 방어 가능
```

소프트 패널티는 sensitivity case 또는 후속 연구로 남김.

---

### 1-3. 프레임워크 확장 결정: H×E×V 도입

**IPCC AR6 표준 위험도 공식 채택**:

```
Risk = Hazard × Exposure × Vulnerability

TAVI(역) = reduction_pct(%) × vulnerability_ratio

  H (Hazard)     : UTCI 기반 열환경 (SOLWEIG)
  E (Exposure)   : Thermal Catchment reduction_pct
                   = (Classic - Thermal) / Classic × 100
  V (Vulnerability): 역 Catchment 내 취약인구 비율
                   = (65세 이상 인구 + 14세 이하 인구) / 전체 인구
```

**Kar et al.(2023) 연결**:

| Kar et al. 개념 | TAVI 대응 |
|----------------|-----------|
| Hard constraint | H × E (물리적 열환경 장벽) |
| Soft constraint | V (취약 집단일수록 패널티 강화) |

---

### 1-4. V 컴포넌트 지표 확정

**사용 지표: 고령인구(65세 이상) 비율 + 어린이(14세 이하) 비율**

```
vulnerability_ratio = (65세+ 인구 + 14세- 인구) / 전체 인구
                    (행정동 단위 → 역 Catchment 내 가중 평균)
```

근거:
- 고령자: 체온 조절 능력 저하, 만성질환 동반, 폭염 사망 위험 높음
- 어린이: 체표면적 대비 열 흡수 많음, 스스로 회피 어려움
- 두 집단 모두 대중교통 의존도 높음 (자가용 운전 불가)

데이터 출처: 통계청 SGIS 행정동별 연령별 인구 (수집 예정)

---

### 1-5. 검증(Validation) 전략 확정

**방법**: 역별 폭염일 vs 비폭염일 승하차 감소율 × reduction_pct 상관

```
heat_ratio(역) = 폭염일 평균 승하차 / 비폭염일 평균 승하차

가설: TAVI ↑ → heat_ratio ↓
     (열 취약 역일수록 폭염일에 더 많이 감소)
```

**필요 데이터**: 일별 승하차 데이터 (수집 예정)  
**폭염일 정의**: 해당 날 13시 UTCI ≥ 38°C (SOLWEIG 기반)  
**비폭염일 정의**: 동월 내 13시 UTCI < 32°C 인 날

---

## 2. 방법론 비판적 검토 결과

### 주관적 파라미터 현황

| 파라미터 | 값 | 상태 | 처리 방향 |
|---------|-----|------|----------|
| UTCI 임계값 38°C | Bröde et al. 2012 | ✅ 방어 가능 | 유지 |
| WALK_SPEED 4.5km/h | 일반 문헌 범위 | ⚠️ 민감도 분석 필요 | 10·15·20분 범위 |
| TIME_BUDGET 15분 | Moreno et al. 2021 | ✅ 방어 가능 | 유지 |
| CANOPY_COEFF 2.5°C | Chen & Ng 2012 | ⚠️ 하한값 | 한계로 명시 |
| MRT 계수 0.5 | 경험적 단순화 | ❌ 검증 없음 | 한계로 명시 |
| α = 0.15 | 근거 없음 | ❌ 폐기 | 소프트 패널티 전체 폐기 |

### 검증 부재 항목 (한계로 서술)
- MRT 단순화 vs 실제 SOLWEIG 결과 비교 없음
- BULD_BUFFER(20m), CANOPY_BUFFER(15m) 민감도 미실시
- V 가중치 단순 합산(고령+어린이) 근거 약함 → IPCC 프레임으로 방어

---

## 3. 논문 타임라인

```
2026-04-16 ~ 04-30 (2주)
  - 일별 승하차 API 수집 (OA-12914)
  - 통계청 SGIS 취약인구 데이터 수집
  - V 컴포넌트 계산 및 TAVI 지수 산출

2026-05-01 ~ 05-15 (2주)
  - 학회 초록 제출
  - 학회 발표자료 작성
  - 민감도 분석 (TIME_BUDGET, THRESHOLD)

2026-05-16 ~ 06-30 (6주)
  - 검증 분석 완료
  - 논문 초안 작성 (전체)

2026-07-01 ~ 07-15
  - 논문 최종 수정 및 투고

2026-09월
  - 석사 논문 심사
```

---

## 4. 목표 저널

| 저널 | IF | 비고 |
|------|-----|------|
| Landscape and Urban Planning | ~7 | **1순위** — 방법론+도시 적용 |
| Urban Climate | ~6 | **2순위** — 열환경+이동성 |
| Annals of AAG | ~5 | 이론 기여 강조 시 |

---

## 5. 후속 연구로 남길 것 (박사 과정 연결)

```
1. 개인 수준 Soft constraint (Kar et al. 방향) — 설문 기반
2. 완전한 STP 프레임워크로 확장
3. 다른 도시 적용 (일반화 가능성 검증)
4. V 지표 고도화 (만성질환자, 냉방 미접근 가구)
5. AHP 기반 가중치 체계
6. 폭염 시나리오별 TAVI 변화 예측 (RCP 기후 시나리오)
```

---

## 6. 참고문헌 (오늘 확정된 핵심)

- Bröde et al. (2012) — UTCI 임계값 38°C 근거
- Lindberg et al. (2008) — SOLWEIG MRT 계산
- Kar, Le & Miller (2023) — Inclusive STP, Hard/Soft constraint
- IPCC AR6 (2021) — Risk = H×E×V 표준 공식
- Moreno et al. (2021) — 15분 도시, TIME_BUDGET 근거
- Chen & Ng (2012) — 캐노피 UTCI 감소 계수
