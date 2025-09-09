📝 DailyLog Desktop App 실행 방법
1. 준비물

Windows PC (Python 3.11 이상 설치 권장)

DailyLog_Desktop_App_v1.3.zip 압축 해제

폴더 구조 예시:

DailyLog_Desktop_App/
 ├─ main.py
 ├─ Run-DailyLog-AutoSetup.bat
 ├─ requirements.txt
 ├─ splash.png           ← (스플래시 이미지, 선택)
 ├─ DailyLog_app.ico     ← (앱 아이콘, 선택)
 └─ ...

2. 최초 실행 (자동 설치 + 실행)

Run-DailyLog-AutoSetup.bat 파일을 더블클릭

배치파일이 자동으로:

Python 실행 파일 경로 탐색

필요 패키지 설치 (PySide6, pandas, openpyxl)

앱 실행 (main.py)

3. 이후 실행

매번 똑같이 Run-DailyLog-AutoSetup.bat 더블클릭하면 됩니다.

이미 패키지가 설치되어 있으면 바로 앱이 실행됩니다.

4. 앱 실행 화면

좌측: Daily Log & 주식 기록 테이블

우측: 입력 폼 (칩 버튼, 덮어쓰기 모드 지원)

상단: 검색창, 불러오기(엎기)/내보내기 버튼

스플래시(splash.png)와 아이콘(DailyLog_app.ico)은 있으면 자동 적용됩니다.

5. 데이터 관리

데이터는 같은 폴더의 daily_log.db (SQLite) 파일에 저장됩니다.

엑셀 불러오기(엎기) → 전체 데이터 대체 (자동 백업 생성)

엑셀 내보내기 → 보고/백업용 파일 생성