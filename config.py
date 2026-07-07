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
EMBEDDINGS_PATH = BASE_DIR / "topic_embeddings.json"
TAXONOMY_PATH = BASE_DIR / "topic_taxonomy.json"
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
    "데이터 엔지니어링": [
        "Airflow로 데이터 파이프라인 구축하기",
        "Kafka 기초: 이벤트 스트리밍 아키텍처 이해",
        "dbt로 데이터 변환 워크플로우 관리하기",
        "데이터 웨어하우스 vs 데이터 레이크 차이점",
        "DuckDB로 로컬 데이터 분석 환경 만들기",
    ],
    "모바일 앱 개발": [
        "Flutter vs React Native 크로스플랫폼 선택 기준",
        "모바일 앱 성능 최적화 체크리스트",
        "앱 스토어 심사 통과 노하우",
        "푸시 알림 설계와 구현 가이드",
        "모바일 앱 오프라인 우선 설계",
    ],
    "게임 개발": [
        "Unity vs Unreal vs Godot 게임 엔진 비교",
        "인디 게임 개발 시작하기",
        "게임 서버 아키텍처 기초",
        "멀티플레이어 게임 네트워킹 이해",
        "게임 성능 최적화 기법 정리",
    ],
    "임베디드 IoT": [
        "라즈베리파이로 홈서버 구축하기",
        "아두이노 입문: 첫 IoT 프로젝트",
        "MQTT 프로토콜로 IoT 기기 연결하기",
        "Home Assistant로 스마트홈 자동화",
        "임베디드 개발자가 알아야 할 RTOS 기초",
    ],
    "테스트 QA": [
        "Playwright로 E2E 테스트 자동화하기",
        "테스트 주도 개발(TDD) 실전 적용법",
        "단위 테스트 vs 통합 테스트 전략",
        "부하 테스트 도구 비교 (k6, JMeter, Locust)",
        "테스트 커버리지의 함정과 올바른 품질 지표",
    ],
    "오픈소스": [
        "오픈소스 기여 첫걸음: 이슈 찾기부터 PR까지",
        "유명 오픈소스 프로젝트 코드 읽는 법",
        "내 프로젝트 오픈소스로 공개하기",
        "오픈소스 라이선스 선택 기준",
        "GitHub 프로필을 빛내는 오픈소스 활동",
    ],
}

