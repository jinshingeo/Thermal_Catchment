# MRT 산출 방법론 해설

> **목적**: 내 연구의 MRT 계산 코드를 처음부터 단계별로 설명하고,  
> 풀 SOLWEIG 모형과의 차이를 할루시네이션 없이 명확히 기록한다.  
> **근거 문헌**: Lindberg, Onomura & Grimmond (2016) *Int J Biometeorol* 60:1439–1452 (`s00484-016-1135-x.pdf`)  
> **코드 파일**: `15_svf_per_link.py`, `39_utci_sdot_solweig.py`

---

## 1. MRT란 무엇인가

**Mean Radiant Temperature (MRT, T_mrt)** 는  
사람에게 사방에서 도달하는 **단파(태양)·장파(열) 복사열의 합**을  
하나의 온도값으로 표현한 지표다.

공기 온도(T_air)와 달리, MRT는 햇빛이 직접 닿는지, 그늘인지,  
주변 건물 벽이 뜨거운지 등에 따라 **같은 골목 내에서도 수십°C 차이**가 날 수 있다.  
이 때문에 도시 열환경의 공간 분화를 포착하는 데 핵심 변수로 쓰인다.

> 근거: "T_mrt shows larger spatial variation over short distances"  
> (Lindberg et al. 2016, p.1439 Introduction)

---

## 2. MRT 계산의 기본 물리 공식

모든 MRT 계산의 기초는 **Stefan-Boltzmann 역산**이다.

사람 몸에 흡수되는 총 복사량 R (W/m²):

```
R = ξ_k × Σ(K_i × F_i) + ε_p × Σ(L_i × F_i)    [i = 1 to 6]
```

여기서 R로부터 MRT를 역산:

```
T_mrt (K) = ( R / (ε_p × σ) )^0.25
T_mrt (°C) = T_mrt(K) - 273.15
```

| 기호 | 의미 | 값 | 근거 |
|------|------|-----|------|
| ξ_k | 인체 단파복사 흡수 계수 | 0.70 | Fanger (1970) |
| ε_p | 인체 장파복사 방사율 | 0.97 | ISO 7726 (1998) |
| σ | Stefan-Boltzmann 상수 | 5.67×10⁻⁸ W/m²K⁴ | 물리상수 |
| K_i | 방향 i에서 오는 단파복사 | — | 계산값 |
| L_i | 방향 i에서 오는 장파복사 | — | 계산값 |
| F_i | 방향 i의 각도 가중계수 | 0.22(사방), 0.06(상·하) | Höppe (1992) |

이 공식은 풀 SOLWEIG도, 내 연구의 약식도 동일하게 사용한다.  
**차이는 K_i와 L_i를 어떻게 계산하느냐에 있다.**

---

## 3. 풀 SOLWEIG 모형의 MRT 산출 방식

> 근거: Lindberg, Onomura & Grimmond (2016) 전체; Lindberg & Grimmond (2011b)

### 3.1 계산 높이

**z = 1.1 m** (지면 위 1.1m = 서 있는 사람의 무게 중심 높이)

> "This height (z=1.1 m) represents the centre of mass of a standing human  
> but can be altered accordingly."  
> (Lindberg et al. 2016, p.1442)

### 3.2 입력 데이터 요구사항

| 입력 | 내용 |
|------|------|
| T_a | 기온 |
| RH | 상대습도 |
| G | 전천일사량 (global) |
| I | 직달일사 (direct) |
| D | 산란일사 (diffuse) |
| DSM | 건물 수치표면모델 (pixel resolution 1m) |
| CDSM | 식생 캐노피 수치표면모델 |
| 위도·경도·고도 | 태양 기하학 계산용 |

### 3.3 SVF 계산 방법

DSM(수치표면모델)을 이용해 **픽셀 단위 fisheye 투영**으로 SVF를 계산.

- 검색 방향: 0°~359°를 **20° 간격** (18방향)
- 최대 검색 거리: 관측 높이의 20배 (z=1.1m이면 약 22m)
- 건물 SVF (Ψ_sky_b)와 식생 SVF (Ψ_sky_v)를 **별도 계산**

> "For each pixel a search is conducted at 20° intervals between 0° and 359°."  
> (Lindberg et al. 2016, p.1442)

