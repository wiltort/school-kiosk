"""Тесты автозагрузки через ярлык в папке Startup (src/apps/admin/autostart.py)."""

from src.apps.admin import autostart


def test_not_supported_on_non_windows(monkeypatch):
    monkeypatch.setattr(autostart.sys, "platform", "linux")
    monkeypatch.setenv("SCHOOL_KIOSK_APP_EXE", "C:/kiosk.exe")

    assert autostart.is_supported() is False
    assert autostart.is_enabled() is False
    assert autostart.set_enabled(True) is False


def test_creates_and_removes_shortcut_on_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(autostart.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("SCHOOL_KIOSK_APP_EXE", r"C:\Program Files\Kiosk\kiosk.exe")

    captured: dict = {}

    class _FakeCompleted:
        returncode = 0
        stderr = ""

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        captured["cmd"] = cmd
        return _FakeCompleted()

    monkeypatch.setattr(autostart.subprocess, "run", _fake_run)
    # `shutil.which` on a non-Windows host with sys.platform mocked to win32
    # crashes in Python 3.14 (`_winapi` is None on Linux), so stub it too.
    monkeypatch.setattr(autostart.shutil, "which", lambda _name: "powershell.exe")

    assert autostart.is_supported() is True
    assert autostart.set_enabled(True) is True

    # Команда создаёт ярлык через штатный WScript.Shell с нужным TargetPath.
    cmd = captured.get("cmd") or []
    joined = " ".join(cmd)
    assert "CreateShortcut" in joined
    assert "kiosk.exe" in joined

    # is_enabled зависит от фактического наличия файла ярлыка.
    shortcut = autostart._shortcut_path()
    assert shortcut is not None
    assert autostart.is_enabled() is False

    shortcut.parent.mkdir(parents=True, exist_ok=True)
    shortcut.touch()
    assert autostart.is_enabled() is True

    # Отключение удаляет ярлык.
    assert autostart.set_enabled(False) is True
    assert autostart.is_enabled() is False
