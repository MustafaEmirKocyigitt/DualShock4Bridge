"""
Akıllı Oyun Algılayıcı (Game Detector) Modülü
============================================
Arka planda düşük CPU maliyetiyle çalışan süreçleri izler.
Desteklenen bir oyun başlatıldığında köprüyü otomatik aktif eder,
oyun kapandığında köprüyü dinlenme (uyku) moduna alır.
"""

import threading
import time
from typing import Callable, List, Optional, Set
import psutil


class GameDetector:
    def __init__(
        self,
        target_games: List[str],
        check_interval: float = 2.0,
        on_game_started: Optional[Callable[[str], None]] = None,
        on_game_stopped: Optional[Callable[[str], None]] = None
    ):
        self.target_games: Set[str] = {g.lower() for g in target_games}
        self.check_interval: float = check_interval
        self.on_game_started: Optional[Callable[[str], None]] = on_game_started
        self.on_game_stopped: Optional[Callable[[str], None]] = on_game_stopped

        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._active_game: Optional[str] = None

    @property
    def active_game(self) -> Optional[str]:
        return self._active_game

    def is_game_running(self) -> bool:
        return self._active_game is not None

    def start(self):
        """İzleme arka plan iş parçacığını başlatır."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="GameDetectorThread")
        self._thread.start()

    def stop(self):
        """İzleme iş parçacığını durdurur."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _find_running_target_game(self) -> Optional[str]:
        """Çalışan süreçler arasında hedef oyunları arar."""
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info['name']
                    if name and name.lower() in self.target_games:
                        return name
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return None

    def _monitor_loop(self):
        while self._running:
            found_game = self._find_running_target_game()

            if found_game and self._active_game is None:
                # Oyun yeni başladı
                self._active_game = found_game
                if self.on_game_started:
                    try:
                        self.on_game_started(found_game)
                    except Exception as e:
                        print(f"[!] Oyun başlatma bildirim hatası: {e}")

            elif not found_game and self._active_game is not None:
                # Oyun kapandı
                last_game = self._active_game
                self._active_game = None
                if self.on_game_stopped:
                    try:
                        self.on_game_stopped(last_game)
                    except Exception as e:
                        print(f"[!] Oyun kapanma bildirim hatası: {e}")

            time.sleep(self.check_interval)
