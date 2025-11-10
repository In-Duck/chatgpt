import asyncio
import threading
import time
from queue import Empty, Queue
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
        self.check_interval = 200

        # 설정값
        self.region: Optional[Tuple[int, int, int, int]] = None  # (x1, y1, x2, y2)
        self.telegram_token: Optional[str] = None
        self.telegram_chat_id: Optional[str] = None
        self.user_nickname: str = "유저"
        self.red_threshold = 1

        # 상태
        self.user_present = False
        self.last_check_result: Optional[int] = None  # 이전 체크 결과 캐싱

        # 텔레그램 전송 관리
        self._send_queue: "Queue[str]" = Queue()
        self._sender_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

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

        # shutdown()으로 중지된 뒤 다시 시작될 때를 대비해 전송 워커 상태를 초기화
        self._stop_event.clear()
        self._ensure_sender_thread()

        self.is_running = True
        self.user_present = False
        self.last_check_result = None
        self._check_region()

    def stop(self):
        """유저 탐색을 중지합니다."""
        self.is_running = False
        self.timer.stop()
        self.last_check_result = None
        self.user_present = False

    def _check_region(self):
        """특정 구역에서 빨간색을 감지합니다."""
        if not self.is_running or not self.region:
            return

        try:
            # 화면 캡처
            x1, y1, x2, y2 = self.region
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))

            # 빨간색 픽셀 카운트
            red_pixels = self._count_red_pixels_optimized(screenshot)

            # --- 중요 변경 ---
            # 이전 결과와 같더라도 상태(user_present)가 다를 수 있으므로 단순히 return 하지 않음
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

            # 디버깅 로그
            # print(f"[DEBUG] red_pixels={red_pixels}, user_present={self.user_present}, state_changed={state_changed}")

        except Exception as e:
            print(f"구역 체크 중 오류: {e}")

        finally:
            # 타이머 재시작 (무조건 이어지도록 finally로 이동)
            if self.is_running:
                self.timer.start(self.check_interval)

    def _count_red_pixels_optimized(self, image) -> int:
        try:
            import numpy as np

            img_array = np.array(image)

            # RGB 채널 분리
            r = img_array[:, :, 0]
            g = img_array[:, :, 1]
            b = img_array[:, :, 2]

            # 정확히 빨간색 (255, 0, 0)인 픽셀 찾기
            red_mask = (r >= 200) & (g <= 50) & (b <= 50)
            red_count = int(np.sum(red_mask))

            return red_count
        except ImportError:
            return self._count_red_pixels(image)

    def _count_red_pixels(self, image) -> int:
        pixels = image.load()
        width, height = image.size
        red_count = 0

        for x in range(width):
            for y in range(height):
                r, g, b = pixels[x, y][:3]
                # 정확히 빨간색 (255, 0, 0)만 감지
                if r >= 200 and g <= 50 and b <= 50:
                    red_count += 1

        return red_count

    def _send_telegram_message(self, message: str):
        """텔레그램으로 메시지를 전송합니다."""
        if not self.telegram_token or not self.telegram_chat_id:
            return

        if self._stop_event.is_set():
            return

        self._ensure_sender_thread()
        self._send_queue.put(message)

    def _ensure_sender_thread(self):
        """전송용 백그라운드 스레드가 실행 중인지 확인합니다."""
        if self._sender_thread and self._sender_thread.is_alive():
            return

        self._stop_event.clear()
        self._sender_thread = threading.Thread(
            target=self._sender_worker,
            name="TelegramSender",
            daemon=True,
        )
        self._sender_thread.start()

    def _sender_worker(self):
        """텔레그램 메시지를 순차적으로 전송하는 워커."""
        while True:
            try:
                message = self._send_queue.get(timeout=0.2)
            except Empty:
                if self._stop_event.is_set():
                    break
                continue

            self._send_with_retry(message)
            self._send_queue.task_done()

        # 남은 항목 정리
        while True:
            try:
                self._send_queue.get_nowait()
                self._send_queue.task_done()
            except Empty:
                break

    def _send_with_retry(self, message: str, retries: int = 3):
        """전송 실패 시 재시도합니다."""
        for attempt in range(1, retries + 1):
            try:
                asyncio.run(self._async_send_message(message))
                return
            except Exception as exc:
                print(f"텔레그램 메시지 전송 실패({attempt}/{retries}): {exc}")
                if attempt < retries:
                    time.sleep(0.5)
        else:
            print("텔레그램 메시지 전송이 반복 실패하여 포기합니다.")

    def shutdown(self):
        """전송 스레드를 정리합니다."""
        self._stop_event.set()

        if self._sender_thread and self._sender_thread.is_alive():
            # 대기 중인 메시지를 모두 처리하도록 기다립니다.
            self._send_queue.join()
            self._sender_thread.join(timeout=1.0)

        self._sender_thread = None

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
