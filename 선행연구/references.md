# 참고문헌 목록 (TAVI 연구)

> 마지막 업데이트: 2026-04-10 (SOLWEIG/합성DSM 추가)

---

## 1. Space-Time Prism / 접근성

### Hägerstrand (1970)
- **인용**: Hägerstrand, T. (1970). What about people in regional science? *Papers in Regional Science*, 24(1), 7–24.
- **핵심 내용**: Space-Time Prism(STP) 개념 원전. 개인이 주어진 시간예산 내에서 이동할 수 있는 시공간 범위를 프리즘으로 정의.
- **사용 근거 신뢰도**: A (1차 문헌, 개념 원전)

### Miller (1991)
- **인용**: Miller, H. J. (1991). Modelling accessibility using space-time prism concepts within geographical information systems. *International Journal of Geographical Information System*, 5(3), 287–301.
- **핵심 내용**: GIS 기반 STP 분석 방법론. 네트워크 기반 도달 가능 범위(PPA) 계산 정립.
- **사용 근거 신뢰도**: A (1차 문헌)

---

## 2. 15분 도시 (시간예산 15분 설정 근거)

### Moreno et al. (2021)
- **인용**: Moreno, C., Allam, Z., Chabaud, D., Gall, C., & Pratlong, F. (2021). Introducing the "15-minute city": Sustainability, resilience and place identity in future post-pandemic cities. *Smart Cities*, 4(1), 93–111.
- **핵심 내용**: 15분 도시 개념 정의. 일상 서비스에 도보·자전거 15분 내 접근 가능한 도시구조 제안.
- **사용 근거 신뢰도**: A (1차 문헌, MDPI Smart Cities)
- **사용 위치**: TIME_BUDGET = 15분 설정 이론적 근거

---

## 3. UTCI (Universal Thermal Climate Index)

### Bröde et al. (2012) — UTCI 계산 절차
- **인용**: Bröde, P., Fiala, D., Błażejczyk, K., Holmér, I., Jendritzky, G., Kampmann, B., ... & Havenith, G. (2012). Deriving the operational procedure for the Universal Thermal Climate Index (UTCI). *International Journal of Biometeorology*, 56(3), 481–494.
- **핵심 내용**: UTCI 계산 방법 및 국제 표준 열스트레스 카테고리 정의.
- **사용 근거 신뢰도**: A (1차 문헌, 국제 표준)
- **사용 위치**: UTCI → 열스트레스 카테고리 변환 기준

### UTCI 열스트레스 카테고리 (본 연구 적용 기준)
| UTCI | 카테고리 | penalty |
|---|---|---|
| < 26°C | no thermal stress | 0 |
| 26~32°C | moderate heat stress | 1 |
| 32~38°C | strong heat stress | 2 |
| 38~46°C | very strong heat stress | 3 |
| > 46°C | extreme heat stress | 4 |

출처: Bröde et al. (2012), Table 1

### Fiala et al. (2012) — UTCI 생리 모델
- **인용**: Fiala, D., Havenith, G., Bröde, P., Kampmann, B., & Jendritzky, G. (2012). UTCI-Fiala multi-node model of human heat transfer and temperature regulation. *International Journal of Biometeorology*, 56(3), 429–441.
- **핵심 내용**: UTCI 계산의 기반이 되는 인체 열전달 다절점 모델.
- **사용 근거 신뢰도**: A (1차 문헌)
- **사용 위치**: UTCI 지표 선택 배경 설명

---

## 4. SOLWEIG 및 합성 DSM

### Lindberg et al. (2008) — SOLWEIG 원전 ★ 핵심
- **인용**: Lindberg, F., Holmer, B., & Thorsson, S. (2008). SOLWEIG 1.0 – Modelling spatial variations of 3D radiant fluxes and mean radiant temperatures in complex urban settings. *International Journal of Biometeorology*, 52(7), 697–713.
- **핵심 내용**: SOLWEIG(Solar and Long-Wave Environmental Irradiance Geometry) 모델 원전. DSM 입력으로 픽셀 단위 MRT 및 UTCI 계산. 건물 폴리곤 기반 합성 DSM을 공식 입력으로 지원.
- **사용 근거 신뢰도**: A (1차 문헌, 도시기후 분야 표준 도구)
- **사용 위치**: 합성 DSM 기반 UTCI 계산 방법론 근거

### Lindberg et al. (2018) — UMEP (SOLWEIG 구현 플랫폼) ★ 핵심
- **인용**: Lindberg, F., Grimmond, C. S. B., Gabey, A., Huang, B., Kent, C. W., Sun, T., ... & Zhang, Z. (2018). Urban Multi-scale Environmental Predictor (UMEP): An integrated tool for city-based climate services. *Environmental Modelling & Software*, 99, 70–87.
- **핵심 내용**: UMEP 플랫폼 내 "DSM from polygon" 도구 명시. LiDAR 미확보 시 건물 폴리곤 + 높이 속성으로 합성 DSM 생성하는 공식 워크플로우 제공.
- **사용 근거 신뢰도**: A (1차 문헌, QGIS 오픈소스 플랫폼)
- **사용 위치**: 건물 폴리곤 → 합성 DSM 생성 방법론 근거
- **핵심 인용 문구**: "Building footprint polygons with height attributes can be used to generate a building DSM as an alternative when airborne LiDAR data is unavailable."

