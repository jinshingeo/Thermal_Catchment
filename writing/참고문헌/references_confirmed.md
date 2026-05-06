# 확보된 참고문헌 정리
**TAVI 석사논문 | 신진 | 최종 업데이트: 2026-05-06**

> **표기 규칙**
> - ✅ 원문 직접 확인 / 검색 결과에서 직접 인용
> - ⚠️ 원문 확인 필요 (내용 요약만 기재, 논문 열람 후 직접 발췌 필요)
> - 인용 양식: APA 7th

---

## 1. MRT 산출 — SOLWEIG 표준 공식

### Lindberg, F., Holmer, B., & Thorsson, S. (2008)
**APA**
> Lindberg, F., Holmer, B., & Thorsson, S. (2008). SOLWEIG 1.0 – Modelling spatial variations of 3D radiant fluxes and mean radiant temperature in complex urban settings. *International Journal of Biometeorology*, 52(7), 697–713. https://doi.org/10.1007/s00484-008-0162-7

**인용 위치**: MRT 산출의 기반 모델(SOLWEIG)을 도입할 때, 방법론 섹션 첫 문장

**원문 (✅ 확인)**
> "A new radiation model (SOLWEIG 1.0), which simulates spatial variations of 3D radiation fluxes and Tmrt in complex urban settings, is presented."
> (복잡한 도시 환경에서 3D 복사 플럭스와 평균복사온도의 공간 변이를 시뮬레이션하는 새로운 복사 모델(SOLWEIG 1.0)을 제시한다.)

---

### Lindberg, F., & Grimmond, C. S. B. (2011)
**APA**
> Lindberg, F., & Grimmond, C. S. B. (2011). The influence of vegetation and building morphology on shadow patterns and mean radiant temperatures in urban areas: model development and evaluation. *Theoretical and Applied Climatology*, 105(3–4), 311–323. https://doi.org/10.1007/s00704-010-0382-8

**인용 위치**: MRT 계산 수식 직접 인용 시 (`MRT = [(α_k·K_abs + L_mean) / (ε_p·σ)]^0.25`), 방법론 섹션 MRT 산출 공식 설명

**원문 (⚠️ 원문 확인 필요)**
> 수식 원문 및 SVF·복사 성분 분리 관련 핵심 문장 — 논문 열람 후 직접 발췌 필요.
> 핵심 기여: 수목·건물 형태가 그림자 패턴 및 MRT에 미치는 영향을 모델화하고 검증. SVF를 MRT 공간 변이의 주요 결정 인자로 제시.

---

### Fischereit, J. (2021)
**APA**
> Fischereit, J. (2021). The simple urban radiation model for estimating mean radiant temperature in idealised street canyons. *Urban Climate*, 35, 100694. https://doi.org/10.1016/j.uclim.2020.100694

**인용 위치**: LiDAR DSM 없이 SVF와 H/W비만으로 MRT 추정하는 방식의 선행 사례 — 방법론 한계 서술 시 "본 연구와 유사하게 단순화된 도시 형태 파라미터로 MRT를 추정한 사례"로 인용

**원문 (✅ 검색 결과 확인)**
> "The Simple Urban Radiation Model (SURM) is an open-source and modular model presented for estimating mean radiant temperature in idealized street canyons. It addresses thermal comfort in urban areas by modeling how radiation fluxes (expressed as mean radiant temperature/Tmrt) are influenced by building morphology due to shading and reflection of radiation."
> (SURM은 이상화된 가로 협곡(street canyon)에서 평균복사온도를 추정하기 위한 오픈소스 모듈형 모델이다. 음영과 복사 반사에 의한 건물 형태의 영향을 모델링하여 복사 플럭스(MRT)를 통해 도시 내 열 쾌적성을 다룬다.)

---

## 2. UTCI 기준 및 등급 체계

### Bröde, P., Fiala, D., Błażejczyk, K., Holmér, I., Jendritzky, G., Kampmann, B., Tinz, B., & Havenith, G. (2012)
**APA**
> Bröde, P., Fiala, D., Błażejczyk, K., Holmér, I., Jendritzky, G., Kampmann, B., Tinz, B., & Havenith, G. (2012). Deriving the operational procedure for the Universal Thermal Climate Index (UTCI). *International Journal of Biometeorology*, 56(3), 481–494. https://doi.org/10.1007/s00484-011-0454-1

