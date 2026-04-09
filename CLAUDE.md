# 프로젝트 CLAUDE.md — TAVI 논문 분석

## 연구 개요
- **주제**: 열환경을 반영한 대중교통 역세권 보행 접근성 취약성 지수 (TAVI)
- **연구 질문**: 폭염 시 UTCI 기반 열환경 소프트 제약을 적용했을 때 역세권 Thermal Catchment가 얼마나 감소하는가? 그 감소 패턴을 공간 환경 변수로 설명할 수 있는가?
- **연구 지역**: 성동구 (서울) — 전체 지하철역 7개 (응봉·성수·왕십리·행당·뚝섬·서울숲·옥수)
- **핵심 지표**: reduction_pct(%) = (Classic Catchment − Thermal Catchment) / Classic Catchment × 100

## 연구 방향 (Plan A 우선, Plan B 확장)
- **Plan A**: 공간환경 변수(NDVI, 불투수면, 건물높이, 하천거리 등) → reduction_pct 회귀분석
- **Plan B (확장)**: H×E×V 프레임워크 → TAVI = Hazard × Exposure × Vulnerability

## 폴더 구조
```
01_네트워크/     # 도로 네트워크 데이터 (OSM)
02_기상데이터/   # UTCI, 기온, 열환경 시계열 데이터
03_건물데이터/   # 건물 형태, DEM, 그늘 자원
04_분석결과/     # Catchment 계산 결과물
05_시각화/       # 지도, 그래프 시각화
docs/            # 연구 레포트, 보고서
선행연구/        # 참고 논문
```

## 분석 환경
- Python 기반 분석 (Jupyter Notebook + .py 스크립트)
- 주요 라이브러리: geopandas, networkx, osmnx, shapely, matplotlib, contextily
- 좌표계: EPSG:4326 (네트워크), EPSG:3857 (베이스맵), EPSG:5186 (거리계산)

## 코딩 규칙
- 분석 코드는 Jupyter Notebook(.ipynb) 우선, 반복 실행 스크립트는 .py
- 재현 가능성 확보: 난수 시드 고정, 경로는 상대경로 사용
- 중간 결과물: `04_분석결과/`에 저장
- 시각화: `04_분석결과/figures/` 또는 `05_시각화/`에 저장

## 핵심 파라미터
- WALK_SPEED = 4.5 km/h
- TIME_BUDGET = 30분
- ALPHA = 0.15 (열 패널티 가중치)
- UTCI 기준: <26°C(0), 26~32(1), 32~38(2), 38~46(3), >46(4)

## 작업 규칙
- 항상 한국어로 작성
- 출처 없는 통계·수치 사용 금지
- 파일명: YYYY-MM-DD_주제.md 형식
- 분석 로직 변경 전 현재 결과물 백업 확인

## 절대 하지 말 것
- 출처 없는 통계 인용
- 검증 안 된 정보를 사실처럼 기술
- 대용량 데이터 파일 Git 커밋 (gitignore 확인)
