# 유럽 5대 리그 선수 시즌 기록 분석 (권한 오류 수정)

## 수정 내용
SeleniumBase의 Chrome 드라이버 저장 폴더를 Streamlit Cloud에서 쓰기 가능한 `/tmp/seleniumbase_drivers`로 변경했습니다. soccerdata 캐시도 `/tmp/soccerdata_fbref`에 저장합니다.

## 배포
GitHub 저장소 루트의 `app.py`, `requirements.txt`, `packages.txt`, `README.md`를 모두 새 버전으로 교체한 뒤 Streamlit 앱을 재부팅하세요.

## 사용
선수 이름(영문 권장)과 시즌(예: 2022-2023)을 입력합니다.

자료 출처: https://fbref.com/en/comps/Big5/
수집 도구: https://soccerdata.readthedocs.io/
