"""
주제 생성 모듈
- Gemini로 주제 자동 생성
- 유사 주제 필터링
- 카테고리 균등 분배
- 하드코딩 풀 폴백
"""

import random
import datetime

from config import CATEGORIES, load_history, save_history
from gemini_api import call_gemini_api_with_fallback


def is_similar_topic(new_topic, existing_topics, threshold=0.5):
    """새 주제가 기존 주제와 유사한지 검사 (키워드 겹침 비율)"""
    new_words = set(new_topic.lower().replace(",", " ").replace(":", " ").split())
    stopwords = {"vs", "및", "의", "와", "을", "를", "이", "가", "에", "는", "은",
                 "로", "으로", "위한", "대한", "어떤", "가이드", "정리", "비교", "분석",
                 "완벽", "실전", "핵심"}
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

    recent_posts = post_log[-30:] if len(post_log) > 30 else post_log
    category_counts = {cat: 0 for cat in categories}
    for post in recent_posts:
        cat = post.get("category", "")
        if cat in category_counts:
            category_counts[cat] += 1

    min_count = min(category_counts.values())
    least_used = [cat for cat, count in category_counts.items() if count == min_count]
    return random.choice(least_used)


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


def generate_topic_with_gemini(api_key):
    """Gemini API로 새로운 블로그 주제 자동 생성"""
    history = load_history()
    posted = history.get("posted_topics", [])
    recent_topics = posted[-30:] if len(posted) > 30 else posted

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

        if not is_similar_topic(topic, recent_topics):
            return category, topic

        print(f"   ⚠️ 유사한 주제 감지, 재생성 중... ({topic_attempt+1}/3)")

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