### 3.4 그림자 계산

DSM + CDSM의 **pixel-level 그림자 투영 알고리즘** 적용.  
각 픽셀이 해당 시각에 햇빛을 받는지(sunlit) 그늘인지(shadow)를  
Boolean 값 S(0 또는 1)로 결정.

### 3.5 단파복사 K_i (6방향)

각 방향(동·서·남·북·상·하)에 대해 개별 계산. 동쪽 방향 예시:

```
K_→E = I[S_b - (1-S_v)(1-τ)]cosη sinϑ
      + (D[1-w] + α_wall[w(G(1-f_s) + Df_s)] + K_↑E) × 0.5
```

| 기호 | 의미 |
|------|------|
| S_b | 건물에 의한 그림자 Boolean |
| S_v | 식생에 의한 그림자 Boolean |
| τ | 식생 단파 투과율 (0.02, 잎 있을 때) |
| η | 태양 고도각 |
| ϑ | 태양 방위각 |
| D | 산란일사 |
| α_wall | 벽면 알베도 |
| f_s | 그늘진 벽면 비율 |
| w | 건물+식생 각도 가중계수 |

### 3.6 장파복사 L_i (6방향)

각 방향에서 오는 장파복사를 하늘, 식생, 벽면, 지면에서 따로 계산:

```
L_→E_sky   = (Ψ_Esky_b + Ψ_Esky_v - 1) × ε_sky × σ × T_a⁴ × w_Esky × 0.5
L_→E_veg   = ε_wall × σ × T_veg⁴ × w_Eveg × 0.5
L_→E_ground = L_↑E × 0.5
...
```

지표면 온도 T_s는 **맑은 날 선형 회귀 파라미터화**로 추정:

- 아스팔트: T_s - T_a = 0.58 × η_max - 10.12 (R²=0.93)
- 잔디: T_s - T_a = 0.21 × η_max - 3.38 (R²=0.67)

> (Lindberg et al. 2016, Table 1 & Fig. 3)

### 3.7 요약: 풀 SOLWEIG의 특징

- 6방향 복사를 **모두 개별 계산** 후 합산
- 1m 해상도 DSM 기반 **픽셀 단위 그림자** 반영
- 관측 높이 **z=1.1m 명시**
- 지표면 유형별(아스팔트, 잔디 등) **온도 파라미터화**
- 식생 투과율(τ=0.02) 반영

---

## 4. 내 연구의 MRT 계산 방식 (SOLWEIG 약식)

> 코드: `15_svf_per_link.py` (SVF 계산), `39_utci_sdot_solweig.py` (MRT 계산)

### 4.1 계산 단위

풀 SOLWEIG: **픽셀(1m × 1m)** 단위  
내 연구: **링크(도로 구간)** 단위 — 링크 중심점(midpoint) 기준

관측 높이 **명시 없음**. 링크 중심점의 (x, y) 좌표만 사용.

---

### 4.2 STEP 1 — SVF 계산 (코드: `15_svf_per_link.py`)

**Oke (1987) H/W Street Canyon 공식** 적용:

```
SVF = 1 / √(1 + (H_eff / W)²)
```

```
H_eff = H_building + 10.0 × canopy_ratio
H_building = 링크 주변 20m 버퍼 내 건물 평균 높이 (지상층수 × 3m)
W = 도로 유형별 표준 폭 (국토부 도로설계기준)
canopy_ratio = 링크 주변 15m 버퍼 내 도시숲 면적 비율
```

| 도로 유형 | 표준 폭(W, m) |
|-----------|--------------|
| trunk | 24.0 |
| primary | 16.0 |
| secondary | 12.0 |
| tertiary | 9.0 |
| residential | 6.0 |
| footway | 3.0 |
| path | 2.0 |

**SVF 해석**:
- SVF = 1.0 → 완전 개활지 (교량, 광장)
- SVF ≈ 0.5 → H/W ≈ 1.0 (6층 건물, 6m 도로)
- SVF ≈ 0.3 → H/W ≈ 3.0 (고층 빌딩 협곡)

> 근거: Oke, T.R. (1987). *Boundary Layer Climates* (2nd ed.). Routledge.

