# 확보된 참고문헌 정리
**TAVI 석사논문 | 신진 | 최종 업데이트: 2026-05-06**

> **표기 규칙**
> - ✅ PDF 직접 확인 / 검색 결과에서 직접 인용
> - ⚠️ 원문 확인 필요 (논문 열람 후 직접 발췌 필요)
> - 인용 양식: APA 7th

---

## 1. MRT 산출 — SOLWEIG 모델

### Lindberg, F., Holmer, B., & Thorsson, S. (2008)
**APA**
> Lindberg, F., Holmer, B., & Thorsson, S. (2008). SOLWEIG 1.0 – Modelling spatial variations of 3D radiant fluxes and mean radiant temperature in complex urban settings. *International Journal of Biometeorology*, 52(7), 697–713. https://doi.org/10.1007/s00484-008-0162-7

**인용 위치**: 방법론 섹션 — SOLWEIG 모델 도입, MRT 산출 기반 모델 소개

**원문 (✅ 검색 결과 확인)**
> "A new radiation model (SOLWEIG 1.0), which simulates spatial variations of 3D radiation fluxes and Tmrt in complex urban settings, is presented."
> (복잡한 도시 환경에서 3D 복사 플럭스와 평균복사온도의 공간 변이를 시뮬레이션하는 새로운 복사 모델 SOLWEIG 1.0을 제시한다.)

---

### Lindberg, F., & Grimmond, C. S. B. (2011)
**APA**
> Lindberg, F., & Grimmond, C. S. B. (2011). The influence of vegetation and building morphology on shadow patterns and mean radiant temperatures in urban areas: model development and evaluation. *Theoretical and Applied Climatology*, 105(3–4), 311–323. https://doi.org/10.1007/s00704-010-0382-8

**인용 위치**: 방법론 섹션 — MRT 표준 공식(`MRT = [(α_k·K_abs + L_mean)/(ε_p·σ)]^0.25`) 직접 인용; SVF를 MRT 공간 변이의 주요 결정 인자로 제시

**원문 (✅ 검색 결과 확인)**
> "The solar and longwave environmental irradiance geometry (SOLWEIG) model simulates spatial variations of 3-D radiation fluxes and mean radiant temperature (Tmrt) as well as shadow patterns in complex urban settings. A new vegetation scheme is included in SOLWEIG and evaluated, with a new shadow casting algorithm for complex vegetation structures."
> (SOLWEIG 모델은 복잡한 도시 환경에서 3D 복사 플럭스와 평균복사온도, 그림자 패턴의 공간 변이를 시뮬레이션한다. 복잡한 식생 구조에 대한 새로운 그림자 투영 알고리즘을 포함한 새로운 식생 기법이 포함·평가되었다.)

> "An overall correspondence of R² = 0.91 (p < 0.01, RMSE = 3.1 K) [between modelled and observed Tmrt]."
> (모델과 실측 Tmrt 사이의 전반적 일치도: R² = 0.91, RMSE = 3.1K.)

---

### Lindberg, F., Onomura, S., & Grimmond, C. S. B. (2016)
**APA**
> Lindberg, F., Onomura, S., & Grimmond, C. S. B. (2016). Influence of ground surface characteristics on the mean radiant temperature in urban areas. *International Journal of Biometeorology*, 60(9), 1439–1452. https://doi.org/10.1007/s00484-016-1135-x

**인용 위치**: 방법론 한계 서술 — SOLWEIG에서 벽면 재질·풍속 미반영(DELTA_T_WALL 고정 사용)의 선행연구 근거

**원문 (✅ PDF 직접 확인)**
> "Neither wind fields nor variations in building wall materials are considered in the current version of the model."
> (현재 버전의 모델에서는 풍장과 건물 벽면 재질의 변이를 고려하지 않는다.)

> "The influence of ground surface materials on Tmrt is small compared to the effects of shadowing. Nevertheless, altering ground surface materials could contribute to a reduction in Tmrt to reduce the radiant load during heat-wave episodes in locations where shadowing is not an option."
> (지표면 재질이 Tmrt에 미치는 영향은 음영 효과에 비해 작다. 그럼에도 음영이 불가능한 위치에서 폭염 기간 복사 부하를 줄이기 위해 지표면 재질 변경이 Tmrt 감소에 기여할 수 있다.)

