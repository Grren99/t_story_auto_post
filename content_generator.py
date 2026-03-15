"""
블로그 글 콘텐츠 생성기 (하위 호환 래퍼)
- 실제 로직은 분리된 모듈에서 처리
- 기존 import를 유지하기 위한 re-export
"""

# 기존 코드에서 import 하던 것들을 모두 re-export
from config import (
    CATEGORIES, IMAGE_KEYWORDS, TISTORY_CATEGORY_MAP,
    load_config, load_history, save_history
)
from post_generator import get_daily_post, get_random_post, generate_post_with_gemini
from topic_generator import pick_topic
from image_handler import get_smart_images, insert_images_into_content
from seo_utils import generate_toc, get_related_posts


# 단독 실행 테스트
if __name__ == "__main__":
    print("=" * 60)
    print("  티스토리 블로그 글 생성기 테스트")
    print("=" * 60)
    print()

    post = get_daily_post()
    if post:
        print()
        print(f"제목: {post['title']}")
        print(f"본문 길이: {len(post['content'])}자")
        print(f"태그: {post.get('tags', [])}")
        print(f"썸네일: {post.get('thumbnail', '없음')}")
        print(f"이미지 파일: {post.get('image_files', [])}")
        print()
        print("--- 본문 미리보기 (앞 800자) ---")
        print(post['content'][:800])
        print("...")
