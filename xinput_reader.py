"""
Yüksek Performanslı XInput Okuyucu (ctypes tabanlı, sıfır ek gecikme, Ordinal 100 Guide tuşu destekli)
"""

import ctypes
import math
from dataclasses import dataclass
from typing import Optional, Tuple

# XInput Buton Maskeleri (Win32 API)
XINPUT_GAMEPAD_DPAD_UP        = 0x0001
XINPUT_GAMEPAD_DPAD_DOWN      = 0x0002
XINPUT_GAMEPAD_DPAD_LEFT      = 0x0004
XINPUT_GAMEPAD_DPAD_RIGHT     = 0x0008
XINPUT_GAMEPAD_START          = 0x0010
XINPUT_GAMEPAD_BACK           = 0x0020
XINPUT_GAMEPAD_LEFT_THUMB     = 0x0040  # L3
XINPUT_GAMEPAD_RIGHT_THUMB    = 0x0080  # R3
XINPUT_GAMEPAD_LEFT_SHOULDER  = 0x0100  # LB / L1
XINPUT_GAMEPAD_RIGHT_SHOULDER = 0x0200  # RB / R1
XINPUT_GAMEPAD_GUIDE          = 0x0400  # Xbox / PS Logosu (XInputGetStateEx - Ordinal 100)
XINPUT_GAMEPAD_A              = 0x1000  # A / Cross
XINPUT_GAMEPAD_B              = 0x2000  # B / Circle
XINPUT_GAMEPAD_X              = 0x4000  # X / Square
XINPUT_GAMEPAD_Y              = 0x8000  # Y / Triangle

# Win32 Dönüş Kodları
ERROR_SUCCESS = 0
ERROR_DEVICE_NOT_CONNECTED = 1167


class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", ctypes.c_ushort),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", ctypes.c_ulong),
        ("Gamepad", XINPUT_GAMEPAD),
    ]


class XINPUT_VIBRATION(ctypes.Structure):
    _fields_ = [
        ("wLeftMotorSpeed", ctypes.c_ushort),
        ("wRightMotorSpeed", ctypes.c_ushort),
    ]


@dataclass
class GamepadState:
    packet_number: int = 0
    connected: bool = False

    # Dijital butonlar
    btn_a: bool = False
    btn_b: bool = False
    btn_x: bool = False
    btn_y: bool = False
    btn_lb: bool = False
    btn_rb: bool = False
    btn_l3: bool = False
    btn_r3: bool = False
    btn_start: bool = False
    btn_back: bool = False
    btn_guide: bool = False

    # D-pad (Yön tuşları)
    dpad_up: bool = False
    dpad_down: bool = False
    dpad_left: bool = False
    dpad_right: bool = False

    # Analog tetikler (0.0 - 1.0)
    trigger_left: float = 0.0
    trigger_right: float = 0.0

    # Analog çubuklar (-1.0 - +1.0)
    thumb_lx: float = 0.0
    thumb_ly: float = 0.0
    thumb_rx: float = 0.0
    thumb_ry: float = 0.0