> "The model requires weather time-series at any time resolution (> 1 minute) for ambient air temperature (Ta), relative air humidity (RH), global (G), direct (I) and diffuse (D) solar radiation, together with a digital surface model (DSM) and site geographical location."
> (모델은 주변 기온, 상대습도, 전천일사, 직달·산란 복사 시계열과 함께 수치표면모델(DSM) 및 지점 위치 정보를 요구한다.)

---

### Lindberg, F., Grimmond, C. S. B., Gabey, A., Huang, B., Kent, C. W., Sun, T., Theeuwes, N. E., Järvi, L., Ward, H. C., Capel-Timms, I., Chang, Y., Jonsson, P., Krave, N., Liu, D., Meyer, D., Olofson, K. F. G., Tan, J., Wästberg, D., Xue, L., & Zhang, Z. (2018)
**APA**
> Lindberg, F., Grimmond, C. S. B., Gabey, A., Huang, B., Kent, C. W., Sun, T., Theeuwes, N. E., Järvi, L., Ward, H. C., Capel-Timms, I., Chang, Y., Jonsson, P., Krave, N., Liu, D., Meyer, D., Olofson, K. F. G., Tan, J., Wästberg, D., Xue, L., & Zhang, Z. (2018). Urban Multi-scale Environmental Predictor (UMEP): An integrated tool for city-based climate services. *Environmental Modelling & Software*, 99, 70–87. https://doi.org/10.1016/j.envsoft.2017.09.020

**인용 위치**: 방법론 섹션 — SOLWEIG를 포함한 UMEP 오픈소스 툴 소개; GIS 기반 건물 데이터 입력 방식의 선행 사례

**원문 (✅ PDF 직접 확인)**
> "UMEP (Urban Multi-scale Environmental Predictor), a city-based climate service tool, combines models and tools essential for climate simulations. Applications are presented to illustrate UMEP's potential in the identification of heat waves and cold waves; the impact of green infrastructure on runoff; the effects of buildings on human thermal stress; solar energy production; and the impact of human activities on heat emissions."
> (도시 기반 기후 서비스 도구인 UMEP은 기후 시뮬레이션에 필수적인 모델과 도구를 결합한다. 폭염·한파 탐지, 녹색 인프라가 유출에 미치는 영향, 건물이 인체 열 스트레스에 미치는 영향, 태양에너지 생산, 인간 활동이 열 방출에 미치는 영향 등의 적용 사례를 제시한다.)

> "planners are knowledgeable about building heights, materials and their spatial arrangement (i.e. urban surface data) and often have GIS skills, but they may not necessarily have detailed knowledge of meteorological data."
> (계획가들은 건물 높이, 재질, 공간 배치(도시 표면 데이터)에 대한 지식과 GIS 기술을 보유하지만, 기상 데이터에 대한 상세한 지식을 반드시 갖추고 있지는 않다.)

---

## 2. MRT 약식 추정 — 단순화 접근의 선행 사례

### Matzarakis, A., Rutz, F., & Mayer, H. (2010)
**APA**
> Matzarakis, A., Rutz, F., & Mayer, H. (2010). Modelling radiation fluxes in simple and complex environments: basics of the RayMan model. *International Journal of Biometeorology*, 54(2), 131–139. https://doi.org/10.1007/s00484-009-0261-0

**인용 위치**: 방법론 섹션 — LiDAR 없이 SVF와 기본 기상자료만으로 MRT를 추정하는 약식 접근의 대표적 선행 사례(RayMan 모델)

**원문 (✅ PDF 직접 확인)**
> "Short- and long-wave radiation flux densities absorbed by people have a significant influence on their energy balance. The heat effect of the absorbed radiation flux densities is parameterised by the mean radiant temperature."
> (사람이 흡수하는 단파·장파 복사 플럭스 밀도는 에너지 균형에 상당한 영향을 미친다. 흡수된 복사 플럭스 밀도의 열 효과는 평균복사온도로 매개변수화된다.)

