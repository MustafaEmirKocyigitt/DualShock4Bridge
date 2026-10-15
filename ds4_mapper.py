"""
XInput -> DualShock 4 (vgamepad VDS4Gamepad) Eşleme Modülü
"""

from typing import Dict, Optional
import vgamepad as vg
from config import Config
from xinput_reader import GamepadState


class DS4Mapper:
    """
    XInput gamepad durumunu sanal bir DualShock 4 (DS4) kontrolcüsüne aktarır.
    """

    def __init__(self, config: Optional[Config] = None, on_rumble=None):
        self.config = config or Config()
        self.on_rumble = on_rumble
        self.gamepad = vg.VDS4Gamepad()

        # İki yönlü titreşim dinleyicisini ViGEmBus'a kaydet
        if self.config.ENABLE_RUMBLE and self.on_rumble:
            try:
                self.gamepad.register_notification(self._rumble_callback)
            except Exception as e:
                print(f"[*] Titresim dinleyicisi kaydedilemedi: {e}")

        # Dijital buton eşleme sözlüğü
        # XInput butonu -> DS4_BUTTONS sabiti
        self.button_mapping = {
            "btn_a": vg.DS4_BUTTONS.DS4_BUTTON_CROSS,
            "btn_b": vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE,
            "btn_x": vg.DS4_BUTTONS.DS4_BUTTON_SQUARE,
            "btn_y": vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE,
            "btn_lb": vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT,
            "btn_rb": vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT,
            "btn_l3": vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT,
            "btn_r3": vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT,
            "btn_start": vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS,
            "btn_back": vg.DS4_BUTTONS.DS4_BUTTON_SHARE,
        }

        # Önceki durum önbelleği (gereksiz vgamepad çağrılarını optimize etmek için)
        self._prev_state: Optional[GamepadState] = None
        self._guide_pressed: bool = False

    def _rumble_callback(self, client, target, large_motor, small_motor, led_number, user_data):
        """Oyundan gelen titreşim komutunu fiziksel kola aktaran ViGEm callback'i"""
        if self.on_rumble:
            self.on_rumble(large_motor, small_motor)

    def _determine_dpad_direction(self, state: GamepadState) -> vg.DS4_DPAD_DIRECTIONS:
        """XInput dpad tuşlarını DS4 yön enumuna çevirir (çapraz yönler dahil)."""
        up = state.dpad_up
        down = state.dpad_down
        left = state.dpad_left
        right = state.dpad_right

        if up and right:
            return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHEAST
        if up and left:
            return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHWEST
        if down and right:
            return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHEAST
        if down and left:
            return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHWEST
        if up:
            return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH
        if down:
            return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH
        if left:
            return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST
        if right:
            return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST

        return vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE

    def update(self, state: GamepadState):
        """
        Gelen XInput durumunu sanal DS4 kontrolcüsüne uygular ve raporu gönderir.
        """
        if not state.connected:
            self.reset()
            return

        # 1. Dijital Butonlar
        for attr, ds4_btn in self.button_mapping.items():
            if attr == "btn_back":
                continue  # Back tuşunu aşağıda özel BACK_MAPPING_MODE ile yöneteceğiz
            is_pressed = getattr(state, attr, False)
            if is_pressed:
                self.gamepad.press_button(button=ds4_btn)
            else:
                self.gamepad.release_button(button=ds4_btn)

        # 2. Özel Butonlar (Guide -> PS Button, Back -> Share / Touchpad Simülasyonu)
        if self.config.ENABLE_GUIDE_BUTTON:
            if state.btn_guide:
                self.gamepad.press_special_button(special_button=vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS)
            else:
                self.gamepad.release_special_button(special_button=vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS)

        # Back Tuşu Modları (Touchpad ve Share)
        mode = getattr(self.config, "BACK_MAPPING_MODE", "both")
        press_touchpad = state.btn_back and (mode in ("both", "touchpad"))
        press_share = state.btn_back and (mode in ("both", "share"))

        if press_touchpad:
            self.gamepad.press_special_button(special_button=vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_TOUCHPAD)
        else:
            self.gamepad.release_special_button(special_button=vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_TOUCHPAD)

        if press_share:
            self.gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHARE)
        else:
            self.gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHARE)

        # 3. Yön Tuşları (D-pad)
        dpad_dir = self._determine_dpad_direction(state)
        self.gamepad.directional_pad(direction=dpad_dir)

        # 4. Analog Tetikler (L2 / R2)
        lt = max(0.0, min(1.0, state.trigger_left))
        rt = max(0.0, min(1.0, state.trigger_right))
        self.gamepad.left_trigger_float(value_float=lt)
        self.gamepad.right_trigger_float(value_float=rt)

        # Tetikler için dijital buton desteği (God of War vb. oyunların %100 uyumu için)
        threshold = self.config.TRIGGER_DIGITAL_THRESHOLD
        if lt >= threshold:
            self.gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_LEFT)
        else:
            self.gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_LEFT)

        if rt >= threshold:
            self.gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_RIGHT)
        else:
            self.gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_RIGHT)

        # 5. Sol ve Sağ Analog Çubuklar
        lx = state.thumb_lx
        ly = -state.thumb_ly if self.config.INVERT_LEFT_Y else state.thumb_ly
        rx = state.thumb_rx
        ry = -state.thumb_ry if self.config.INVERT_RIGHT_Y else state.thumb_ry

        self.gamepad.left_joystick_float(x_value_float=lx, y_value_float=ly)
        self.gamepad.right_joystick_float(x_value_float=rx, y_value_float=ry)

        # 6. Raporu Gönder (ViGEmBus driver update)
        self.gamepad.update()
        self._prev_state = state

    def reset(self):
        """Sanal kontrolcünün tüm girdilerini sıfırlar."""
        try:
            self.gamepad.reset()
            self.gamepad.update()
        except Exception:
            pass

    def close(self):
        """Sanal kontrolcüyü temiz bir şekilde kapatır ve sistemden ayırır."""
        if self.config.ENABLE_RUMBLE and self.on_rumble:
            try:
                self.gamepad.unregister_notification()
            except Exception:
                pass
        self.reset()
        del self.gamepad
