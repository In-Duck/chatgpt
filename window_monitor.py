import ctypes
import win32gui
import win32con
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from typing import Optional, List, Tuple


class WindowMonitor(QObject):
    """Windows 창을 모니터링하고 포커스 상태 변화를 알리는 클래스"""

    window_activated = pyqtSignal(str)  # 창이 활성화되었을 때
    window_lost_focus = pyqtSignal(str)  # 창이 포커스를 잃었을 때

    def __init__(self):
        super().__init__()
        self.target_hwnd: Optional[int] = None
        self.target_title: Optional[str] = None
        self.is_monitoring = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_window_status)
        self.check_interval = 500  # 500ms마다 대상 창 상태 확인
        self.last_foreground_hwnd: Optional[int] = None

    @staticmethod
    def get_all_windows() -> List[Tuple[int, str]]:
        """현재 실행 중인 모든 창 목록을 반환합니다."""
        windows = []

        def enum_callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:  # 제목이 있는 창만
                    results.append((hwnd, title))

        win32gui.EnumWindows(enum_callback, windows)
        return windows

    def set_target_window(self, hwnd: int, title: str):
        """모니터링할 대상 창을 설정합니다."""
        self.target_hwnd = hwnd
        self.target_title = title

    def start_monitoring(self):
        """창 모니터링을 시작합니다."""
        if self.target_hwnd is None:
            return False

        self.is_monitoring = True
        self.timer.start(self.check_interval)

        # 감지 시작 시 즉시 대상 창에 포커스를 부여합니다.
        self._activate_window()

        self.last_foreground_hwnd = self._get_foreground_window()
        if self.last_foreground_hwnd == self.target_hwnd and self.target_title:
            self.window_activated.emit(self.target_title)
        return True

    def stop_monitoring(self):
        """창 모니터링을 중지합니다."""
        self.is_monitoring = False
        self.timer.stop()
        self.last_foreground_hwnd = None

    def _check_window_status(self):
        """대상 창의 활성 상태를 확인합니다."""
        if not self.is_monitoring or self.target_hwnd is None:
            return

        try:
            # 창이 여전히 존재하는지 확인
            if not win32gui.IsWindow(self.target_hwnd):
                if self.last_foreground_hwnd == self.target_hwnd and self.target_title:
                    self.window_lost_focus.emit(self.target_title)
                self.last_foreground_hwnd = None
                return

            foreground_hwnd = self._get_foreground_window()

            if foreground_hwnd == self.target_hwnd:
                if self.last_foreground_hwnd != self.target_hwnd and self.target_title:
                    self.window_activated.emit(self.target_title)
                self.last_foreground_hwnd = self.target_hwnd
                return

            previously_target = self.last_foreground_hwnd == self.target_hwnd
            self.last_foreground_hwnd = foreground_hwnd

            if not previously_target:
                return

            if self.target_title:
                self.window_lost_focus.emit(self.target_title)

            self._activate_window()

            activated_hwnd = self._get_foreground_window()
            if activated_hwnd == self.target_hwnd:
                self.last_foreground_hwnd = self.target_hwnd
                if self.target_title:
                    self.window_activated.emit(self.target_title)

        except Exception:
            # 액세스 거부 등의 오류는 무시하고 계속 진행
            pass

    def _get_foreground_window(self) -> Optional[int]:
        """현재 포그라운드 창 핸들을 안전하게 반환합니다."""
        try:
            return win32gui.GetForegroundWindow()
        except Exception:
            return None

    def _activate_window(self):
        """대상 창을 최상단으로 가져오고 포커스를 설정합니다."""
        if self.target_hwnd is None:
            return

        try:
            if win32gui.IsIconic(self.target_hwnd):
                win32gui.ShowWindow(self.target_hwnd, win32con.SW_RESTORE)

            win32gui.ShowWindow(self.target_hwnd, win32con.SW_SHOW)

            keybd_event = ctypes.windll.user32.keybd_event
            VK_MENU = 0x12
            KEYEVENTF_EXTENDEDKEY = 0x0001
            KEYEVENTF_KEYUP = 0x0002

            keybd_event(VK_MENU, 0, KEYEVENTF_EXTENDEDKEY, 0)

            win32gui.SetWindowPos(
                self.target_hwnd,
                win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
            )

            win32gui.SetForegroundWindow(self.target_hwnd)

            win32gui.SetWindowPos(
                self.target_hwnd,
                win32con.HWND_NOTOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
            )

            keybd_event(VK_MENU, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)

            win32gui.SetActiveWindow(self.target_hwnd)

        except Exception:
            try:
                win32gui.BringWindowToTop(self.target_hwnd)
                win32gui.SetForegroundWindow(self.target_hwnd)
            except Exception:
                pass

    def is_window_valid(self) -> bool:
        """대상 창이 여전히 유효한지 확인합니다."""
        if self.target_hwnd is None:
            return False
        try:
            return win32gui.IsWindow(self.target_hwnd)
        except:
            return False
