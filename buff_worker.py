import random
import time
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from pynput.keyboard import Key, Controller


class BuffWorker(QObject):
    """버프 키를 자동으로 입력하는 클래스"""

    key_pressed = pyqtSignal(str, int)  # 키, 횟수
    last_run_updated = pyqtSignal(float)

    def __init__(self, buff_number: int):
        super().__init__()
        self.buff_number = buff_number
        self.keyboard = Controller()
        self.is_running = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._on_timer_timeout)
        self.timer.setSingleShot(True)  # 단발성 타이머로 설정하여 메모리 최적화
        self.last_run_at = None

    # 설정값
        self.key_to_press = "space"
        self.min_interval = 5.0
        self.max_interval = 10.0
        self.press_count = 1

    def set_config(self, key: str, min_interval: float, max_interval: float, press_count: int):
        """버프 키 입력 설정을 업데이트합니다."""
        self.key_to_press = key
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.press_count = press_count

    def start(self):
        """자동 버프 키 입력을 시작합니다."""
        if self.is_running:
            return

        self.is_running = True
        self.timer.stop()
        self._execute_cycle()

    def stop(self):
        """자동 버프 키 입력을 중지합니다."""
        self.is_running = False
        self.timer.stop()

    def _on_timer_timeout(self):
        """타이머 만료 시 다음 사이클 실행"""
        if not self.is_running:
            return

        self._execute_cycle()

    def _execute_cycle(self):
        """버프 키를 한 차례 실행하고 결과와 관계없이 다음 주기를 예약합니다."""
        if not self.is_running:
            return

        success = self._press_keys_once()

        if not self.is_running:
            return

        if success:
            self._mark_last_run()

        self._schedule_next_cycle()

    def _mark_last_run(self):
        """마지막 실행 시간을 기록하고 시그널을 발송합니다."""
        self.last_run_at = time.time()
        self.last_run_updated.emit(self.last_run_at)

    def _schedule_next_cycle(self):
        """다음 실행까지의 지연을 계산해 타이머를 시작합니다."""
        if not self.is_running:
            return

        next_delay = max(1, self._get_next_delay_ms())
        self._restart_timer(next_delay)

    def _restart_timer(self, delay_ms: int):
        """기존 타이머를 중단하고 지정한 지연으로 다시 시작합니다."""
        if delay_ms <= 0:
            delay_ms = 1
        self.timer.stop()
        self.timer.start(delay_ms)

    def _press_keys_once(self) -> bool:
        """설정된 횟수만큼 키 입력을 수행하고 성공 여부를 반환합니다."""
        try:
            if self.press_count <= 0:
                return True

            key_obj = self._get_key_object(self.key_to_press)

            for i in range(self.press_count):
                if not self.is_running:
                    return False

                self.keyboard.press(key_obj)
                self.keyboard.release(key_obj)
                self.key_pressed.emit(self.key_to_press, i + 1)

                if i < self.press_count - 1:
                    time.sleep(0.05)

            return True

        except Exception as e:
            print(f"버프{self.buff_number} 키 입력 중 오류: {e}")
            return False

    def _get_next_delay_ms(self) -> int:
        """다음 사이클까지 대기할 시간을 밀리초로 반환합니다."""
        return int(random.uniform(self.min_interval, self.max_interval) * 1000)

    def _get_key_object(self, key_name: str):
        """키 이름을 pynput Key 객체로 변환합니다."""
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

        return key_name[0] if len(key_name) > 0 else 'a'
