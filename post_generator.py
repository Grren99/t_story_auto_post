"""
블로그 글 생성 모듈
- Gemini로 글 본문 생성
- 품질 검증 (글자수, H2 개수, HTML 잘림)
- TOC, 내부 링크, 관련 글, Schema markup, CTA 삽입
"""

import json
import re
import random
import datetime

from config import (
    CATEGORIES, TISTORY_CATEGORY_MAP, WRITING_STYLES,
    TITLE_STYLES, TITLE_CLICHES, POST_FORMATS, PERSONAS, LENGTH_PROFILES,
    load_config, load_history, save_history,
    load_embeddings, save_embeddings
)
from gemini_api import call_gemini_api_with_fallback
from topic_generator import pick_topic
from image_handler import get_smart_images, insert_images_into_content
from seo_utils import (
    generate_toc, get_related_posts, insert_inline_internal_links,
    generate_schema_markup, generate_cta_html,
    is_html_truncated, fix_truncated_html
)


def get_banned_title_phrases(window=15, min_count=2):
    """최근 제목에서 반복 사용된 상투 표현 목록 (제목 프롬프트에서 금지)"""
    history = load_history()
    recent_titles = [p.get("title", "") for p in history.get("post_log", [])[-window:]]
    return [ph for ph in TITLE_CLICHES
            if sum(1 for t in recent_titles if ph in t) >= min_count]


def _pick_length_profile():
    names = [p for p in LENGTH_PROFILES]
    weights = [p[3] for p in LENGTH_PROFILES]
    return random.choices(names, weights=weights, k=1)[0]


def generate_post_with_gemini(api_key, category, topic, max_attempts=2,
                              angle=None, series_parent=None):
    """Gemini API로 SEO 최적화된 블로그 글 생성"""
    style = random.choice(WRITING_STYLES)
    title_style = random.choice(TITLE_STYLES)
    format_name, format_desc = random.choice(POST_FORMATS)
    persona = random.choice(PERSONAS)
    length_name, length_spec, min_chars, _ = _pick_length_profile()
    banned_phrases = get_banned_title_phrases()

    print(f"   🎨 변주: 형식={format_name}, 길이={length_name}, 독자={persona.split(' (')[0]}")

    banned_text = ""
    if banned_phrases:
        banned_text = f"\n   ⚠️ 최근 글에서 과사용된 다음 표현은 제목에 절대 쓰지 마세요: {', '.join(banned_phrases)}"

    angle_text = f"\n[글의 관점] {angle}" if angle else ""
    series_text = ""
    if series_parent:
        series_text = f"""
[연재 정보] 이 글은 이전 글 "{series_parent['title']}"의 후속편입니다.
- 도입부에서 이전 글에서 다룬 내용을 한두 문장으로 짚고, 이번 글이 어떤 다음 단계를 다루는지 밝히세요
- 이전 글 내용을 반복하지 말고 명확히 발전된 내용을 작성하세요"""

    prompt = f"""당신은 한국어 IT/개발 블로그 SEO 전문 작성자입니다.

아래 조건에 맞는 블로그 글을 작성해 주세요.
⚠️ 글쓰기 톤: {style}

[카테고리] {category}
[주제] {topic}{angle_text}
[타겟 독자] {persona} — 이 독자의 눈높이와 관심사에 맞춰 쓰세요
[글 형식] {format_desc}{series_text}

[작성 규칙]
1. 반드시 HTML 태그로 포맷팅하세요 (티스토리 블로그용)
2. 제목은 별도로 첫 줄에 순수 텍스트로 출력하세요 (HTML 태그 없이)
3. ⚠️ SEO 제목 규칙: 제목에 검색 유입이 높은 핵심 키워드를 포함하되, 년도(2024년, 2025년 등)는 절대 넣지 마세요.
   ⚠️ 제목 스타일: {title_style}{banned_text}
4. 제목 다음 줄에 이미지 검색 키워드를 영어로 3개 출력하세요 (쉼표 구분)
5. 셋째 줄에 메타 디스크립션을 한 줄로 출력하세요 (150자 이내, 검색 결과에 노출될 요약문)
6. 넷째 줄에 SEO 태그를 쉼표로 구분하여 5~8개 출력하세요 (예: React,프론트엔드,웹개발,SPA,컴포넌트)
7. 다섯째 줄부터 본문을 HTML로 작성하세요

[본문 구조 규칙]
1. ⚠️ 본문 분량: {length_spec}
2. [글 형식] 지시에 따라 H2 소제목으로 큰 구조를 잡으세요 (최소 3개 이상)
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
넷째 줄: SEO 태그 (한국어, 쉼표 구분, 5~8개)
다섯째 줄부터: 본문 HTML
"""

    for attempt in range(max_attempts):
        raw_response = call_gemini_api_with_fallback(api_key, prompt)
        lines = raw_response.strip().split('\n')

        title = lines[0].strip().replace('#', '').replace('<h1>', '').replace('</h1>', '')
        title = title.replace('```html', '').replace('```', '').strip()

        image_keywords = ""
        meta_description = ""
        tags = []
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

        # 넷째 줄: SEO 태그
        if len(lines) > content_start:
            tag_line = lines[content_start].strip()
            if not tag_line.startswith('<') and ',' in tag_line:
                tags = [t.strip() for t in tag_line.replace('```html', '').replace('```', '').split(',') if t.strip()]
                content_start += 1

        content = '\n'.join(lines[content_start:]).strip()
        content = content.replace('```html', '').replace('```', '').strip()

        # TOC 생성 & 삽입
        toc_result = generate_toc(content)
        if toc_result:
            toc_html, content = toc_result
            first_h2 = re.search(r'<h2', content, re.IGNORECASE)
            if first_h2:
                content = content[:first_h2.start()] + toc_html + "\n" + content[first_h2.start():]
            else:
                content = toc_html + "\n" + content

        # 본문 중간 내부 링크 삽입
        content = insert_inline_internal_links(content, title, category)

        # 관련 글 추천 섹션
        related_html = get_related_posts(title, category)
        if related_html:
            content = content + "\n" + related_html

        # Schema markup
        schema_html = generate_schema_markup(title, category, meta_description, content, tags)
        content = schema_html + content

        # 하단 CTA
        content = content + "\n" + generate_cta_html()

        # 품질 검증
        plain_text = re.sub(r'<[^>]+>', '', content)
        text_length = len(plain_text.strip())
        h2_count = len(re.findall(r'<h2', content, re.IGNORECASE))

        quality_ok = True
        if text_length < min_chars:
            print(f"   ⚠️ 본문이 너무 짧음: {text_length}자 (최소 {min_chars}자, {length_name})")
            quality_ok = False
        if h2_count < 3:
            print(f"   ⚠️ H2 소제목 부족: {h2_count}개 (최소 3개)")
            quality_ok = False

        is_truncated = is_html_truncated(content)
        if is_truncated:
            print(f"   ⚠️ HTML 잘림 감지")
            quality_ok = False

        if quality_ok:
            print(f"   ✅ 품질 검증 통과 (본문 {text_length}자, H2 {h2_count}개)")
            return {"title": title, "content": content, "image_keywords": image_keywords,
                    "meta_description": meta_description, "tags": tags,
                    "format": format_name, "persona": persona, "length": length_name}

        if attempt < max_attempts - 1:
            print(f"   🔄 품질 미달 — 재생성 시도 ({attempt+2}/{max_attempts})")
        else:
            print(f"   🔧 최대 시도 횟수 도달 — 현재 글 사용 (본문 {text_length}자)")
            if is_truncated:
                content = fix_truncated_html(content)

    return {"title": title, "content": content, "image_keywords": image_keywords,
            "meta_description": meta_description, "tags": tags,
            "format": format_name, "persona": persona, "length": length_name}


