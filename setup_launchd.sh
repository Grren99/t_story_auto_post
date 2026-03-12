#!/bin/bash
# ============================================================
# launchd 스케줄 등록/해제 스크립트
# 사용법:
#   bash setup_launchd.sh install   → 스케줄 등록
#   bash setup_launchd.sh uninstall → 스케줄 해제
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAUNCH_DIR="$HOME/Library/LaunchAgents"

# 스케줄 목록: 9:00~18:30 (30분 간격, 하루 20회)
SCHEDULES="9.00 9.30 10.00 10.30 11.00 11.30 12.00 12.30 13.00 13.30 14.00 14.30 15.00 15.30 16.00 16.30 17.00 17.30 18.00 18.30"

# LaunchAgents 디렉토리 생성
mkdir -p "$LAUNCH_DIR"

if [ "$1" = "uninstall" ]; then
    echo "스케줄 해제 중..."
    for s in $SCHEDULES; do
        LABEL="com.tistory.autopost.$s"
        launchctl unload "$LAUNCH_DIR/$LABEL.plist" 2>/dev/null
        rm -f "$LAUNCH_DIR/$LABEL.plist"
    done
    # 기존 1시간 간격 plist도 정리
    for h in 9 10 11 12 13 14; do
        LABEL="com.tistory.autopost.$h"
        launchctl unload "$LAUNCH_DIR/$LABEL.plist" 2>/dev/null
        rm -f "$LAUNCH_DIR/$LABEL.plist"
    done
    echo "✅ 모든 스케줄이 해제되었습니다."
    exit 0
fi

# cron 제거
echo "기존 cron 스케줄 제거..."
crontab -r 2>/dev/null
echo "  ✅ cron 제거 완료"

# 기존 1시간 간격 plist 해제
for h in 9 10 11 12 13 14; do
    LABEL="com.tistory.autopost.$h"
    launchctl unload "$LAUNCH_DIR/$LABEL.plist" 2>/dev/null
    rm -f "$LAUNCH_DIR/$LABEL.plist"
done

echo ""
echo "launchd 스케줄 등록 중 (30분 간격, 하루 20회)..."
COUNT=0
for s in $SCHEDULES; do
    LABEL="com.tistory.autopost.$s"
    PLIST="$SCRIPT_DIR/$LABEL.plist"

    if [ ! -f "$PLIST" ]; then
        echo "  ❌ $PLIST 파일 없음"
        continue
    fi

    # 기존 등록 해제
    launchctl unload "$LAUNCH_DIR/$LABEL.plist" 2>/dev/null

    # plist 복사 & 등록
    cp "$PLIST" "$LAUNCH_DIR/$LABEL.plist"
    launchctl load "$LAUNCH_DIR/$LABEL.plist"
    COUNT=$((COUNT + 1))
done

echo "  ✅ ${COUNT}개 스케줄 등록 완료"
echo ""
echo "========================================="
echo "  등록 완료! 매일 9:00~18:30 자동 포스팅"
echo "  30분 간격, 하루 ${COUNT}회"
echo "  로그: $SCRIPT_DIR/launchd.log"
echo "========================================="
echo ""
echo "확인: launchctl list | grep tistory"
