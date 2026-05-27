# MRT 파이프라인 코드 기반 상세 설명 (팩트체크용)

> 작성 목적: 석사논문 MRT 산출 과정을 코드 흐름 순으로 정리해 수치·근거·설계 결정을 이중 검증  
> 작성일: 2026-05-27  
> 관련 코드 위치: `/Users/jin/석사논문/TAVI/Thermal_Catchment/02_코드/`

---

## 전체 흐름 요약

```
Stage 1   OSM 보행 네트워크 구축
    ↓          01_download_network.py
Stage 2   SVF + 캐노피 비율 계산
    ↓          15_svf_per_link.py
Stage 3   기상 데이터 처리 (S-DoT IDW + Open-Meteo GHI)
    ↓          39_utci_sdot_solweig.py (전반부)
Stage 4   SOLWEIG 수식 기반 링크별 MRT 산출
    ↓          39_utci_sdot_solweig.py (후반부)
Stage 5   MRT Hard Cut → Thermal Catchment → TARR
               40_catchment_mrt.py
```

Stage 4 출력(MRT)이 Stage 5의 유일한 열 입력. Tair/RH/GHI는 기상 입력으로 모든 링크에 같은 시간대 기상을 쓰되 Tair/RH만 IDW로 공간 분화. **MRT의 링크 간 차이는 사실상 SVF 하나에서 발생.**

---

## Stage 1 — OSM 보행 네트워크 (`01_download_network.py`)

### 데이터 소스

- **OpenStreetMap**, osmnx 라이브러리 사용
- 대상 지역: `"성동구, 서울특별시, 대한민국"`
- 네트워크 유형: `network_type="walk"` — 보행자가 이용 가능한 모든 도로 포함

### 코드

```python
PLACE = "성동구, 서울특별시, 대한민국"
G_walk = ox.graph_from_place(PLACE, network_type="walk", retain_all=True)
ox.save_graphml(G_walk, graphml_path)
```

`retain_all=True`: 연결되지 않은 컴포넌트도 모두 유지 (한강 교량 등 분리 구간 포함)

### 산출물

- `seongdong_walk_network.graphml` — 이후 모든 스테이지의 기반
- 엣지 속성: `u`, `v`, `geometry`, `length(m)`, `highway` 유형

### 팩트체크 포인트

- `retain_all=True`로 인해 실제 도달 불가 고립 컴포넌트가 포함될 수 있음
- `network_type="walk"`는 차도를 일부 포함할 수 있음 (OSM 태깅 의존)

---

## Stage 2 — SVF + 캐노피 비율 (`15_svf_per_link.py`)

### 사용 데이터

| 데이터 | 파일 경로 | 용도 |
|--------|-----------|------|
| 도로명주소 건물 SHP | `TL_SPBD_BULD_11_202603.shp` | 건물 높이 H 계산 |
| 서울시 도시숲 SHP | `도시숲전체_면_서울_최종_중분류.shp` | 캐노피 비율 계산 |
| OSM 네트워크 | `seongdong_walk_network.graphml` | 링크 기준 좌표 |

### 2-1. 건물 높이 계산

```python
buld['height_m'] = buld['GRO_FLO_CO'].clip(lower=1) * 3
```

- `GRO_FLO_CO`: 도로명주소 건물 SHP의 지상 층수 컬럼
- 층수 × **3m** 고정 → 건물 높이 근사
- `clip(lower=1)`: 0층 기록 오류 방지 (최소 1층으로 처리)

> **3m/층 근거**: 건축법 시행령 기준 일반 주거·상업 건물 층고 2.4~3.0m, 도시 열환경 연구에서 관행적으로 사용하는 근사값. 실제 층고와 최대 수십 % 오차 가능 (초고층·저층 특수 건물).

> **팩트체크**: 정확한 층고 데이터(건물 세움터, 부동산 공시 등)가 있다면 교체 가능. 현재는 전국 표준 근사값 사용.

### 2-2. 도로폭 테이블

