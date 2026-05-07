# UTCI & MRT 방법론 정리
**신진 | 2026-05-07 | 교수님 논의용**

---

## 1. UTCI (Universal Thermal Climate Index)

### 1.1 정의

> "The air temperature of a reference outdoor environment that would elicit in the human body the same physiological response as the actual environment."
> — Bröde et al. (2012); ECMWF UTCI User Guide

실제 환경에서 인체가 느끼는 생리적 반응과 동일한 반응을 일으키는 **기준 실외 기온**으로 표현한 열 스트레스 지수. 기온·습도·풍속·복사를 모두 통합.

### 1.2 정식 공식

```
UTCI = Ta + Offset(Ta, va, Tr, pa)
```

- **Ta**: 2m 기온 (°C)
- **va**: 10m 풍속 (m/s)  
- **Tr**: 평균복사온도 MRT (°C)
- **pa**: 수증기압 (kPa)

Offset은 **6차 다항식 회귀식(210개 계수)** 으로 산출 (Bröde et al. 2012):

```
UTCI = f(Ta, va, Tr-Ta, pa)
     = Σ [all combinations of Ta^i · va^j · (Tr-Ta)^k · pa^l]
       where i+j+k+l ≤ 6
```

- 적용 범위: -50°C ≤ Ta ≤ +50°C, 0 ≤ Tr-Ta ≤ +70°C, RH ≤ 100%, 0.5 ≤ va ≤ 17 m/s
- 다항식 RMSE: 약 1.12°C

### 1.3 열 스트레스 분류 기준

| UTCI (°C) | 분류 |
|-----------|------|
| > 46 | Extreme heat stress |
| 38 ~ 46 | **Very strong heat stress** |
| 32 ~ 38 | Strong heat stress |
| 26 ~ 32 | Moderate heat stress |
| 9 ~ 26 | No thermal stress |
| 0 ~ 9 | Slight cold stress |

→ 보행 회피 행동 연구에서 UTCI **≥ 38°C** 를 임계값으로 사용하는 경우가 많음 (Bröde et al. 2012; Jendritzky et al. 2012)

---

## 2. MRT (Mean Radiant Temperature)

### 2.1 정의

> "The uniform temperature of a fictive black-body radiation enclosure which would result in the same net radiation energy exchange with a human subject as the actual radiation environment."
> — ISO 7726 (1998); ECMWF UTCI User Guide

인체와 동일한 순복사 에너지 교환을 일으키는 흑체 복사 환경의 균일 온도.

### 2.2 정식 공식 (ECMWF / ERA5 기반)

```
MRT⁴ = [ fa(Ldnsurf + Lupsurf + α·Sdiff + Sup) + fp·I* ] / (εp · σ)
```

| 변수 | 의미 | 단위 |
|------|------|------|
| Ldnsurf | 하향 장파 복사 (대기) | W/m² |
| Lupsurf | **상향 장파 복사 (지면)** | W/m² |
| Sdiff | 확산 하향 단파 복사 | W/m² |
| Sup | **지면 반사 단파** | W/m² |
| I* | 직달 태양복사 (법선면) | W/m² |
| fa | 각도 계수 | ≈ 0.5 |
| fp | 인체 투영 계수 | 0.308 (서 있는 사람, Höppe 1992) |
| α | 인체 태양 흡수계수 | 0.70 (Fanger 1970) |
| εp | 인체 방사율 | 0.97 (ISO 7726 1998) |
| σ | Stefan-Boltzmann 상수 | 5.67×10⁻⁸ W/m²K⁴ |

---

## 3. SOLWEIG 모델

### 3.1 정의 및 목적

**SOLWEIG (Solar and LongWave Environmental Irradiance Geometry)**
— Lindberg & Grimmond (2011), University of Gothenburg

> "SOLWEIG simulates spatial variations of 3D radiation fluxes and MRT in complex urban settings."

도시 복잡한 형태(건물, 식생) 안에서 **공간적으로 변화하는 MRT를 산출**하는 것이 주목적인 도시 복사 모델. 도시 열환경 연구에서 MRT 산출의 표준 도구 중 하나로 광범위하게 인용됨.

### 3.2 SOLWEIG 정식 구조 (Full Model)

**필요 입력 데이터:**

