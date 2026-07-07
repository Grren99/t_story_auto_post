"""
과거 발행 주제의 임베딩 백필 스크립트
- 서버에서 새 중복 차단 시스템을 처음 쓸 때 1회 실행
- post_history.json의 모든 주제를 임베딩해 topic_embeddings.json에 저장
- 이미 임베딩된 주제는 건너뜀 (여러 번 실행해도 안전)

사용법: python3 backfill_embeddings.py
"""

import time

from config import load_config, load_history, load_embeddings, save_embeddings
from gemini_api import get_embedding_with_fallback


def main():
    api_key = load_config().get("gemini_api_key", "")
    if not api_key:
        print("❌ config.json에 gemini_api_key가 없습니다.")
        return

    history = load_history()
    embeddings = load_embeddings()
    topics = history.get("posted_topics", [])
    todo = [t for t in topics if t not in embeddings]

    print(f"전체 주제 {len(topics)}개 중 백필 대상: {len(todo)}개")
    if not todo:
        print("✅ 모든 주제가 이미 임베딩되어 있습니다.")
        return

    done = 0
    for i, topic in enumerate(todo):
        vec = get_embedding_with_fallback(api_key, topic)
        if vec is None:
            print(f"❌ 임베딩 실패로 중단 — 다시 실행하면 이어서 진행됩니다: {topic}")
            break
        embeddings[topic] = vec
        done += 1
        # 10개마다 저장 (원자적 쓰기 — 중단돼도 파일이 손상되지 않음)
        if done % 10 == 0:
            save_embeddings(embeddings)
            print(f"  {done}/{len(todo)} 완료")
        time.sleep(0.3)

    save_embeddings(embeddings)
    print(f"✅ 백필 종료: 이번에 {done}개 처리, 총 {len(embeddings)}개 저장됨")
    if done < len(todo):
        print("   남은 주제가 있습니다 — 스크립트를 다시 실행하면 이어서 진행됩니다.")


if __name__ == "__main__":
    main()