**풀 SOLWEIG와의 차이**:  
풀 SOLWEIG는 DSM fisheye 투영으로 실제 하늘 가림 비율을 픽셀 단위로 계산.  
이 코드는 2D 가로협곡 공식으로 근사 — **높이 지정 없음, 그림자 계산 없음**.

---

### 4.3 STEP 2 — 기상 입력: IDW 보간 (코드: `39_utci_sdot_solweig.py`)

S-DoT 센서 57개소 실측값(기온·상대습도·풍속)을  
**IDW(역거리 가중 보간)**으로 링크 중심점에 할당.

```python
w = 1 / dist²                              # IDW power = 2
interpolated = Σ(w_i × val_i) / Σ(w_i)
```

일사량(GHI)은 Open-Meteo 아카이브 단일 지점값 (성동구 대표 1개소) 사용.  
폭염일 7일 (2025.07.28–08.03) 시간대별 평균으로 정규화.

---

### 4.4 STEP 3 — 직산 분리 (Erbs et al. 1982)

전천일사(GHI)를 직달(K_dir)과 산란(K_dif)으로 분리.

```
kt = GHI / (1367 × cos_z)    # 청명도 지수 (clearness index)

if kt ≤ 0.22:  kd = 1 - 0.09 × kt
if kt ≤ 0.80:  kd = 0.9511 - 0.1604×kt + 4.388×kt² - 16.638×kt³ + 12.336×kt⁴
else:          kd = 0.165

K_dif = GHI × kd
K_dir = GHI × (1 - kd)
```

여기서 `cos_z`는 태양 천정각의 코사인 (위도 37.55°, 경도 127.04°, DOY=210 고정 계산).

> 근거: Erbs, D.G., Klein, S.A., Duffie, J.A. (1982). *Solar Energy* 28(4):293–302.

---

### 4.5 STEP 4 — 단파복사 흡수량 계산

```python
K_abs = K_dir × FP + K_dif × svf × 0.5
```

| 항 | 의미 |
|---|---|
| K_dir × FP | 직달 태양복사 중 인체에 흡수되는 양 (FP=0.308: 서 있는 사람의 투영계수) |
| K_dif × svf × 0.5 | 하늘에서 오는 산란복사 × SVF × 반구 계수 |

**FP = 0.308**: 서 있는 사람이 직달 태양복사를 받을 때의  
투영 면적 계수 (projection factor for standing person).

> 근거: Höppe, P. (1992). *Energy and Buildings* 19:221–230.

**풀 SOLWEIG와의 차이**:  
풀 SOLWEIG는 6방향(동·서·남·북·상·하) 단파복사를 개별 계산하고  
각 방향의 그림자 여부(S=0/1)를 반영.  
이 코드는 직달+산란을 단순 합산 — **방향성 없음, 그림자 없음**.

---

### 4.6 STEP 5 — 장파복사 추정

#### 하늘 장파복사 (Brutsaert 1975)

```python
ea = (RH/100) × 6.112 × exp(17.67 × Tair / (Tair + 243.5))  # 수증기압 (hPa)
ε_sky = clip(0.575 × ea^(1/7), 0.70, 1.00)                    # 하늘 방사율
L_sky = ε_sky × σ × Tair_K⁴
```

> 근거: Brutsaert, W. (1975). *Water Resources Research* 11(5):742–744.

#### 벽면 장파복사

```python
dT = 10.0 if GHI > 50 else 0.0   # 일사 있을 때 벽면 온도 +10K 가정
L_wall = ε_wall × σ × (Tair_K + dT)⁴
ε_wall = 0.90
```

벽면 온도 = 기온 + 10K (일사 있을 때) / 기온과 동일 (야간)  
→ **상수 오프셋 가정**. 풀 SOLWEIG의 지표면 파라미터화와 다름.

#### SVF 가중 평균 장파복사

```python
L_mean = L_sky × svf + L_wall × (1 - svf)
```

SVF만큼은 하늘 복사, 나머지(1-SVF)는 벽면 복사로 가중.

**풀 SOLWEIG와의 차이**:  
풀 SOLWEIG는 하늘·식생·벽·지면을 6방향 × 4성분으로 분리 계산.  
이 코드는 하늘+벽 2성분을 SVF로 단순 가중평균 — **지면 복사 없음, 방향성 없음**.

---