# ============================================================
# 주제 다양화 매트릭스 (카테고리 × 세부주제 × 앵글)
# 주제 생성 시 세부주제와 앵글을 랜덤 조합하여 주제 공간을 확장
# ============================================================
SUBTOPICS = {
    "기술 리뷰": [
        "프론트엔드 프레임워크/라이브러리", "백엔드 프레임워크", "프로그래밍 언어 (Rust, Go, Kotlin, Zig 등)",
        "JavaScript/TypeScript 생태계", "ORM과 데이터 액세스 기술", "상태 관리 라이브러리",
        "빌드 도구와 번들러", "테스트 프레임워크", "런타임 환경 (Node, Deno, Bun, WASM)",
        "CSS 프레임워크와 스타일링 기법", "모바일 크로스플랫폼 (Flutter, React Native)", "데스크톱 앱 기술 (Electron, Tauri)",
        "데이터베이스 (RDB, NoSQL, NewSQL, 시계열)", "메시지 큐와 이벤트 스트리밍", "검색 엔진 기술 (Elasticsearch 등)",
    ],
    "개발 도구": [
        "코드 에디터/IDE와 플러그인", "터미널과 셸 도구", "Git 워크플로우 도구",
        "API 개발/테스트 도구", "디버깅과 프로파일링 도구", "문서화 도구",
        "패키지 매니저", "코드 품질 도구 (린터, 포매터, 정적분석)", "협업 도구",
        "데이터베이스 클라이언트/GUI 도구", "로컬 개발 환경 도구 (컨테이너, VM)", "AI 코딩 어시스턴트",
    ],
    "개발 책 리뷰": [
        "코드 품질/리팩터링 도서", "소프트웨어 아키텍처 도서", "알고리즘/자료구조 도서",
        "시스템 설계 도서", "개발 문화/조직 도서", "특정 언어 심화 도서",
        "데이터베이스/데이터 엔지니어링 도서", "DevOps/SRE 도서", "개발자 커리어/성장 도서",
        "컴퓨터 과학 기초 도서 (OS, 네트워크, 컴파일러)",
    ],
    "이슈 분석": [
        "개발 조직 문화와 프로세스", "기술 선택과 의사결정", "오픈소스 생태계",
        "개발자 커뮤니티와 트렌드", "소프트웨어 품질과 기술 부채", "원격 근무와 협업 방식",
        "주니어/시니어 성장 이슈", "코드 리뷰와 페어 프로그래밍", "애자일/스크럼 실천",
        "라이선스와 법적 이슈", "AI가 바꾸는 개발 업무",
    ],
    "튜토리얼": [
        "웹 서버/리버스 프록시 설정", "인증/인가 구현", "캐싱 적용",
        "데이터베이스 설계와 튜닝", "비동기 처리와 작업 큐", "웹소켓/실시간 기능 구현",
        "파일 업로드/이미지 처리", "검색 기능 구현", "결제/외부 API 연동",
        "로깅과 모니터링 구축", "테스트 코드 작성", "배포 파이프라인 구축",
        "크롤링/스크래핑 자동화", "CLI 도구 만들기", "성능 측정과 부하 테스트",
    ],
    "AI 머신러닝": [
        "LLM API 활용 개발", "RAG와 벡터 검색", "AI 에이전트 구축",
        "프롬프트 엔지니어링", "파인튜닝과 모델 커스터마이징", "로컬 LLM 구동",
        "이미지/음성 생성 AI", "MLOps와 모델 서빙", "임베딩과 시맨틱 검색",
        "AI 평가와 테스트", "멀티모달 AI 활용", "머신러닝 기초 이론",
    ],
    "클라우드 인프라": [
        "컴퓨팅 서비스 (EC2, Lambda, Cloud Run)", "컨테이너 오케스트레이션 (K8s, ECS)", "IaC (Terraform, Pulumi, CDK)",
        "네트워킹 (VPC, DNS, 로드밸런서)", "스토리지와 CDN", "관리형 데이터베이스 서비스",
        "모니터링/옵저버빌리티", "비용 최적화", "고가용성과 재해 복구",
        "서버리스 아키텍처", "마이크로서비스와 서비스 메시", "CI/CD와 GitOps",
    ],
    "보안": [
        "웹 취약점과 방어 (XSS, CSRF, Injection)", "인증/인가 보안 (OAuth, JWT, 세션)", "암호화와 키 관리",
        "API 보안", "컨테이너/클라우드 보안", "시크릿 관리",
        "의존성/공급망 보안", "보안 테스트와 취약점 스캔", "네트워크 보안 (TLS, 방화벽)",
        "개인정보 보호와 컴플라이언스", "보안 사고 사례 분석",
    ],
    "커리어 취업": [
        "기술 면접 준비", "코딩 테스트 전략", "이력서와 포트폴리오",
        "연봉 협상과 처우", "이직 전략", "사이드 프로젝트",
        "개발자 브랜딩 (블로그, 발표, 오픈소스)", "리더십과 매니징 트랙", "직무 전환 (프론트→백엔드, 개발→DevOps 등)",
        "글로벌 취업과 영어", "프리랜싱과 창업", "번아웃과 멘탈 관리",
    ],
    "생산성 자동화": [
        "셸 스크립트와 CLI 자동화", "GitHub Actions 활용", "개발 환경 자동화 (dotfiles, devcontainer)",
        "문서/지식 관리 자동화", "반복 업무 자동화 (Python 스크립트)", "봇 만들기 (Slack, Discord, Telegram)",
        "크론과 스케줄링", "코드 생성과 템플릿화", "AI를 활용한 업무 자동화",
        "키보드/윈도우 매니저 등 로컬 생산성", "노코드/로우코드 연동",
    ],
    "데이터 엔지니어링": [
        "데이터 파이프라인 (Airflow, Dagster)", "이벤트 스트리밍 (Kafka, Flink)", "데이터 웨어하우스/레이크하우스",
        "ETL/ELT 설계와 dbt", "데이터 품질과 거버넌스", "고급 SQL과 쿼리 최적화",
        "분석 엔진 (Spark, DuckDB)", "데이터 모델링", "실시간 분석 아키텍처", "BI/시각화 도구",
    ],
    "모바일 앱 개발": [
        "Flutter 개발", "React Native 개발", "네이티브 개발 (Swift, Kotlin)",
        "앱 배포와 스토어 심사", "푸시 알림과 딥링크", "모바일 성능 최적화",
        "오프라인 지원과 로컬 DB", "앱 수익화 전략", "모바일 테스트와 CI/CD", "모바일 앱 보안",
    ],
    "게임 개발": [
        "Unity 개발", "Unreal Engine 개발", "Godot 개발",
        "게임 서버와 백엔드", "게임 물리/그래픽스 기초", "인디 게임 제작과 출시",
        "게임 성능 최적화", "멀티플레이 네트워킹", "게임 AI 구현", "라이브옵스와 수익화",
    ],
    "임베디드 IoT": [
        "아두이노/라즈베리파이 프로젝트", "MCU 펌웨어 개발", "RTOS 활용",
        "센서/액추에이터 연동", "IoT 통신 프로토콜 (MQTT, BLE, LoRa)", "엣지 컴퓨팅",
        "홈 자동화 (Home Assistant)", "임베디드 리눅스", "저전력 설계", "IoT 보안",
    ],
    "테스트 QA": [
        "단위/통합 테스트 전략", "E2E 자동화 (Playwright, Cypress)", "테스트 주도 개발 (TDD)",
        "성능/부하 테스트", "테스트 커버리지와 품질 지표", "모킹과 테스트 더블",
        "API 테스트 자동화", "QA 프로세스와 협업", "시각적 회귀 테스트", "테스트 데이터 관리",
    ],
    "오픈소스": [
        "오픈소스 기여 방법", "유명 프로젝트 코드 분석", "라이선스와 법적 이슈",
        "내 프로젝트 공개와 운영", "메인테이너 경험담", "GitHub 고급 활용",
        "상용 서비스의 오픈소스 대체재", "오픈소스 커뮤니티와 거버넌스", "스폰서십과 펀딩", "오픈소스 문서화",
    ],
}

