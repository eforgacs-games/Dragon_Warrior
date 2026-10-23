"""Keep the Korean gettext catalog in step with the game's text, without needing GNU gettext installed.

    uv run --frozen python data/text/locales/catalog_tools.py missing   # list untranslated messages
    uv run --frozen python data/text/locales/catalog_tools.py add       # append them to the .po with empty msgstr
    uv run --frozen python data/text/locales/catalog_tools.py compile   # rebuild base.mo from base.po

Messages are found the way xgettext would find them: the first argument of every _("...") or self._("...") call in
src/ and data/. Some text is translated through a variable (_(item_name), self._(enemy.name)), so item, spell and
enemy names are added from the game's own tables. tests/test_translations.py fails when any of these has no Korean
translation, or when base.mo is out of date.
"""
import ast
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOCALES_DIR = Path(__file__).resolve().parent
KOREAN_PO = LOCALES_DIR / 'ko' / 'LC_MESSAGES' / 'base.po'
KOREAN_MO = LOCALES_DIR / 'ko' / 'LC_MESSAGES' / 'base.mo'
SOURCE_DIRS = ('src', 'data')

# Enemy spells that are never named on screen (the breath attacks print their own line)
UNNAMED_SPELLS = ('FIREBREATH', 'FIREBREATH2', 'ATTACK')

# Messages that are deliberately left untranslated, and why. Keep this short: anything a player sees in normal play
# should be translated.
ENGLISH_ONLY = {
    # Dev config only (DEBUG_KEYS): these keys open the English-only debug tools in src/debug_tools.py
    "F5: Warp": "debug key",
    "F6: Give item/gold/level": "debug key",
    "F7: Load checkpoint": "debug key",
    "Debug keys:": "debug key",  # the title of the F1 help page that lists them
}


def _is_gettext_call(node: ast.Call) -> bool:
    func = node.func
    return (isinstance(func, ast.Name) and func.id == '_') or (isinstance(func, ast.Attribute) and func.attr == '_')


def source_files(root: Path = ROOT):
    for directory in SOURCE_DIRS:
        yield from sorted((root / directory).rglob('*.py'))


def gettext_calls(root: Path = ROOT):
    """Yield (location, first argument node) for every _() / self._() call in the game's source."""
    for path in source_files(root):
        tree = ast.parse(path.read_text(encoding='utf-8'), str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and node.args and _is_gettext_call(node):
                yield f"{path.relative_to(root)}:{node.lineno}", node.args[0]


def extract_literal_messages(root: Path = ROOT) -> dict[str, list[str]]:
    """msgid -> source locations, for every _() call whose argument is a string literal."""
    messages: dict[str, list[str]] = {}
    for location, argument in gettext_calls(root):
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str) and argument.value:
            messages.setdefault(argument.value, []).append(location)
    return messages


def unextractable_gettext_calls(root: Path = ROOT) -> list[str]:
    """_() calls that gettext can never match: an f-string, or a string that is formatted before it's translated
    (the placeholders have to stay in the msgid, with .format() called on the translation)."""
    problems = []
    for location, argument in gettext_calls(root):
        if isinstance(argument, ast.JoinedStr):
            problems.append(f"{location}: f-string inside _()")
        elif isinstance(argument, ast.Call) and isinstance(argument.func, ast.Attribute) and \
                argument.func.attr == 'format' and isinstance(argument.func.value, ast.Constant):
            problems.append(f"{location}: .format() inside _()")
    return problems


