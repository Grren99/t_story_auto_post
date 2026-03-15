"""
Gemini API 호출 모듈
- 단일 모델 호출 (429 재시도)
- 다중 API 키 + 모델 폴백 체인
"""

import json
import time
import urllib.request
import urllib.error

from config import load_config

# ============================================================
# Gemini 모델 목록
# ============================================================
GEMINI_MODELS = [
    "gemini-2.5-flash",
]


def call_gemini_api(api_key, prompt, model=None, max_retries=1):
    """단일 Gemini 모델로 API 호출 (429 재시도 포함)"""
    model = model or GEMINI_MODELS[0]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 16384}
    }

    data = json.dumps(payload).encode('utf-8')

    for attempt in range(max_retries + 1):
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            if e.code == 429 and attempt < max_retries:
                wait = (attempt + 1) * 10
                print(f"   ⏳ {model} 요청 제한 (429). {wait}초 후 재시도... ({attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            raise Exception(f"Gemini API 에러 ({e.code}): {error_body}")
        except Exception as e:
            raise Exception(f"Gemini API 호출 실패: {e}")

    raise Exception(f"Gemini API 최대 재시도 횟수 초과 ({model})")


def get_api_keys():
    """config.json에서 Gemini API 키 목록 로드"""
    config = load_config()
    keys = config.get("gemini_api_keys", [])
    if not keys:
        single = config.get("gemini_api_key", "")
        if single and single != "여기에_GEMINI_API_키":
            keys = [single]
    return keys


def call_gemini_api_with_fallback(api_key, prompt):
    """Gemini API 키 + 모델 폴백 체인"""
    api_keys = get_api_keys()
    if api_key not in api_keys:
        api_keys.insert(0, api_key)

    last_error = None
    for ki, key in enumerate(api_keys):
        key_label = f"키{ki+1}" if len(api_keys) > 1 else "API키"
        for mi, model in enumerate(GEMINI_MODELS):
            try:
                print(f"   🔄 [{key_label}] {model} 시도 중...")
                result = call_gemini_api(key, prompt, model=model)
                if ki > 0 or mi > 0:
                    print(f"   ✅ [{key_label}] {model} 폴백 성공!")
                return result
            except Exception as e:
                last_error = e
                print(f"   ⚠️ [{key_label}] {model} 실패: {e}")

        if ki < len(api_keys) - 1:
            print(f"   🔑 다음 API 키로 전환합니다...")

    raise Exception(f"모든 API 키 & 모델 실패. 마지막 에러: {last_error}")
