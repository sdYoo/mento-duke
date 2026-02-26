#!/bin/bash
# Naver Cafe 채용공고 스크래퍼 실행 스크립트
cd "$(dirname "$0")"
source .venv/bin/activate

case "${1:-scrape}" in
  login)
    python3 main.py login
    ;;
  today)
    python3 main.py scrape --keywords "전산,IT" --today --headed
    ;;
  headed)
    python3 main.py scrape --keywords "전산,IT" --headed
    ;;
  *)
    python3 main.py scrape --keywords "전산,IT"
    ;;
esac