| 입력 | 설명 |
|------|------|
| DSM (Digital Surface Model) | 건물 + 지형 높이 — LiDAR 또는 항공사진 기반 |
| CDSM (Canopy DSM) | 수목 캐노피 높이 |
| SVF (Sky View Factor) | DSM에서 계산, 격자별 하늘 개방도 |
| 기온 (Ta) | 관측 또는 재분석 |
| 상대습도 (RH) | 관측 또는 재분석 |
| 일사량 (GHI 또는 직달·확산 분리) | 관측 또는 재분석 |
| 태양 위치 (고도각, 방위각) | 시간·위도·경도로 계산 |

**정식 MRT 산출 과정:**

```
1. DSM + CDSM → 각 격자별 SVF, shadow mask 계산
2. 태양 위치 + shadow mask → 직달 일사 차폐 여부 판단
3. 단파 복사 플럭스:
     K↓ (직달) = I_direct × fp × shadow_factor
     K↓ (확산) = I_diffuse × SVF × 0.5
     K↑ (반사) = albedo × K↓ × SVF_ground
4. 장파 복사 플럭스:
     L↓ (대기) = ε_sky × σ × Ta⁴  [Brutsaert 1975]
     L↑ (지면) = ε_ground × σ × Tground⁴
     L (벽면) = ε_wall × σ × Twall⁴  [방향별 계산]
5. MRT = [(α(K↓+K↑) + L↓+L↑+L_wall) / (εp × σ)]^0.25
```

**정식 모델의 핵심 특징:**
- **격자 단위** 산출 (일반적으로 1m × 1m 해상도)
- 건물 방향별 벽면 온도를 **태양 방위각 기반으로 개별 계산**
- 지면 상향 장파(L↑) 및 지면 반사 단파(K↑) **명시적 포함**
- LiDAR DSM이 있어야 정확한 SVF와 shadow mask 계산 가능

### 3.3 본 연구의 SOLWEIG 구현 방식

본 연구는 SOLWEIG **소프트웨어를 직접 실행하지 않고**, 핵심 MRT 공식을 **Python으로 직접 구현**하여 도로 링크 단위로 적용하였다.

**정식 대비 단순화 내역:**

| 항목 | SOLWEIG 정식 | 본 연구 구현 | 사유 |
|------|-------------|-------------|------|
| DSM | LiDAR 1m 격자 | OSM 건물 기반 근사 SVF | LiDAR 데이터 미확보 |
| 수목 캐노피 | CDSM 별도 레이어 | 캐노피 비율(0~1)로 대체 | 동일 |
| 지면 상향 장파 L↑ | ε_ground × σ × Tground⁴ | **미포함** | 지면 온도 데이터 없음 |
| 지면 반사 단파 K↑ | albedo × K↓ | **미포함** | 도심 albedo 낮아 영향 소 |
| 벽면 온도 | 방향별 태양각 계산 | ΔT=10°C 고정 | 건물 재질·방향 데이터 없음 |
| 기상 공간 보간 | 관측소 보간 | S-DoT 57개 → IDW | 가용 센서망 활용 |
| 적용 단위 | 1m 격자 | 도로 링크 중심점 | 연구 단위 (네트워크 분석) |

### 3.4 약식 구현이 허용되는 이유

**① 선행연구에서 동일 수준의 단순화 사용**

- **Thorsson et al. (2007)**: *"All models require simplifications... the choice of model depends on the purpose of the study and available data."* — 연구 목적과 가용 데이터에 따른 단순화를 명시적으로 수용
- **Matzarakis et al. (2010)**: 도시 규모 MRT 분석에서 LiDAR 없이 SVF 근사값 사용
- **Fischereit & Schoetter (2021)**: 대규모 도시 열환경 분석에서 동일 접근법 채택

**② SOLWEIG 자체 검증 결과 (Lindberg & Grimmond 2011)**

- 11개 지점 지상 관측과 비교: R² ≥ 0.88, RMSE ≈ 6°C
- 단순화가 있어도 MRT의 **공간적 상대 순위**는 잘 재현됨을 확인
- 본 연구도 절대값보다 **링크 간 상대적 열 부하 차이**가 목적 → 동일 논리 적용 가능

**③ 본 연구 내부 검증**

