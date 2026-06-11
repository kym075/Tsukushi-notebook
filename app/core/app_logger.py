import datetime
import traceback

from app.core.paths import get_app_dir


LOG_FILE = get_app_dir() / "app.log"


def log_error(message, exc=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"[{timestamp}] {message}"]
    if exc is not None:
        lines.extend(traceback.format_exception(type(exc), exc, exc.__traceback__))

    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("\n".join(line.rstrip() for line in lines))
            f.write("\n\n")
    except OSError:
        pass
