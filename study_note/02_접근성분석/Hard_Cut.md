# Hard Cut — 이분법적 링크 제거

## 한 줄 정의
> MRT가 임계값 이상인 도로 구간을 **완전히 통행 불가** 로 처리하는 방식 (0 아니면 1)

---

## 쉬운 설명

MRT ≥ 55°C인 도로 구간은 "못 걷는 곳"으로 간주하고 **지도에서 그냥 지워버리는** 방식입니다.

- MRT 54°C 링크: 통과 가능 ✅
- MRT 55°C 링크: 통과 불가 ❌
- MRT 56°C 링크: 통과 불가 ❌

임계값을 기준으로 딱 잘라서(Hard) 판단합니다.

---

## 이 연구에서 어떻게 쓰였나

```python
hot_edges = set(zip(
    h13[h13['mrt'] >= MRT_THRESH]['u'].astype(str),
    h13[h13['mrt'] >= MRT_THRESH]['v'].astype(str)
))
G_thermal = G.copy()
G_thermal.remove_edges_from([
    (u, v) for u, v in G_thermal.edges()
    if (str(u), str(v)) in hot_edges or (str(v), str(u)) in hot_edges
])
```

13시 기준 **약 3,010개 링크(19.3%)** 가 제거됩니다.

---

## 대안이 있었나? 왜 Hard Cut을 썼나?

| 방법 | 설명 | 비교 |
|------|------|------|
| **Hard Cut (이 연구)** | 임계값 초과 → 완전 제거 | 단순·명확·공간 단위 개념화 쉬움 |
| **Soft Penalty** | MRT가 높을수록 보행 속도 감소 | 더 현실적이지만 임계값 효과 희석 |
| **Madina 방식** | Perceived distance로 연속 함수 | Hard Cut = Madina의 이진화 특수 케이스로 인용 가능 |
| **UTCI 등급별 속도 감소** | UTCI 구간별로 다른 속도 적용 | 폭염 조건에서 포화 효과로 차별화 불가 |

**Hard Cut을 선택한 이유**:
1. **공간 단위 개념화**: "Thermal Catchment Area"라는 면적 개념을 만들려면 Hard Cut이 필요 (Soft Penalty는 면적이 아니라 연속적인 접근성 점수가 됨)
2. **물리적 임계값 근거**: UTCI ≥ 38°C = "Extreme Heat Stress" → 신체 활동 위험 → 회피 행동의 이분법적 근거
3. **Madina 이론 연결**: Sevtsuk & Alhassan(2025)의 Perceived Distance 프레임워크에서 Hard Cut은 이진화 특수 케이스로 정당화 가능

---

## Hard Cut의 한계

- **55°C 미만이라도 더울 수 있음**: 54°C도 충분히 위험하지만 통과 가능으로 처리
- **행동 가정 단순화**: 실제로는 개인별로 임계값이 다름 (노인, 어린이, 기저질환자)
- → Monte Carlo로 임계값 불확실성을 분포로 다루어 보완

---

## 핵심 수치

| 항목 | 값 |
|------|-----|
| 임계값 | MRT ≥ 55°C |
| 제거 링크 수 (13시) | ~3,010개 (19.3%) |
| 총 네트워크 링크 | 15,608개 |
| 임계값 근거 | UTCI=38°C → MRT 역산 |

---

## 관련 개념
- [[UTCI]] — Hard Cut 임계값의 근거 제공
- [[Thermal_Catchment]] — Hard Cut 적용 후 남은 접근 가능 범위
- [[Monte_Carlo]] — 임계값 불확실성 보완