```python
WIDTH_BY_HIGHWAY = {
    'trunk':            24.0,
    'trunk_link':       10.0,
    'primary':          16.0,
    'primary_link':      8.0,
    'secondary':        12.0,
    'secondary_link':    6.0,
    'tertiary':          9.0,
    'tertiary_link':     6.0,
    'residential':       6.0,
    'living_street':     5.0,
    'service':           5.0,
    'footway':           3.0,
    'pedestrian':        4.0,
    'path':              2.0,
    'steps':             2.0,
    'corridor':          3.0,
    'unclassified':      6.0,
}
DEFAULT_WIDTH = 6.0
```

> **근거**: 국토교통부 도로설계기준 + OSM 도로 유형 정의. 양방향 차로 포함 전체 노면폭 기준.

> **팩트체크 포인트**: 이 수치들은 국내 평균 기준이며 성동구 실제 도로폭과 다를 수 있음. 특히 `footway`(3m), `path`(2m)는 보행전용이라 H/W비에 민감 — 좁은 도로일수록 SVF가 과소 추정될 가능성.

### 2-3. 캐노피 비율 계산

```python
CANOPY_BUFFER = 15  # m
TREE_HEIGHT   = 10.0  # m

def calc_canopy_ratio(link_geom):
    buf = link_geom.buffer(CANOPY_BUFFER)
    clipped_area = 도시숲_폴리곤.intersection(buf).area.sum()
    return clipped_area / buf.area
```

- 링크 중심선에서 **15m** 버퍼 내 도시숲 폴리곤 면적 비율
- 결과는 0.0 ~ 1.0 (비율)

> **15m 근거**: 연구팀 내부 합의값. 도시 보행로 양측 수목 영향권 반영을 위한 경험적 설정. 명시적 문헌 출처 없음 → **팩트체크 필요**.

> **TREE_HEIGHT 10m 근거**: UMEP TreePlanter Tutorial (Lindberg et al.) 도시 가로수 표준 캐노피 높이. 실제 서울 가로수는 수종별로 5~15m 편차 있음.

### 2-4. SVF 계산 — Oke (1987) H/W 협곡 공식

```python
BULD_BUFFER = 20  # m — 건물 탐색 반경

def calc_svf_hw(link_geom, highway_val, canopy_ratio=0.0):
    W = get_width(highway_val)
    buf = link_geom.buffer(BULD_BUFFER)
    H_bld = 버퍼_내_건물_평균_높이
    H_eff = H_bld + TREE_HEIGHT * canopy_ratio
    svf = 1.0 / np.sqrt(1.0 + (H_eff / W) ** 2)
    return svf
```

**SVF 공식 전개:**

$$\text{SVF} = \frac{1}{\sqrt{1 + \left(\frac{H_{\text{eff}}}{W}\right)^2}}$$

$$H_{\text{eff}} = H_{\text{건물}} + 10\,\text{m} \times \text{캐노피비율}$$

> **Oke (1987) 근거**: T.R. Oke, *Boundary Layer Climates* (2nd ed.), Routledge. 무한 길이 도시 협곡(street canyon) 가정 하에 유도된 기하학적 SVF 공식.

> **팩트체크 포인트**: 이 공식은 **무한 길이 균일 협곡**을 가정. 실제 도시 블록 끝단, 교차로, 불규칙 건물 배치에서는 과소/과대 추정 발생. 실제 SOLWEIG 소프트웨어는 DSM 기반 반구 투영(fisheye)으로 SVF를 구하는데, 이 코드는 해당 DSM 없이 H/W로 대체한 것.

> **건물 탐색 버퍼 20m 근거**: 내부 합의값. 명시적 문헌 없음 → **팩트체크 필요**.

### 산출물

```
link_svf_canopy.csv
컬럼: u, v, svf, mean_bld_H, road_W, HW_ratio, canopy_ratio, highway
```

---

## Stage 3 — 기상 데이터 처리 (`39_utci_sdot_solweig.py`)

