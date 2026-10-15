"""
DualShock 4 Kontrol Merkezi - Profesyonel Yönetim Paneli
========================================================
Kullanıcı arayüzü ve anti-pattern kurallarına %100 uyumlu:
- İç içe kart/kutu yok.
- Gradient, parlama veya katmanlı gölge yok (en fazla 1px sakin kenarlık).
- Durum göstergesi renkli nokta + metinle sunulur.
- Monospace font sadece teknik değerlerde; sayısal metriklerde sans + tabular-nums.
- Her kartta/bölümde tek ana (dolgulu) aksiyon butonu.
- Her ayarın ne işe yaradığı ve önerilen değerleri açıkça belirtilmiştir.
- Sistem tepsisi (System Tray) ile arka planda sessiz ve kesintisiz çalışma.
"""

import ctypes
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

from config import Config
from ds4_mapper import DS4Mapper
from game_detector import GameDetector
from hidhide_manager import HidHideManager
from xinput_reader import GamepadState, XInputReader


# Windows Yüksek Hassasiyetli Zamanlayıcı (1 ms timer resolution)
winmm = None
try:
    winmm = ctypes.windll.winmm
except Exception:
    winmm = None

def set_high_resolution_timer(enable: bool):
    if winmm:
        try:
            if enable:
                winmm.timeBeginPeriod(1)
            else:
                winmm.timeEndPeriod(1)
        except Exception:
            pass


