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
    "AI 머신러닝": [
        "ChatGPT vs Claude vs Gemini 성능 비교 분석",
        "LLM 파인튜닝 입문 가이드",
        "RAG(검색 증강 생성) 구현 실전 가이드",
        "LangChain으로 AI 에이전트 만들기",
        "Stable Diffusion 로컬 설치와 활용법",
        "허깅페이스 Transformers 라이브러리 입문",
        "AI 코딩 어시스턴트 활용 극대화 전략",
        "MLOps 파이프라인 구축 가이드",
        "벡터 데이터베이스 비교 (Pinecone vs Weaviate vs Chroma)",
        "프롬프트 엔지니어링 실전 테크닉",
    ],
    "클라우드 인프라": [
        "AWS vs GCP vs Azure 서비스 비교 가이드",
        "쿠버네티스(K8s) 입문 핵심 개념 정리",
        "서버리스 아키텍처 장단점과 적용 사례",
        "AWS Lambda 실전 활용 가이드",
        "클라우드 비용 최적화 전략",
        "Docker 컨테이너 보안 베스트 프랙티스",
        "IaC(Infrastructure as Code) 도구 비교",
        "마이크로서비스 아키텍처 설계 원칙",
        "모니터링 도구 비교 (Grafana vs Datadog vs New Relic)",
        "CDN 서비스 비교와 적용 가이드",
    ],
    "보안": [
        "웹 애플리케이션 보안 OWASP Top 10 정리",
        "API 보안 베스트 프랙티스",
        "SQL Injection 방어 실전 가이드",
        "XSS 공격과 방어 패턴 총정리",
        "OAuth 2.0과 OIDC 인증 흐름 완벽 가이드",
        "HTTPS와 TLS 동작 원리 쉽게 이해하기",
        "컨테이너 보안 체크리스트",
        "개발자가 알아야 할 암호화 기초",
        "GitHub 시크릿 관리와 보안 자동화",
        "제로 트러스트 보안 모델 이해하기",
    ],
    "커리어 취업": [
        "개발자 기술 면접 준비 완벽 가이드",
        "코딩 테스트 효율적인 준비 전략",
        "개발자 이력서 작성법과 포트폴리오 전략",
        "주니어 개발자 연봉 협상 가이드",
        "개발자 사이드 프로젝트 아이디어 모음",
        "개발자 영어 공부법과 추천 리소스",
        "테크 리드가 되기 위한 소프트 스킬",
        "개발자 블로그 운영 전략과 효과",
        "프리랜서 개발자 시작 가이드",
        "개발자 번아웃 극복과 동기 부여 방법",
    ],
    "생산성 자동화": [
        "개발 워크플로우 자동화 도구 모음",
        "셸 스크립트로 반복 작업 자동화하기",
        "Notion으로 개발 프로젝트 관리하기",
        "개발자를 위한 시간 관리 기법",
        "cron과 스케줄러로 서버 자동화하기",
        "GitHub Actions 워크플로우 활용 사례 모음",
        "Python 자동화 스크립트 실전 예제",
        "개발 환경 세팅 자동화 (dotfiles, Ansible)",
        "Slack 봇으로 팀 생산성 높이기",
        "코드 리뷰 자동화 도구와 전략",
    ],
}