### 3-1. S-DoT 데이터 (Tair, RH, 풍속)

- **소스**: 서울시 IoT 도시데이터 S-DoT 센서 57개소
- **기간**: 2025-07-28 ~ 2025-08-03 (폭염일 7일)
- **변수**: 기온(`temp`), 습도(`humi`), 풍속(`v`)

**IDW 보간:**

```python
IDW_POWER = 2

def idw(qx, qy, sx, sy, vals, power=IDW_POWER):
    dx, dy = sx - qx, sy - qy
    dist = np.sqrt(dx**2 + dy**2)
    if dist.min() < 1.0:
        return float(vals[dist.argmin()])   # 센서 바로 위 → 최근접값
    w = 1.0 / dist ** power
    return float(np.sum(w * vals) / np.sum(w))
```

- 링크 중심점(EPSG:5186) ↔ 센서 좌표(EPSG:5186) 거리 기반
- power=2: 거리 제곱 역수 가중 (표준 IDW)

> **팩트체크**: IDW power=2는 관행적 기본값. 성동구 57개 센서 → 링크 약 16,000개 커버. 센서 밀도가 낮은 변두리(한강 이남, 한강 수변)에서 보간 오차 클 수 있음.

**풍속 하한 클리핑:**

```python
va = max(idw(...), 0.5)   # 최소 0.5 m/s
```

> **0.5 m/s 근거**: UTCI/MRT 계산에서 풍속이 0에 가까울 때 수치 불안정 방지 목적. ISO 7726 권장 최소 기류 속도 참고. → **팩트체크**: 실제 S-DoT 무풍 기록 빈도 확인 필요.

### 3-2. Open-Meteo (GHI, 일사량)

- **소스**: Open-Meteo archive API
- **위치**: 성동구 중심 단일 지점 (lat=37.550, lon=127.040)
- **변수**: `shortwave_radiation` (전천일사, W/m²)
- **기간**: 2025-07-28 ~ 2025-08-03

```python
ghi_hourly = ghi_df.groupby('hour')['GHI'].mean().to_dict()
```

→ 7일 평균 시간대별 GHI 딕셔너리 (시간대: W/m²)

> **팩트체크**: GHI는 성동구 전체에 단일값 사용 — 공간 변이 없음. 구름 분포, 건물 음영 등 실제 국지적 일사량 차이 미반영.

### 3-3. 태양 시간 보정 및 SOLAR_FACTOR

**태양 고도각 가중치 (시간대별):**

```python
SOLAR_FACTOR = {
    0: 0.00, 1: 0.00, 2: 0.00, 3: 0.00, 4: 0.00,
    5: 0.05, 6: 0.20, 7: 0.40, 8: 0.60, 9: 0.75,
    10: 0.88, 11: 0.95, 12: 1.00, 13: 1.00, 14: 0.95,
    15: 0.88, 16: 0.75, 17: 0.60, 18: 0.40, 19: 0.20,
    20: 0.05, 21: 0.00, 22: 0.00, 23: 0.00,
}
```

> **용도**: 캐노피 차폐 보정에만 사용 (Stage 3 끝, UTCI 보정). MRT 수식 자체에는 cos_z를 직접 계산.

> **팩트체크**: SOLAR_FACTOR는 실측값이 아닌 서울 여름 태양 고도 패턴을 경험적으로 정규화한 수치. 12~13시를 1.0으로 정규화.

**캐노피 보정 (UTCI에만 적용, MRT에는 미적용):**

```python
CANOPY_COEFF = 2.5   # °C (Chen & Ng 2012)
delta_canopy = CANOPY_COEFF * canopy_ratio * SOLAR_FACTOR[hour]
utci_final = utci_val - delta_canopy
```

> **중요**: 캐노피 보정은 **MRT가 아닌 UTCI에 적용**됨. 최종 분석(Method 4)은 MRT를 직접 사용하므로 캐노피 보정이 MRT에 반영되지 않는 구조. → **팩트체크 필요**: MRT에 캐노피 차폐를 반영하려면 SVF 계산 시 H_eff에 포함시키는 방식(현재 코드가 이렇게 함)만 작동.

