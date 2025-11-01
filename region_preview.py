from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPainter, QPen, QColor
from typing import Tuple


class RegionPreviewWindow(QWidget):
    """구역 미리보기를 위한 투명 오버레이 창"""
    
    def __init__(self, region: Tuple[int, int, int, int]):
        super().__init__()
        self.region = region
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        # 창 설정
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | 
            Qt.FramelessWindowHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # 전체 화면 크기로 설정
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
    
    def paintEvent(self, event):
        """구역을 빨간 테두리로 그립니다."""
        painter = QPainter(self)
        
        # 빨간색 테두리 설정 (두께 3px)
        pen = QPen(QColor(255, 0, 0), 3, Qt.SolidLine)
        painter.setPen(pen)
        
        # 구역 그리기
        x1, y1, x2, y2 = self.region
        rect = QRect(x1, y1, x2 - x1, y2 - y1)
        painter.drawRect(rect)
    
    def show_preview(self):
        """미리보기 표시"""
        self.show()
    
    def hide_preview(self):
        """미리보기 숨김"""
        self.hide()