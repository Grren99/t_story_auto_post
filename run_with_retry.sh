#!/bin/bash
# ============================================================
# 크래시 자동 재시도 래퍼 (서버 cron용)
# - segfault/stack smashing 등 비정상 종료 시 최대 3회 재시도
# - 발행이 이미 완료된 뒤 죽은 경우(발행 이력에 URL 기록됨)는
#   재시도하지 않음 → 중복 발행 방지
# - 재시도부터는 --now로 실행 (랜덤 딜레이 중복 방지)
#
# 사용법: run_with_retry.sh [tistory_poster.py 인자들...]
# crontab 예시:
#   0 7,9,10,... * * * /root/t_story_auto_post/run_with_retry.sh >> 로그 2>&1
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"
MAX_RETRIES=3

cd "$SCRIPT_DIR" || exit 1

count_published_today() {
    "$PYTHON" - <<'PY'
import json, datetime
try:
    h = json.load(open("post_history.json"))
    today = str(datetime.date.today())
    print(sum(1 for p in h.get("post_log", []) if p.get("date") == today and p.get("url")))
except Exception:
    print(0)
PY
}

before=$(count_published_today)

for attempt in $(seq 1 $MAX_RETRIES); do
    extra=""
    [ "$attempt" -gt 1 ] && extra="--now"

    "$PYTHON" "$SCRIPT_DIR/tistory_poster.py" "$@" $extra
    code=$?

    [ $code -eq 0 ] && exit 0

    # 비정상 종료 — 그 사이 발행이 완료됐는지 확인 (중복 발행 방지)
    after=$(count_published_today)
    if [ "$after" -gt "$before" ]; then
        echo "⚠️ [retry] 비정상 종료(코드 $code)했지만 발행은 완료됨 — 재시도 생략"
        exit 0
    fi

    echo "⚠️ [retry] 비정상 종료(코드 $code) — 재시도 $attempt/$MAX_RETRIES"
    sleep 10
done

echo "❌ [retry] ${MAX_RETRIES}회 모두 실패 — 이번 회차 건너뜀"
exit 1
