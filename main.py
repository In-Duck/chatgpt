import sys
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow
import builtins

builtins.print = lambda *a, **k: None

def main():
    """애플리케이션 진입점"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 모던한 스타일 적용
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()