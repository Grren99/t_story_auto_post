"""
주제 생성 모듈
- Gemini로 주제 후보 다중 생성 (세부주제 × 앵글 매트릭스로 다양성 확보)
- 전체 발행 이력 기반 중복 차단 (키워드 사전 필터 + 임베딩 의미 유사도)
- 연재(후속/심화) 모드: 과거 글의 업그레이드 글 작성
- 카테고리 균등 분배
- 하드코딩 풀 폴백
"""

import random
import datetime

from config import (
    CATEGORIES, ANGLES,
    load_config, load_history,
    load_embeddings,
    load_taxonomy, save_taxonomy, get_effective_subtopics,
    get_all_categories,
)
from gemini_api import call_gemini_api_with_fallback, get_embedding_with_fallback

# 키워드 겹침 사전 필터 임계값 (저렴한 1차 검사)
KEYWORD_SIM_THRESHOLD = 0.6
# 임베딩 코사인 유사도 임계값 — 이상이면 중복 판정 (config.json에서 조정 가능)
EMBEDDING_SIM_THRESHOLD = 0.85
# 연재(후속/심화) 글 기본 비율
SERIES_RATIO_DEFAULT = 0.2
# 와일드카드(카테고리 무관 자유 주제) 기본 비율
WILDCARD_RATIO_DEFAULT = 0.1
# 한 번에 생성할 주제 후보 수
CANDIDATE_COUNT = 10
# 후보 중 임베딩 검사할 최대 개수 (API 호출 제한)
MAX_EMBED_CHECKS = 6
# 발행 N회마다 세부주제 자동 확장
TAXONOMY_EXPAND_EVERY = 15
# 카테고리당 세부주제 상한 (시드 + 학습 합산)
MAX_SUBTOPICS_PER_CATEGORY = 30
# 확장 주기 도달 시 신규 카테고리를 제안할 확률 (나머지는 세부주제 확장)
NEW_CATEGORY_PROB = 0.3
# 학습으로 추가될 수 있는 신규 카테고리 상한
MAX_LEARNED_CATEGORIES = 8

STOPWORDS = {"vs", "및", "의", "와", "을", "를", "이", "가", "에", "는", "은",
             "로", "으로", "위한", "대한", "어떤", "가이드", "정리", "비교", "분석",
             "완벽", "실전", "핵심", "방법", "활용", "전략", "총정리", "모음",
             "입문", "기초", "이해하기", "알아보기", "하는", "해야", "할"}

# 조사 절단용 접미사 (긴 것 우선)
_PARTICLES = ("으로", "에서", "와의", "과의", "까지", "부터", "처럼",
              "는", "은", "이", "가", "을", "를", "에", "의", "로", "와", "과", "도")


def _topic_words(topic):
    """주제 문자열 → 정규화된 키워드 집합 (조사 제거, 불용어 제외)"""
    cleaned = topic.lower()
    for ch in ",:()[]/'\"?!":
        cleaned = cleaned.replace(ch, " ")

    words = set()
    for w in cleaned.split():
        for suffix in _PARTICLES:
            if len(w) > len(suffix) + 1 and w.endswith(suffix):
                w = w[:-len(suffix)]
                break
        if w and w not in STOPWORDS:
            words.add(w)
    return words


def is_similar_topic(new_topic, existing_topics, threshold=KEYWORD_SIM_THRESHOLD):
    """키워드 겹침 비율 기반 유사 검사 (전체 이력 대상 1차 필터)"""
    new_words = _topic_words(new_topic)
    if len(new_words) < 2:
        return False

    for existing in existing_topics:
        existing_words = _topic_words(existing)
        if len(existing_words) < 2:
            continue
        overlap = len(new_words & existing_words)
        similarity = overlap / min(len(new_words), len(existing_words))
        if similarity >= threshold:
            return True
    return False


