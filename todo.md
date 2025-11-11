# Window Monitor & Auto Key Input Application

## MVP Implementation Plan

### Core Files:
1. **main.py** - 애플리케이션 진입점
2. **main_window.py** - 메인 윈도우 UI (상태 표시, 버튼들)
3. **settings_dialog.py** - 환경설정 다이얼로그 (창 선택, 키 설정, 타이밍 설정, 유저 탐색 설정)
4. **window_monitor.py** - 창 감지 및 활성화 로직
5. **key_input_worker.py** - 자동 키 입력 로직
6. **user_detector.py** - 유저 탐색 로직 (빨간색 감지, 텔레그램 알람)
7. **region_preview.py** - 구역 미리보기 오버레이 창
8. **config_manager.py** - 설정 저장/로드 (JSON)
9. **requirements.txt** - 필요한 패키지 목록

### Key Features:
- PyQt5 기반 GUI
- 창 감지: 선택된 창이 비활성화되면 즉시 최상단으로 복원
- 자동 키 입력: 설정된 간격으로 지정된 키를 입력
- 유저 탐색: 특정 구역에서 빨간색 감지 시 텔레그램 알람
- 설정 저장: JSON 파일로 저장하여 재시작 후에도 유지
- 효율적인 리소스 사용: QTimer와 이벤트 기반 처리

### Technical Stack:
- PyQt5: GUI 프레임워크
- pywin32: Windows API 접근 (창 감지, 활성화)
- pynput: 키보드 입력
- Pillow: 화면 캡처 및 이미지 처리
- pyautogui: 화면 캡처
- python-telegram-bot: 텔레그램 봇 연동
- JSON: 설정 저장

### New Features (유저 탐색):
1. 특정 구역 지속 탐색 (500ms 간격)
2. 빨간색 5픽셀 이상 감지 시 텔레그램 알람
3. 빨간색 사라지면 텔레그램 알람
4. 설정창에 텔레그램 토큰/아이디, 닉네임, 구역 설정
5. 구역 미리보기 버튼 (3초간 빨간 테두리 표시)
6. 메인 UI에 유저탐색/중지 버튼

### Optimization Updates (2025-11-10):
✅ 배치 템플릿 매칭으로 CPU 사용량 최적화
✅ 한 번에 모든 이미지 매칭 처리
✅ img 폴더 경로로 통일

### Implementation Status:
✅ 모든 기능 구현 완료
✅ 성능 최적화 완료