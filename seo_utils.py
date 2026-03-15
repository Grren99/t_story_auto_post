"""
SEO 유틸리티 모듈
- TOC (목차) 생성
- 관련 글 추천 섹션
- 본문 내부 링크 삽입
- Schema markup (JSON-LD)
- HTML 잘림 감지 & 복구
"""

import json
import re
import random

from config import load_history


def generate_toc(html_content):
    """HTML 본문에서 h2/h3 태그를 파싱하여 목차(Table of Contents) HTML 생성"""
    headings = re.findall(r'<(h[23])[^>]*>(.*?)</\1>', html_content, re.IGNORECASE | re.DOTALL)
    if len(headings) < 2:
        return ""

    toc_items = []
    for i, (tag, text) in enumerate(headings):
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

    same_category = [p for p in post_log if p.get("category") == current_category and p.get("title") != current_topic]
    other_posts = [p for p in post_log if p.get("category") != current_category and p.get("title") != current_topic]

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
    """본문 중간에 자연스러운 내부 링크를 삽입 (SEO 강화)"""
    history = load_history()
    post_log = history.get("post_log", [])
    if not post_log:
        return html_content

    linkable = [p for p in post_log if p.get("url") and p.get("title") != current_title]
    if not linkable:
        return html_content

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

        keywords = [w for w in title.replace(",", " ").replace(":", " ").split() if len(w) >= 3]
        if not keywords:
            continue

        for keyword in keywords[:3]:
            if f'>{keyword}<' not in html_content and keyword in html_content:
                pattern = re.compile(
                    r'(<p[^>]*>)(.*?)(' + re.escape(keyword) + r')(.*?)(</p>)',
                    re.IGNORECASE | re.DOTALL
                )
                match = pattern.search(html_content)
                if match:
                    link_html = f'<a href="{url}" style="color:#1a73e8;text-decoration:underline;" title="{title}">{keyword}</a>'
                    full_match = match.group(0)
                    replaced = match.group(1) + match.group(2) + link_html + match.group(4) + match.group(5)
                    html_content = html_content.replace(full_match, replaced, 1)
                    links_inserted += 1
                    break

    if links_inserted > 0:
        print(f"   🔗 본문 내부 링크 {links_inserted}개 삽입")
    return html_content


def generate_schema_markup(title, category, meta_description, content, tags):
    """Article Schema markup (JSON-LD) 생성"""
    schema_desc = meta_description or re.sub(r'<[^>]+>', '', content)[:150]
    schema_desc = schema_desc.replace('"', '\\"').replace('\n', ' ').strip()
    schema_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": schema_desc,
        "articleSection": category,
        "inLanguage": "ko",
        "keywords": ", ".join(tags) if tags else category,
    }, ensure_ascii=False)
    return f'<script type="application/ld+json">{schema_json}</script>\n'


def generate_cta_html():
    """하단 CTA (댓글/공감 유도) HTML 생성"""
    return (
        '<div style="background:#e8f5e9;border-left:4px solid #4caf50;padding:15px 20px;'
        'margin:30px 0;border-radius:4px;text-align:center;">'
        '<p style="font-size:15px;margin:0;color:#2e7d32;">'
        '이 글이 도움이 되셨다면 <b>공감(♥)</b>과 <b>댓글</b>로 응원해 주세요!<br>'
        '<span style="font-size:13px;color:#666;">궁금한 점이나 다루었으면 하는 주제가 있다면 댓글로 남겨주세요.</span>'
        '</p></div>'
    )


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
