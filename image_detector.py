"""
이미지 감지 및 텔레그램 알림
특정 이미지가 화면에 나타나면 텔레그램으로 알림을 보냅니다.
"""
import asyncio
import threading
import time
from typing import Optional, Tuple, List, Dict
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import cv2
import numpy as np
from PIL import ImageGrab
from telegram import Bot
from telegram.error import TelegramError


class ImageDetector(QObject):
    """이미지 감지 및 텔레그램 알림 클래스"""

    image_detected = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.detection_region: Optional[Tuple[int, int, int, int]] = None
        self.template_variants: List[Dict[str, object]] = []
        self.template_source_count: int = 0
        self.scale_values = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9,
                             0.95, 1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35,
                             1.4, 1.45, 1.5, 1.55, 1.6, 1.65, 1.7, 1.75, 1.8,
                             1.85, 1.9, 1.95, 2.0]
        self.angle_values = [-45, -30, -15, 0, 15, 30, 45]
        self.confidence_threshold = 0.7
        self.check_interval = 10000  # 10초

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
        self.repeat_interval = 6000
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

        self.template_variants = []
        self.template_source_count = len(template_paths)
        for path in template_paths:
            try:
                template = cv2.imread(path)
                if template is None:
                    print(f"템플릿 이미지 로드 실패: {path}")
                    continue
                template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                variants = self._generate_template_variants(template_gray, path)
                if variants:
                    self.template_variants.extend(variants)
                    print(f"템플릿 로드 성공 (변형 {len(variants)}개): {path}")
            except Exception as e:
                print(f"템플릿 이미지 로드 오류 ({path}): {e}")

        if self.telegram_token:
            self._init_telegram_bot()

    def _init_telegram_bot(self):
        """텔레그램 봇 초기화"""
        try:
            # 기존 루프가 살아있다면 닫기
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
        if self.is_running or not self.detection_region or not self.template_variants:
            return
        if not self.telegram_token or not self.telegram_chat_id:
            print("텔레그램 설정이 없습니다.")
            return

        # 항상 새로운 봇 루프 보장
        self._init_telegram_bot()

        self.is_running = True
        self.last_detected = False
        self.detection_count = 0
        self.is_repeating = False
        self.user_responded = False

        print(
            f"이미지 감지 시작: 구역={self.detection_region}, 원본 템플릿 {self.template_source_count}개, 변형 템플릿 {len(self.template_variants)}개"
        )

        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._check_image)
        self.check_timer.start(self.check_interval)
        self._check_image()

    def stop(self):
        """이미지 감지 중지"""
        print("이미지 감지 중지 시작...")
        self.is_running = False

        # 타이머 정리
        for timer in [self.check_timer, self.repeat_timer]:
            if timer:
                timer.stop()
        self.check_timer = None
        self.repeat_timer = None

        # 텔레그램 루프 정리
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
        """이미지 감지 수행"""
        if not self.is_running:
            return
        try:
            x1, y1, x2, y2 = self.detection_region
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            screenshot_np = np.array(screenshot)
            screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2GRAY)

            detected = False
            for variant in self.template_variants:
                template = variant["image"]
                th, tw = template.shape[:2]
                sh, sw = screenshot_gray.shape[:2]
                if th > sh or tw > sw:
                    continue
                res = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val >= self.confidence_threshold:
                    detected = True
                    print(
                        f"이미지 감지! 신뢰도: {max_val:.2f} (스케일 {variant['scale']:.2f}, 회전 {variant['angle']}°, 원본 {variant['source']})"
                    )
                    break

            if detected and not self.last_detected:
                self.detection_count += 1
                self.last_detected = True
                self.is_repeating = True
                self.repeat_count = 0
                self._send_repeat_message()
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

    def _generate_template_variants(self, template_gray, source_path):
        variants = []
        for scale in self.scale_values:
            try:
                resized = cv2.resize(
                    template_gray,
                    dsize=None,
                    fx=scale,
                    fy=scale,
                    interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR,
                )
            except cv2.error:
                continue
            if resized.shape[0] < 5 or resized.shape[1] < 5:
                continue
            for angle in self.angle_values:
                if angle == 0:
                    rotated = resized.copy()
                else:
                    rotated = self._rotate_image(resized, angle)
                if rotated.shape[0] < 5 or rotated.shape[1] < 5:
                    continue
                variants.append(
                    {"image": rotated, "scale": scale, "angle": angle, "source": source_path}
                )
        return variants

    def _rotate_image(self, image, angle):
        h, w = image.shape[:2]
        center = (w / 2.0, h / 2.0)
        m = cv2.getRotationMatrix2D(center, angle, 1.0)
        cos = abs(m[0, 0])
        sin = abs(m[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))
        m[0, 2] += (new_w / 2) - center[0]
        m[1, 2] += (new_h / 2) - center[1]
        return cv2.warpAffine(
            image, m, (new_w, new_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )

    def _send_repeat_message(self):
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
        """텔레그램으로 메시지 전송"""
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
    
    def send_notification(self, message: str):
        """외부에서 호출할 수 있는 텔레그램 알림 전송 함수"""
        if not self.telegram_token or not self.telegram_chat_id:
            print("텔레그램 설정이 없어 메시지를 보낼 수 없습니다.")
            return

        # 텔레그램 봇이 아직 초기화되지 않았거나 닫혀 있으면 다시 초기화
        if not self.bot or not self.loop or (self.loop and self.loop.is_closed()):
            self._init_telegram_bot()

        try:
            self._send_telegram_message(message)
        except Exception as e:
            print(f"텔레그램 알림 전송 실패: {e}")


    async def _async_send_message(self, message: str):
        try:
            await self.bot.send_message(chat_id=self.telegram_chat_id, text=message)
            print(f"텔레그램 메시지 전송 성공: {message}")
        except TelegramError as e:
            print(f"텔레그램 오류: {e}")
        except Exception as e:
            print(f"전송 오류: {e}")
