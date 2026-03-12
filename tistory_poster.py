"""
티스토리 자동 포스팅 스크립트
- 쿠키 기반 로그인 (2단계 인증 지원)
- 이미지 업로드 & 썸네일(대표 이미지) 설정
- 카테고리 자동 분류 (없으면 새로 생성)
- 처음 한 번만 수동 로그인 → 쿠키 저장 → 이후 자동 로그인

사용법:
    python tistory_poster.py --save-cookies   # 처음 1회: 수동 로그인 후 쿠키 저장
    python tistory_poster.py                  # 이후: 자동 포스팅
    python tistory_poster.py --dry-run        # 발행 없이 테스트
"""

import json
import time
import os
import pickle
import argparse
import logging
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementNotInteractableException, StaleElementReferenceException,
    UnexpectedAlertPresentException
)

from content_generator import get_daily_post, get_random_post

# ============================================================
# 로깅 설정
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('tistory_poster.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# 설정 로드
# ============================================================
CONFIG_PATH = Path(__file__).parent / "config.json"
COOKIES_PATH = Path(__file__).parent / "cookies.pkl"
CATEGORIES_CACHE = Path(__file__).parent / "categories_cache.json"


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def send_telegram(message):
    """텔레그램으로 알림 메시지 전송"""
    try:
        config = load_config()
        token = config.get("telegram_bot_token", "")
        chat_id = config.get("telegram_chat_id", "")
        if not token or not chat_id:
            logger.warning("텔레그램 설정이 없어 알림을 건너뜁니다.")
            return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.warning(f"텔레그램 알림 전송 실패: {e}")


# ============================================================
# 메인 포스터 클래스
# ============================================================
class TistoryPoster:
    def __init__(self, config):
        self.config = config
        self.driver = None
        self.wait = None

    def setup_driver(self, headless=True):
        """Chrome WebDriver 설정"""
        options = Options()

        if headless:
            options.add_argument('--headless=new')

        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-gpu')
        options.add_argument('--lang=ko-KR')

        options.add_argument(
            '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        driver_path = self.config.get('chrome_driver_path', 'auto')
        if driver_path == 'auto':
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
            except ImportError:
                service = Service()
        else:
            service = Service(driver_path)

        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 30)
        logger.info("Chrome WebDriver 초기화 완료")

    def save_cookies(self):
        """현재 브라우저 쿠키를 파일로 저장"""
        cookies = self.driver.get_cookies() or []
        with open(COOKIES_PATH, 'wb') as f:
            pickle.dump(cookies, f)
        logger.info(f"쿠키 저장 완료: {COOKIES_PATH} ({len(cookies)}개)")

    def load_cookies(self):
        """저장된 쿠키를 브라우저에 로드"""
        if not COOKIES_PATH.exists():
            return False

        with open(COOKIES_PATH, 'rb') as f:
            cookies = pickle.load(f)

        # 먼저 티스토리 도메인으로 이동 (쿠키 설정을 위해)
        self.driver.get("https://www.tistory.com")
        time.sleep(2)

        for cookie in cookies:
            try:
                cookie.pop('sameSite', None)
                cookie.pop('httpOnly', None)
                self.driver.add_cookie(cookie)
            except Exception:
                pass

        logger.info(f"쿠키 로드 완료 ({len(cookies)}개)")
        return True

    def check_login_status(self):
        """로그인 상태 확인"""
        blog_url = self.config['blog_url']
        manage_url = f"{blog_url}/manage"
        self.driver.get(manage_url)
        time.sleep(3)

        current_url = self.driver.current_url
        logger.info(f"로그인 확인 URL: {current_url}")

        if '/manage' in current_url and 'login' not in current_url:
            logger.info("✅ 로그인 상태 확인됨")
            return True
        else:
            logger.warning("❌ 로그인되지 않은 상태")
            return False

    def kakao_login(self):
        """카카오 아이디/비밀번호로 직접 로그인 (2단계 인증 없음)"""
        tistory_id = self.config.get('tistory_id', '')
        tistory_pw = self.config.get('tistory_pw', '')

        if not tistory_id or not tistory_pw:
            raise Exception("config.json에 tistory_id, tistory_pw가 필요합니다.")

        logger.info("카카오 로그인 시작...")

        # 1) 티스토리 로그인 페이지 이동
        self.driver.get("https://www.tistory.com/auth/login")
        time.sleep(3)

        # 2) 카카오 로그인 버튼 클릭
        try:
            # JS로 "카카오" 텍스트 포함하는 클릭 가능한 요소 찾기
            clicked = self.driver.execute_script("""
                var all = document.querySelectorAll('a, button, div[role="button"], span');
                for (var i = 0; i < all.length; i++) {
                    var el = all[i];
                    var text = el.textContent.trim();
                    if (text.includes('카카오') && el.offsetParent !== null) {
                        el.click();
                        return 'clicked: ' + text.substring(0, 30);
                    }
                }
                return false;
            """)
            if clicked:
                logger.info(f"카카오 로그인 버튼 클릭: {clicked}")
            else:
                self.driver.save_screenshot('error_no_kakao_btn.png')
                raise Exception("카카오 로그인 버튼을 찾을 수 없습니다.")
            time.sleep(3)
        except Exception as e:
            if 'clicked' not in str(e):
                raise

        # 3) 카카오 로그인 페이지에서 아이디/비번 입력
        try:
            # 아이디 입력
            id_input = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "input[name='loginId'], input#loginId, "
                    "input[name='email'], input[type='email'], "
                    "input[name='loginKey'], input[placeholder*='카카오메일']"
                ))
            )
            id_input.clear()
            id_input.send_keys(tistory_id)
            logger.info(f"아이디 입력 완료: {tistory_id[:3]}***")
            time.sleep(0.5)

            # 비밀번호 입력
            pw_input = self.driver.find_element(
                By.CSS_SELECTOR,
                "input[name='password'], input#password, "
                "input[type='password']"
            )
            pw_input.clear()
            pw_input.send_keys(tistory_pw)
            logger.info("비밀번호 입력 완료")
            time.sleep(0.5)

            # 로그인 버튼 클릭
            login_btn = self.driver.find_element(
                By.CSS_SELECTOR,
                "button[type='submit'], button.btn_confirm, "
                "input[type='submit'], button.submit"
            )
            login_btn.click()
            logger.info("로그인 버튼 클릭")
            time.sleep(5)

        except (TimeoutException, NoSuchElementException) as e:
            self.driver.save_screenshot('error_kakao_login_form.png')
            raise Exception(f"카카오 로그인 폼을 찾을 수 없습니다: {e}")

        # 4) 로그인 성공 확인 (최대 30초 대기)
        for i in range(30):
            current_url = self.driver.current_url
            if 'tistory.com' in current_url and 'login' not in current_url and 'kakao' not in current_url:
                logger.info(f"✅ 카카오 로그인 성공! URL: {current_url}")
                return True
            time.sleep(1)

        # 로그인 실패
        current_url = self.driver.current_url
        self.driver.save_screenshot('error_kakao_login_fail.png')
        raise Exception(f"카카오 로그인 실패. 현재 URL: {current_url}")

    def login(self):
        """카카오 아이디/비번으로 자동 로그인"""
        self.kakao_login()

        # 로그인 후 관리 페이지 접근 가능한지 확인
        if not self.check_login_status():
            raise Exception("로그인 후에도 관리 페이지 접근 불가. 아이디/비번을 확인하세요.")

    # ============================================================
    # 카테고리 관리
    # ============================================================
    def get_existing_categories(self):
        """티스토리 관리 페이지에서 기존 카테고리 목록 가져오기 (JS 기반)"""
        blog_url = self.config['blog_url']

        # 글쓰기 페이지에서 카테고리 파싱
        new_post_url = f"{blog_url}/manage/newpost/?type=post"
        self.driver.get(new_post_url)
        time.sleep(5)

        categories = {}

        try:
            # 방법 1: select 요소
            cats = self.driver.execute_script("""
                var results = [];
                // select 박스
                var sel = document.querySelector('#category, select[name="category"]');
                if (sel) {
                    var opts = sel.querySelectorAll('option');
                    opts.forEach(function(o) {
                        if (o.value && o.value !== '0' && o.textContent.trim()) {
                            results.push({name: o.textContent.trim(), value: o.value});
                        }
                    });
                }
                // 커스텀 드롭다운 (티스토리 새 에디터)
                if (results.length === 0) {
                    var items = document.querySelectorAll(
                        '.category-item, [data-category-id], .mce-category li, ' +
                        '.list_category li, .dropdown-category li'
                    );
                    items.forEach(function(item) {
                        var id = item.getAttribute('data-category-id') ||
                                 item.getAttribute('data-value') || '';
                        var name = item.textContent.trim();
                        if (id && name) {
                            results.push({name: name, value: id});
                        }
                    });
                }
                return results;
            """)

            if cats:
                for cat in cats:
                    clean_name = cat['name'].replace("ㄴ ", "").strip()
                    categories[clean_name] = cat['value']
                    logger.info(f"   카테고리 발견: {clean_name} (ID: {cat['value']})")
            else:
                # 방법 2: 페이지 소스에서 카테고리 JSON 추출
                page_source = self.driver.page_source
                import re as _re
                # 티스토리는 카테고리 데이터를 JS 변수에 저장하기도 함
                cat_match = _re.search(r'category["\']?\s*:\s*(\[[\s\S]*?\])', page_source)
                if cat_match:
                    try:
                        cat_data = json.loads(cat_match.group(1))
                        for c in cat_data:
                            name = c.get('name', c.get('label', ''))
                            cid = str(c.get('id', c.get('value', '')))
                            if name and cid:
                                categories[name] = cid
                                logger.info(f"   카테고리 발견 (JS): {name} (ID: {cid})")
                    except json.JSONDecodeError:
                        pass

                if not categories:
                    logger.warning("카테고리를 찾을 수 없습니다. 에디터 HTML 구조를 확인해주세요.")
                    # 디버깅용: 카테고리 관련 요소 덤프
                    debug_info = self.driver.execute_script("""
                        var info = [];
                        var selects = document.querySelectorAll('select');
                        selects.forEach(function(s) {
                            info.push('SELECT: id=' + s.id + ' name=' + s.name +
                                       ' class=' + s.className + ' options=' + s.options.length);
                        });
                        return info;
                    """)
                    for d in (debug_info or []):
                        logger.info(f"   DEBUG: {d}")

        except Exception as e:
            logger.warning(f"카테고리 목록 조회 실패: {e}")

        # 캐시 저장
        try:
            with open(CATEGORIES_CACHE, 'w', encoding='utf-8') as f:
                json.dump(categories, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        logger.info(f"총 {len(categories)}개 카테고리 로드됨")
        return categories

    def _switch_to_content_iframe(self):
        """카테고리 관리 페이지의 콘텐츠 iframe으로 전환"""
        # 티스토리 관리 페이지는 메인 콘텐츠가 iframe 안에 로드됨
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        logger.info(f"   iframe 개수: {len(iframes)}")

        for i, iframe in enumerate(iframes):
            src = iframe.get_attribute("src") or ""
            name = iframe.get_attribute("name") or ""
            iframe_id = iframe.get_attribute("id") or ""
            logger.info(f"   iframe[{i}]: id={iframe_id}, name={name}, src={src[:80]}")

            # 카테고리 관련 iframe 또는 콘텐츠 iframe으로 전환
            if ("category" in src.lower() or "manage" in src.lower() or
                "content" in name.lower() or "main" in name.lower() or
                iframe_id in ("mainFrame", "contentFrame")):
                try:
                    self.driver.switch_to.frame(iframe)
                    logger.info(f"   ✅ iframe[{i}]로 전환 완료")
                    return True
                except Exception as e:
                    logger.info(f"   iframe[{i}] 전환 실패: {e}")

        # iframe이 있지만 매칭 안 된 경우 첫 번째로 시도
        if iframes:
            try:
                self.driver.switch_to.frame(iframes[0])
                logger.info("   ✅ 첫 번째 iframe으로 전환")
                return True
            except Exception:
                pass

        return False

    def _find_and_dump_all_elements(self):
        """현재 context(메인 또는 iframe)의 모든 interactive 요소 덤프"""
        return self.driver.execute_script("""
            var info = [];
            document.querySelectorAll('button, a, input, [role="button"], .btn, [class*="btn"]').forEach(function(el) {
                var rect = el.getBoundingClientRect();
                info.push({
                    tag: el.tagName,
                    id: el.id || '',
                    cls: (el.className || '').toString().substring(0, 100),
                    text: el.textContent.trim().substring(0, 60),
                    type: el.type || '',
                    name: el.name || '',
                    visible: (el.offsetParent !== null || el.offsetWidth > 0),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height)
                });
            });
            return info;
        """) or []

    def create_category(self, category_name):
        """티스토리 카테고리 관리 페이지에서 새 카테고리 생성"""
        blog_url = self.config['blog_url']
        category_url = f"{blog_url}/manage/category"

        logger.info(f"새 카테고리 생성: {category_name}")
        self.driver.get(category_url)
        time.sleep(5)

        # 스크린샷 저장 (디버깅)
        self.driver.save_screenshot('debug_category_page.png')
        logger.info("카테고리 관리 페이지 스크린샷: debug_category_page.png")

        # === 1단계: 메인 프레임에서 요소 탐색 ===
        self.driver.switch_to.default_content()
        logger.info("--- 메인 프레임 요소 탐색 ---")
        main_elements = self._find_and_dump_all_elements()
        for d in main_elements[:20]:
            logger.info(f"   [메인] {d['tag']}: '{d['text']}' "
                       f"(id={d['id']}, cls={d['cls'][:50]}, visible={d['visible']}, "
                       f"w={d['w']}, h={d['h']})")

        # === 2단계: iframe이 있으면 iframe으로 전환 후 탐색 ===
        in_iframe = False
        if self._switch_to_content_iframe():
            in_iframe = True
            time.sleep(2)
            logger.info("--- iframe 내부 요소 탐색 ---")
            iframe_elements = self._find_and_dump_all_elements()
            for d in iframe_elements[:30]:
                logger.info(f"   [iframe] {d['tag']}: '{d['text']}' "
                           f"(id={d['id']}, cls={d['cls'][:50]}, visible={d['visible']}, "
                           f"w={d['w']}, h={d['h']})")

        try:
            # === 3단계: '추가' 버튼 찾기 (JS 기반 - 현재 context에서) ===
            add_btn_info = self.driver.execute_script("""
                var result = null;
                // 방법 A: 클래스명으로 찾기
                var selectors = [
                    'button.btn_add', '.btn_add', '#add-category', '#btn-add-category',
                    'a.btn_add', 'button[class*="add"]', 'a[class*="add"]',
                    '.btn-add', '#addCategory', '.category-add',
                    'button.btn_tit', '.btn_tit'
                ];
                for (var i = 0; i < selectors.length; i++) {
                    var el = document.querySelector(selectors[i]);
                    if (el) {
                        return {found: true, method: 'selector:' + selectors[i],
                                tag: el.tagName, text: el.textContent.trim().substring(0, 40)};
                    }
                }

                // 방법 B: 텍스트로 찾기
                var all = document.querySelectorAll('button, a, span, div, [role="button"]');
                for (var i = 0; i < all.length; i++) {
                    var text = all[i].textContent.trim();
                    if (text === '추가' || text === '카테고리 추가' || text === '새 카테고리' ||
                        text === '+ 추가' || text === '+추가' || text === '+' ||
                        text === 'Add' || text === 'Add Category') {
                        return {found: true, method: 'text:' + text,
                                tag: all[i].tagName, text: text};
                    }
                }
                return {found: false, method: 'none', tag: '', text: ''};
            """)
            logger.info(f"   추가 버튼 탐색 결과: {add_btn_info}")

            # 실제 클릭 시도 (JS click 사용 - element not interactable 우회)
            clicked = self.driver.execute_script("""
                // 방법 A: 셀렉터
                var selectors = [
                    'button.btn_add', '.btn_add', '#add-category', '#btn-add-category',
                    'a.btn_add', 'button[class*="add"]', 'a[class*="add"]',
                    '.btn-add', '#addCategory', '.category-add',
                    'button.btn_tit', '.btn_tit'
                ];
                for (var i = 0; i < selectors.length; i++) {
                    var el = document.querySelector(selectors[i]);
                    if (el) {
                        el.click();
                        return 'clicked:' + selectors[i];
                    }
                }
                // 방법 B: 텍스트
                var all = document.querySelectorAll('button, a, span, div, [role="button"]');
                for (var i = 0; i < all.length; i++) {
                    var text = all[i].textContent.trim();
                    if (text === '추가' || text === '카테고리 추가' || text === '새 카테고리' ||
                        text === '+ 추가' || text === '+추가' || text === '+') {
                        all[i].click();
                        return 'clicked_text:' + text;
                    }
                }
                return false;
            """)

            if not clicked:
                # iframe에 있었으면 메인으로 돌아가서 다시 시도
                if in_iframe:
                    self.driver.switch_to.default_content()
                    clicked = self.driver.execute_script("""
                        var all = document.querySelectorAll('button, a, span, div, [role="button"]');
                        for (var i = 0; i < all.length; i++) {
                            var text = all[i].textContent.trim();
                            if (text === '추가' || text === '카테고리 추가' || text === '+') {
                                all[i].click();
                                return 'main_clicked:' + text;
                            }
                        }
                        return false;
                    """)

            if not clicked:
                logger.error("카테고리 추가 버튼을 찾을 수 없습니다.")
                self.driver.save_screenshot('error_category_no_add_btn.png')
                return False

            logger.info(f"   추가 버튼 클릭: {clicked}")
            time.sleep(2)

            # === 4단계: 이름 입력 ===
            # iframe 상태 다시 확인
            if in_iframe:
                try:
                    self.driver.switch_to.default_content()
                    self._switch_to_content_iframe()
                except Exception:
                    pass

            name_entered = self.driver.execute_script(f"""
                var target = "{category_name}";
                // 가장 최근에 나타난 빈 텍스트 입력 필드 찾기
                var inputs = document.querySelectorAll('input[type="text"], input:not([type])');
                for (var i = inputs.length - 1; i >= 0; i--) {{
                    var inp = inputs[i];
                    if (inp.offsetParent !== null && (inp.value === '' || inp.value === '새 카테고리')) {{
                        inp.value = '';
                        inp.focus();
                        // 네이티브 입력 이벤트 발생
                        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value').set;
                        nativeInputValueSetter.call(inp, target);
                        inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                        inp.dispatchEvent(new Event('change', {{bubbles: true}}));
                        return 'entered:' + inp.className;
                    }}
                }}
                return false;
            """)

            if not name_entered:
                logger.error("카테고리 이름 입력 필드를 찾을 수 없습니다.")
                self.driver.save_screenshot('error_category_no_input.png')
                return False

            logger.info(f"   이름 입력 완료: {name_entered}")
            time.sleep(1)

            # === 5단계: 저장/확인 ===
            # Enter 키 전송
            self.driver.execute_script("""
                var inp = document.querySelector('input:focus');
                if (inp) {
                    inp.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true}));
                    inp.dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true}));
                }
            """)
            time.sleep(1)

            # 저장 버튼 클릭
            saved = self.driver.execute_script("""
                var btns = document.querySelectorAll('button, a, [role="button"]');
                for (var i = 0; i < btns.length; i++) {
                    var text = btns[i].textContent.trim();
                    if ((text === '저장' || text === '확인' || text === '적용' ||
                         text === '변경사항 저장' || text === 'Save') &&
                        btns[i].offsetParent !== null) {
                        btns[i].click();
                        return 'saved:' + text;
                    }
                }
                return false;
            """)

            if saved:
                logger.info(f"   {saved}")
                time.sleep(2)

            logger.info(f"✅ 카테고리 생성 시도 완료: {category_name}")

            # 최종 전체 저장 버튼
            self.driver.execute_script("""
                var btns = document.querySelectorAll('button, a');
                for (var i = 0; i < btns.length; i++) {
                    var text = btns[i].textContent.trim();
                    if ((text === '저장' || text === '변경사항 저장') &&
                        btns[i].offsetParent !== null) {
                        btns[i].click();
                        break;
                    }
                }
            """)
            time.sleep(2)

            return True

        except Exception as e:
            logger.error(f"카테고리 생성 실패: {e}")
            self.driver.save_screenshot('error_category_create.png')
            return False
        finally:
            # 항상 메인 프레임으로 돌아가기
            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass

    def setup_categories(self, category_names):
        """여러 카테고리를 한 번에 생성 (이미 있는 건 건너뜀)"""
        blog_url = self.config['blog_url']

        # 먼저 글쓰기 페이지에서 기존 카테고리 확인
        logger.info("기존 카테고리 확인 중...")
        self.driver.switch_to.default_content()
        self.driver.get(f"{blog_url}/manage/newpost/?type=post")
        time.sleep(5)

        # #category-btn 클릭해서 기존 카테고리 목록 파악
        existing = set()
        try:
            btn = self.driver.find_element(By.CSS_SELECTOR, "#category-btn")
            btn.click()
            time.sleep(1.5)

            items = self.driver.execute_script("""
                var names = [];
                var menuItems = document.querySelectorAll('.mce-menu-item .mce-text');
                menuItems.forEach(function(el) {
                    names.push(el.textContent.trim());
                });
                return names;
            """)
            existing = set(items or [])
            logger.info(f"기존 카테고리: {existing}")

            # 드롭다운 닫기
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"기존 카테고리 조회 실패: {e}")

        # 없는 카테고리만 생성
        created = []
        skipped = []
        failed = []
        for name in category_names:
            if name in existing:
                skipped.append(name)
                logger.info(f"   ✓ 이미 존재: {name}")
            else:
                # create_category 후 항상 메인 프레임으로 복귀
                self.driver.switch_to.default_content()
                if self.create_category(name):
                    created.append(name)
                else:
                    failed.append(name)
                    logger.warning(f"   ✗ 생성 실패: {name}")

        print()
        print("=== 카테고리 설정 결과 ===")
        if skipped:
            print(f"  이미 존재: {', '.join(skipped)}")
        if created:
            print(f"  새로 생성: {', '.join(created)}")
        if failed:
            print(f"  생성 실패: {', '.join(failed)}")
            print()
            print("💡 자동 생성이 실패한 경우, 직접 만들어주세요:")
            print(f"   1. {blog_url}/manage/category 접속")
            print(f"   2. '추가' 클릭 → 카테고리 이름 입력 → 저장")
            print(f"   필요한 카테고리: {', '.join(failed)}")
        if not created and not skipped and not failed:
            print("  변경 없음")
        print()

    def _click_category_btn_and_select(self, category_name):
        """#category-btn 클릭 → 드롭다운에서 카테고리 선택"""
        # 1) #category-btn 클릭해서 드롭다운 열기
        try:
            btn = self.driver.find_element(By.CSS_SELECTOR, "#category-btn")
            btn.click()
            time.sleep(1.5)
            logger.info("카테고리 드롭다운 열림 (#category-btn)")
        except NoSuchElementException:
            logger.info("#category-btn 없음")
            return False

        # 2) 드롭다운에서 모든 항목 텍스트 출력 (디버깅)
        items_info = self.driver.execute_script("""
            var info = [];
            // 드롭다운 내 모든 클릭 가능한 요소 탐색
            var candidates = document.querySelectorAll(
                'li, a, button, span, div'
            );
            candidates.forEach(function(el) {
                var text = el.textContent.trim();
                var isVisible = el.offsetParent !== null;
                // 드롭다운 내 카테고리 항목은 보통 짧은 텍스트
                if (isVisible && text.length > 0 && text.length < 50) {
                    var rect = el.getBoundingClientRect();
                    if (rect.width > 20 && rect.height > 10) {
                        info.push({
                            text: text,
                            tag: el.tagName,
                            cls: el.className.substring(0, 60),
                            id: el.id
                        });
                    }
                }
            });
            return info;
        """)

        # 드롭다운 항목 로깅
        if items_info:
            for item in items_info[:20]:
                logger.info(f"   [드롭다운 항목] {item.get('tag')}: '{item.get('text')}' "
                           f"(class={item.get('cls', '')}, id={item.get('id', '')})")

        # 3) 카테고리 이름과 매칭되는 항목 클릭
        # 티스토리 에디터: div.mce-menu-item 내부의 span.mce-text에 카테고리명
        clicked = self.driver.execute_script(f"""
            var target = "{category_name}";

            // 방법 A: mce-menu-item 직접 탐색 (티스토리 에디터 전용)
            var menuItems = document.querySelectorAll('.mce-menu-item, [id^="category-item-"]');
            for (var i = 0; i < menuItems.length; i++) {{
                var el = menuItems[i];
                var textSpan = el.querySelector('.mce-text');
                var text = textSpan ? textSpan.textContent.trim() : el.textContent.trim();
                if (text === target) {{
                    el.click();
                    return "mce:" + text;
                }}
            }}

            // 방법 B: 모든 보이는 요소 탐색 (폴백)
            var all = document.querySelectorAll('li, a, button, span, div');
            for (var i = 0; i < all.length; i++) {{
                var el = all[i];
                if (el.offsetParent === null) continue;
                // 직접 텍스트만 체크 (하위 요소 제외)
                var directText = '';
                el.childNodes.forEach(function(n) {{
                    if (n.nodeType === 3) directText += n.textContent;
                }});
                directText = directText.trim();
                var fullText = el.textContent.trim();
                if (directText === target || fullText === target) {{
                    el.click();
                    return "fallback:" + fullText;
                }}
            }}

            return false;
        """)

        if clicked:
            logger.info(f"✅ 카테고리 선택 완료: {category_name} (결과: {clicked})")
            time.sleep(0.5)
            return True

        # 드롭다운 닫기 (Escape)
        try:
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except Exception:
            pass

        return False

    def select_category(self, category_name):
        """글 작성 페이지에서 카테고리 선택"""
        if not category_name:
            logger.info("카테고리 미지정 - 기본값으로 진행")
            return False

        logger.info(f"카테고리 선택 시도: {category_name}")

        # === 방법 1: #category-btn 버튼 드롭다운 (티스토리 새 에디터) ===
        if self._click_category_btn_and_select(category_name):
            return True

        # === 방법 2: select 요소 (구 에디터 호환) ===
        try:
            select_el = self.driver.find_element(
                By.CSS_SELECTOR, "#category, select[name='category']"
            )
            options = select_el.find_elements(By.TAG_NAME, "option")
            for opt in options:
                opt_text = opt.text.strip().replace("ㄴ ", "").strip()
                if opt_text == category_name:
                    select_obj = Select(select_el)
                    select_obj.select_by_value(opt.get_attribute("value"))
                    logger.info(f"✅ 카테고리 선택 (select): {category_name}")
                    return True
        except NoSuchElementException:
            pass
        except Exception as e:
            logger.info(f"select 방법 실패: {e}")

        # === 카테고리가 없는 경우 ===
        # 자동 생성은 너무 불안정 → 경고만 출력하고 기본값으로 진행
        logger.warning(f"카테고리 '{category_name}'을 찾을 수 없습니다.")
        logger.warning("팁: 티스토리 관리 > 카테고리 관리에서 먼저 카테고리를 만들어주세요.")
        logger.warning("기본 카테고리(카테고리 없음)로 포스팅합니다.")
        return False

    # ============================================================
    # 이미지 업로드 & 썸네일 설정
    # ============================================================
    def _find_image_file_input(self):
        """에디터의 이미지 업로드 file input 찾기 (hidden 포함)"""
        # hidden file input을 보이게 만들기
        self.driver.execute_script("""
            document.querySelectorAll('input[type="file"]').forEach(function(inp) {
                inp.style.display = 'block';
                inp.style.visibility = 'visible';
                inp.style.height = '1px';
                inp.style.width = '1px';
                inp.style.opacity = '0.01';
                inp.style.position = 'fixed';
                inp.style.top = '-100px';
            });
        """)
        time.sleep(0.5)

        file_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
        for fi in file_inputs:
            accept = fi.get_attribute('accept') or ''
            if 'image' in accept:
                return fi

        # image accept가 없으면 첫 번째 file input 반환
        return file_inputs[0] if file_inputs else None

    def _upload_single_image(self, filepath):
        """단일 이미지를 에디터에 업로드하고 Tistory CDN URL 반환"""
        abs_path = os.path.abspath(filepath)
        if not os.path.exists(abs_path):
            logger.warning(f"이미지 파일 없음: {abs_path}")
            return None

        # 현재 에디터 내 이미지 수
        before_count = self.driver.execute_script("""
            var e = tinymce.get('editor-tistory');
            return e ? e.dom.select('img').length : 0;
        """) or 0

        file_input = self._find_image_file_input()
        if not file_input:
            logger.warning("파일 업로드 input을 찾을 수 없습니다.")
            return None

        try:
            file_input.send_keys(abs_path)
        except Exception as e:
            logger.warning(f"파일 전송 실패: {e}")
            return None

        # 업로드 완료 대기 (최대 15초)
        uploaded_url = None
        for _ in range(30):
            time.sleep(0.5)
            after_count = self.driver.execute_script("""
                var e = tinymce.get('editor-tistory');
                return e ? e.dom.select('img').length : 0;
            """) or 0

            if after_count > before_count:
                uploaded_url = self.driver.execute_script(f"""
                    var e = tinymce.get('editor-tistory');
                    if (!e) return null;
                    var imgs = e.dom.select('img');
                    return imgs.length > {before_count} ? imgs[imgs.length - 1].src : null;
                """)
                break

        if uploaded_url:
            logger.info(f"   ✅ 이미지 업로드: {uploaded_url[:80]}...")
        else:
            logger.warning(f"   ⚠️ 이미지 업로드 감지 실패: {filepath}")

        return uploaded_url

    def upload_images_and_replace_urls(self, html_content, image_map):
        """
        이미지를 Tistory에 업로드하고 본문 HTML의 외부 URL을 CDN URL로 교체
        image_map: {외부URL: 로컬파일경로}
        """
        if not image_map:
            return html_content

        logger.info(f"이미지 {len(image_map)}개 Tistory 업로드 시작...")

        # 에디터를 비운 상태에서 이미지 업로드
        self.driver.execute_script("""
            var e = tinymce.get('editor-tistory');
            if (e) e.setContent('');
        """)
        time.sleep(0.5)

        url_replacements = {}  # 외부URL → Tistory CDN URL

        for ext_url, local_path in image_map.items():
            if not local_path or not os.path.exists(local_path):
                continue

            tistory_url = self._upload_single_image(local_path)
            if tistory_url:
                url_replacements[ext_url] = tistory_url

            time.sleep(1)  # 업로드 간격

        # 에디터 비우기 (업로드된 임시 이미지 제거)
        self.driver.execute_script("""
            var e = tinymce.get('editor-tistory');
            if (e) e.setContent('');
        """)
        time.sleep(0.5)

        # HTML 내 외부 URL을 Tistory CDN URL로 교체
        result_html = html_content
        replaced_count = 0
        for ext_url, cdn_url in url_replacements.items():
            if ext_url in result_html:
                result_html = result_html.replace(ext_url, cdn_url)
                replaced_count += 1

        logger.info(f"이미지 URL 교체: {replaced_count}/{len(image_map)}개 완료")
        return result_html

    def upload_thumbnail(self, thumbnail_path):
        """대표 이미지(썸네일) 설정 - Tistory의 대표 이미지 업로드 기능 사용"""
        if not thumbnail_path or not os.path.exists(thumbnail_path):
            logger.info("썸네일 파일 없음 - 본문 첫 이미지가 자동 대표 이미지가 됩니다.")
            return False

        abs_path = os.path.abspath(thumbnail_path)

        try:
            # 방법 1: 대표 이미지 설정 버튼/영역 찾기
            thumb_btn = self.driver.execute_script("""
                // 대표 이미지 관련 요소 찾기
                var selectors = [
                    '#representImgBtn', '.btn_thumb', '.thumb-upload',
                    '[class*="represent"]', '[class*="thumb"]',
                    'button[data-type="represent"]'
                ];
                for (var i = 0; i < selectors.length; i++) {
                    var el = document.querySelector(selectors[i]);
                    if (el && el.offsetParent !== null) return el;
                }
                // 텍스트로 찾기
                var btns = document.querySelectorAll('button, a, span, label');
                for (var i = 0; i < btns.length; i++) {
                    var text = btns[i].textContent.trim();
                    if (text.includes('대표') || text.includes('썸네일') ||
                        text.includes('커버')) {
                        return btns[i];
                    }
                }
                return null;
            """)

            if thumb_btn:
                self.driver.execute_script("arguments[0].click();", thumb_btn)
                time.sleep(2)

                # 썸네일 전용 file input 찾기
                thumb_input = self._find_image_file_input()
                if thumb_input:
                    thumb_input.send_keys(abs_path)
                    time.sleep(3)
                    logger.info("✅ 대표 이미지 업로드 완료")
                    return True

            # 방법 2: 대표 이미지 전용 file input 직접 찾기
            self.driver.execute_script("""
                document.querySelectorAll('input[type="file"]').forEach(function(inp) {
                    inp.style.display = 'block';
                    inp.style.visibility = 'visible';
                    inp.style.height = '1px';
                    inp.style.width = '1px';
                    inp.style.opacity = '0.01';
                    inp.style.position = 'fixed';
                    inp.style.top = '-100px';
                });
            """)
            time.sleep(0.3)

            # 모든 file input 시도 (가장 마지막이 보통 대표 이미지용)
            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
            if len(file_inputs) >= 2:
                # 두 번째 이상의 file input이 대표 이미지용일 가능성
                for fi in reversed(file_inputs):
                    try:
                        fi.send_keys(abs_path)
                        time.sleep(3)
                        logger.info("✅ 대표 이미지 업로드 시도 완료")
                        return True
                    except Exception:
                        continue

            logger.info("대표 이미지 업로드 위치 미발견 - 본문 첫 이미지가 자동 대표 이미지가 됩니다.")
            return False

        except Exception as e:
            logger.warning(f"대표 이미지 업로드 실패: {e}")
            logger.info("본문 첫 이미지가 자동 대표 이미지로 설정됩니다.")
            return False

    # ============================================================
    # 글 작성 & 발행
    # ============================================================
    def create_post(self, title, html_content, category=None,
                    thumbnail=None, image_files=None, image_map=None,
                    dry_run=False):
        """새 글 작성 및 발행"""
        blog_url = self.config['blog_url']
        new_post_url = f"{blog_url}/manage/newpost/?type=post"

        logger.info(f"글 작성 페이지 이동: {new_post_url}")
        self.driver.get(new_post_url)
        time.sleep(3)

        # === 임시저장 글 복구 알림창 처리 ===
        # "저장된 글이 있습니다. 이어서 작성하시겠습니까?" 알림이 뜰 수 있음
        try:
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            logger.info(f"알림창 감지: {alert_text}")
            alert.dismiss()  # "아니오" 클릭 → 새 글 작성
            logger.info("알림창 닫음 (새 글 작성 선택)")
            time.sleep(2)
        except Exception:
            logger.info("임시저장 알림창 없음 → 정상 진행")

        logger.info(f"현재 URL: {self.driver.current_url}")

        # === 1. 카테고리 선택 ===
        if category:
            # 먼저 페이지에 어떤 카테고리 관련 요소가 있는지 디버깅
            try:
                debug = self.driver.execute_script("""
                    var info = [];
                    // select 요소들
                    document.querySelectorAll('select').forEach(function(s) {
                        info.push('SELECT: id=' + s.id + ' name=' + s.name +
                                   ' options=' + s.options.length);
                    });
                    // 카테고리 관련 클래스 가진 요소
                    var cats = document.querySelectorAll('[class*="categor"], [id*="categor"]');
                    cats.forEach(function(c) {
                        info.push('CAT: tag=' + c.tagName + ' id=' + c.id +
                                   ' class=' + c.className.substring(0, 80));
                    });
                    return info;
                """)
                for d in (debug or []):
                    logger.info(f"   [카테고리 탐색] {d}")
            except Exception:
                pass

            self.select_category(category)
            time.sleep(1)

            # 카테고리 선택 과정에서 페이지가 바뀌었을 수 있으므로 확인
            if '/manage/newpost' not in self.driver.current_url:
                logger.info("글쓰기 페이지로 복귀 중...")
                self.driver.get(new_post_url)
                time.sleep(5)

        # === 2. 제목 입력 ===
        try:
            title_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#post-title-inp"))
            )
            title_input.clear()
            title_input.send_keys(title)
            logger.info(f"제목 입력 완료: {title}")
            time.sleep(1)
        except TimeoutException:
            logger.error("제목 입력 필드를 찾을 수 없습니다.")
            self.driver.save_screenshot('error_title.png')
            logger.info("에러 스크린샷: error_title.png")
            raise

        # === 3. TinyMCE 에디터 로드 대기 ===
        try:
            self.wait.until(
                lambda d: d.execute_script(
                    "return typeof tinymce !== 'undefined' && tinymce.editors.length > 0"
                )
            )
            time.sleep(1)
        except TimeoutException:
            logger.error("TinyMCE 에디터를 찾을 수 없습니다.")
            raise

        # === 4. 이미지 Tistory 업로드 & URL 교체 (로컬 파일이 있는 경우만) ===
        final_content = html_content
        if image_map:
            # 실제 존재하는 로컬 파일만 필터링
            valid_map = {k: v for k, v in image_map.items() if v and os.path.exists(v)}
            if valid_map:
                try:
                    final_content = self.upload_images_and_replace_urls(html_content, valid_map)
                except Exception as e:
                    logger.warning(f"이미지 업로드 실패, 외부 URL로 진행: {e}")
                    final_content = html_content
            else:
                logger.info("로컬 이미지 파일 없음 - 외부 URL로 진행")

        # === 5. HTML 콘텐츠 삽입 ===
        try:
            # arguments[0]으로 전달하면 JS 이스케이프 문제 없음
            result = self.driver.execute_script("""
                var editor = tinymce.get('editor-tistory');
                if (editor) {
                    editor.setContent(arguments[0]);
                    editor.save();
                    return editor.getContent().length;
                }
                return -1;
            """, final_content)

            logger.info(f"본문 HTML 삽입 완료 (원본: {len(html_content)}자 → 에디터: {result}자)")

            # 삽입 검증
            if result and result > 0 and result < len(final_content) * 0.3:
                logger.warning(f"⚠️ 본문이 잘렸을 수 있습니다! 원본: {len(final_content)}자, 에디터: {result}자")

            time.sleep(1)

        except Exception as e:
            logger.error(f"본문 삽입 실패: {e}")
            raise

        # === 6. 썸네일 업로드 (대표 이미지) ===
        if thumbnail:
            self.upload_thumbnail(thumbnail)

        if dry_run:
            logger.info("[DRY RUN] 발행하지 않고 종료합니다.")
            self.driver.save_screenshot('dry_run_preview.png')
            logger.info("미리보기 스크린샷 저장: dry_run_preview.png")
            return True

        # === 5. 완료(발행) 버튼 클릭 ===
        try:
            publish_btn = self.wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "#publish-layer-btn, .btn_publish, .btn-publish"
                ))
            )
            publish_btn.click()
            time.sleep(2)

            # 공개 설정
            try:
                public_radio = self.driver.find_element(
                    By.CSS_SELECTOR, "#open20, input[value='20'], .radio_public"
                )
                if not public_radio.is_selected():
                    public_radio.click()
                    time.sleep(0.5)
            except NoSuchElementException:
                logger.warning("공개 설정 라디오 버튼 미발견. 기본값으로 진행.")

            # 최종 발행 버튼
            confirm_btn = self.wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    ".btn-publish, #publish-btn, button.btn_ok"
                ))
            )
            confirm_btn.click()
            time.sleep(3)

            logger.info(f"✅ 글 발행 완료: {title}")
            logger.info(f"   카테고리: {category or '없음'}")
            logger.info(f"   썸네일: {'있음' if thumbnail else '없음'}")
            return True

        except TimeoutException:
            logger.error("발행 버튼을 찾을 수 없습니다.")
            self.driver.save_screenshot('error_publish.png')
            raise

    def close(self):
        """브라우저 종료"""
        if self.driver:
            self.driver.quit()
            logger.info("브라우저 종료")


