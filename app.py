"""
XInput to DualShock 4 Controller Bridge
=======================================
Fiziksel XInput (Xbox uyumlu) gamepad girişlerini okuyarak sanal bir Sony DualShock 4 (DS4)
kontrolcüsüne aktarır. Böylece PC oyunlarında (örn. God of War, Spider-Man) kol PlayStation
kontrolcüsü olarak tanınır ve ekranda PS tuş simgeleri (Kare, Üçgen, Daire, Çarpı) görüntülenir.

Geliştirmeler:
1. İki Yönlü Titreşim (Force Feedback / Rumble)
2. Touchpad ve Share Gelişmiş Tuş Simülasyonu
3. Sistem Tepsisi (System Tray) ve Mini Bildirim Arayüzü
4. Akıllı Oyun Algılama (Auto-Launch / Auto-Active)
5. Dahili HidHide Yönetimi (Cloaking / Whitelist)
6. Görsel Canlı Kalibrasyon ve Kontrol Paneli (Tkinter)
7. Tek Bağımsız Dağıtım Desteği (.EXE)
"""

import argparse
import ctypes
import os
import signal
import sys
import threading
import time

from calibration_gui import CalibrationGUI
from config import Config
from ds4_mapper import DS4Mapper
from game_detector import GameDetector
from hidhide_manager import HidHideManager
from tray_manager import TrayManager
from xinput_reader import GamepadState, XInputReader


# Windows Yüksek Hassasiyetli Zamanlayıcı (1 ms timer resolution)
winmm = None
try:
    winmm = ctypes.windll.winmm
except Exception:
    winmm = None


def set_high_resolution_timer(enable: bool):
    """Windows varsayılan 15.6ms zamanlayıcı çözünürlüğünü 1ms hassasiyete çeker."""
    if winmm:
        try:
            if enable:
                winmm.timeBeginPeriod(1)
            else:
                winmm.timeEndPeriod(1)
        except Exception:
            pass


def format_state_summary(state: GamepadState) -> str:
    """Canlı basılı tuşların ve analog eksenlerin özet metnini üretir."""
    pressed = []
    if state.btn_a: pressed.append("A(X)")
    if state.btn_b: pressed.append("B(O)")
    if state.btn_x: pressed.append("X([])")
    if state.btn_y: pressed.append("Y(/\\)")
    if state.btn_lb: pressed.append("LB(L1)")
    if state.btn_rb: pressed.append("RB(R1)")
    if state.btn_l3: pressed.append("L3")
    if state.btn_r3: pressed.append("R3")
    if state.btn_start: pressed.append("Start(Options)")
    if state.btn_back: pressed.append("Back(Share/Touchpad)")
    if state.btn_guide: pressed.append("Guide(PS)")
    if state.dpad_up: pressed.append("DPAD_UP")
    if state.dpad_down: pressed.append("DPAD_DOWN")
    if state.dpad_left: pressed.append("DPAD_LEFT")
    if state.dpad_right: pressed.append("DPAD_RIGHT")

    triggers = f"LT:{state.trigger_left:.2f} RT:{state.trigger_right:.2f}"
    sticks = f"L:({state.thumb_lx:+.2f},{state.thumb_ly:+.2f}) R:({state.thumb_rx:+.2f},{state.thumb_ry:+.2f})"
    keys = " ".join(pressed) if pressed else "(Tuş basılmadı)"
    return f"{triggers} | {sticks} | {keys}"