### 4.7 STEP 6 — MRT 산출 (Stefan-Boltzmann 역산)

```python
mrt_K = ((ALPHA_K × K_abs + L_mean) / (EPSILON_P × σ))^0.25
mrt_°C = mrt_K - 273.15
```

| 상수 | 값 | 근거 |
|------|----|------|
| ALPHA_K (ξ_k) | 0.70 | Fanger (1970) |
| EPSILON_P (ε_p) | 0.97 | ISO 7726 (1998) |
| σ | 5.67×10⁻⁸ | Stefan-Boltzmann |

---

### 4.8 STEP 7 — 캐노피 보정 (UTCI에 반영)

MRT 자체를 보정하지 않고, **UTCI 계산 후 캐노피 효과를 별도 차감**:

```python
delta_c = CANOPY_COEFF × canopy_ratio × SOLAR_FACTOR[hour]
utci_final = utci_val - delta_c
CANOPY_COEFF = 2.5
```

`SOLAR_FACTOR`: 시간대별 태양 강도 정규화 계수 (13시 = 1.00, 최대).

> **주의**: CANOPY_COEFF = 2.5는 경험적 파라미터로,  
> 특정 문헌의 수치가 아닌 연구 내 설정값임.

---

## 5. 풀 SOLWEIG vs 내 연구 비교표

| 항목 | 풀 SOLWEIG | 내 연구 (약식) |
|------|-----------|---------------|
| **계산 단위** | 픽셀 (1m × 1m) | 도로 링크 중심점 |
| **관측 높이** | z = 1.1m (명시) | 미지정 |
| **SVF 계산** | DSM fisheye 투영 (pixel-level) | Oke(1987) H/W Canyon 공식 |
| **그림자** | DSM 기반 pixel-level 투영 | 없음 |
| **단파복사** | 6방향 개별 계산, 그림자 Boolean 반영 | 직달+산란 단순 합산 (FP=0.308) |
| **장파복사** | 하늘·식생·벽·지면 6방향 분리 계산 | 하늘+벽 SVF 가중 평균 |
| **지표면 온도** | 지표 유형별 선형 회귀 파라미터화 | 상수 +10K 오프셋 (일사 시) |
| **식생 처리** | CDSM + 투과율 τ=0.02 | canopy_ratio × 10m 고정 높이 → SVF 보정 |
| **기상 입력** | 단일 관측소 또는 재분석 | S-DoT 57개소 IDW 보간 |
| **일사량** | 직달+산란 실측 또는 분리 모형 | Open-Meteo GHI → Erbs(1982) 분리 |
| **근거 문헌** | Lindberg & Grimmond (2011); Lindberg et al. (2016) | Oke(1987); Brutsaert(1975); Erbs et al.(1982); Höppe(1992) |

---

## 6. 내 연구 방법론이 가지는 한계

위 비교에서 도출되는 구체적 한계:

1. **그림자 미반영**  
   건물이 만드는 실제 그림자 패턴을 계산하지 않음.  
   그늘진 골목과 햇빛 노출 도로의 MRT 차이가 과소평가될 수 있음.

2. **관측 높이 미지정**  
   풀 SOLWEIG의 z=1.1m 기준이 적용되지 않음.  
   링크 중심점 좌표(지면 수준)에서 계산한 SVF를 사용.

3. **SVF 근사 오차**  
   Oke H/W Canyon은 이상적인 직선 가로협곡을 가정.  
   실제 불규칙한 도시 형태에서는 오차 발생 가능.

4. **지표면 온도 단순화**  
   벽면 온도 = 기온 + 10K 상수 가정.  
   아스팔트·잔디 등 지표 유형별 온도 차이 미반영.

5. **캐노피 보정의 경험적 불확실성**  
   CANOPY_COEFF = 2.5는 연구 내 설정값으로,  
   특정 실측 데이터에 기반하지 않음.

---

## 7. 논문·발표에서 이 연구를 어떻게 설명해야 하는가

**정확한 표현**:
> "SOLWEIG 모형의 복사 교환 수식 (Lindberg & Grimmond 2011)에 기반하되,  
> 링크 단위 분석에 적합하도록 DSM 대신 Oke(1987) H/W Canyon 공식으로  
> SVF를 근사하고, 직산 분리(Erbs et al. 1982)와 대기 장파 추정(Brutsaert 1975)을  
> 결합한 약식 구현을 적용하였다."