> "The model only requires basic meteorological data (air temperature, air humidity and wind speed) for the simulation of radiation flux densities and common thermal indices for the thermal human-bioclimate."
> (이 모델은 복사 플럭스 밀도와 열 인간 생물기후를 위한 일반적 열 지수를 시뮬레이션하는 데 기온, 습도, 풍속과 같은 기본 기상 데이터만을 필요로 한다.)

> "sky view factor—because of the limitation of the horizon and the influence of short- and long-wave radiation flux densities"
> (하늘열린비율(SVF)—수평선 제한과 단파·장파 복사 플럭스 밀도에 대한 영향 때문에)

---

### Thorsson, S., Lindberg, F., Eliasson, I., & Holmer, B. (2007)
**APA**
> Thorsson, S., Lindberg, F., Eliasson, I., & Holmer, B. (2007). Different methods for estimating the mean radiant temperature in an outdoor urban setting. *International Journal of Climatology*, 27(14), 1983–1993. https://doi.org/10.1002/joc.1537

**인용 위치**: 방법론 섹션 — MRT 추정의 단순화 필요성 및 한계 인정; "모든 모델은 단순화를 요구한다"는 직접 인용

**원문 (✅ PDF 직접 확인)**
> "Modelling the Tmrt in outdoor spaces however is not evident, particular in complex urban environments and thus all models require simplifications."
> (그러나 옥외 공간에서의 Tmrt 모델링은 특히 복잡한 도시 환경에서 자명하지 않으며, 따라서 모든 모델은 단순화를 요구한다.)

> "Method C [RayMan] works very well during the middle of the day in July, i.e. at high sun elevations. However, the model considerably underestimates the Tmrt in the morning and evening in July and during the whole day in October, i.e. at low sun elevations."
> (RayMan 모델은 7월 낮 시간대(높은 태양고도)에는 잘 작동한다. 그러나 7월 아침·저녁과 10월 전일(낮은 태양고도)에서는 Tmrt를 상당히 과소추정한다.)

---

### Fischereit, J. (2021)
**APA**
> Fischereit, J. (2021). The simple urban radiation model for estimating mean radiant temperature in idealised street canyons. *Urban Climate*, 35, 100694. https://doi.org/10.1016/j.uclim.2020.100694

**인용 위치**: 방법론 섹션 — SVF와 H/W비만으로 MRT를 추정하는 단순화 모델의 선행 사례; 본 연구와 유사한 약식 접근의 SCI 근거

**원문 (✅ 검색 결과 확인)**
> "The Simple Urban Radiation Model (SURM) is an open-source and modular model presented for estimating mean radiant temperature in idealized street canyons. It addresses thermal comfort in urban areas by modeling how radiation fluxes (expressed as mean radiant temperature/Tmrt) are influenced by building morphology due to shading and reflection of radiation."
> (SURM은 이상화된 가로 협곡에서 MRT를 추정하기 위한 오픈소스 모듈형 모델이다. 음영과 복사 반사에 의한 건물 형태의 영향을 모델링하여 도시 내 열 쾌적성을 다룬다.)

---

## 3. UTCI 기준 및 등급 체계

### Bröde, P., Fiala, D., Błażejczyk, K., Holmér, I., Jendritzky, G., Kampmann, B., Tinz, B., & Havenith, G. (2012)
**APA**
> Bröde, P., Fiala, D., Błażejczyk, K., Holmér, I., Jendritzky, G., Kampmann, B., Tinz, B., & Havenith, G. (2012). Deriving the operational procedure for the Universal Thermal Climate Index (UTCI). *International Journal of Biometeorology*, 56(3), 481–494. https://doi.org/10.1007/s00484-011-0454-1

**인용 위치**: 방법론 섹션 — UTCI 38°C Hard Cut 임계값 설정 근거; "Very Strong Heat Stress" 등급 정의

**원문 (✅ 검색 결과 확인)**
> "The UTCI was classified into ten categories... values from +38°C to +46°C correspond to 'very strong heat stress'."
> (UTCI는 10개 등급으로 분류되었으며, +38°C~+46°C는 '매우 강한 열 스트레스(very strong heat stress)'에 해당한다.)

