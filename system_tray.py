from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSignal, QObject


class SystemTrayManager(QObject):
    """시스템 트레이 아이콘을 관리하는 클래스"""
    
    # 시그널 정의
    show_window = pyqtSignal()
    hide_window = pyqtSignal()
    start_all = pyqtSignal()
    stop_all = pyqtSignal()
    quit_app = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.tray_icon = None
        self.menu = None
    
    def setup_tray(self):
        """트레이 아이콘과 메뉴를 설정합니다."""
        # 트레이 아이콘 생성 (기본 아이콘 사용)
        self.tray_icon = QSystemTrayIcon(self.parent_window)
        
        # 아이콘 설정 (애플리케이션 아이콘 사용)
        if self.parent_window:
            self.tray_icon.setIcon(self.parent_window.windowIcon())
        
        # 컨텍스트 메뉴 생성
        self.menu = QMenu()
        
        # 메뉴 항목 추가
        show_action = QAction("보이기", self.menu)
        show_action.triggered.connect(self.show_window.emit)
        self.menu.addAction(show_action)
        
        hide_action = QAction("숨기기", self.menu)
        hide_action.triggered.connect(self.hide_window.emit)
        self.menu.addAction(hide_action)
        
        self.menu.addSeparator()
        
        start_all_action = QAction("모두 시작", self.menu)
        start_all_action.triggered.connect(self.start_all.emit)
        self.menu.addAction(start_all_action)
        
        stop_all_action = QAction("모두 중지", self.menu)
        stop_all_action.triggered.connect(self.stop_all.emit)
        self.menu.addAction(stop_all_action)
        
        self.menu.addSeparator()
        
        quit_action = QAction("종료", self.menu)
        quit_action.triggered.connect(self.quit_app.emit)
        self.menu.addAction(quit_action)
        
        # 트레이 아이콘에 메뉴 설정
        self.tray_icon.setContextMenu(self.menu)
        
        # 더블클릭 시 창 보이기
        self.tray_icon.activated.connect(self._on_tray_activated)
        
        # 툴팁 설정
        self.update_tooltip("준비")
    
    def show_tray(self):
        """트레이 아이콘을 표시합니다."""
        if self.tray_icon:
            self.tray_icon.show()
    
    def hide_tray(self):
        """트레이 아이콘을 숨깁니다."""
        if self.tray_icon:
            self.tray_icon.hide()
    
    def update_tooltip(self, status: str):
        """트레이 아이콘의 툴팁을 업데이트합니다."""
        if self.tray_icon:
            self.tray_icon.setToolTip(f"창 모니터링 프로그램 - {status}")
    
    def show_message(self, title: str, message: str, icon=QSystemTrayIcon.Information):
        """트레이 알림 메시지를 표시합니다."""
        if self.tray_icon:
            self.tray_icon.showMessage(title, message, icon, 2000)
    
    def _on_tray_activated(self, reason):
        """트레이 아이콘 클릭 이벤트 처리"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window.emit()