**인용 위치**: UTCI 38°C Hard Cut 임계값 설정 근거 — 분석 방법 및 임계값 정당화 섹션

**원문 (⚠️ 원문 확인 필요)**
> UTCI 등급 체계: 38°C 이상 = "very strong heat stress", 46°C 이상 = "extreme heat stress"로 분류.
> 핵심 기여: UTCI 계산 절차의 운영 방법론 제시 및 등급 기준 정의.
> → 논문 열람 후 등급 분류 표 원문 발췌 필요.

---

## 3. 복사 분리 및 장파 추정

### Erbs, D. G., Klein, S. A., & Duffie, J. A. (1982)
**APA**
> Erbs, D. G., Klein, S. A., & Duffie, J. A. (1982). Estimation of the diffuse radiation fraction for hourly, daily and monthly-average global radiation. *Solar Energy*, 28(4), 293–302. https://doi.org/10.1016/0038-092X(82)90302-4

**인용 위치**: 전천일사(GHI)를 직달(K_dir)·산란(K_dif)으로 분리하는 Erbs 모델 적용 시 — 방법론 MRT 계산 세부 단계

**원문 (⚠️ 원문 확인 필요)**
> 직산 분리 모델: kt(청명도 지수) 구간에 따라 산란 비율(kd)을 다항식으로 추정.
> 핵심 기여: 시간·일·월 단위 GHI에서 확산 복사 비율 추정 방법론 제시.

---

### Brutsaert, W. (1975)
**APA**
> Brutsaert, W. (1975). On a derivable formula for long-wave radiation from clear skies. *Water Resources Research*, 11(5), 742–744. https://doi.org/10.1029/WR011i005p00742

**인용 위치**: 대기 장파(L_sky) 추정식 사용 시 — 방법론 MRT 계산 세부 단계

**원문 (⚠️ 원문 확인 필요)**
> 대기 장파 추정식: `ε_sky = 0.575 × ea^(1/7)` (ea: 수증기압 [hPa])
> 핵심 기여: 맑은 하늘 조건에서 수증기압 기반 대기 장파 복사 추정 공식 제시.

---

## 4. 보행 네트워크 + 열환경 분석 (Thermal Catchment 관련)

### Basu, R., Colaninno, N., Alhassan, A., & Sevtsuk, A. (2024)
**APA**
> Basu, R., Colaninno, N., Alhassan, A., & Sevtsuk, A. (2024). Hot and bothered: Exploring the effect of heat on pedestrian route choice behavior and accessibility. *Cities*, 155, 105435. https://doi.org/10.1016/j.cities.2024.105435

**인용 위치**: 열환경(UTCI)이 보행 접근성(walkshed/catchment)을 제약한다는 선행연구 근거 — 서론 및 연구 필요성 서술

**원문 (✅ 검색 결과 확인)**
> "Although many cities are incentivizing non-auto modes of transportation in response to the climate crisis, their sustainable mobility transition efforts are being challenged by the rising intensity and frequency of heatwaves. Pedestrians are exposed to high levels of heat stress on hot days, which may reduce their willingness to walk."
> (많은 도시들이 기후위기 대응으로 비자동차 교통수단을 장려하고 있으나, 폭염의 빈도와 강도 증가가 지속 가능한 이동성 전환 노력에 도전이 되고 있다. 보행자들은 더운 날 높은 열 스트레스에 노출되며, 이는 보행 의지를 감소시킬 수 있다.)

> "[The study] conducted a walkshed analysis constructing catchment areas around MBTA stations using different types based on geometric distance, perceived distance with route attributes, and UTCI on typical and hottest summer days."
> (MBTA 역사 주변 도달권(catchment area)을 기하학적 거리, 경로 속성 반영 지각 거리, 그리고 전형적·최고 더위 날의 UTCI를 기준으로 구분하여 walkshed 분석을 수행하였다.)

---

