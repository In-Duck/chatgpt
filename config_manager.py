import json
import os
from typing import Optional, Dict, Any


class ConfigManager:
    """설정 저장 및 로드를 관리하는 클래스"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.default_config = {
            "selected_window": None,
            "key_to_press": "space",
            "min_interval": 5.0,
            "max_interval": 10.0,
            "press_count": 1,
            "telegram_token": "",
            "telegram_chat_id": "",
            "user_nickname": "유저",
            "detection_region": (0, 0, 100, 100)
        }
    
    def load_config(self) -> Dict[str, Any]:
        """설정 파일에서 설정을 로드합니다."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 기본값으로 누락된 키 채우기
                    for key, value in self.default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                print(f"설정 로드 실패: {e}")
                return self.default_config.copy()
        return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """설정을 파일에 저장합니다."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"설정 저장 실패: {e}")
            return False
    
    def update_config(self, key: str, value: Any) -> bool:
        """특정 설정 값을 업데이트합니다."""
        config = self.load_config()
        config[key] = value
        return self.save_config(config)