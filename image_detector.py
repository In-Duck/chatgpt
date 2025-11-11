"""
이미지 감지 및 텔레그램 알림 (pyautogui 버전)
- pyautogui를 사용한 간단한 이미지 인식
- 전체 이미지가 구역 내에 있어야 감지
- 감지 시 구역 스크린샷 + 매칭 위치 표시
"""
import asyncio
import threading
import time
import io
from typing import Optional, Tuple, List
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import pyautogui
from PIL import ImageGrab, Image, ImageDraw
from telegram import Bot
from telegram.error import TelegramError
from utils import resource_path


class ImageDetector(QObject):
    """이미지 감지 및 텔레그램 알림 클래스 (pyautogui 사용)"""

    image_detected = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.detection_region: Optional[Tuple[int, int, int, int]] = None
        
        # 템플릿 경로 목록
        self.template_paths: List[str] = []
        self.confidence_threshold = 0.8
        self.check_interval = 5000  # 5초

        # 텔레그램 설정
        self.telegram_token: Optional[str] = None
        self.telegram_chat_id: Optional[str] = None
        self.user_nickname: str = "유저"

        # 타이머
        self.check_timer: Optional[QTimer] = None

        # 감지 상태
        self.last_detected = False
        self.detection_count = 0
        self.last_screenshot: Optional[Image.Image] = None
        self.last_matched_location: Optional[Tuple[int, int, int, int]] = None
        self.last_matched_template: Optional[str] = None

        # 텔레그램 봇
        self.bot: Optional[Bot] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.bot_thread: Optional[threading.Thread] = None

        # 반복 알림 관련
        self.repeat_timer: Optional[QTimer] = None
        self.repeat_count = 0
        self.max_repeat_count = 10
        self.repeat_interval = 6000
        self.is_repeating = False
        self.user_responded = False
        self.screenshot_sent = False

    def set_config(
        self,
        detection_region: Tuple[int, int, int, int],
        template_paths: List[str],
        telegram_token: str,
        telegram_chat_id: str,
        user_nickname: str,
        confidence: float = 0.85
    ):
        """설정을 업데이트합니다."""
        self.detection_region = detection_region
        self.template_paths = template_paths
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.user_nickname = user_nickname
        self.confidence_threshold = confidence

        print(f"이미지 감지 설정: 구역={detection_region}, 템플릿 {len(template_paths)}개, 신뢰도={confidence}")

        if self.telegram_token:
            self._init_telegram_bot()

    def _init_telegram_bot(self):
        """텔레그램 봇 초기화"""
        try:
            if self.loop and not self.loop.is_closed():
                self.loop.call_soon_threadsafe(self.loop.stop)
                time.sleep(0.3)
                try:
                    self.loop.close()
                except Exception:
                    pass

            self.loop = asyncio.new_event_loop()
            self.bot = Bot(token=self.telegram_token)

            def run_loop():
                asyncio.set_event_loop(self.loop)
                self.loop.run_forever()

            self.bot_thread = threading.Thread(target=run_loop, daemon=True)
            self.bot_thread.start()
            print("텔레그램 봇 초기화 완료")
        except Exception as e:
            print(f"텔레그램 봇 초기화 실패: {e}")

    def start(self):
        """이미지 감지 시작"""
        if self.is_running or not self.detection_region or not self.template_paths:
            return
        if not self.telegram_token or not self.telegram_chat_id:
            print("텔레그램 설정이 없습니다.")
            return

        self._init_telegram_bot()

        self.is_running = True
        self.last_detected = False
        self.detection_count = 0
        self.is_repeating = False
        self.user_responded = False
        self.screenshot_sent = False

        print(f"이미지 감지 시작: 구역={self.detection_region}, 템플릿 {len(self.template_paths)}개")

        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._check_image)
        self.check_timer.start(self.check_interval)
        self._check_image()

    def stop(self):
        """이미지 감지 중지"""
        print("이미지 감지 중지 시작...")
        self.is_running = False

        for timer in [self.check_timer, self.repeat_timer]:
            if timer:
                timer.stop()
        self.check_timer = None
        self.repeat_timer = None

        try:
            if self.loop:
                if self.loop.is_running():
                    self.loop.call_soon_threadsafe(self.loop.stop)
                    time.sleep(0.5)
                if not self.loop.is_closed():
                    self.loop.close()
            if self.bot_thread and self.bot_thread.is_alive():
                self.bot_thread.join(timeout=1)
        except Exception as e:
            print(f"이벤트 루프 정리 오류: {e}")

        self.loop = None
        self.bot_thread = None
        self.bot = None
        print("이미지 감지 중지 완료")

    def _check_image(self):
        """이미지 감지 수행 - 전체 이미지가 구역 내에 있어야 함"""
        if not self.is_running:
            return
            
        try:
            x1, y1, x2, y2 = self.detection_region
            region_width = x2 - x1
            region_height = y2 - y1
            
            # 모든 템플릿에 대해 검색
            detected = False
            best_box = None
            best_template = None

            for template_path in self.template_paths:
                try:
                    template_full_path = resource_path(template_path)
                    
                    # 템플릿 이미지 로드하여 크기 확인
                    template_img = Image.open(template_full_path)
                    template_width, template_height = template_img.size
                    
                    # pyautogui로 이미지 찾기 (구역 내에서만 검색)
                    location = pyautogui.locateOnScreen(
                        template_full_path,
                        confidence=self.confidence_threshold,
                        region=(x1, y1, region_width, region_height)
                    )

                    if location:
                        # location은 (left, top, width, height) 형식
                        left, top, width, height = location
                        right = left + width
                        bottom = top + height
                        
                        # 전체 이미지가 구역 내에 있는지 확인
                        if left >= x1 and top >= y1 and right <= x2 and bottom <= y2:
                            detected = True
                            best_box = (left, top, right, bottom)
                            best_template = template_path
                            print(f"✓ 전체 이미지 감지: {template_path} at ({left}, {top}, {right}, {bottom})")
                            break  # 첫 번째 매칭 발견 시 중단
                        else:
                            print(f"✗ 부분 이미지 감지 (무시): {template_path} - 구역 밖으로 벗어남")

                except Exception as e:
                    print(f"템플릿 {template_path} 검색 오류: {e}")
                    continue

            if detected and not self.last_detected:
                self.detection_count += 1
                self.last_detected = True
                self.is_repeating = True
                self.repeat_count = 0
                self.screenshot_sent = False
                self.last_matched_location = best_box
                self.last_matched_template = best_template

                left, top, right, bottom = best_box
                print(f"이미지 감지! 위치: ({left}, {top}, {right}, {bottom}), 템플릿: {best_template}")

                # 구역 스크린샷 캡처 및 매칭 위치 표시하여 전송
                self._send_first_detection(best_box, best_template)

                if self.repeat_timer:
                    self.repeat_timer.stop()
                self.repeat_timer = QTimer()
                self.repeat_timer.timeout.connect(self._send_repeat_message)
                self.repeat_timer.start(self.repeat_interval)
                self.image_detected.emit(f"거탐 이미지 감지: 감지 #{self.detection_count}")

            elif not detected and self.last_detected:
                self.last_detected = False
                self.is_repeating = False
                if self.repeat_timer:
                    self.repeat_timer.stop()
                    self.repeat_timer = None
                msg = f"✅ {self.user_nickname} 거탐 사라짐"
                self._send_telegram_message(msg)
                self.image_detected.emit("거탐 이미지 사라짐")

        except Exception as e:
            print(f"이미지 체크 오류: {e}")

    def _send_first_detection(self, match_box: Tuple[int, int, int, int], template_name: str):
        """첫 감지 시 구역 스크린샷 + 매칭 위치 표시하여 전송"""
        if not self.screenshot_sent:
            try:
                x1, y1, x2, y2 = self.detection_region
                left, top, right, bottom = match_box
                
                # 구역 전체 스크린샷 캡처
                screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                
                # 매칭된 위치에 빨간 테두리 그리기
                draw = ImageDraw.Draw(screenshot)
                # 좌표를 구역 기준으로 변환
                box_left = left - x1
                box_top = top - y1
                box_right = right - x1
                box_bottom = bottom - y1
                
                # 빨간 테두리 (두께 3픽셀)
                for i in range(3):
                    draw.rectangle(
                        [box_left - i, box_top - i, box_right + i, box_bottom + i],
                        outline='red',
                        width=1
                    )
                
                msg = (
                    f"🚨 {self.user_nickname} 거탐 감지됨 (1/{self.max_repeat_count})\n"
                    f"매칭 위치: ({left}, {top}, {right}, {bottom})\n"
                    f"매칭 템플릿: {template_name}\n"
                    f"감지 구역: ({x1}, {y1}, {x2}, {y2})"
                )
                self._send_telegram_photo(screenshot, msg)
                self.screenshot_sent = True
                self.repeat_count = 1
                print(f"첫 감지 메시지 + 스크린샷 전송 (매칭 위치 표시)")
            except Exception as e:
                print(f"스크린샷 전송 오류: {e}")
                msg = f"🚨 {self.user_nickname} 거탐 감지됨 (1/{self.max_repeat_count})"
                self._send_telegram_message(msg)
                self.screenshot_sent = True
                self.repeat_count = 1

    def _send_repeat_message(self):
        """반복 메시지 전송"""
        if not self.is_repeating or self.user_responded:
            if self.repeat_timer:
                self.repeat_timer.stop()
                self.repeat_timer = None
            return
            
        self.repeat_count += 1
        if self.repeat_count > self.max_repeat_count:
            self.is_repeating = False
            if self.repeat_timer:
                self.repeat_timer.stop()
                self.repeat_timer = None
            return
            
        msg = f"🚨 {self.user_nickname} 거탐 감지됨 ({self.repeat_count}/{self.max_repeat_count})"
        self._send_telegram_message(msg)
        print(f"반복 메시지 전송: {self.repeat_count}/{self.max_repeat_count}")

    def _send_telegram_message(self, message: str):
        """텔레그램으로 텍스트 메시지 전송"""
        if not self.bot or not self.loop or not self.telegram_chat_id:
            self._init_telegram_bot()

        try:
            if not self.loop.is_running():
                raise RuntimeError("이벤트 루프가 실행 중이 아님")

            asyncio.run_coroutine_threadsafe(
                self._async_send_message(message),
                self.loop
            )
        except Exception as e:
            print(f"메시지 전송 실패: {e}")

    def _send_telegram_photo(self, image: Image.Image, caption: str):
        """텔레그램으로 사진 전송"""
        if not self.bot or not self.loop or not self.telegram_chat_id:
            self._init_telegram_bot()

        try:
            if not self.loop.is_running():
                raise RuntimeError("이벤트 루프가 실행 중이 아님")

            asyncio.run_coroutine_threadsafe(
                self._async_send_photo(image, caption),
                self.loop
            )
        except Exception as e:
            print(f"사진 전송 실패: {e}")
    
    def send_notification(self, message: str):
        """외부에서 호출할 수 있는 텔레그램 알림 전송 함수"""
        if not self.telegram_token or not self.telegram_chat_id:
            print("텔레그램 설정이 없어 메시지를 보낼 수 없습니다.")
            return

        if not self.bot or not self.loop or (self.loop and self.loop.is_closed()):
            self._init_telegram_bot()

        try:
            self._send_telegram_message(message)
        except Exception as e:
            print(f"텔레그램 알림 전송 실패: {e}")

    async def _async_send_message(self, message: str):
        """비동기 메시지 전송"""
        try:
            await self.bot.send_message(chat_id=self.telegram_chat_id, text=message)
            print(f"텔레그램 메시지 전송 성공: {message}")
        except TelegramError as e:
            print(f"텔레그램 오류: {e}")
        except Exception as e:
            print(f"전송 오류: {e}")

    async def _async_send_photo(self, image: Image.Image, caption: str):
        """비동기 사진 전송"""
        try:
            bio = io.BytesIO()
            image.save(bio, format='PNG')
            bio.seek(0)
            
            await self.bot.send_photo(
                chat_id=self.telegram_chat_id,
                photo=bio,
                caption=caption
            )
            print(f"텔레그램 사진 전송 성공: {caption}")
        except TelegramError as e:
            print(f"텔레그램 오류: {e}")
        except Exception as e:
            print(f"사진 전송 오류: {e}")