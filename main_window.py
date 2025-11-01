from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTextEdit, QMessageBox, QGridLayout)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QFont
from settings_dialog import SettingsDialog
from window_monitor import WindowMonitor
from key_input_worker import KeyInputWorker
from user_detector import UserDetector
from config_manager import ConfigManager
from buff_worker import BuffWorker
from hotkey_manager import HotkeyManager
from system_tray import SystemTrayManager


class MainWindow(QMainWindow):
    """메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        
        # 워커 초기화
        self.window_monitor = WindowMonitor()
        self.key_input_worker = KeyInputWorker()
        self.user_detector = UserDetector()
        self.buff1_worker = BuffWorker(1)
        self.buff2_worker = BuffWorker(2)
        self.buff3_worker = BuffWorker(3)
        
        # 핫키 매니저 초기화
        self.hotkey_manager = HotkeyManager()
        
        # 시스템 트레이 매니저 초기화
        self.tray_manager = SystemTrayManager(self)
        
        # 상태
        self.is_monitoring = False
        self.is_key_input_active = False
        self.is_detecting = False
        self.is_buff1_active = False
        self.is_buff2_active = False
        self.is_buff3_active = False
        
        # 핫키 안내 라벨 (나중에 업데이트용)
        self.hotkey_info_label = None
        
        self.init_ui()
        self.connect_signals()
        self.apply_config()
        self.setup_hotkeys()
        self.setup_system_tray()
        self.check_for_updates_on_startup()
    
    def check_for_updates_on_startup(self):
        """프로그램 시작 시 업데이트 확인"""
        try:
            from update_checker import UpdateChecker
            
            checker = UpdateChecker("In-Duck/MapleLand")
            has_update, release_info = checker.check_for_updates()
            
            if has_update and release_info:
                reply = QMessageBox.question(
                    self,
                    "업데이트 가능",
                    f"새로운 버전이 있습니다!\n\n"
                    f"현재 버전: {checker.get_current_version()}\n"
                    f"최신 버전: {release_info['version']}\n\n"
                    f"지금 업데이트하시겠습니까?\n"
                    f"(나중에 환경설정 > 업데이트 탭에서도 업데이트할 수 있습니다)",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    import subprocess
                    import sys
                    subprocess.Popen([sys.executable, "updater.py", release_info['download_url'], release_info['version']])
                    sys.exit(0)
        
        except Exception as e:
            print(f"업데이트 확인 중 오류: {e}")
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("창 모니터링 & 자동화")
        self.setFixedSize(340, 480)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 타이틀
        title = QLabel("창 모니터링 & 자동화")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 핫키 안내
        self.hotkey_info_label = QLabel()
        self.hotkey_info_label.setStyleSheet("color: #666; font-size: 8pt;")
        self.hotkey_info_label.setAlignment(Qt.AlignCenter)
        self.hotkey_info_label.setWordWrap(True)
        layout.addWidget(self.hotkey_info_label)
        
        # 현재 실행 상태 - 간결하게 표시
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            background-color: #f5f5f5; 
            padding: 8px; 
            border-radius: 4px;
            font-size: 9pt;
            font-weight: bold;
        """)
        self.status_label.setWordWrap(True)
        self.status_label.setMaximumHeight(50)
        layout.addWidget(self.status_label)
        
        # 버튼 영역
        button_layout = QVBoxLayout()
        button_layout.setSpacing(6)
        
        # 첫째 줄: 감지 시작 / 줍기 시작
        first_row = QHBoxLayout()
        first_row.setSpacing(6)
        
        self.monitor_btn = QPushButton("감지 시작")
        self.monitor_btn.setMinimumHeight(36)
        self.monitor_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.monitor_btn.clicked.connect(self.toggle_monitoring)
        first_row.addWidget(self.monitor_btn)
        
        self.key_input_btn = QPushButton("줍기 시작")
        self.key_input_btn.setMinimumHeight(36)
        self.key_input_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        self.key_input_btn.clicked.connect(self.toggle_key_input)
        first_row.addWidget(self.key_input_btn)
        
        button_layout.addLayout(first_row)
        
        # 둘째 줄: 버프1 / 버프2 / 버프3
        second_row = QHBoxLayout()
        second_row.setSpacing(6)
        
        self.buff1_btn = QPushButton("버프1")
        self.buff1_btn.setMinimumHeight(36)
        self.buff1_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                font-size: 9pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
        """)
        self.buff1_btn.clicked.connect(self.toggle_buff1)
        second_row.addWidget(self.buff1_btn)
        
        self.buff2_btn = QPushButton("버프2")
        self.buff2_btn.setMinimumHeight(36)
        self.buff2_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-size: 9pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.buff2_btn.clicked.connect(self.toggle_buff2)
        second_row.addWidget(self.buff2_btn)
        
        self.buff3_btn = QPushButton("버프3")
        self.buff3_btn.setMinimumHeight(36)
        self.buff3_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFC107;
                color: white;
                font-size: 9pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #FFA000;
            }
        """)
        self.buff3_btn.clicked.connect(self.toggle_buff3)
        second_row.addWidget(self.buff3_btn)
        
        button_layout.addLayout(second_row)
        
        # 유저탐색 버튼
        self.detect_btn = QPushButton("유저탐색")
        self.detect_btn.setMinimumHeight(36)
        self.detect_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.detect_btn.clicked.connect(self.toggle_detection)
        button_layout.addWidget(self.detect_btn)
        
        # 일괄 시작/중지 버튼 (2개로 분리)
        batch_row = QHBoxLayout()
        batch_row.setSpacing(6)
        
        self.batch_start_btn = QPushButton("일괄 시작")
        self.batch_start_btn.setMinimumHeight(36)
        self.batch_start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.batch_start_btn.clicked.connect(self.batch_start_all)
        batch_row.addWidget(self.batch_start_btn)
        
        self.batch_stop_btn = QPushButton("일괄 중지")
        self.batch_stop_btn.setMinimumHeight(36)
        self.batch_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.batch_stop_btn.clicked.connect(self.batch_stop_all)
        batch_row.addWidget(self.batch_stop_btn)
        
        button_layout.addLayout(batch_row)
        
        # 환경설정 버튼
        settings_btn = QPushButton("환경설정")
        settings_btn.setMinimumHeight(36)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        settings_btn.clicked.connect(self.open_settings)
        button_layout.addWidget(settings_btn)
        
        layout.addLayout(button_layout)
        
        central_widget.setLayout(layout)
        
        self.update_status()
    
    def connect_signals(self):
        """시그널 연결"""
        pass
    
    def setup_hotkeys(self):
        """핫키 설정"""
        # 설정에서 핫키 로드
        self.hotkey_manager.set_hotkeys(
            pickup=self.config.get("hotkey_pickup", "f9"),
            buff=self.config.get("hotkey_buff", "f10"),
            monitor=self.config.get("hotkey_monitor", "f11"),
            detector=self.config.get("hotkey_detector", "f12")
        )
        
        # 핫키 시그널 연결
        self.hotkey_manager.pickup_toggle.connect(self.toggle_key_input)
        self.hotkey_manager.buff_toggle.connect(self.toggle_all_buffs)
        self.hotkey_manager.monitor_toggle.connect(self.toggle_monitoring)
        self.hotkey_manager.detector_toggle.connect(self.toggle_detection)
        
        # 핫키 활성화
        self.hotkey_manager.enable_hotkeys()
        
        # 핫키 안내 업데이트
        self.update_hotkey_info()
    
    def update_hotkey_info(self):
        """핫키 안내 텍스트 업데이트"""
        hotkey_text = "핫키: " + self.hotkey_manager.get_hotkey_display()
        self.hotkey_info_label.setText(hotkey_text)
    
    def setup_system_tray(self):
        """시스템 트레이 설정"""
        # 트레이 시그널 연결
        self.tray_manager.show_window.connect(self.show_from_tray)
        self.tray_manager.hide_window.connect(self.hide_to_tray)
        self.tray_manager.start_all.connect(self.batch_start_all)
        self.tray_manager.stop_all.connect(self.batch_stop_all)
        self.tray_manager.quit_app.connect(self.quit_application)
        
        # 트레이 설정 및 표시
        self.tray_manager.setup_tray()
        self.tray_manager.show_tray()
    
    def toggle_all_buffs(self):
        """모든 버프 토글 (버프 핫키용)"""
        # 하나라도 실행 중이면 모두 중지, 아니면 모두 시작
        any_active = self.is_buff1_active or self.is_buff2_active or self.is_buff3_active
        
        if any_active:
            if self.is_buff1_active:
                self.toggle_buff1()
            if self.is_buff2_active:
                self.toggle_buff2()
            if self.is_buff3_active:
                self.toggle_buff3()
        else:
            if not self.is_buff1_active:
                self.toggle_buff1()
            if not self.is_buff2_active:
                self.toggle_buff2()
            if not self.is_buff3_active:
                self.toggle_buff3()
    
    def show_from_tray(self):
        """트레이에서 창 보이기"""
        self.show()
        self.activateWindow()
    
    def hide_to_tray(self):
        """창을 트레이로 숨기기"""
        self.hide()
        self.tray_manager.show_message("알림", "트레이로 최소화되었습니다.\n더블클릭으로 다시 열 수 있습니다.")
    
    def quit_application(self):
        """애플리케이션 종료"""
        self.close()
    
    def apply_config(self):
        """설정 적용"""
        # 창 모니터 설정
        if self.config.get("selected_window"):
            hwnd = self.config["selected_window"]["hwnd"]
            title = self.config["selected_window"]["title"]
            self.window_monitor.set_target_window(hwnd, title)
        
        # 줍기 워커 설정
        self.key_input_worker.set_config(
            self.config.get("key_to_press", "space"),
            self.config.get("min_interval", 5.0),
            self.config.get("max_interval", 10.0),
            self.config.get("press_count", 1)
        )
        
        # 버프 워커 설정
        self.buff1_worker.set_config(
            self.config.get("buff1_key", "1"),
            self.config.get("buff1_min_interval", 5.0),
            self.config.get("buff1_max_interval", 10.0),
            self.config.get("buff1_press_count", 1)
        )
        
        self.buff2_worker.set_config(
            self.config.get("buff2_key", "2"),
            self.config.get("buff2_min_interval", 5.0),
            self.config.get("buff2_max_interval", 10.0),
            self.config.get("buff2_press_count", 1)
        )
        
        self.buff3_worker.set_config(
            self.config.get("buff3_key", "3"),
            self.config.get("buff3_min_interval", 5.0),
            self.config.get("buff3_max_interval", 10.0),
            self.config.get("buff3_press_count", 1)
        )
        
        # 유저 탐지 설정
        if self.config.get("detection_region"):
            self.user_detector.set_config(
                self.config.get("detection_region", (0, 0, 100, 100)),
                self.config.get("telegram_token", ""),
                self.config.get("telegram_chat_id", ""),
                self.config.get("user_nickname", "유저")
            )
    
    def toggle_monitoring(self):
        """창 감지 토글"""
        if not self.window_monitor.is_window_valid():
            QMessageBox.warning(self, "경고", "모니터링할 창이 선택되지 않았거나 유효하지 않습니다.\n환경설정에서 창을 선택해주세요.")
            return
        
        if self.is_monitoring:
            self.window_monitor.stop_monitoring()
            self.is_monitoring = False
            self.monitor_btn.setText("감지 시작")
            self.monitor_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-size: 10pt;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
        else:
            self.window_monitor.start_monitoring()
            self.is_monitoring = True
            self.monitor_btn.setText("감지 중지")
            self.monitor_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-size: 10pt;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
        
        self.update_status()
    
    def toggle_key_input(self):
        """줍기 토글"""
        if self.is_key_input_active:
            self.key_input_worker.stop()
            self.is_key_input_active = False
            self.key_input_btn.setText("줍기 시작")
            self.key_input_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    font-size: 10pt;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #0b7dda;
                }
            """)
        else:
            self.key_input_worker.start()
            self.is_key_input_active = True
            self.key_input_btn.setText("줍기 중지")
            self.key_input_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-size: 10pt;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
        
        self.update_status()
    
    def toggle_buff1(self):
        """버프1 토글"""
        if self.is_buff1_active:
            self.buff1_worker.stop()
            self.is_buff1_active = False
            self.buff1_btn.setText("버프1")
            self.buff1_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF5722;
                    color: white;
                    font-size: 9pt;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #E64A19;
                }
            """)
        else:
            self.buff1_worker.start()
            self.is_buff1_active = True
            self.buff1_btn.setText("버프1 ●")
            self.buff1_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-size: 9pt;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
        
        self.update_status()
    
    def toggle_buff2(self):
        """버프2 토글"""
        if self.is_buff2_active:
            self.buff2_worker.stop()
            self.is_buff2_active = False
            self.buff2_btn.setText("버프2")
            self.buff2_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    font-size: 9pt;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
            """)
        else:
            self.buff2_worker.start()
            self.is_buff2_active = True
            self.buff2_btn.setText("버프2 ●")
            self.buff2_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-size: 9pt;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
        
        self.update_status()
    
    def toggle_buff3(self):
        """버프3 토글"""
        if self.is_buff3_active:
            self.buff3_worker.stop()
            self.is_buff3_active = False
            self.buff3_btn.setText("버프3")
            self.buff3_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFC107;
                    color: white;
                    font-size: 9pt;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #FFA000;
                }
            """)
        else:
            self.buff3_worker.start()
            self.is_buff3_active = True
            self.buff3_btn.setText("버프3 ●")
            self.buff3_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-size: 9pt;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
        
        self.update_status()
    
    def toggle_detection(self):
        """유저 탐색 토글"""
        if not self.config.get("detection_region"):
            QMessageBox.warning(self, "경고", "탐색 구역이 설정되지 않았습니다.\n환경설정에서 구역을 설정해주세요.")
            return
        
        if self.is_detecting:
            self.user_detector.stop()
            self.is_detecting = False
            self.detect_btn.setText("유저탐색")
            self.detect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #9C27B0;
                    color: white;
                    font-size: 10pt;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #7B1FA2;
                }
            """)
        else:
            self.user_detector.start()
            self.is_detecting = True
            self.detect_btn.setText("유저탐색 ●")
            self.detect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-size: 10pt;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
        
        self.update_status()
    
    def batch_start_all(self):
        """모든 기능을 일괄 시작"""
        if not self.window_monitor.is_window_valid():
            QMessageBox.warning(self, "경고", "모니터링할 창이 선택되지 않았거나 유효하지 않습니다.\n환경설정에서 창을 선택해주세요.")
            return
        
        # 모두 시작
        if not self.is_monitoring:
            self.toggle_monitoring()
        if not self.is_key_input_active:
            self.toggle_key_input()
        if not self.is_buff1_active:
            self.toggle_buff1()
        if not self.is_buff2_active:
            self.toggle_buff2()
        if not self.is_buff3_active:
            self.toggle_buff3()
        if not self.is_detecting and self.config.get("detection_region"):
            self.toggle_detection()
    
    def batch_stop_all(self):
        """실행 중인 모든 기능을 일괄 중지"""
        # 실행 중인 것만 중지
        if self.is_monitoring:
            self.toggle_monitoring()
        if self.is_key_input_active:
            self.toggle_key_input()
        if self.is_buff1_active:
            self.toggle_buff1()
        if self.is_buff2_active:
            self.toggle_buff2()
        if self.is_buff3_active:
            self.toggle_buff3()
        if self.is_detecting:
            self.toggle_detection()
    
    def open_settings(self):
        """환경설정 다이얼로그 열기"""
        dialog = SettingsDialog(self, self.config)
        if dialog.exec_():
            new_settings = dialog.get_settings()
            
            # 설정 업데이트
            self.config.update(new_settings)
            self.config_manager.save_config(self.config)
            
            # 실행 중이면 중지
            if self.is_monitoring:
                self.toggle_monitoring()
            if self.is_key_input_active:
                self.toggle_key_input()
            if self.is_buff1_active:
                self.toggle_buff1()
            if self.is_buff2_active:
                self.toggle_buff2()
            if self.is_buff3_active:
                self.toggle_buff3()
            if self.is_detecting:
                self.toggle_detection()
            
            # 새 설정 적용
            self.apply_config()
            
            # 핫키 재설정
            self.hotkey_manager.set_hotkeys(
                pickup=new_settings.get("hotkey_pickup", ""),
                buff=new_settings.get("hotkey_buff", ""),
                monitor=new_settings.get("hotkey_monitor", ""),
                detector=new_settings.get("hotkey_detector", "")
            )
            
            # 핫키 안내 업데이트
            self.update_hotkey_info()
            
            self.update_status()
            
            QMessageBox.information(self, "알림", "설정이 저장되었습니다.")
    
    def update_status(self):
        """상태 텍스트 업데이트 - 간결하게"""
        running_items = []
        
        if self.is_monitoring:
            running_items.append("👁️ 감지")
        if self.is_key_input_active:
            running_items.append("🎯 줍기")
        if self.is_buff1_active:
            running_items.append("⚡ 버프1")
        if self.is_buff2_active:
            running_items.append("⚡ 버프2")
        if self.is_buff3_active:
            running_items.append("⚡ 버프3")
        if self.is_detecting:
            running_items.append("🔍 유저탐색")
        
        if running_items:
            status_text = "🟢 실행중: " + " | ".join(running_items)
        else:
            status_text = "⚪ 대기중"
        
        self.status_label.setText(status_text)
        
        # 트레이 툴팁 업데이트
        if running_items:
            self.tray_manager.update_tooltip("실행중: " + ", ".join(running_items))
        else:
            self.tray_manager.update_tooltip("대기중")
    
    def changeEvent(self, event):
        """창 상태 변경 이벤트"""
        if event.type() == event.WindowStateChange:
            if self.isMinimized():
                # 최소화 시 트레이로 숨기기
                QTimer.singleShot(0, self.hide_to_tray)
        super().changeEvent(event)
    
    def closeEvent(self, event):
        """창 닫기 이벤트"""
        # 모든 워커 중지
        if self.is_monitoring:
            self.window_monitor.stop_monitoring()
        if self.is_key_input_active:
            self.key_input_worker.stop()
        if self.is_buff1_active:
            self.buff1_worker.stop()
        if self.is_buff2_active:
            self.buff2_worker.stop()
        if self.is_buff3_active:
            self.buff3_worker.stop()
        if self.is_detecting:
            self.user_detector.stop()
        
        # 핫키 비활성화
        self.hotkey_manager.disable_hotkeys()
        
        # 트레이 아이콘 숨기기
        self.tray_manager.hide_tray()
        
        event.accept()