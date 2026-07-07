# Tistory Auto Post

티스토리 블로그에 IT/개발 관련 글을 자동으로 생성하고 발행하는 자동화 도구입니다.

Google Gemini API로 SEO 최적화된 글을 생성하고, Pixabay에서 관련 이미지를 검색해 삽입한 뒤, Selenium으로 티스토리에 자동 로그인하여 포스팅합니다.

---

## 주요 기능

- Gemini 2.5-flash 기반 IT/개발 블로그 글 자동 생성 (숏폼/표준/롱폼 길이 믹스)
- 16개 시드 카테고리 + Gemini가 새 카테고리를 스스로 제안·학습 (최대 8개 추가, 티스토리에 자동 생성)
- 세부주제 자동 확장 (발행 15회마다 Gemini가 새 세부 영역 추가, 기존 영역과 겹치면 자동 거부)
- 글 다양화: 제목 스타일 8종 + 과사용 표현 자동 금지, 글 형식 8종(FAQ/리스트/사례연구 등), 타겟 독자 6종 랜덤 조합
- 와일드카드 모드: 10% 확률로 카테고리를 벗어난 니치/교차 주제 발굴
- Pixabay 이미지 자동 검색 및 본문 삽입 (3장, lazy loading)
- SEO 자동 태그 5~8개 생성 & 티스토리 태그 입력
- 카카오 계정으로 티스토리 자동 로그인 (쿠키 기반)
- 전체 발행 이력 기반 중복 방지 (키워드 + Gemini 임베딩 의미 유사도 검사)
- 세부주제 × 앵글 매트릭스로 주제 다양화 (후보 10개 생성 후 가장 참신한 주제 선택)
- 연재 모드: 과거 글의 후속/심화편 자동 작성 + 이전 글 링크 삽입 (기본 20%)
- 발행 시간 0~30분 랜덤 딜레이 (봇 패턴 방지)
- 글 품질 검증 (최소 글자수, H2 개수, HTML 잘림 감지)
- 텔레그램 알림 (성공/실패/일일 제한)
- Tistory 일일 15개 발행 제한 자동 감지

### SEO 기능

- 에버그린 제목 (년도/시간 표현 제외)
- 메타 디스크립션 자동 생성
- H2/H3 구조화된 본문 + 클릭 가능한 목차(TOC)
- 이미지 alt 태그 최적화 (주제 키워드 포함)
- 본문 내부 링크 자동 삽입 (최대 2개)
- 하단 관련 글 추천 섹션
- Schema markup (JSON-LD Article 구조화 데이터)
- 발행 후 Google Sitemap ping
- 하단 CTA (댓글/공감 유도)
- 5가지 글쓰기 톤 랜덤 적용

---

## 파일 구조

```
tistory_auto_post/
├── tistory_poster.py          # 메인 엔트리포인트 (Selenium 로그인/발행)
├── content_generator.py       # 하위 호환 래퍼 (기존 import 유지)
├── config.py                  # 설정, 상수, 카테고리, 히스토리 관리
├── gemini_api.py              # Gemini API 호출, 모델/키 폴백 체인
├── topic_generator.py         # 주제 후보 생성, 임베딩 중복 차단, 연재 모드, 카테고리 분배
├── post_generator.py          # 글 생성, 품질 검증, 이미지 삽입
├── image_handler.py           # Pixabay/Unsplash 이미지 검색 & 다운로드
├── seo_utils.py               # TOC, 내부링크, Schema markup, CTA, HTML복구
├── notifications.py           # 텔레그램 알림
├── config.json                # 설정 파일 (git 제외)
├── config.example.json        # 설정 파일 샘플
├── post_history.json          # 발행 이력 (중복 방지)
├── topic_embeddings.json      # 주제 임베딩 벡터 (의미 기반 중복 검사, git 제외)
├── run_daily_post.sh          # 스케줄러용 실행 스크립트
├── setup_cron.sh              # Linux cron 등록 (07~21시, 15회/일)
├── setup_server.sh            # Rocky Linux 서버 초기 설치
├── setup_launchd.sh           # macOS launchd 등록/해제
└── README.md
```

