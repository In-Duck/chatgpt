import time
from typing import Optional, Tuple
from pathlib import Path

import cv2
import numpy as np
import pyautogui
from PIL import ImageGrab
from PyQt5.QtCore import QObject, QTimer, pyqtSignal


class ImageClickerWorker(QObject):
    """특정 이미지를 감지하고 클릭하는 클래스"""
    
    image_found = pyqtSignal(int, int)  # x, y 좌표
    image_clicked = pyqtSignal(int, int)  # x, y 좌표
    image_not_found = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._search_and_click)
        self.timer.setSingleShot(True)
        self.check_interval = 1000  # 1초 간격으로 변경 (CPU 부담 감소)
        
        # 설정값
        self.region: Optional[Tuple[int, int, int, int]] = None  # (x1, y1, x2, y2)
        self.template_path: Optional[str] = None
        self.template_image: Optional[np.ndarray] = None
        self.confidence_threshold: float = 0.8  # 매칭 신뢰도 임계값
        
        # 통계
        self.total_searches = 0
        self.total_clicks = 0
        self.last_click_time: Optional[float] = None
        
        # 캐시 (메모리 최적화)
        self._last_screenshot = None
        self._screenshot_cache_time = 0
    
    def set_config(
        self,
        region: Tuple[int, int, int, int],
        template_path: str,
        confidence_threshold: float = 0.8
    ):
        """이미지 클릭 설정을 업데이트합니다."""
        self.region = region
        self.template_path = template_path
        self.confidence_threshold = confidence_threshold
        
        # 템플릿 이미지 로드 (흑백으로 변환하여 인식률 향상)
        if template_path and Path(template_path).exists():
            try:
                template_bgr = cv2.imread(template_path, cv2.IMREAD_COLOR)
                if template_bgr is None:
                    self.error_occurred.emit(f"이미지를 로드할 수 없습니다: {template_path}")
                    self.template_image = None
                else:
                    # BGR을 그레이스케일로 변환하여 인식률 향상
                    self.template_image = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
                    print(f"템플릿 이미지 로드 성공 (흑백 변환): {template_path}")
            except Exception as e:
                self.error_occurred.emit(f"이미지 로드 중 오류: {e}")
                self.template_image = None
        else:
            self.template_image = None
    
    def start(self):
        """이미지 탐색 및 클릭을 시작합니다."""
        if self.is_running or not self.region or self.template_image is None:
            if self.template_image is None:
                self.error_occurred.emit("탐색할 이미지가 설정되지 않았습니다.")
            return
        
        self.is_running = True
        self.total_searches = 0
        self.total_clicks = 0
        self.last_click_time = None
        self._last_screenshot = None
        self._screenshot_cache_time = 0
        self._search_and_click()
    
    def stop(self):
        """이미지 탐색 및 클릭을 중지합니다."""
        self.is_running = False
        self.timer.stop()
        self._last_screenshot = None
        self._screenshot_cache_time = 0
    
    def _search_and_click(self):
        """이미지를 탐색하고 발견하면 클릭합니다."""
        if not self.is_running or not self.region or self.template_image is None:
            return
        
        try:
            self.total_searches += 1
            
            # 화면 캡처
            x1, y1, x2, y2 = self.region
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            screenshot_np = np.array(screenshot, dtype=np.uint8)
            screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
            
            # 스크린샷을 그레이스케일로 변환하여 인식률 향상
            screenshot_gray = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)
            
            # 메모리 해제
            del screenshot, screenshot_np, screenshot_bgr
            
            # 템플릿 매칭 (그레이스케일 이미지로 매칭)
            result = cv2.matchTemplate(screenshot_gray, self.template_image, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # 메모리 해제
            del screenshot_gray, result
            
            # 신뢰도 확인
            if max_val >= self.confidence_threshold:
                # 템플릿의 중심 좌표 계산
                template_h, template_w = self.template_image.shape[:2]
                center_x = max_loc[0] + template_w // 2
                center_y = max_loc[1] + template_h // 2
                
                # 절대 좌표로 변환
                absolute_x = x1 + center_x
                absolute_y = y1 + center_y
                
                self.image_found.emit(absolute_x, absolute_y)
                
                # 클릭 수행
                pyautogui.click(absolute_x, absolute_y)
                self.total_clicks += 1
                self.last_click_time = time.time()
                self.image_clicked.emit(absolute_x, absolute_y)
                
                print(f"이미지 클릭 성공! 신뢰도: {max_val:.2f} (흑백 매칭)")
                
                # 클릭 후 짧은 대기 (중복 클릭 방지)
                time.sleep(0.1)
            else:
                self.image_not_found.emit()
        
        except Exception as e:
            self.error_occurred.emit(f"이미지 탐색 중 오류: {e}")
        
        finally:
            # 타이머 재시작
            if self.is_running:
                self.timer.start(self.check_interval)
    
    def get_stats(self) -> dict:
        """통계 정보를 반환합니다."""
        return {
            "total_searches": self.total_searches,
            "total_clicks": self.total_clicks,
            "last_click_time": self.last_click_time
        }