def _max_embedding_similarity(vec, embeddings):
    """저장된 전체 이력 임베딩과의 최대 코사인 유사도 (벡터는 정규화 가정 → 내적)"""
    best_sim, best_topic = 0.0, None
    for topic, stored in embeddings.items():
        if len(stored) != len(vec):
            continue  # 차원이 다른 과거 벡터는 비교 불가
        sim = sum(a * b for a, b in zip(vec, stored))
        if sim > best_sim:
            best_sim, best_topic = sim, topic
    return best_sim, best_topic


def _embedding_threshold():
    try:
        return float(load_config().get("embedding_similarity_threshold", EMBEDDING_SIM_THRESHOLD))
    except Exception:
        return EMBEDDING_SIM_THRESHOLD


def pick_balanced_category(history, exclude=None):
    """최근 발행 이력 기반 카테고리 균등 분배 - 덜 쓴 카테고리 우선 선택"""
    exclude = exclude or []
    all_cats = get_all_categories()
    categories = [c for c in all_cats if c not in exclude]
    if not categories:
        categories = all_cats
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

    # 풀 소진 시에도 발행 이력은 절대 초기화하지 않음 (중복 방지 기억 유지)
    if not all_topics:
        for category, topics in CATEGORIES.items():
            for topic in topics:
                all_topics.append({"category": category, "topic": topic})

    today_seed = datetime.date.today().toordinal()
    random.seed(today_seed)
    chosen = random.choice(all_topics)
    random.seed()

    return {"category": chosen["category"], "topic": chosen["topic"],
            "embedding": None, "angle": None, "series_parent": None}


def _parse_topic_lines(raw):
    """Gemini 응답 → 주제 후보 리스트"""
    topics = []
    for line in raw.strip().split('\n'):
        t = line.strip().lstrip('-·•*0123456789. ').strip()
        t = t.replace('"', '').replace("'", "").strip()
        if 5 <= len(t) <= 100 and t not in topics:
            topics.append(t)
    return topics


def generate_topic_candidates(api_key, category, history):
    """세부주제 × 앵글 조합으로 주제 후보를 한 번에 여러 개 생성"""
    posted = history.get("posted_topics", [])
    post_log = history.get("post_log", [])

    # 프롬프트 금지 목록: 같은 카테고리 전체 + 전체 최근 50개 (나머지는 임베딩 검사가 차단)
    same_cat = [p.get("topic", "") for p in post_log if p.get("category") == category]
    ban_list = list(dict.fromkeys(same_cat[-150:] + posted[-50:]))
    ban_text = "\n".join(f"- {t}" for t in ban_list) if ban_list else "(없음)"

    subtopic_pool = get_effective_subtopics(category)
    subtopics = random.sample(subtopic_pool, k=min(3, len(subtopic_pool))) if subtopic_pool else []
    angle = random.choice(ANGLES)

    subtopic_text = ", ".join(subtopics) if subtopics else "자유"

    prompt = f"""당신은 한국어 IT/개발 블로그 주제를 기획하는 전문가입니다.

아래 조건에 맞는 블로그 글 주제를 {CANDIDATE_COUNT}개 제안해 주세요.

[카테고리] {category}
[이번에 다룰 세부 영역] {subtopic_text}
[글의 관점/형식] {angle}

[이미 작성된 주제 — 같거나 비슷한 주제 절대 금지]
{ban_text}

[규칙]
1. {CANDIDATE_COUNT}개 주제는 서로 다른 기술/도구/개념을 다뤄야 합니다 (같은 기술의 변형 금지)
2. 위 금지 목록과 의미가 겹치는 주제를 제안하지 마세요. 유명하고 뻔한 주제보다 덜 다뤄졌지만 검색 수요가 있는 구체적인 주제를 우선하세요
3. [글의 관점/형식]을 주제에 반영하세요
4. 최신 트렌드를 반영하되, 년도(2024년, 2025년 등)나 시간 표현(오늘, 최근, today, 현재 등)은 절대 넣지 마세요
5. 한국 개발자가 관심 가질 만한 실용적인 주제
6. 한 줄에 주제 1개씩만 출력하세요 (설명, 번호, 기호 없이)"""

    raw = call_gemini_api_with_fallback(api_key, prompt)
    return _parse_topic_lines(raw), angle


