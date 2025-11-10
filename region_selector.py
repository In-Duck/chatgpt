from PyQt5.QtWidgets import QWidget, QApplication, QRubberBand
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont
from typing import Optional, Tuple


class RegionSelectorWindow(QWidget):
    """드래그로 구역을 선택할 수 있는 전체 화면 오버레이"""

    region_selected = pyqtSignal(tuple)  # (x1, y1, x2, y2) 시그널

    def __init__(self):
        super().__init__()
        self.start_pos: Optional[QPoint] = None
        self.current_pos: Optional[QPoint] = None
        self.selection_rect: Optional[QRect] = None
        self.is_selecting = False
        self.rubber_band: Optional[QRubberBand] = None
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        # 창 설정 - 전체 화면 오버레이
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.setWindowModality(Qt.ApplicationModal)

        # 전체 화면 크기로 설정
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self)

    def reset_selection_state(self):
        """선택 상태 초기화"""
        self.start_pos = None
        self.current_pos = None
        self.selection_rect = None
        self.is_selecting = False
        if self.rubber_band:
            self.rubber_band.hide()
        self.update()

    def mousePressEvent(self, event):
        """마우스 클릭 시작"""
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.current_pos = event.pos()
            self.is_selecting = True
            if self.rubber_band:
                self.rubber_band.setGeometry(QRect(self.start_pos, self.start_pos))
                self.rubber_band.show()
            self.update()

    def mouseMoveEvent(self, event):
        """마우스 드래그 중"""
        if self.is_selecting and self.start_pos:
            self.current_pos = event.pos()
            x1 = min(self.start_pos.x(), self.current_pos.x())
            y1 = min(self.start_pos.y(), self.current_pos.y())
            x2 = max(self.start_pos.x(), self.current_pos.x())
            y2 = max(self.start_pos.y(), self.current_pos.y())
            self.selection_rect = QRect(x1, y1, x2 - x1, y2 - y1)
            if self.rubber_band:
                self.rubber_band.setGeometry(QRect(QPoint(x1, y1), QPoint(x2, y2)))
            self.update()

    def mouseReleaseEvent(self, event):
        """마우스 클릭 종료"""
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            if self.rubber_band:
                self.rubber_band.hide()

            if self.start_pos and self.current_pos:
                x1 = min(self.start_pos.x(), self.current_pos.x())
                y1 = min(self.start_pos.y(), self.current_pos.y())
                x2 = max(self.start_pos.x(), self.current_pos.x())
                y2 = max(self.start_pos.y(), self.current_pos.y())
                self.selection_rect = QRect(x1, y1, x2 - x1, y2 - y1)

                # 최소 크기 확인 (10x10 픽셀 이상)
                if (x2 - x1) >= 10 and (y2 - y1) >= 10:
                    self.region_selected.emit((x1, y1, x2, y2))
                    self.close()
                else:
                    self.reset_selection_state()

    def keyPressEvent(self, event):
        """ESC 키로 취소"""
        if event.key() == Qt.Key_Escape:
            event.accept()  # 이벤트를 여기서 처리하고 부모로 전달하지 않음
            self.reset_selection_state()
            self.close()
        else:
            event.ignore()

    def paintEvent(self, event):
        """화면 그리기"""
        painter = QPainter(self)

        # 반투명 어두운 배경
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))

        # 선택 영역이 있으면 그리기
        if self.selection_rect and not self.selection_rect.isNull():
            selection_rect = QRect(self.selection_rect)
            x1 = selection_rect.x()
            y1 = selection_rect.y()
            x2 = x1 + selection_rect.width()
            y2 = y1 + selection_rect.height()
            # 선택 영역 배경 (투명하게)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(selection_rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            # 선택 영역 테두리 (밝은 빨간색, 두껍게)
            pen = QPen(QColor(255, 50, 50), 3, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(selection_rect)

            # 선택 영역 내부 (반투명 빨간색)
            brush = QBrush(QColor(255, 50, 50, 30))
            painter.setBrush(brush)
            painter.drawRect(selection_rect)

            # 좌표 정보 표시
            width = x2 - x1
            height = y2 - y1
            info_text = f"영역: ({x1}, {y1}) → ({x2}, {y2}) | 크기: {width} x {height}"

            # 텍스트 배경
            font = QFont("맑은 고딕", 11, QFont.Bold)
            painter.setFont(font)
            metrics = painter.fontMetrics()
            text_rect = metrics.boundingRect(info_text)
            text_rect.adjust(-12, -6, 12, 6)

            # 텍스트 위치 (선택 영역 위쪽 또는 아래쪽)
            text_x = selection_rect.left()
            text_y = selection_rect.top() - text_rect.height() - 15
            if text_y < 10:  # 화면 위쪽이면 아래로
                text_y = selection_rect.bottom() + 15

            text_rect.moveTo(text_x, text_y)

            # 텍스트 배경 그리기
            painter.setBrush(QBrush(QColor(0, 0, 0, 200)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(text_rect, 5, 5)

            # 텍스트 그리기
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(text_rect, Qt.AlignCenter, info_text)

        # 안내 메시지 (선택 전)
        if not self.is_selecting and not self.selection_rect:
            font = QFont("맑은 고딕", 16, QFont.Bold)
            painter.setFont(font)

            screen_rect = self.rect()
            help_text = "마우스로 드래그하여 영역을 선택하세요\nESC 키를 눌러 취소"

            # 안내 메시지 배경
            metrics = painter.fontMetrics()
            text_rect = metrics.boundingRect(screen_rect, Qt.AlignCenter, help_text)
            text_rect.adjust(-20, -15, 20, 15)

            painter.setBrush(QBrush(QColor(0, 0, 0, 200)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(text_rect, 10, 10)

            # 안내 메시지 텍스트
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(screen_rect, Qt.AlignCenter, help_text)

    def show_selector(self):
        """선택기 표시"""
        self.reset_selection_state()
        self.showFullScreen()
        self.activateWindow()
        self.raise_()
        self.setFocus(Qt.ActiveWindowFocusReason)
        QApplication.processEvents()

    def closeEvent(self, event):
        """창이 닫힐 때 입력 장치 해제"""
        try:
            if QApplication.overrideCursor():
                QApplication.restoreOverrideCursor()
            self.releaseKeyboard()
            self.releaseMouse()
        finally:
            super().closeEvent(event)

    def showEvent(self, event):
        """창 표시 시 입력 장치 확보"""
        super().showEvent(event)
        QApplication.setOverrideCursor(Qt.CrossCursor)
        self.grabKeyboard()
        self.grabMouse()
