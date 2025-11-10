import time

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTextEdit, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QFont
from settings_dialog import SettingsDialog
from window_monitor import WindowMonitor
from key_input_worker import KeyInputWorker
from user_detector import UserDetector
from image_clicker_worker import ImageClickerWorker
from config_manager import ConfigManager
from buff_worker import BuffWorker
from hotkey_manager import HotkeyManager
from system_tray import SystemTrayManager
from image_detector import ImageDetector


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
        self.image_clicker_worker = ImageClickerWorker()
        self.buff1_worker = BuffWorker(1)
        self.buff2_worker = BuffWorker(2)
        self.buff3_worker = BuffWorker(3)
        self.image_detector = ImageDetector()  # 텔레그램 모니터 대신 이미지 감지기

        # 핫키 매니저 초기화
        self.hotkey_manager = HotkeyManager()

        # 시스템 트레이 매니저 초기화
        self.tray_manager = SystemTrayManager(self)

        # 상태
        self.is_monitoring = False
        self.is_key_input_active = False
        self.is_detecting = False
        self.is_image_clicking = False
        self.is_buff1_active = False
        self.is_buff2_active = False
        self.is_buff3_active = False
        self.is_image_detecting = False  # 거탐 이미지 감지 상태

        # 핫키 안내 라벨 (나중에 업데이트용)
        self.hotkey_info_label = None
        self.buff_info_labels = {}
        self.buff_intervals = {
            1: (0.0, 0.0),
            2: (0.0, 0.0),
            3: (0.0, 0.0),
        }
        self.buff_last_run = {1: None, 2: None, 3: None}

        self.init_ui()
        self.connect_signals()
        self.apply_config()
        self.setup_hotkeys()
        self.setup_system_tray()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("창 모니터링 & 자동화")
        self.setFixedSize(340, 580)

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

        buff_info_widget = QWidget()
        buff_info_widget.setStyleSheet("""
            QWidget#BuffInfoPanel {
                background-color: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
            QWidget#BuffInfoPanel QLabel[labelRole="header"] {
                color: #666;
                font-size: 8pt;
                font-weight: bold;
                padding-bottom: 2px;
            }
            QWidget#BuffInfoPanel QLabel[labelRole="icon"] {
                font-size: 10pt;
                font-weight: bold;
            }
            QWidget#BuffInfoPanel QLabel[labelRole="name"] {
                font-size: 9pt;
                font-weight: bold;
            }
            QWidget#BuffInfoPanel QLabel[labelRole="detail"] {
                font-size: 8.5pt;
            }
            QWidget#BuffInfoPanel QLabel[labelRole="icon"][state="active"],
            QWidget#BuffInfoPanel QLabel[labelRole="name"][state="active"] {
                color: #2e7d32;
            }
            QWidget#BuffInfoPanel QLabel[labelRole="icon"][state="inactive"] {
                color: #bbbbbb;
            }
            QWidget#BuffInfoPanel QLabel[labelRole="name"][state="inactive"] {
                color: #444444;
            }
            QWidget#BuffInfoPanel QLabel[labelRole="detail"][state="active"] {
                color: #2e7d32;
            }
            QWidget#BuffInfoPanel QLabel[labelRole="detail"][state="inactive"] {
                color: #555555;
            }
        """)
        buff_info_widget.setObjectName("BuffInfoPanel")

        buff_box = QVBoxLayout()
        buff_box.setContentsMargins(12, 10, 12, 10)
        buff_box.setSpacing(6)

        header_label = QLabel("버프 상태")
        header_label.setProperty("labelRole", "header")
        header_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        buff_box.addWidget(header_label)

        for idx in range(1, 4):
            row_widget = QWidget()
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            icon_label = QLabel("○")
            icon_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            icon_label.setProperty("labelRole", "icon")

            name_label = QLabel(f"버프{idx}")
            name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            name_label.setProperty("labelRole", "name")

            detail_label = QLabel()
            detail_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            detail_label.setProperty("labelRole", "detail")

            row_layout.addWidget(icon_label)
            row_layout.addWidget(name_label, 1)
            row_layout.addWidget(detail_label, 2)

            row_widget.setLayout(row_layout)

            self.buff_info_labels[idx] = {
                "icon": icon_label,
                "name": name_label,
                "detail": detail_label,
            }

            buff_box.addWidget(row_widget)

        buff_info_widget.setLayout(buff_box)
        button_layout.addWidget(buff_info_widget)

        # 셋째 줄: 유저탐색 / 리치
        third_row = QHBoxLayout()
        third_row.setSpacing(6)

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
        third_row.addWidget(self.detect_btn)

        self.image_click_btn = QPushButton("리치")
        self.image_click_btn.setMinimumHeight(36)
        self.image_click_btn.setStyleSheet("""
            QPushButton {
                background-color: #00BCD4;
                color: white;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0097A7;
            }
        """)
        self.image_click_btn.clicked.connect(self.toggle_image_clicking)
        third_row.addWidget(self.image_click_btn)

        button_layout.addLayout(third_row)

        # 넷째 줄: 거탐 감지 (이미지 기반)
        fourth_row = QHBoxLayout()
        fourth_row.setSpacing(6)

        self.image_detect_btn = QPushButton("거탐 감지")
        self.image_detect_btn.setMinimumHeight(36)
        self.image_detect_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
        """)
        self.image_detect_btn.clicked.connect(self.toggle_image_detection)
        fourth_row.addWidget(self.image_detect_btn)

        button_layout.addLayout(fourth_row)

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
        self.update_buff_info_labels()

    def connect_signals(self):
        """시그널 연결"""
        self.buff1_worker.last_run_updated.connect(lambda ts: self.on_buff_last_run_updated(1, ts))
        self.buff2_worker.last_run_updated.connect(lambda ts: self.on_buff_last_run_updated(2, ts))
        self.buff3_worker.last_run_updated.connect(lambda ts: self.on_buff_last_run_updated(3, ts))
        
        # 이미지 클릭 워커 시그널 연결
        self.image_clicker_worker.image_clicked.connect(self.on_image_clicked)
        self.image_clicker_worker.error_occurred.connect(self.on_image_click_error)
        
        # 이미지 감지기 시그널 연결
        self.image_detector.image_detected.connect(self.on_image_detected)

    def on_image_detected(self, message: str):
        """이미지 감지 시 호출"""
        print(f"거탐 이미지 감지: {message}")

    def setup_hotkeys(self):
        """핫키 설정"""
        # 설정에서 핫키 로드
        self.hotkey_manager.set_hotkeys(
            pickup=self.config.get("hotkey_pickup", "f9"),
            buff=self.config.get("hotkey_buff", "f10"),
            monitor=self.config.get("hotkey_monitor", "f11"),
            detector=self.config.get("hotkey_detector", "f12"),
            image_click=self.config.get("hotkey_image_click", "")
        )

        # 핫키 시그널 연결
        self.hotkey_manager.pickup_toggle.connect(self.toggle_key_input)
        self.hotkey_manager.buff_toggle.connect(self.toggle_all_buffs)
        self.hotkey_manager.monitor_toggle.connect(self.toggle_monitoring)
        self.hotkey_manager.detector_toggle.connect(self.toggle_detection)
        self.hotkey_manager.image_click_toggle.connect(self.toggle_image_clicking)

        # 핫키 활성화
        self.hotkey_manager.enable_hotkeys()

        # 핫키 안내 업데이트
        self.update_hotkey_info()

    def update_hotkey_info(self):
        """핫키 안내 텍스트 업데이트"""
        hotkey_text = "핫키: " + self.hotkey_manager.get_hotkey_display()
        self.hotkey_info_label.setText(hotkey_text)

    def on_buff_last_run_updated(self, buff_number: int, timestamp: float):
        """버프 워커에서 마지막 실행 시간이 갱신될 때 호출"""
        self.buff_last_run[buff_number] = timestamp
        self.update_buff_info_labels()

    def on_image_clicked(self, x: int, y: int):
        """이미지 클릭 성공 시 호출"""
        print(f"이미지 클릭: ({x}, {y})")

    def on_image_click_error(self, error_msg: str):
        """이미지 클릭 오류 발생 시 호출"""
        print(f"이미지 클릭 오류: {error_msg}")

    def update_buff_info_labels(self):
        """버프 간격 및 마지막 실행 정보를 UI에 표시"""
        active_map = {
            1: self.is_buff1_active,
            2: self.is_buff2_active,
            3: self.is_buff3_active,
        }

        for idx in range(1, 4):
            row = self.buff_info_labels.get(idx)
            if not row:
                continue

            min_interval, max_interval = self.buff_intervals.get(idx, (0.0, 0.0))
            if min_interval == 0.0 and max_interval == 0.0:
                interval_text = "간격 없음"
            elif abs(min_interval - max_interval) < 0.001:
                interval_text = f"간격 {min_interval:.1f}초"
            else:
                interval_text = f"간격 {min_interval:.1f}~{max_interval:.1f}초"

            last_run = self.buff_last_run.get(idx)
            if last_run:
                last_text = time.strftime("마지막 %H:%M:%S", time.localtime(last_run))
            else:
                last_text = "마지막 --"

            is_active = active_map[idx]
            icon_text = "●" if is_active else "○"

            detail_suffix = "실행 중" if is_active else "대기 중"
            detail_text = f"{interval_text} · {last_text} · {detail_suffix}"

            row["icon"].setText(icon_text)
            row["detail"].setText(detail_text)

            state_value = "active" if is_active else "inactive"
            for key in ("icon", "name", "detail"):
                label = row[key]
                label.setProperty("state", state_value)
                label.style().unpolish(label)
                label.style().polish(label)
                label.update()

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
        self.buff_intervals[1] = (
            self.config.get("buff1_min_interval", 5.0),
            self.config.get("buff1_max_interval", 10.0),
        )

        self.buff2_worker.set_config(
            self.config.get("buff2_key", "2"),
            self.config.get("buff2_min_interval", 5.0),
            self.config.get("buff2_max_interval", 10.0),
            self.config.get("buff2_press_count", 1)
        )
        self.buff_intervals[2] = (
            self.config.get("buff2_min_interval", 5.0),
            self.config.get("buff2_max_interval", 10.0),
        )

        self.buff3_worker.set_config(
            self.config.get("buff3_key", "3"),
            self.config.get("buff3_min_interval", 5.0),
            self.config.get("buff3_max_interval", 10.0),
            self.config.get("buff3_press_count", 1)
        )
        self.buff_intervals[3] = (
            self.config.get("buff3_min_interval", 5.0),
            self.config.get("buff3_max_interval", 10.0),
        )

        self.update_buff_info_labels()

        # 유저 탐지 설정
        if self.config.get("detection_region"):
            self.user_detector.set_config(
                self.config.get("detection_region", (0, 0, 100, 100)),
                self.config.get("telegram_token", ""),
                self.config.get("telegram_chat_id", ""),
                self.config.get("user_nickname", "유저")
            )

        # 거탐 이미지 감지 설정 - false_detection_region 사용
        template_paths = [
            "gt1.png",
            "gt2.png",
            "gt3.png"
        ]
        if self.config.get("telegram_token") and self.config.get("telegram_chat_id"):
            # false_detection_region이 있으면 사용, 없으면 detection_region 사용
            detection_region = self.config.get("false_detection_region", self.config.get("detection_region", (0, 0, 100, 100)))
            self.image_detector.set_config(
                detection_region,
                template_paths,
                self.config.get("telegram_token", ""),
                self.config.get("telegram_chat_id", ""),
                self.config.get("user_nickname", "유저"),
                0.7
            )

        # 이미지 클릭 설정 - surak.png 자동 로드
        if self.config.get("image_click_region"):
            self.image_clicker_worker.set_config(
                self.config.get("image_click_region", (0, 0, 100, 100)),
                "surak.png",  # 항상 surak.png 사용
                self.config.get("image_click_confidence", 0.8)
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
        was_active = self.is_buff1_active

        if was_active:
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

        if not was_active:
            self.buff_last_run[1] = None

        self.update_status()

    def toggle_buff2(self):
        """버프2 토글"""
        was_active = self.is_buff2_active

        if was_active:
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

        if not was_active:
            self.buff_last_run[2] = None

        self.update_status()

    def toggle_buff3(self):
        """버프3 토글"""
        was_active = self.is_buff3_active

        if was_active:
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

        if not was_active:
            self.buff_last_run[3] = None

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

    def toggle_image_clicking(self):
        """이미지 클릭 토글"""
        if not self.config.get("image_click_region"):
            QMessageBox.warning(self, "경고", "이미지 클릭 설정이 완료되지 않았습니다.\n환경설정에서 구역을 설정해주세요.")
            return

        if self.is_image_clicking:
            self.image_clicker_worker.stop()
            self.is_image_clicking = False
            self.image_click_btn.setText("리치")
            self.image_click_btn.setStyleSheet("""
                QPushButton {
                    background-color: #00BCD4;
                    color: white;
                    font-size: 10pt;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #0097A7;
                }
            """)
        else:
            self.image_clicker_worker.start()
            self.is_image_clicking = True
            self.image_click_btn.setText("리치 ●")
            self.image_click_btn.setStyleSheet("""
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

    def toggle_image_detection(self):
        """거탐 이미지 감지 토글"""
        if not self.config.get("telegram_token") or not self.config.get("telegram_chat_id"):
            QMessageBox.warning(self, "경고", "텔레그램 설정이 완료되지 않았습니다.\n환경설정에서 봇 토큰과 채팅 ID를 설정해주세요.")
            return

        if self.is_image_detecting:
            self.image_detector.stop()
            self.is_image_detecting = False
            self.image_detect_btn.setText("거탐 감지")
            self.image_detect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #607D8B;
                    color: white;
                    font-size: 10pt;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #455A64;
                }
            """)
        else:
            self.image_detector.start()
            self.is_image_detecting = True
            self.image_detect_btn.setText("거탐 감지 ●")
            self.image_detect_btn.setStyleSheet("""
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
        if not self.is_image_clicking and self.config.get("image_click_region"):
            self.toggle_image_clicking()
        if not self.is_image_detecting and self.config.get("telegram_token") and self.config.get("telegram_chat_id"):
            self.toggle_image_detection()

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
        if self.is_image_clicking:
            self.toggle_image_clicking()
        if self.is_image_detecting:
            self.toggle_image_detection()

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
            if self.is_image_clicking:
                self.toggle_image_clicking()
            if self.is_image_detecting:
                self.toggle_image_detection()

            # 새 설정 적용
            self.apply_config()

            # 핫키 재설정
            self.hotkey_manager.set_hotkeys(
                pickup=new_settings.get("hotkey_pickup", ""),
                buff=new_settings.get("hotkey_buff", ""),
                monitor=new_settings.get("hotkey_monitor", ""),
                detector=new_settings.get("hotkey_detector", ""),
                image_click=new_settings.get("hotkey_image_click", "")
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
        if self.is_image_clicking:
            running_items.append("🖱️ 리치")
        if self.is_image_detecting:
            running_items.append("📱 거탐감지")

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
        self.update_buff_info_labels()

    def changeEvent(self, event):
        """창 상태 변경 이벤트"""
        if event.type() == event.WindowStateChange:
            if self.isMinimized():
                # 최소화 시 기본 동작을 유지하여 작업 표시줄에 남도록 처리
                self.showMinimized()
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
        if self.is_image_clicking:
            self.image_clicker_worker.stop()
        if self.is_image_detecting:
            self.image_detector.stop()

        # 핫키 비활성화
        self.hotkey_manager.disable_hotkeys()

        # 트레이 아이콘 숨기기
        self.tray_manager.hide_tray()

        event.accept()