class BridgeController:
    """
    Köprü uygulamasının tüm yaşam döngüsünü (Girdi okuma, DS4 aktarma,
    titreşim, sistem tepsisi, oyun izleme ve kalibrasyon) yönetir.
    """

    def __init__(self, config: Config, with_tray: bool = True):
        self.config = config
        self.with_tray = with_tray

        self.is_running = True
        self.is_paused = False

        self.reader = XInputReader(
            controller_index=self.config.CONTROLLER_INDEX,
            deadzone=self.config.THUMB_DEADZONE,
            enable_guide=self.config.ENABLE_GUIDE_BUTTON
        )

        self.mapper: Optional[DS4Mapper] = None
        self.tray: Optional[TrayManager] = None
        self.detector: Optional[GameDetector] = None
        self.hidhide = HidHideManager()

    def _on_game_vibration(self, large_motor: int, small_motor: int):
        """Oyundan gelen titreşimi fiziksel kola aktarır."""
        if self.config.ENABLE_RUMBLE and not self.is_paused:
            self.reader.set_vibration(large_motor, small_motor, self.config.RUMBLE_STRENGTH)

    def _on_game_started(self, game_name: str):
        print(f"\n[+] Hedef Oyun Başlatıldı: {game_name}! Köprü etkinleştiriliyor...")
        self.is_paused = False
        if self.tray:
            self.tray.set_active_state(True)

    def _on_game_stopped(self, game_name: str):
        print(f"\n[-] Hedef Oyun Kapandı: {game_name}. Köprü bekleme moduna alınıyor.")
        self.is_paused = True
        if self.mapper:
            self.mapper.reset()
        if self.tray:
            self.tray.set_active_state(False)

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        status_text = "DURAKLATILDI" if self.is_paused else "AKTIF"
        print(f"\n[*] Köprü durumu değiştirildi: {status_text}")
        if self.is_paused and self.mapper:
            self.mapper.reset()
        if self.tray:
            self.tray.set_active_state(not self.is_paused)

    def open_calibration(self):
        """Görsel kalibrasyon arayüzünü açar."""
        def launch():
            gui = CalibrationGUI(self.config, self.reader)
            gui.show()
        threading.Thread(target=launch, daemon=True).start()

    def stop(self):
        self.is_running = False

    def run(self):
        # 1. Sanal DualShock 4 Başlat
        print("\n[+] Sanal DualShock 4 kontrolcüsü oluşturuluyor...")
        try:
            self.mapper = DS4Mapper(config=self.config, on_rumble=self._on_game_vibration)
            print("[OK] Sanal DualShock 4 başarıyla sisteme bağlandı!")
        except Exception as e:
            print(f"\n[HATA] Sanal kontrolcü başlatılamadı: {e}")
            print("Lütfen ViGEmBus sürücüsünün kurulu olduğundan emin olun.")
            sys.exit(1)

        # 2. Sistem Tepsisini Başlat
        if self.with_tray:
            try:
                self.tray = TrayManager(
                    config=self.config,
                    on_toggle_bridge=self.toggle_pause,
                    on_open_calibration=self.open_calibration,
                    on_exit=self.stop
                )
                self.tray.start()
                print("[OK] Sistem Tepsisi (Tray) simgesi aktif edildi.")
            except Exception as e:
                print(f"[!] Sistem tepsisi başlatılamadı: {e}")

        # 3. Akıllı Oyun Algılayıcıyı Başlat
        if self.config.AUTO_GAME_DETECT:
            self.detector = GameDetector(
                target_games=self.config.DETECTED_GAMES,
                on_game_started=self._on_game_started,
                on_game_stopped=self._on_game_stopped
            )
            self.detector.start()
            print("[OK] Akıllı Oyun Algılama aktif. Oyun başlatıldığında otomatik devreye girecek.")
            # Başlangıçta oyun yoksa duraklat
            if not self.detector.is_game_running():
                print("[*] Hedef oyun çalışmıyor, köprü bekleme modunda...")
                self.is_paused = True
                if self.tray:
                    self.tray.set_active_state(False)

        # 4. Windows Multimedya Zamanlayıcı
        set_high_resolution_timer(True)

        target_interval = 1.0 / self.config.POLLING_RATE_HZ
        was_connected = False
        loop_count = 0
        fps_start = time.perf_counter()
        last_ui_update = 0.0

        print("\n[*] Köprü ÇALIŞIYOR! Girişler anlık sanal DualShock 4'e aktarılıyor.")
        print("[*] Konsolu kapatmak için Ctrl+C tuşlarına basabilirsiniz.\n")

        try:
            while self.is_running:
                loop_start = time.perf_counter()

                # Duraklatılmışsa sadece düşük frekansta bekle (CPU tasarrufu)
                if self.is_paused:
                    time.sleep(0.05)
                    continue

                # 1. Fiziksel Kolu Oku
                state = self.reader.read()

                # 2. Bağlantı Durumu
                if state.connected != was_connected:
                    was_connected = state.connected
                    if state.connected:
                        print(f"\n[+] Fiziksel kol #{self.config.CONTROLLER_INDEX} bağlandı ve aktarıma başlandı.")
                    else:
                        print(f"\n[-] Fiziksel kol #{self.config.CONTROLLER_INDEX} bağlantısı koptu. Bekleniyor...")

                # 3. Sanal DS4'e Aktar
                self.mapper.update(state)

                # 4. Canlı Konsol Girdi Gösterimi
                now = time.perf_counter()
                if state.connected and (now - last_ui_update >= 0.05):
                    has_input = (
                        state.btn_a or state.btn_b or state.btn_x or state.btn_y or
                        state.btn_lb or state.btn_rb or state.btn_l3 or state.btn_r3 or
                        state.btn_start or state.btn_back or state.btn_guide or
                        state.dpad_up or state.dpad_down or state.dpad_left or state.dpad_right or
                        state.trigger_left > 0.05 or state.trigger_right > 0.05 or
                        abs(state.thumb_lx) > 0.15 or abs(state.thumb_ly) > 0.15 or
                        abs(state.thumb_rx) > 0.15 or abs(state.thumb_ry) > 0.15
                    )
                    if has_input or self.config.DEBUG:
                        summary = format_state_summary(state)
                        sys.stdout.write(f"\r[*] Girdi: {summary.ljust(95)}")
                        sys.stdout.flush()
                        last_ui_update = now

                # 5. Yüksek Hassasiyetli 250 Hz Zamanlama
                elapsed = time.perf_counter() - loop_start
                sleep_time = target_interval - elapsed
                if sleep_time > 0.0015:
                    time.sleep(sleep_time - 0.0008)
                while (time.perf_counter() - loop_start) < target_interval:
                    pass

        except Exception as e:
            print(f"\n[HATA] Çalışma hatası: {e}")
        finally:
            self._cleanup()

    def _cleanup(self):
        print("\n\n[*] Temiz kapanış yapılıyor...")
        if self.detector:
            self.detector.stop()
        if self.tray:
            self.tray.stop()
        try:
            self.reader.stop_vibration()
        except Exception:
            pass
        if self.mapper:
            try:
                self.mapper.close()
                print("[OK] Sanal DualShock 4 kaldırıldı.")
            except Exception:
                pass
        set_high_resolution_timer(False)
        print("[OK] Sistem zamanlayıcısı normale döndürüldü. Güle güle!")


