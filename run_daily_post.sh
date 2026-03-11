#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
# ============================================================
# 티스토리 자동 포스팅 스케줄러
# 매일 지정된 시간에 자동으로 블로그 글 발행
# ============================================================

# 스크립트 경로
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/cron_run.log"
PYTHON_PATH="/usr/bin/python3"  # Mac 기본 Python3 경로

# Python 경로 자동 탐색 (pyenv, homebrew 등)
if command -v python3 &> /dev/null; then
    PYTHON_PATH="$(which python3)"
fi

# 로그에 시작 시간 기록
echo "" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "실행 시작: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "Python: $PYTHON_PATH" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 작업 디렉토리 이동
cd "$SCRIPT_DIR"

# 포스팅 실행
$PYTHON_PATH "$SCRIPT_DIR/tistory_poster.py" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

# 결과 기록
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 포스팅 성공 ($(date '+%H:%M:%S'))" >> "$LOG_FILE"
else
    echo "❌ 포스팅 실패 - 종료코드: $EXIT_CODE ($(date '+%H:%M:%S'))" >> "$LOG_FILE"
fi

echo "========================================" >> "$LOG_FILE"