> **CANOPY_COEFF 2.5°C 근거**: Chen & Ng (2012), Urban trees reduce mean radiant temperature, 수목이 제공하는 UTCI 감소 효과 최대 2.5°C 추정.

---

## Stage 4 — SOLWEIG 수식 기반 MRT 계산 (`39_utci_sdot_solweig.py`)

### 4-1. 물리 상수 전체 목록

```python
ALPHA_K      = 0.70     # 인체 단파 흡수율
EPSILON_P    = 0.97     # 인체 장파 방사율
FP           = 0.308    # 투영면적계수 (서 있는 사람)
SIGMA        = 5.67e-8  # Stefan-Boltzmann 상수 (W m⁻² K⁻⁴)
EPSILON_WALL = 0.90     # 도시 표면 장파 방사율
DELTA_T_WALL = 10.0     # 주간 도시 표면 기온 초과분 (K)
```

| 상수 | 값 | 출처 |
|------|----|------|
| α_k (단파 흡수율) | 0.70 | Fanger (1970); ISO 7730 |
| ε_p (인체 방사율) | 0.97 | ISO 7726 (1998) |
| fp (투영면적계수) | 0.308 | Höppe (1992) — 서 있는 사람 전방향 평균 |
| σ | 5.67×10⁻⁸ | Stefan-Boltzmann 상수 (물리 고정값) |
| ε_wall | 0.90 | Oke (1987) 도시 표면 방사율 |
| ΔT_wall | +10 K | Oke (1982) 주간 도시 표면 가열 |

> **팩트체크 — fp=0.308**: Höppe (1992)는 서 있는 사람(standing person)의 평균 투영면적계수. 실제 MRT 식에서는 6방향(상·하·전·후·좌·우) 평균값 사용. 이 값은 SOLWEIG 코드에서도 동일하게 사용됨. ✅

> **팩트체크 — ΔT_wall=10K**: Oke (1982)의 도시 표면 과열 경험값. 성동구 실측 표면 온도와 차이 있을 수 있음. 특히 아스팔트 도로는 낮에 +15~20K까지 가열될 수 있어 과소 추정 가능성. → **검토 필요**.

### 4-2. 태양 천정각 계산

```python
def cos_solar_zenith(hour, lat=37.55, lon=127.04, doy=210):
    lat_r = np.radians(lat)
    decl  = np.radians(23.45 * np.sin(np.radians(360/365 * (284 + doy))))
    solar_time  = hour + (lon - 135.0) / 15.0   # KST → 태양시 보정
    hour_angle  = np.radians(15.0 * (solar_time - 12.0))
    cos_z = (np.sin(lat_r)*np.sin(decl) +
             np.cos(lat_r)*np.cos(decl)*np.cos(hour_angle))
    return float(max(cos_z, 0.0))
```

- **lat=37.55, lon=127.04**: 서울 성동구 중심 좌표 고정
- **doy=210**: 7월 29일 — 연간 대표일로 고정

> **doy=210 근거**: 분석 기간(2025-07-28~08-03)의 중간일 대표값. 태양 적위 변화가 연간 대비 이 기간에는 미미하므로 고정해도 큰 오차 없음.

> **경도 보정** `(lon - 135.0) / 15.0`: KST(UTC+9, 135°E 기준) → 태양시 변환. 서울(127.04°E)은 표준 경선보다 약 0.53시간 일찍 기준되므로 보정. ✅

### 4-3. 직산 분리 — Erbs et al. (1982)

```python
def split_radiation(GHI, cos_z):
    if GHI <= 10 or cos_z < 0.01:
        return 0.0, float(GHI)     # 야간 또는 수평면 → 전량 산란 처리
    kt = min(GHI / (1367.0 * cos_z), 1.0)   # 청명도 지수
    if kt <= 0.22:
        kd = 1.0 - 0.09 * kt
    elif kt <= 0.80:
        kd = max(0.9511 - 0.1604*kt + 4.388*kt**2
                 - 16.638*kt**3 + 12.336*kt**4, 0.1)
    else:
        kd = 0.165
    K_dir = GHI * (1 - kd)   # 직달
    K_dif = GHI * kd          # 산란
    return K_dir, K_dif
```

