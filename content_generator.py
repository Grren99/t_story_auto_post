"""
블로그 글 콘텐츠 생성기 (Gemini API + 스마트 이미지)
- Google Gemini API로 매일 새로운 IT/개발 블로그 글 자동 생성
- 카테고리별 맞춤 이미지:
  - 책 리뷰 → Google Books API로 실제 책 표지 (무료, 키 불필요)
  - 기술/도구 → Pixabay에서 해당 기술명 검색
  - 기타 → Pixabay 일반 검색

Gemini API 키 발급: https://aistudio.google.com/apikey
Pixabay API 키 발급: https://pixabay.com/api/docs/
"""

import json
import random
import datetime
import os
import re
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

# ============================================================
# 설정
# ============================================================
CONFIG_PATH = Path(__file__).parent / "config.json"
HISTORY_PATH = Path(__file__).parent / "post_history.json"
IMAGES_DIR = Path(__file__).parent / "images"

# 블로그 글 카테고리 & 세부 주제 풀
CATEGORIES = {
    "기술 리뷰": [
        "최신 프론트엔드 프레임워크 비교 (React vs Vue vs Svelte vs Solid)",
        "2026년 주목할 백엔드 프레임워크",
        "TypeScript 5.x 새로운 기능 분석",
        "Rust가 주목받는 이유와 적용 사례",
        "Go 언어의 장단점과 실무 활용",
        "Kotlin Multiplatform 실전 후기",
        "Bun vs Node vs Deno 성능 비교",
        "Tailwind CSS vs styled-components 실전 비교",
        "GraphQL vs REST API 언제 뭘 써야 할까",
        "Next.js App Router 도입 후기",
        "Astro 프레임워크가 인기 있는 이유",
        "Vite가 Webpack을 대체하는 이유",
        "htmx로 SPA 없이 동적 웹 만들기",
        "Prisma vs TypeORM vs Drizzle ORM 비교",
        "Zod와 함께하는 TypeScript 런타임 검증",
    ],
    "개발 도구": [
        "개발자 생산성을 높이는 터미널 도구 모음",
        "AI 코딩 어시스턴트 비교 (Copilot vs Cursor vs Claude Code)",
        "최고의 API 테스트 도구 비교",
        "Git GUI 클라이언트 비교",
        "Docker Desktop 대안 정리",
        "개발자를 위한 macOS 필수 앱",
        "VS Code 생산성 향상 단축키 모음",
        "Postman vs Insomnia vs Bruno 비교",
        "개발 문서화 도구 비교 (Notion vs Confluence vs GitBook)",
        "CI/CD 파이프라인 도구 비교 (GitHub Actions vs GitLab CI)",
    ],
    "개발 책 리뷰": [
        "클린 코드(Clean Code) 핵심 요약과 실전 적용",
        "리팩터링 2판에서 배우는 코드 개선 기법",
        "도메인 주도 설계(DDD) 핵심 개념 정리",
        "가상 면접 사례로 배우는 대규모 시스템 설계",
        "이펙티브 자바 핵심 정리",
        "실용주의 프로그래머 핵심 요약",
        "디자인 패턴의 아름다움 핵심 정리",
        "객체지향의 사실과 오해 핵심 리뷰",
        "함수형 프로그래밍 입문서 비교",
        "소프트웨어 장인 정신 핵심 요약",
    ],
    "이슈 분석": [
        "오픈소스 라이선스 완벽 정리 (MIT, Apache, GPL)",
        "개발자 번아웃 예방과 생산성 관리",
        "주니어 개발자가 실무에서 겪는 흔한 실수",
        "코드 리뷰 문화 만들기 실전 가이드",
        "기술 부채를 관리하는 현실적인 방법",
        "스타트업 vs 대기업 개발자 커리어 비교",
        "개발자 이직 시 포트폴리오 작성 전략",
        "시니어 개발자가 되기 위한 역량",
        "풀스택 vs 전문 분야 어떤 길을 선택할까",
        "AI 시대에 개발자가 준비해야 할 것",
    ],
    "튜토리얼": [
        "Docker Compose로 개발 환경 한 번에 세팅하기",
        "GitHub Actions로 CI/CD 파이프라인 구축하기",
        "Python으로 웹 스크래핑 자동화하기",
        "Redis 캐시 도입으로 API 성능 10배 향상시키기",
        "Nginx 리버스 프록시 설정 완벽 가이드",
        "JWT 인증 구현 단계별 가이드",
        "Linux 서버 초기 세팅 체크리스트",
        "PostgreSQL 성능 튜닝 실전 가이드",
        "Git hooks로 코드 품질 자동 관리하기",
        "Terraform으로 AWS 인프라 코드로 관리하기",
    ],
}

