import importlib.util
import random
import threading
import time
from dataclasses import dataclass
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal

_PYNPUT_KEYBOARD_SPEC = importlib.util.find_spec("pynput.keyboard")

if _PYNPUT_KEYBOARD_SPEC is not None:
    from pynput.keyboard import Controller, Key  # type: ignore
else:  # pragma: no cover - 플랫폼에 따라 발생
    Controller = None  # type: ignore[assignment]
    Key = None  # type: ignore[assignment]


@dataclass(frozen=True)
class BuffConfig:
    """버프 키 입력에 필요한 설정값을 표현합니다."""

    key: str = "space"
    min_interval: float = 5.0
    max_interval: float = 10.0
    press_count: int = 1

    @classmethod
    def create(
        cls,
        key: str,
        min_interval: float,
        max_interval: float,
        press_count: int,
    ) -> "BuffConfig":
        """외부 입력을 안전한 설정으로 정규화합니다."""

        normalized_key = key or "space"

        try:
            min_value = float(min_interval)
        except (TypeError, ValueError):
            min_value = 0.1

        try:
            max_value = float(max_interval)
        except (TypeError, ValueError):
            max_value = min_value

        min_value = max(0.1, min_value)
        max_value = max(min_value, max_value)

        try:
            count = int(press_count)
        except (TypeError, ValueError):
            count = 1

        count = max(1, min(count, 100))

        return cls(normalized_key, min_value, max_value, count)


