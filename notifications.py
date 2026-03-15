"""
알림 모듈
- 텔레그램 메시지 전송
"""

import logging
import urllib.request
import urllib.parse

from config import load_config

logger = logging.getLogger(__name__)


def send_telegram(message):
    """텔레그램으로 알림 메시지 전송"""
    try:
        config = load_config()
        token = config.get("telegram_bot_token", "")
        chat_id = config.get("telegram_chat_id", "")
        if not token or not chat_id:
            logger.warning("텔레그램 설정이 없어 알림을 건너뜁니다.")
            return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.warning(f"텔레그램 알림 전송 실패: {e}")
