#!/bin/bash
# ============================================
# 티스토리 자동 포스팅 - 서버 초기 설치 스크립트
# Ubuntu/Debian 기반 Linux 서버용
# ============================================

set -e

echo "🚀 티스토리 자동 포스팅 서버 설치 시작"
echo "==========================================="

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${PROJECT_DIR}"

# 1. 시스템 패키지 설치
echo ""
echo "📦 [1/5] 시스템 패키지 설치..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv wget curl unzip

# 2. Google Chrome 설치 (headless 모드용)
echo ""
echo "🌐 [2/5] Google Chrome 설치..."
if ! command -v google-chrome &> /dev/null; then
    wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo apt-get install -y -qq /tmp/chrome.deb || sudo apt-get install -f -y -qq
    rm -f /tmp/chrome.deb
    echo "   ✅ Chrome 설치 완료: $(google-chrome --version)"
else
    echo "   ✅ Chrome 이미 설치됨: $(google-chrome --version)"
fi

# 3. Python 가상환경 + 패키지 설치
echo ""
echo "🐍 [3/5] Python 가상환경 설정..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "   ✅ Python 패키지 설치 완료"

# 4. config.json 확인
echo ""
echo "⚙️  [4/5] 설정 파일 확인..."
if [ ! -f "config.json" ]; then
    echo "   ❌ config.json이 없습니다!"
    echo "   config.example.json을 복사해서 설정하세요:"
    echo "   cp config.example.json config.json"
    echo "   nano config.json"
else
    echo "   ✅ config.json 존재"
fi

# 5. logs 디렉토리 생성
echo ""
echo "📁 [5/5] 디렉토리 설정..."
mkdir -p logs
echo "   ✅ logs 디렉토리 준비 완료"

# 6. 테스트 실행
echo ""
echo "==========================================="
echo "✅ 설치 완료!"
echo ""
echo "📋 다음 단계:"
echo "  1. config.json 설정 확인"
echo "     nano config.json"
echo ""
echo "  2. 수동 테스트 실행"
echo "     source venv/bin/activate"
echo "     python tistory_poster.py"
echo ""
echo "  3. cron 등록"
echo "     bash setup_cron.sh"
echo ""
echo "  4. 실행 확인"
echo "     crontab -l"
echo "     tail -f logs/cron_$(date +%Y%m%d).log"