def _select_novel_topic(api_key, candidates, posted, embeddings, threshold):
    """후보 중 전체 이력과 가장 겹치지 않는 주제 선택.
    반환: (topic, embedding) 또는 (None, None)"""
    # 1차: 키워드 겹침 필터 (전체 이력 대상, API 비용 없음)
    survivors = [t for t in candidates if not is_similar_topic(t, posted)]
    if not survivors:
        return None, None

    # 2차: 임베딩 의미 유사도 — 가장 참신한(최대 유사도가 낮은) 주제 선택
    best = None  # (sim, topic, vec)
    for topic in survivors[:MAX_EMBED_CHECKS]:
        vec = get_embedding_with_fallback(api_key, topic)
        if vec is None:
            # 임베딩 불가 → 키워드 검사만 통과한 첫 후보 사용
            print("   ℹ️ 임베딩 사용 불가 — 키워드 검사만으로 선택합니다.")
            return topic, None

        sim, similar_to = _max_embedding_similarity(vec, embeddings)
        if sim >= threshold:
            print(f"   ⚠️ 의미 중복 제외: '{topic}' (유사도 {sim:.2f} ↔ '{similar_to}')")
            continue
        if best is None or sim < best[0]:
            best = (sim, topic, vec)

    if best:
        print(f"   ✅ 참신도 검사 통과 (최대 유사도 {best[0]:.2f})")
        return best[1], best[2]
    return None, None


def generate_topic_for_category(api_key, category, history):
    """카테고리 하나에 대해 후보 생성 → 중복 필터 → 선택. 실패 시 None"""
    posted = history.get("posted_topics", [])
    embeddings = load_embeddings()
    threshold = _embedding_threshold()

    candidates, angle = generate_topic_candidates(api_key, category, history)
    if not candidates:
        return None

    topic, vec = _select_novel_topic(api_key, candidates, posted, embeddings, threshold)
    if topic is None:
        print(f"   ⚠️ [{category}] 후보 {len(candidates)}개 전부 기존 글과 중복 — 다른 카테고리로 전환")
        return None

    return {"category": category, "topic": topic,
            "embedding": vec, "angle": angle, "series_parent": None}


# ============================================================
# 와일드카드 모드 — 카테고리 매트릭스를 벗어난 자유 주제
# ============================================================
def generate_wildcard_topic(api_key, history):
    """카테고리 제약 없이 니치/교차 영역의 자유 주제 생성. 실패 시 None"""
    posted = history.get("posted_topics", [])
    recent = posted[-50:]
    ban_text = "\n".join(f"- {t}" for t in recent) if recent else "(없음)"
    category_list = ", ".join(get_all_categories())

    prompt = f"""당신은 한국어 IT/개발 블로그 주제를 기획하는 전문가입니다.

카테고리 제약 없이, 남들이 잘 다루지 않는 참신한 블로그 주제를 {CANDIDATE_COUNT}개 제안해 주세요.

[방향]
- 두 기술 영역의 교차점 (예: 게임 개발 기법을 웹에 적용, 임베디드 관점의 최적화)
- 니치하지만 검색 수요가 있는 주제 (예: 특정 에러 해결, 레거시 기술 마이그레이션, 개발 습관)
- 개발 문화/역사/사고방식처럼 기술 외적이지만 개발자가 좋아할 주제

[이미 작성된 주제 — 겹치면 안 됨]
{ban_text}

[규칙]
1. {CANDIDATE_COUNT}개는 서로 완전히 다른 영역을 다뤄야 합니다
2. 년도나 시간 표현은 절대 넣지 마세요
3. 각 줄을 "주제 | 카테고리" 형식으로 출력하세요. 카테고리는 다음 중 가장 가까운 것: {category_list}
4. 설명, 번호, 기호 없이 한 줄에 하나씩만 출력하세요"""

    raw = call_gemini_api_with_fallback(api_key, prompt)

    candidates = {}  # topic → category
    for line in raw.strip().split('\n'):
        line = line.strip().lstrip('-·•*0123456789. ').strip()
        if '|' not in line:
            continue
        topic, _, cat = line.rpartition('|')
        topic = topic.replace('"', '').replace("'", "").strip()
        cat = cat.strip()
        if 5 <= len(topic) <= 100 and topic not in candidates:
            candidates[topic] = cat if cat in get_all_categories() else None

    if not candidates:
        return None

    embeddings = load_embeddings()
    topic, vec = _select_novel_topic(api_key, list(candidates.keys()), posted,
                                     embeddings, _embedding_threshold())
    if topic is None:
        return None

    category = candidates.get(topic) or pick_balanced_category(history)
    print(f"   🎲 와일드카드 주제 선택 (카테고리: {category})")
    return {"category": category, "topic": topic, "embedding": vec,
            "angle": "와일드카드 자유 주제", "series_parent": None}