# 글의 관점/형식 — 같은 기술도 앵글이 다르면 다른 글이 됨
ANGLES = [
    "입문자를 위한 기초 개념 정리",
    "실무 적용 사례와 베스트 프랙티스",
    "자주 겪는 문제와 트러블슈팅 가이드",
    "성능 최적화와 튜닝 기법",
    "두 가지 이상 기술/방식의 비교 분석",
    "안티패턴과 흔한 실수 모음",
    "마이그레이션/업그레이드 경험 가이드",
    "내부 동작 원리 깊이 파헤치기",
    "실전 체크리스트와 점검 가이드",
    "단계별 따라하기 실습",
    "장단점과 도입 의사결정 가이드",
    "자주 묻는 질문(FAQ) 형식 정리",
]

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
    "데이터 엔지니어링": "data analytics pipeline",
    "모바일 앱 개발": "mobile app smartphone development",
    "게임 개발": "game development videogame",
    "임베디드 IoT": "iot electronics circuit board",
    "테스트 QA": "software testing quality",
    "오픈소스": "open source code community",
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
    "데이터 엔지니어링": "데이터 엔지니어링",
    "모바일 앱 개발": "모바일 앱 개발",
    "게임 개발": "게임 개발",
    "임베디드 IoT": "임베디드 IoT",
    "테스트 QA": "테스트 QA",
    "오픈소스": "오픈소스",
}

# 글쓰기 톤 스타일
WRITING_STYLES = [
    "친근하고 대화하듯이 설명하는 스타일 (예: ~하죠, ~거든요, ~인데요)",
    "전문적이고 신뢰감 있는 분석 스타일 (예: ~이다, ~할 수 있다, ~로 판단된다)",
    "실무 경험을 공유하는 후기 스타일 (예: 직접 써보니, 실제로 적용해 본 결과)",
    "문제 해결 중심의 실용적 스타일 (예: 이런 문제가 있었는데, 해결 방법은)",
    "비교 분석을 통한 객관적 리뷰 스타일 (예: 각각의 장단점을 살펴보면)",
]

# 제목 스타일 — 제목이 한 가지 패턴으로 수렴하는 것을 방지
TITLE_STYLES = [
    "질문형 — 독자의 고민을 그대로 묻는 제목 (예: 'ORM, 정말 써야 할까?')",
    "숫자형 — 구체적 숫자를 내세운 제목 (예: 'Redis 도입 전 확인할 7가지')",
    "경험형 — 직접 해본 사람의 후기 느낌 (예: 'Bun으로 갈아탄 지 3개월, 솔직한 소감')",
    "반전/경고형 — 통념을 뒤집거나 실수를 경고 (예: '그 인덱스, 오히려 느려집니다')",
    "How-to형 — 구체적 행동 중심 (예: 'JWT 토큰 만료를 우아하게 처리하는 법')",
    "비교형 — 선택지를 대비 (예: 'Kafka냐 RabbitMQ냐: 메시지 큐 선택의 기준')",
    "스토리형 — 상황이나 사건에서 출발 (예: '새벽 3시 서버 장애에서 배운 것들')",
    "결과형 — 성과/수치를 앞세움 (예: '쿼리 하나 고쳐서 응답 속도 10배 올린 이야기')",
]

# 최근 제목에서 반복 사용 시 금지할 상투 표현
TITLE_CLICHES = [
    "완벽 가이드", "완벽 정리", "총정리", "핵심 정리", "핵심 요약",
    "모든 것", "한눈에 보는", "A to Z", "가이드", "마스터하기", "완벽",
]

