import ctypes
import win32gui
import win32con
import win32process
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from typing import Optional, List, Tuple


class WindowMonitor(QObject):
    """대상 창이 비활성화될 경우 자동으로 전면 복원 + 포커스까지 재부여하는 모니터 클래스"""

    window_activated = pyqtSignal(str)
    window_lost_focus = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.target_hwnd: Optional[int] = None
        self.target_title: Optional[str] = None
        self.is_monitoring = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_window_status)
        self.check_interval = 500  # 0.5초 간격 감시
        self.last_foreground_hwnd: Optional[int] = None

    @staticmethod
    def get_all_windows() -> List[Tuple[int, str]]:
        windows = []

        def enum_callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    results.append((hwnd, title))

        win32gui.EnumWindows(enum_callback, windows)
        return windows

    def set_target_window(self, hwnd: int, title: str):
        """모니터링할 대상 창 지정"""
        self.target_hwnd = hwnd
        self.target_title = title

    def start_monitoring(self):
        """모니터링 시작"""
        if self.target_hwnd is None:
            return False

        self.is_monitoring = True
        self.timer.start(self.check_interval)

        self._activate_window()
        self.last_foreground_hwnd = self._get_foreground_window()
        if self.last_foreground_hwnd == self.target_hwnd and self.target_title:
            self.window_activated.emit(self.target_title)
        return True

    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_monitoring = False
        self.timer.stop()
        self.last_foreground_hwnd = None

    def _check_window_status(self):
        """1초마다 대상 창이 포커스를 잃었는지 감시하고, 잃으면 복원"""
        if not self.is_monitoring or self.target_hwnd is None:
            return

        try:
            # 창이 유효하지 않으면 감시 종료
            if not win32gui.IsWindow(self.target_hwnd):
                if self.target_title:
                    self.window_lost_focus.emit(self.target_title)
                self.last_foreground_hwnd = None
                return

            foreground_hwnd = self._get_foreground_window()

            # 포그라운드가 아닐 때 포커스 복원
            if foreground_hwnd != self.target_hwnd:
                if self.target_title:
                    self.window_lost_focus.emit(self.target_title)
                self._activate_window()
            else:
                if self.last_foreground_hwnd != self.target_hwnd and self.target_title:
                    self.window_activated.emit(self.target_title)

            self.last_foreground_hwnd = foreground_hwnd

        except Exception:
            pass

    def _get_foreground_window(self) -> Optional[int]:
        try:
            return win32gui.GetForegroundWindow()
        except Exception:
            return None

    def _activate_window(self):
        """Alt 키 없이, 창을 잠깐 전면으로 복원하지만 항상 위에는 두지 않음"""
        if self.target_hwnd is None:
            return

        try:
            user32 = ctypes.windll.user32

            # 최소화된 경우 복원
            if win32gui.IsIconic(self.target_hwnd):
                win32gui.ShowWindow(self.target_hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(self.target_hwnd, win32con.SW_SHOWNORMAL)

            # ✅ 일시적으로만 topmost 설정 (포커스 복원용)
            win32gui.SetWindowPos(
                self.target_hwnd,
                win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW,
            )

            # 입력 스레드 연결
            foreground_hwnd = user32.GetForegroundWindow()
            target_thread_id, _ = win32process.GetWindowThreadProcessId(self.target_hwnd)
            foreground_thread_id, _ = win32process.GetWindowThreadProcessId(foreground_hwnd)
            attached = False

            if foreground_thread_id != target_thread_id:
                attached = bool(user32.AttachThreadInput(foreground_thread_id, target_thread_id, True))

            try:
                user32.AllowSetForegroundWindow(win32con.ASFW_ANY)
                user32.BringWindowToTop(self.target_hwnd)
                user32.SetForegroundWindow(self.target_hwnd)
                user32.SetActiveWindow(self.target_hwnd)
                user32.SetFocus(self.target_hwnd)
                user32.EnableWindow(self.target_hwnd, True)
            finally:
                if attached:
                    user32.AttachThreadInput(foreground_thread_id, target_thread_id, False)

            # ✅ topmost 해제 (시각적 순서 복구)
            win32gui.SetWindowPos(
                self.target_hwnd,
                win32con.HWND_NOTOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW,
            )

        except Exception:
            try:
                win32gui.BringWindowToTop(self.target_hwnd)
                win32gui.SetForegroundWindow(self.target_hwnd)
            except Exception:
                pass



    def is_window_valid(self) -> bool:
        if self.target_hwnd is None:
            return False
        try:
            return win32gui.IsWindow(self.target_hwnd)
        except:
            return False
