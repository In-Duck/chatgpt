"""
이미지 기반 자동 클릭 워커 (pyautogui 버전)
- pyautogui를 사용한 간단한 이미지 인식 및 클릭
- 전체 이미지가 구역 내에 있어야 감지
- 3개의 surak 이미지 중 하나라도 감지되면 즉시 클릭 후 시퀀스 실행
"""
import time
from typing import Optional, Tuple, List
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
import pyautogui
from PIL import Image
from utils import resource_path


class ImageClickerWorker(QObject):
    """이미지를 찾아 자동으로 클릭하는 워커 (pyautogui 사용)"""

    image_clicked = pyqtSignal(int, int)  # 클릭 성공 (x, y)
    error_occurred = pyqtSignal(str)  # 오류 발생
    release_completed = pyqtSignal()  # 이미지 사라짐
    sequence_started = pyqtSignal()  # 시퀀스 시작
    sequence_completed = pyqtSignal()  # 시퀀스 완료
    sequence_step = pyqtSignal(str)  # 시퀀스 단계 알림

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.search_region: Optional[Tuple[int, int, int, int]] = None
        self.template_paths: List[str] = []  # 여러 템플릿 지원
        self.confidence: float = 0.7
        self.click_interval = 3000  # 3초마다 클릭

        # 타이머
        self.click_timer: Optional[QTimer] = None
        self.sequence_timer: Optional[QTimer] = None

        # 상태
        self.image_found = False
        self.last_location: Optional[Tuple[int, int, int, int]] = None
        self.current_template: Optional[str] = None
        self.sequence_triggered = False  # 시퀀스가 이미 트리거되었는지 추적
        
        # 시퀀스 관련
        self.is_sequence_running = False
        self.sequence_step_index = 0
        self.sequence_wait_time = 0
        
        # 창인식 영역 (고정: 20, 20, 1296, 759)
        self.window_region = (20, 20, 1296, 759)

    def set_config(
        self,
        search_region: Tuple[int, int, int, int],
        template_path: str,
        confidence: float = 0.7
    ):
        """단일 템플릿 설정 (기존 호환성 유지)"""
        self.search_region = search_region
        self.template_paths = [template_path]
        self.confidence = confidence
        print(f"이미지 클릭 설정: 구역={search_region}, 템플릿={template_path}, 신뢰도={confidence}")

    def set_config_multi(
        self,
        search_region: Tuple[int, int, int, int],
        template_paths: List[str],
        confidence: float = 0.7
    ):
        """다중 템플릿 설정 (3개의 surak 이미지 지원)"""
        self.search_region = search_region
        self.template_paths = template_paths
        self.confidence = confidence
        print(f"이미지 클릭 설정: 구역={search_region}, 템플릿={len(template_paths)}개, 신뢰도={confidence}")

    def start(self):
        """이미지 검색 및 클릭 시작"""
        if self.is_running or not self.search_region or not self.template_paths:
            return

        self.is_running = True
        self.image_found = False
        self.last_location = None
        self.current_template = None
        self.is_sequence_running = False
        self.sequence_triggered = False

        print(f"이미지 클릭 시작: 구역={self.search_region}, 템플릿 {len(self.template_paths)}개, 신뢰도={self.confidence}")

        # 3초마다 이미지 검색 및 클릭
        self.click_timer = QTimer()
        self.click_timer.timeout.connect(self._search_and_click)
        self.click_timer.start(self.click_interval)
        self._search_and_click()

    def stop(self):
        """이미지 검색 중지"""
        print("이미지 클릭 중지")
        self.is_running = False
        self.image_found = False
        self.last_location = None
        self.current_template = None
        self.is_sequence_running = False
        self.sequence_triggered = False

        if self.click_timer:
            self.click_timer.stop()
            self.click_timer = None
            
        if self.sequence_timer:
            self.sequence_timer.stop()
            self.sequence_timer = None

    def _search_and_click(self):
        """이미지를 찾아 클릭 - 전체 이미지가 구역 내에 있어야 함"""
        if not self.is_running or self.is_sequence_running:
            return

        try:
            x1, y1, x2, y2 = self.search_region
            region_width = x2 - x1
            region_height = y2 - y1
            
            # 모든 템플릿에 대해 검색
            found = False
            found_template_name = None
            
            for idx, template_path in enumerate(self.template_paths):
                template_full_path = resource_path(template_path)
                
                # 템플릿 이미지 로드하여 크기 확인
                template_img = Image.open(template_full_path)
                template_width, template_height = template_img.size

                # pyautogui로 이미지 찾기 (구역 지정)
                location = pyautogui.locateOnScreen(
                    template_full_path,
                    confidence=self.confidence,
                    region=(x1, y1, region_width, region_height)
                )

                if location:
                    # location은 (left, top, width, height) 형식
                    left, top, width, height = location
                    right = left + width
                    bottom = top + height
                    
                    # 전체 이미지가 구역 내에 있는지 확인
                    if left >= x1 and top >= y1 and right <= x2 and bottom <= y2:
                        # 중심점 계산
                        x = left + width // 2
                        y = top + height // 2
                        
                        # 이미지 발견 상태 업데이트
                        was_found = self.image_found
                        self.image_found = True
                        self.last_location = (left, top, right, bottom)
                        self.current_template = template_path
                        found = True
                        found_template_name = f"surak{idx+1 if idx > 0 else ''}.png"
                        
                        if not was_found:
                            print(f"✓ [FOUND #{idx+1}] 이미지 발견: {template_path} at ({left}, {top}, {right}, {bottom}) 중심=({x}, {y})")
                            print(f"→ 찾은 이미지: {found_template_name}")
                            print(f"→ 즉시 클릭 후 시퀀스 시작")
                        
                        # 클릭 수행 (단일 클릭)
                        pyautogui.moveTo(x, y, duration=0.1)
                        pyautogui.click()
                        
                        self.image_clicked.emit(x, y)
                        
                        # 시퀀스가 아직 트리거되지 않았다면 즉시 시작
                        if not self.sequence_triggered:
                            print(f"[TRIGGER] surak 이미지 감지 → 즉시 시퀀스 시작")
                            self.sequence_triggered = True
                            self.release_completed.emit()
                            self._start_sequence()
                        
                        break  # 첫 번째 매칭된 이미지만 처리
                    else:
                        # 부분 이미지는 무시
                        if self.image_found and self.current_template == template_path:
                            print(f"✗ [PARTIAL] 부분 이미지 감지 (무시): {template_path} ({left}, {top}, {right}, {bottom}) - 구역 밖으로 벗어남")

            # 모든 템플릿에서 이미지를 찾지 못함
            if not found:
                if self.image_found:
                    print(f"[RELEASE] 이미지 사라짐 확인 ({self.current_template})")
                    self.image_found = False
                    self.last_location = None
                    self.current_template = None
                    # 시퀀스는 이미 시작되었으므로 여기서는 아무것도 하지 않음

        except Exception as e:
            error_msg = f"이미지 검색 오류: {e}"
            print(f"[ERROR] {error_msg}")
            self.error_occurred.emit(error_msg)

    def _start_sequence(self):
        """시퀀스 실행 시작"""
        if self.is_sequence_running:
            return
            
        self.is_sequence_running = True
        self.sequence_step_index = 0
        print("\n" + "="*60)
        print("시퀀스 시작: malon → hunt → filter → malon → 대기(3분) → malon → filter → malon")
        print("="*60 + "\n")
        self.sequence_started.emit()
        
        # 시퀀스 타이머 시작
        self.sequence_timer = QTimer()
        self.sequence_timer.timeout.connect(self._execute_sequence_step)
        self.sequence_timer.start(100)  # 100ms마다 체크

    def _execute_sequence_step(self):
        """시퀀스 단계별 실행"""
        if not self.is_running or not self.is_sequence_running:
            if self.sequence_timer:
                self.sequence_timer.stop()
                self.sequence_timer = None
            return

        try:
            # 시퀀스 정의: (이미지, 클릭타입, 대기시간)
            # 클릭타입: "double" or "single"
            # 대기시간: 다음 단계까지 대기 (초)
            sequence_steps = [
                ("img/malon.png", "double", 0.5),    # Step 1: malon 더블클릭
                ("img/hunt.png", "single", 0.5),     # Step 2: hunt 클릭
                ("img/filter.png", "single", 0.5),   # Step 3: filter 클릭
                ("img/malon.png", "double", 180.0),  # Step 4: malon 더블클릭 → 3분 대기
                ("img/malon.png", "double", 0.5),    # Step 5: malon 더블클릭
                ("img/filter.png", "single", 0.5),   # Step 6: filter 클릭
                ("img/malon.png", "double", 0.5),    # Step 7: malon 더블클릭
            ]
            
            if self.sequence_step_index >= len(sequence_steps):
                # 시퀀스 완료
                print("\n" + "="*60)
                print("시퀀스 완료!")
                print("="*60 + "\n")
                self.is_sequence_running = False
                self.sequence_triggered = False  # 다음 감지를 위해 리셋
                if self.sequence_timer:
                    self.sequence_timer.stop()
                    self.sequence_timer = None
                self.sequence_completed.emit()
                return
            
            # 대기 시간 처리
            if self.sequence_wait_time > 0:
                self.sequence_wait_time -= 0.1
                if self.sequence_wait_time > 0:
                    return  # 아직 대기 중
                else:
                    self.sequence_wait_time = 0
                    self.sequence_step_index += 1
                    if self.sequence_step_index >= len(sequence_steps):
                        self._execute_sequence_step()  # 재귀 호출로 완료 처리
                    return
            
            # 현재 단계 실행
            image_path, click_type, wait_time = sequence_steps[self.sequence_step_index]
            
            step_name = f"Step {self.sequence_step_index + 1}/{len(sequence_steps)}"
            print(f"\n[{step_name}] 실행 중: {image_path} ({click_type} click)")
            
            # 창인식 영역에서 이미지 찾기
            result = self._find_and_click_in_window(image_path, click_type)
            
            if result:
                x, y = result
                print(f"[{step_name}] ✓ 성공: ({x}, {y}) 클릭 완료")
                
                # 다음 단계로 이동 준비
                if wait_time > 1.0:
                    print(f"[{step_name}] → {wait_time}초 대기 시작...")
                    self.sequence_step.emit(f"{step_name}: {image_path} 클릭 완료, {wait_time}초 대기")
                else:
                    self.sequence_step.emit(f"{step_name}: {image_path} 클릭 완료")
                
                self.sequence_wait_time = wait_time
            else:
                print(f"[{step_name}] ✗ 실패: {image_path} 이미지를 찾을 수 없음 (재시도 중...)")
                # 실패 시 0.5초 후 재시도
                self.sequence_wait_time = 0.5
                
        except Exception as e:
            error_msg = f"시퀀스 실행 오류: {e}"
            print(f"[ERROR] {error_msg}")
            self.error_occurred.emit(error_msg)
            self.is_sequence_running = False
            self.sequence_triggered = False
            if self.sequence_timer:
                self.sequence_timer.stop()
                self.sequence_timer = None

    def _find_and_click_in_window(self, image_path: str, click_type: str) -> Optional[Tuple[int, int]]:
        """창인식 영역에서 이미지를 찾아 클릭"""
        try:
            x1, y1, x2, y2 = self.window_region
            region_width = x2 - x1
            region_height = y2 - y1
            
            template_full_path = resource_path(image_path)
            
            # pyautogui로 이미지 찾기
            location = pyautogui.locateOnScreen(
                template_full_path,
                confidence=self.confidence,
                region=(x1, y1, region_width, region_height)
            )
            
            if location:
                left, top, width, height = location
                right = left + width
                bottom = top + height
                
                # 전체 이미지가 구역 내에 있는지 확인
                if left >= x1 and top >= y1 and right <= x2 and bottom <= y2:
                    # 중심점 계산
                    x = left + width // 2
                    y = top + height // 2
                    
                    # 클릭 수행
                    pyautogui.moveTo(x, y, duration=0.1)
                    
                    if click_type == "double":
                        pyautogui.doubleClick()
                    else:
                        pyautogui.click()
                    
                    return (x, y)
            
            return None
            
        except Exception as e:
            print(f"이미지 찾기 오류: {e}")
            return None

    def on_image_release_completed(self):
        """외부에서 호출 가능한 릴리즈 완료 핸들러"""
        if not self.is_sequence_running and not self.sequence_triggered:
            self._start_sequence()