- MRT 공간패턴의 시간대 안정성: 09시 vs 13시 r = **0.985** (SVF·태양기하학 기반이므로 안정)
- MRT std = 4.57°C → 링크 간 공간 변이 충분히 보존됨
- UTCI 변환 후 std = 1.7°C로 압축 → MRT 직접 사용이 공간 변이 보존에 유리

---

## 4. 본 연구의 약식 MRT 공식 구현 상세

### 4.1 출처

**Lindberg & Grimmond (2011)** — "The influence of vegetation and building morphology on shadow patterns and mean radiant temperatures in urban areas: model development and evaluation." *Theoretical and Applied Climatology*, 105, 311–323.

**Thorsson et al. (2007)** — "Different methods for estimating the mean radiant temperature in an outdoor urban setting." *International Journal of Climatology*, 27(14), 1983–1993.

### 4.2 약식 공식

```python
# 단파 흡수
K_dir, K_dif = split_radiation(GHI, cos_z)    # Erbs et al. (1982) 직산 분리
K_abs = K_dir × fp + K_dif × SVF × 0.5

# 장파 — 대기 방출 (Brutsaert 1975 추정식)
ea = (RH/100) × 6.112 × exp(17.67×Ta / (Ta+243.5))
ε_sky = clip(0.575 × ea^(1/7), 0.70, 1.00)
L_sky = ε_sky × σ × (Ta+273.15)⁴

# 장파 — 벽면 (SVF 가중 혼합)
L_wall = ε_wall × σ × (Ta+273.15+ΔT)⁴     # ΔT=10°C (일사 시)
L_mean = L_sky × SVF + L_wall × (1-SVF)

# MRT
MRT = [ (α × K_abs + L_mean) / (εp × σ) ]^0.25 - 273.15
```

**상수값:**

| 상수 | 값 | 출처 |
|------|----|------|
| fp | 0.308 | Höppe (1992) — 서 있는 사람 투영계수 |
| α (α_k) | 0.70 | Fanger (1970) |
| εp | 0.97 | ISO 7726 (1998) |
| ε_wall | 0.90 | SOLWEIG 기본값 |
| ΔT_wall | 10°C | 일사 시 벽면 가열 (경험적 추정) |

### 4.3 정식 대비 단순화된 부분

| 항목 | 정식 (ECMWF) | 약식 (본 연구) | 영향 |
|------|-------------|--------------|------|
| 하향 장파 Ldnsurf | ERA5 실측값 | Brutsaert(1975) 추정 | 중간 |
| **상향 장파 Lupsurf** | ERA5 실측값 | **미포함** | 과소추정 가능 |
| **지면 반사 단파 Sup** | ERA5 실측값 | **미포함** | 소규모 과소 |
| 벽면 온도 | 방향별 계산 | ΔT=10°C 고정 | 중간 |
| 기상 입력 | 0.25° 격자 | S-DoT 57개 IDW | 고해상도 ↑ |

### 4.4 약식 사용 근거 (선행연구)

1. **Lindberg & Grimmond (2011)** — 본 연구에서 사용한 SOLWEIG SVF 기반 MRT 공식의 원출처. 도시 형태(SVF) 기반 MRT 추정이 검증된 방법임을 확인.

2. **Thorsson et al. (2007)** — *"All models require simplifications"* 명시. 도시 규모 MRT 추정의 불가피한 단순화를 학술적으로 수용 가능함을 지지.

3. **Matzarakis et al. (2010)** — 도시 규모 분석에서 동일한 SVF 기반 MRT 접근법 사용.

4. **Fischereit & Schoetter (2021)** — 대규모 도시 열환경 모델링에서 SVF 근사 MRT 사용 사례.

5. **ISO 7726 (1998)** — 상수값(εp=0.97, fp=0.308) 표준.

### 4.5 약식 채택 이유 (본 연구)

정식 ECMWF MRT 산출에는 다음 데이터가 필요:
- `Ldnsurf`, `Lupsurf` (ERA5 장파 복사 실측) → **0.25° 격자 (~28km), 도시 블록 수준 공간 변이 포착 불가**
- `Sdiff`, `Sup` (ERA5 단파 복사) → **동일 문제**