> "The Universal Thermal Climate Index (UTCI) aimed for a one-dimensional quantity adequately reflecting the human physiological reaction to the multi-dimensionally defined actual outdoor thermal environment."
> (UTCI는 실제 옥외 열환경의 다차원적 정의에 대한 인체의 생리적 반응을 적절히 반영하는 단일 차원 지표를 목표로 한다.)

---

## 4. 복사 분리 및 장파 추정

### Erbs, D. G., Klein, S. A., & Duffie, J. A. (1982)
**APA**
> Erbs, D. G., Klein, S. A., & Duffie, J. A. (1982). Estimation of the diffuse radiation fraction for hourly, daily and monthly-average global radiation. *Solar Energy*, 28(4), 293–302. https://doi.org/10.1016/0038-092X(82)90302-4

**인용 위치**: 방법론 섹션 — 전천일사(GHI)를 직달(K_dir)·산란(K_dif)으로 분리하는 Erbs 모델 적용 시

**원문 (✅ PDF 직접 확인)**
> "Hourly pyrheliometer and pyranometer data from four U.S. locations are used to establish a relationship between the hourly diffuse fraction and the hourly clearness index kT."
> (미국 4개 지점의 시간별 직달일사계 및 전천일사계 데이터를 사용하여 시간별 산란 비율과 시간별 청명도 지수 kT 사이의 관계를 수립하였다.)

> 핵심 공식 (직접 인용):
> `Id/I = 1.0 − 0.09 kT` (kT ≤ 0.22)
> `Id/I = 0.9511 − 0.1604 kT + 4.388 kT² − 16.638 kT³ + 12.336 kT⁴` (0.22 < kT ≤ 0.80)
> `Id/I = 0.165` (kT > 0.80)

---

### Brutsaert, W. (1975)
**APA**
> Brutsaert, W. (1975). On a derivable formula for long-wave radiation from clear skies. *Water Resources Research*, 11(5), 742–744. https://doi.org/10.1029/WR011i005p00742

**인용 위치**: 방법론 섹션 — 대기 장파(L_sky) 추정에서 Brutsaert 공식(`ε_sky = 0.575 × ea^(1/7)`) 사용 시

**원문 (✅ PDF 직접 확인)**
> "A derivation is presented for the effective atmospheric emissivity to predict downcoming long-wave radiation at ground level under a clear sky and for a nearly standard atmosphere. The proposed formulation has the advantage that its simple functional form is based on physical grounds without the need for empirical parameters from radiation measurements."
> (맑은 하늘 조건 및 거의 표준 대기에서 지표면 하향 장파 복사를 예측하기 위한 유효 대기 방사율 도출식을 제시한다. 제안된 공식은 복사 측정의 경험적 파라미터 없이 물리적 근거에 기반한 단순한 함수 형태라는 장점이 있다.)

> "They only require the temperature and the vapor pressure, they should be useful in obtaining a reasonable estimate where extreme accuracy is not required."
> (이 공식은 기온과 수증기압만을 요구하며, 극도의 정확도가 필요하지 않은 경우 합리적인 추정값을 얻는 데 유용하다.)

---

## 5. 보행자 열환경과 행동 반응

### Nikolopoulou, M., Baker, N., & Steemers, K. (2001)
**APA**
> Nikolopoulou, M., Baker, N., & Steemers, K. (2001). Thermal comfort in outdoor urban spaces: Understanding the human parameter. *Solar Energy*, 70(3), 227–235. https://doi.org/10.1016/S0038-092X(00)00093-1

**인용 위치**: 서론 — 열환경이 옥외 공간 이용 행태에 영향을 미친다는 근거; 생리적 접근만으로는 옥외 쾌적성을 설명하기 부족하다는 선행연구

**원문 (✅ PDF 직접 확인)**
> "The thermal environment is indeed of prime importance influencing people's use of these spaces, but psychological adaptation (available choice, environmental stimulation, thermal history, memory effect, expectations) is also of great importance in such spaces that present few constraints."
> (열환경은 이러한 공간의 이용에 영향을 미치는 가장 중요한 요소이지만, 심리적 적응(선택 가능성, 환경 자극, 열 이력, 기억 효과, 기대치)도 제약이 적은 공간에서는 매우 중요하다.)