- **1367 W/m²**: 태양상수 (대기권 외 수평면 일사)
- **kd**: 산란 비율 (diffuse fraction), kt 구간별 4차 다항식 피팅
- Erbs et al. (1982) — 미국 5개 기상관측소 실측 기반 회귀모델

> **팩트체크**: Erbs 모델은 미국 데이터 기반. 서울 여름(몬순 기후) 환경에서 산란 비율이 다를 수 있음. 대안으로 Reindl 모델(1990), Perez 모델이 있으나 입력 변수 추가 필요. 현재 GHI만 있어 Erbs가 유일한 선택지. ✅

### 4-4. MRT 수식 — Lindberg & Grimmond (2011) 전체 전개

```python
def compute_mrt(Tair, GHI, RH, svf, cos_z):
    Tair_K = Tair + 273.15

    # ① 단파 흡수량
    K_dir, K_dif = split_radiation(GHI, cos_z)
    K_abs = K_dir * FP + K_dif * svf * 0.5

    # ② 대기 장파 하향 (Brutsaert 1975)
    ea = (RH/100) * 6.112 * np.exp(17.67*Tair / (Tair+243.5))  # 수증기압 hPa
    eps_sky = np.clip(0.575 * ea**(1/7), 0.70, 1.00)
    L_sky = eps_sky * SIGMA * Tair_K**4

    # ③ 도시 표면 장파 (Oke 1987)
    dT = DELTA_T_WALL if GHI > 50 else 0.0    # 낮에만 +10K
    L_wall = EPSILON_WALL * SIGMA * (Tair_K + dT)**4

    # ④ SVF 가중 평균 장파
    L_mean = L_sky * svf + L_wall * (1 - svf)

    # ⑤ MRT 역산
    mrt_K = ((ALPHA_K * K_abs + L_mean) / (EPSILON_P * SIGMA))**0.25
    return mrt_K - 273.15
```

**수식 분해:**

**① 단파 흡수량 K_abs**

$$K_{\text{abs}} = K_{\text{dir}} \times f_p + K_{\text{dif}} \times \text{SVF} \times 0.5$$

- $K_{\text{dir}} \times f_p$: 직달 태양복사 × 인체 투영면적계수 (0.308)
- $K_{\text{dif}} \times \text{SVF} \times 0.5$: 산란복사 × 하늘 노출 비율 × 반구 인자(0.5)

> 0.5는 하늘 반구 기여 보정 인자 (산란은 전방향 → 인체는 상반구만 노출).

**② 대기 장파 L_sky — Brutsaert (1975)**

$$\varepsilon_{\text{sky}} = 0.575 \times e_a^{1/7} \quad (\text{clipped to } [0.70,\ 1.00])$$
$$L_{\text{sky}} = \varepsilon_{\text{sky}} \times \sigma \times T_{\text{air},K}^4$$

- $e_a$: 수증기압 (Magnus 공식, hPa)
- Brutsaert (1975): 맑은 하늘 장파 하향 복사 추정식

> **팩트체크**: Brutsaert 공식은 맑은 하늘(clear-sky) 조건. 구름 있는 폭염일에는 ε_sky가 과소 추정될 수 있음. 구름량 데이터 없이는 보정 불가. → 현재 코드 한계.

**③ 도시 표면 장파 L_wall — Oke (1987)**

$$L_{\text{wall}} = \varepsilon_{\text{wall}} \times \sigma \times (T_{\text{air},K} + \Delta T_{\text{wall}})^4$$

- GHI > 50 W/m² (낮)이면 ΔT_wall = +10K, 야간이면 0K
- 50 W/m² 기준은 주야 경계 구분을 위한 경험적 임계값