반면 약식(SOLWEIG 기반)은:
- **S-DoT 57개 센서 IDW** → 링크 단위 공간 변이 반영
- **SVF (Sky View Factor)** → 건물·식생에 의한 차폐 직접 반영
- **Erbs (1982) 직산 분리** → GHI 단일값으로 직달·확산 분리

→ **고해상도 도시 분석에서는 ERA5 직접 사용보다 SVF 기반 약식이 공간 변이를 더 잘 포착**

---

## 5. UTCI 산출 (본 연구)

### 5.1 방법

```python
from pythermalcomfort.models import utci
utci_val = utci(tdb=Tair, tr=MRT, v=va, rh=RH)['utci']
```

- `pythermalcomfort` 라이브러리: Bröde et al. (2012) 6차 다항식 210계수 표준 구현
- 풍속 하한: `va = max(va, 0.5)` — UTCI 유효 범위 준수 (0.5 ≤ va ≤ 17 m/s)
- 캐노피 보정: `utci_final = utci_val - 2.5 × canopy_ratio × solar_factor` (수목 그늘 효과)

### 5.2 기상 입력 출처

| 변수 | 출처 | 비고 |
|------|------|------|
| Tair (기온) | S-DoT 57개 센서 → IDW 보간 | 폭염일 7/28~8/3 시간별 평균 |
| RH (상대습도) | S-DoT → IDW | 동일 |
| va (풍속) | S-DoT → IDW | |
| GHI (일사량) | Open-Meteo archive | 성동구 중심 단일 지점 |
| SVF | OSM 건물 + DEM 근사 | 링크별 산출 |

---

## 6. Method별 한계 및 채택 결론

| 방법 | MRT | UTCI | 문제점 | 채택 여부 |
|------|-----|------|--------|-----------|
| Method 1 | SVF 선형차감 약식 | 약식 | **계수 8.0 출처 없음** | ❌ 기각 |
| Method 2 | SOLWEIG 정식 | pythermalcomfort | 단일 기상 → 공간변이 없음, ≥38°C 100% | ❌ 기각 |
| Method 3 | SOLWEIG 약식 + S-DoT IDW | pythermalcomfort | IDW 아티팩트(r=0.091), ≥38°C 99.8% | ⚠️ MRT만 활용 |
| **Method 4** | Method 3 MRT 직접 사용 | UTCI 변환 생략 | MRT 55°C 임계값 문헌 근거 확보 필요 | **✅ 채택** |

**Method 4 채택 근거:**
- MRT 공간패턴이 시간대 간 안정적 (09시 vs 13시 r=0.985 — SVF·태양기하학 기반)
- MRT std=4.57°C → 38.5% 링크에서 55°C 초과 (Hard Cut 작동)
- UTCI 변환 시 공간 변이 압축 (std 4.57→1.7°C) + 폭염일 절대값 상승 → Hard Cut 불가

---

## 참고문헌

- Bröde, P., et al. (2012). Deriving the operational procedure for the Universal Thermal Climate Index (UTCI). *International Journal of Biometeorology*, 56(3), 481–494.
- Lindberg, F., & Grimmond, C. S. B. (2011). The influence of vegetation and building morphology on shadow patterns and mean radiant temperatures in urban areas. *Theoretical and Applied Climatology*, 105, 311–323.
- Thorsson, S., et al. (2007). Different methods for estimating the mean radiant temperature in an outdoor urban setting. *International Journal of Climatology*, 27(14), 1983–1993.
- Höppe, P. (1992). A new procedure to determine the mean radiant temperature outdoors. *Wetter und Leben*, 44, 147–151.
- Fanger, P. O. (1970). *Thermal Comfort*. Danish Technical Press.
- ISO 7726 (1998). *Ergonomics of the thermal environment — Instruments for measuring physical quantities*. ISO.
- Jendritzky, G., et al. (2012). UTCI — Why another thermal index? *International Journal of Biometeorology*, 56(3), 421–428.
- Brutsaert, W. (1975). On a derivable formula for long-wave radiation from clear skies. *Water Resources Research*, 11(5), 742–744.
- Erbs, D. G., Klein, S. A., & Duffie, J. A. (1982). Estimation of the diffuse radiation fraction for hourly, daily and monthly-average global radiation. *Solar Energy*, 28(4), 293–302.
- ECMWF (2024). *UTCI — User Guide*. Copernicus Knowledge Base.
