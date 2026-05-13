# GTFS — 대중교통 데이터 표준

## 한 줄 정의
> 버스·지하철·트램 등의 **노선·정류장·시간표 정보를 담은 국제 표준 데이터 형식**

---

## GTFS란?

GTFS = General Transit Feed Specification. Google이 만든 대중교통 데이터 표준으로, 전 세계 대부분의 도시에서 이 형식으로 데이터를 공개합니다.

---

## 주요 파일 구조

| 파일명 | 내용 |
|--------|------|
| `routes.txt` | 노선 목록 (1호선, 153번 버스 등) |
| `trips.txt` | 각 노선의 운행 편 |
| `stop_times.txt` | 각 정류장별 도착·출발 시간 |
| `stops.txt` | 정류장 위치(좌표) 정보 |
| `calendar.txt` | 운행 요일 정보 |

---

## 이 연구에서 어떻게 썼나

**목적**: 버스 정류장별 **노선 수** 계산 → 중력모델의 가중치 $S_j$

```python
# stop_times_cleaned.txt에서 버스 노선 수 추출
st = pd.read_csv(STOP_TIMES_TXT, usecols=['trip_id', 'stop_id'])
# trip_id에서 route_id 추출 (_Ord001 같은 suffix 제거)
st['route_id'] = st['trip_id'].str.replace(r'_Ord\d+$', '', regex=True)
# 정류장별 unique 노선 수 계산
bus_route_cnt = (st[st['stop_id'].isin(bus_ids)]
                 .groupby('stop_id')['route_id'].nunique()
                 .to_dict())
```

**결과**: 버스 482개 정류장 각각의 노선 수 (1~22개 노선)

---

## 파일 크기

`stop_times_cleaned.txt` = **4.4M 행** (성동구 통과 모든 버스 정류장 × 모든 운행 편)

---

## 지하철은 GTFS에서 안 쓴?

지하철 노선 수는 수동으로 입력했습니다:

| 역 | 노선 수 | 노선 |
|----|---------|------|
| 왕십리역 | **4** | 2·5호선·분당선·경의중앙선 |
| 옥수역 | **2** | 3호선·경의중앙선 |
| 나머지 5개 역 | **1** | 각 1개 노선 |

이유: GTFS 지하철 데이터가 성동구 분석에 맞게 정제되지 않아, 직접 입력이 더 정확했음

---

## 관련 개념
- [[Gravity_Model]] — GTFS로 구한 노선 수가 가중치로 들어감
- [[Catchment_Area]] — 정류장 위치 정보 사용
