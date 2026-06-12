#!/bin/sh

set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VENV_DIR=${VENV_DIR:-"$PROJECT_DIR/.venv"}
VENV_PYTHON="$VENV_DIR/bin/python"
DEPS_MARKER="$VENV_DIR/.requirements-installed"
COMMAND=${1:-serve}

if [ "$#" -gt 0 ]; then
  shift
fi

cd "$PROJECT_DIR"

python_is_usable() {
  candidate=$1

  if [ ! -x "$candidate" ] && ! command -v "$candidate" >/dev/null 2>&1; then
    return 1
  fi

  "$candidate" -c 'import subprocess, venv' >/dev/null 2>&1 &&
    "$candidate" -m ensurepip --version >/dev/null 2>&1
}

find_usable_python() {
  if [ -n "${PYTHON_BIN:-}" ]; then
    if python_is_usable "$PYTHON_BIN"; then
      SELECTED_PYTHON=$PYTHON_BIN
      return 0
    fi

    echo "오류: PYTHON_BIN=$PYTHON_BIN 은 정상적으로 실행되지 않습니다." >&2
    return 1
  fi

  for candidate in \
    /opt/homebrew/bin/python3 \
    /usr/local/opt/python/bin/python3 \
    /usr/local/opt/python@3.13/bin/python3 \
    "$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3" \
    python3 \
    /usr/local/bin/python3 \
    /usr/bin/python3
  do
    if python_is_usable "$candidate"; then
      SELECTED_PYTHON=$candidate
      return 0
    fi
  done

  return 1
}

prepare_venv() {
  if [ -d "$VENV_DIR" ] && ! python_is_usable "$VENV_PYTHON"; then
    echo "불완전한 가상환경을 다시 생성합니다: $VENV_DIR"
    rm -rf "$VENV_DIR"
  fi

  if [ ! -x "$VENV_PYTHON" ]; then
    if ! find_usable_python; then
      cat >&2 <<'EOF'
오류: 가상환경을 만들 수 있는 정상 Python 3를 찾지 못했습니다.

현재 기본 python3는 macOS 코드 서명 정책에 의해 차단된 것으로 보입니다.
Homebrew Python을 설치한 뒤 다시 실행해 주세요.

  brew install python
  sh run.sh simulate --trials 1000000 --workers 1

또는 정상 Python 경로를 직접 지정할 수 있습니다.

  PYTHON_BIN=/opt/homebrew/bin/python3 sh run.sh test
EOF
      exit 1
    fi

    echo "[1/3] Python 가상환경을 생성합니다: $VENV_DIR"
    echo "      사용 Python: $SELECTED_PYTHON"
    "$SELECTED_PYTHON" -m venv "$VENV_DIR"
  else
    echo "[1/3] Python 가상환경이 이미 준비되어 있습니다."
  fi

  if [ ! -f "$DEPS_MARKER" ] || [ requirements.txt -nt "$DEPS_MARKER" ]; then
    echo "[2/3] Python 의존성을 설치합니다."
    "$VENV_PYTHON" -m pip install -r requirements.txt
    touch "$DEPS_MARKER"
  else
    echo "[2/3] Python 의존성이 이미 준비되어 있습니다."
  fi
}

case "$COMMAND" in
  serve)
    HOST=${HOST:-127.0.0.1}
    PORT=${PORT:-8000}

    if [ -n "${NODE_BIN:-}" ]; then
      SELECTED_NODE=$NODE_BIN
    elif command -v node >/dev/null 2>&1; then
      SELECTED_NODE=node
    else
      echo "오류: 웹 서버 실행에 필요한 Node.js를 찾을 수 없습니다." >&2
      echo "Node.js를 설치하거나 NODE_BIN 환경변수로 경로를 지정해 주세요." >&2
      exit 1
    fi

    echo "웹 서버를 시작합니다. Python 가상환경은 필요하지 않습니다."
    echo "브라우저 주소: http://localhost:$PORT/"
    echo "종료하려면 Ctrl+C를 누르세요."
    exec "$SELECTED_NODE" server.js "$HOST" "$PORT"
    ;;
  simulate)
    prepare_venv
    echo "[3/3] 시뮬레이션을 실행합니다."
    exec "$VENV_PYTHON" simulate.py "$@"
    ;;
  test)
    prepare_venv
    echo "[3/3] 테스트를 실행합니다."
    exec "$VENV_PYTHON" -m unittest discover -s tests -v
    ;;
  *)
    echo "사용법:" >&2
    echo "  sh run.sh                       웹 시각화 서버 실행" >&2
    echo "  sh run.sh simulate [옵션]       Python 시뮬레이션 실행" >&2
    echo "  sh run.sh test                  테스트 실행" >&2
    exit 2
    ;;
esac
