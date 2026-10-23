"""
The game's translations, read straight from the gettext .po files in data/text/locales.

The compiled .mo catalogs aren't kept in the repository (a binary file that every new line of text changes, so any two
pull requests that add text conflict on it). Instead, each .po is compiled to .mo bytes in memory the first time its
language is used, and kept for the rest of the run. Nothing is written to disk, so this works the same from source and
from a read-only PyInstaller build.

Only plain msgid/msgstr entries are supported: the catalogs have no msgctxt or msgid_plural.
"""
import ast
import gettext
import io
import struct
from functools import cache
from pathlib import Path

from src.paths import data_path

GETTEXT_DOMAIN = 'base'
MO_MAGIC = 0x950412de
MO_HEADER_SIZE = 7 * 4
MO_TABLE_ENTRY_SIZE = 2 * 4  # (length, offset) of one string


def po_path(language_code: str) -> Path:
    """The .po file of a language, e.g. data/text/locales/ko/LC_MESSAGES/base.po for 'ko'."""
    return Path(data_path('text', 'locales', language_code, 'LC_MESSAGES', f'{GETTEXT_DOMAIN}.po'))


def _unquote(line: str) -> str:
    line = line.strip()
    if not (line.startswith('"') and line.endswith('"')):
        raise ValueError(f"expected a quoted string: {line!r}")
    return ast.literal_eval(line)


def read_po(path: Path) -> dict[str, str]:
    """msgid -> msgstr for every (non-obsolete) entry, header included under the empty msgid."""
    catalog: dict[str, str] = {}
    msgid: str | None = None
    msgstr: str | None = None
    current = None

    def flush():
        if msgid is not None and msgstr is not None:
            catalog[msgid] = msgstr

    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('msgid '):
            flush()
            msgid, msgstr, current = _unquote(line[len('msgid '):]), None, 'msgid'
        elif line.startswith('msgstr '):
            msgstr, current = _unquote(line[len('msgstr '):]), 'msgstr'
        elif line.startswith('"'):
            if current == 'msgid' and msgid is not None:
                msgid += _unquote(line)
            elif current == 'msgstr' and msgstr is not None:
                msgstr += _unquote(line)
        else:
            raise ValueError(f"{path}: can't parse line: {raw_line!r}")
    flush()
    return catalog


def mo_bytes(catalog: dict[str, str]) -> bytes:
    """The catalog in the GNU .mo format (as msgfmt writes it), without the optional hash table. Untranslated
    entries (an empty msgstr) are left out, so gettext falls back to the English msgid for them."""
    entries = sorted((msgid.encode('utf-8'), msgstr.encode('utf-8'))
                     for msgid, msgstr in catalog.items() if msgstr)
    ids_table_start = MO_HEADER_SIZE
    strs_table_start = ids_table_start + MO_TABLE_ENTRY_SIZE * len(entries)
    ids_start = strs_table_start + MO_TABLE_ENTRY_SIZE * len(entries)
    ids = b''.join(msgid + b'\0' for msgid, _ in entries)
    strs_start = ids_start + len(ids)
    strs = b''.join(msgstr + b'\0' for _, msgstr in entries)

    header = struct.pack('7I', MO_MAGIC, 0, len(entries), ids_table_start, strs_table_start, 0, 0)
    ids_table = _string_table([msgid for msgid, _ in entries], ids_start)
    strs_table = _string_table([msgstr for _, msgstr in entries], strs_start)
    return header + ids_table + strs_table + ids + strs


def _string_table(strings: list[bytes], start: int) -> bytes:
    """(length, offset) of each string, stored one after another (each followed by a NUL) from start."""
    table = b''
    offset = start
    for string in strings:
        table += struct.pack('2I', len(string), offset)
        offset += len(string) + 1
    return table


def compile_po(path: Path) -> gettext.GNUTranslations:
    """Translations compiled from a .po file in memory."""
    return gettext.GNUTranslations(io.BytesIO(mo_bytes(read_po(path))))


@cache
def load_translations(language_code: str) -> gettext.GNUTranslations:
    """The language's translations, compiled from its .po on first use and cached for the rest of the run."""
    return compile_po(po_path(language_code))