---

## 사전 준비

### 1. API 키 발급 (전부 무료)

| API | 발급 URL | 용도 |
|-----|---------|------|
| Google Gemini | https://aistudio.google.com/apikey | 글 생성 |
| Pixabay | https://pixabay.com/api/docs/ | 이미지 검색 |

### 2. 카카오 계정

- 티스토리에 연동된 카카오 계정의 이메일/비밀번호 필요
- **2단계 인증은 반드시 꺼야 합니다** (자동 로그인 불가)

### 3. 텔레그램 알림 (선택)

- BotFather로 봇 생성 → 토큰 발급
- chat_id 확인 후 config.json에 설정

---

## 설치

### Linux 서버 (Rocky Linux 9)

```bash
git clone https://github.com/Grren99/t_story_auto_post.git
cd t_story_auto_post
bash setup_server.sh
```

### macOS

```bash
git clone https://github.com/Grren99/t_story_auto_post.git
cd t_story_auto_post
pip3 install selenium webdriver-manager
```

---

## 설정

```bash
cp config.example.json config.json
```

```json
{
    "blog_url": "https://your-blog.tistory.com",
    "tistory_id": "카카오_이메일@email.com",
    "tistory_pw": "카카오_비밀번호",
    "login_method": "kakao",
    "gemini_api_key": "Gemini_API_키",
    "gemini_api_keys": ["키1", "키2", "키3"],
    "pixabay_api_key": "Pixabay_API_키",
    "telegram_bot_token": "텔레그램_봇_토큰",
    "telegram_chat_id": "텔레그램_채팅_ID",
    "headless": true,
    "chrome_driver_path": "auto"
}
```

| 항목 | 설명 |
|------|------|
| `blog_url` | 티스토리 블로그 주소 |
| `tistory_id` | 카카오 계정 이메일 |
| `tistory_pw` | 카카오 계정 비밀번호 |
| `gemini_api_key` | Gemini API 키 (단일) |
| `gemini_api_keys` | Gemini API 키 목록 (폴백용, 선택) |
| `pixabay_api_key` | Pixabay API 키 |
| `telegram_bot_token` | 텔레그램 봇 토큰 (선택) |
| `telegram_chat_id` | 텔레그램 채팅 ID (선택) |
| `headless` | `true`: 브라우저 숨김 / `false`: 브라우저 표시 |

> config.json에는 개인정보가 포함됩니다. `.gitignore`에 등록되어 있으므로 git에 올라가지 않습니다.

---

## 사용법

### 수동 실행

```bash
# 일반 실행 (headless)
python3 tistory_poster.py

# 브라우저 보면서 실행 (디버깅)
python3 tistory_poster.py --no-headless

# 발행 없이 테스트
python3 tistory_poster.py --dry-run

# 랜덤 주제 선택
python3 tistory_poster.py --random
```

### 카테고리 관리

```bash
# 현재 카테고리 목록 조회
python3 tistory_poster.py --list-categories

# 필요한 카테고리 자동 생성 (없는 것만)
python3 tistory_poster.py --setup-categories
```

### CLI 옵션

| 옵션 | 설명 |
|------|------|
| `--dry-run` | 글 생성만 하고 발행하지 않음 |
| `--no-headless` | 브라우저 화면을 보면서 실행 |
| `--random` | 랜덤 주제로 글 생성 |
| `--list-categories` | 블로그의 기존 카테고리 목록 조회 |
| `--setup-categories` | 필요한 카테고리 자동 생성 |

---

## 자동 스케줄링

### Linux 서버 (cron)

```bash
bash setup_cron.sh
```

매시간 정각 07:00~21:00 실행 (하루 15회, Tistory 일일 발행 제한에 맞춤)

스크립트 내에서 0~30분 랜덤 딜레이가 적용되어 자연스러운 발행 패턴을 유지합니다.

```bash
# 확인
crontab -l

# 로그
tail -f logs/cron_$(date +%Y%m%d).log
```

