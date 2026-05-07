# 응용지리정보체계론 텀프로젝트 CLAUDE.md

## 과제 개요
- **수업**: 2026-2 응용지리정보체계론 Final Project
- **주제**: MLLM을 활용한 거리 영상 기반 링크별 열 노출 평가 및 역세권 Thermal Catchment 분석
- **제출 기한**: 2026-05-11
- **형식**: A4 2-3매 레포트 + PPT 5분 발표

## 연구 아이디어
기존 TAVI(석사 논문)의 MRT/UTCI 산출 과정을
MLLM(Multimodal Large Language Model)으로 대체하거나 보완하는 방법론 제안.
거리 영상(Google Street View) → MLLM → 링크별 열 노출 지수 → Thermal Catchment

## 폴더 구조
```
01_데이터/거리영상/   # GSV 크롤링 이미지
02_코드/              # 분석 스크립트
03_결과물/figures/    # 출력 그래프·지도
docs/                 # 레포트, PPT 구조, MD
```

## 연계 자료
- 석사 논문 코드: /Users/jin/석사논문/TAVI/Thermal_Catchment/
- 실습 참고: /Users/jin/석사논문/TAVI/응용지리정보체계론/실습 제출물/
- GSV 크롤링: /Users/jin/석사논문/TAVI/응용지리정보체계론/구글거리영상 크롤링/