# ============================================================
# 세부주제/카테고리 자동 확장 — 발행이 쌓일수록 주제 공간이 스스로 넓어짐
# ============================================================
def propose_new_category(api_key):
    """Gemini에게 완전히 새로운 카테고리 제안 요청.
    반환: (이름, {"image_keyword", "subtopics"}) 또는 None"""
    existing = get_all_categories()
    # 기존 세부영역까지 제시해야 의미가 겹치는 카테고리(예: 데브옵스↔클라우드 인프라)를 막을 수 있음
    existing_text = "\n".join(
        f"- {c}: {', '.join(get_effective_subtopics(c)[:8])}" for c in existing
    )
    all_existing_subs = [s for c in existing for s in get_effective_subtopics(c)]

    prompt = f"""한국어 IT/개발 블로그에 새로 추가할 카테고리를 1개 제안해 주세요.

[현재 카테고리와 세부영역 — 이름은 물론 다루는 영역 자체가 겹치면 안 됨]
{existing_text}

[규칙]
1. 위 카테고리들의 세부영역과도 겹치지 않는 완전히 새로운 영역이어야 합니다
2. 한국 개발자/IT 종사자에게 꾸준한 검색 수요가 있는 영역이어야 합니다
3. 카테고리 이름은 2~12자의 간결한 한국어로 지으세요
4. 아래 형식으로 정확히 한 줄만 출력하세요 (설명 없이):
카테고리명 | 영어 이미지 검색 키워드 2~3단어 (쉼표/세미콜론 없이) | 세부영역1; 세부영역2; 세부영역3; 세부영역4; 세부영역5"""

    raw = call_gemini_api_with_fallback(api_key, prompt)

    for line in raw.strip().split('\n'):
        parts = [p.strip() for p in line.strip().split('|')]
        if len(parts) != 3:
            continue
        name, image_keyword, subs_raw = parts
        name = name.replace('"', '').replace("'", "").strip()
        image_keyword = image_keyword.replace(';', ' ').replace(',', ' ')
        image_keyword = " ".join(image_keyword.split())
        subtopics = [s.strip() for s in subs_raw.split(';') if s.strip()]
        if not (2 <= len(name) <= 20) or len(subtopics) < 3:
            continue
        if name in existing or is_similar_topic(name, existing, threshold=0.5):
            continue
        # 제안된 세부영역의 절반 이상이 기존 세부영역과 겹치면 사실상 중복 카테고리
        overlap = sum(1 for s in subtopics
                      if is_similar_topic(s, all_existing_subs, threshold=0.5))
        if overlap * 2 >= len(subtopics):
            print(f"   ⚠️ 신규 카테고리 '{name}' 거부 — 기존 세부영역과 {overlap}/{len(subtopics)} 겹침")
            continue
        return name, {"image_keyword": image_keyword, "subtopics": subtopics}
    return None