> **팩트체크**: 주야 구분을 GHI=50 W/m²으로만 판단 — 일출·일몰 전후 모호한 구간(10~100 W/m²) 존재. 또한 모든 도시 표면을 단일 ΔT=10K로 처리 — 아스팔트, 콘크리트, 잔디 등 재질별 차이 미반영. → **텀프로젝트에서 MLLM이 이 한계를 보완할 수 있는 지점**.

**④ SVF 가중 장파 L_mean**

$$L_{\text{mean}} = L_{\text{sky}} \times \text{SVF} + L_{\text{wall}} \times (1 - \text{SVF})$$

- SVF → 하늘에서 오는 장파 비율
- (1-SVF) → 건물 벽면에서 오는 장파 비율

> **핵심**: MRT의 공간 변이는 이 SVF 가중치에서 발생. SVF가 높으면(개활지) L_sky 비중 ↑, L_wall 비중 ↓. 여름 낮에는 L_sky < L_wall이므로 개활지(SVF→1)가 MRT 더 높음 → Thermal Catchment에서 서울숲 인근이 고TARR인 이유.

**⑤ MRT 역산 (Stefan-Boltzmann)**

$$T_{\text{mrt}} = \left[\frac{\alpha_k \times K_{\text{abs}} + L_{\text{mean}}}{\varepsilon_p \times \sigma}\right]^{0.25} - 273.15$$

### 산출물

```
link_utci_sdot_solweig.csv
컬럼: u, v, hour, Tair_idw, RH_idw, va_idw, GHI, svf, mrt, utci_m3, utci_final
```

**MRT 분포 (13시 기준, 폭염일 평균):**
- 범위: 약 42~63°C
- std: 약 4.6°C — SVF 공간 변이에서 발생

---

## Stage 5 — Thermal Catchment (`40_catchment_mrt.py`)

### 5-1. MRT 임계값 55°C 결정 과정

UTCI를 직접 쓰면 폭염일 13시에 ≥38°C 비율이 **99.8%** → Hard Cut 불가 → UTCI 포기, MRT 직접 사용.

임계값 55°C 도출:

```
UTCI = 38°C (Bröde et al. 2012, "Very Strong Heat Stress" 경계) 가 되는
MRT 값을 역산:

  조건: Tair=36°C, RH=60%, va=2.37 m/s (폭염일 7일 평균)
  pythermalcomfort.utci(tdb=36, tr=MRT, v=2.37, rh=60) = 38°C
  → MRT ≈ 55°C
```

> **팩트체크**: 55°C는 특정 기상 조건(Tair=36, RH=60, va=2.37)에서의 역산값. 조건이 달라지면 임계 MRT도 달라짐. 현재 코드에서는 55°C를 시간·공간 불변 상수로 사용 — 기상 조건이 다른 시간대(7시, 16시 등)에서는 동일 기준 적용이 물리적으로 정확하지 않음. → **연구 한계로 인식 필요**.

### 5-2. 보행 파라미터

```python
WALK_SPEED  = 4.5 * 1000 / 3600   # = 1.25 m/s
TIME_BUDGET = 15 * 60              # = 900초
```

- **4.5 km/h**: 성인 평균 보행속도 (교통공학 표준값)
- **15분**: 역세권 보행권 분석 표준 시간예산

> **팩트체크**: 4.5 km/h는 건강 성인 기준. 고령자, 열 스트레스 상황 보행 속도는 3~4 km/h로 낮아짐 → 실제 Thermal Catchment 면적이 현재 분석보다 더 작을 가능성.

### 5-3. Hard Cut 적용 및 Dijkstra

```python
def compute_catchment(G_base, station_node, hot_edges_set):
    # 1) Classic: 전체 네트워크로 Dijkstra
    classic_dist = nx.single_source_dijkstra_path_length(
        G_base, station_node, cutoff=TIME_BUDGET, weight='travel_time'
    )

    # 2) Thermal: hot edges 제거 후 Dijkstra
    G_thermal = G_base.copy()
    G_thermal.remove_edges_from(hot_edges 목록)
    thermal_dist = nx.single_source_dijkstra_path_length(
        G_thermal, station_node, cutoff=TIME_BUDGET, weight='travel_time'
    )
```

