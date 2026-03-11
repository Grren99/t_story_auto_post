#!/bin/bash
# ============================================================
# launchd 스케줄 등록/해제 스크립트
# 사용법:
#   bash setup_launchd.sh install   → 스케줄 등록
#   bash setup_launchd.sh uninstall → 스케줄 해제
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAUNCH_DIR="$HOME/Library/LaunchAgents"

# LaunchAgents 디렉토리 생성
mkdir -p "$LAUNCH_DIR"

if [ "$1" = "uninstall" ]; then
    echo "스케줄 해제 중..."
    for h in 9 10 11 12 13 14; do
        LABEL="com.tistory.autopost.$h"
        launchctl unload "$LAUNCH_DIR/$LABEL.plist" 2>/dev/null
        rm -f "$LAUNCH_DIR/$LABEL.plist"
        echo "  ✅ $h시 스케줄 해제"
    done
    echo "완료! 모든 스케줄이 해제되었습니다."
    exit 0
fi

# cron 제거
echo "기존 cron 스케줄 제거..."
crontab -r 2>/dev/null
echo "  ✅ cron 제거 완료"

echo ""
echo "launchd 스케줄 등록 중..."
for h in 9 10 11 12 13 14; do
    LABEL="com.tistory.autopost.$h"
    PLIST="$SCRIPT_DIR/$LABEL.plist"

    if [ ! -f "$PLIST" ]; then
        echo "  ❌ $PLIST 파일 없음"
        continue
    fi

    # 기존 등록 해제
    launchctl unload "$LAUNCH_DIR/$LABEL.plist" 2>/dev/null

    # plist 복사
    cp "$PLIST" "$LAUNCH_DIR/$LABEL.plist"

    # 등록
    launchctl load "$LAUNCH_DIR/$LABEL.plist"
    echo "  ✅ $h시 스케줄 등록 완료"
done

echo ""
echo "========================================="
echo "  등록 완료! 매일 9시~14시 자동 포스팅"
echo "  로그: $SCRIPT_DIR/launchd.log"
echo "========================================="
echo ""
echo "확인: launchctl list | grep tistory"
