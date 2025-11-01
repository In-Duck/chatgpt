import keyboard
from PyQt5.QtCore import QObject, pyqtSignal


class HotkeyManager(QObject):
    """전역 핫키를 관리하는 클래스"""
    
    # 시그널 정의
    pickup_toggle = pyqtSignal()  # 줍기 토글
    buff_toggle = pyqtSignal()    # 버프 토글
    monitor_toggle = pyqtSignal() # 감지 토글
    detector_toggle = pyqtSignal() # 유저탐색 토글
    
    def __init__(self):
        super().__init__()
        self.is_enabled = False
        self.registered_hotkeys = []
        
        # 기본 핫키 설정
        self.hotkey_pickup = "f9"
        self.hotkey_buff = "f10"
        self.hotkey_monitor = "f11"
        self.hotkey_detector = "f12"
    
    def set_hotkeys(self, pickup="", buff="", monitor="", detector=""):
        """핫키를 설정합니다."""
        # 기존 핫키 비활성화
        if self.is_enabled:
            self.disable_hotkeys()
        
        # 새 핫키 설정 (빈 문자열이 아닌 경우만)
        if pickup:
            self.hotkey_pickup = pickup
        else:
            self.hotkey_pickup = ""
            
        if buff:
            self.hotkey_buff = buff
        else:
            self.hotkey_buff = ""
            
        if monitor:
            self.hotkey_monitor = monitor
        else:
            self.hotkey_monitor = ""
            
        if detector:
            self.hotkey_detector = detector
        else:
            self.hotkey_detector = ""
        
        # 핫키 다시 활성화
        self.enable_hotkeys()
    
    def enable_hotkeys(self):
        """핫키를 활성화합니다."""
        if self.is_enabled:
            return
        
        try:
            # 줍기 핫키
            if self.hotkey_pickup:
                keyboard.add_hotkey(self.hotkey_pickup, self._on_pickup_toggle, suppress=True)
                self.registered_hotkeys.append(self.hotkey_pickup)
            
            # 버프 핫키
            if self.hotkey_buff:
                keyboard.add_hotkey(self.hotkey_buff, self._on_buff_toggle, suppress=True)
                self.registered_hotkeys.append(self.hotkey_buff)
            
            # 감지 핫키
            if self.hotkey_monitor:
                keyboard.add_hotkey(self.hotkey_monitor, self._on_monitor_toggle, suppress=True)
                self.registered_hotkeys.append(self.hotkey_monitor)
            
            # 유저탐색 핫키
            if self.hotkey_detector:
                keyboard.add_hotkey(self.hotkey_detector, self._on_detector_toggle, suppress=True)
                self.registered_hotkeys.append(self.hotkey_detector)
            
            self.is_enabled = True
            
        except Exception as e:
            print(f"핫키 등록 실패: {e}")
    
    def disable_hotkeys(self):
        """핫키를 비활성화합니다."""
        if not self.is_enabled:
            return
        
        try:
            for hotkey in self.registered_hotkeys:
                keyboard.remove_hotkey(hotkey)
            self.registered_hotkeys.clear()
            self.is_enabled = False
            
        except Exception as e:
            print(f"핫키 해제 실패: {e}")
    
    def get_hotkey_display(self):
        """현재 핫키 설정을 표시용 문자열로 반환합니다."""
        hotkeys = []
        
        if self.hotkey_pickup:
            hotkeys.append(f"{self.hotkey_pickup.upper()}=줍기")
        else:
            hotkeys.append("줍기=없음")
            
        if self.hotkey_buff:
            hotkeys.append(f"{self.hotkey_buff.upper()}=버프")
        else:
            hotkeys.append("버프=없음")
            
        if self.hotkey_monitor:
            hotkeys.append(f"{self.hotkey_monitor.upper()}=감지")
        else:
            hotkeys.append("감지=없음")
            
        if self.hotkey_detector:
            hotkeys.append(f"{self.hotkey_detector.upper()}=유저탐색")
        else:
            hotkeys.append("유저탐색=없음")
        
        return " | ".join(hotkeys)
    
    def _on_pickup_toggle(self):
        """줍기 핫키 콜백"""
        self.pickup_toggle.emit()
    
    def _on_buff_toggle(self):
        """버프 핫키 콜백"""
        self.buff_toggle.emit()
    
    def _on_monitor_toggle(self):
        """감지 핫키 콜백"""
        self.monitor_toggle.emit()
    
    def _on_detector_toggle(self):
        """유저탐색 핫키 콜백"""
        self.detector_toggle.emit()