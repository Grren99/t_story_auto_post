#!/bin/bash
# ============================================================
# 티스토리 자동 포스팅 cron 설정 스크립트
#
# 사용법:
#   chmod +x setup_cron.sh
#   ./setup_cron.sh
#
# 기본: 매일 오전 9시에 자동 포스팅
# 변경하고 싶으면 아래 CRON_TIME 수정
# ============================================================

CRON_TIME="0 9 * * *"   # 매일 09:00
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_PATH="$(which python3)"
LOG_FILE="${SCRIPT_DIR}/cron_post.log"

echo "=== 티스토리 자동 포스팅 cron 설정 ==="
echo ""
echo "스크립트 경로: ${SCRIPT_DIR}"
echo "Python 경로:   ${PYTHON_PATH}"
echo "스케줄:        ${CRON_TIME} (매일 오전 9시)"
echo "로그 파일:     ${LOG_FILE}"
echo ""

# 기존 cron에서 tistory_poster 관련 항목 제거 후 새로 추가
CRON_CMD="${CRON_TIME} cd ${SCRIPT_DIR} && ${PYTHON_PATH} tistory_poster.py >> ${LOG_FILE} 2>&1"

# 기존 crontab 백업
crontab -l > /tmp/crontab_backup 2>/dev/null

# 기존 tistory 관련 cron 제거 후 새로 추가
(crontab -l 2>/dev/null | grep -v "tistory_poster" ; echo "${CRON_CMD}") | crontab -

echo "✅ cron 등록 완료!"
echo ""
echo "등록된 cron 확인:"
crontab -l | grep tistory_poster
echo ""
echo "cron 제거하려면: crontab -e 에서 해당 줄 삭제"
