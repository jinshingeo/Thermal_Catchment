# SOLWEIG & Erbs 모델

## SOLWEIG

### 한 줄 정의
> 도시 환경에서 **링크별 MRT를 계산하는 복사 모델** — SVF·태양 기하학·단파/장파 복사를 종합

### 원래 SOLWEIG란?
Lindberg & Grimmond(2011)이 개발한 소프트웨어로, 도시 캐니언 내 복사 환경을 시뮬레이션합니다. 고해상도 DSM(수치표면모델)을 입력받아 각 지점의 MRT를 계산합니다.

### 이 연구에서 어떻게 썼나?
SOLWEIG 소프트웨어를 직접 실행하지 않고, **핵심 복사 플럭스 수식을 Python으로 직접 구현**했습니다. 이를 "SOLWEIG 약식(simplified)" 이라고 표현합니다.

**단파복사 항** ($K_{sw}$):
$$K_{sw} = \alpha_p \left[(1-SVF) \cdot K_{dif} + shadow \cdot K_{dir} \cdot \cos\theta + SVF \cdot K_{dif}\right]$$

**장파복사 항** ($L_{lw}$):
$$L_{lw} = \epsilon_p \left[SVF \cdot L_{sky} + (1-SVF) \cdot L_{wall}\right]$$

**MRT 최종 계산**:
$$T_{mrt} = \left[\frac{K_{sw} + L_{lw}}{\sigma}\right]^{0.25} - 273.15$$

### 주요 파라미터

| 파라미터 | 값 | 의미 |
|---------|-----|------|
| $\alpha_p$ | 0.70 | 인체 단파 흡수율 |
| $\epsilon_p$ | 0.97 | 인체 장파 방출률 |
| $\epsilon_w$ | 0.95 | 건물벽면 방출률 |
| $\Delta T_{wall}$ | +5 K | 벽면 온도 = 기온 + 5°C 가정 |
| $\sigma$ | $5.67 \times 10^{-8}$ W/m²K⁴ | Stefan-Boltzmann 상수 |

---

## Erbs 모델

### 한 줄 정의
> **GHI 하나만 있으면** DNI(직달일사량)와 DHI(확산일사량)로 분리해주는 경험적 공식

### 왜 필요한가?
Open-Meteo에서는 GHI(전체 일사량)만 제공합니다. 하지만 MRT 계산에는 직달과 산란을 **따로** 알아야 합니다 (그림자인지 아닌지에 따라 직달만 차단되기 때문).

### 공식 (간략히)
태양의 위치(천정각 $\theta$)와 GHI를 이용해서 청천지수($k_t = GHI / I_0$)를 계산하고, 이로부터 DHI 비율을 경험식으로 추정합니다.

$$DHI = f(k_t) \times GHI, \quad DNI = \frac{GHI - DHI}{\cos\theta}$$

### 대안

| 방법 | 특징 |
|------|------|
| **Erbs (이 연구)** | 단순·널리 검증됨 |
| **Perez 모델** | 더 정확하지만 복잡 |
| **실측 분리** | 직달·산란 센서 별도 필요 |

---

## 전체 연결 흐름

```
Open-Meteo GHI
     ↓ Erbs 모델
DNI + DHI
     ↓
     + SVF (OSM 건물)
     + Tair, RH (S-DoT IDW)
     + 태양 기하학 (위도·경도·시간)
     ↓ SOLWEIG 약식
링크별 MRT
     ↓
MRT ≥ 55°C → Hard Cut → Thermal Catchment
```

---

## 관련 개념
- [[MRT]] — 이 모델의 최종 출력값
- [[SVF]] — 핵심 입력 변수
- [[GHI_DNI_DHI]] — Erbs 모델의 입출력