# ============================================================
# 메인 실행
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='티스토리 자동 포스팅')
    parser.add_argument('--random', action='store_true',
                        help='랜덤 글 선택')
    parser.add_argument('--dry-run', action='store_true',
                        help='발행 없이 테스트')
    parser.add_argument('--no-headless', action='store_true',
                        help='브라우저 화면 표시')
    parser.add_argument('--list-categories', action='store_true',
                        help='기존 카테고리 목록 조회')
    parser.add_argument('--setup-categories', action='store_true',
                        help='필요한 카테고리 자동 생성 (없는 것만)')
    args = parser.parse_args()

    config = load_config()
    poster = TistoryPoster(config)

    try:
        # === 카테고리 목록 조회 모드 ===
        if args.list_categories:
            poster.setup_driver(headless=True)
            poster.login()
            cats = poster.get_existing_categories()
            print()
            print("=== 기존 카테고리 목록 ===")
            for name, cat_id in cats.items():
                print(f"  - {name} (ID: {cat_id})")
            if not cats:
                print("  (카테고리 없음)")
            return

        # === 카테고리 자동 생성 모드 ===
        if args.setup_categories:
            from content_generator import TISTORY_CATEGORY_MAP
            # 매핑에 있는 모든 고유 카테고리 이름
            needed = list(set(TISTORY_CATEGORY_MAP.values()))
            print(f"생성할 카테고리: {needed}")
            poster.setup_driver(headless=False)  # 화면 보이게
            poster.login()
            poster.setup_categories(needed)
            return

        # === 자동 포스팅 모드 ===
        headless = not args.no_headless and config.get('headless', True)

        # 글 생성 (콘텐츠 + 이미지 + 카테고리 정보)
        if args.random:
            post = get_random_post()
        else:
            post = get_daily_post()

        if post is None:
            logger.info("🚫 AI 글 생성 실패 — 이번 실행은 발행을 건너뜁니다.")
            send_telegram("🚫 <b>글 생성 실패</b>\nAI 글 생성에 실패하여 이번 실행을 건너뜁니다.")
            return

        logger.info(f"=== 티스토리 자동 포스팅 시작 ({datetime.now().strftime('%Y-%m-%d %H:%M')}) ===")
        logger.info(f"선택된 글: {post['title']}")
        logger.info(f"카테고리: {post.get('category', '미지정')}")
        logger.info(f"썸네일: {post.get('thumbnail', '없음')}")
        logger.info(f"이미지 파일: {len(post.get('image_files', []))}개")

        poster.setup_driver(headless=headless)
        poster.login()
        poster.create_post(
            title=post['title'],
            html_content=post['content'],
            category=post.get('category'),
            thumbnail=post.get('thumbnail'),
            image_files=post.get('image_files'),
            image_map=post.get('image_map', {}),
            dry_run=args.dry_run
        )

        logger.info("=== 포스팅 완료 ===")
        send_telegram(
            f"✅ <b>포스팅 성공</b>\n"
            f"제목: {post['title']}\n"
            f"카테고리: {post.get('category', '미지정')}\n"
            f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

    except Exception as e:
        logger.error(f"❌ 포스팅 실패: {e}")
        send_telegram(f"❌ <b>포스팅 실패</b>\n에러: {e}")
        try:
            if poster.driver and poster.driver.window_handles:
                poster.driver.save_screenshot('error_screenshot.png')
                logger.info("에러 스크린샷 저장: error_screenshot.png")
        except:
            logger.warning("스크린샷 저장 실패 (창이 이미 닫힘)")
        raise
    finally:
        poster.close()


if __name__ == "__main__":
    main()
