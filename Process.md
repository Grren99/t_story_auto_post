# Process: 티스토리 자동 포스팅 작동 원리

이 문서는 `python3 tistory_poster.py` 실행 시 내부에서 어떤 일이 일어나는지 단계별로 설명합니다.

---

## 전체 흐름 요약

```
[1] 콘텐츠 생성 (content_generator.py)
    ├── 카테고리 & 주제 선택
    ├── Gemini API로 글 생성
    ├── Pixabay 이미지 검색 & 삽입
    └── 최종 HTML 반환

[2] 티스토리 포스팅 (tistory_poster.py)
    ├── Chrome WebDriver 초기화
    ├── 카카오 로그인
    ├── 글쓰기 페이지 이동
    ├── 임시저장 알림 처리
    ├── 카테고리 선택
    ├── 제목 입력
    ├── TinyMCE 에디터에 본문 삽입
    ├── 발행 버튼 클릭
    └── 브라우저 종료
```

---

## 1단계: 콘텐츠 생성 (`content_generator.py`)

### 1-1. 카테고리 & 주제 선택

프로그램에는 5개 카테고리와 각각 10~15개의 주제가 하드코딩되어 있습니다.

```
카테고리:
├── 기술 리뷰     → "React vs Vue vs Svelte", "Bun vs Node vs Deno" 등
├── 개발 도구     → "AI 코딩 어시스턴트 비교", "터미널 커스터마이징" 등
├── 개발 지식 책  → "클린 코드 핵심 요약", "DDD 핵심 개념 정리" 등
├── 개발 이슈     → "개발자 번아웃 예방", "AI 시대 개발자 준비" 등
└── 튜토리얼     → "Docker Compose 세팅", "JWT 인증 구현" 등
```

선택 과정:
1. 카테고리를 랜덤으로 선택
2. 해당 카테고리 내에서 주제를 랜덤으로 선택
3. `post_history.json`에 기록된 이전 주제는 제외 (중복 방지)
4. 카테고리 이름을 티스토리 실제 카테고리명으로 매핑

```
내부 카테고리명          →  티스토리 카테고리명
"기술 리뷰"             →  "기술 리뷰"
"개발 도구"             →  "개발 도구"
"개발 책 리뷰"          →  "개발 지식 책"
"이슈 분석"             →  "개발 이슈"
"튜토리얼"              →  "튜토리얼"
```

### 1-2. Gemini API로 글 생성

선택된 주제를 바탕으로 Google Gemini API (`gemini-2.0-flash`)에 프롬프트를 보냅니다.

프롬프트 핵심:
- IT/개발 블로그 글 작성 요청
- HTML 태그로 포맷팅 (`<h2>`, `<h3>`, `<p>`, `<pre><code>` 등)
- 실무 경험 기반의 자연스러운 한국어 톤
- `maxOutputTokens: 8192`로 긴 글 생성

반환값: 제목 + HTML 본문 (약 6,000~9,000자)

### 1-3. Pixabay 이미지 검색 & 삽입

1. 글의 키워드를 추출
2. Pixabay API로 관련 이미지 검색 (영문 키워드)
3. 검색 결과에서 최대 3장의 이미지 URL 확보
4. HTML `<img>` 태그로 본문 중간에 삽입

이미지는 다운로드하지 않고 Pixabay의 외부 URL(`webformatURL`, 640px)을 직접 사용합니다. 각 이미지 아래에 Pixabay 출처 크레딧이 포함됩니다.

### 1-4. 최종 출력

```python
{
    "title": "생성된 글 제목",
    "content": "<h2>...</h2><p>...</p>...",      # 이미지 포함 HTML
    "category": "기술 리뷰",                       # 티스토리 카테고리명
    "thumbnail": None,                             # 현재 미사용
    "image_files": [],                             # 현재 미사용
    "image_map": {}                                # 현재 미사용
}
```

---

## 2단계: 티스토리 포스팅 (`tistory_poster.py`)

### 2-1. Chrome WebDriver 초기화

```
headless 모드 여부 확인 (config.json의 headless 값)
    ├── headless=true  → 브라우저 숨겨서 백그라운드 실행
    └── headless=false → 브라우저 화면 표시

webdriver-manager가 Chrome 버전에 맞는 ChromeDriver를 자동 설치/캐시
```

주요 Chrome 옵션:
- `--headless=new`: 백그라운드 실행
- `--no-sandbox`: 샌드박스 비활성화
- `--disable-dev-shm-usage`: 공유 메모리 제한 해제
- `--disable-gpu`: GPU 렌더링 비활성화

### 2-2. 카카오 로그인

쿠키 없이 매번 카카오 아이디/비밀번호로 직접 로그인합니다.

