import time
from typing import Optional, Tuple
from pathlib import Path
from utils import resource_path
import cv2
import numpy as np
import pyautogui
from PIL import ImageGrab
from PyQt5.QtCore import QObject, QTimer, pyqtSignal


class ImageClickerWorker(QObject):
    """특정 이미지를 감지하고 클릭하는 클래스"""

    image_found = pyqtSignal(int, int)
    image_clicked = pyqtSignal(int, int)
    image_not_found = pyqtSignal()
    release_completed = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.is_running = False

        # 주기적 탐색 타이머
        self.timer = QTimer()
        self.timer.timeout.connect(self._search_phase)
        self.timer.setSingleShot(True)

        # 클릭 상태 타이머
        self.active_click_timer = QTimer()
        self.active_click_timer.timeout.connect(self._active_click_phase)
        self.active_click_timer.setSingleShot(True)

        # 인터벌 설정
        self.check_interval = 10000  # 10초 간격 탐색
        self.active_click_interval = 500  # 0.5초 간격 클릭

        # 설정값
        self.region: Optional[Tuple[int, int, int, int]] = None
        self.template_path: Optional[str] = None
        self.template_image: Optional[np.ndarray] = None
        self.confidence_threshold: float = 0.8

        # 통계
        self.total_searches = 0
        self.total_clicks = 0
        self.last_click_time: Optional[float] = None

        # 상태 플래그
        self._in_active_click = False

        # 스케일 보정 (다른 크기도 인식)
        self.scale_values = [
            0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9,
            0.95, 1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35,
            1.4, 1.45, 1.5, 1.55, 1.6, 1.65, 1.7, 1.75, 1.8,
            1.85, 1.9, 1.95, 2.0
        ]

    # ------------------------------
    # 설정
    # ------------------------------
    def set_config(
        self,
        region: Tuple[int, int, int, int],
        template_path: str,
        confidence_threshold: float = 0.8
    ):
        """탐색 영역 및 템플릿 이미지 설정"""
        self.region = region
        self.template_path = template_path
        self.confidence_threshold = confidence_threshold

        if template_path and Path(template_path).exists():
            try:
                full_path = resource_path(template_path)
                template_bgr = cv2.imread(full_path, cv2.IMREAD_COLOR)
                if template_bgr is None:
                    self.error_occurred.emit(f"이미지를 로드할 수 없습니다: {template_path}")
                    self.template_image = None
                else:
                    self.template_image = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
                    print(f"템플릿 이미지 로드 성공 (흑백 변환): {template_path}")
            except Exception as e:
                self.error_occurred.emit(f"이미지 로드 중 오류: {e}")
                self.template_image = None
        else:
            self.template_image = None

    # ------------------------------
    # 시작 / 중지
    # ------------------------------
    def start(self):
        """탐색 시작"""
        if self.is_running or not self.region or self.template_image is None:
            if self.template_image is None:
                self.error_occurred.emit("탐색할 이미지가 설정되지 않았습니다.")
            return

        self.is_running = True
        self.total_searches = 0
        self.total_clicks = 0
        self.last_click_time = None
        self._in_active_click = False

        print("이미지 자동 클릭 시작")
        self._schedule_next_search(0)

    def stop(self):
        """탐색 중지"""
        self.is_running = False
        try:
            self.timer.stop()
            self.active_click_timer.stop()
        except Exception:
            pass
        self._in_active_click = False
        print("이미지 자동 클릭 중지됨")

    # ------------------------------
    # 탐색 및 클릭 로직
    # ------------------------------
    def _schedule_next_search(self, delay_ms: int):
        if not self.is_running or self._in_active_click:
            return
        try:
            self.timer.stop()
            self.timer.start(delay_ms)
        except Exception:
            pass

    def _search_phase(self):
        """주기적으로 이미지 탐색"""
        if not self.is_running or not self.region or self.template_image is None:
            return
        try:
            self.total_searches += 1
            found, center = self._locate_image_scaled()
            if found and center:
                self._start_active_click(center)
            else:
                self.image_not_found.emit()
                self._schedule_next_search(self.check_interval)
        except Exception as e:
            self.error_occurred.emit(f"이미지 탐색 중 오류: {e}")
            self._schedule_next_search(self.check_interval)

    def _start_active_click(self, center):
        """이미지 발견 시 클릭 시작"""
        if not self.is_running:
            return
        self.timer.stop()
        self._in_active_click = True
        self.active_click_timer.start(0)

    def _active_click_phase(self):
        """0.5초마다 클릭"""
        if not self.is_running or not self._in_active_click or not self.region or self.template_image is None:
            return
        try:
            found, center = self._locate_image_scaled()
            if found and center:
                x, y = center
                self.image_found.emit(x, y)
                pyautogui.click(x, y)
                self.total_clicks += 1
                self.last_click_time = time.time()
                self.image_clicked.emit(x, y)
                print(f"이미지 클릭 ({self.total_clicks}회)")
                self.active_click_timer.start(self.active_click_interval)
            else:
                # 이미지가 사라졌으면 클릭 종료 후 다시 탐색 시작
                self._finish_active_click()
        except Exception as e:
            self.error_occurred.emit(f"반복 클릭 중 오류: {e}")
            self._finish_active_click()

    def _finish_active_click(self):
        """클릭 루프 종료 후 즉시 탐색 재시작"""
        if not self._in_active_click:
            return
        try:
            self.active_click_timer.stop()
        except Exception:
            pass
        self._in_active_click = False
        self.release_completed.emit()
        print("이미지 사라짐 → 탐색 재개")
        if self.is_running:
            self._schedule_next_search(0)

    # ------------------------------
    # 이미지 탐색
    # ------------------------------
    def _locate_image_scaled(self):
        """여러 스케일로 이미지 매칭 (크기 달라도 인식)"""
        if not self.region or self.template_image is None:
            return False, None

        x1, y1, x2, y2 = self.region
        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        screenshot_np = np.array(screenshot, dtype=np.uint8)
        screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
        screenshot_gray = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)

        del screenshot, screenshot_np, screenshot_bgr

        best_val = 0
        best_loc = None
        best_scale = 1.0
        template_h, template_w = self.template_image.shape[:2]

        for scale in self.scale_values:
            try:
                resized = cv2.resize(self.template_image, (int(template_w * scale), int(template_h * scale)))
            except cv2.error:
                continue
            if resized.shape[0] < 5 or resized.shape[1] < 5:
                continue
            result = cv2.matchTemplate(screenshot_gray, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val > best_val:
                best_val = max_val
                best_loc = max_loc
                best_scale = scale

        del screenshot_gray

        if best_val >= self.confidence_threshold and best_loc is not None:
            resized_h = int(template_h * best_scale)
            resized_w = int(template_w * best_scale)
            cx = best_loc[0] + resized_w // 2
            cy = best_loc[1] + resized_h // 2
            print(f"이미지 감지: 신뢰도 {best_val:.2f}, 스케일 {best_scale:.2f}")
            return True, (x1 + cx, y1 + cy)
        return False, None

    # ------------------------------
    # 통계
    # ------------------------------
    def get_stats(self) -> dict:
        return {
            "total_searches": self.total_searches,
            "total_clicks": self.total_clicks,
            "last_click_time": self.last_click_time
        }
