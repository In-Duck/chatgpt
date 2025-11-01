from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QDoubleSpinBox, QSpinBox, QPushButton, 
                             QGroupBox, QRadioButton, QButtonGroup, QScrollArea, 
                             QWidget, QTabWidget, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from window_monitor import WindowMonitor
from region_preview import RegionPreviewWindow
from hotkey_input_widget import HotkeyInputWidget
from typing import Optional, Tuple


class SettingsDialog(QDialog):
    """환경설정 다이얼로그"""
    
    def __init__(self, parent=None, current_config=None):
        super().__init__(parent)
        self.current_config = current_config or {}
        self.selected_window: Optional[Tuple[int, str]] = None
        self.preview_window: Optional[RegionPreviewWindow] = None
        self.preview_timer: Optional[QTimer] = None
        self.init_ui()
        self.load_current_settings()
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("환경설정")
        self.setFixedSize(380, 600)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # 탭 위젯 생성
        tabs = QTabWidget()
        
        # 탭 1: 기본 설정
        basic_tab = QWidget()
        basic_layout = QVBoxLayout()
        basic_layout.setSpacing(8)
        basic_layout.setContentsMargins(6, 6, 6, 6)
        
        # 창 선택 섹션
        window_group = QGroupBox("모니터링할 창 선택")
        window_layout = QVBoxLayout()
        window_layout.setSpacing(6)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(180)
        
        scroll_widget = QWidget()
        self.window_list_layout = QVBoxLayout(scroll_widget)
        self.window_list_layout.setSpacing(4)
        self.window_button_group = QButtonGroup()
        self.window_button_group.setExclusive(True)
        
        self.refresh_window_list()
        
        scroll.setWidget(scroll_widget)
        window_layout.addWidget(scroll)
        
        refresh_btn = QPushButton("창 목록 새로고침")
        refresh_btn.setMaximumHeight(30)
        refresh_btn.clicked.connect(self.refresh_window_list)
        window_layout.addWidget(refresh_btn)
        
        window_group.setLayout(window_layout)
        basic_layout.addWidget(window_group)
        
        # 줍기 설정 섹션
        key_group = QGroupBox("줍기 설정")
        key_layout = QVBoxLayout()
        key_layout.setSpacing(6)
        
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("입력할 키:"))
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("예: space, z, x...")
        key_row.addWidget(self.key_input)
        key_layout.addLayout(key_row)
        
        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("최소 간격(초):"))
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setMinimum(0.1)
        self.min_spin.setMaximum(3600.0)
        self.min_spin.setSingleStep(0.1)
        self.min_spin.setDecimals(1)
        self.min_spin.setValue(5.0)
        interval_row.addWidget(self.min_spin)
        
        interval_row.addWidget(QLabel("최대 간격(초):"))
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setMinimum(0.1)
        self.max_spin.setMaximum(3600.0)
        self.max_spin.setSingleStep(0.1)
        self.max_spin.setDecimals(1)
        self.max_spin.setValue(10.0)
        interval_row.addWidget(self.max_spin)
        key_layout.addLayout(interval_row)
        
        count_row = QHBoxLayout()
        count_row.addWidget(QLabel("간격당 입력 횟수:"))
        self.count_spin = QSpinBox()
        self.count_spin.setMinimum(1)
        self.count_spin.setMaximum(100)
        self.count_spin.setValue(1)
        count_row.addWidget(self.count_spin)
        key_layout.addLayout(count_row)
        
        key_group.setLayout(key_layout)
        basic_layout.addWidget(key_group)
        
        basic_tab.setLayout(basic_layout)
        tabs.addTab(basic_tab, "기본 설정")
        
        # 탭 2: 버프 설정
        buff_tab = QWidget()
        buff_scroll = QScrollArea()
        buff_scroll.setWidgetResizable(True)
        
        buff_scroll_widget = QWidget()
        buff_layout = QVBoxLayout(buff_scroll_widget)
        buff_layout.setSpacing(8)
        buff_layout.setContentsMargins(6, 6, 6, 6)
        
        # 버프1 설정
        buff1_group = QGroupBox("버프1 설정")
        buff1_layout = QVBoxLayout()
        buff1_layout.setSpacing(6)
        
        buff1_key_row = QHBoxLayout()
        buff1_key_row.addWidget(QLabel("키:"))
        self.buff1_key_input = QLineEdit()
        self.buff1_key_input.setPlaceholderText("예: 1, q...")
        buff1_key_row.addWidget(self.buff1_key_input)
        buff1_layout.addLayout(buff1_key_row)
        
        buff1_interval_row = QHBoxLayout()
        buff1_interval_row.addWidget(QLabel("최소(초):"))
        self.buff1_min_spin = QDoubleSpinBox()
        self.buff1_min_spin.setMinimum(0.1)
        self.buff1_min_spin.setMaximum(3600.0)
        self.buff1_min_spin.setSingleStep(0.1)
        self.buff1_min_spin.setDecimals(1)
        self.buff1_min_spin.setValue(5.0)
        buff1_interval_row.addWidget(self.buff1_min_spin)
        
        buff1_interval_row.addWidget(QLabel("최대(초):"))
        self.buff1_max_spin = QDoubleSpinBox()
        self.buff1_max_spin.setMinimum(0.1)
        self.buff1_max_spin.setMaximum(3600.0)
        self.buff1_max_spin.setSingleStep(0.1)
        self.buff1_max_spin.setDecimals(1)
        self.buff1_max_spin.setValue(10.0)
        buff1_interval_row.addWidget(self.buff1_max_spin)
        
        buff1_interval_row.addWidget(QLabel("횟수:"))
        self.buff1_count_spin = QSpinBox()
        self.buff1_count_spin.setMinimum(1)
        self.buff1_count_spin.setMaximum(100)
        self.buff1_count_spin.setValue(1)
        buff1_interval_row.addWidget(self.buff1_count_spin)
        buff1_layout.addLayout(buff1_interval_row)
        
        buff1_group.setLayout(buff1_layout)
        buff_layout.addWidget(buff1_group)
        
        # 버프2 설정
        buff2_group = QGroupBox("버프2 설정")
        buff2_layout = QVBoxLayout()
        buff2_layout.setSpacing(6)
        
        buff2_key_row = QHBoxLayout()
        buff2_key_row.addWidget(QLabel("키:"))
        self.buff2_key_input = QLineEdit()
        self.buff2_key_input.setPlaceholderText("예: 2, w...")
        buff2_key_row.addWidget(self.buff2_key_input)
        buff2_layout.addLayout(buff2_key_row)
        
        buff2_interval_row = QHBoxLayout()
        buff2_interval_row.addWidget(QLabel("최소(초):"))
        self.buff2_min_spin = QDoubleSpinBox()
        self.buff2_min_spin.setMinimum(0.1)
        self.buff2_min_spin.setMaximum(3600.0)
        self.buff2_min_spin.setSingleStep(0.1)
        self.buff2_min_spin.setDecimals(1)
        self.buff2_min_spin.setValue(5.0)
        buff2_interval_row.addWidget(self.buff2_min_spin)
        
        buff2_interval_row.addWidget(QLabel("최대(초):"))
        self.buff2_max_spin = QDoubleSpinBox()
        self.buff2_max_spin.setMinimum(0.1)
        self.buff2_max_spin.setMaximum(3600.0)
        self.buff2_max_spin.setSingleStep(0.1)
        self.buff2_max_spin.setDecimals(1)
        self.buff2_max_spin.setValue(10.0)
        buff2_interval_row.addWidget(self.buff2_max_spin)
        
        buff2_interval_row.addWidget(QLabel("횟수:"))
        self.buff2_count_spin = QSpinBox()
        self.buff2_count_spin.setMinimum(1)
        self.buff2_count_spin.setMaximum(100)
        self.buff2_count_spin.setValue(1)
        buff2_interval_row.addWidget(self.buff2_count_spin)
        buff2_layout.addLayout(buff2_interval_row)
        
        buff2_group.setLayout(buff2_layout)
        buff_layout.addWidget(buff2_group)
        
        # 버프3 설정
        buff3_group = QGroupBox("버프3 설정")
        buff3_layout = QVBoxLayout()
        buff3_layout.setSpacing(6)
        
        buff3_key_row = QHBoxLayout()
        buff3_key_row.addWidget(QLabel("키:"))
        self.buff3_key_input = QLineEdit()
        self.buff3_key_input.setPlaceholderText("예: 3, e...")
        buff3_key_row.addWidget(self.buff3_key_input)
        buff3_layout.addLayout(buff3_key_row)
        
        buff3_interval_row = QHBoxLayout()
        buff3_interval_row.addWidget(QLabel("최소(초):"))
        self.buff3_min_spin = QDoubleSpinBox()
        self.buff3_min_spin.setMinimum(0.1)
        self.buff3_min_spin.setMaximum(3600.0)
        self.buff3_min_spin.setSingleStep(0.1)
        self.buff3_min_spin.setDecimals(1)
        self.buff3_min_spin.setValue(5.0)
        buff3_interval_row.addWidget(self.buff3_min_spin)
        
        buff3_interval_row.addWidget(QLabel("최대(초):"))
        self.buff3_max_spin = QDoubleSpinBox()
        self.buff3_max_spin.setMinimum(0.1)
        self.buff3_max_spin.setMaximum(3600.0)
        self.buff3_max_spin.setSingleStep(0.1)
        self.buff3_max_spin.setDecimals(1)
        self.buff3_max_spin.setValue(10.0)
        buff3_interval_row.addWidget(self.buff3_max_spin)
        
        buff3_interval_row.addWidget(QLabel("횟수:"))
        self.buff3_count_spin = QSpinBox()
        self.buff3_count_spin.setMinimum(1)
        self.buff3_count_spin.setMaximum(100)
        self.buff3_count_spin.setValue(1)
        buff3_interval_row.addWidget(self.buff3_count_spin)
        buff3_layout.addLayout(buff3_interval_row)
        
        buff3_group.setLayout(buff3_layout)
        buff_layout.addWidget(buff3_group)
        
        buff_scroll.setWidget(buff_scroll_widget)
        
        buff_tab_layout = QVBoxLayout(buff_tab)
        buff_tab_layout.setContentsMargins(0, 0, 0, 0)
        buff_tab_layout.addWidget(buff_scroll)
        
        tabs.addTab(buff_tab, "버프 설정")
        
        # 탭 3: 유저 탐색 설정
        detection_tab = QWidget()
        detection_layout = QVBoxLayout()
        detection_layout.setSpacing(8)
        detection_layout.setContentsMargins(6, 6, 6, 6)
        
        # 텔레그램 설정
        telegram_group = QGroupBox("텔레그램 설정")
        telegram_layout = QVBoxLayout()
        telegram_layout.setSpacing(6)
        
        token_row = QHBoxLayout()
        token_row.addWidget(QLabel("봇 토큰:"))
        self.telegram_token_input = QLineEdit()
        self.telegram_token_input.setPlaceholderText("123456:ABC-DEF...")
        token_row.addWidget(self.telegram_token_input)
        telegram_layout.addLayout(token_row)
        
        chat_id_row = QHBoxLayout()
        chat_id_row.addWidget(QLabel("채팅 ID:"))
        self.telegram_chat_id_input = QLineEdit()
        self.telegram_chat_id_input.setPlaceholderText("123456789")
        chat_id_row.addWidget(self.telegram_chat_id_input)
        telegram_layout.addLayout(chat_id_row)
        
        nickname_row = QHBoxLayout()
        nickname_row.addWidget(QLabel("닉네임:"))
        self.user_nickname_input = QLineEdit()
        self.user_nickname_input.setPlaceholderText("홍길동")
        nickname_row.addWidget(self.user_nickname_input)
        telegram_layout.addLayout(nickname_row)
        
        telegram_group.setLayout(telegram_layout)
        detection_layout.addWidget(telegram_group)
        
        # 구역 설정
        region_group = QGroupBox("탐색 구역 설정")
        region_layout = QVBoxLayout()
        region_layout.setSpacing(6)
        
        coord_row1 = QHBoxLayout()
        coord_row1.addWidget(QLabel("X1:"))
        self.x1_spin = QSpinBox()
        self.x1_spin.setMinimum(0)
        self.x1_spin.setMaximum(9999)
        self.x1_spin.setValue(0)
        coord_row1.addWidget(self.x1_spin)
        
        coord_row1.addWidget(QLabel("Y1:"))
        self.y1_spin = QSpinBox()
        self.y1_spin.setMinimum(0)
        self.y1_spin.setMaximum(9999)
        self.y1_spin.setValue(0)
        coord_row1.addWidget(self.y1_spin)
        region_layout.addLayout(coord_row1)
        
        coord_row2 = QHBoxLayout()
        coord_row2.addWidget(QLabel("X2:"))
        self.x2_spin = QSpinBox()
        self.x2_spin.setMinimum(0)
        self.x2_spin.setMaximum(9999)
        self.x2_spin.setValue(100)
        coord_row2.addWidget(self.x2_spin)
        
        coord_row2.addWidget(QLabel("Y2:"))
        self.y2_spin = QSpinBox()
        self.y2_spin.setMinimum(0)
        self.y2_spin.setMaximum(9999)
        self.y2_spin.setValue(100)
        coord_row2.addWidget(self.y2_spin)
        region_layout.addLayout(coord_row2)
        
        # 구역 미리보기 버튼
        self.preview_btn = QPushButton("구역 미리보기 (3초)")
        self.preview_btn.setMaximumHeight(30)
        self.preview_btn.clicked.connect(self.show_region_preview)
        region_layout.addWidget(self.preview_btn)
        
        region_info = QLabel("※ 빨간색 테두리로 구역 표시")
        region_info.setStyleSheet("color: #666; font-size: 9pt;")
        region_layout.addWidget(region_info)
        
        region_group.setLayout(region_layout)
        detection_layout.addWidget(region_group)
        
        detection_tab.setLayout(detection_layout)
        tabs.addTab(detection_tab, "유저 탐색")
        
        # 탭 4: 핫키 설정
        hotkey_tab = QWidget()
        hotkey_layout = QVBoxLayout()
        hotkey_layout.setSpacing(8)
        hotkey_layout.setContentsMargins(6, 6, 6, 6)
        
        hotkey_info = QLabel("각 기능에 사용할 핫키를 설정하세요.\n클릭 후 원하는 키를 눌러주세요.")
        hotkey_info.setStyleSheet("color: #666; font-size: 9pt;")
        hotkey_info.setWordWrap(True)
        hotkey_layout.addWidget(hotkey_info)
        
        # 줍기 핫키
        pickup_hotkey_row = QHBoxLayout()
        pickup_hotkey_row.addWidget(QLabel("줍기:"))
        self.pickup_hotkey_input = HotkeyInputWidget()
        pickup_hotkey_row.addWidget(self.pickup_hotkey_input)
        clear_pickup_btn = QPushButton("초기화")
        clear_pickup_btn.setMaximumWidth(60)
        clear_pickup_btn.clicked.connect(self.pickup_hotkey_input.clear_hotkey)
        pickup_hotkey_row.addWidget(clear_pickup_btn)
        hotkey_layout.addLayout(pickup_hotkey_row)
        
        # 버프 핫키
        buff_hotkey_row = QHBoxLayout()
        buff_hotkey_row.addWidget(QLabel("버프:"))
        self.buff_hotkey_input = HotkeyInputWidget()
        buff_hotkey_row.addWidget(self.buff_hotkey_input)
        clear_buff_btn = QPushButton("초기화")
        clear_buff_btn.setMaximumWidth(60)
        clear_buff_btn.clicked.connect(self.buff_hotkey_input.clear_hotkey)
        buff_hotkey_row.addWidget(clear_buff_btn)
        hotkey_layout.addLayout(buff_hotkey_row)
        
        # 감지 핫키
        monitor_hotkey_row = QHBoxLayout()
        monitor_hotkey_row.addWidget(QLabel("감지:"))
        self.monitor_hotkey_input = HotkeyInputWidget()
        monitor_hotkey_row.addWidget(self.monitor_hotkey_input)
        clear_monitor_btn = QPushButton("초기화")
        clear_monitor_btn.setMaximumWidth(60)
        clear_monitor_btn.clicked.connect(self.monitor_hotkey_input.clear_hotkey)
        monitor_hotkey_row.addWidget(clear_monitor_btn)
        hotkey_layout.addLayout(monitor_hotkey_row)
        
        # 유저탐색 핫키
        detector_hotkey_row = QHBoxLayout()
        detector_hotkey_row.addWidget(QLabel("유저탐색:"))
        self.detector_hotkey_input = HotkeyInputWidget()
        detector_hotkey_row.addWidget(self.detector_hotkey_input)
        clear_detector_btn = QPushButton("초기화")
        clear_detector_btn.setMaximumWidth(60)
        clear_detector_btn.clicked.connect(self.detector_hotkey_input.clear_hotkey)
        detector_hotkey_row.addWidget(clear_detector_btn)
        hotkey_layout.addLayout(detector_hotkey_row)
        
        hotkey_layout.addStretch()
        
        hotkey_tab.setLayout(hotkey_layout)
        tabs.addTab(hotkey_tab, "핫키 설정")
        
        layout.addWidget(tabs)
        
        # 버튼
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        save_btn = QPushButton("저장")
        save_btn.setMinimumHeight(32)
        save_btn.clicked.connect(self.validate_and_accept)
        cancel_btn = QPushButton("취소")
        cancel_btn.setMinimumHeight(32)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def validate_and_accept(self):
        """설정을 검증하고 저장합니다."""
        errors = []
        
        # 줍기 설정 검증
        if not self.key_input.text().strip():
            errors.append("줍기 키가 비어있습니다.")
        
        if self.min_spin.value() > self.max_spin.value():
            errors.append("줍기: 최소 간격이 최대 간격보다 큽니다.")
        
        # 버프1 설정 검증
        if self.buff1_key_input.text().strip():
            if self.buff1_min_spin.value() > self.buff1_max_spin.value():
                errors.append("버프1: 최소 간격이 최대 간격보다 큽니다.")
        
        # 버프2 설정 검증
        if self.buff2_key_input.text().strip():
            if self.buff2_min_spin.value() > self.buff2_max_spin.value():
                errors.append("버프2: 최소 간격이 최대 간격보다 큽니다.")
        
        # 버프3 설정 검증
        if self.buff3_key_input.text().strip():
            if self.buff3_min_spin.value() > self.buff3_max_spin.value():
                errors.append("버프3: 최소 간격이 최대 간격보다 큽니다.")
        
        # 구역 설정 검증
        if self.x1_spin.value() >= self.x2_spin.value():
            errors.append("탐색 구역: X1이 X2보다 크거나 같습니다.")
        
        if self.y1_spin.value() >= self.y2_spin.value():
            errors.append("탐색 구역: Y1이 Y2보다 크거나 같습니다.")
        
        # 핫키 중복 검증
        hotkeys = {}
        if self.pickup_hotkey_input.get_hotkey():
            hotkeys['줍기'] = self.pickup_hotkey_input.get_hotkey()
        if self.buff_hotkey_input.get_hotkey():
            if self.buff_hotkey_input.get_hotkey() in hotkeys.values():
                errors.append("핫키 중복: 버프 핫키가 다른 기능과 중복됩니다.")
            hotkeys['버프'] = self.buff_hotkey_input.get_hotkey()
        if self.monitor_hotkey_input.get_hotkey():
            if self.monitor_hotkey_input.get_hotkey() in hotkeys.values():
                errors.append("핫키 중복: 감지 핫키가 다른 기능과 중복됩니다.")
            hotkeys['감지'] = self.monitor_hotkey_input.get_hotkey()
        if self.detector_hotkey_input.get_hotkey():
            if self.detector_hotkey_input.get_hotkey() in hotkeys.values():
                errors.append("핫키 중복: 유저탐색 핫키가 다른 기능과 중복됩니다.")
        
        # 오류가 있으면 경고 메시지 표시
        if errors:
            QMessageBox.warning(
                self,
                "설정 오류",
                "다음 오류를 수정해주세요:\n\n" + "\n".join(f"• {error}" for error in errors)
            )
            return
        
        # 검증 통과 시 저장
        self.accept()
    
    def refresh_window_list(self):
        """창 목록을 새로고침합니다."""
        for i in reversed(range(self.window_list_layout.count())):
            widget = self.window_list_layout.itemAt(i).widget()
            if widget:
                self.window_button_group.removeButton(widget)
                widget.deleteLater()
        
        windows = WindowMonitor.get_all_windows()
        
        if not windows:
            label = QLabel("실행 중인 창이 없습니다.")
            self.window_list_layout.addWidget(label)
            return
        
        for hwnd, title in windows:
            radio = QRadioButton(f"{title} (HWND: {hwnd})")
            radio.setProperty("hwnd", hwnd)
            radio.setProperty("title", title)
            self.window_button_group.addButton(radio)
            self.window_list_layout.addWidget(radio)
            
            if self.current_config.get("selected_window"):
                if self.current_config["selected_window"]["hwnd"] == hwnd:
                    radio.setChecked(True)
    
    def load_current_settings(self):
        """현재 설정을 UI에 로드합니다."""
        # 줍기 설정
        if "key_to_press" in self.current_config:
            self.key_input.setText(self.current_config["key_to_press"])
        
        if "min_interval" in self.current_config:
            self.min_spin.setValue(self.current_config["min_interval"])
        
        if "max_interval" in self.current_config:
            self.max_spin.setValue(self.current_config["max_interval"])
        
        if "press_count" in self.current_config:
            self.count_spin.setValue(self.current_config["press_count"])
        
        # 버프1 설정
        if "buff1_key" in self.current_config:
            self.buff1_key_input.setText(self.current_config["buff1_key"])
        if "buff1_min_interval" in self.current_config:
            self.buff1_min_spin.setValue(self.current_config["buff1_min_interval"])
        if "buff1_max_interval" in self.current_config:
            self.buff1_max_spin.setValue(self.current_config["buff1_max_interval"])
        if "buff1_press_count" in self.current_config:
            self.buff1_count_spin.setValue(self.current_config["buff1_press_count"])
        
        # 버프2 설정
        if "buff2_key" in self.current_config:
            self.buff2_key_input.setText(self.current_config["buff2_key"])
        if "buff2_min_interval" in self.current_config:
            self.buff2_min_spin.setValue(self.current_config["buff2_min_interval"])
        if "buff2_max_interval" in self.current_config:
            self.buff2_max_spin.setValue(self.current_config["buff2_max_interval"])
        if "buff2_press_count" in self.current_config:
            self.buff2_count_spin.setValue(self.current_config["buff2_press_count"])
        
        # 버프3 설정
        if "buff3_key" in self.current_config:
            self.buff3_key_input.setText(self.current_config["buff3_key"])
        if "buff3_min_interval" in self.current_config:
            self.buff3_min_spin.setValue(self.current_config["buff3_min_interval"])
        if "buff3_max_interval" in self.current_config:
            self.buff3_max_spin.setValue(self.current_config["buff3_max_interval"])
        if "buff3_press_count" in self.current_config:
            self.buff3_count_spin.setValue(self.current_config["buff3_press_count"])
        
        # 텔레그램 설정
        if "telegram_token" in self.current_config:
            self.telegram_token_input.setText(self.current_config["telegram_token"])
        
        if "telegram_chat_id" in self.current_config:
            self.telegram_chat_id_input.setText(self.current_config["telegram_chat_id"])
        
        if "user_nickname" in self.current_config:
            self.user_nickname_input.setText(self.current_config["user_nickname"])
        
        # 구역 설정
        if "detection_region" in self.current_config:
            region = self.current_config["detection_region"]
            self.x1_spin.setValue(region[0])
            self.y1_spin.setValue(region[1])
            self.x2_spin.setValue(region[2])
            self.y2_spin.setValue(region[3])
        
        # 핫키 설정
        if "hotkey_pickup" in self.current_config:
            self.pickup_hotkey_input.set_hotkey(self.current_config["hotkey_pickup"])
        
        if "hotkey_buff" in self.current_config:
            self.buff_hotkey_input.set_hotkey(self.current_config["hotkey_buff"])
        
        if "hotkey_monitor" in self.current_config:
            self.monitor_hotkey_input.set_hotkey(self.current_config["hotkey_monitor"])
        
        if "hotkey_detector" in self.current_config:
            self.detector_hotkey_input.set_hotkey(self.current_config["hotkey_detector"])
    
    def show_region_preview(self):
        """구역 미리보기를 표시합니다."""
        region = (
            self.x1_spin.value(),
            self.y1_spin.value(),
            self.x2_spin.value(),
            self.y2_spin.value()
        )
        
        # 기존 미리보기 창 제거
        if self.preview_window:
            self.preview_window.close()
        
        # 새 미리보기 창 생성
        self.preview_window = RegionPreviewWindow(region)
        self.preview_window.show_preview()
        
        # 3초 후 자동으로 닫기
        if self.preview_timer:
            self.preview_timer.stop()
        
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.hide_region_preview)
        self.preview_timer.start(3000)
    
    def hide_region_preview(self):
        """구역 미리보기를 숨깁니다."""
        if self.preview_window:
            self.preview_window.hide_preview()
            self.preview_window.close()
            self.preview_window = None
    
    def get_settings(self):
        """현재 설정을 반환합니다."""
        selected_window = None
        for button in self.window_button_group.buttons():
            if button.isChecked():
                selected_window = {
                    "hwnd": button.property("hwnd"),
                    "title": button.property("title")
                }
                break
        
        return {
            "selected_window": selected_window,
            "key_to_press": self.key_input.text() or "space",
            "min_interval": self.min_spin.value(),
            "max_interval": self.max_spin.value(),
            "press_count": self.count_spin.value(),
            "buff1_key": self.buff1_key_input.text() or "1",
            "buff1_min_interval": self.buff1_min_spin.value(),
            "buff1_max_interval": self.buff1_max_spin.value(),
            "buff1_press_count": self.buff1_count_spin.value(),
            "buff2_key": self.buff2_key_input.text() or "2",
            "buff2_min_interval": self.buff2_min_spin.value(),
            "buff2_max_interval": self.buff2_max_spin.value(),
            "buff2_press_count": self.buff2_count_spin.value(),
            "buff3_key": self.buff3_key_input.text() or "3",
            "buff3_min_interval": self.buff3_min_spin.value(),
            "buff3_max_interval": self.buff3_max_spin.value(),
            "buff3_press_count": self.buff3_count_spin.value(),
            "telegram_token": self.telegram_token_input.text(),
            "telegram_chat_id": self.telegram_chat_id_input.text(),
            "user_nickname": self.user_nickname_input.text() or "유저",
            "detection_region": (
                self.x1_spin.value(),
                self.y1_spin.value(),
                self.x2_spin.value(),
                self.y2_spin.value()
            ),
            "hotkey_pickup": self.pickup_hotkey_input.get_hotkey(),
            "hotkey_buff": self.buff_hotkey_input.get_hotkey(),
            "hotkey_monitor": self.monitor_hotkey_input.get_hotkey(),
            "hotkey_detector": self.detector_hotkey_input.get_hotkey()
        }
    
    def closeEvent(self, event):
        """다이얼로그 닫을 때 미리보기 창도 닫기"""
        self.hide_region_preview()
        event.accept()