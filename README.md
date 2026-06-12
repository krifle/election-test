# 쌍둥이 득표 확률 실험실

2026년 6월 3일 제9회 전국동시지방선거의 이른바 "쌍둥이 득표" 논란에서
허명회 고려대 명예교수가 제시한 이항분포 모형을 재현하는 프로젝트입니다.

## 바로 보기

웹 화면만 실행할 때는 Python이나 venv가 필요하지 않습니다. `run.sh`가 Node.js
내장 웹 서버를 실행합니다.

```bash
sh run.sh
```

브라우저에서 <http://localhost:8000/web/> 을 엽니다.

다른 포트를 사용하려면:

```bash
PORT=9000 sh run.sh
```

화면에서 다음을 확인할 수 있습니다.

- 송도 사례의 정확한 일치 확률 `0.009028958...`
- 이 프로젝트에서 실제 실행한 10억 회 결과 `0.009034607`
- 브라우저 Monte Carlo 추정치의 수렴 과정
- 시행 수 `n`과 득표확률 `p`에 따른 민감도
- 행정동 수와 "유사한 쌍" 비율을 반영한 다중비교 계산
- Python으로 실행한 대규모 결과 JSON 불러오기

## Python 시뮬레이션

Python 시뮬레이션이나 테스트를 실행할 때만 `.venv`가 필요합니다.
`run.sh`가 정상적으로 작동하는 Python을 찾아 처음 한 번 `.venv`와 NumPy를
설치합니다.

```bash
sh run.sh simulate --trials 1000000 --workers 1
```

10억 회 실행 예시:

```bash
sh run.sh simulate \
  --trials 1000000000 \
  --workers 8 \
  --batch-size 1000000 \
  --output results/one-billion.json
```

`--workers`는 컴퓨터의 물리 코어 수에 맞춰 조정합니다. 10억 회는 CPU 성능에
따라 상당한 시간이 걸립니다. 메모리는 `batch-size × workers`에 비례하고,
기본 배치 크기에서는 프로세스당 대략 수십 MB 이내로 유지됩니다.

저장된 재현 결과는 [data/one-billion.json](data/one-billion.json)에 있습니다.
시드 `20260603`, 작업자 8개, 100만 회 단위 배치로 실제 10억 회를 실행했으며
9,034,607회가 일치했습니다. 브라우저 페이지는 이 체크포인트를 자동으로
불러와 수렴 그래프에 표시합니다.

## 검증

```bash
sh run.sh test
```

기본 `python3`가 macOS 코드 서명 오류로 실행되지 않으면 스크립트가 다른
Python 설치를 자동으로 찾습니다. 자동 탐색이 실패하면 Homebrew Python을
설치하거나 경로를 직접 지정합니다.

```bash
brew install python
PYTHON_BIN=/opt/homebrew/bin/python3 sh run.sh test
```

자세한 조사 내용과 통계적 해석은 [docs/analysis.md](docs/analysis.md)를 참고하세요.