```
[1] tistory.com/auth/login 이동
[2] "카카오계정으로 로그인" 버튼 클릭 (JS로 텍스트 매칭)
[3] 카카오 로그인 페이지에서:
    ├── 이메일 입력 (config.json의 tistory_id)
    ├── 비밀번호 입력 (config.json의 tistory_pw)
    └── 로그인 버튼 클릭
[4] 최대 30초 대기하며 리다이렉트 확인
[5] tistory.com/manage 접근 가능하면 로그인 성공
```

> 2단계 인증이 켜져있으면 자동 로그인이 불가능합니다.

### 2-3. 글쓰기 페이지 이동

```
[1] {blog_url}/manage/newpost/?type=post 이동
[2] 3초 대기
[3] 임시저장 알림창 체크
    ├── 알림 있음 → alert.dismiss() (아니오 클릭 → 새 글 작성)
    └── 알림 없음 → 그냥 진행
```

티스토리는 이전에 작성 중이던 글이 있으면 "저장된 글이 있습니다. 이어서 작성하시겠습니까?" 알림을 띄웁니다. 이걸 자동으로 닫아줍니다.

### 2-4. 카테고리 선택

```
[1] #category-btn (카테고리 드롭다운 버튼) 클릭
[2] 드롭다운 메뉴에서 span.mce-text 요소들을 탐색
[3] 텍스트가 일치하는 카테고리 항목 클릭
[4] 카테고리가 없으면 → /manage/category 페이지에서 자동 생성
```

### 2-5. 제목 입력

```
[1] #post-title-inp 요소 대기
[2] 기존 내용 클리어
[3] Gemini가 생성한 제목 입력 (send_keys)
```

### 2-6. TinyMCE 에디터에 본문 삽입

티스토리의 글쓰기 에디터는 TinyMCE 기반입니다. JavaScript를 통해 본문을 삽입합니다.

```javascript
// Selenium execute_script로 실행
var editor = tinymce.get('editor-tistory');
editor.setContent(arguments[0]);  // arguments[0] = HTML 본문
editor.save();
```

핵심: 본문은 `arguments[0]` 파라미터로 전달합니다. f-string이나 JS 템플릿 리터럴을 사용하면 특수문자(백틱, 따옴표 등)에서 깨질 수 있기 때문입니다.

### 2-7. 발행

```
[1] 발행 버튼 클릭 (#publish-layer-btn 또는 유사 선택자)
[2] 공개 설정 확인 (기본: 공개)
[3] 최종 발행 확인 버튼 클릭 (.btn-publish)
[4] 3초 대기 후 발행 완료 로그
```

### 2-8. 발행 이력 기록

발행이 성공하면 `post_history.json`에 기록:

```json
{
    "2026-03-11": {
        "title": "발행된 글 제목",
        "category": "기술 리뷰",
        "topic": "Next.js App Router 도입 후기"
    }
}
```

다음 실행 시 이미 발행한 주제는 선택에서 제외됩니다.

### 2-9. 브라우저 종료

`driver.quit()`으로 Chrome 프로세스를 완전히 종료합니다.

---

## 스케줄링 작동 방식

### macOS launchd

`setup_launchd.sh install` 실행 시:

```
[1] 기존 cron 스케줄 삭제
[2] com.tistory.autopost.{9~14}.plist 파일을 ~/Library/LaunchAgents/ 에 복사
[3] launchctl load로 각 plist 등록
```

등록된 plist는 macOS가 지정된 시간에 자동으로 `python3 tistory_poster.py`를 실행합니다.

```
매일 9:00  → 1번째 글 자동 생성 & 발행
매일 10:00 → 2번째 글
매일 11:00 → 3번째 글
매일 12:00 → 4번째 글
매일 13:00 → 5번째 글
매일 14:00 → 6번째 글
```

각 실행은 독립적이며, 매번 새로운 Chrome 인스턴스를 띄우고, 로그인하고, 포스팅한 뒤 종료합니다.

로그는 `launchd.log`에 누적됩니다.

---

## 에러 처리

| 상황 | 처리 |
|------|------|
| 로그인 실패 | 스크린샷 저장 + 에러 로그 + 프로세스 종료 |
| 카테고리 없음 | 자동 생성 시도 (실패 시 "카테고리 없음"으로 발행) |
| TinyMCE 로드 실패 | 최대 20초 대기 후 타임아웃 에러 |
| 임시저장 알림 | 자동으로 "아니오" 클릭 |
| 발행 버튼 못 찾음 | 스크린샷 저장 + 에러 로그 |
| 네트워크 에러 | 프로세스 종료 (다음 스케줄에서 재시도) |