### macOS (launchd)

```bash
bash setup_launchd.sh install    # 등록
bash setup_launchd.sh uninstall  # 해제
launchctl list | grep tistory    # 확인
```

---

## 주제 카테고리 (10개)

| 카테고리 | 예시 주제 |
|---------|----------|
| 기술 리뷰 | React vs Vue vs Svelte, Bun vs Node vs Deno |
| 개발 도구 | AI 코딩 어시스턴트 비교, API 테스트 도구 비교 |
| 개발 책 리뷰 | 클린 코드 핵심 요약, DDD 핵심 개념 정리 |
| 이슈 분석 | 개발자 번아웃 예방, 풀스택 vs 전문분야 |
| 튜토리얼 | Docker Compose 환경 세팅, JWT 인증 구현 |
| AI 머신러닝 | LLM 파인튜닝, RAG 구현, 프롬프트 엔지니어링 |
| 클라우드 인프라 | AWS vs GCP vs Azure, 쿠버네티스 입문 |
| 보안 | OWASP Top 10, OAuth 2.0, SQL Injection 방어 |
| 커리어 취업 | 기술 면접 준비, 이력서 작성법, 연봉 협상 |
| 생산성 자동화 | 워크플로우 자동화, 셸 스크립트, GitHub Actions |

Gemini가 매번 새로운 주제를 생성하며, 카테고리별 균등 분배 + 유사 주제 중복 방지가 적용됩니다.

---

## Gemini API 무료 한도

- 모델: `gemini-2.5-flash` — **무료 티어 하루 20회/키** (정책 변경으로 대폭 축소됨)
- 글 1편당 생성 호출 2~4회 (주제 후보 1회 + 본문 1~2회) + 임베딩 호출 수 회 (임베딩은 별도 쿼터)
- 하루 여러 편 발행하려면 **API 키 여러 개 등록 필수** (`gemini_api_keys` 배열) — 자동 폴백
- 한도 도달 시 자동으로 다음 키로 전환

## 중복 방지 & 다양성 설정 (config.json)

| 키 | 기본값 | 설명 |
|----|--------|------|
| `series_post_ratio` | 0.2 | 연재(후속편) 글 비율. 0이면 비활성화 |
| `wildcard_post_ratio` | 0.1 | 카테고리를 벗어난 자유 주제 비율. 0이면 비활성화 |
| `embedding_similarity_threshold` | 0.85 | 이 값 이상이면 중복 판정. 낮출수록 엄격 |
| `auto_create_categories` | true | 발행 직전 카테고리가 블로그에 없으면 자동 생성 |

Gemini가 학습한 신규 카테고리는 `topic_taxonomy.json`에 저장되고, 발행 직전 pre-flight에서
티스토리 블로그에 자동 생성됩니다 (`auto_create_categories`). `--setup-categories`를 수동 실행해도 됩니다.

새 주제는 **전체 발행 이력**과 비교됩니다: 키워드 겹침 1차 필터 → Gemini 임베딩 코사인 유사도 2차 필터.
주제 임베딩은 `topic_embeddings.json`에 누적 저장되어 1~2년 운영해도 의미가 겹치는 주제를 차단합니다.

---

## 트러블슈팅

### "unexpected alert" 에러
티스토리 임시저장 복구 또는 일일 발행 제한 알림창. 자동 처리됩니다.

### Pixabay 이미지가 안 보임
외부 URL 핫링크 차단일 수 있음. Pixabay 정책에 따라 일부 이미지가 표시되지 않을 수 있습니다.

### 일일 15개 제한 도달
Tistory는 하루 최대 15개 공개 발행만 허용합니다. 제한 도달 시 자동 감지 후 텔레그램 알림을 보내고 해당 실행을 건너뜁니다.

### selenium 못 찾는 에러
```bash
pip3 install selenium webdriver-manager
```

### ChromeDriver 버전 에러
Chrome 브라우저를 최신으로 업데이트하세요. `webdriver-manager`가 자동으로 맞는 드라이버를 설치합니다.

---

## 라이선스

MIT License
