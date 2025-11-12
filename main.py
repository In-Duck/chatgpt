import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from main_window import MainWindow
import builtins

builtins.print = lambda *a, **k: None

# print 함수를 재정의하여 한글 출력 문제 해결
def main():
    """애플리케이션 진입점"""
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("instargram.ico"))
    app.setStyle('Fusion')  # 모던한 스타일 적용
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()