> "The initial results demonstrate that a purely physiological approach is inadequate in characterising comfort conditions outdoors."
> (초기 결과는 순수 생리학적 접근이 옥외 쾌적성 조건을 특성화하는 데 불충분함을 보여준다.)

---

### Thorsson, S., Lindqvist, M., & Lindqvist, S. (2004)
**APA**
> Thorsson, S., Lindqvist, M., & Lindqvist, S. (2004). Thermal bioclimatic conditions and patterns of behaviour in an urban park in Göteborg, Sweden. *International Journal of Biometeorology*, 48(3), 149–156. https://doi.org/10.1007/s00484-003-0189-8

**인용 위치**: 서론 — 열환경이 '너무 덥거나 추울 때' 보행자의 공간 회피·이용 패턴을 변화시킨다는 행동 근거

**원문 (✅ PDF 직접 확인)**
> "It is found that the thermal environment, access and design are important factors in the use of the park. In order to continue to use the park when the thermal conditions become too cold or too hot for comfort, people improve their comfort conditions by modifying their clothing and by choosing the most supportive thermal opportunities available within the place."
> (열환경, 접근성, 설계가 공원 이용의 중요한 요인임을 발견하였다. 열 조건이 너무 춥거나 너무 더워 불쾌할 때, 사람들은 의복 조절과 해당 장소 내에서 가장 유리한 열 환경을 선택함으로써 쾌적성을 개선한다.)

---

## 6. 보행 네트워크 + 열환경 (Thermal Catchment 관련)

### Basu, R., Colaninno, N., Alhassan, A., & Sevtsuk, A. (2024)
**APA**
> Basu, R., Colaninno, N., Alhassan, A., & Sevtsuk, A. (2024). Hot and bothered: Exploring the effect of heat on pedestrian route choice behavior and accessibility. *Cities*, 155, 105435. https://doi.org/10.1016/j.cities.2024.105435

**인용 위치**: 서론 — 폭염이 보행 접근성(walkshed/catchment)을 제약한다는 최신 선행연구; 열환경 + 보행 네트워크 분석의 직접적 선행 사례

**원문 (✅ 검색 결과 확인)**
> "Pedestrians are exposed to high levels of heat stress on hot days, which may reduce their willingness to walk. It is thus important to understand how heat affects pedestrian behavior and accessibility."
> (보행자들은 더운 날 높은 열 스트레스에 노출되며, 이는 보행 의지를 감소시킬 수 있다. 따라서 열이 보행자 행동과 접근성에 어떤 영향을 미치는지 이해하는 것이 중요하다.)

> "[The study] conducted a walkshed analysis constructing catchment areas around MBTA stations using different types based on geometric distance, perceived distance with route attributes, and UTCI on typical and hottest summer days."
> (MBTA 역사 주변 도달권을 기하학적 거리, 경로 속성 반영 지각 거리, 그리고 전형적·최고 더위 날의 UTCI를 기준으로 구분하여 walkshed 분석을 수행하였다.)

---

### Colaninno, N., Basu, R., Hosseini, M., Alhassan, A., Liu, L., & Sevtsuk, A. (2025)
**APA**
> Colaninno, N., Basu, R., Hosseini, M., Alhassan, A., Liu, L., & Sevtsuk, A. (2025). A sidewalk-level urban heat risk assessment framework using pedestrian mobility and urban microclimate modeling. *Environment and Planning B: Urban Analytics and City Science*, 52(1). https://doi.org/10.1177/23998083241280746

**인용 위치**: 서론 — UTCI + 보행 네트워크 결합 프레임워크의 선행 사례; 연구 갭(Thermal Catchment 미적용) 서술

**원문 (✅ 검색 결과 확인)**
> "The framework assesses pedestrian heat-related exposure and risk in urban areas by integrating the Universal Thermal Climate Index (UTCI) as the hazard and pedestrian trips to critical destinations as exposure."
> (이 프레임워크는 UTCI를 위험 요소로, 주요 목적지까지의 보행 통행을 노출 지표로 통합하여 도시 지역의 보행자 열 관련 노출 및 위험을 평가한다.)