class XInputReader:
    """
    Windows XInput kütüphanesini doğrudan ctypes ile sarmalar.
    Mikrosaniye seviyesinde hızlıdır ve Guide (PS) butonunu okumak için
    XInputGetStateEx (ordinal 100) fonksiyonunu kullanır.
    """

    def __init__(self, controller_index: int = 0, deadzone: float = 0.06, enable_guide: bool = True):
        self.controller_index = controller_index
        self.deadzone = deadzone
        self.enable_guide = enable_guide
        self._raw_state = XINPUT_STATE()
        self._get_state_fn = None
        self._set_state_fn = None
        self._is_ex = False

        self._load_xinput()

    def _load_xinput(self):
        # xinput1_4.dll (Windows 8/10/11), yoksa xinput1_3.dll, yoksa xinput9_1_0.dll
        dll_names = ["xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"]
        dll = None
        for name in dll_names:
            try:
                dll = ctypes.windll.LoadLibrary(name)
                break
            except OSError:
                continue

        if not dll:
            raise RuntimeError("Sistemde XInput DLL'i bulunamadı!")

        # Titreşim ayarlama fonksiyonu
        self._set_state_fn = getattr(dll, "XInputSetState", None)

        # Guide butonu için ordinal 100 (XInputGetStateEx) dene
        if self.enable_guide:
            try:
                self._get_state_fn = dll[100]
                self._is_ex = True
            except (AttributeError, KeyError, IndexError):
                self._get_state_fn = getattr(dll, "XInputGetState", None)
                self._is_ex = False
        else:
            self._get_state_fn = getattr(dll, "XInputGetState", None)
            self._is_ex = False

        if not self._get_state_fn:
            raise RuntimeError("XInput durum fonksiyonu yüklenemedi!")

    def set_vibration(self, large_motor: int, small_motor: int, multiplier: float = 1.0):
        """
        Fiziksel XInput kontrolcüsünün titreşim motorlarını çalıştırır.
        large_motor: 0 - 255 (Ağır titreşim motoru)
        small_motor: 0 - 255 (Hafif titreşim motoru)
        multiplier: 0.0 - 2.0 (Titreşim yoğunluk çarpanı)
        """
        if not self._set_state_fn or self.controller_index is None:
            return

        adj_large = int(large_motor * multiplier)
        adj_small = int(small_motor * multiplier)

        # 0-255 değerini Win32 XInput 0-65535 aralığına ölçekle
        w_left = min(65535, max(0, int(adj_large * 257)))
        w_right = min(65535, max(0, int(adj_small * 257)))

        vib = XINPUT_VIBRATION(
            wLeftMotorSpeed=w_left,
            wRightMotorSpeed=w_right,
        )
        try:
            self._set_state_fn(self.controller_index, ctypes.byref(vib))
        except Exception:
            pass

    def stop_vibration(self):
        """Titreşimi tamamen kapatır."""
        self.set_vibration(0, 0)

    def _apply_radial_deadzone(self, x: float, y: float) -> Tuple[float, float]:
        """
        Dairesel ölü bölge (deadzone) filtresi uygular.
        Stick merkez civarındayken drift yapmasını engeller, eşik aşıldığında pürüzsüz ölçekler.
        """
        magnitude = math.sqrt(x * x + y * y)
        if magnitude <= self.deadzone:
            return 0.0, 0.0

        # Eşik dışındayken 0.0 - 1.0 arasına lineer yeniden ölçekle
        scaled_magnitude = min(1.0, (magnitude - self.deadzone) / (1.0 - self.deadzone))
        scale = scaled_magnitude / magnitude
        return x * scale, y * scale

    def read(self) -> GamepadState:
        """
        Belirtilen indeksteki kolun anlık durumunu okur ve GamepadState nesnesi döner.
        """
        ret = self._get_state_fn(self.controller_index, ctypes.byref(self._raw_state))

        if ret != ERROR_SUCCESS:
            return GamepadState(connected=False)

        gp = self._raw_state.Gamepad
        buttons = gp.wButtons

        # Analog çubukları normalize et (-1.0 ile 1.0 arasına)
        # XInput kısa tamsayı aralığı: -32768 .. +32767
        raw_lx = gp.sThumbLX / (32767.0 if gp.sThumbLX >= 0 else 32768.0)
        raw_ly = gp.sThumbLY / (32767.0 if gp.sThumbLY >= 0 else 32768.0)
        raw_rx = gp.sThumbRX / (32767.0 if gp.sThumbRX >= 0 else 32768.0)
        raw_ry = gp.sThumbRY / (32767.0 if gp.sThumbRY >= 0 else 32768.0)

        # Ölü bölge uygula
        lx, ly = self._apply_radial_deadzone(raw_lx, raw_ly)
        rx, ry = self._apply_radial_deadzone(raw_rx, raw_ry)

        # Tetikler: 0 .. 255 -> 0.0 .. 1.0
        lt = gp.bLeftTrigger / 255.0
        rt = gp.bRightTrigger / 255.0

        return GamepadState(
            packet_number=self._raw_state.dwPacketNumber,
            connected=True,
            btn_a=bool(buttons & XINPUT_GAMEPAD_A),
            btn_b=bool(buttons & XINPUT_GAMEPAD_B),
            btn_x=bool(buttons & XINPUT_GAMEPAD_X),
            btn_y=bool(buttons & XINPUT_GAMEPAD_Y),
            btn_lb=bool(buttons & XINPUT_GAMEPAD_LEFT_SHOULDER),
            btn_rb=bool(buttons & XINPUT_GAMEPAD_RIGHT_SHOULDER),
            btn_l3=bool(buttons & XINPUT_GAMEPAD_LEFT_THUMB),
            btn_r3=bool(buttons & XINPUT_GAMEPAD_RIGHT_THUMB),
            btn_start=bool(buttons & XINPUT_GAMEPAD_START),
            btn_back=bool(buttons & XINPUT_GAMEPAD_BACK),
            btn_guide=bool(buttons & XINPUT_GAMEPAD_GUIDE),
            dpad_up=bool(buttons & XINPUT_GAMEPAD_DPAD_UP),
            dpad_down=bool(buttons & XINPUT_GAMEPAD_DPAD_DOWN),
            dpad_left=bool(buttons & XINPUT_GAMEPAD_DPAD_LEFT),
            dpad_right=bool(buttons & XINPUT_GAMEPAD_DPAD_RIGHT),
            trigger_left=lt,
            trigger_right=rt,
            thumb_lx=lx,
            thumb_ly=ly,
            thumb_rx=rx,
            thumb_ry=ry,
        )

    @staticmethod
    def find_first_connected_index() -> Optional[int]:
        """Sisteme bağlı ilk XInput kolunun indeksini (0-3) tespit eder."""
        try:
            import XInput
            connected = XInput.get_connected()
            for idx, is_conn in enumerate(connected):
                if is_conn:
                    return idx
        except Exception:
            # Yedek ctypes taraması
            for idx in range(4):
                try:
                    reader = XInputReader(controller_index=idx, enable_guide=False)
                    if reader.read().connected:
                        return idx
                except Exception:
                    pass
        return None