# 글 형식 템플릿 — (이름, 구조 지시)
POST_FORMATS = [
    ("표준형", "H2 소제목 5~7개로 개념 소개 → 상세 설명 → 정리 순서의 표준 구성"),
    ("FAQ형", "독자가 실제로 검색할 법한 질문들을 H2 소제목으로 삼아 질문-답변 형식으로 구성하세요 (질문 5~8개)"),
    ("리스트형", "'N가지' 항목 나열식 구성 — 각 항목을 H2 소제목으로 만들고, 항목마다 이유와 구체적 예시를 포함하세요"),
    ("사례연구형", "구체적인 상황/프로젝트를 설정하고 '문제 발생 → 원인 분석 → 해결 과정 → 교훈' 순서로 서술하세요 (각 단계를 H2로)"),
    ("체크리스트형", "실무에서 바로 쓸 수 있는 점검 항목 중심 구성 — 영역별로 H2 소제목을 만들고 체크 항목과 그 이유를 설명하세요"),
    ("문제해결형", "하나의 문제 상황에서 출발해 여러 해결 방법을 단계적으로 비교하고 적용하는 구성 (각 방법을 H2로)"),
    ("미신타파형", "널리 퍼진 오해/통념을 하나씩 H2 소제목으로 제시하고 사실과 근거로 바로잡는 구성"),
    ("로드맵형", "단계(레벨)별 학습/도입 경로를 순서대로 안내하는 구성 — 각 단계를 H2 소제목으로"),
]

# 타겟 독자 페르소나 — 같은 주제도 독자가 다르면 다른 글이 됨
PERSONAS = [
    "프로그래밍을 배우기 시작한 입문자 (전문 용어는 반드시 풀어서 설명)",
    "실무 1~3년차 주니어 개발자 (기본기는 있지만 실전 경험이 부족)",
    "5년차 이상 시니어 개발자 (깊이 있는 내용과 트레이드오프 논의를 선호)",
    "팀을 이끄는 테크리드/엔지니어링 매니저 (기술 선택과 팀 운영 관점)",
    "개발 지식이 필요한 기획자/PM (코드보다 개념과 의사결정 관점)",
    "취업/이직을 준비 중인 예비 개발자 (면접과 실무 연결 관점)",
]

# 글 길이 프로필 — (이름, 분량 지시, 품질검증 최소 글자수, 선택 가중치)
LENGTH_PROFILES = [
    ("숏폼", "1500~2500자 — 핵심만 간결하게, H2 소제목 3~4개", 800, 0.25),
    ("표준", "3000~5000자 — 충분히 상세하게, H2 소제목 5~7개", 1500, 0.55),
    ("롱폼", "5000~7000자 — 모든 측면을 깊이 있게 다루는 심층 글, H2 소제목 6~9개", 2500, 0.20),
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


def load_embeddings():
    """주제별 임베딩 벡터 저장소 로드 ({주제: [벡터]})"""
    if EMBEDDINGS_PATH.exists():
        with open(EMBEDDINGS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_taxonomy():
    """동적 세부주제 저장소 로드 (Gemini가 제안한 학습 세부주제)"""
    if TAXONOMY_PATH.exists():
        with open(TAXONOMY_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"learned_subtopics": {}, "expanded_at_post_count": 0}


def save_taxonomy(taxonomy):
    with open(TAXONOMY_PATH, 'w', encoding='utf-8') as f:
        json.dump(taxonomy, f, ensure_ascii=False, indent=2)


def get_learned_categories():
    """Gemini가 학습한 신규 카테고리 ({이름: {"image_keyword", "subtopics"}})"""
    return load_taxonomy().get("learned_categories", {})


def get_all_categories():
    """시드 카테고리 + 학습된 신규 카테고리 전체 목록"""
    learned = [c for c in get_learned_categories() if c not in CATEGORIES]
    return list(CATEGORIES.keys()) + learned


def get_effective_subtopics(category):
    """시드 세부주제(SUBTOPICS) + 동적으로 학습된 세부주제 합산"""
    taxonomy = load_taxonomy()
    seed = SUBTOPICS.get(category, [])
    # 학습된 신규 카테고리라면 그 카테고리의 세부주제가 시드
    if not seed:
        seed = taxonomy.get("learned_categories", {}).get(category, {}).get("subtopics", [])
    learned = taxonomy.get("learned_subtopics", {}).get(category, [])
    return seed + [s for s in learned if s not in seed]


def get_image_keyword(category):
    """카테고리별 이미지 검색 키워드 (학습된 카테고리 포함)"""
    if category in IMAGE_KEYWORDS:
        return IMAGE_KEYWORDS[category]
    learned = get_learned_categories().get(category, {})
    return learned.get("image_keyword") or "programming coding"


def save_embeddings(embeddings):
    with open(EMBEDDINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(embeddings, f, ensure_ascii=False)
