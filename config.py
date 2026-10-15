"""
XInput to DualShock 4 Yapılandırma Dosyası
"""

import json
import os
from dataclasses import asdict, dataclass, field
from typing import List

CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_GAMES = [
    "GoW.exe",
    "GodOfWar.exe",
    "SpiderMan.exe",
    "MilesMorales.exe",
    "HorizonZeroDawn.exe",
    "HorizonForbiddenWest.exe",
    "tlou-i.exe",
    "TheLastOfUs.exe",
    "Uncharted.exe",
    "Returnal.exe",
    "GhostOfTsushima.exe",
    "DeathStranding.exe",
    "RatchetAndClank.exe",
    "DetroitBecomeHuman.exe"
]

@dataclass
class Config:
    # 1. Temel Köprü Ayarları
    POLLING_RATE_HZ: float = 250.0
    CONTROLLER_INDEX: int = 0
    THUMB_DEADZONE: float = 0.06
    TRIGGER_DIGITAL_THRESHOLD: float = 0.12

    # Y ekseni yönü (DS4 formatında Yukarı = İleri için True)
    INVERT_LEFT_Y: bool = True
    INVERT_RIGHT_Y: bool = True

    # Guide (Ortadaki PS / Logo) butonu desteği (XInputGetStateEx)
    ENABLE_GUIDE_BUTTON: bool = True

    # 2. Geliştirme #1: Titreşim (Force Feedback / Rumble)
    ENABLE_RUMBLE: bool = True
    RUMBLE_STRENGTH: float = 1.0  # 0.0 - 2.0 arası titreşim çarpanı

    # 3. Geliştirme #2: Touchpad Simülasyonu
    # "both" -> Back hem Share hem Touchpad Click
    # "touchpad" -> Back sadece Touchpad Click
    # "share" -> Back sadece Share
    BACK_MAPPING_MODE: str = "both"

    # 4. Geliştirme #3 & #4: Sistem Tepsisi ve Akıllı Oyun Algılama
    START_IN_TRAY: bool = False
    AUTO_GAME_DETECT: bool = False
    DETECTED_GAMES: List[str] = field(default_factory=lambda: list(DEFAULT_GAMES))

    # 5. Geliştirme #5: Dahili HidHide Yönetimi
    AUTO_CLOAK_PHYSICAL: bool = False

    # Dil Seçimi: "en" (İngilizce) veya "tr" (Türkçe)
    LANGUAGE: str = "en"

    # Debug ve canlı loglama
    DEBUG: bool = False

    def save_to_file(self, filepath: str = CONFIG_FILE_PATH):
        """Ayarları JSON dosyasına yazar."""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[!] Ayarlar kaydedilemedi: {e}")

    @classmethod
    def load_from_file(cls, filepath: str = CONFIG_FILE_PATH) -> "Config":
        """JSON dosyasından ayarları okur, yoksa varsayılanları döner."""
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
            except Exception as e:
                print(f"[!] Ayar dosyası okunamadı, varsayılanlar kullanılıyor: {e}")
        return cls()
