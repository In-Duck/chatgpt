import random
import time
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from pynput.keyboard import Key, Controller


class BuffWorker(QObject):
    """버프 키를 자동으로 입력하는 클래스"""
    
    key_pressed = pyqtSignal(str, int)  # 키, 횟수

    def __init__(self, buff_number: int):
        super().__init__()
        self.buff_number = buff_number
        self.keyboard = Controller()
        self.is_running = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._press_keys_cycle)
        self.timer.setSingleShot(True)  # 단발성 타이머로 설정하여 메모리 최적화

        # 설정값
        self.key_to_press = "space"
        self.min_interval = 5.0
        self.max_interval = 10.0
        self.press_count = 1
        
        # 첫 실행 여부 플래그
        self.is_first_run = True

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
        self.is_first_run = True
        # 즉시 첫 사이클 실행 (딜레이 없음)
        self._press_keys_cycle()

    def stop(self):
        """자동 버프 키 입력을 중지합니다."""
        self.is_running = False
        self.is_first_run = True
        self.timer.stop()

    def _press_keys_cycle(self):
        """한 사이클의 키 입력을 수행합니다."""
        if not self.is_running:
            return

        try:
            key_obj = self._get_key_object(self.key_to_press)

            # 지정된 횟수만큼 입력
            for i in range(self.press_count):
                if not self.is_running:
                    return

                self.keyboard.press(key_obj)
                self.keyboard.release(key_obj)
                self.key_pressed.emit(self.key_to_press, i + 1)

                # 연속 입력 시 짧은 간격 (50ms)
                if i < self.press_count - 1:
                    time.sleep(0.05)

        except Exception as e:
            print(f"버프{self.buff_number} 키 입력 중 오류: {e}")

        # 다음 사이클까지 대기
        if self.is_running:
            # 랜덤 간격 계산
            next_delay = int(random.uniform(self.min_interval, self.max_interval) * 1000)
            self.timer.start(next_delay)

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