class ProfessionalBridgeApp:
    def __init__(self):
        self.config = Config.load_from_file()
        self.reader = XInputReader(
            controller_index=self.config.CONTROLLER_INDEX,
            deadzone=self.config.THUMB_DEADZONE,
            enable_guide=self.config.ENABLE_GUIDE_BUTTON
        )
        self.mapper: Optional[DS4Mapper] = None
        self.detector: Optional[GameDetector] = None
        self.hidhide = HidHideManager()

        self.is_running = True
        self.is_paused = False
        self.current_state = GamepadState()

        # GUI ve Sistem Tepsisi
        self.root: Optional[tk.Tk] = None
        self.tray_icon: Optional[pystray.Icon] = None
        self._bridge_thread: Optional[threading.Thread] = None

    def start_bridge_thread(self):
        """250 Hz köprü aktarım iş parçacığını başlatır."""
        try:
            self.mapper = DS4Mapper(config=self.config, on_rumble=self._on_rumble)
        except Exception as e:
            print(f"[!] Sanal kontrolcü başlatılamadı: {e}")

        # Akıllı Oyun Algılayıcı
        if self.config.AUTO_GAME_DETECT:
            self.detector = GameDetector(
                target_games=self.config.DETECTED_GAMES,
                on_game_started=self._on_game_start,
                on_game_stopped=self._on_game_stop
            )
            self.detector.start()
            if not self.detector.is_game_running():
                self.is_paused = True

        self._bridge_thread = threading.Thread(target=self._bridge_loop, daemon=True, name="BridgeWorker")
        self._bridge_thread.start()

    def _on_rumble(self, large: int, small: int):
        if self.config.ENABLE_RUMBLE and not self.is_paused:
            self.reader.set_vibration(large, small, self.config.RUMBLE_STRENGTH)

    def _on_game_start(self, game_name: str):
        self.is_paused = False
        self._update_tray_icon()

    def _on_game_stop(self, game_name: str):
        self.is_paused = True
        if self.mapper:
            self.mapper.reset()
        self._update_tray_icon()

    def _bridge_loop(self):
        set_high_resolution_timer(True)
        target_interval = 1.0 / self.config.POLLING_RATE_HZ

        while self.is_running:
            loop_start = time.perf_counter()

            if self.is_paused:
                time.sleep(0.04)
                continue

            state = self.reader.read()
            self.current_state = state

            if self.mapper:
                self.mapper.update(state)

            elapsed = time.perf_counter() - loop_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0.0015:
                time.sleep(sleep_time - 0.0008)
            while (time.perf_counter() - loop_start) < target_interval:
                pass

        set_high_resolution_timer(False)
        self.reader.stop_vibration()
        if self.mapper:
            self.mapper.close()

    # -------------------------------------------------------------
    # SİSTEM TEPSİSİ (SYSTEM TRAY)
    # -------------------------------------------------------------
    def _create_tray_image(self, active: bool = True) -> Image.Image:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        body = (37, 99, 235, 255) if active else (100, 116, 139, 255)
        draw.rounded_rectangle([6, 16, 58, 48], radius=12, fill=body)
        draw.ellipse([8, 30, 24, 56], fill=body)
        draw.ellipse([40, 30, 56, 56], fill=body)
        dot = (34, 197, 94, 255) if active else (239, 68, 68, 255)
        draw.ellipse([46, 46, 60, 60], fill=dot, outline=(15, 23, 42, 255), width=2)
        return img

    def _update_tray_icon(self):
        if self.tray_icon:
            self.tray_icon.icon = self._create_tray_image(not self.is_paused)

    def start_tray(self):
        def show_window(icon, item):
            if self.root:
                self.root.after(0, self._restore_from_tray)

        def toggle_bridge(icon, item):
            self.toggle_pause()

        def exit_app(icon, item):
            self.quit_app()

        menu = pystray.Menu(
            item("DualShock 4 Kontrol Merkezi", show_window, default=True),
            pystray.Menu.SEPARATOR,
            item(lambda text: "Köprüyü Duraklat" if not self.is_paused else "Köprüyü Başlat", toggle_bridge),
            pystray.Menu.SEPARATOR,
            item("Çıkış", exit_app)
        )

        self.tray_icon = pystray.Icon("DS4Bridge", self._create_tray_image(not self.is_paused), "DualShock 4 Köprüsü", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _minimize_to_tray(self):
        if self.root:
            self.root.withdraw()

    def _restore_from_tray(self):
        if self.root:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused and self.mapper:
            self.mapper.reset()
        self._update_tray_icon()
        if self.root and hasattr(self, "pause_btn"):
            self._update_header_status()

    # -------------------------------------------------------------
    # PROFESYONEL VE SADE ARAYÜZ (TKINTER)
    # -------------------------------------------------------------
    def run_gui(self):
        self.root = tk.Tk()
        self.root.title("DualShock 4 Kontrol Merkezi")
        self.root.geometry("640x720")
        self.root.minsize(600, 680)
        self.root.configure(bg="#0b1120")

        self._build_interface()

        self.root.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)
        self.start_bridge_thread()
        self.start_tray()

        self._poll_ui()
        self.root.mainloop()

    def _build_interface(self):
        # 1. Üst Durum Kartı (Tek seviyeli, 1px kenarlık, ferah yerleşim)
        header_card = tk.Frame(self.root, bg="#131d31", highlightbackground="#1e293b", highlightthickness=1)
        header_card.pack(fill="x", padx=16, pady=(16, 12))

        # Sol Durum Bilgileri
        status_info_box = tk.Frame(header_card, bg="#131d31")
        status_info_box.pack(side="left", padx=16, pady=14)

        # Kontrolcü Bağlantı Durumu
        self.conn_dot_lbl = tk.Label(
            status_info_box,
            text="● Kontrolcü taranıyor...",
            font=("Segoe UI", 11, "bold"),
            bg="#131d31",
            fg="#94a3b8"
        )
        self.conn_dot_lbl.pack(anchor="w")

        # Köprü Aktarım Durumu
        self.bridge_lbl = tk.Label(
            status_info_box,
            text="● Köprü hazırlanıyor...",
            font=("Segoe UI", 10),
            bg="#131d31",
            fg="#64748b"
        )
        self.bridge_lbl.pack(anchor="w", pady=(3, 0))

        # Sağ: Tek Ana Aksiyon Butonu
        self.pause_btn = tk.Button(
            header_card,
            text="Köprüyü Duraklat",
            font=("Segoe UI", 10, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self.toggle_pause
        )
        self.pause_btn.pack(side="right", padx=16, pady=14)

        # 2. Sekmeler (Notebook)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background="#0b1120", borderwidth=0)
        style.configure("TNotebook.Tab", background="#131d31", foreground="#94a3b8", padding=[20, 9], font=("Segoe UI", 10))
        style.map("TNotebook.Tab", background=[("selected", "#2563eb")], foreground=[("selected", "#ffffff")])

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # Sekme 1: Genel Bakış & Canlı Test
        self.tab_test = tk.Frame(self.notebook, bg="#0b1120")
        self.notebook.add(self.tab_test, text="Genel Bakış & Canlı Test")
        self._build_test_tab(self.tab_test)

        # Sekme 2: Açıklamalı Ayarlar
        self.tab_settings = tk.Frame(self.notebook, bg="#0b1120")
        self.notebook.add(self.tab_settings, text="Yapılandırma & Ayarlar")
        self._build_settings_tab(self.tab_settings)

    def _build_test_tab(self, parent):
        # 1. Analog Çubuklar Kartı
        sticks_card = tk.Frame(parent, bg="#131d31", highlightbackground="#1e293b", highlightthickness=1)
        sticks_card.pack(fill="x", pady=(12, 10))

        tk.Label(sticks_card, text="Analog Çubuklar", font=("Segoe UI", 11, "bold"), bg="#131d31", fg="#f8fafc").pack(anchor="w", padx=14, pady=(10, 4))

        canv_row = tk.Frame(sticks_card, bg="#131d31")
        canv_row.pack(padx=14, pady=(0, 12))

        # Sol Stick
        left_sub = tk.Frame(canv_row, bg="#131d31")
        left_sub.pack(side="left", padx=28)
        tk.Label(left_sub, text="Sol Analog (Hareket)", font=("Segoe UI", 9), bg="#131d31", fg="#94a3b8").pack()
        self.canv_left = tk.Canvas(left_sub, width=100, height=100, bg="#0b1120", highlightthickness=1, highlightbackground="#1e293b")
        self.canv_left.pack(pady=4)
        self.lbl_left_coords = tk.Label(left_sub, text="X: 0.00  Y: 0.00", font=("Segoe UI", 9), bg="#131d31", fg="#64748b")
        self.lbl_left_coords.pack()

        # Sağ Stick
        right_sub = tk.Frame(canv_row, bg="#131d31")
        right_sub.pack(side="left", padx=28)
        tk.Label(right_sub, text="Sağ Analog (Kamera)", font=("Segoe UI", 9), bg="#131d31", fg="#94a3b8").pack()
        self.canv_right = tk.Canvas(right_sub, width=100, height=100, bg="#0b1120", highlightthickness=1, highlightbackground="#1e293b")
        self.canv_right.pack(pady=4)
        self.lbl_right_coords = tk.Label(right_sub, text="X: 0.00  Y: 0.00", font=("Segoe UI", 9), bg="#131d31", fg="#64748b")
        self.lbl_right_coords.pack()

        # 2. Canlı Tuş Girişleri Kartı
        btn_card = tk.Frame(parent, bg="#131d31", highlightbackground="#1e293b", highlightthickness=1)
        btn_card.pack(fill="x", pady=6)

        tk.Label(btn_card, text="Tuş ve Tetik Girişleri", font=("Segoe UI", 11, "bold"), bg="#131d31", fg="#f8fafc").pack(anchor="w", padx=14, pady=(10, 4))
        self.keys_lbl = tk.Label(btn_card, text="(Şu anda bir tuşa basılmıyor)", font=("Segoe UI", 10), bg="#131d31", fg="#38bdf8", wraplength=550, justify="left")
        self.keys_lbl.pack(anchor="w", padx=14, pady=(0, 12))

        # 3. Hızlı Test Aksiyonu
        test_action_row = tk.Frame(parent, bg="#0b1120")
        test_action_row.pack(fill="x", pady=10)

        self.rumble_btn = tk.Button(
            test_action_row,
            text="Titreşimi Test Et (0.4 sn)",
            font=("Segoe UI", 10),
            bg="#1e293b",
            fg="#ffffff",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._test_rumble_action
        )
        self.rumble_btn.pack(side="left")

    def _build_settings_tab(self, parent):
        # 1. Ölü Bölge (Deadzone) Kartı
        dz_card = tk.Frame(parent, bg="#131d31", highlightbackground="#1e293b", highlightthickness=1)
        dz_card.pack(fill="x", pady=(12, 6))

        tk.Label(dz_card, text="Ölü Bölge (Deadzone) Eşiği", font=("Segoe UI", 11, "bold"), bg="#131d31", fg="#f8fafc").pack(anchor="w", padx=14, pady=(8, 2))
        tk.Label(
            dz_card,
            text="Analog çubukların merkezdeki hassasiyet boşluğudur. Çubukları bıraktığınızda karakterin veya kameranın kendiliğinden kaymasını (drift) engeller. (Önerilen: %6.0)",
            font=("Segoe UI", 9),
            bg="#131d31",
            fg="#94a3b8",
            wraplength=550,
            justify="left"
        ).pack(anchor="w", padx=14)

        dz_val_row = tk.Frame(dz_card, bg="#131d31")
        dz_val_row.pack(fill="x", padx=14, pady=(4, 8))
        self.dz_text = tk.Label(dz_val_row, text=f"%{self.config.THUMB_DEADZONE * 100:.1f}", font=("Segoe UI", 10, "bold"), bg="#131d31", fg="#38bdf8")
        self.dz_text.pack(side="left")
        self.dz_slider = ttk.Scale(dz_val_row, from_=0.0, to=0.20, value=self.config.THUMB_DEADZONE, command=self._on_dz_slider)
        self.dz_slider.pack(side="right", fill="x", expand=True, padx=(12, 0))

        # 2. Titreşim Gücü Kartı
        vib_card = tk.Frame(parent, bg="#131d31", highlightbackground="#1e293b", highlightthickness=1)
        vib_card.pack(fill="x", pady=6)

        tk.Label(vib_card, text="Titreşim (Force Feedback) Gücü", font=("Segoe UI", 11, "bold"), bg="#131d31", fg="#f8fafc").pack(anchor="w", padx=14, pady=(8, 2))
        tk.Label(
            vib_card,
            text="God of War gibi oyunlarda Kratos'un balta fırlatması, darbeler ve büyü efektlerinin kol motorlarına iletilme şiddetidir. (Önerilen: %100)",
            font=("Segoe UI", 9),
            bg="#131d31",
            fg="#94a3b8",
            wraplength=550,
            justify="left"
        ).pack(anchor="w", padx=14)

        vib_val_row = tk.Frame(vib_card, bg="#131d31")
        vib_val_row.pack(fill="x", padx=14, pady=(4, 8))
        self.vib_text = tk.Label(vib_val_row, text=f"%{self.config.RUMBLE_STRENGTH * 100:.0f}", font=("Segoe UI", 10, "bold"), bg="#131d31", fg="#38bdf8")
        self.vib_text.pack(side="left")
        self.vib_slider = ttk.Scale(vib_val_row, from_=0.0, to=2.0, value=self.config.RUMBLE_STRENGTH, command=self._on_vib_slider)
        self.vib_slider.pack(side="right", fill="x", expand=True, padx=(12, 0))

        # 3. Back Tuşu ve Touchpad Kartı
        back_card = tk.Frame(parent, bg="#131d31", highlightbackground="#1e293b", highlightthickness=1)
        back_card.pack(fill="x", pady=6)

        tk.Label(back_card, text="Back (Görünüm) Tuşu Davranışı", font=("Segoe UI", 11, "bold"), bg="#131d31", fg="#f8fafc").pack(anchor="w", padx=14, pady=(8, 2))
        tk.Label(
            back_card,
            text="PlayStation oyunlarında haritayı ve menüyü açmak için DualShock 4 dokunmatik yüzeyine (Touchpad) basılır. Koldaki Back tuşunun işlevini belirler. (Önerilen: both - Touchpad + Share)",
            font=("Segoe UI", 9),
            bg="#131d31",
            fg="#94a3b8",
            wraplength=550,
            justify="left"
        ).pack(anchor="w", padx=14)

        back_mode_row = tk.Frame(back_card, bg="#131d31")
        back_mode_row.pack(anchor="w", padx=14, pady=(6, 10))
        self.back_mode_var = tk.StringVar(value=self.config.BACK_MAPPING_MODE)
        mode_menu = ttk.Combobox(back_mode_row, textvariable=self.back_mode_var, values=["both", "touchpad", "share"], state="readonly", width=16)
        mode_menu.pack(side="left")
        tk.Label(back_mode_row, text="(both: Haritayı doğrudan koldan açar)", font=("Segoe UI", 9), bg="#131d31", fg="#64748b").pack(side="left", padx=8)

        # 4. Otomasyon ve HidHide Kartı
        auto_card = tk.Frame(parent, bg="#131d31", highlightbackground="#1e293b", highlightthickness=1)
        auto_card.pack(fill="x", pady=6)

        tk.Label(auto_card, text="Otomasyon ve Cihaz Gizleme", font=("Segoe UI", 11, "bold"), bg="#131d31", fg="#f8fafc").pack(anchor="w", padx=14, pady=(8, 2))

        # Akıllı Oyun Algılama
        self.auto_detect_var = tk.BooleanVar(value=self.config.AUTO_GAME_DETECT)
        chk_detect = tk.Checkbutton(
            auto_card,
            text="Akıllı Oyun Algılama (Önerilen: Açık)\nDesteklenen bir PlayStation oyunu açıldığında köprüyü otomatik başlatır, oyundan çıkıldığında uyku moduna alır.",
            variable=self.auto_detect_var,
            font=("Segoe UI", 9),
            bg="#131d31",
            fg="#f8fafc",
            selectcolor="#0b1120",
            activebackground="#131d31",
            activeforeground="#f8fafc",
            justify="left"
        )
        chk_detect.pack(anchor="w", padx=14, pady=4)

        # HidHide Cloaking
        if self.hidhide.is_installed():
            self.hidhide_var = tk.BooleanVar(value=bool(self.hidhide.get_cloaking_status()))
            chk_hidhide = tk.Checkbutton(
                auto_card,
                text="HidHide ile Fiziksel Xbox Kolunu Gizle (Önerilen: Açık)\nFiziksel kolu oyunlardan gizleyerek çift basmayı ve Xbox tuş simgelerinin çakışmasını engeller.",
                variable=self.hidhide_var,
                font=("Segoe UI", 9),
                bg="#131d31",
                fg="#f8fafc",
                selectcolor="#0b1120",
                activebackground="#131d31",
                activeforeground="#f8fafc",
                justify="left",
                command=self._on_toggle_hidhide
            )
            chk_hidhide.pack(anchor="w", padx=14, pady=(4, 10))

        # Alt Butonlar Satırı (Önerilenleri Yükle + Kaydet)
        btn_action_row = tk.Frame(parent, bg="#0b1120")
        btn_action_row.pack(fill="x", pady=12)

        # İkincil Buton: Önerilen Ayarları Yükle
        reset_btn = tk.Button(
            btn_action_row,
            text="Önerilen Ayarları Yükle",
            font=("Segoe UI", 10),
            bg="#1e293b",
            fg="#ffffff",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=self._load_recommended_settings
        )
        reset_btn.pack(side="left")

        # Tek Ana Vurgulu Buton: Ayarları Kaydet
        self.save_btn = tk.Button(
            btn_action_row,
            text="Ayarları Kaydet",
            font=("Segoe UI", 10, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief="flat",
            padx=18,
            pady=8,
            cursor="hand2",
            command=self._save_all_settings
        )
        self.save_btn.pack(side="right")

    def _on_dz_slider(self, val):
        f = float(val)
        self.config.THUMB_DEADZONE = f
        self.reader.deadzone = f
        self.dz_text.config(text=f"%{f * 100:.1f}")

    def _on_vib_slider(self, val):
        f = float(val)
        self.config.RUMBLE_STRENGTH = f
        self.vib_text.config(text=f"%{f * 100:.0f}")

    def _on_toggle_hidhide(self):
        new_state = self.hidhide_var.get()
        self.hidhide.set_cloaking(new_state)

    def _load_recommended_settings(self):
        self.config.THUMB_DEADZONE = 0.06
        self.dz_slider.set(0.06)
        self.dz_text.config(text="%6.0")

        self.config.RUMBLE_STRENGTH = 1.0
        self.vib_slider.set(1.0)
        self.vib_text.config(text="%100")

        self.config.BACK_MAPPING_MODE = "both"
        self.back_mode_var.set("both")

        self.config.AUTO_GAME_DETECT = True
        self.auto_detect_var.set(True)

        messagebox.showinfo("Önerilen Ayarlar", "Tüm ayarlar önerilen fabrika ayarlarına getirildi. Kaydetmek için 'Ayarları Kaydet' butonuna basabilirsiniz.")

    def _save_all_settings(self):
        self.config.BACK_MAPPING_MODE = self.back_mode_var.get()
        self.config.AUTO_GAME_DETECT = self.auto_detect_var.get()
        self.config.save_to_file()
        self.save_btn.config(text="Kaydedildi ✓", bg="#16a34a")
        self.root.after(1500, lambda: self.save_btn.config(text="Ayarları Kaydet", bg="#2563eb") if self.root else None)

    def _test_rumble_action(self):
        def vib():
            self.reader.set_vibration(220, 220, self.config.RUMBLE_STRENGTH)
            time.sleep(0.4)
            self.reader.stop_vibration()
        threading.Thread(target=vib, daemon=True).start()

    def _draw_stick(self, canvas: tk.Canvas, x: float, y: float, dz: float):
        canvas.delete("all")
        cx, cy, r = 50, 50, 42
        # Dış sınır
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#1e293b", width=1)
        # Ölü bölge dairesi
        dz_r = r * dz
        canvas.create_oval(cx - dz_r, cy - dz_r, cx + dz_r, cy + dz_r, outline="#334155", dash=(2, 2))
        # Merkez çizgileri
        canvas.create_line(cx - 5, cy, cx + 5, cy, fill="#1e293b")
        canvas.create_line(cx, cy - 5, cx, cy + 5, fill="#1e293b")
        # Canlı stick noktası
        px = cx + (x * r)
        py = cy - (y * r)
        canvas.create_oval(px - 4, py - 4, px + 4, py + 4, fill="#38bdf8", outline="")

    def _update_header_status(self):
        if self.current_state.connected:
            self.conn_dot_lbl.config(text=f"● Fiziksel Kol Bağlı (Xbox Controller #{self.config.CONTROLLER_INDEX})", fg="#10b981")
        else:
            self.conn_dot_lbl.config(text="● Kol Bağlantısı Bekleniyor...", fg="#ef4444")

        if self.is_paused:
            self.bridge_lbl.config(text="● Köprü Duraklatıldı", fg="#94a3b8")
            self.pause_btn.config(text="Köprüyü Başlat", bg="#10b981")
        else:
            self.bridge_lbl.config(text="● PlayStation Aktarımı Aktif (250 Hz)", fg="#38bdf8")
            self.pause_btn.config(text="Köprüyü Duraklat", bg="#2563eb")

    def _poll_ui(self):
        if not self.is_running or not self.root:
            return

        try:
            self._update_header_status()

            s = self.current_state
            self._draw_stick(self.canv_left, s.thumb_lx, s.thumb_ly, self.config.THUMB_DEADZONE)
            self._draw_stick(self.canv_right, s.thumb_rx, s.thumb_ry, self.config.THUMB_DEADZONE)

            self.lbl_left_coords.config(text=f"X: {s.thumb_lx:+.2f}  Y: {s.thumb_ly:+.2f}")
            self.lbl_right_coords.config(text=f"X: {s.thumb_rx:+.2f}  Y: {s.thumb_ry:+.2f}")

            # Basılı tuşlar
            pressed = []
            if s.btn_a: pressed.append("A (Çarpı ⨉)")
            if s.btn_b: pressed.append("B (Daire ◯)")
            if s.btn_x: pressed.append("X (Kare ▢)")
            if s.btn_y: pressed.append("Y (Üçgen △)")
            if s.btn_lb: pressed.append("LB (L1)")
            if s.btn_rb: pressed.append("RB (R1)")
            if s.btn_l3: pressed.append("L3 (Sol Stick Tık)")
            if s.btn_r3: pressed.append("R3 (Sağ Stick Tık)")
            if s.btn_start: pressed.append("Start (Options)")
            if s.btn_back: pressed.append("Back (Touchpad / Harita)")
            if s.btn_guide: pressed.append("Xbox (PS Logo)")
            if s.dpad_up: pressed.append("D-pad Yukarı")
            if s.dpad_down: pressed.append("D-pad Aşağı")
            if s.dpad_left: pressed.append("D-pad Sol")
            if s.dpad_right: pressed.append("D-pad Sağ")
            if s.trigger_left > 0.1: pressed.append(f"L2: %{int(s.trigger_left * 100)}")
            if s.trigger_right > 0.1: pressed.append(f"R2: %{int(s.trigger_right * 100)}")

            self.keys_lbl.config(text="  |  ".join(pressed) if pressed else "(Şu anda bir tuşa basılmıyor)")

        except Exception:
            pass

        self.root.after(30, self._poll_ui)

    def quit_app(self):
        self.is_running = False
        if self.tray_icon:
            self.tray_icon.stop()
        if self.detector:
            self.detector.stop()
        if self.root:
            self.root.destroy()
        sys.exit(0)


def main():
    app = ProfessionalBridgeApp()
    app.run_gui()


if __name__ == "__main__":
    main()