**피해야 할 표현**:
- ~~"SOLWEIG 모형을 적용하였다"~~ → 약식 구현임을 명시해야 함
- ~~"보행자 높이 기준(1.1m)"~~ → 코드에 높이 지정 없음
- ~~"그림자 효과를 반영하였다"~~ → 그림자 계산 없음

---

---

## 8. 캐노피·수변 처리 방식 비교

### 8.1 캐노피 (수목)

#### 풀 SOLWEIG

**CDSM (Canopy Digital Surface Model)** 을 별도 입력으로 사용:

- 건물 SVF (Ψ_sky_b)와 **식생 SVF (Ψ_sky_v)를 분리 계산**
- 단파복사: 식생 투과율 **τ = 0.02** 적용 (잎 달린 상태 기준)
  - 나무 그림자 아래도 2%만 직달 통과
- 장파복사: 식생 = 기온과 동일한 온도의 흑체로 가정
- Shadow casting: 나무가 드리우는 그림자를 픽셀 단위 계산

> 핵심: 나무의 **실제 3D 형상 + 투과율**로 복사를 물리적으로 계산

#### 내 코드 (두 단계 처리)

**① SVF에 간접 반영** (`15_svf_per_link.py`):
```python
TREE_HEIGHT = 10.0  # m, 고정 가정 (UMEP TreePlanter Tutorial; Lindberg et al.)
H_eff = H_building + TREE_HEIGHT × canopy_ratio
SVF = 1 / √(1 + (H_eff / W)²)
```
캐노피가 있으면 H_eff가 커져서 SVF가 낮아짐 → 하늘 복사 차단 효과 간접 반영

**② UTCI에 직접 차감** (`39_utci_sdot_solweig.py`):
```python
delta_c = CANOPY_COEFF × canopy_ratio × SOLAR_FACTOR[hour]
utci_final = utci_val - delta_c
CANOPY_COEFF = 2.5   # 경험적 파라미터 — 특정 문헌 수치 아님
```
캐노피 면적 비율에 비례해서 UTCI를 경험적으로 낮춤.

**한계**:
- 수목 높이 10m 고정 (성숙목 과소 추정, 어린 나무 과대 추정 가능)
- CANOPY_COEFF = 2.5는 문헌 미기반 경험적 파라미터
- τ = 0.02 투과율 미적용 (나무 그림자 아래 투과 효과 없음)

---

### 8.2 수변 (한강·중랑천)

#### 풀 SOLWEIG

논문에서 **단순화 처리** (향후 과제로 개선 예정이라 명시):

- 수면 온도(T_s) ≈ 기온(T_a) (물의 열용량이 커서 변화 작음)
- 알베도 α = 0.05 (매우 낮음 → 반사 거의 없음)
- 단파복사 거의 흡수, 장파복사는 T_a 기준 흑체 가정

> "Water temperature does not influence air temperature."  
> (Lindberg et al. 2016, p.1446)

#### 내 코드

**명시적 수변 처리 없음.**

한강·중랑천 인접 링크는 구조적으로:
- 주변 20m 내 건물 없음 → H_building ≈ 0
- canopy_ratio 낮음
- 결과적으로 **SVF ≈ 1.0** (개활지로 자동 근사)

수면 냉각 효과(증발 등)는 미반영.

---

### 8.3 요약 비교

| | 풀 SOLWEIG | 내 코드 |
|---|---|---|
| **캐노피** | CDSM + τ=0.02 투과율 + 픽셀 그림자 | H_eff 보정(10m 고정) + UTCI 경험적 차감 |
| **수변** | T_s≈T_a, α=0.05 단순화 | 처리 없음 (개활지로 자동 근사) |

> **참고**: 풀 SOLWEIG도 수변을 단순화하고 있음을 논문이 인정.  
> 캐노피·수변 모두 내 연구의 한계로 명시하되,  
> 풀 SOLWEIG 자체의 단순화 수준과 크게 다르지 않음을 근거로 활용 가능.

---

*작성일: 2026-05-29*  
*작성자: Claude Sonnet 4.6 (코드·논문 기반 분석)*
