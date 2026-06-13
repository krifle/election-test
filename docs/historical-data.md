# 역대 선거 데이터 수집과 쌍둥이 득표 분석 계획

작성일: 2026-06-13

## 1. 결론부터

가능합니다. 지금 프로젝트는 이미 "두 지역에서 같은 득표수가 나오는 일이 드물기만 한 것은 아니다"를 수학과 시뮬레이션으로 설명하고 있으므로, 다음 단계는 실제 선거 원자료를 같은 형식으로 정규화한 뒤 연도별로 얼마나 자주 같은 패턴이 나왔는지 세는 것입니다.

이 저장소에는 이를 위한 최소 분석 도구를 추가했습니다.

- `scripts/analyze_historical_twins.py`
- `tests/fixtures/sample-historical-election.json`

정규화된 JSON만 준비되면 다음 세 가지를 바로 셀 수 있습니다.

- `candidate_votes`: 같은 후보가 서로 다른 두 지역에서 정확히 같은 표수를 받은 경우
- `top2_vector`: 상위 2명의 득표 벡터가 같은 경우
- `full_vector`: 모든 후보 득표 벡터가 같은 경우

## 2. 한국 데이터는 어디서 받을 수 있나

중앙선거관리위원회 선거통계시스템의 `역대선거` 메뉴에서 역대 지방선거 개표 자료를 볼 수 있습니다. 특히 아래 두 경로가 핵심입니다.

- 선거통계시스템 메인: <https://info.nec.go.kr/>
- 역대선거 페이지: <https://info.nec.go.kr/main/main_previous_load.xhtml>
- 역대선거 데이터 일괄 다운로드: <https://info.nec.go.kr/download/electionInfoDownload.xhtml?electionId=0000000000>

확인한 내용:

- 선관위 `역대선거` 페이지에는 `개표현황`, `개표현황(읍면동별)`, `개표현황(투표구별)`가 있습니다.
- 같은 페이지에는 `역대선거 데이터 일괄 다운로드` 메뉴가 따로 있습니다.
- 제4회~제8회 전국동시지방선거 투표율이 한 화면에서 제공되고, 세부 결과는 `역대선거` 하위 개표 메뉴로 내려갑니다.

즉, 한국 지방선거의 경우 가장 좋은 1차 원천은 선관위 공식 자료입니다.

## 3. 한국 데이터 수집 우선순위

분석 목적상 가장 중요한 단위부터 받는 것이 좋습니다.

1. `읍면동별 개표결과`
2. 가능하면 `투표구별 개표결과`
3. 사전투표와 선거일투표가 분리된다면 둘 다 보존
4. 후보별 득표수와 총유효표를 같이 저장

이유는 간단합니다.

- 현재 논란의 형태가 "특정 두 지역의 같은 후보 득표수 일치"이기 때문입니다.
- 읍면동 단위만 있어도 과거 지방선거 전체에서 유사 사례가 얼마나 있었는지 충분히 셀 수 있습니다.
- 투표구 단위까지 내려가면 더 작은 단위에서의 자연발생 빈도도 따로 볼 수 있습니다.

## 4. 추천 JSON 정규화 형식

이 프로젝트에서 쓰기 좋은 최소 공통 스키마는 아래처럼 잡는 것이 좋습니다.

```json
{
  "dataset_id": "kr-local-2022-mayor-emd",
  "country": "KR",
  "election_name": "제8회 전국동시지방선거",
  "election_type": "local",
  "year": 2022,
  "round": "general",
  "units": [
    {
      "contest_id": "incheon-mayor",
      "contest_name": "인천광역시장선거",
      "unit_id": "2818582000",
      "unit_name": "송도1동",
      "level": "dong",
      "total_valid_votes": 4470,
      "candidates": [
        {"candidate_id": "cand-a", "name": "후보A", "party": "정당A", "votes": 3030},
        {"candidate_id": "cand-b", "name": "후보B", "party": "정당B", "votes": 1440}
      ]
    }
  ]
}
```

핵심 원칙:

- 한 파일은 가능하면 `하나의 선거연도 + 하나의 나라 + 하나의 집계 체계`로 둡니다.
- `contest_id`는 선거 종류를 고정합니다.
- `unit_id`와 `unit_name`은 행정구역 또는 투표구를 뜻합니다.
- 후보 배열은 raw 값 그대로 보존합니다.

## 5. 바로 실행하는 방법

예시 파일로 구조를 확인하려면:

```bash
python3 scripts/analyze_historical_twins.py tests/fixtures/sample-historical-election.json
```

