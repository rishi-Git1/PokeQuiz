"""Optional terminal audio: menu BGM, input blip, and win completion stinger."""

from __future__ import annotations

import builtins
import os
import threading
from pathlib import Path

from pokequiz.models import GameSettings

_stop = threading.Event()
_thread: threading.Thread | None = None

_mixer_ready = False
_original_input = builtins.input
_input_hook_installed = False
_select_sound = None  # pygame.mixer.Sound | None
_completion_sound = None  # pygame.mixer.Sound | None

_mute_bgm = False
_mute_input_sfx = False
_mute_completion_sfx = False


def _assets_dir() -> Path:
    return Path(__file__).resolve().parent / "assets"


def _default_bgm_paths() -> list[Path]:
    base = _assets_dir()
    return [
        base / "littleroot.ogg",
        base / "littleroot.mp3",
        base / "littleroot.wav",
    ]


def _default_pokedex_select_paths() -> list[Path]:
    base = _assets_dir()
    return [
        base / "pokedex_select.wav",
        base / "pokedex_select.ogg",
        base / "pokedex_select.mp3",
    ]


def _default_completion_paths() -> list[Path]:
    base = _assets_dir()
    return [
        base / "completion.wav",
        base / "completion.ogg",
        base / "completion.mp3",
    ]


