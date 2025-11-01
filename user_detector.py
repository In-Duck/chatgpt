import time
from PIL import ImageGrab
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from typing import Optional, Tuple
import asyncio
from telegram import Bot


class UserDetector(QObject):
    """특정 구역에서 빨간색을 감지하여 텔레그램 알람을 보내는 클래스"""
    
    user_detected = pyqtSignal(str)  # 유저 발견
    user_disappeared = pyqtSignal(str)  # 유저 사라짐
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_region)
        self.timer.setSingleShot(True)  # 단발성 타이머로 설정하여 메모리 최적화
        self.check_interval = 500  # 500ms 간격으로 체크 (사용자 요청에 따라 유지)
        
        # 설정값
        self.region: Optional[Tuple[int, int, int, int]] = None  # (x1, y1, x2, y2)
        self.telegram_token: Optional[str] = None
        self.telegram_chat_id: Optional[str] = None
        self.user_nickname: str = "유저"
        self.red_threshold = 2  # 빨간색 픽셀 임계값 (2픽셀)
        
        # 상태
        self.user_present = False
        self.bot: Optional[Bot] = None
        self.last_check_result = None  # 이전 체크 결과 캐싱
    
    def set_config(self, region: Tuple[int, int, int, int], telegram_token: str, 
                   telegram_chat_id: str, user_nickname: str):
        """탐지 설정을 업데이트합니다."""
        self.region = region
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.user_nickname = user_nickname
        
        # 텔레그램 봇 초기화
        if telegram_token:
            try:
                self.bot = Bot(token=telegram_token)
            except Exception as e:
                print(f"텔레그램 봇 초기화 실패: {e}")
                self.bot = None
    
    def start(self):
        """유저 탐색을 시작합니다."""
        if self.is_running or not self.region:
            return
        
        self.is_running = True
        self.user_present = False
        self.last_check_result = None
        self._check_region()
    
    def stop(self):
        """유저 탐색을 중지합니다."""
        self.is_running = False
        self.timer.stop()
        self.last_check_result = None
    
    def _check_region(self):
        """특정 구역에서 빨간색을 감지합니다."""
        if not self.is_running or not self.region:
            return
        
        try:
            # 화면 캡처
            x1, y1, x2, y2 = self.region
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            
            # 빨간색 픽셀 카운트 (최적화된 버전)
            red_pixels = self._count_red_pixels_optimized(screenshot)
            
            # 이전 결과와 동일하면 스킵 (CPU 최적화)
            if red_pixels == self.last_check_result:
                if self.is_running:
                    self.timer.start(self.check_interval)
                return
            
            self.last_check_result = red_pixels
            
            # 빨간색이 임계값 이상이면 유저 발견
            if red_pixels >= self.red_threshold:
                if not self.user_present:
                    self.user_present = True
                    message = f"{self.user_nickname} 유저 발견"
                    self.user_detected.emit(message)
                    self._send_telegram_message(message)
            else:
                if self.user_present:
                    self.user_present = False
                    message = f"{self.user_nickname} 유저 사라짐"
                    self.user_disappeared.emit(message)
                    self._send_telegram_message(message)
        
        except Exception as e:
            print(f"구역 체크 중 오류: {e}")
        
        # 다음 체크 예약
        if self.is_running:
            self.timer.start(self.check_interval)
    
    def _count_red_pixels_optimized(self, image) -> int:
        """이미지에서 정확히 빨간색(255, 0, 0) 픽셀 수를 카운트합니다. (최적화 버전)"""
        try:
            # numpy를 사용한 최적화 버전
            import numpy as np
            
            img_array = np.array(image)
            
            # RGB 채널 분리
            r = img_array[:, :, 0]
            g = img_array[:, :, 1]
            b = img_array[:, :, 2]
            
            # 정확히 빨간색 (255, 0, 0)인 픽셀 찾기
            red_mask = (r == 255) & (g == 0) & (b == 0)
            red_count = np.sum(red_mask)
            
            return int(red_count)
        except ImportError:
            # numpy가 없는 경우 기존 방식 사용
            return self._count_red_pixels(image)
    
    def _count_red_pixels(self, image) -> int:
        """이미지에서 정확히 빨간색(255, 0, 0) 픽셀 수를 카운트합니다. (기본 버전)"""
        pixels = image.load()
        width, height = image.size
        red_count = 0
        
        for x in range(width):
            for y in range(height):
                r, g, b = pixels[x, y][:3]
                # 정확히 빨간색 (255, 0, 0)만 감지
                if r == 255 and g == 0 and b == 0:
                    red_count += 1
        
        return red_count
    
    def _send_telegram_message(self, message: str):
        """텔레그램으로 메시지를 전송합니다."""
        if not self.bot or not self.telegram_chat_id:
            return
        
        try:
            # 비동기 함수를 동기적으로 실행
            asyncio.run(self._async_send_message(message))
        except Exception as e:
            print(f"텔레그램 메시지 전송 실패: {e}")
    
    async def _async_send_message(self, message: str):
        """비동기로 텔레그램 메시지를 전송합니다."""
        try:
            await self.bot.send_message(chat_id=self.telegram_chat_id, text=message)
        except Exception as e:
            print(f"비동기 메시지 전송 실패: {e}")