### Colaninno, N., Basu, R., Hosseini, M., Alhassan, A., Liu, L., & Sevtsuk, A. (2025)
**APA**
> Colaninno, N., Basu, R., Hosseini, M., Alhassan, A., Liu, L., & Sevtsuk, A. (2025). A sidewalk-level urban heat risk assessment framework using pedestrian mobility and urban microclimate modeling. *Environment and Planning B: Urban Analytics and City Science*, 52(1). https://doi.org/10.1177/23998083241280746

**인용 위치**: UTCI + 보행 네트워크 결합 프레임워크 선행 사례 — 서론 관련 연구 갭 서술

**원문 (✅ 검색 결과 확인)**
> "The framework assesses pedestrian heat-related exposure and risk in urban areas by integrating the Universal Thermal Climate Index (UTCI) as the hazard and pedestrian trips to critical destinations as exposure."
> (이 프레임워크는 UTCI를 위험 요소로, 주요 목적지까지의 보행 통행을 노출 지표로 통합하여 도시 지역의 보행자 열 관련 노출 및 위험을 평가한다.)

> "The researchers created and used a sidewalk network instead of using the road network comprising street centerlines, which allows differentiation between two sides of the street that may have varying degrees of shading and vegetation."
> (도로 중심선으로 구성된 도로 네트워크 대신 보도 네트워크를 생성·활용하였으며, 이를 통해 음영과 식생 정도가 다를 수 있는 도로 양쪽을 구분할 수 있다.)

---

## 5. 방법론 표준화 및 측정 기기

### Johansson, E., Thorsson, S., Emmanuel, R., & Kruger, E. (2014)
**APA**
> Johansson, E., Thorsson, S., Emmanuel, R., & Kruger, E. (2014). Instruments and methods in outdoor thermal comfort studies – The need for standardization. *Urban Climate*, 10, 346–366. https://doi.org/10.1016/j.uclim.2013.12.002

**인용 위치**: 옥외 열환경 연구에서 MRT 측정 방법론의 다양성과 표준화 필요성 서술 — 방법론 한계 및 향후 과제 섹션

**원문 (⚠️ 원문 확인 필요)**
> 핵심 기여: 26개 선행연구를 검토하여 MRT 측정 기기·방법의 비표준화 문제를 지적. LiDAR 없이 실내용 기기를 옥외에 사용할 경우 직달 태양복사의 영향으로 오차 발생 가능성 제시.
> → ⚠️ 55°C 임계값과는 무관한 논문. MRT 측정 방법론 표준화 근거로만 사용 가능.

---

## 6. 추가 확보 필요 (미확인 — 탐색 중)

| 필요 인용 목적 | 추천 검색어 | 우선순위 |
|--------------|------------|---------|
| MRT Hard Cut 임계값 (보행 회피) | `UTCI threshold pedestrian avoidance behavior outdoor` | ★★★ |
| Synthetic DSM 사용 + 한계 명시 | `SOLWEIG "synthetic DSM" OR "building footprint" limitation urban` | ★★★ |
| IDW 보간법 원전 | `Shepard 1968 inverse distance weighting` | ★★☆ |
| SVF와 MRT 상관 실증 | `sky view factor mean radiant temperature correlation urban` | ★★☆ |
| UTCI vs MRT 비교 연구 | `UTCI MRT comparison outdoor thermal comfort index` | ★☆☆ |

---

## 7. 인용 지도 (논문 섹션별)

```
서론
├── Basu et al. (2024) — 열환경이 보행 접근성을 제약한다
├── Colaninno et al. (2025) — UTCI + 보행 네트워크 프레임워크
└── [미확보] 보행 회피 온도 임계값 근거

방법론 — MRT 산출
├── Lindberg et al. (2008) — SOLWEIG 모델 원본
├── Lindberg & Grimmond (2011) — MRT 표준 공식
├── Erbs et al. (1982) — 직산 분리
├── Brutsaert (1975) — 대기 장파 추정
└── Fischereit (2021) — 단순화 접근의 선행 사례

방법론 — UTCI Hard Cut
└── Bröde et al. (2012) — UTCI 등급 (38°C = very strong heat stress)

방법론 한계
├── Johansson et al. (2014) — MRT 측정 표준화 문제
└── [미확보] Synthetic DSM 사용 한계 인정 논문

```
