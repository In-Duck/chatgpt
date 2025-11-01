from PyQt5.QtWidgets import QLineEdit, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeyEvent


class HotkeyInputWidget(QLineEdit):
    """핫키 입력을 위한 커스텀 위젯"""
    
    hotkey_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("클릭 후 키를 눌러주세요")
        self.current_hotkey = ""
        self.modifiers = []
        self.key = ""
    
    def keyPressEvent(self, event: QKeyEvent):
        """키 입력 이벤트 처리"""
        key = event.key()
        
        # 수정자 키 (Ctrl, Alt, Shift) 처리
        modifiers = []
        if event.modifiers() & Qt.ControlModifier:
            modifiers.append("ctrl")
        if event.modifiers() & Qt.AltModifier:
            modifiers.append("alt")
        if event.modifiers() & Qt.ShiftModifier:
            modifiers.append("shift")
        
        # 일반 키 매핑
        key_map = {
            Qt.Key_F1: "f1", Qt.Key_F2: "f2", Qt.Key_F3: "f3", Qt.Key_F4: "f4",
            Qt.Key_F5: "f5", Qt.Key_F6: "f6", Qt.Key_F7: "f7", Qt.Key_F8: "f8",
            Qt.Key_F9: "f9", Qt.Key_F10: "f10", Qt.Key_F11: "f11", Qt.Key_F12: "f12",
            Qt.Key_Space: "space", Qt.Key_Return: "enter", Qt.Key_Enter: "enter",
            Qt.Key_Backspace: "backspace", Qt.Key_Tab: "tab", Qt.Key_Escape: "esc",
            Qt.Key_Delete: "delete", Qt.Key_Insert: "insert",
            Qt.Key_Home: "home", Qt.Key_End: "end",
            Qt.Key_PageUp: "page up", Qt.Key_PageDown: "page down",
            Qt.Key_Up: "up", Qt.Key_Down: "down", Qt.Key_Left: "left", Qt.Key_Right: "right",
            Qt.Key_Plus: "+", Qt.Key_Minus: "-", Qt.Key_Asterisk: "*", Qt.Key_Slash: "/",
        }
        
        # 숫자 키
        if Qt.Key_0 <= key <= Qt.Key_9:
            key_name = chr(key).lower()
        # 알파벳 키
        elif Qt.Key_A <= key <= Qt.Key_Z:
            key_name = chr(key).lower()
        # 특수 키
        elif key in key_map:
            key_name = key_map[key]
        # 수정자 키만 눌렀을 때는 무시
        elif key in (Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift):
            return
        else:
            # 지원하지 않는 키
            QMessageBox.warning(self, "경고", "지원하지 않는 키입니다.")
            return
        
        # 핫키 문자열 생성
        if modifiers:
            hotkey_str = "+".join(modifiers) + "+" + key_name
        else:
            hotkey_str = key_name
        
        self.current_hotkey = hotkey_str
        self.setText(hotkey_str.upper())
        self.hotkey_changed.emit(hotkey_str)
    
    def set_hotkey(self, hotkey: str):
        """핫키 설정"""
        self.current_hotkey = hotkey
        if hotkey:
            self.setText(hotkey.upper())
        else:
            self.setText("")
    
    def get_hotkey(self) -> str:
        """현재 핫키 반환"""
        return self.current_hotkey
    
    def clear_hotkey(self):
        """핫키 초기화"""
        self.current_hotkey = ""
        self.setText("")
        self.hotkey_changed.emit("")