상위 2명 벡터까지 같았는지 보려면:

```bash
python3 scripts/analyze_historical_twins.py \
  tests/fixtures/sample-historical-election.json \
  --mode top2_vector
```

결과를 JSON으로 저장하려면:

```bash
python3 scripts/analyze_historical_twins.py data/kr-local-2022.json --output results/twins-2022.json
```

## 6. 해외 데이터는 어떻게 접근하면 좋나

해외는 "모든 나라를 한 번에 같은 품질로" 구하기 어렵습니다. 그래서 두 층으로 나누는 것이 좋습니다.

### 6-1. 국제 비교용 공통 베이스

- THEA: <https://electiondataarchive.org/>
- International IDEA Voter Turnout Database: <https://www.idea.int/data-tools/data/voter-turnout-database>

확인한 내용:

- THEA는 스스로를 `subnational election results` 저장소라고 설명합니다.
- International IDEA는 전 세계 투표율 데이터베이스를 제공하지만, FAQ에서 `local elections`는 포함하지 않는다고 밝힙니다.

의미:

- `정확한 지방선거 득표 벡터 비교`에는 THEA가 더 적합합니다.
- `투표율, 규모, 제도 비교` 같은 보조 지표는 IDEA가 좋습니다.

### 6-2. 나라별 공식 오픈데이터

추천 시작점:

- 브라질 TSE 오픈데이터: <https://dadosabertos.tse.jus.br>
- 멕시코 INE 결과 시스템: <https://www.ine.mx/voto-y-elecciones/resultados-electorales/>
- 미국 MIT Election Lab 데이터 허브: <https://electionlab.mit.edu/data>

확인한 내용:

- 브라질 TSE는 공개 데이터 포털에서 선거 데이터셋을 자유롭게 제공한다고 명시합니다.
- 멕시코 INE는 연방 결과 1991~2024, 지방 결과 2015~2024를 제공하고, `CSV`와 `XLSX` 다운로드를 지원한다고 명시합니다.
- MIT Election Lab은 `Local Elections`, `by precinct` 단위 데이터를 별도 카테고리로 제공합니다.

즉, 해외는 다음 전략이 현실적입니다.

- 1차: 한국 + 브라질 + 멕시코 + 미국처럼 공식 또는 준공식 공개가 잘 된 나라부터 시작
- 2차: THEA 같은 아카이브로 나라 수를 넓힘
- 3차: 각국 지방선거 관리기관 원자료와 대조

## 7. 실제 분석 질문 예시

정규화가 끝나면 다음 질문에 바로 답할 수 있습니다.

- 연도별로 같은 후보의 동일 득표가 몇 쌍 나왔는가
- 지방선거 종류별로 어떤 선거에서 더 자주 나왔는가
- 읍면동 단위와 투표구 단위의 빈도 차이는 얼마나 되는가
- 총유효표가 비슷한 지역끼리만 제한했을 때 빈도는 어떻게 달라지는가
- 상위 2후보 득표 벡터까지 동일한 사례는 몇 개인가

## 8. 추천 작업 순서

1. 한국 제4회~제8회 지방선거 `읍면동별 개표결과`를 먼저 수집
2. 연도별 JSON으로 정규화
3. `candidate_votes`와 `top2_vector` 두 기준으로 집계
4. 그 뒤 브라질이나 멕시코처럼 공개가 잘 된 나라 1개를 추가
5. 국가별 빈도를 비교할 때는 지역 수와 후보 수 차이를 같이 보정

## 9. 주의할 점

- 행정구역 개편 때문에 서로 다른 연도를 단순 비교하면 왜곡될 수 있습니다.
- 후보 수가 2명인 선거와 5명인 선거는 동일 패턴 확률이 다릅니다.
- 사전투표, 본투표, 합산결과를 섞으면 해석이 달라집니다.
- "발견된 쌍의 개수"와 "그 쌍이 놀라운지"는 다른 문제입니다.

그래서 저장 시점부터 아래 필드는 꼭 남기는 편이 좋습니다.

- `year`
- `contest_id`
- `level`
- `total_valid_votes`
- `candidate count`
- `vote channel`이 구분되면 그 정보

## 10. 다음 단계 제안

가장 생산적인 다음 단계는 한국 역대 지방선거용 수집기부터 붙이는 것입니다. 선관위 다운로드 파일 형식이 CSV/XLS/XLSX/HTML 중 무엇으로 떨어지는지만 확인되면, 이 저장소 안에 `nec -> normalized json` 변환 스크립트를 바로 이어서 만들 수 있습니다.
