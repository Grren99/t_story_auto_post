#!/bin/bash
# ============================================
# 티스토리 자동 포스팅 - cron 설정 스크립트
# Linux 서버용 (07~21시, 15회/일 - Tistory 일일 15개 제한)
# ============================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${PROJECT_DIR}/venv/bin/python"
SCRIPT="${PROJECT_DIR}/tistory_poster.py"
LOG_DIR="${PROJECT_DIR}/logs"

echo "📁 프로젝트 경로: ${PROJECT_DIR}"

mkdir -p "${LOG_DIR}"

# Python 가상환경 확인
if [ ! -f "${PYTHON_BIN}" ]; then
    echo "❌ 가상환경이 없습니다. 먼저 설치 스크립트를 실행하세요:"
    echo "   bash setup_server.sh"
    exit 1
fi

# 기존 티스토리 관련 cron 제거
echo "🗑️  기존 티스토리 cron 작업 제거 중..."
crontab -l 2>/dev/null | grep -v "tistory_poster" > /tmp/crontab_clean 2>/dev/null || true

# 새 cron 작업 추가
echo "📝 새 cron 작업 등록 중..."
cat >> /tmp/crontab_clean << CRON
# === 티스토리 자동 포스팅 (07~21시, 15회/일) ===
0 7-21 * * * cd ${PROJECT_DIR} && ${PYTHON_BIN} ${SCRIPT} >> ${LOG_DIR}/cron_\$(date +\%Y\%m\%d).log 2>&1
# === 오래된 로그 자동 삭제 (7일 이상) ===
0 3 * * * find ${LOG_DIR} -name "cron_*.log" -mtime +7 -delete 2>/dev/null
CRON

crontab /tmp/crontab_clean
rm -f /tmp/crontab_clean

echo ""
echo "✅ cron 설정 완료!"
echo ""
echo "등록된 스케줄:"
echo "  매시간 정각 (07:00 ~ 21:00, 하루 15회)"
echo "  매일 03:00에 7일 이상 된 로그 자동 삭제"
echo ""
echo "📋 확인: crontab -l"
echo "📜 로그: tail -f ${LOG_DIR}/cron_\$(date +%Y%m%d).log"
echo ""
echo "cron 제거: crontab -e 에서 tistory 관련 줄 삭제"