def get_daily_post():
    """오늘의 블로그 글 생성 (Gemini + 스마트 이미지)"""
    config = load_config()
    api_key = config.get("gemini_api_key", "")
    pixabay_key = config.get("pixabay_api_key", "")

    picked = pick_topic(api_key)
    category = picked["category"]
    topic = picked["topic"]
    series_parent = picked.get("series_parent")
    print(f"📌 선택된 카테고리: {category}")
    print(f"📌 선택된 주제: {topic}")
    if series_parent:
        print(f"📌 연재 후속편: {series_parent['title']}")

    post = None

    if api_key and api_key != "여기에_GEMINI_API_키":
        try:
            print("🤖 Gemini API로 글 생성 중 (모델 폴백 체인 활성화)...")
            post = generate_post_with_gemini(
                api_key, category, topic,
                angle=picked.get("angle"), series_parent=series_parent
            )
            print(f"✅ 생성 완료: {post['title']} ({len(post['content'])}자)")
        except Exception as e:
            print(f"⚠️ 모든 Gemini 모델 실패: {e}")
            print("🚫 AI 생성 불가 — 이번 실행은 발행을 건너뜁니다.")
            return None
    else:
        print("⚠️ Gemini API 키 미설정 — 발행을 건너뜁니다.")
        return None

    # 스마트 이미지 검색
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

    # 연재 후속편이면 본문 상단에 이전 글 링크 박스 삽입
    if series_parent and series_parent.get("url"):
        series_html = (
            f'<p style="font-size:15px;background:#fff8e6;border-left:4px solid #f0a500;'
            f'padding:12px 16px;border-radius:6px;margin-bottom:20px;">'
            f'📚 이 글은 <a href="{series_parent["url"]}" '
            f'style="color:#1a73e8;font-weight:bold;">{series_parent["title"]}</a>'
            f'의 후속편입니다. 기초 내용이 궁금하다면 이전 글을 먼저 읽어보세요.</p>'
        )
        post["content"] = series_html + "\n" + post["content"]

    # 발행 이력 저장
    history = load_history()
    history["posted_topics"].append(topic)
    log_entry = {
        "date": str(datetime.date.today()),
        "category": category,
        "topic": topic,
        "title": post["title"],
        "url": "",
    }
    if picked.get("angle"):
        log_entry["angle"] = picked["angle"]
    for key in ("format", "persona", "length"):
        if post.get(key):
            log_entry[key] = post[key]
    if series_parent:
        log_entry["series_parent"] = series_parent["title"]
    history.setdefault("post_log", []).append(log_entry)
    save_history(history)

    # 주제 임베딩 저장 (향후 의미 기반 중복 차단에 사용)
    embedding = picked.get("embedding")
    if embedding is None:
        from gemini_api import get_embedding_with_fallback
        embedding = get_embedding_with_fallback(api_key, topic)
    if embedding:
        embeddings = load_embeddings()
        embeddings[topic] = embedding
        save_embeddings(embeddings)

    tistory_category = TISTORY_CATEGORY_MAP.get(category, category)

    return {
        "title": post["title"],
        "content": post["content"],
        "thumbnail": image_data.get("thumbnail"),
        "image_files": image_data.get("files", []),
        "image_map": image_data.get("image_map", {}),
        "category": tistory_category,
        "meta_description": post.get("meta_description", ""),
        "tags": post.get("tags", []),
    }


def get_random_post():
    return get_daily_post()