def main():
    os.system("")  # ANSI desteği

    parser = argparse.ArgumentParser(description="XInput -> DualShock 4 Gamepad Köprüsü")
    parser.add_argument("-i", "--index", type=int, default=None, help="Okunacak fiziksel kol indeksi (0-3).")
    parser.add_argument("-r", "--rate", type=float, default=250.0, help="Frekans Hz (varsayılan: 250)")
    parser.add_argument("-d", "--deadzone", type=float, default=None, help="Ölü bölge (deadzone) eşiği (0.0 - 1.0)")
    parser.add_argument("--test", action="store_true", help="Canlı girdi testi yapar.")
    parser.add_argument("--debug", action="store_true", help="Ayrıntılı debug logları gösterir.")
    parser.add_argument("--gui", action="store_true", help="Görsel kalibrasyon ve test penceresini açar.")
    parser.add_argument("--no-tray", action="store_true", help="Sistem tepsisi simgesini devre dışı bırakır.")
    parser.add_argument("--auto-detect", action="store_true", help="Akıllı oyun algılayıcıyı zorunlu açar.")
    parser.add_argument("--cloak", action="store_true", help="HidHide ile fiziksel kolu gizlemeyi dener.")

    args = parser.parse_args()

    # Ayarları dosyadan oku
    config = Config.load_from_file()

    # CLI argümanları ile ez
    if args.index is not None:
        config.CONTROLLER_INDEX = args.index
    else:
        detected = XInputReader.find_first_connected_index()
        config.CONTROLLER_INDEX = detected if detected is not None else 0

    if args.rate:
        config.POLLING_RATE_HZ = args.rate
    if args.deadzone is not None:
        config.THUMB_DEADZONE = args.deadzone
    if args.debug:
        config.DEBUG = True
    if args.auto_detect:
        config.AUTO_GAME_DETECT = True

    # HidHide Gizleme İsteği
    if args.cloak:
        hid = HidHideManager()
        if hid.is_installed():
            print("[*] HidHide gizleme aktifleştiriliyor...")
            hid.set_cloaking(True)

    # Doğrudan GUI açma modu
    if args.gui:
        gui = CalibrationGUI(config)
        gui.show()
        return

    # Canlı Girdi Test Modu
    if args.test:
        reader = XInputReader(controller_index=config.CONTROLLER_INDEX, deadzone=config.THUMB_DEADZONE)
        set_high_resolution_timer(True)
        print("\n[TEST MODU AKTIF] Fiziksel koldan gelen veriler okunuyor. Çıkış için Ctrl+C basınız.\n")
        try:
            while True:
                s = reader.read()
                sys.stdout.write(f"\r{format_state_summary(s)}".ljust(110))
                sys.stdout.flush()
                time.sleep(0.01)
        except KeyboardInterrupt:
            print("\nTest sonlandırıldı.")
        finally:
            set_high_resolution_timer(False)
        return

    # Banner Bilgisi
    print("=" * 68)
    print("      XInput -> Sony DualShock 4 Controller Bridge")
    print("=" * 68)
    print(f" Hedef Frekans       : {config.POLLING_RATE_HZ:.0f} Hz (~{1000.0/config.POLLING_RATE_HZ:.1f} ms döngü süresi)")
    print(f" Fiziksel Kol İndeksi: #{config.CONTROLLER_INDEX}")
    print(f" Deadzone            : %{config.THUMB_DEADZONE * 100:.1f}")
    print(f" Sol Analog Y Eksen  : {'Tersine Çevrildi (Yukarı = İleri)' if config.INVERT_LEFT_Y else 'Normal'}")
    print(f" Sağ Analog Y Eksen  : {'Tersine Çevrildi (Kamera Düzeltildi)' if config.INVERT_RIGHT_Y else 'Normal'}")
    print(f" İki Yönlü Titreşim  : {'Aktif (Force Feedback Çarpanı: ' + str(config.RUMBLE_STRENGTH) + 'x)' if config.ENABLE_RUMBLE else 'Kapalı'}")
    print(f" Back Tuşu Modu      : {config.BACK_MAPPING_MODE} (Touchpad / Share)")
    print(f" Akıllı Oyun Algılama: {'Aktif (Hedef oyun açıldığında başlar)' if config.AUTO_GAME_DETECT else 'Devre Dışı (Sürekli Aktif)'}")
    print(f" Sistem Tepsisi      : {'Açık (Görev Çubuğunda Simgesi Var)' if not args.no_tray else 'Kapalı'}")
    print("=" * 68)

    controller = BridgeController(config=config, with_tray=not args.no_tray)

    def sig_handler(sig, frame):
        controller.stop()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    controller.run()


if __name__ == "__main__":
    main()
