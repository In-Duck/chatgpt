import asyncio
from typing import Optional, Tuple

from PIL import ImageGrab
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
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
        self.check_interval = 500  # 0.5초 간격으로 변경 (CPU 부담 감소)

        # 설정값
        self.region: Optional[Tuple[int, int, int, int]] = None  # (x1, y1, x2, y2)
        self.telegram_token: Optional[str] = None
        self.telegram_chat_id: Optional[str] = None
        self.user_nickname: str = "유저"
        self.red_threshold = 1

        # 상태
        self.user_present = False
        self.last_check_result: Optional[int] = None  # 이전 체크 결과 캐싱
        
        # 캐시된 이미지 (메모리 최적화)
        self._last_screenshot = None
        self._screenshot_cache_time = 0

    def set_config(
        self,
        region: Tuple[int, int, int, int],
        telegram_token: str,
        telegram_chat_id: str,
        user_nickname: str,
    ):
        """탐지 설정을 업데이트합니다."""
        self.region = region
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.user_nickname = user_nickname

    def start(self):
        """유저 탐색을 시작합니다."""
        if self.is_running or not self.region:
            return

        self.is_running = True
        self.user_present = False
        self.last_check_result = None
        self._last_screenshot = None
        self._screenshot_cache_time = 0
        self._check_region()

    def stop(self):
        """유저 탐색을 중지합니다."""
        self.is_running = False
        self.timer.stop()
        self.last_check_result = None
        self._last_screenshot = None
        self._screenshot_cache_time = 0

    def _check_region(self):
        """특정 구역에서 빨간색을 감지합니다."""
        if not self.is_running or not self.region:
            return

        try:
            # 화면 캡처 (메모리 효율적으로)
            x1, y1, x2, y2 = self.region
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))

            # 빨간색 픽셀 카운트 (최적화된 버전)
            red_pixels = self._count_red_pixels_optimized(screenshot)
            
            # 스크린샷 메모리 해제
            del screenshot

            # 상태 변경 감지
            state_changed = False

            if red_pixels >= self.red_threshold:
                if not self.user_present:
                    self.user_present = True
                    message = f"{self.user_nickname} 유저 발견"
                    self.user_detected.emit(message)
                    self._send_telegram_message(message)
                    state_changed = True
            else:
                if self.user_present:
                    self.user_present = False
                    message = f"{self.user_nickname} 유저 사라짐"
                    self.user_disappeared.emit(message)
                    self._send_telegram_message(message)
                    state_changed = True

            # 이전 결과 갱신
            self.last_check_result = red_pixels

        except Exception as e:
            print(f"구역 체크 중 오류: {e}")

        finally:
            # 타이머 재시작 (무조건 이어지도록 finally로 이동)
            if self.is_running:
                self.timer.start(self.check_interval)

    def _count_red_pixels_optimized(self, image) -> int:
        """최적화된 빨간색 픽셀 카운팅"""
        try:
            import numpy as np

            # NumPy 배열로 변환 (메모리 효율적)
            img_array = np.array(image, dtype=np.uint8)

            # RGB 채널 분리
            r = img_array[:, :, 0]
            g = img_array[:, :, 1]
            b = img_array[:, :, 2]

            # 정확히 빨간색 (255, 0, 0)인 픽셀 찾기
            red_mask = (r >= 200) & (g <= 50) & (b <= 50)
            red_count = int(np.sum(red_mask))
            
            # 메모리 해제
            del img_array, r, g, b, red_mask

            return red_count
        except ImportError:
            # NumPy 없으면 기본 방식 사용
            return self._count_red_pixels(image)
        except Exception as e:
            print(f"픽셀 카운팅 오류: {e}")
            return 0

    def _count_red_pixels(self, image) -> int:
        """기본 빨간색 픽셀 카운팅 (NumPy 없을 때)"""
        try:
            pixels = image.load()
            width, height = image.size
            red_count = 0

            # 샘플링으로 성능 개선 (모든 픽셀 대신 일부만 체크)
            step = 2  # 2픽셀마다 체크
            for x in range(0, width, step):
                for y in range(0, height, step):
                    r, g, b = pixels[x, y][:3]
                    if r >= 200 and g <= 50 and b <= 50:
                        red_count += 1

            # 샘플링한 만큼 보정
            red_count *= (step * step)
            
            return red_count
        except Exception as e:
            print(f"픽셀 카운팅 오류: {e}")
            return 0

    def _send_telegram_message(self, message: str):
        """텔레그램으로 메시지를 전송합니다."""
        if not self.telegram_token or not self.telegram_chat_id:
            return

        try:
            asyncio.run(self._async_send_message(message))
        except RuntimeError as exc:
            # PyQt 환경 등에서 이벤트 루프가 이미 실행 중인 경우를 대비한 폴백
            if "asyncio.run() cannot be called" in str(exc):
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(self._async_send_message(message))
                finally:
                    loop.close()
            else:
                print(f"텔레그램 메시지 전송 실패: {exc}")

    async def _async_send_message(self, message: str):
        """비동기로 텔레그램 메시지를 전송합니다."""
        bot: Optional[Bot] = None
        try:
            bot = Bot(token=self.telegram_token)
            await bot.send_message(chat_id=self.telegram_chat_id, text=message)
        except Exception as e:
            print(f"비동기 메시지 전송 실패: {e}")
        finally:
            if bot is not None:
                session = getattr(bot, "session", None)
                if session is not None and not session.closed:
                    await session.close()