def maybe_expand_taxonomy(api_key, history):
    """발행 N회마다 주제 공간 확장:
    - 일정 확률로 완전히 새로운 카테고리 추가 (상한까지)
    - 그 외에는 세부주제가 가장 적은 카테고리에 새 세부 영역 추가"""
    taxonomy = load_taxonomy()
    post_count = len(history.get("post_log", []))
    if post_count - taxonomy.get("expanded_at_post_count", 0) < TAXONOMY_EXPAND_EVERY:
        return
    taxonomy["expanded_at_post_count"] = post_count

    # 신규 카테고리 제안 (상한 미달 시 확률적으로)
    learned_cats = taxonomy.get("learned_categories", {})
    if len(learned_cats) < MAX_LEARNED_CATEGORIES and random.random() < NEW_CATEGORY_PROB:
        try:
            result = propose_new_category(api_key)
            if result:
                name, data = result
                taxonomy.setdefault("learned_categories", {})[name] = data
                save_taxonomy(taxonomy)
                print(f"   🆕 신규 카테고리 학습: '{name}' (세부영역 {len(data['subtopics'])}개)"
                      f" — 다음 발행 시 티스토리에 자동 생성됩니다")
                return
        except Exception as e:
            print(f"   ⚠️ 신규 카테고리 제안 실패 — 세부주제 확장으로 대체: {e}")

    # 세부주제가 적은 카테고리 우선, 상한 도달 카테고리는 제외
    expandable = [c for c in get_all_categories()
                  if len(get_effective_subtopics(c)) < MAX_SUBTOPICS_PER_CATEGORY]
    if not expandable:
        save_taxonomy(taxonomy)
        return

    category = min(expandable, key=lambda c: len(get_effective_subtopics(c)))
    existing = get_effective_subtopics(category)
    existing_text = "\n".join(f"- {s}" for s in existing)

    prompt = f"""한국어 IT/개발 블로그의 "{category}" 카테고리에서 다룰 수 있는 새로운 세부 영역을 3개 제안해 주세요.

[이미 있는 세부 영역 — 겹치면 안 됨]
{existing_text}

[규칙]
1. 글 제목이 아니라 "세부 영역"(주제 분류)을 제안하세요 (예: "서버리스 아키텍처", "모바일 앱 보안")
2. 기존 세부 영역과 겹치지 않는, 아직 다루지 않은 영역이어야 합니다
3. 한국 개발자에게 검색 수요가 있는 영역이어야 합니다
4. 한 줄에 1개씩만 출력하세요 (설명, 번호, 기호 없이)"""

    try:
        raw = call_gemini_api_with_fallback(api_key, prompt)
        new_subs = [s for s in _parse_topic_lines(raw)
                    if not is_similar_topic(s, existing, threshold=0.5)][:3]
        if new_subs:
            taxonomy.setdefault("learned_subtopics", {}).setdefault(category, []).extend(new_subs)
            print(f"   🌱 세부주제 확장: [{category}] + {new_subs}")
    except Exception as e:
        print(f"   ⚠️ 세부주제 확장 실패 — 이번 주기는 건너뜁니다: {e}")

    save_taxonomy(taxonomy)


# ============================================================
# 연재(후속/심화) 모드 — 과거 글을 업그레이드하는 글 작성
# ============================================================
def pick_series_topic(api_key, history):
    """과거 발행 글 중 하나를 골라 후속/심화편 주제 생성. 실패 시 None"""
    post_log = history.get("post_log", [])
    posted = history.get("posted_topics", [])

    # URL이 있는 글만 연재 가능 (이전 글 링크 필수), 이미 후속편이 있는 글 제외
    has_sequel = {p.get("series_parent") for p in post_log if p.get("series_parent")}
    parents = [p for p in post_log
               if p.get("url") and p.get("title") and p.get("title") not in has_sequel]
    if not parents:
        return None

    parent = random.choice(parents)

    prompt = f"""당신은 한국어 IT/개발 블로그를 연재로 기획하는 전문가입니다.

아래 글의 "다음 단계" 후속편 주제를 5개 제안해 주세요.

[이전 글 제목] {parent['title']}
[이전 글 주제] {parent.get('topic', parent['title'])}

[규칙]
1. 이전 글을 읽은 독자가 다음 단계로 나아갈 수 있는 심화/실전/응용 주제여야 합니다
   (예: 입문 → 실전 적용 → 트러블슈팅 → 성능 최적화 → 대규모 운영)
2. 이전 글 내용의 단순 반복이 아니라 명확히 한 단계 발전된 내용이어야 합니다
3. 년도나 시간 표현은 절대 넣지 마세요
4. 한 줄에 주제 1개씩만 출력하세요 (설명, 번호, 기호 없이)"""

    raw = call_gemini_api_with_fallback(api_key, prompt)
    candidates = _parse_topic_lines(raw)
    if not candidates:
        return None

    embeddings = load_embeddings()
    topic, vec = _select_novel_topic(api_key, candidates, posted, embeddings, _embedding_threshold())
    if topic is None:
        return None

    category = parent.get("category", "")
    if category not in get_all_categories():
        category = pick_balanced_category(history)

    print(f"   📚 연재 모드: '{parent['title']}' 의 후속편")
    return {"category": category, "topic": topic, "embedding": vec, "angle": "연재 후속편",
            "series_parent": {"title": parent["title"], "url": parent["url"]}}


