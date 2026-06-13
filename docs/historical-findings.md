# 역대 지방선거 쌍둥이 득표 확인 결과

작성일: 2026-06-13

## 1. 이번에 확보한 공식 원자료

중앙선거관리위원회 개방포털과 공공데이터포털에서 다음 파일을 확보했다.

- [data/raw/nec-local/2010-local.xlsx](/Users/janghokim/Documents/election-test/data/raw/nec-local/2010-local.xlsx)
- [data/raw/nec-local/2014-local.xlsx](/Users/janghokim/Documents/election-test/data/raw/nec-local/2014-local.xlsx)
- [data/raw/nec-local/2018-local.xlsx](/Users/janghokim/Documents/election-test/data/raw/nec-local/2018-local.xlsx)
- [data/raw/nec-local/2022-local.xlsx](/Users/janghokim/Documents/election-test/data/raw/nec-local/2022-local.xlsx)

확인한 공식 데이터셋:

- 제5회 전국동시지방선거 개표결과
- 제6회 전국동시지방선거 개표결과
- 제7회 전국동시지방선거 개표결과
- 제8회 전국동시지방선거 개표결과

이번 확인 범위에서는 `제4회 전국동시지방선거(2006-05-31)`의 같은 형태 `읍면동별 개표 XLSX`는 공식 파일데이터 목록에서 찾지 못했다.

## 2. 정규화한 데이터

변환 스크립트:

- [scripts/build_nec_local_history.py](/Users/janghokim/Documents/election-test/scripts/build_nec_local_history.py:1)

정규화 결과:

- `읍면동 총합`
  - [data/historical/kr-local-2010-total.json](/Users/janghokim/Documents/election-test/data/historical/kr-local-2010-total.json:1)
  - [data/historical/kr-local-2014-total.json](/Users/janghokim/Documents/election-test/data/historical/kr-local-2014-total.json:1)
  - [data/historical/kr-local-2018-total.json](/Users/janghokim/Documents/election-test/data/historical/kr-local-2018-total.json:1)
  - [data/historical/kr-local-2022-total.json](/Users/janghokim/Documents/election-test/data/historical/kr-local-2022-total.json:1)
- `관내사전투표`
  - [data/historical/kr-local-2014-in_person_advance.json](/Users/janghokim/Documents/election-test/data/historical/kr-local-2014-in_person_advance.json:1)
  - [data/historical/kr-local-2018-in_person_advance.json](/Users/janghokim/Documents/election-test/data/historical/kr-local-2018-in_person_advance.json:1)
  - [data/historical/kr-local-2022-in_person_advance.json](/Users/janghokim/Documents/election-test/data/historical/kr-local-2022-in_person_advance.json:1)

총 분석 단위 수:

- 총합 읍면동: `89,238`개
- 관내사전투표 읍면동: `62,579`개

`잘못 투입·구분된 투표지` 같은 특수 행과 `0표 패턴`은 강한 비교에서는 제외했다.

## 3. 무엇을 셌는가

약한 기준:

- 같은 후보가 서로 다른 두 읍면동에서 같은 `양의 득표수`를 받은 경우

강한 기준:

- `top2`: 상위 2명의 득표 벡터가 완전히 같은 경우
- `full`: 후보 전체 득표 벡터가 완전히 같은 경우

## 4. 연도별 결과

### 4-1. 읍면동 총합

같은 후보의 같은 양의 득표수 쌍 수:

- 2010년: `38,980`
- 2014년: `32,356`
- 2018년: `72,981`
- 2022년: `63,647`

상위 2명 득표 벡터 완전 일치 쌍 수:

- 2010년: `2`
- 2014년: `2`
- 2018년: `1`
- 2022년: `0`

전체 후보 득표 벡터 완전 일치 쌍 수:

- 2010년: `1`
- 2014년: `0`
- 2018년: `0`
- 2022년: `0`

### 4-2. 관내사전투표

같은 후보의 같은 양의 득표수 쌍 수:

- 2014년: `195,185`
- 2018년: `243,368`
- 2022년: `135,214`