# 카테고리별 기본 Pixabay 키워드
IMAGE_KEYWORDS = {
    "기술 리뷰": "programming code technology",
    "개발 도구": "developer tools software",
    "개발 책 리뷰": "programming book reading",
    "이슈 분석": "software developer teamwork",
    "튜토리얼": "coding tutorial computer",
    "AI 머신러닝": "artificial intelligence machine learning",
    "클라우드 인프라": "cloud computing server infrastructure",
    "보안": "cybersecurity lock digital",
    "커리어 취업": "career developer interview",
    "생산성 자동화": "productivity automation workflow",
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
    "AI 머신러닝": "AI 머신러닝",
    "클라우드 인프라": "클라우드 인프라",
    "보안": "보안",
    "커리어 취업": "커리어 취업",
    "생산성 자동화": "생산성 자동화",
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


def pick_topic_from_pool():
    """하드코딩된 주제 풀에서 선택 (Gemini 주제 생성 실패 시 폴백용)"""
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


def is_similar_topic(new_topic, existing_topics, threshold=0.5):
    """새 주제가 기존 주제와 유사한지 검사 (키워드 겹침 비율)"""
    new_words = set(new_topic.lower().replace(",", " ").replace(":", " ").split())
    # 불용어 제거
    stopwords = {"vs", "및", "의", "와", "을", "를", "이", "가", "에", "는", "은", "로", "으로", "위한", "대한", "어떤", "가이드", "정리", "비교", "분석", "완벽", "실전", "핵심"}
    new_words -= stopwords

    if len(new_words) < 2:
        return False

    for existing in existing_topics:
        existing_words = set(existing.lower().replace(",", " ").replace(":", " ").split()) - stopwords
        if len(existing_words) < 2:
            continue
        overlap = len(new_words & existing_words)
        similarity = overlap / min(len(new_words), len(existing_words))
        if similarity >= threshold:
            return True
    return False


def pick_balanced_category(history):
    """최근 발행 이력 기반 카테고리 균등 분배 - 덜 쓴 카테고리 우선 선택"""
    categories = list(CATEGORIES.keys())
    post_log = history.get("post_log", [])

    # 최근 30개 글의 카테고리 빈도 집계
    recent_posts = post_log[-30:] if len(post_log) > 30 else post_log
    category_counts = {cat: 0 for cat in categories}
    for post in recent_posts:
        cat = post.get("category", "")
        if cat in category_counts:
            category_counts[cat] += 1

    # 최소 빈도 카테고리들 중 랜덤 선택
    min_count = min(category_counts.values())
    least_used = [cat for cat, count in category_counts.items() if count == min_count]
    return random.choice(least_used)


def generate_topic_with_gemini(api_key):
    """Gemini API로 새로운 블로그 주제 자동 생성"""
    history = load_history()
    posted = history.get("posted_topics", [])
    recent_topics = posted[-30:] if len(posted) > 30 else posted  # 최근 30개만

    category = pick_balanced_category(history)

    recent_list = "\n".join(f"- {t}" for t in recent_topics) if recent_topics else "(없음)"

    prompt = f"""당신은 한국어 IT/개발 블로그 주제를 기획하는 전문가입니다.

아래 카테고리에 맞는 블로그 글 주제를 1개만 제안해 주세요.

[카테고리] {category}

[카테고리 설명]
- 기술 리뷰: 프레임워크, 언어, 라이브러리 비교/분석
- 개발 도구: IDE, 터미널 도구, 생산성 도구 소개
- 개발 책 리뷰: 프로그래밍/소프트웨어 관련 도서 리뷰
- 이슈 분석: 개발자 커리어, 업계 트렌드, 문화
- 튜토리얼: 단계별 실습 가이드, 세팅 가이드
- AI 머신러닝: LLM, 생성형 AI, MLOps, 머신러닝 실전 활용
- 클라우드 인프라: AWS/GCP/Azure, 쿠버네티스, 서버리스, DevOps
- 보안: 웹 보안, 인증/인가, 암호화, 보안 자동화
- 커리어 취업: 면접 준비, 이력서, 연봉 협상, 커리어 성장
- 생산성 자동화: 개발 워크플로우, 자동화 스크립트, 프로젝트 관리

[최근 작성된 주제 (중복 금지)]
{recent_list}

[규칙]
1. 위 최근 주제와 겹치지 않는 새로운 주제를 제안하세요
2. 최신 트렌드를 반영하되, 년도(2024년, 2025년 등)나 시간 표현(오늘, 최근, today, 현재 등)은 절대 넣지 마세요
3. 한국 개발자가 관심 가질 만한 실용적인 주제
4. 주제만 한 줄로 출력하세요 (설명, 번호, 기호 없이)"""

    # 최대 3회 시도하여 유사하지 않은 주제 생성
    for topic_attempt in range(3):
        raw = call_gemini_api_with_fallback(api_key, prompt)
        topic = raw.strip().split('\n')[0].strip()
        topic = topic.lstrip('-·•0123456789. ').strip()
        topic = topic.replace('"', '').replace("'", "").strip()

        if len(topic) < 5 or len(topic) > 100:
            raise Exception(f"생성된 주제가 유효하지 않음: '{topic}'")

        # 기존 주제와 유사도 검사
        if not is_similar_topic(topic, recent_topics):
            return category, topic

        print(f"   ⚠️ 유사한 주제 감지, 재생성 중... ({topic_attempt+1}/3)")

    # 3회 시도 후에도 유사하면 그냥 사용
    print(f"   ℹ️ 유사도 검사 통과 못했지만 사용합니다: {topic}")
    return category, topic


def pick_topic(api_key=""):
    """주제 선택: Gemini 자동 생성 → 실패 시 하드코딩 풀에서 선택"""
    if api_key and api_key != "여기에_GEMINI_API_키":
        try:
            print("🧠 Gemini로 새로운 주제 생성 중...")
            category, topic = generate_topic_with_gemini(api_key)
            print(f"   ✅ AI 생성 주제: [{category}] {topic}")
            return category, topic
        except Exception as e:
            print(f"   ⚠️ 주제 생성 실패: {e}")
            print(f"   📋 하드코딩 주제 풀에서 선택합니다.")

    return pick_topic_from_pool()


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
    """Pixabay에서 주제별 키워드로 이미지 검색"""
    result = {"thumbnail": None, "files": [], "images_html": [], "image_map": {}}

    if pixabay_key:
        search_query = image_keywords or IMAGE_KEYWORDS.get(category, "programming coding")
        print(f"🖼️ Pixabay 이미지 검색 중: {search_query}")

        images = search_pixabay_images(pixabay_key, search_query, count=3)

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
                        f'<img src="{img_url}" alt="{topic} 관련 이미지 {i+1}" '
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
# Gemini API (모델 폴백 체인 + 429 재시도)
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
                wait = (attempt + 1) * 10  # 10초, 20초, 30초
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
    """Gemini API 키 + 모델 폴백 체인
    키1 → (2.5→2.0→1.5) → 키2 → (2.5→2.0→1.5) → ...
    """
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


def generate_toc(html_content):
    """HTML 본문에서 h2/h3 태그를 파싱하여 목차(Table of Contents) HTML 생성"""
    headings = re.findall(r'<(h[23])[^>]*>(.*?)</\1>', html_content, re.IGNORECASE | re.DOTALL)
    if len(headings) < 2:
        return ""

    toc_items = []
    for i, (tag, text) in enumerate(headings):
        # HTML 태그 제거하여 순수 텍스트 추출
        clean_text = re.sub(r'<[^>]+>', '', text).strip()
        anchor_id = f"toc-{i}"
        indent = "margin-left:20px;" if tag.lower() == "h3" else ""
        toc_items.append(
            f'<li style="{indent}"><a href="#{anchor_id}" style="text-decoration:none;color:#333;">{clean_text}</a></li>'
        )

    toc_html = (
        '<div style="background:#f8f9fa;border:1px solid #e1e4e8;border-radius:8px;padding:20px;margin:20px 0;">'
        '<p style="font-weight:bold;font-size:18px;margin-bottom:10px;">📑 목차</p>'
        f'<ul style="list-style:none;padding-left:0;margin:0;">{"".join(toc_items)}</ul>'
        '</div>'
    )

    # 본문의 h2/h3에 id 속성 추가
    counter = [0]
    def add_id(match):
        tag = match.group(1)
        attrs = match.group(2) or ""
        content = match.group(3)
        anchor_id = f"toc-{counter[0]}"
        counter[0] += 1
        return f'<{tag}{attrs} id="{anchor_id}">{content}</{tag}>'

    html_content = re.sub(r'<(h[23])([^>]*)>(.*?)</\1>', add_id, html_content, flags=re.IGNORECASE | re.DOTALL)

    return toc_html, html_content


def get_related_posts(current_topic, current_category, max_count=3):
    """post_history.json에서 관련 글 목록을 가져와 추천 섹션 HTML 생성"""
    history = load_history()
    post_log = history.get("post_log", [])
    if not post_log:
        return ""

    # 같은 카테고리 글 우선, 최근 글에서 선택
    same_category = [p for p in post_log if p.get("category") == current_category and p.get("title") != current_topic]
    other_posts = [p for p in post_log if p.get("category") != current_category and p.get("title") != current_topic]

    # 같은 카테고리에서 최대 2개 + 다른 카테고리에서 나머지
    candidates = same_category[-5:] + other_posts[-5:]
    if not candidates:
        return ""

    random.shuffle(candidates)
    selected = candidates[:max_count]

    items_html = ""
    for post in selected:
        title = post.get("title", "")
        category = post.get("category", "")
        url = post.get("url", "")
        if url:
            items_html += (
                f'<li style="margin-bottom:8px;">'
                f'<span style="color:#666;font-size:13px;">[{category}]</span> '
                f'<a href="{url}" style="color:#1a73e8;text-decoration:none;">{title}</a></li>'
            )
        else:
            items_html += (
                f'<li style="margin-bottom:8px;">'
                f'<span style="color:#666;font-size:13px;">[{category}]</span> '
                f'{title}</li>'
            )

    return (
        '<div style="background:#fff8e1;border-left:4px solid #ffc107;padding:15px 20px;margin:30px 0;border-radius:4px;">'
        '<p style="font-weight:bold;font-size:16px;margin-bottom:10px;">📌 함께 읽으면 좋은 글</p>'
        f'<ul style="padding-left:20px;margin:0;">{items_html}</ul>'
        '</div>'
    )


def insert_inline_internal_links(html_content, current_title, current_category, max_links=2):
    """본문 중간에 자연스러운 내부 링크를 삽입 (SEO 강화)
    관련 글의 키워드가 본문에 등장하면 해당 위치에 링크 삽입"""
    history = load_history()
    post_log = history.get("post_log", [])
    if not post_log:
        return html_content

    # URL이 있는 글만 필터 (현재 글 제외)
    linkable = [p for p in post_log if p.get("url") and p.get("title") != current_title]
    if not linkable:
        return html_content

    # 같은 카테고리 글 우선
    same_cat = [p for p in linkable if p.get("category") == current_category]
    other_cat = [p for p in linkable if p.get("category") != current_category]
    candidates = same_cat[-10:] + other_cat[-5:]

    links_inserted = 0
    for post in reversed(candidates):
        if links_inserted >= max_links:
            break

        title = post.get("title", "")
        url = post.get("url", "")
        if not title or not url:
            continue

        # 제목에서 핵심 키워드 추출 (3글자 이상 단어)
        keywords = [w for w in title.replace(",", " ").replace(":", " ").split() if len(w) >= 3]
        if not keywords:
            continue

        for keyword in keywords[:3]:
            # 이미 링크가 된 텍스트 안에 있는지 확인 (중복 링크 방지)
            if f'>{keyword}<' not in html_content and keyword in html_content:
                # <p> 태그 안에서만 치환 (h2, h3 등은 건드리지 않음)
                pattern = re.compile(
                    r'(<p[^>]*>)(.*?)(' + re.escape(keyword) + r')(.*?)(</p>)',
                    re.IGNORECASE | re.DOTALL
                )
                match = pattern.search(html_content)
                if match:
                    link_html = f'<a href="{url}" style="color:#1a73e8;text-decoration:underline;" title="{title}">{keyword}</a>'
                    # 첫 번째 매치만 치환
                    full_match = match.group(0)
                    replaced = match.group(1) + match.group(2) + link_html + match.group(4) + match.group(5)
                    html_content = html_content.replace(full_match, replaced, 1)
                    links_inserted += 1
                    break

    if links_inserted > 0:
        print(f"   🔗 본문 내부 링크 {links_inserted}개 삽입")
    return html_content


def generate_post_with_gemini(api_key, category, topic, max_attempts=2):
    prompt = f"""당신은 한국어 IT/개발 블로그 SEO 전문 작성자입니다.

아래 조건에 맞는 블로그 글을 작성해 주세요.

[카테고리] {category}
[주제] {topic}

[작성 규칙]
1. 반드시 HTML 태그로 포맷팅하세요 (티스토리 블로그용)
2. 제목은 별도로 첫 줄에 순수 텍스트로 출력하세요 (HTML 태그 없이)
3. ⚠️ SEO 제목 규칙: 제목에 검색 유입이 높은 핵심 키워드를 포함하되, 년도(2024년, 2025년 등)는 절대 넣지 마세요. 좋은 예: "풀스택 vs 전문분야: 개발자 커리어 어떤 길을 선택할까", "Docker 입문 가이드: 컨테이너 기초부터 배포까지", "React vs Vue 비교 분석: 프론트엔드 프레임워크 선택법"
4. 제목 다음 줄에 이미지 검색 키워드를 영어로 3개 출력하세요 (쉼표 구분)
5. 셋째 줄에 메타 디스크립션을 한 줄로 출력하세요 (150자 이내, 검색 결과에 노출될 요약문)
6. 넷째 줄부터 본문을 HTML로 작성하세요

[본문 구조 규칙]
1. ⚠️ 본문은 3000자~5000자 분량으로 충분히 상세하게 작성하세요
2. H2 소제목을 5~7개 사용하여 큰 구조를 잡으세요
3. 각 H2 아래에 필요하면 H3 소제목을 1~2개 추가하세요
4. 핵심 키워드는 <b> 태그로 강조
5. 비교 내용이 있으면 <table> 사용 (스타일 포함)
6. 테이블 스타일: style="border-collapse:collapse;width:100%", th에 background:#f4f4f4, td/th에 border:1px solid #ddd;padding:8px
7. 코드 예시가 있으면 <pre><code> 태그 사용
8. 각 섹션마다 실용적이고 구체적인 예시, 수치, 비교를 포함하세요
9. 도입부에 독자의 관심을 끄는 질문이나 상황 제시
10. 마지막에 핵심 요약 + 댓글 유도 문구 포함
11. ⚠️ 반드시 글을 끝까지 완성하세요. 모든 HTML 태그를 정상적으로 닫고, 마무리 문단까지 작성하세요.
12. ⚠️ 본문에 년도(2024년, 2025년 등), 시간 표현(오늘, 최근, today, 현재, 요즘 등)을 절대 사용하지 마세요. 시간에 구애받지 않는 에버그린 콘텐츠로 작성하세요.

[출력 형식]
첫 줄: 글 제목 (순수 텍스트, SEO 키워드 포함)
둘째 줄: 이미지 검색 키워드 (영어, 쉼표 구분)
셋째 줄: 메타 디스크립션 (한국어, 150자 이내)
넷째 줄부터: 본문 HTML
"""

    for attempt in range(max_attempts):
        raw_response = call_gemini_api_with_fallback(api_key, prompt)
        lines = raw_response.strip().split('\n')

        title = lines[0].strip().replace('#', '').replace('<h1>', '').replace('</h1>', '')
        title = title.replace('```html', '').replace('```', '').strip()

        image_keywords = ""
        meta_description = ""
        content_start = 1

        # 둘째 줄: 이미지 키워드
        if len(lines) > 1:
            second_line = lines[1].strip()
            if not second_line.startswith('<'):
                image_keywords = second_line.replace('```html', '').replace('```', '').strip()
                content_start = 2

        # 셋째 줄: 메타 디스크립션
        if len(lines) > content_start:
            meta_line = lines[content_start].strip()
            if not meta_line.startswith('<') and len(meta_line) > 10:
                meta_description = meta_line.replace('```html', '').replace('```', '').strip()
                content_start += 1

        content = '\n'.join(lines[content_start:]).strip()
        content = content.replace('```html', '').replace('```', '').strip()

        # 목차(TOC) 생성 & 삽입
        toc_result = generate_toc(content)
        if toc_result:
            toc_html, content = toc_result
            # 첫 번째 <h2> 앞에 목차 삽입
            first_h2 = re.search(r'<h2', content, re.IGNORECASE)
            if first_h2:
                content = content[:first_h2.start()] + toc_html + "\n" + content[first_h2.start():]
            else:
                content = toc_html + "\n" + content

        # 본문 중간 내부 링크 삽입 (SEO 강화)
        content = insert_inline_internal_links(content, title, category)

        # 관련 글 추천 섹션 추가
        related_html = get_related_posts(title, category)
        if related_html:
            content = content + "\n" + related_html

        # 하단 CTA (댓글/공감 유도)
        cta_html = (
            '<div style="background:#e8f5e9;border-left:4px solid #4caf50;padding:15px 20px;'
            'margin:30px 0;border-radius:4px;text-align:center;">'
            '<p style="font-size:15px;margin:0;color:#2e7d32;">'
            '이 글이 도움이 되셨다면 <b>공감(♥)</b>과 <b>댓글</b>로 응원해 주세요!<br>'
            '<span style="font-size:13px;color:#666;">궁금한 점이나 다루었으면 하는 주제가 있다면 댓글로 남겨주세요.</span>'
            '</p></div>'
        )
        content = content + "\n" + cta_html

        # 품질 검증: 본문 텍스트 길이 (HTML 태그 제외)
        plain_text = re.sub(r'<[^>]+>', '', content)
        text_length = len(plain_text.strip())

        # H2 태그 개수 검증
        h2_count = len(re.findall(r'<h2', content, re.IGNORECASE))

        quality_ok = True
        if text_length < 1500:
            print(f"   ⚠️ 본문이 너무 짧음: {text_length}자 (최소 1500자)")
            quality_ok = False
        if h2_count < 3:
            print(f"   ⚠️ H2 소제목 부족: {h2_count}개 (최소 3개)")
            quality_ok = False

        # 잘림 감지: 열린 태그가 닫히지 않았는지 확인
        is_truncated = is_html_truncated(content)
        if is_truncated:
            print(f"   ⚠️ HTML 잘림 감지")
            quality_ok = False

        if quality_ok:
            print(f"   ✅ 품질 검증 통과 (본문 {text_length}자, H2 {h2_count}개)")
            return {"title": title, "content": content, "image_keywords": image_keywords, "meta_description": meta_description}

        if attempt < max_attempts - 1:
            print(f"   🔄 품질 미달 — 재생성 시도 ({attempt+2}/{max_attempts})")
        else:
            print(f"   🔧 최대 시도 횟수 도달 — 현재 글 사용 (본문 {text_length}자)")
            if is_truncated:
                content = fix_truncated_html(content)

    return {"title": title, "content": content, "image_keywords": image_keywords, "meta_description": meta_description}


def is_html_truncated(html):
    """HTML이 잘렸는지 감지 (열린 태그가 닫히지 않은 경우)"""
    block_tags = ['p', 'h2', 'h3', 'blockquote', 'table', 'tr', 'td', 'th',
                  'thead', 'tbody', 'ul', 'ol', 'li', 'div', 'code', 'pre']

    open_tags = []
    for match in re.finditer(r'<(/?)(\w+)[^>]*>', html):
        is_close = match.group(1) == '/'
        tag = match.group(2).lower()
        if tag not in block_tags:
            continue
        if is_close:
            if open_tags and open_tags[-1] == tag:
                open_tags.pop()
        else:
            open_tags.append(tag)

    return len(open_tags) > 0


def fix_truncated_html(html):
    """토큰 제한으로 잘린 HTML의 열린 태그를 닫아서 복구"""
    block_tags = ['p', 'h2', 'h3', 'blockquote', 'table', 'tr', 'td', 'th',
                  'thead', 'tbody', 'ul', 'ol', 'li', 'div', 'code', 'pre']

    open_tags = []
    for match in re.finditer(r'<(/?)(\w+)[^>]*>', html):
        is_close = match.group(1) == '/'
        tag = match.group(2).lower()
        if tag not in block_tags:
            continue
        if is_close:
            if open_tags and open_tags[-1] == tag:
                open_tags.pop()
        else:
            open_tags.append(tag)

    if open_tags:
        print(f"   🔧 잘린 HTML 감지 — 닫히지 않은 태그 {len(open_tags)}개 복구: {open_tags}")
        for tag in reversed(open_tags):
            html += f'</{tag}>'

    return html



# ============================================================
# 메인 함수
# ============================================================
def get_daily_post():
    """오늘의 블로그 글 생성 (Gemini + 스마트 이미지)"""
    config = load_config()
    api_key = config.get("gemini_api_key", "")
    pixabay_key = config.get("pixabay_api_key", "")

    category, topic = pick_topic(api_key)
    print(f"📌 선택된 카테고리: {category}")
    print(f"📌 선택된 주제: {topic}")

    post = None

    if api_key and api_key != "여기에_GEMINI_API_키":
        try:
            print("🤖 Gemini API로 글 생성 중 (모델 폴백 체인 활성화)...")
            post = generate_post_with_gemini(api_key, category, topic)
            print(f"✅ 생성 완료: {post['title']} ({len(post['content'])}자)")
        except Exception as e:
            print(f"⚠️ 모든 Gemini 모델 실패: {e}")
            print("🚫 AI 생성 불가 — 이번 실행은 발행을 건너뜁니다.")
            return None
    else:
        print("⚠️ Gemini API 키 미설정 — 발행을 건너뜁니다.")
        return None

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
        "url": "",
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
        "meta_description": post.get("meta_description", ""),
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
