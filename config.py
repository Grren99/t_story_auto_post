"""
설정 및 상수 관리
- config.json 로드
- post_history.json 관리
- 카테고리, 이미지 키워드, 티스토리 매핑 등 상수
"""

import json
from pathlib import Path

# ============================================================
# 경로 설정
# ============================================================
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
HISTORY_PATH = BASE_DIR / "post_history.json"
IMAGES_DIR = BASE_DIR / "images"

# ============================================================
# 블로그 카테고리 & 폴백 주제 풀
# ============================================================
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

# 글쓰기 톤 스타일
WRITING_STYLES = [
    "친근하고 대화하듯이 설명하는 스타일 (예: ~하죠, ~거든요, ~인데요)",
    "전문적이고 신뢰감 있는 분석 스타일 (예: ~이다, ~할 수 있다, ~로 판단된다)",
    "실무 경험을 공유하는 후기 스타일 (예: 직접 써보니, 실제로 적용해 본 결과)",
    "문제 해결 중심의 실용적 스타일 (예: 이런 문제가 있었는데, 해결 방법은)",
    "비교 분석을 통한 객관적 리뷰 스타일 (예: 각각의 장단점을 살펴보면)",
]


# ============================================================
# 설정 / 히스토리 로드 & 저장
# ============================================================
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