상위 2명 득표 벡터 완전 일치 쌍 수:

- 2014년: `44`
- 2018년: `14`
- 2022년: `2`

전체 후보 득표 벡터 완전 일치 쌍 수:

- 2014년: `1`
- 2018년: `2`
- 2022년: `0`

## 5. 실제 예시

읍면동 총합 `top2` 일치 예시:

- 2010년 경북 교육감선거:
  - 경상북도 성주군 대가면
  - 경상북도 봉화군 법전면
  - 상위 2명 득표: `[901, 330]`
- 2014년 경남 교육감선거:
  - 경상남도 의령군 화정면
  - 경상남도 함양군 휴천면
  - 상위 2명 득표: `[344, 341]`
- 2018년 경북 교육감선거:
  - 경상북도 안동시 풍천면
  - 경상북도 성주군 초전면
  - 상위 2명 득표: `[696, 640]`

관내사전투표 `top2` 일치 예시:

- 2022년 전북 광역의원비례대표:
  - 전라북도 남원시 사매면
  - 전라북도 김제시 성덕면
  - 상위 2명 득표: `[334, 61]`
- 2022년 경북 광역의원비례대표:
  - 경상북도 경산시 남천면
  - 경상북도 영양군 청기면
  - 상위 2명 득표: `[418, 69]`
- 2014년 관내사전투표 전체 벡터 일치:
  - 서울특별시 강동구 암사제1동
  - 서울특별시 강동구 성내제3동
  - 기초의원비례대표 전체 벡터: `[848, 649]`

## 6. 해석

핵심은 다음과 같다.

- `비슷한 일이 전혀 없었다`는 결론은 데이터와 맞지 않는다.
- 약한 기준인 `같은 후보 같은 표수`는 역대 지방선거에서 매우 많이 반복된다.
- 더 강한 기준인 `상위 2명 완전 일치`도 실제로 반복된다.
- `전체 벡터 완전 일치`는 훨씬 드물지만 그래도 0이 아니다.

즉, 프로젝트의 기본 주장인 `같은 득표 패턴은 실제 선거 자료에서도 자연스럽게 반복될 수 있다`는 점은 적어도 `2010~2022 공식 읍면동 자료`와 모순되지 않는다.

추가로 `관내사전투표가 왜 더 자주 보이느냐`를 따로 비교한 결과, 가장 큰 설명은 `표본 크기`였다.

- 관내사전투표 중앙값 유효표수: `964표`
- 선거일투표 중앙값 유효표수: `3,357표`
- 상위 2명 완전 일치율은 관내사전투표가 더 높았지만,
- `500~999표` 같은 같은 `n` 구간으로 맞추면 두 채널의 차이가 크게 줄었다.

자세한 비교는 [docs/advance-vs-election-day.md](/Users/janghokim/Documents/election-test/docs/advance-vs-election-day.md:1)에 따로 정리했다.

## 7. 결과 파일

원시 집계:

- [results/historical/total-candidate-votes.json](/Users/janghokim/Documents/election-test/results/historical/total-candidate-votes.json:1)
- [results/historical/total-top2-vector.json](/Users/janghokim/Documents/election-test/results/historical/total-top2-vector.json:1)
- [results/historical/total-full-vector.json](/Users/janghokim/Documents/election-test/results/historical/total-full-vector.json:1)
- [results/historical/advance-candidate-votes.json](/Users/janghokim/Documents/election-test/results/historical/advance-candidate-votes.json:1)
- [results/historical/advance-top2-vector.json](/Users/janghokim/Documents/election-test/results/historical/advance-top2-vector.json:1)
- [results/historical/advance-full-vector.json](/Users/janghokim/Documents/election-test/results/historical/advance-full-vector.json:1)

잡음 제거 후 요약:

- [results/historical/filtered-summary.json](/Users/janghokim/Documents/election-test/results/historical/filtered-summary.json:1)
- [results/historical/advance-vs-election-day.json](/Users/janghokim/Documents/election-test/results/historical/advance-vs-election-day.json:1)