### Colaninno et al. (2024) — 선행연구 ★ 방법론 비교
- **인용**: Colaninno, N., Basu, R., Hosseini, M., Alhassan, A., Liu, L., & Sevtsuk, A. (2024). A sidewalk-level urban heat risk assessment framework using pedestrian mobility and urban microclimate modeling. *EPB: Urban Analytics and City Science*, 52(5), 1071–1090.
- **핵심 내용**: SOLWEIG + LiDAR DSM으로 1m 해상도 UTCI 계산 → 보도 세그먼트 집계 → 보행 열위험 평가. IPCC H×E×V 프레임워크 적용. 본 연구와 가장 유사한 방법론.
- **사용 근거 신뢰도**: A (1차 문헌, Urban Analytics and City Science)
- **사용 위치**: UTCI 계산 방법론 및 H×E×V 프레임워크 비교 근거
- **본 연구와의 차이**: Colaninno et al.은 LiDAR DSM 사용. 본 연구는 LiDAR 미확보로 건물 폴리곤 기반 합성 DSM 사용 (Lindberg et al. 2018의 공식 대안 방법).

### Hersbach et al. (2020) — ERA5 기상데이터
- **인용**: Hersbach, H., Bell, B., Berrisford, P., et al. (2020). The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society*, 146(730), 1999–2049.
- **핵심 내용**: ECMWF Copernicus Climate Change Service(C3S)의 ERA5 재분석 기상데이터. 시간별 기온·습도·풍속·일사량 제공. SOLWEIG 기상 입력으로 사용.
- **사용 근거 신뢰도**: A (1차 문헌)
- **사용 위치**: SOLWEIG 기상 입력 데이터 (ASOS 대체)

---

## 5. SVF (Sky View Factor) 및 열환경 보정

### Oke (1987) — H/W street canyon 공식 ★ 핵심
- **인용**: Oke, T. R. (1987). *Boundary Layer Climates* (2nd ed.). Routledge.
- **핵심 내용**: 도시 열섬 및 도시 협곡 에너지 수지 기본서. SVF 계산 공식 제시:
  ```
  SVF = 1 / √(1 + (H/W)²)
  ```
  H = 건물 평균 높이, W = 도로 폭
- **사용 근거 신뢰도**: A (교과서급 1차 문헌, 도시기후 분야 표준)
- **사용 위치**: `15_svf_per_link.py` SVF 계산 공식

### Lindberg & Grimmond (2011) — SVF와 MRT 관계
- **인용**: Lindberg, F., & Grimmond, C. S. B. (2011). The influence of vegetation and building morphology on shadow patterns and mean radiant temperatures in urban areas: model development and evaluation. *Theoretical and Applied Climatology*, 105(3–4), 311–323.
- **핵심 내용**: SVF 감소 → 평균복사온도(MRT) 감소 → UTCI 감소 메커니즘. 여름 낮 기준 SVF 0→1 변화 시 MRT 최대 ~10°C 차이.
- **사용 근거 신뢰도**: A (1차 문헌)
- **사용 위치**: `16_utci_link_corrected.py` SVF_COEFF = 8.0°C 설정 근거

### Chen & Ng (2012) — 수목 캐노피와 보행 열환경
- **인용**: Chen, L., & Ng, E. (2012). Outdoor thermal comfort and outdoor activities: A review of research in the past decade. *Cities*, 29(2), 118–125.
- **핵심 내용**: 수목 캐노피가 있는 보행로의 UTCI/PET 감소 효과 리뷰. 완전 캐노피 시 2~5°C 감소.
- **사용 근거 신뢰도**: A (리뷰 논문)
- **사용 위치**: `16_utci_link_corrected.py` CANOPY_COEFF = 2.5°C 설정 근거

---

## 5. 보행 속도 및 열 패널티 가중치

### 보행 속도 4.5 km/h
- 일반 성인 평균 보행속도. WHO 및 교통공학 기준 3.6~5.0 km/h 범위 내.
- 사용 위치: `WALK_SPEED = 4.5 * 1000 / 3600`

### 열 패널티 가중치 α = 0.15
- **현재 상태**: 임의 설정값 (문헌 근거 확보 필요)
- 민감도 분석(α = 0.10, 0.15, 0.20, 0.30) 수행 예정
- 사용 위치: `data['thermal_time'] = base_time * (1 + alpha * penalty)` (구 모델)
- **주의**: 신규 모델(링크 회피)에서는 α 불필요. 임계값(38°C)이 대신 사용됨.

---

## 6. 공간보간 (IDW)

### Shepard (1968)
- **인용**: Shepard, D. (1968). A two-dimensional interpolation function for irregularly-spaced data. *Proceedings of the 1968 ACM National Conference*, 517–524.
- **핵심 내용**: Inverse Distance Weighting(IDW) 공간보간법 원전.
- **사용 근거 신뢰도**: A (1차 문헌)
- **사용 위치**: ASOS 관측소 → 링크별 UTCI 보간 (`link_utci_by_hour_v3.csv` 생성 시)

---

## 8. 추가 확인 필요

| 내용 | 현재 상태 | 할 일 |
|---|---|---|
| α = 0.15 패널티 근거 | 미확보 | 유사 연구에서 인용 가능한 값 탐색 |
| 도로 유형별 폭 추정값 | 실무 기준 | 국토부 도로설계기준 또는 OSM 통계 인용 필요 |
| SOLAR_FACTOR(시간별) | 서울 여름 태양고도 근사 | 기상청 일사량 데이터로 검증 가능 |
