"""Writing the game's JSON files (the adventure logs, the save states and the autosave, the settings) so that a crash
or a full disk part way through never leaves one half written. Not NES.

The file is written to a temporary file next to it, flushed to the disk, and then moved over the old one in one step
(os.replace, which is atomic on every platform the game runs on): a reader finds either the old file, whole, or the
new one, whole.
"""
import json
import os
from contextlib import suppress
from typing import Any

# The temporary file is the file's own name with this added (a file the game's save folder listings ignore)
TEMPORARY_SUFFIX = '.tmp'


def atomic_write_json(path: str, value: Any, *, trailing_newline: bool = False, **dump_options: Any) -> None:
    """Write ``value`` as JSON (json.dumps with ``dump_options``, then a newline if ``trailing_newline``) to
    ``path``, replacing what was there in one step (see the module docstring), and make its folder if need be.
    Raises OSError if it can't be written; the old file, if there was one, is then left as it was."""
    folder = os.path.dirname(path) or '.'
    os.makedirs(folder, exist_ok=True)
    text = json.dumps(value, **dump_options) + ('\n' if trailing_newline else '')
    temporary_path = path + TEMPORARY_SUFFIX
    try:
        with open(temporary_path, 'w', encoding='utf-8') as temporary_file:
            temporary_file.write(text)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        with suppress(OSError):
            os.remove(temporary_path)
        raise
