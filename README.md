# Naver Cafe 채용공고 스크래퍼

네이버 카페 [공준모(공무원/공기업 준비 모임)](https://cafe.naver.com/studentstudyhard)의 채용공고 게시판에서 특정 키워드(예: "전산", "IT")가 포함된 채용 정보를 자동으로 수집하는 CLI 도구입니다.

수집된 공고는 **기관명, 공고명, 접수 마감일, 원문 링크**를 포함한 표 형태로 정리되어 파일로 저장됩니다.

---

## 목차

- [미리보기](#미리보기)
- [요구사항](#요구사항)
- [설치](#설치)
- [사용법](#사용법)
  - [1단계: 네이버 로그인 (최초 1회)](#1단계-네이버-로그인-최초-1회)
  - [2단계: 스크래핑 실행](#2단계-스크래핑-실행)
- [CLI 옵션](#cli-옵션)
- [환경변수 설정](#환경변수-설정)
- [출력 결과](#출력-결과)
- [축약 실행 (run.sh)](#축약-실행-runsh)
- [Shell Alias 설정](#shell-alias-설정)
- [대상 게시판](#대상-게시판)
- [동작 방식](#동작-방식)
- [프로젝트 구조](#프로젝트-구조)
- [문제 해결](#문제-해결)
- [자주 묻는 질문](#자주-묻는-질문)

---

## 미리보기

```
$ python3 main.py scrape --keywords "전산,IT" --today

10:32:15 | INFO     | 스크래핑 시작: 카페=studentstudyhard
10:32:15 | INFO     | 키워드=[전산, IT], 페이지=2
10:32:15 | INFO     | Step 1/4: 게시판 탐색 중...
10:32:18 | INFO     | 3개 게시판 발견
10:32:18 | INFO     | Step 2/4: 게시글 목록 수집 중...
10:32:22 | INFO     | [중앙공기업] '전산, IT' 포함 게시글 5건 발견
10:32:25 | INFO     | Step 3/4: 게시글 상세 정보 추출 중...
10:32:40 | INFO     | Step 4/4: 결과 저장 중...
10:32:40 | SUCCESS  | 스크래핑 완료!
```

출력 예시 (`data/2026-03-03.csv`):

```csv
기관분류,기관명,공고명,접수기한,링크
중앙공기업,한국철도공사,한국철도공사 전산직 채용 (~3.11),~3.11,https://cafe.naver.com/...
지방공기업,서울교통공사,서울교통공사 IT직 채용 (~3.15),~3.15,https://cafe.naver.com/...
```

---

## 요구사항

| 항목 | 버전 | 비고 |
|------|------|------|
| Python | 3.10 이상 | `python3 --version`으로 확인 |
| pip | 최신 권장 | `pip install --upgrade pip` |
| OS | macOS / Linux / Windows | Playwright가 지원하는 모든 OS |
| 네이버 계정 | - | 공준모 카페 가입 필수 |

---

## 설치

### 1. 저장소 클론

```bash
git clone https://github.com/<your-username>/mento-duke.git
cd mento-duke
```

### 2. Python 가상환경 생성 및 활성화

```bash
# 가상환경 생성
python3 -m venv .venv

# 활성화 (macOS / Linux)
source .venv/bin/activate

# 활성화 (Windows PowerShell)
.venv\Scripts\Activate.ps1

# 활성화 (Windows CMD)
.venv\Scripts\activate.bat
```

> 활성화되면 프롬프트 앞에 `(.venv)`가 표시됩니다.

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

설치되는 주요 패키지:

| 패키지 | 역할 |
|--------|------|
| `playwright` | 브라우저 자동화 (로그인, DOM 파싱) |
| `httpx` | 비동기 HTTP 클라이언트 (REST API 호출) |
| `pandas` | 데이터 처리 및 CSV 내보내기 |
| `pydantic` / `pydantic-settings` | 설정 관리 및 데이터 모델 |
| `typer` | CLI 인터페이스 |
| `loguru` | 로깅 |
| `python-dotenv` | `.env` 파일 로드 |

### 4. Playwright 브라우저 설치

```bash
playwright install chromium
```

> Chromium 브라우저 바이너리를 다운로드합니다 (약 150MB). 인터넷 연결이 필요합니다.

### 5. 환경변수 설정 (선택사항)

```bash
cp .env.example .env
```

기본값 그대로 사용해도 됩니다. 커스텀이 필요한 경우 [환경변수 설정](#환경변수-설정) 섹션을 참고하세요.

### 설치 확인

```bash
python3 main.py --help
```

아래와 같이 출력되면 설치가 완료된 것입니다:

```
Usage: main.py [OPTIONS] COMMAND [ARGS]...

  네이버 카페 채용공고 스크래퍼

Options:
  --help  Show this message and exit.

Commands:
  login   Open browser for manual Naver login and save cookies.
  scrape  Run the full scraping pipeline.
```

---

## 사용법

### 1단계: 네이버 로그인 (최초 1회)

```bash
python3 main.py login
```

**과정:**
1. Chromium 브라우저가 자동으로 열리고 네이버 로그인 페이지로 이동합니다.
2. 아이디/비밀번호를 **직접 입력**하여 로그인합니다.
3. 로그인이 감지되면 쿠키가 `data/cookies.json`에 자동 저장됩니다.
4. 브라우저가 자동으로 닫힙니다.

> **참고:** 로그인 대기 시간은 최대 5분입니다. 5분 내에 로그인을 완료해주세요.
>
> **재로그인이 필요한 경우:** 쿠키가 만료되어 스크래핑이 실패하면 `login` 명령을 다시 실행하세요.

### 2단계: 스크래핑 실행

```bash
# 기본 실행 (headless 모드, "전산" 키워드, 2페이지)
python3 main.py scrape

# 여러 키워드 동시 검색
python3 main.py scrape --keywords "전산,IT"

# 오늘 올라온 공고만 필터링
python3 main.py scrape --keywords "전산,IT" --today

# 특정 기간의 공고 조회
python3 main.py scrape --keywords "전산,IT" --from 2026-03-01 --to 2026-03-05

# 특정 날짜 이후 공고 조회 (오늘까지)
python3 main.py scrape --keywords "전산,IT" --from 2026-03-01

# 브라우저 화면을 보면서 실행 (디버깅에 유용)
python3 main.py scrape --keywords "전산,IT" --headed

# 3페이지까지 탐색
python3 main.py scrape --pages 3

# 옵션 조합
python3 main.py scrape --keywords "전산,IT" --headed --pages 3 --today
```

실행이 완료되면 `data/` 폴더에 결과 파일이 생성됩니다.

---

## CLI 옵션

### `login` 명령

```bash
python3 main.py login
```

옵션 없이 실행합니다. 브라우저가 열리고 수동으로 네이버에 로그인합니다.

### `scrape` 명령

```bash
python3 main.py scrape [옵션]
```

| 옵션 | 축약 | 설명 | 기본값 | 예시 |
|------|------|------|--------|------|
| `--keywords` | `-k` | 쉼표로 구분한 검색 키워드 | `전산` | `--keywords "전산,IT,컴퓨터"` |
| `--headed` | - | 브라우저 화면을 표시 | `False` (headless) | `--headed` |
| `--pages` | `-p` | 게시판당 탐색할 페이지 수 | `2` | `--pages 5` |
| `--today` | `-t` | 오늘 올라온 공고만 필터링 | `False` | `--today` |
| `--from` | `-f` | 조회 시작 날짜 (YYYY-MM-DD) | `None` | `--from 2026-03-01` |
| `--to` | - | 조회 종료 날짜 (YYYY-MM-DD) | `None` | `--to 2026-03-05` |

> **참고:** `--from`/`--to`가 지정되면 `--today`보다 우선합니다. `--from`만 지정하면 해당 날짜부터 오늘까지, `--to`만 지정하면 처음부터 해당 날짜까지 필터링합니다.

**키워드 필터링 동작:**
- 키워드는 게시글 **제목**에서 검색됩니다.
- 여러 키워드는 **OR 조건**으로 동작합니다 (하나라도 포함되면 수집).
- 대소문자를 구분하지 않습니다.

---

## 환경변수 설정

`.env` 파일을 생성하여 기본 동작을 변경할 수 있습니다:

```bash
cp .env.example .env
```

`.env` 파일 내용:

```env
# 대상 카페 URL slug (cafe.naver.com/{CAFE_ID})
CAFE_ID=studentstudyhard

# 기본 검색 키워드 (CLI의 --keywords 옵션으로 덮어쓸 수 있음)
KEYWORD=전산

# 게시판당 탐색 페이지 수 (CLI의 --pages 옵션으로 덮어쓸 수 있음)
SCRAPE_PAGES=2

# HTTP 요청 간 대기 시간 (초) - 서버 부하 방지용
REQUEST_DELAY=1.0

# 브라우저 모드 (CLI의 --headed 옵션으로 덮어쓸 수 있음)
HEADLESS=true
```

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `CAFE_ID` | `studentstudyhard` | 대상 네이버 카페 URL slug |
| `KEYWORD` | `전산` | 기본 필터링 키워드 |
| `SCRAPE_PAGES` | `2` | 게시판당 탐색 페이지 수 (1페이지 = 최대 50건) |
| `REQUEST_DELAY` | `1.0` | 요청 간 대기 시간(초). 너무 낮추면 차단될 수 있음 |
| `HEADLESS` | `true` | `false`로 설정하면 브라우저 화면 표시 |

> CLI 옵션은 환경변수보다 우선합니다. 예를 들어 `.env`에 `SCRAPE_PAGES=2`로 설정되어 있어도 `--pages 5`를 전달하면 5페이지를 탐색합니다.

---

## 출력 결과

스크래핑이 완료되면 `data/` 폴더에 실행 날짜 기준 CSV 파일 1개가 생성됩니다.

### `data/YYYY-MM-DD.csv`

Excel, Google Sheets 등에서 바로 열 수 있는 UTF-8 BOM 인코딩 CSV 파일입니다.

- **파일명**: 실행 날짜 기준 (예: `2026-03-03.csv`)
- **같은 날 재실행**: 마지막 실행 결과로 덮어쓰기
- **이전 날짜 파일**: 그대로 유지 (날짜별 이력 보존)

```csv
기관분류,기관명,공고명,접수기한,링크
중앙공기업,한국철도공사,한국철도공사 전산직 채용 (~3.11),~3.11,https://cafe.naver.com/studentstudyhard/...
지방공기업,서울교통공사,서울교통공사 IT직 채용 (~3.15),~3.15,https://cafe.naver.com/studentstudyhard/...
대학기타,OO대학교,정규직 직원(전산직) 채용 (~3.20),~3.20,https://cafe.naver.com/studentstudyhard/...
```

---

## 축약 실행 (run.sh)

가상환경 활성화와 기본 옵션을 자동 처리하는 스크립트입니다. 모든 명령에 **키워드 "전산, IT"**이 기본 적용됩니다.

```bash
# 실행 권한 부여 (최초 1회)
chmod +x run.sh
```

| 명령어 | 실행되는 내용 | 키워드 |
|--------|--------------|--------|
| `./run.sh` | headless 모드로 스크래핑 | 전산, IT |
| `./run.sh login` | 네이버 로그인 및 쿠키 저장 | - |
| `./run.sh today` | 오늘 올라온 공고만 필터 (headed 모드) | 전산, IT |
| `./run.sh headed` | 브라우저 화면 표시하며 스크래핑 | 전산, IT |
| `./run.sh range 2026-03-01 2026-03-05` | 기간 지정 조회 (headed 모드) | 전산, IT |

```bash
# 예시
./run.sh              # headless 스크래핑 (전산, IT)
./run.sh today        # 오늘 공고만 (headed)
./run.sh headed       # 브라우저 표시
./run.sh login        # 최초 로그인
./run.sh range 2026-03-01 2026-03-05  # 기간 지정 조회
```

> **참고:** 키워드를 변경하려면 `run.sh`를 직접 수정하거나, `python3 main.py scrape --keywords "원하는키워드"` 명령을 사용하세요.

---

## Shell Alias 설정

`~/.zshrc` (또는 `~/.bashrc`)에 아래 alias를 추가하면 어디서든 바로 실행할 수 있습니다:

```bash
# ~/.zshrc 또는 ~/.bashrc에 추가
alias scrape='/절대/경로/mento-duke/run.sh'
alias scrape-today='/절대/경로/mento-duke/run.sh today'
alias scrape-login='/절대/경로/mento-duke/run.sh login'
```

설정 후 적용:

```bash
source ~/.zshrc
```

이제 어디서든 실행 가능:

```bash
scrape          # headless 모드로 스크래핑
scrape-today    # 오늘 공고만 필터 (headed)
scrape-login    # 네이버 로그인 및 쿠키 저장
```

---

## 대상 게시판

카페 좌측 메뉴의 **[실시간 채용공고]** 카테고리 하위 3개 게시판을 탐색합니다:

| 게시판 | 설명 |
|--------|------|
| ★중앙공기업 | 중앙 공기업 채용공고 (한국철도공사, 한국전력 등) |
| ★지방공기업 | 지방 공기업 채용공고 (서울교통공사, 지방공사 등) |
| ★대학/기타기관 | 대학교 및 기타기관 채용공고 |

> 게시판 이름은 `src/config.py`의 `target_boards` 설정에서 변경할 수 있습니다.

---

## 동작 방식

```
login 명령 → 브라우저에서 수동 네이버 로그인 → 쿠키 저장 (data/cookies.json)
                                                         ↓
scrape 명령 → 저장된 쿠키로 인증 ────────────────────────┘
    ↓
Step 1. 카페 메인 페이지에서 게시판 ID(clubId, menuId) 자동 탐색
    ↓
Step 2. Naver REST API로 게시글 목록 수집 → 키워드 필터링
         (API 실패 시 → DOM 파싱으로 자동 전환)
    ↓
Step 3. 각 게시글 상세 페이지 접근 (cafe_main iframe) → 기관명/마감일 추출
    ↓
Step 4. 결과를 날짜별 CSV 파일로 저장 (data/YYYY-MM-DD.csv)
```

**핵심 기술:**
- **게시글 목록**: Naver Cafe REST API (`ArticleListV2dot1.json`)로 빠르게 수집합니다. API 실패 시 Playwright DOM 파싱으로 자동 전환됩니다.
- **게시글 상세**: Playwright로 `cafe_main` iframe에 접근하여 본문을 파싱하고, 정규표현식으로 기관명과 마감일을 추출합니다.
- **인증**: 첫 실행 시 수동 로그인 후 쿠키를 저장하고, 이후 실행에서 자동 재사용합니다.

---

## 프로젝트 구조

```
mento-duke/
├── main.py                  # CLI 진입점 (login, scrape 명령)
├── run.sh                   # 축약 실행 스크립트
├── requirements.txt         # Python 의존성 목록
├── .env.example             # 환경변수 템플릿
├── .gitignore
│
├── src/                     # 핵심 모듈
│   ├── __init__.py
│   ├── config.py            # 설정 관리 (Pydantic Settings + .env)
│   ├── models.py            # 데이터 모델 (Board, ArticleSummary, JobPosting)
│   ├── auth.py              # 네이버 로그인, 쿠키 저장/로드/검증
│   └── exporter.py          # 결과 내보내기 (날짜별 CSV)
│
├── tasks/                   # 스크래핑 작업 모듈
│   ├── __init__.py
│   ├── discover.py          # 카페 clubId + 게시판 menuId 자동 탐색
│   ├── scrape_listings.py   # API/DOM으로 게시글 목록 수집
│   └── scrape_details.py    # 게시글 본문 상세 파싱 (기관명, 마감일)
│
├── data/                    # 출력 파일 디렉토리
│   └── .gitkeep             # (cookies.json, YYYY-MM-DD.csv)
│
└── logs/                    # 실행 로그 디렉토리
    └── .gitkeep             # (일별 자동 생성, 7일 후 자동 삭제)
```

---

## 문제 해결

### 쿠키 파일이 없다는 오류

```
쿠키 파일이 없습니다. 'python main.py login' 을 먼저 실행해주세요.
```

**해결:** `python3 main.py login`을 실행하여 네이버에 로그인하세요.

### 스크래핑 결과가 0건

가능한 원인과 해결법:

| 원인 | 해결 |
|------|------|
| 쿠키 만료 | `python3 main.py login`으로 재로그인 |
| 키워드가 너무 구체적 | 더 넓은 키워드 사용 (예: `--keywords "전산,IT,컴퓨터"`) |
| 해당 키워드 공고가 없음 | `--headed` 옵션으로 브라우저를 보면서 확인 |
| 게시판 구조 변경 | `src/config.py`의 `target_boards` 확인 |

### API 실패, DOM 파싱으로 전환

```
API 실패, DOM 파싱으로 전환: ★중앙공기업
```

이것은 경고이지 오류가 아닙니다. REST API가 실패하면 자동으로 브라우저 기반 DOM 파싱으로 전환되어 정상 동작합니다. 단, DOM 파싱은 API보다 느립니다.

### cafe_main iframe을 찾을 수 없음

```
cafe_main iframe을 찾을 수 없습니다.
```

네이버 카페 페이지 구조가 변경되었을 수 있습니다. `--headed` 옵션으로 실행하여 브라우저 상태를 직접 확인하세요.

### Playwright 브라우저 설치 오류

```bash
# Playwright 브라우저 재설치
playwright install --force chromium

# 시스템 의존성 설치 (Linux)
playwright install-deps chromium
```

### 기관명/마감일이 "확인필요"로 표시됨

게시글 본문의 형식이 다양하여 자동 추출이 어려운 경우입니다. 링크를 통해 원문을 직접 확인하세요.

---

## 자주 묻는 질문

**Q: 카페 회원이 아니면 사용할 수 없나요?**
A: 네, 네이버 카페 게시글을 조회하려면 해당 카페에 가입되어 있어야 합니다.

**Q: 쿠키는 얼마나 유지되나요?**
A: 네이버 세션 쿠키의 유효 기간에 따라 다릅니다. 보통 수일~수주 유지되지만, 스크래핑 실패 시 재로그인하면 됩니다.

**Q: 다른 네이버 카페에도 사용할 수 있나요?**
A: `.env` 파일에서 `CAFE_ID`를 변경하고, `src/config.py`의 `target_boards`를 해당 카페의 게시판 이름으로 수정하면 가능합니다.

**Q: 차단되지 않나요?**
A: 기본적으로 요청 간 1초 지연(`REQUEST_DELAY=1.0`)이 설정되어 있어 서버에 부담을 주지 않습니다. 이 값을 너무 낮추지 않는 것을 권장합니다.

**Q: Windows에서도 동작하나요?**
A: 네, Python 3.10 이상과 Playwright가 설치되어 있으면 Windows에서도 정상 동작합니다. 가상환경 활성화 명령만 OS에 맞게 사용하세요.

---

## 라이센스

이 프로젝트는 개인 학습 및 취업 준비 목적으로 제작되었습니다.