> "The researchers created and used a sidewalk network instead of using the road network comprising street centerlines, which allows differentiation between two sides of the street that may have varying degrees of shading and vegetation."
> (도로 중심선으로 구성된 도로 네트워크 대신 보도 네트워크를 생성·활용하였으며, 이를 통해 음영과 식생 정도가 다를 수 있는 도로 양쪽을 구분할 수 있다.)

---

## 7. MRT 측정 방법론 표준화

### Johansson, E., Thorsson, S., Emmanuel, R., & Krüger, E. (2014)
**APA**
> Johansson, E., Thorsson, S., Emmanuel, R., & Krüger, E. (2014). Instruments and methods in outdoor thermal comfort studies – The need for standardization. *Urban Climate*, 10, 346–366. https://doi.org/10.1016/j.uclim.2013.12.002

**인용 위치**: 방법론 한계 섹션 — MRT 측정 기기·방법의 다양성과 비표준화 문제; 본 연구의 약식 MRT 접근이 불가피한 맥락 설명
> ⚠️ 주의: 이 논문은 MRT 55°C 임계값과 무관. 방법론 표준화 검토 논문으로만 인용.

**원문 (✅ PDF 직접 확인)**
> "We found a great variety of instruments and methods used to measure meteorological variables, especially with respect to the mean radiant temperature and wind speed."
> (기상 변수, 특히 평균복사온도와 풍속 측정에 사용되는 기기와 방법이 매우 다양함을 발견하였다.)

> "The use of a variety of methods makes it difficult to compare results of the different studies. There is thus a need for standardization and to give guidance regarding how to conduct field surveys in outdoor environments."
> (다양한 방법의 사용은 서로 다른 연구들의 결과를 비교하기 어렵게 만든다. 따라서 옥외 환경에서 현장 조사를 수행하는 방법에 대한 표준화와 지침이 필요하다.)

---

## 8. 인용 지도 (논문 섹션별)

```
서론
├── Nikolopoulou et al. (2001) — 열환경이 옥외 공간 이용에 영향
├── Thorsson et al. (2004) — 열환경이 보행 행동을 변화시킴
├── Basu et al. (2024) — UTCI + 보행 네트워크 접근성 분석
└── Colaninno et al. (2025) — UTCI + 보행 네트워크 프레임워크

방법론 — MRT 산출
├── Lindberg et al. (2008) — SOLWEIG 모델 원본
├── Lindberg & Grimmond (2011) — MRT 표준 공식 (직접 인용)
├── Erbs et al. (1982) — 직산 분리 공식
├── Brutsaert (1975) — 대기 장파 추정 공식
├── Matzarakis et al. (2010) — 약식 접근(RayMan)의 선행 사례
├── Thorsson et al. (2007) — "모든 모델은 단순화를 요구한다"
└── Lindberg et al. (2018) UMEP — GIS 기반 도시 데이터 입력 방식

방법론 — UTCI Hard Cut
└── Bröde et al. (2012) — UTCI 38°C = very strong heat stress

방법론 한계
├── Lindberg et al. (2016) — 벽면 재질·풍속 미반영은 SOLWEIG 자체 한계
├── Thorsson et al. (2007) — 단순화 모델의 과소추정 한계 인정
├── Johansson et al. (2014) — MRT 측정 방법 비표준화 문제
└── Fischereit (2021) — 단순화 MRT 추정 모델의 선행 출판 사례
```

---

## 9. 추가 확보 필요

| 필요 인용 목적 | 추천 검색 제목 | 우선순위 |
|--------------|--------------|---------|
| MRT Hard Cut 임계값 (보행 회피) | `Thermal bioclimatic conditions and patterns of behaviour` (Thorsson 2004 ← 이미 확보, 활용 가능) | —  |
| Synthetic DSM 사용 + 한계 명시 | Web of Science: `SOLWEIG "building footprint" limitation` | ★★★ |
| IDW 보간법 원전 | `Shepard 1968 "A two-dimensional interpolation function for irregularly-spaced data"` | ★★☆ |