def resolve_bgm_file() -> Path | None:
    env = (os.environ.get("POKEQUIZ_BGM") or "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p
    for candidate in _default_bgm_paths():
        if candidate.is_file():
            return candidate
    return None


def resolve_pokedex_select_sound() -> Path | None:
    env = (os.environ.get("POKEQUIZ_INPUT_SFX") or "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p
    for candidate in _default_pokedex_select_paths():
        if candidate.is_file():
            return candidate
    return None


def resolve_completion_sound() -> Path | None:
    env = (os.environ.get("POKEQUIZ_COMPLETION_SFX") or "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p
    for candidate in _default_completion_paths():
        if candidate.is_file():
            return candidate
    return None


def _bgm_volume() -> float:
    raw = (os.environ.get("POKEQUIZ_BGM_VOLUME") or "0.35").strip()
    try:
        v = float(raw)
    except ValueError:
        return 0.35
    return max(0.0, min(1.0, v))


def _sfx_volume() -> float:
    raw = (os.environ.get("POKEQUIZ_INPUT_SFX_VOLUME") or "0.65").strip()
    try:
        v = float(raw)
    except ValueError:
        return 0.65
    return max(0.0, min(1.0, v))


def _completion_volume() -> float:
    raw = (os.environ.get("POKEQUIZ_COMPLETION_SFX_VOLUME") or "0.75").strip()
    try:
        v = float(raw)
    except ValueError:
        return 0.75
    return max(0.0, min(1.0, v))


def _import_pygame():
    import pygame

    return pygame


def configure(settings: GameSettings) -> None:
    """Sync mute flags from settings; start or stop BGM to match."""
    global _mute_bgm, _mute_input_sfx, _mute_completion_sfx
    _mute_bgm = settings.mute_bgm
    _mute_input_sfx = settings.mute_input_sfx
    _mute_completion_sfx = settings.mute_completion_sfx
    if _mute_bgm:
        stop()
    else:
        start_if_configured()


def ensure_mixer() -> bool:
    """Initialize pygame.mixer on the main thread (required for BGM + input SFX together)."""
    global _mixer_ready
    if _mixer_ready:
        return True
    try:
        pygame = _import_pygame()
    except ImportError:
        return False
    try:
        pygame.mixer.init()
        _mixer_ready = True
        return True
    except Exception:
        return False


def _play_loop(path: Path) -> None:
    pygame = _import_pygame()
    try:
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.set_volume(_bgm_volume())
        pygame.mixer.music.play(loops=-1)
        _stop.wait()
    finally:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass


def start_if_configured() -> None:
    global _thread
    if _mute_bgm:
        return
    if _thread is not None and _thread.is_alive():
        return
    path = resolve_bgm_file()
    if path is None:
        return
    try:
        _import_pygame()
    except ImportError:
        print(
            "Tip: for background music, `pip install pygame` and place littleroot.ogg/mp3/wav "
            "in pokequiz/assets/ (or set POKEQUIZ_BGM)."
        )
        return
    if not ensure_mixer():
        return
    _stop.clear()
    _thread = threading.Thread(target=_play_loop, args=(path,), name="pokequiz-bgm", daemon=True)
    _thread.start()


def stop() -> None:
    global _thread
    _stop.set()
    if _thread is not None:
        _thread.join(timeout=3.0)
        _thread = None


def _load_select_sound():
    global _select_sound
    if _select_sound is not None:
        return
    path = resolve_pokedex_select_sound()
    if path is None:
        return
    pygame = _import_pygame()
    try:
        snd = pygame.mixer.Sound(str(path))
        snd.set_volume(_sfx_volume())
        _select_sound = snd
    except Exception:
        _select_sound = None


def play_pokedex_select_sound() -> None:
    if _mute_input_sfx:
        return
    if resolve_pokedex_select_sound() is None:
        return
    if not ensure_mixer():
        return
    _load_select_sound()
    if _select_sound is None:
        return
    try:
        _select_sound.play()
    except Exception:
        pass


def _load_completion_sound() -> None:
    global _completion_sound
    if _completion_sound is not None:
        return
    path = resolve_completion_sound()
    if path is None:
        return
    pygame = _import_pygame()
    try:
        snd = pygame.mixer.Sound(str(path))
        snd.set_volume(_completion_volume())
        _completion_sound = snd
    except Exception:
        _completion_sound = None


def play_completion_sound() -> None:
    """Short fanfare when the player wins a mode (not on quit or loss)."""
    if _mute_completion_sfx:
        return
    if resolve_completion_sound() is None:
        return
    if not ensure_mixer():
        return
    _load_completion_sound()
    if _completion_sound is None:
        return
    try:
        _completion_sound.play()
    except Exception:
        pass


def _input_with_select_sound(prompt: str = "") -> str:
    line = _original_input(prompt)
    play_pokedex_select_sound()
    return line


def install_input_sound_hook_if_configured() -> None:
    global _input_hook_installed
    if _input_hook_installed:
        return
    if resolve_pokedex_select_sound() is None:
        return
    try:
        _import_pygame()
    except ImportError:
        print(
            "Tip: for Pokedex input sound, `pip install pygame` and place pokedex_select.wav/ogg/mp3 "
            "in pokequiz/assets/ (or set POKEQUIZ_INPUT_SFX)."
        )
        return
    if not ensure_mixer():
        return
    builtins.input = _input_with_select_sound
    _input_hook_installed = True


def setup_terminal_audio() -> None:
    """Prepare mixer + input hook when asset files exist; BGM thread starts separately from main()."""
    want_bgm = resolve_bgm_file() is not None
    want_sfx = resolve_pokedex_select_sound() is not None
    want_completion = resolve_completion_sound() is not None
    if not want_bgm and not want_sfx and not want_completion:
        return
    try:
        _import_pygame()
    except ImportError:
        if want_bgm:
            print(
                "Tip: for background music, `pip install pygame` and place littleroot.ogg/mp3/wav "
                "in pokequiz/assets/ (or set POKEQUIZ_BGM)."
            )
        if want_sfx:
            print(
                "Tip: for Pokedex input sound, `pip install pygame` and place pokedex_select.wav/ogg/mp3 "
                "in pokequiz/assets/ (or set POKEQUIZ_INPUT_SFX)."
            )
        if want_completion:
            print(
                "Tip: for win fanfare, `pip install pygame` and place completion.wav/ogg/mp3 "
                "in pokequiz/assets/ (or set POKEQUIZ_COMPLETION_SFX)."
            )
        return
    if not ensure_mixer():
        return
    install_input_sound_hook_if_configured()


def shutdown_terminal_audio() -> None:
    global _input_hook_installed, _mixer_ready, _select_sound, _completion_sound
    if _input_hook_installed:
        builtins.input = _original_input
        _input_hook_installed = False
    stop()
    _select_sound = None
    _completion_sound = None
    if _mixer_ready:
        try:
            pygame = _import_pygame()
            if pygame.mixer.get_init():
                pygame.mixer.quit()
        except Exception:
            pass
        _mixer_ready = False
