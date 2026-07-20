from codex_usage_taskbar.startup import startup_command


def test_startup_command_quotes_paths_with_spaces():
    assert startup_command(r"C:\Program Files\Codex Usage\CodexUsageTaskbar.exe") == r'"C:\Program Files\Codex Usage\CodexUsageTaskbar.exe"'

