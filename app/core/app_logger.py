import datetime
import sys
import traceback
from pathlib import Path


def get_log_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


LOG_FILE = get_log_dir() / "app.log"


def log_error(message, exc=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"[{timestamp}] {message}"]
    if exc is not None:
        lines.extend(traceback.format_exception(type(exc), exc, exc.__traceback__))

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("\n".join(line.rstrip() for line in lines))
            f.write("\n\n")
    except OSError:
        pass