# 책 제목 → Google Books 검색용 영어 제목 매핑
BOOK_TITLE_MAP = {
    "클린 코드": "Clean Code Robert Martin",
    "리팩터링 2판": "Refactoring Martin Fowler",
    "도메인 주도 설계": "Domain Driven Design Eric Evans",
    "가상 면접 사례로 배우는 대규모 시스템 설계": "System Design Interview Alex Xu",
    "이펙티브 자바": "Effective Java Joshua Bloch",
    "실용주의 프로그래머": "Pragmatic Programmer",
    "디자인 패턴의 아름다움": "Design Patterns",
    "객체지향의 사실과 오해": "Object Oriented Programming",
    "함수형 프로그래밍": "Functional Programming",
    "소프트웨어 장인 정신": "Software Craftsmanship",
    "혼자 공부하는 컴퓨터구조": "Computer Architecture",
}

# 카테고리별 기본 Pixabay 키워드
IMAGE_KEYWORDS = {
    "기술 리뷰": "programming code technology",
    "개발 도구": "developer tools software",
    "개발 책 리뷰": "programming book reading",
    "이슈 분석": "software developer teamwork",
    "튜토리얼": "coding tutorial computer",
}

# 내부 카테고리 → 티스토리 블로그 카테고리 매핑
# ⚠️ 실제 블로그 카테고리 이름과 정확히 일치해야 함 (띄어쓰기 포함)
# 현재 블로그 카테고리: 개발 지식 책, Server, - AWS 포스팅, - NCP
# 없는 카테고리는 --setup-categories 로 자동 생성 가능
TISTORY_CATEGORY_MAP = {
    "기술 리뷰": "기술 리뷰",
    "개발 도구": "개발 도구",
    "개발 책 리뷰": "개발 지식 책",
    "이슈 분석": "개발 이슈",
    "튜토리얼": "튜토리얼",
}


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_history():
    if HISTORY_PATH.exists():
        with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"posted_topics": []}


def save_history(history):
    with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def pick_topic():
    history = load_history()
    posted = set(history.get("posted_topics", []))

    all_topics = []
    for category, topics in CATEGORIES.items():
        for topic in topics:
            if topic not in posted:
                all_topics.append({"category": category, "topic": topic})

    if not all_topics:
        history["posted_topics"] = []
        save_history(history)
        for category, topics in CATEGORIES.items():
            for topic in topics:
                all_topics.append({"category": category, "topic": topic})

    today_seed = datetime.date.today().toordinal()
    random.seed(today_seed)
    chosen = random.choice(all_topics)
    random.seed()

    return chosen["category"], chosen["topic"]


# ============================================================
# 이미지 다운로드 공통
# ============================================================
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
                # 점진적 대기: 5, 10, 15, 20초
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


