"""
이미지 감지 및 텔레그램 알림
특정 이미지가 화면에 나타나면 텔레그램으로 알림을 보냅니다.
"""
import asyncio
import threading
import time
from typing import Optional, Tuple, List
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import pyautogui
import cv2
import numpy as np
from PIL import ImageGrab
from telegram import Bot
from telegram.error import TelegramError


class ImageDetector(QObject):
    """이미지 감지 및 텔레그램 알림 클래스"""
    
    image_detected = pyqtSignal(str)  # 이미지 감지 시그널
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.detection_region: Optional[Tuple[int, int, int, int]] = None
        self.template_images: List[np.ndarray] = []
        self.confidence_threshold = 0.7
        self.check_interval = 500  # 500ms 간격으로 체크
        
        # 텔레그램 설정
        self.telegram_token: Optional[str] = None
        self.telegram_chat_id: Optional[str] = None
        self.user_nickname: str = "유저"
        
        # 타이머
        self.check_timer: Optional[QTimer] = None
        
        # 감지 상태
        self.last_detected = False
        self.detection_count = 0
        
        # 텔레그램 봇
        self.bot: Optional[Bot] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.bot_thread: Optional[threading.Thread] = None
        
        # 반복 알림 관련
        self.repeat_timer: Optional[QTimer] = None
        self.repeat_count = 0
        self.max_repeat_count = 10
        self.repeat_interval = 6000  # 6초
        self.is_repeating = False
        self.user_responded = False
        
    def set_config(
        self,
        detection_region: Tuple[int, int, int, int],
        template_paths: List[str],
        telegram_token: str,
        telegram_chat_id: str,
        user_nickname: str,
        confidence: float = 0.7
    ):
        """설정을 업데이트합니다."""
        self.detection_region = detection_region
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.user_nickname = user_nickname
        self.confidence_threshold = confidence
        
        # 템플릿 이미지 로드 (흑백으로 변환)
        self.template_images = []
        for path in template_paths:
            try:
                template = cv2.imread(path)
                if template is not None:
                    # BGR을 그레이스케일로 변환하여 인식률 향상
                    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                    self.template_images.append(template_gray)
                    print(f"템플릿 이미지 로드 성공 (흑백 변환): {path}")
                else:
                    print(f"템플릿 이미지 로드 실패: {path}")
            except Exception as e:
                print(f"템플릿 이미지 로드 오류 ({path}): {e}")
        
        # 텔레그램 봇 초기화
        if self.telegram_token:
            self._init_telegram_bot()
    
    def _init_telegram_bot(self):
        """텔레그램 봇 초기화"""
        try:
            self.bot = Bot(token=self.telegram_token)
            
            # 이벤트 루프 생성
            self.loop = asyncio.new_event_loop()
            
            def run_loop():
                asyncio.set_event_loop(self.loop)
                self.loop.run_forever()
            
            self.bot_thread = threading.Thread(target=run_loop, daemon=True)
            self.bot_thread.start()
            
            print("텔레그램 봇 초기화 완료")
        except Exception as e:
            print(f"텔레그램 봇 초기화 실패: {e}")
    
    def start(self):
        """이미지 감지를 시작합니다."""
        if self.is_running or not self.detection_region or not self.template_images:
            return
        
        if not self.telegram_token or not self.telegram_chat_id:
            print("텔레그램 설정이 없습니다.")
            return
        
        self.is_running = True
        self.last_detected = False
        self.detection_count = 0
        self.is_repeating = False
        self.user_responded = False
        
        print(f"이미지 감지 시작: 구역={self.detection_region}, 템플릿 수={len(self.template_images)}")
        
        # 타이머 시작
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._check_image)
        self.check_timer.start(self.check_interval)
    
    def stop(self):
        """이미지 감지를 중지합니다."""
        print("이미지 감지 중지 시작...")
        self.is_running = False
        
        if self.check_timer:
            self.check_timer.stop()
            self.check_timer = None
        
        if self.repeat_timer:
            self.repeat_timer.stop()
            self.repeat_timer = None
        
        self.is_repeating = False
        self.user_responded = False
        
        # 이벤트 루프 정리
        if self.loop and not self.loop.is_closed():
            try:
                if self.loop.is_running():
                    self.loop.call_soon_threadsafe(self.loop.stop)
                    time.sleep(0.5)
            except Exception as e:
                print(f"이벤트 루프 중지 중 오류: {e}")
        
        print("이미지 감지 중지 완료")
    
    def _check_image(self):
        """이미지를 체크합니다."""
        if not self.is_running:
            return
        
        try:
            # 화면 캡처
            x1, y1, x2, y2 = self.detection_region
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            screenshot_np = np.array(screenshot)
            screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
            
            # 스크린샷을 그레이스케일로 변환하여 인식률 향상
            screenshot_gray = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)
            
            # 스크린샷 크기 확인
            screenshot_h, screenshot_w = screenshot_gray.shape[:2]
            
            # 각 템플릿 이미지와 매칭
            detected = False
            for template in self.template_images:
                # 템플릿 크기 확인
                template_h, template_w = template.shape[:2]
                
                # 템플릿이 스크린샷보다 크면 스킵 (OpenCV 오류 방지)
                if template_h > screenshot_h or template_w > screenshot_w:
                    print(f"템플릿 크기({template_w}x{template_h})가 스크린샷 크기({screenshot_w}x{screenshot_h})보다 큽니다. 스킵합니다.")
                    continue
                
                try:
                    # 그레이스케일 이미지로 매칭 (인식률 향상)
                    result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    
                    if max_val >= self.confidence_threshold:
                        detected = True
                        print(f"이미지 감지! 신뢰도: {max_val:.2f} (흑백 매칭)")
                        break
                except cv2.error as e:
                    print(f"템플릿 매칭 중 OpenCV 오류: {e}")
                    continue
            
            # 상태 변화 감지
            if detected and not self.last_detected:
                # 이미지가 나타남 - 반복 알림 시작
                self.detection_count += 1
                self.last_detected = True
                self.is_repeating = True
                self.repeat_count = 0
                self.user_responded = False
                
                # 첫 번째 메시지 전송
                self._send_repeat_message()
                
                # 반복 타이머 시작
                if self.repeat_timer:
                    self.repeat_timer.stop()
                self.repeat_timer = QTimer()
                self.repeat_timer.timeout.connect(self._send_repeat_message)
                self.repeat_timer.start(self.repeat_interval)
                
                self.image_detected.emit(f"거탐 이미지 감지: 감지 #{self.detection_count}")
                
            elif not detected and self.last_detected:
                # 이미지가 사라짐 - 반복 알림 중지
                self.last_detected = False
                self.is_repeating = False
                
                if self.repeat_timer:
                    self.repeat_timer.stop()
                    self.repeat_timer = None
                
                message = f"✅ {self.user_nickname} 거탐 사라짐"
                self._send_telegram_message(message)
                self.image_detected.emit("거탐 이미지 사라짐")
                
        except Exception as e:
            print(f"이미지 체크 중 오류: {e}")
    
    def _send_repeat_message(self):
        """반복 메시지 전송"""
        if not self.is_repeating or self.user_responded:
            if self.repeat_timer:
                self.repeat_timer.stop()
                self.repeat_timer = None
            return
        
        self.repeat_count += 1
        
        if self.repeat_count > self.max_repeat_count:
            # 최대 반복 횟수 도달
            self.is_repeating = False
            if self.repeat_timer:
                self.repeat_timer.stop()
                self.repeat_timer = None
            return
        
        message = f"🚨 {self.user_nickname} 거탐 감지됨 ({self.repeat_count}/{self.max_repeat_count})"
        self._send_telegram_message(message)
        print(f"반복 메시지 전송: {self.repeat_count}/{self.max_repeat_count}")
    
    def _send_telegram_message(self, message: str):
        """텔레그램으로 메시지를 전송합니다."""
        if not self.bot or not self.loop or not self.telegram_chat_id:
            return
        
        try:
            asyncio.run_coroutine_threadsafe(
                self._async_send_message(message),
                self.loop
            )
        except Exception as e:
            print(f"메시지 전송 실패: {e}")
    
    async def _async_send_message(self, message: str):
        """비동기로 텔레그램 메시지를 전송합니다."""
        try:
            await self.bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message
            )
            print(f"텔레그램 메시지 전송 성공: {message}")
        except TelegramError as e:
            print(f"텔레그램 메시지 전송 오류: {e}")
        except Exception as e:
            print(f"메시지 전송 오류: {e}")