def dynamic_messages() -> dict[str, list[str]]:
    """Text that reaches _() through a variable: item, spell and enemy names, the text of the generated windows
    that are drawn translated (src/translated_window.py) and the options screen's text."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.enemy_lookup import enemy_string_lookup
    from src.items import armor, shields, tools, weapons
    from src.options_screen import DIALOG_STYLE_OPTIONS, MESSAGE_SPEED_OPTIONS, NPCS_MAKE_WAY_OPTIONS
    from src.spells import Spell
    from src.translated_window import layout_texts
    from src.windows import COMBAT_COMMAND_LAYOUT, COMMAND_LAYOUT, STATUS_LAYOUT, TITLE_MENU_LAYOUTS, YES_NO_LAYOUT

    messages: dict[str, list[str]] = {}
    for source, table in (('src/items.py', weapons), ('src/items.py', armor), ('src/items.py', shields),
                          ('src/items.py', tools), ('src/enemy_lookup.py', enemy_string_lookup)):
        for name in table:
            messages.setdefault(name, []).append(source)
    for spell in Spell:
        if spell.value not in UNNAMED_SPELLS:
            messages.setdefault(spell.value, []).append('src/spells.py')
    for layout in (COMMAND_LAYOUT, COMBAT_COMMAND_LAYOUT, STATUS_LAYOUT, YES_NO_LAYOUT, *TITLE_MENU_LAYOUTS):
        for text in layout_texts(layout):
            if 'src/windows.py' not in messages.get(text.text, []):
                messages.setdefault(text.text, []).append('src/windows.py')
    for options in (MESSAGE_SPEED_OPTIONS, DIALOG_STYLE_OPTIONS, NPCS_MAKE_WAY_OPTIONS):
        for text in [prompt[2] for prompt in options.prompt] + list(options.labels):
            messages.setdefault(text, []).append('src/options_screen.py')
    return messages


def extract_messages(root: Path = ROOT) -> dict[str, list[str]]:
    messages = extract_literal_messages(root)
    for msgid, locations in dynamic_messages().items():
        messages.setdefault(msgid, []).extend(locations)
    return messages


# .po reading and writing

def _unquote(line: str) -> str:
    line = line.strip()
    assert line.startswith('"') and line.endswith('"'), line
    return ast.literal_eval(line)


def read_po(path: Path = KOREAN_PO) -> dict[str, str]:
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


def _po_string(keyword: str, text: str) -> str:
    def quote(part: str) -> str:
        return '"' + part.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t') + '"'

    parts = text.splitlines(keepends=True)
    if len(parts) <= 1:
        return f"{keyword} {quote(text)}\n"
    return f'{keyword} ""\n' + ''.join(quote(part) + '\n' for part in parts)


def po_entry(msgid: str, msgstr: str = '', locations: list[str] | None = None) -> str:
    references = ''.join(f"#: {location}\n" for location in locations or ())
    return references + _po_string('msgid', msgid) + _po_string('msgstr', msgstr)


def missing_translations(catalog: dict[str, str] | None = None, root: Path = ROOT) -> dict[str, list[str]]:
    catalog = read_po() if catalog is None else catalog
    return {msgid: locations for msgid, locations in extract_messages(root).items()
            if not catalog.get(msgid) and msgid not in ENGLISH_ONLY}


def add_missing_entries(path: Path = KOREAN_PO) -> list[str]:
    """Append an empty entry for every extracted message the .po doesn't have yet. Returns the msgids added."""
    catalog = read_po(path)
    new = {msgid: locations for msgid, locations in extract_messages().items()
           if msgid not in catalog and msgid not in ENGLISH_ONLY}
    if new:
        text = path.read_text(encoding='utf-8').rstrip('\n') + '\n'
        text += ''.join('\n' + po_entry(msgid, '', locations[:3]) for msgid, locations in new.items())
        path.write_text(text, encoding='utf-8')
    return list(new)


# .mo compiling (the GNU format, as written by msgfmt and Python's Tools/i18n/msgfmt.py)

def mo_bytes(catalog: dict[str, str]) -> bytes:
    entries = sorted((msgid.encode('utf-8'), msgstr.encode('utf-8')) for msgid, msgstr in catalog.items()
                     if msgstr)
    ids = b''
    strs = b''
    offsets = []
    for msgid, msgstr in entries:
        offsets.append((len(ids), len(msgid), len(strs), len(msgstr)))
        ids += msgid + b'\0'
        strs += msgstr + b'\0'
    key_start = 7 * 4 + 16 * len(entries)
    value_start = key_start + len(ids)
    key_offsets: list[int] = []
    value_offsets: list[int] = []
    for id_offset, id_length, str_offset, str_length in offsets:
        key_offsets += [id_length, id_offset + key_start]
        value_offsets += [str_length, str_offset + value_start]
    header = struct.pack('Iiiiiii', 0x950412de, 0, len(entries), 7 * 4, 7 * 4 + len(entries) * 8, 0, 0)
    return header + struct.pack(f'{len(key_offsets)}i', *key_offsets) + \
        struct.pack(f'{len(value_offsets)}i', *value_offsets) + ids + strs


def compile_mo(po_path: Path = KOREAN_PO, mo_path: Path = KOREAN_MO) -> None:
    mo_path.write_bytes(mo_bytes(read_po(po_path)))


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else 'missing'
    if command == 'missing':
        missing = missing_translations()
        for msgid, locations in missing.items():
            print(po_entry(msgid, '', locations))
        print(f"{len(missing)} message(s) without a Korean translation", file=sys.stderr)
        return 1 if missing else 0
    if command == 'add':
        added = add_missing_entries()
        print(f"Added {len(added)} empty entr{'y' if len(added) == 1 else 'ies'} to {KOREAN_PO.relative_to(ROOT)}")
        return 0
    if command == 'compile':
        compile_mo()
        print(f"Wrote {KOREAN_MO.relative_to(ROOT)}")
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
