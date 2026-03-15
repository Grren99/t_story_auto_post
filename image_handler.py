"""
이미지 처리 모듈
- Pixabay 이미지 검색
- Unsplash 폴백
- 이미지 다운로드
- 본문에 이미지 삽입
"""

import json
import re
import time
import urllib.request
import urllib.error
import urllib.parse

from config import IMAGES_DIR, IMAGE_KEYWORDS


def download_image(image_url, filename, retry=4):
    """이미지를 로컬 파일로 다운로드 (429 재시도 포함, 점진적 대기)"""
    IMAGES_DIR.mkdir(exist_ok=True)
    filepath = IMAGES_DIR / filename

    for attempt in range(retry + 1):
        req = urllib.request.Request(image_url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": "https://pixabay.com/",
        })

        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                with open(filepath, 'wb') as f:
                    f.write(response.read())
            print(f"   📥 이미지 다운로드: {filepath}")
            return str(filepath)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retry:
                wait = (attempt + 1) * 5
                print(f"   ⏳ 다운로드 제한 (429). {wait}초 후 재시도... ({attempt+1}/{retry})")
                time.sleep(wait)
                continue
            print(f"   ⚠️ 이미지 다운로드 실패: {e}")
            return None
        except Exception as e:
            print(f"   ⚠️ 이미지 다운로드 실패: {e}")
            return None

    return None


def search_pixabay_images(api_key, query, count=3):
    """Pixabay에서 이미지 검색"""
    clean_query = query.replace(",", " ").replace(";", " ").strip()
    clean_query = " ".join(clean_query.split())[:100]
    encoded_query = urllib.parse.quote(clean_query)
    url = (
        f"https://pixabay.com/api/?key={api_key}"
        f"&q={encoded_query}"
        f"&image_type=photo"
        f"&orientation=horizontal"
        f"&min_width=800"
        f"&per_page={count * 2}"
        f"&safesearch=true"
        f"&lang=en"
    )

    req = urllib.request.Request(url, headers={"User-Agent": "TistoryAutoPost/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            hits = result.get("hits", [])
            images = []
            for hit in hits[:count]:
                images.append({
                    "url": hit.get("webformatURL", ""),
                    "large_url": hit.get("largeImageURL", ""),
                    "tags": hit.get("tags", ""),
                    "page_url": hit.get("pageURL", ""),
                    "user": hit.get("user", ""),
                    "type": "pixabay",
                })
            return images
    except Exception as e:
        print(f"⚠️ Pixabay 검색 실패: {e}")
        return []


def download_unsplash_image(query, filename):
    """Unsplash Source에서 이미지 다운로드 (API 키 불필요)"""
    IMAGES_DIR.mkdir(exist_ok=True)
    filepath = IMAGES_DIR / filename

    clean_query = query.replace(",", " ").replace(";", " ").strip()
    keywords = "+".join(clean_query.split()[:3])
    url = f"https://source.unsplash.com/800x450/?{urllib.parse.quote(keywords)}"

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read()
            if len(data) < 1000:
                print(f"   ⚠️ Unsplash 이미지 너무 작음 (응답: {len(data)}B)")
                return None, None
            with open(filepath, 'wb') as f:
                f.write(data)
            final_url = response.url
            print(f"   📥 Unsplash 이미지 다운로드: {filepath}")
            return str(filepath), final_url
    except Exception as e:
        print(f"   ⚠️ Unsplash 다운로드 실패: {e}")
        return None, None


def get_smart_images(category, topic, image_keywords="", pixabay_key=""):
    """Pixabay에서 주제별 키워드로 이미지 검색"""
    result = {"thumbnail": None, "files": [], "images_html": [], "image_map": {}}

    if pixabay_key:
        search_query = image_keywords or IMAGE_KEYWORDS.get(category, "programming coding")
        print(f"🖼️ Pixabay 이미지 검색 중: {search_query}")

        images = search_pixabay_images(pixabay_key, search_query, count=3)

        if images:
            print(f"   ✅ Pixabay 이미지 {len(images)}장 찾음 (외부 URL 직접 사용)")
            for i, img in enumerate(images):
                img_url = img.get("url", "") or img.get("large_url", "")
                user = img.get("user", "")
                page_url = img.get("page_url", "")

                if img_url:
                    # SEO 최적화: alt에 주제 키워드 + 이미지 태그 포함
                    img_tags = img.get("tags", "")
                    alt_text = f"{topic} - {img_tags}" if img_tags else topic
                    result["images_html"].append(
                        f'<div style="text-align:center;margin:20px 0;">'
                        f'<img src="{img_url}" alt="{alt_text}" '
                        f'loading="lazy" '
                        f'style="max-width:100%;height:auto;border-radius:8px;'
                        f'box-shadow:0 2px 8px rgba(0,0,0,0.1);" />'
                        f'<p style="font-size:11px;color:#999;margin-top:5px;">'
                        f'Image by {user} on <a href="{page_url}" target="_blank">Pixabay</a></p>'
                        f'</div>'
                    )

    return result


def insert_images_into_content(html_content, images_html, topic=""):
    """이미지 HTML들을 본문의 적절한 위치에 삽입"""
    if not images_html:
        return html_content

    h2_pattern = re.compile(r'(<h2[^>]*>)', re.IGNORECASE)
    h2_positions = [m.start() for m in h2_pattern.finditer(html_content)]

    if not h2_positions:
        return images_html[0] + html_content

    result = html_content
    insert_points = []

    if len(h2_positions) >= 1:
        insert_points.append(h2_positions[0])
    if len(images_html) >= 2 and len(h2_positions) >= 3:
        insert_points.append(h2_positions[len(h2_positions) // 2])
    if len(images_html) >= 3 and len(h2_positions) >= 5:
        insert_points.append(h2_positions[len(h2_positions) * 3 // 4])

    for i, pos in enumerate(reversed(insert_points)):
        img_idx = len(insert_points) - 1 - i
        if img_idx < len(images_html):
            result = result[:pos] + images_html[img_idx] + "\n" + result[pos:]

    return result
