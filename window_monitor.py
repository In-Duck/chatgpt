import win32gui
import win32process
import win32con
import ctypes
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from typing import Optional, List, Tuple


class WindowMonitor(QObject):
    """Windows 창을 모니터링하고 활성화하는 클래스"""
    
    window_activated = pyqtSignal(str)  # 창이 활성화되었을 때
    window_lost_focus = pyqtSignal(str)  # 창이 포커스를 잃었을 때
    
    def __init__(self):
        super().__init__()
        self.target_hwnd: Optional[int] = None
        self.target_title: Optional[str] = None
        self.is_monitoring = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_window_status)
        self.check_interval = 1000  # 1000ms(1초)로 증가하여 CPU 사용량 감소
        self.last_foreground_hwnd = None  # 이전 포그라운드 창 캐싱
    
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
        return True
    
    def stop_monitoring(self):
        """창 모니터링을 중지합니다."""
        self.is_monitoring = False
        self.timer.stop()
        self.last_foreground_hwnd = None
    
    def _check_window_status(self):
        """대상 창의 상태를 확인하고 필요시 활성화합니다."""
        if not self.is_monitoring or self.target_hwnd is None:
            return
        
        try:
            # 창이 여전히 존재하는지 확인
            if not win32gui.IsWindow(self.target_hwnd):
                return
            
            # 현재 포커스된 창 확인
            foreground_hwnd = win32gui.GetForegroundWindow()
            
            # 캐시된 값과 비교하여 변경된 경우만 처리 (CPU 최적화)
            if foreground_hwnd == self.last_foreground_hwnd:
                return
            
            self.last_foreground_hwnd = foreground_hwnd
            
            # 대상 창이 포커스를 잃었다면 다시 활성화
            if foreground_hwnd != self.target_hwnd:
                self._activate_window()
        
        except Exception as e:
            # 액세스 거부 등의 오류는 무시하고 계속 진행
            pass
    
    def _activate_window(self):
        """대상 창을 최상단으로 가져오고 활성화합니다."""
        try:
            # 최소화된 경우 복원
            if win32gui.IsIconic(self.target_hwnd):
                win32gui.ShowWindow(self.target_hwnd, win32con.SW_RESTORE)
            
            # 창을 보이게 설정
            win32gui.ShowWindow(self.target_hwnd, win32con.SW_SHOW)
            
            # Alt 키를 시뮬레이션하여 포커스 제한 우회
            keybd_event = ctypes.windll.user32.keybd_event
            VK_MENU = 0x12  # Alt key
            KEYEVENTF_EXTENDEDKEY = 0x0001
            KEYEVENTF_KEYUP = 0x0002
            
            # Alt 키 누름
            keybd_event(VK_MENU, 0, KEYEVENTF_EXTENDEDKEY, 0)
            
            # 창을 최상단으로 설정
            win32gui.SetWindowPos(
                self.target_hwnd,
                win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
            )
            
            # 포커스 설정
            win32gui.SetForegroundWindow(self.target_hwnd)
            
            # TOPMOST 해제 (항상 위가 아닌 일반 최상단으로)
            win32gui.SetWindowPos(
                self.target_hwnd,
                win32con.HWND_NOTOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
            )
            
            # Alt 키 놓음
            keybd_event(VK_MENU, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
            
            # 창 활성화
            win32gui.SetActiveWindow(self.target_hwnd)
            
        except Exception as e:
            # 일부 메서드가 실패해도 계속 진행
            try:
                # 대체 방법: BringWindowToTop 사용
                win32gui.BringWindowToTop(self.target_hwnd)
                win32gui.SetForegroundWindow(self.target_hwnd)
            except:
                pass
    
    def is_window_valid(self) -> bool:
        """대상 창이 여전히 유효한지 확인합니다."""
        if self.target_hwnd is None:
            return False
        try:
            return win32gui.IsWindow(self.target_hwnd)
        except:
            return False