- `travel_time = length(m) / WALK_SPEED(m/s)` — 링크 통과 시간(초)
- Hard Cut: MRT ≥ 55°C 링크는 물리적으로 통행 불가 처리 (가중치 증가가 아닌 완전 제거)
- 간접 고립(directly connected하지 않아도 경로 차단으로 도달 불가한 노드) 자동 반영

### 5-4. TARR 계산

```python
reduction_pct = len(lost_nodes) / max(len(classic_nodes), 1) * 100
# lost_nodes = classic_nodes - thermal_nodes
```

$$\text{TARR}_i = \frac{S_i^{\text{classic}} - S_i^{\text{thermal}}}{S_i^{\text{classic}}} \times 100$$

- 노드 수 기준 + 도로 길이(m) 기준 두 가지 병행 산출
- 출발점이 처음부터 접근 불가인 케이스는 분석에서 제외

---

## 팩트체크 종합 요약

| 구성 요소 | 설계 결정 | 근거 있음? | 팩트체크 포인트 |
|-----------|-----------|-----------|----------------|
| 층수×3m | 건물 높이 근사 | 관행적 사용 | 실제 층고 데이터 대체 가능 여부 |
| 도로폭 테이블 | highway 유형별 고정 | 국토부 기준 | 성동구 실제 폭과 차이 가능 |
| 건물 버퍼 20m | SVF 계산 탐색 반경 | 내부 합의 | 명시적 문헌 근거 없음 |
| 캐노피 버퍼 15m | 캐노피 비율 탐색 반경 | 내부 합의 | 명시적 문헌 근거 없음 |
| TREE_HEIGHT 10m | 수목 차폐 높이 | UMEP Tutorial | 서울 수종별 편차 미반영 |
| ΔT_wall=+10K | 도시 표면 가열 | Oke (1982) | 노면 재질별 차이 미반영 |
| GHI > 50 기준 | 주야 표면 가열 구분 | 경험적 | 일출·일몰 전후 모호한 구간 |
| doy=210 고정 | 태양 위치 대표일 | 기간 중간일 | 분석 기간 내 변화 미미 ✅ |
| IDW power=2 | 기상 공간 보간 | 관행적 표준 | ✅ |
| MRT 임계값 55°C | Hard Cut 기준 | UTCI 역산 | 시간대별 기상 조건 변화 미반영 |
| 보행속도 4.5 km/h | Catchment 계산 | 교통공학 표준 | 고령자/열환경 감속 미반영 |

---

## MLLM 대체 가능 지점 메모

위 파이프라인에서 GSV + Qwen2-VL-7B로 대체하거나 보완할 수 있는 구성 요소:

| Stage | 현재 방법 | MLLM 대체 방향 |
|-------|-----------|----------------|
| Stage 2 SVF | Oke H/W 공식 (건물SHP) | 이미지에서 하늘 노출 비율 직접 추론 |
| Stage 2 캐노피비율 | 도시숲 SHP 면적비 | 이미지에서 수목 캐노피 커버리지 추론 |
| Stage 4 ΔT_wall | 모든 링크 +10K 고정 | 이미지에서 노면 재질 식별 → 재질별 ΔT 적용 |
| Stage 4 차양구조물 | 미반영 | 이미지에서 아케이드·파라솔·캐노피 식별 |
| Stage 4 MRT 전체 | SOLWEIG 수식 | 이미지 → 직접 MRT 범주 추론 (End-to-End) |

---

*관련 코드:*
- `15_svf_per_link.py` — SVF 계산
- `39_utci_sdot_solweig.py` — IDW 보간 + SOLWEIG MRT
- `40_catchment_mrt.py` — Thermal Catchment + TARR