class BuffWorker(QObject):
    """버프 키를 자동으로 입력하는 클래스"""

    key_pressed = pyqtSignal(str, int)  # 키, 횟수
    last_run_updated = pyqtSignal(float)
    error_occurred = pyqtSignal(str)

    def __init__(self, buff_number: int):
        super().__init__()
        self.buff_number = buff_number

        self.is_running = False
        self.last_run_at: Optional[float] = None

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._state_lock = threading.Lock()
        self._config_lock = threading.Lock()
        self._keyboard_lock = threading.Lock()
        self._error_lock = threading.Lock()

        self._config = BuffConfig()
        self._last_error_message: Optional[str] = None

        # 외부에서 접근하는 속성은 기존과 동일하게 유지합니다.
        self.key_to_press = self._config.key
        self.min_interval = self._config.min_interval
        self.max_interval = self._config.max_interval
        self.press_count = self._config.press_count

        self.keyboard: Optional[Controller] = None
        self._keyboard_unsupported = Controller is None

    def set_config(self, key: str, min_interval: float, max_interval: float, press_count: int):
        """버프 키 입력 설정을 업데이트합니다."""
        config = BuffConfig.create(key, min_interval, max_interval, press_count)

        with self._config_lock:
            self._config = config

        self.key_to_press = config.key
        self.min_interval = config.min_interval
        self.max_interval = config.max_interval
        self.press_count = config.press_count

    def start(self):
        """자동 버프 키 입력을 시작합니다."""
        with self._state_lock:
            if self.is_running:
                return

            thread = self._thread
            if thread and thread.is_alive():
                # 잔여 스레드가 남아있다면 완전히 중단되도록 대기합니다.
                self._stop_event.set()

        if thread and thread.is_alive():
            thread.join(timeout=2.0)

        # 새로운 실행을 위해 오류 메시지를 초기화합니다.
        self._last_error_message = None
        controller = self._ensure_keyboard_controller()
        if controller is None:
            with self._state_lock:
                self.is_running = False
                if self._thread and not self._thread.is_alive():
                    self._thread = None
            return

        with self._state_lock:
            if self.is_running:
                return

            self._stop_event.clear()
            self.is_running = True
            new_thread = threading.Thread(
                target=self._run_loop,
                name=f"BuffWorker-{self.buff_number}",
                daemon=True,
            )
            self._thread = new_thread
            new_thread.start()

    def stop(self):
        """자동 버프 키 입력을 중지합니다."""
        with self._state_lock:
            if not self.is_running:
                return

            self.is_running = False
            thread = self._thread
            self._stop_event.set()

        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)

        still_alive = bool(thread and thread.is_alive())

        with self._state_lock:
            if not still_alive and self._thread is thread:
                self._thread = None

        if not still_alive:
            self._stop_event.clear()
            self._last_error_message = None

    def _execute_cycle(self):
        """버프 키를 한 차례 실행하고 결과와 관계없이 다음 주기를 예약합니다."""
        if not self.is_running:
            return

        config = self._get_config_snapshot()
        success = self._press_keys_once(config)

        if not self.is_running:
            return

        if success:
            self._mark_last_run()

        # 다음 실행은 백그라운드 스레드 루프에서 처리됩니다.

    def _run_loop(self):
        """백그라운드 스레드에서 버프 사이클을 관리합니다."""
        try:
            # 즉시 첫 실행 수행
            self._execute_cycle()

            while self.is_running and not self._stop_event.is_set():
                config = self._get_config_snapshot()
                delay_seconds = self._get_next_delay_seconds(config)

                if delay_seconds <= 0:
                    delay_seconds = 0.1

                if self._stop_event.wait(delay_seconds):
                    break

                self._execute_cycle()
        except Exception as exc:
            self._emit_error_once(
                f"버프{self.buff_number} 실행 중 예기치 못한 오류가 발생했습니다.\n원인: {exc}"
            )
            self._request_stop()
        finally:
            # 스레드 종료 시 상태 정리
            with self._state_lock:
                self.is_running = False
                self._thread = None
            self._stop_event.clear()

    def _mark_last_run(self):
        """마지막 실행 시간을 기록하고 시그널을 발송합니다."""
        self.last_run_at = time.time()
        self.last_run_updated.emit(self.last_run_at)

    def _press_keys_once(self, config: BuffConfig) -> bool:
        """설정된 횟수만큼 키 입력을 수행하고 성공 여부를 반환합니다."""
        try:
            if config.press_count <= 0:
                return True

            controller = self._ensure_keyboard_controller()
            if controller is None:
                self._handle_fatal_error(
                    "키보드 제어 장치를 초기화할 수 없어 버프를 중단합니다."
                )
                return False

            key_obj = self._get_key_object(config.key)

            for i in range(config.press_count):
                if not self.is_running:
                    return False

                controller.press(key_obj)
                controller.release(key_obj)
                self.key_pressed.emit(config.key, i + 1)

                if i < config.press_count - 1 and self._stop_event.wait(0.05):
                    return False

            return True

        except Exception as e:
            self._emit_error_once(
                f"버프{self.buff_number} 키 입력 중 오류가 발생했습니다.\n원인: {e}"
            )
            self._handle_fatal_error("버프 실행을 안전하게 중단했습니다.")
            return False

    def _get_next_delay_seconds(self, config: BuffConfig) -> float:
        """다음 사이클까지 대기할 시간을 초 단위로 반환합니다."""
        return random.uniform(config.min_interval, config.max_interval)

    def _get_key_object(self, key_name: str):
        """키 이름을 pynput Key 객체로 변환합니다."""
        special_keys = {}

        if Key is not None:
            special_keys = {
                'space': Key.space,
                'enter': Key.enter,
                'tab': Key.tab,
                'esc': Key.esc,
                'backspace': Key.backspace,
                'delete': Key.delete,
                'up': Key.up,
                'down': Key.down,
                'left': Key.left,
                'right': Key.right,
                'shift': Key.shift,
                'ctrl': Key.ctrl,
                'alt': Key.alt,
            }

        key_lower = key_name.lower()
        if key_lower in special_keys:
            return special_keys[key_lower]

        if key_lower == 'space':
            return ' '
        if key_lower in {'enter', 'return'}:
            return '\n'

        return key_name[0] if len(key_name) > 0 else 'a'

    def _get_config_snapshot(self) -> BuffConfig:
        """동시에 수정 중인 설정을 안전하게 복사합니다."""
        with self._config_lock:
            config = self._config

        return BuffConfig(config.key, config.min_interval, config.max_interval, config.press_count)

    def _ensure_keyboard_controller(self) -> Optional[Controller]:
        """키보드 제어 객체를 지연 초기화합니다."""
        controller = self.keyboard
        if controller is not None:
            return controller

        if self._keyboard_unsupported:
            self._emit_error_once(
                (
                    "이 PC에서는 키보드 제어 모듈(pynput)을 사용할 수 없어 버프 기능을 실행할 수 없습니다.\n"
                    "관리자 권한 실행이나 보조 기능 권한을 확인하거나 지원되는 환경에서 이용해 주세요."
                )
            )
            return None

        with self._keyboard_lock:
            controller = self.keyboard
            if controller is not None:
                return controller

            try:
                controller = Controller()
            except Exception as exc:
                self._keyboard_unsupported = True
                self._emit_error_once(
                    (
                        f"버프{self.buff_number}의 키 입력 장치를 초기화하지 못했습니다.\n"
                        "관리자 권한 실행이나 보조 기능 사용 권한을 확인해주세요.\n"
                        f"원인: {exc}"
                    )
                )
                return None

            self.keyboard = controller
            return controller

    def _handle_fatal_error(self, message: str):
        """치명적 오류 발생 시 워커를 안전하게 중단합니다."""
        if message:
            self._emit_error_once(message)
        self._request_stop()

    def _request_stop(self):
        """외부 stop 호출과 동일하게 중단을 요청합니다."""
        self._stop_event.set()
        with self._state_lock:
            self.is_running = False

    def _emit_error_once(self, message: str):
        """동일한 오류 메시지를 한 번만 전파합니다."""
        if not message:
            return

        with self._error_lock:
            if message == self._last_error_message:
                return
            self._last_error_message = message

        self.error_occurred.emit(message)
