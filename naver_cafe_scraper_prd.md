# Product Requirements Document (PRD): Naver Cafe Job Posting Scraper

## 1. 개요 (Project Overview)
본 프로젝트는 특정 네이버 카페의 채용공고 게시판에서 '전산직' 관련 채용 정보만을 필터링하여 주요 정보를 리스트업하는 자동화 스크립트/도구를 작성하는 것을 목표로 합니다.

## 2. 대상 출처 (Target Source)
- **대상 카페 URL**: https://cafe.naver.com/studentstudyhard (공준모)

## 3. 요구사항 (Requirements)

### 3.1 대상 게시판 (Target Categories)
좌측 메뉴의 **[● 실시간 채용공고]** 카테고리 하위에 있는 다음 3개의 게시판을 탐색합니다. (실제 메뉴명에는 별표(★) 기호가 포함되어 있습니다)
1. **★중앙공기업**
2. **★지방공기업**
3. **★대학/기타기관**

### 3.2 필터링 조건 (Filtering Condition)
- 위 3개 게시판의 게시글 중에서 제목이나 내용에 **"전산직"** (또는 '전산') 키워드가 포함된 공고만 필터링하여 추출합니다.

### 3.3 추출 데이터 (Data Extraction Fields)
조건에 맞는 각 공고에서 다음의 핵심 정보를 추출하여 리스트업합니다.
- **기관명** (Institution Name)
- **공고명** (Job Title / Post Title)
- **접수 마감일/기한** (Application Deadline)
- **공고 원문 링크** (Link to the post)

## 4. 결과물 형태 (Output Format)
추출된 데이터는 읽기 쉬운 형태(Markdown 파일의 표(Table) 또는 CSV 파일)로 저장되어야 합니다.

**[출력 예시 - Markdown Table]**
| 기관분류 | 기관명 | 공고명 | 접수 기한 | 링크 |
| --- | --- | --- | --- | --- |
| 중앙공기업 | 한국00공사 | 2024년 상반기 전산직 신입 채용 | 2024.05.30 18:00 | [바로가기](URL) |
| 대학/기타기관 | 00대학교 | 정규직 직원(전산직) 채용 | 2024.06.05 15:00 | [바로가기](URL) |

## 5. Claude Code를 위한 기술적 참고사항 (Technical Considerations)
- **Iframe 처리**: 네이버 카페는 본문 영역이 `cafe_main` 이라는 iframe 내부에 존재합니다. 크롤러 구현 시 일반적인 HTML 파싱 외에 iframe URL(`ArticleList.nhn` 등)로 직접 접근하거나 프레임을 전환하는 로직이 필요합니다.
- **도구 선택**: 단순 HTTP GET 요청(BeautifulSoup 등)으로 iframe 소스를 가져오거나, 필요할 경우 브라우저 자동화 도구(Playwright, Puppeteer 등)를 사용해 구현해주세요.
- **페이지네이션**: 공고가 많을 경우 최신 1~2페이지 정도를 우선적으로 탐색하도록 구현해주세요.
