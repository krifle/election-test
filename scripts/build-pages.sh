#!/bin/sh

set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUTPUT_DIR=${1:-"$PROJECT_DIR/_site"}

case "$OUTPUT_DIR" in
  / | "$PROJECT_DIR")
    echo "오류: 안전하지 않은 출력 경로입니다: $OUTPUT_DIR" >&2
    exit 1
    ;;
esac

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR/data"

cp -R "$PROJECT_DIR/web/." "$OUTPUT_DIR/"
cp "$PROJECT_DIR/data/one-billion.json" "$OUTPUT_DIR/data/one-billion.json"
cp "$PROJECT_DIR/docs/analysis.md" "$OUTPUT_DIR/analysis.md"
cp "$PROJECT_DIR/docs/historical-data.md" "$OUTPUT_DIR/historical-data.md"
cp "$PROJECT_DIR/docs/historical-findings.md" "$OUTPUT_DIR/historical-findings.md"
touch "$OUTPUT_DIR/.nojekyll"

echo "GitHub Pages 정적 파일 생성 완료: $OUTPUT_DIR"
