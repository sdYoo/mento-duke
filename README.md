# Naver Cafe 채용공고 스크래퍼

공준모 카페(studentstudyhard)의 채용공고 게시판에서 **"전산직"** 관련 공고를 자동 수집하는 CLI 도구입니다.

## 빠른 실행 가이드

```bash
# 1. 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 2. 의존성 설치
pip install -r requirements.txt
playwright install chromium

# 3. 네이버 로그인 (최초 1회 - 브라우저가 열리면 직접 로그인)
python3 main.py login

# 4. 스크래핑 실행
python3 main.py scrape --keywords "전산,IT" --headed
```

실행 결과는 `data/` 폴더에 저장됩니다:
- `data/YYYY-MM-DD.txt` — 오늘 날짜 표 형태 결과
- `data/results.md` — Markdown 테이블
- `data/results.csv` — CSV 파일

### CLI 옵션

| 옵션 | 설명 | 예시 |
|------|------|------|
| `--keywords`, `-k` | 쉼표 구분 검색 키워드 | `--keywords "전산,IT"` |
| `--headed` | 브라우저 화면 표시 | `--headed` |
| `--pages`, `-p` | 게시판당 탐색 페이지 수 | `--pages 3` |
| `--today`, `-t` | 오늘 올라온 공고만 필터 | `--today` |

```bash
# 사용 예시
python3 main.py scrape --keywords "전산,IT" --today        # 오늘 공고만
python3 main.py scrape --keywords "행정" --pages 3         # 행정직 3페이지
python3 main.py scrape --keywords "전산,IT" --headed       # 브라우저 표시
```

---

## 대상 게시판

| 게시판 | 설명 |
|--------|------|
| ★중앙공기업 | 중앙 공기업 채용공고 |
| ★지방공기업 | 지방 공기업 채용공고 |
| ★대학/기타기관 | 대학교 및 기타기관 채용공고 |

## 동작 방식

```
login 명령 → 브라우저에서 수동 네이버 로그인 → 쿠키 저장
                                                  ↓
scrape 명령 → 저장된 쿠키로 인증 ──────────────────┘
    ↓
Step 1. 카페 메인 페이지에서 게시판 ID 자동 탐색
    ↓
Step 2. Naver REST API로 게시글 목록 수집 → "전산" 키워드 필터링
    ↓
Step 3. 각 게시글 상세 페이지 접근 (iframe) → 기관명/마감일 추출
    ↓
Step 4. 결과를 Markdown 테이블 + CSV 파일로 저장
```

- **게시글 목록**: Naver Cafe REST API (`ArticleListV2dot1.json`)로 빠르게 수집하고, API 실패 시 DOM 파싱으로 자동 전환합니다.
- **게시글 상세**: Playwright로 `cafe_main` iframe에 접근하여 본문을 파싱합니다.
- **인증**: 첫 실행 시 수동 로그인 후 쿠키를 `data/cookies.json`에 저장하고, 이후 실행에서 자동 재사용합니다.

## 설치

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. Playwright 브라우저 설치

```bash
playwright install chromium
```

### 3. 환경변수 설정 (선택)

```bash
cp .env.example .env
```

`.env` 파일에서 기본값을 변경할 수 있습니다:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `CAFE_ID` | `studentstudyhard` | 대상 카페 URL slug |
| `KEYWORD` | `전산` | 필터링 키워드 |
| `SCRAPE_PAGES` | `2` | 게시판당 탐색 페이지 수 |
| `REQUEST_DELAY` | `1.0` | 요청 간 대기 시간(초) |
| `HEADLESS` | `true` | 헤드리스 브라우저 모드 |

## 사용법

### Step 1: 네이버 로그인 (최초 1회)

```bash
python3 main.py login
```

- Chromium 브라우저가 열리고 네이버 로그인 페이지로 이동합니다.
- 직접 아이디/비밀번호를 입력하여 로그인합니다.
- 로그인이 완료되면 쿠키가 `data/cookies.json`에 저장됩니다.
- 쿠키가 만료되면 이 명령을 다시 실행하세요.

### Step 2: 스크래핑 실행

```bash
# 기본 실행 (headless 모드, 전산 키워드, 2페이지)
python3 main.py scrape

# 브라우저 화면을 보면서 실행
python3 main.py scrape --headed

# 여러 키워드 동시 검색 (쉼표 구분)
python3 main.py scrape --keywords "전산,IT"

# 오늘 올라온 공고만 필터링
python3 main.py scrape --keywords "전산,IT" --today

# 3페이지까지 탐색
python3 main.py scrape --pages 3

# 옵션 조합
python3 main.py scrape --keywords "전산,IT" --headed --pages 3
```

## 출력 결과

스크래핑이 완료되면 `data/` 폴더에 세 개의 파일이 생성됩니다.

### `data/YYYY-MM-DD.txt` (표 형태 텍스트)

```
+----+------------+------------------+------------------------------------------+--------+---------------------------------------------+
| No | 기관분류   | 기관명           | 공고명                                   | 접수기한 | 링크                                        |
+----+------------+------------------+------------------------------------------+--------+---------------------------------------------+
| 1  | 중앙공기업 | 한국철도공사     | ★총1,800명 [한국철도공사 채용] ... (~3.11) | ~3.11  | https://cafe.naver.com/studentstudyhard/... |
+----+------------+------------------+------------------------------------------+--------+---------------------------------------------+
```

### `data/results.md` (Markdown 테이블)

| 기관분류 | 기관명 | 공고명 | 접수기한 | 링크 |
|----------|--------|--------|----------|------|
| 중앙공기업 | 한국OO공사 | [한국OO공사 채용] 전산직 채용 (~3.11) | ~3.11 | https://cafe.naver.com/... |

### `data/results.csv` (CSV)

Excel 등에서 바로 열 수 있는 UTF-8 BOM 인코딩 CSV 파일입니다.

## 프로젝트 구조

```
mento-duke/
├── main.py                     # CLI 진입점 (login, scrape 명령)
├── requirements.txt            # Python 의존성
├── .env.example                # 환경변수 템플릿
├── src/
│   ├── config.py               # 설정 관리 (Pydantic Settings)
│   ├── models.py               # 데이터 모델 (Board, ArticleSummary, JobPosting)
│   ├── auth.py                 # 쿠키 저장/로드/검증
│   └── exporter.py             # Markdown + CSV 내보내기
├── tasks/
│   ├── discover.py             # clubId + menuId 자동 탐색
│   ├── scrape_listings.py      # API로 게시글 목록 수집
│   └── scrape_details.py       # 게시글 본문 상세 파싱
├── data/                       # 출력 파일 (cookies.json, results.md, results.csv)
└── logs/                       # 실행 로그
```

## 오류 대응

| 상황 | 동작 |
|------|------|
| 쿠키 파일 없음 | `login` 명령 먼저 실행하라는 안내 출력 |
| 쿠키 만료 | 재로그인 유도 |
| API 요청 실패 | DOM 스크래핑으로 자동 전환 |
| 개별 게시글 파싱 실패 | 경고 로그 후 다음 게시글로 계속 진행 |
| 기관명/마감일 추출 실패 | "확인필요"로 대체하여 프로그램 중단 방지 |

## 참고사항

- 네이버 카페 회원 로그인이 필요합니다 (공준모 카페 가입 필수).
- 요청 간 1초 지연이 기본 설정되어 있어 서버에 부담을 주지 않습니다.
- 게시판당 최대 50건 x 페이지 수만큼 탐색합니다.
- 로그 파일은 `logs/` 폴더에 일별로 저장되며, 7일 후 자동 삭제됩니다.