# ============================================================
# Google Books API - 책 표지 검색 (무료, 키 불필요)
# ============================================================
def search_book_cover(topic):
    """
    Google Books API로 책 표지 이미지 검색
    - 완전 무료, API 키 불필요
    - 한국어 책도 검색 가능
    """
    # 주제에서 책 이름 추출
    search_term = None
    for korean_title, english_title in BOOK_TITLE_MAP.items():
        if korean_title in topic:
            search_term = english_title
            break

    if not search_term:
        # 매핑에 없으면 주제 자체를 검색
        search_term = topic

    encoded_query = urllib.parse.quote(search_term)
    url = f"https://www.googleapis.com/books/v1/volumes?q={encoded_query}&maxResults=3&langRestrict=ko"

    # 429 대비 재시도 (최대 3회, 간격 2초)
    for attempt in range(3):
        req = urllib.request.Request(url, headers={
            "User-Agent": "TistoryAutoPost/1.0"
        })

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                items = result.get("items", [])

                for item in items:
                    image_links = item.get("volumeInfo", {}).get("imageLinks", {})
                    for size in ["extraLarge", "large", "medium", "thumbnail", "smallThumbnail"]:
                        img_url = image_links.get(size, "")
                        if img_url:
                            img_url = img_url.replace("http://", "https://")
                            img_url = re.sub(r'zoom=\d', 'zoom=3', img_url)

                            book_title = item.get("volumeInfo", {}).get("title", topic)
                            authors = ", ".join(item.get("volumeInfo", {}).get("authors", []))

                            return {
                                "url": img_url,
                                "title": book_title,
                                "authors": authors,
                                "type": "book_cover",
                            }
                # 검색 결과 있지만 이미지 없으면 break
                break

        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                wait_time = (attempt + 1) * 3
                print(f"   ⏳ Google Books 요청 제한 (429). {wait_time}초 후 재시도...")
                time.sleep(wait_time)
                continue
            print(f"   ⚠️ Google Books 검색 실패: {e}")
            break
        except Exception as e:
            print(f"   ⚠️ Google Books 검색 실패: {e}")
            break

    # 영어로 못 찾으면 한국어로 재시도
    if search_term != topic:
        try:
            encoded_query = urllib.parse.quote(topic)
            url = f"https://www.googleapis.com/books/v1/volumes?q={encoded_query}&maxResults=3"
            req = urllib.request.Request(url, headers={"User-Agent": "TistoryAutoPost/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                items = result.get("items", [])
                for item in items:
                    image_links = item.get("volumeInfo", {}).get("imageLinks", {})
                    for size in ["extraLarge", "large", "medium", "thumbnail"]:
                        img_url = image_links.get(size, "")
                        if img_url:
                            img_url = img_url.replace("http://", "https://")
                            img_url = re.sub(r'zoom=\d', 'zoom=3', img_url)
                            return {
                                "url": img_url,
                                "title": item.get("volumeInfo", {}).get("title", topic),
                                "authors": ", ".join(item.get("volumeInfo", {}).get("authors", [])),
                                "type": "book_cover",
                            }
        except Exception:
            pass

    return None


# ============================================================
# Pixabay 이미지 검색
# ============================================================
def search_pixabay_images(api_key, query, count=3):
    # Pixabay는 공백으로 구분된 키워드만 허용 (쉼표, 특수문자 제거)
    clean_query = query.replace(",", " ").replace(";", " ").strip()
    # 연속 공백 제거 & 최대 100자
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


# ============================================================
# Unsplash 폴백 이미지 (API 키 불필요, Pixabay 실패 시 사용)
# ============================================================
def download_unsplash_image(query, filename):
    """Unsplash Source에서 이미지 다운로드 (API 키 불필요)"""
    IMAGES_DIR.mkdir(exist_ok=True)
    filepath = IMAGES_DIR / filename

    # Unsplash Source URL (리다이렉트로 실제 이미지 반환)
    clean_query = query.replace(",", " ").replace(";", " ").strip()
    keywords = "+".join(clean_query.split()[:3])  # 최대 3단어
    url = f"https://source.unsplash.com/800x450/?{urllib.parse.quote(keywords)}"

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read()
            if len(data) < 1000:  # 너무 작으면 실패한 응답
                print(f"   ⚠️ Unsplash 이미지 너무 작음 (응답: {len(data)}B)")
                return None, None
            with open(filepath, 'wb') as f:
                f.write(data)
            final_url = response.url  # 리다이렉트된 실제 URL
            print(f"   📥 Unsplash 이미지 다운로드: {filepath}")
            return str(filepath), final_url
    except Exception as e:
        print(f"   ⚠️ Unsplash 다운로드 실패: {e}")
        return None, None


# ============================================================
# 스마트 이미지 검색 (카테고리별 맞춤)
# ============================================================
def get_smart_images(category, topic, image_keywords="", pixabay_key=""):
    """
    카테고리에 따라 최적의 이미지 소스 선택:
    - 책 리뷰 → Google Books API (실제 책 표지)
    - 기타 → Pixabay (주제별 키워드 검색)
    """
    result = {"thumbnail": None, "files": [], "images_html": [], "image_map": {}}
    today = datetime.date.today().strftime("%Y%m%d")

    # === 1. 책 리뷰: 실제 책 표지 가져오기 ===
    if category == "개발 책 리뷰":
        print(f"📚 Google Books에서 책 표지 검색 중...")
        book = search_book_cover(topic)

        if book:
            print(f"   ✅ 책 발견: {book['title']} ({book['authors']})")

            # 책 표지 다운로드
            filepath = download_image(book["url"], f"{today}_book_cover.jpg")
            if filepath:
                result["thumbnail"] = filepath
                result["files"].append(filepath)

            # 책 표지 HTML (본문 상단용)
            result["images_html"].append(
                f'<div style="text-align:center;margin:20px 0;">'
                f'<img src="{book["url"]}" alt="{book["title"]}" '
                f'style="max-height:400px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);" />'
                f'<p style="font-size:13px;color:#666;margin-top:8px;">'
                f'📖 {book["title"]}{" - " + book["authors"] if book["authors"] else ""}</p>'
                f'</div>'
            )
            # URL → 로컬파일 매핑 (나중에 Tistory 업로드용)
            if filepath:
                result["image_map"][book["url"]] = filepath
        else:
            print(f"   ⚠️ 책 표지를 찾지 못했습니다.")

    # === 2. Pixabay로 추가 이미지 검색 ===
    if pixabay_key:
        search_query = image_keywords or IMAGE_KEYWORDS.get(category, "programming coding")
        print(f"🖼️ Pixabay 이미지 검색 중: {search_query}")

        # 책 리뷰면 1장만, 그 외는 2~3장
        count = 1 if category == "개발 책 리뷰" else 3
        images = search_pixabay_images(pixabay_key, search_query, count=count)

        if images:
            print(f"   ✅ Pixabay 이미지 {len(images)}장 찾음 (외부 URL 직접 사용)")
            for i, img in enumerate(images):
                # webformatURL(640px) 사용 — 다운로드 없이 외부 URL 직접 참조
                img_url = img.get("url", "") or img.get("large_url", "")
                user = img.get("user", "")
                page_url = img.get("page_url", "")

                if img_url:
                    result["images_html"].append(
                        f'<div style="text-align:center;margin:20px 0;">'
                        f'<img src="{img_url}" alt="{topic}" '
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

    # 첫 이미지: 첫 h2 바로 앞
    if len(h2_positions) >= 1:
        insert_points.append(h2_positions[0])
    # 두 번째 이미지: 중간 h2 앞
    if len(images_html) >= 2 and len(h2_positions) >= 3:
        insert_points.append(h2_positions[len(h2_positions) // 2])
    # 세 번째 이미지: 후반 h2 앞
    if len(images_html) >= 3 and len(h2_positions) >= 5:
        insert_points.append(h2_positions[len(h2_positions) * 3 // 4])

    # 역순 삽입
    for i, pos in enumerate(reversed(insert_points)):
        img_idx = len(insert_points) - 1 - i
        if img_idx < len(images_html):
            result = result[:pos] + images_html[img_idx] + "\n" + result[pos:]

    return result


# ============================================================
# Gemini API
# ============================================================
def call_gemini_api(api_key, prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 8192}
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"Gemini API 에러 ({e.code}): {error_body}")
    except Exception as e:
        raise Exception(f"Gemini API 호출 실패: {e}")


def generate_post_with_gemini(api_key, category, topic):
    prompt = f"""당신은 한국어 IT/개발 블로그 작성 전문가입니다.

아래 조건에 맞는 블로그 글을 작성해 주세요.

[카테고리] {category}
[주제] {topic}

[작성 규칙]
1. 반드시 HTML 태그로 포맷팅하세요 (티스토리 블로그용)
2. 제목은 별도로 첫 줄에 순수 텍스트로 출력하세요 (HTML 태그 없이)
3. 제목 다음 줄에 이미지 검색 키워드를 영어로 3개 출력하세요 (쉼표 구분, 주제와 직접 관련된 구체적 키워드)
4. 셋째 줄부터 본문을 HTML로 작성하세요
5. 사용할 HTML 태그: <p>, <h2>, <b>, <blockquote>, <table>, <code>, <ul>, <li>
6. 본문은 1500~2500자 사이로 작성
7. h2 소제목을 3~6개 사용하여 구조화
8. 핵심 키워드는 <b> 태그로 강조
9. 비교 내용이 있으면 <table> 사용 (스타일 포함)
10. 테이블 스타일: style="border-collapse:collapse;width:100%", th에 background:#f4f4f4, td/th에 border:1px solid #ddd;padding:8px
11. 마지막에 댓글 유도 문구 포함
12. 실용적이고 구체적인 내용 위주로 작성

[출력 형식]
첫 줄: 글 제목 (순수 텍스트만)
둘째 줄: 이미지 검색 키워드 (영어, 쉼표 구분)
셋째 줄부터: 본문 HTML
"""

    raw_response = call_gemini_api(api_key, prompt)
    lines = raw_response.strip().split('\n')

    title = lines[0].strip().replace('#', '').replace('<h1>', '').replace('</h1>', '')
    title = title.replace('```html', '').replace('```', '').strip()

    image_keywords = ""
    content_start = 1
    if len(lines) > 1:
        second_line = lines[1].strip()
        if not second_line.startswith('<'):
            image_keywords = second_line.replace('```html', '').replace('```', '').strip()
            content_start = 2

    content = '\n'.join(lines[content_start:]).strip()
    content = content.replace('```html', '').replace('```', '').strip()

    return {"title": title, "content": content, "image_keywords": image_keywords}


# ============================================================
# 폴백
# ============================================================
FALLBACK_POSTS = [
    {
        "title": "개발자가 알아야 할 Git 명령어 TOP 10",
        "content": """<p>Git은 개발자의 필수 도구입니다. 오늘은 실무에서 가장 많이 쓰는 Git 명령어 10가지를 정리합니다.</p>
<h2>1. git log --oneline --graph</h2>
<p>커밋 히스토리를 <b>한 줄씩 그래프</b>로 보여줍니다.</p>
<h2>2. git stash / git stash pop</h2>
<p>작업 중인 변경사항을 <b>임시 저장</b>하고, 다른 브랜치에서 작업 후 다시 꺼내올 수 있습니다.</p>
<h2>3. git rebase -i</h2>
<p>커밋 히스토리를 <b>깔끔하게 정리</b>할 수 있습니다.</p>
<h2>4. git cherry-pick</h2>
<p>다른 브랜치의 <b>특정 커밋만 가져올</b> 수 있습니다.</p>
<h2>5. git bisect</h2>
<p>버그가 처음 발생한 커밋을 <b>이진 탐색으로 찾아</b>줍니다.</p>
<h2>마무리</h2>
<p>여러분이 자주 쓰는 Git 명령어가 있다면 댓글로 공유해 주세요!</p>""",
        "image_keywords": "git version control programming",
    },
]


# ============================================================
# 메인 함수
# ============================================================
def get_daily_post():
    """오늘의 블로그 글 생성 (Gemini + 스마트 이미지)"""
    config = load_config()
    api_key = config.get("gemini_api_key", "")
    pixabay_key = config.get("pixabay_api_key", "")

    category, topic = pick_topic()
    print(f"📌 선택된 카테고리: {category}")
    print(f"📌 선택된 주제: {topic}")

    post = None

    if api_key and api_key != "여기에_GEMINI_API_키":
        try:
            print("🤖 Gemini API로 글 생성 중...")
            post = generate_post_with_gemini(api_key, category, topic)
            print(f"✅ 생성 완료: {post['title']} ({len(post['content'])}자)")
        except Exception as e:
            print(f"⚠️ Gemini API 실패: {e}")
            print("📋 폴백 글을 사용합니다.")
    else:
        print("⚠️ Gemini API 키 미설정. 폴백 글 사용.")

    if post is None:
        today = datetime.date.today()
        fb = FALLBACK_POSTS[today.toordinal() % len(FALLBACK_POSTS)]
        post = {"title": fb["title"], "content": fb["content"].strip(),
                "image_keywords": fb.get("image_keywords", "")}

    # === 스마트 이미지 검색 ===
    image_data = get_smart_images(
        category=category,
        topic=topic,
        image_keywords=post.get("image_keywords", ""),
        pixabay_key=pixabay_key,
    )

    # 본문에 이미지 HTML 삽입
    if image_data["images_html"]:
        post["content"] = insert_images_into_content(
            post["content"], image_data["images_html"], topic=topic
        )
        print(f"🖼️ 이미지 {len(image_data['images_html'])}장 본문에 삽입 완료")

    if image_data["thumbnail"]:
        print(f"✅ 썸네일: {image_data['thumbnail']}")

    # 발행 이력 저장
    history = load_history()
    history["posted_topics"].append(topic)
    history.setdefault("post_log", []).append({
        "date": str(datetime.date.today()),
        "category": category,
        "topic": topic,
        "title": post["title"],
    })
    save_history(history)

    # 티스토리 카테고리 이름
    tistory_category = TISTORY_CATEGORY_MAP.get(category, category)

    return {
        "title": post["title"],
        "content": post["content"],
        "thumbnail": image_data.get("thumbnail"),
        "image_files": image_data.get("files", []),
        "image_map": image_data.get("image_map", {}),
        "category": tistory_category,
    }


def get_random_post():
    return get_daily_post()


# ============================================================
# 단독 실행 테스트
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  티스토리 블로그 글 생성기 테스트")
    print("=" * 60)
    print()

    post = get_daily_post()
    print()
    print(f"제목: {post['title']}")
    print(f"본문 길이: {len(post['content'])}자")
    print(f"썸네일: {post.get('thumbnail', '없음')}")
    print(f"이미지 파일: {post.get('image_files', [])}")
    print()
    print("--- 본문 미리보기 (앞 800자) ---")
    print(post['content'][:800])
    print("...")
