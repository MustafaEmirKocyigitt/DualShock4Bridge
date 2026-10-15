"""
DualShock 4 Kontrol Merkezi - Dil ve Çeviri Modülü (i18n)
=========================================================
Türkçe (TR) ve İngilizce (EN) dil desteği sağlar.
"""

TRANSLATIONS = {
    "tr": {
        # Pencere & Başlık
        "app_title": "DualShock 4 Kontrol Merkezi",
        "tray_title": "DualShock 4 Köprüsü",
        "tray_restore": "Kontrol Merkezini Aç",
        "tray_pause": "Köprüyü Duraklat",
        "tray_start": "Köprüyü Başlat",
        "tray_exit": "Çıkış",

        # Üst Durum Çubuğu
        "controller_connected": "● Fiziksel Kol Bağlı (Xbox Controller #{idx})",
        "controller_waiting": "● Kol Bağlantısı Bekleniyor...",
        "bridge_active": "● PlayStation Aktarımı Aktif (250 Hz)",
        "bridge_paused": "● Köprü Duraklatıldı",
        "bridge_initializing": "● Köprü hazırlanıyor...",
        "btn_pause": "Köprüyü Duraklat",
        "btn_start": "Köprüyü Başlat",

        # Sekmeler
        "tab_test": "Genel Bakış & Canlı Test",
        "tab_settings": "Yapılandırma & Ayarlar",

        # Canlı Test Sekmesi
        "sec_sticks": "Analog Çubuklar",
        "stick_left": "Sol Analog (Hareket)",
        "stick_right": "Sağ Analog (Kamera)",
        "sec_buttons": "Tuş ve Tetik Girişleri",
        "no_button_pressed": "(Şu anda bir tuşa basılmıyor)",
        "btn_test_rumble": "Titreşimi Test Et (0.4 sn)",

        # Ayarlar Sekmesi
        "sec_deadzone_title": "Ölü Bölge (Deadzone) Eşiği",
        "sec_deadzone_desc": "Analog çubukların merkezdeki hassasiyet boşluğudur. Çubukları bıraktığınızda karakterin veya kameranın kendiliğinden kaymasını (drift) engeller. (Önerilen: %6.0)",
        "sec_rumble_title": "Titreşim (Force Feedback) Gücü",
        "sec_rumble_desc": "God of War gibi oyunlarda Kratos'un balta fırlatması, darbeler ve büyü efektlerinin kol motorlarına iletilme şiddetidir. (Önerilen: %100)",
        "sec_back_title": "Back (Görünüm) Tuşu Davranışı",
        "sec_back_desc": "PlayStation oyunlarında haritayı ve menüyü açmak için DualShock 4 dokunmatik yüzeyine (Touchpad) basılır. Koldaki Back tuşunun işlevini belirler. (Önerilen: both - Touchpad + Share)",
        "back_desc_both": "(both: Haritayı doğrudan koldan açar)",
        "sec_auto_title": "Otomasyon ve Cihaz Gizleme",
        "chk_auto_game": "Akıllı Oyun Algılama (Önerilen: Açık)\nDesteklenen bir PlayStation oyunu açıldığında köprüyü otomatik başlatır, oyundan çıkıldığında uyku moduna alır.",
        "chk_hidhide": "HidHide ile Fiziksel Xbox Kolunu Gizle (Önerilen: Açık)\nFiziksel kolu oyunlardan gizleyerek çift basmayı ve Xbox tuş simgelerinin çakışmasını engeller.",
        
        # Butonlar & Mesajlar
        "btn_load_recommended": "Önerilen Ayarları Yükle",
        "btn_save_settings": "Ayarları Kaydet",
        "saved_success": "Kaydedildi ✓",
        "recommended_title": "Önerilen Ayarlar",
        "recommended_msg": "Tüm ayarlar önerilen fabrika ayarlarına getirildi. Kaydetmek için 'Ayarları Kaydet' butonuna basabilirsiniz.",
        "lang_switch_btn": "Language: English",
    },
    "en": {
        # Window & Title
        "app_title": "DualShock 4 Control Center",
        "tray_title": "DualShock 4 Bridge",
        "tray_restore": "Open Control Center",
        "tray_pause": "Pause Bridge",
        "tray_start": "Resume Bridge",
        "tray_exit": "Exit",

        # Header Status Bar
        "controller_connected": "● Physical Controller Connected (Xbox Controller #{idx})",
        "controller_waiting": "● Waiting for Controller Connection...",
        "bridge_active": "● PlayStation Emulation Active (250 Hz)",
        "bridge_paused": "● Bridge Paused",
        "bridge_initializing": "● Bridge initializing...",
        "btn_pause": "Pause Bridge",
        "btn_start": "Resume Bridge",

        # Tabs
        "tab_test": "Overview & Live Test",
        "tab_settings": "Configuration & Settings",

        # Live Test Tab
        "sec_sticks": "Analog Thumbsticks",
        "stick_left": "Left Stick (Movement)",
        "stick_right": "Right Stick (Camera)",
        "sec_buttons": "Button & Trigger Inputs",
        "no_button_pressed": "(No button currently pressed)",
        "btn_test_rumble": "Test Vibration (0.4s)",

        # Settings Tab
        "sec_deadzone_title": "Thumbstick Deadzone Threshold",
        "sec_deadzone_desc": "Center deadzone filter for analog sticks. Prevents in-game character drift or unintended camera movements when sticks are idle. (Recommended: 6.0%)",
        "sec_rumble_title": "Vibration (Force Feedback) Strength",
        "sec_rumble_desc": "Intensity of weapon strikes, impact forces, and magic rumble effects relayed to physical motors in games like God of War. (Recommended: 100%)",
        "sec_back_title": "Back (View) Button Behavior",
        "sec_back_desc": "PlayStation games require a DualShock 4 Touchpad click to open the map and journal. Configures the Xbox Back button mapping. (Recommended: both - Touchpad + Share)",
        "back_desc_both": "(both: Instantly triggers in-game map)",
        "sec_auto_title": "Automation & Device Cloaking",
        "chk_auto_game": "Smart Game Detection (Recommended: Enabled)\nAutomatically starts the bridge when a supported PlayStation title launches; sleeps when closed to save CPU & battery.",
        "chk_hidhide": "Hide Physical Xbox Controller with HidHide (Recommended: Enabled)\nCloaks the physical device from games to prevent double-input and conflicting Xbox button glyphs.",

        # Buttons & Messages
        "btn_load_recommended": "Load Recommended Defaults",
        "btn_save_settings": "Save Settings",
        "saved_success": "Saved ✓",
        "recommended_title": "Recommended Settings",
        "recommended_msg": "All settings have been restored to recommended factory defaults. Click 'Save Settings' to apply.",
        "lang_switch_btn": "Dil: Türkçe",
    }
}


def get_text(key: str, lang: str = "en", **kwargs) -> str:
    """Belirtilen anahtara ve dile göre çevrilmiş metni döner."""
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    text = lang_dict.get(key, TRANSLATIONS["en"].get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