# ============================================================
# 메인 진입점
# ============================================================
def pick_topic(api_key=""):
    """주제 선택 → dict 반환
    {"category", "topic", "embedding", "angle", "series_parent"}
    1) 발행 N회마다 세부주제 자동 확장
    2) 일정 확률로 연재(후속편) 모드 / 와일드카드(자유 주제) 모드
    3) Gemini 후보 생성 + 전체 이력 중복 차단 (카테고리 3개까지 시도)
    4) 모두 실패 시 하드코딩 풀 폴백
    """
    if api_key and api_key != "여기에_GEMINI_API_키":
        history = load_history()

        # 세부주제 자동 확장 (주기 도달 시)
        try:
            maybe_expand_taxonomy(api_key, history)
        except Exception as e:
            print(f"   ⚠️ 세부주제 확장 중 오류: {e}")

        try:
            config = load_config()
            series_ratio = float(config.get("series_post_ratio", SERIES_RATIO_DEFAULT))
            wildcard_ratio = float(config.get("wildcard_post_ratio", WILDCARD_RATIO_DEFAULT))
        except Exception:
            series_ratio = SERIES_RATIO_DEFAULT
            wildcard_ratio = WILDCARD_RATIO_DEFAULT

        # 와일드카드 모드 (기본 10%, config.json의 wildcard_post_ratio로 조정)
        if random.random() < wildcard_ratio:
            try:
                print("🎲 와일드카드(자유 주제) 생성 시도 중...")
                result = generate_wildcard_topic(api_key, history)
                if result:
                    print(f"   ✅ 와일드카드 주제: [{result['category']}] {result['topic']}")
                    return result
                print("   ℹ️ 와일드카드 실패 — 일반 주제로 진행")
            except Exception as e:
                print(f"   ⚠️ 와일드카드 생성 실패: {e}")

        # 연재 모드 (기본 20%, config.json의 series_post_ratio로 조정)
        if random.random() < series_ratio:
            try:
                print("🔗 연재(후속편) 주제 생성 시도 중...")
                result = pick_series_topic(api_key, history)
                if result:
                    print(f"   ✅ 연재 주제: [{result['category']}] {result['topic']}")
                    return result
                print("   ℹ️ 연재 가능한 글 없음 — 일반 주제로 진행")
            except Exception as e:
                print(f"   ⚠️ 연재 주제 생성 실패: {e}")

        # 일반 모드: 중복이면 카테고리를 바꿔가며 최대 3회 시도
        tried = []
        for _ in range(3):
            category = pick_balanced_category(history, exclude=tried)
            tried.append(category)
            try:
                print(f"🧠 Gemini로 새로운 주제 생성 중... [카테고리: {category}]")
                result = generate_topic_for_category(api_key, category, history)
                if result:
                    print(f"   ✅ AI 생성 주제: [{result['category']}] {result['topic']}")
                    return result
            except Exception as e:
                print(f"   ⚠️ 주제 생성 실패: {e}")

        print("   📋 모든 시도 실패 — 하드코딩 주제 풀에서 선택합니다.")

    return pick_topic_from_pool()
