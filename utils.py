# utils.py
import os
import sys

def resource_path(relative_path: str) -> str:
    """PyInstaller 실행 또는 IDE 실행 둘 다 호환되는 리소스 경로 반환"""
    try:
        # PyInstaller로 빌드된 경우
        base_path = sys._MEIPASS
    except Exception:
        # 개발 중 (예: Visual Studio Code, PyCharm)
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
