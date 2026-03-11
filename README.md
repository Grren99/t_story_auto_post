# Tistory Auto Post

티스토리 블로그에 IT/개발 관련 글을 자동으로 생성하고 발행하는 자동화 도구입니다.

Google Gemini API로 글을 생성하고, Pixabay에서 관련 이미지를 검색해 삽입한 뒤, Selenium으로 티스토리에 자동 로그인하여 포스팅합니다.

---

## 주요 기능

- Gemini API 기반 IT/개발 블로그 글 자동 생성 (8,000자 내외)
- 5개 카테고리 자동 분류 (기술 리뷰, 개발 도구, 개발 지식 책, 개발 이슈, 튜토리얼)
- Pixabay 이미지 자동 검색 및 본문 삽입 (3장)
- 카카오 계정으로 티스토리 자동 로그인 (쿠키 불필요)
- 중복 포스팅 방지 (히스토리 관리)
- macOS launchd 기반 스케줄링 (매일 최대 6회 자동 포스팅)

---

## 파일 구조

```
tistory_auto_post/
├── tistory_poster.py                  # 메인 (로그인, 카테고리, 글쓰기, 발행)
├── content_generator.py               # 콘텐츠 생성 (Gemini API, Pixabay)
├── config.json                        # 설정 파일 (⚠️ git 제외)
├── config.example.json                # 설정 파일 샘플
├── post_history.json                  # 발행 이력 (중복 방지)
├── run_daily_post.sh                  # 스케줄러용 실행 스크립트
├── setup_launchd.sh                   # launchd 등록/해제 스크립트
├── com.tistory.autopost.*.plist       # launchd 스케줄 (9시~14시)
├── .gitignore                         # git 제외 목록
└── README.md                          # 이 파일
```

---

## 사전 준비

### 1. API 키 발급

| API | 발급 URL | 비용 |
|-----|---------|------|
| Google Gemini | https://aistudio.google.com/apikey | 무료 |
| Pixabay | https://pixabay.com/api/docs/ | 무료 |

### 2. 카카오 계정

- 티스토리에 연동된 카카오 계정의 이메일/비밀번호 필요
- **2단계 인증은 반드시 꺼야 합니다** (자동 로그인 불가)

### 3. Python 패키지 설치

```bash
# Python 3.9 이상 필요
python3 --version

# 패키지 설치 (macOS homebrew python인 경우)
pip3 install selenium webdriver-manager google-generativeai requests --break-system-packages
```

### 4. Chrome 브라우저

- Google Chrome 최신 버전 설치 필수
- ChromeDriver는 `webdriver-manager`가 자동 관리

---

## 설정 방법

### config.json 생성

```bash
cp config.example.json config.json
```

`config.json`을 열어서 본인 정보로 수정:

```json
{
    "blog_url": "https://your-blog.tistory.com",
    "tistory_id": "카카오_이메일@email.com",
    "tistory_pw": "카카오_비밀번호",
    "login_method": "kakao",
    "gemini_api_key": "Gemini_API_키",
    "pixabay_api_key": "Pixabay_API_키",
    "post_time": "09:00",
    "headless": true,
    "chrome_driver_path": "auto"
}
```

| 항목 | 설명 |
|------|------|
| `blog_url` | 티스토리 블로그 주소 |
| `tistory_id` | 카카오 계정 이메일 |
| `tistory_pw` | 카카오 계정 비밀번호 |
| `gemini_api_key` | Google Gemini API 키 |
| `pixabay_api_key` | Pixabay API 키 |
| `headless` | `true`: 브라우저 숨김 / `false`: 브라우저 표시 |

> ⚠️ `config.json`에는 개인정보가 포함되어 있습니다. **절대 git에 올리지 마세요.** `.gitignore`에 이미 등록되어 있습니다.

---

## 사용법

### 수동 포스팅 (1회)

```bash
cd /path/to/tistory_auto_post

# 일반 실행 (headless 모드)
python3 tistory_poster.py

# 브라우저 보면서 실행 (디버깅용)
python3 tistory_poster.py --no-headless

# 발행 없이 테스트만
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

### CLI 옵션 정리

| 옵션 | 설명 |
|------|------|
| `--dry-run` | 글 생성만 하고 발행하지 않음 |
| `--no-headless` | 브라우저 화면을 보면서 실행 |
| `--random` | 랜덤 주제로 글 생성 |
| `--list-categories` | 블로그의 기존 카테고리 목록 조회 |
| `--setup-categories` | 필요한 카테고리 자동 생성 |

---

## 자동 스케줄링 (macOS launchd)

매일 정해진 시간에 자동으로 포스팅되도록 설정합니다.

### 스케줄 등록

```bash
bash /path/to/tistory_auto_post/setup_launchd.sh install
```

기본 설정: **매일 9시, 10시, 11시, 12시, 13시, 14시** 총 6회 자동 포스팅

### 등록 확인

```bash
launchctl list | grep tistory
```

### 스케줄 해제

```bash
bash /path/to/tistory_auto_post/setup_launchd.sh uninstall
```

### 로그 확인

```bash
cat /path/to/tistory_auto_post/launchd.log
```

### 시간 변경

`com.tistory.autopost.{시간}.plist` 파일의 `<key>Hour</key>` 아래 `<integer>` 값을 원하는 시간으로 수정하세요.

---

## 주제 카테고리

| 카테고리 | 예시 주제 |
|---------|----------|
| 기술 리뷰 | React vs Vue vs Svelte, Bun vs Node vs Deno |
| 개발 도구 | AI 코딩 어시스턴트 비교, API 테스트 도구 비교 |
| 개발 지식 책 | 클린 코드 핵심 요약, DDD 핵심 개념 정리 |
| 개발 이슈 | 개발자 번아웃 예방, AI 시대 개발자 준비 |
| 튜토리얼 | Docker Compose 환경 세팅, JWT 인증 구현 |

---

## Gemini API 무료 한도

- 모델: `gemini-2.0-flash`
- 분당 15회 / 하루 1,500회 요청
- 하루 6편 포스팅해도 여유

---

## 트러블슈팅

### "unexpected alert" 에러
→ 티스토리 임시저장 복구 알림창. 최신 코드에서 자동 처리됩니다.

### Pixabay 이미지가 안 보임
→ 외부 URL 핫링크 차단일 수 있음. Pixabay 정책에 따라 일부 이미지가 표시되지 않을 수 있습니다.

### macOS "Operation not permitted"
→ `cron` 대신 `launchd`를 사용하세요 (`setup_launchd.sh install`).

### selenium 못 찾는 에러
→ `pip3 install selenium --break-system-packages`

### ChromeDriver 버전 에러
→ Chrome 브라우저를 최신으로 업데이트하세요. `webdriver-manager`가 자동으로 맞는 드라이버를 설치합니다.

---

## 라이선스

MIT License
