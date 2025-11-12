"""
이미지 기반 자동 클릭 워커 (pyautogui 버전)
- pyautogui를 사용한 간단한 이미지 인식 및 클릭
- 전체 이미지가 구역 내에 있어야 감지
- 조건부 시퀀스 실행: surak → hunt → filter 순차 처리
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
    phase5_completed = pyqtSignal()  # Phase 5 완료 (리치해제 완료)
    phase6_progress = pyqtSignal(int, int)  # Phase 6 진행 상황 (경과 시간, 전체 시간)

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.search_region: Optional[Tuple[int, int, int, int]] = None
        self.template_paths: List[str] = []  # 여러 템플릿 지원
        self.confidence: float = 0.7
        self.click_interval = 3000  # 3초마다 surak 검색
        self.action_interval = 500  # 0.5초 간격으로 액션

        # 타이머
        self.click_timer: Optional[QTimer] = None
        self.sequence_timer: Optional[QTimer] = None

        # 상태
        self.image_found = False
        self.last_location: Optional[Tuple[int, int, int, int]] = None
        self.current_template: Optional[str] = None
        
        # 시퀀스 관련
        self.is_sequence_running = False
        self.sequence_phase = 0  # 시퀀스 단계
        self.wait_counter = 0  # 대기 카운터
        self.phase6_start_time = 0  # Phase 6 시작 시간
        
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
        self.sequence_phase = 0
        self.phase6_start_time = 0

        print(f"이미지 클릭 시작: 구역={self.search_region}, 템플릿 {len(self.template_paths)}개, 신뢰도={self.confidence}")

        # 3초마다 surak 이미지 검색
        self.click_timer = QTimer()
        self.click_timer.timeout.connect(self._search_surak)
        self.click_timer.start(self.click_interval)
        self._search_surak()

    def stop(self):
        """이미지 검색 중지"""
        print("이미지 클릭 중지")
        self.is_running = False
        self.image_found = False
        self.last_location = None
        self.current_template = None
        self.is_sequence_running = False
        self.sequence_phase = 0
        self.phase6_start_time = 0

        if self.click_timer:
            self.click_timer.stop()
            self.click_timer = None
            
        if self.sequence_timer:
            self.sequence_timer.stop()
            self.sequence_timer = None

    def _search_surak(self):
        """surak 이미지 검색 (3초 간격)"""
        if not self.is_running or self.is_sequence_running:
            return

        try:
            x1, y1, x2, y2 = self.search_region
            region_width = x2 - x1
            region_height = y2 - y1
            
            # 모든 surak 템플릿에 대해 검색
            found = False
            
            for idx, template_path in enumerate(self.template_paths):
                template_full_path = resource_path(template_path)
                template_img = Image.open(template_full_path)

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
                        found = True
                        self.image_found = True
                        self.last_location = (left, top, right, bottom)
                        self.current_template = template_path
                        
                        print(f"✓ [SURAK FOUND] {template_path} 발견 at ({left}, {top}, {right}, {bottom})")
                        print(f"→ surak 사라질 때까지 0.5초마다 클릭 시작")
                        
                        # surak 클릭 단계로 전환
                        self._start_surak_clicking()
                        break

            if not found and self.image_found:
                print("[SURAK] 이미지 없음 (계속 검색 중...)")

        except Exception as e:
            error_msg = f"surak 검색 오류: {e}"
            print(f"[ERROR] {error_msg}")
            self.error_occurred.emit(error_msg)

    def _start_surak_clicking(self):
        """surak 클릭 단계 시작"""
        if self.is_sequence_running:
            return
            
        # 3초 타이머 중지
        if self.click_timer:
            self.click_timer.stop()
            
        self.is_sequence_running = True
        self.sequence_phase = 1  # Phase 1: surak 클릭
        
        print("\n" + "="*60)
        print("시퀀스 시작: Phase 1 - surak 클릭")
        print("="*60 + "\n")
        self.sequence_started.emit()
        
        # 0.5초마다 실행되는 시퀀스 타이머
        self.sequence_timer = QTimer()
        self.sequence_timer.timeout.connect(self._execute_sequence)
        self.sequence_timer.start(self.action_interval)

    def _execute_sequence(self):
        """시퀀스 단계별 실행"""
        if not self.is_running or not self.is_sequence_running:
            if self.sequence_timer:
                self.sequence_timer.stop()
                self.sequence_timer = None
            return

        try:
            if self.sequence_phase == 1:
                # Phase 1: surak 사라질 때까지 클릭
                self._phase1_click_surak()
                
            elif self.sequence_phase == 2:
                # Phase 2: hunt 보일 때까지 malon 더블클릭
                self._phase2_malon_until_hunt()
                
            elif self.sequence_phase == 3:
                # Phase 3: filter 보일 때까지 hunt 클릭
                self._phase3_hunt_until_filter()
                
            elif self.sequence_phase == 4:
                # Phase 4: 0.5초 대기 후 filter 클릭
                self._phase4_wait_and_click_filter()
                
            elif self.sequence_phase == 5:
                # Phase 5: filter 안 보일 때까지 malon 더블클릭
                self._phase5_malon_until_filter_gone()
                
            elif self.sequence_phase == 6:
                # Phase 6: 3분 대기
                self._phase6_wait_3min()
                
            elif self.sequence_phase == 7:
                # Phase 7: hunt 보일 때까지 malon 더블클릭
                self._phase7_malon_until_hunt()
                
            elif self.sequence_phase == 8:
                # Phase 8: filter 보일 때까지 hunt 클릭
                self._phase8_hunt_until_filter()
                
            elif self.sequence_phase == 9:
                # Phase 9: 0.5초 대기 후 filter 클릭
                self._phase9_wait_and_click_filter()
                
            elif self.sequence_phase == 10:
                # Phase 10: filter 안 보일 때까지 malon 더블클릭
                self._phase10_malon_until_filter_gone()
                
            else:
                # 시퀀스 완료
                self._complete_sequence()

        except Exception as e:
            error_msg = f"시퀀스 실행 오류: {e}"
            print(f"[ERROR] {error_msg}")
            self.error_occurred.emit(error_msg)
            self._complete_sequence()

    def _phase1_click_surak(self):
        """Phase 1: surak 사라질 때까지 클릭"""
        found = self._find_image_in_region("img/surak/surak.png", self.search_region) or \
                self._find_image_in_region("img/surak/surak2.png", self.search_region) or \
                self._find_image_in_region("img/surak/surak3.png", self.search_region)
        
        if found:
            x, y = found
            pyautogui.moveTo(x, y, duration=0.05)
            pyautogui.click()
            print(f"[Phase 1] surak 클릭: ({x}, {y})")
            self.image_clicked.emit(x, y)
        else:
            print("[Phase 1] surak 사라짐 → Phase 2로 전환")
            self.sequence_phase = 2
            self.sequence_step.emit("Phase 1 완료: surak 사라짐")

    def _phase2_malon_until_hunt(self):
        """Phase 2: hunt 보일 때까지 malon 더블클릭"""
        hunt_found = self._find_image_in_region("img/hunt.png", self.window_region)
        
        if hunt_found:
            print("[Phase 2] hunt 발견 → Phase 3로 전환")
            self.sequence_phase = 3
            self.sequence_step.emit("Phase 2 완료: hunt 발견")
        else:
            malon_found = self._find_image_in_region("img/malon.png", self.window_region)
            if malon_found:
                x, y = malon_found
                pyautogui.moveTo(x, y, duration=0.05)
                pyautogui.doubleClick()
                print(f"[Phase 2] malon 더블클릭: ({x}, {y})")
                self.image_clicked.emit(x, y)

    def _phase3_hunt_until_filter(self):
        """Phase 3: filter 보일 때까지 hunt 클릭"""
        filter_found = self._find_image_in_region("img/filter.png", self.window_region)
        
        if filter_found:
            print("[Phase 3] filter 발견 → Phase 4로 전환")
            self.sequence_phase = 4
            self.wait_counter = 0
            self.sequence_step.emit("Phase 3 완료: filter 발견")
        else:
            hunt_found = self._find_image_in_region("img/hunt.png", self.window_region)
            if hunt_found:
                x, y = hunt_found
                pyautogui.moveTo(x, y, duration=0.05)
                pyautogui.click()
                print(f"[Phase 3] hunt 클릭: ({x}, {y})")
                self.image_clicked.emit(x, y)

    def _phase4_wait_and_click_filter(self):
        """Phase 4: 0.5초 대기 후 filter 클릭"""
        if self.wait_counter == 0:
            print("[Phase 4] 0.5초 대기 중...")
            self.wait_counter = 1
        else:
            filter_found = self._find_image_in_region("img/filter.png", self.window_region)
            if filter_found:
                x, y = filter_found
                pyautogui.moveTo(x, y, duration=0.05)
                pyautogui.click()
                print(f"[Phase 4] filter 클릭: ({x}, {y})")
                self.image_clicked.emit(x, y)
                self.sequence_phase = 5
                self.sequence_step.emit("Phase 4 완료: filter 클릭")
            else:
                print("[Phase 4] filter 없음, Phase 5로 전환")
                self.sequence_phase = 5

    def _phase5_malon_until_filter_gone(self):
        """Phase 5: filter 안 보일 때까지 malon 더블클릭"""
        filter_found = self._find_image_in_region("img/filter.png", self.window_region)
        
        if not filter_found:
            print("[Phase 5] filter 사라짐 → Phase 6 (3분 대기)로 전환")
            self.sequence_phase = 6
            self.wait_counter = 0
            self.phase6_start_time = time.time()
            self.sequence_step.emit("Phase 5 완료: filter 사라짐, 3분 대기 시작")
            
            # Phase 5 완료 시그널 발송 (텔레그램 알림용)
            self.phase5_completed.emit()
            
            # Phase 6 시작 시그널 (UI 업데이트용)
            self.phase6_progress.emit(0, 180)
        else:
            malon_found = self._find_image_in_region("img/malon.png", self.window_region)
            if malon_found:
                x, y = malon_found
                pyautogui.moveTo(x, y, duration=0.05)
                pyautogui.doubleClick()
                print(f"[Phase 5] malon 더블클릭: ({x}, {y})")
                self.image_clicked.emit(x, y)

    def _phase6_wait_3min(self):
        """Phase 6: 3분(180초) 대기"""
        total_seconds = 180
        
        if self.wait_counter == 0:
            print("[Phase 6] 3분(180초) 대기 시작...")
            self.wait_counter = 1
            self.phase6_start_time = time.time()
        
        elapsed = int(time.time() - self.phase6_start_time)
        
        # UI에 진행 상황 전송
        self.phase6_progress.emit(elapsed, total_seconds)
        
        if elapsed >= total_seconds:  # 3분
            print("[Phase 6] 3분 대기 완료 → Phase 7로 전환")
            self.sequence_phase = 7
            self.wait_counter = 0
            self.sequence_step.emit("Phase 6 완료: 3분 대기 완료")
            # 마지막 진행 상황 전송 (0초 남음)
            self.phase6_progress.emit(total_seconds, total_seconds)
        elif elapsed % 30 == 0 and elapsed > 0:  # 30초마다 로그 (0초 제외)
            remaining = total_seconds - elapsed
            print(f"[Phase 6] 대기 중... ({elapsed}초 경과 / {remaining}초 남음)")

    def _phase7_malon_until_hunt(self):
        """Phase 7: hunt 보일 때까지 malon 더블클릭"""
        hunt_found = self._find_image_in_region("img/hunt.png", self.window_region)
        
        if hunt_found:
            print("[Phase 7] hunt 발견 → Phase 8로 전환")
            self.sequence_phase = 8
            self.sequence_step.emit("Phase 7 완료: hunt 발견")
        else:
            malon_found = self._find_image_in_region("img/malon.png", self.window_region)
            if malon_found:
                x, y = malon_found
                pyautogui.moveTo(x, y, duration=0.05)
                pyautogui.doubleClick()
                print(f"[Phase 7] malon 더블클릭: ({x}, {y})")
                self.image_clicked.emit(x, y)

    def _phase8_hunt_until_filter(self):
        """Phase 8: filter 보일 때까지 hunt 클릭"""
        filter_found = self._find_image_in_region("img/filter.png", self.window_region)
        
        if filter_found:
            print("[Phase 8] filter 발견 → Phase 9로 전환")
            self.sequence_phase = 9
            self.wait_counter = 0
            self.sequence_step.emit("Phase 8 완료: filter 발견")
        else:
            hunt_found = self._find_image_in_region("img/hunt.png", self.window_region)
            if hunt_found:
                x, y = hunt_found
                pyautogui.moveTo(x, y, duration=0.05)
                pyautogui.click()
                print(f"[Phase 8] hunt 클릭: ({x}, {y})")
                self.image_clicked.emit(x, y)

    def _phase9_wait_and_click_filter(self):
        """Phase 9: 0.5초 대기 후 filter 클릭"""
        if self.wait_counter == 0:
            print("[Phase 9] 0.5초 대기 중...")
            self.wait_counter = 1
        else:
            filter_found = self._find_image_in_region("img/filter.png", self.window_region)
            if filter_found:
                x, y = filter_found
                pyautogui.moveTo(x, y, duration=0.05)
                pyautogui.click()
                print(f"[Phase 9] filter 클릭: ({x}, {y})")
                self.image_clicked.emit(x, y)
                self.sequence_phase = 10
                self.sequence_step.emit("Phase 9 완료: filter 클릭")
            else:
                print("[Phase 9] filter 없음, Phase 10으로 전환")
                self.sequence_phase = 10

    def _phase10_malon_until_filter_gone(self):
        """Phase 10: filter 안 보일 때까지 malon 더블클릭"""
        filter_found = self._find_image_in_region("img/filter.png", self.window_region)
        
        if not filter_found:
            print("[Phase 10] filter 사라짐 → 시퀀스 완료")
            self.sequence_phase = 11  # 완료 단계
            self.sequence_step.emit("Phase 10 완료: filter 사라짐")
        else:
            malon_found = self._find_image_in_region("img/malon.png", self.window_region)
            if malon_found:
                x, y = malon_found
                pyautogui.moveTo(x, y, duration=0.05)
                pyautogui.doubleClick()
                print(f"[Phase 10] malon 더블클릭: ({x}, {y})")
                self.image_clicked.emit(x, y)

    def _complete_sequence(self):
        """시퀀스 완료"""
        print("\n" + "="*60)
        print("시퀀스 완료!")
        print("="*60 + "\n")
        
        self.is_sequence_running = False
        self.sequence_phase = 0
        self.wait_counter = 0
        self.phase6_start_time = 0
        
        if self.sequence_timer:
            self.sequence_timer.stop()
            self.sequence_timer = None
            
        # 3초 타이머 재시작
        if self.click_timer:
            self.click_timer.start(self.click_interval)
            
        self.sequence_completed.emit()

    def _find_image_in_region(self, image_path: str, region: Tuple[int, int, int, int]) -> Optional[Tuple[int, int]]:
        """특정 영역에서 이미지를 찾아 중심 좌표 반환"""
        try:
            x1, y1, x2, y2 = region
            region_width = x2 - x1
            region_height = y2 - y1
            
            template_full_path = resource_path(image_path)
            
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
                    x = left + width // 2
                    y = top + height // 2
                    return (x, y)
            
            return None
            
        except Exception as e:
            return None

    def on_image_release_completed(self):
        """외부에서 호출 가능한 릴리즈 완료 핸들러"""
        pass