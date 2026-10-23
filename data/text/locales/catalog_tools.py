"""Keep the Korean gettext catalog in step with the game's text, without needing GNU gettext installed.

    uv run --frozen python data/text/locales/catalog_tools.py missing   # list untranslated messages
    uv run --frozen python data/text/locales/catalog_tools.py add       # append them to the .po with empty msgstr

Messages are found the way xgettext would find them: the first argument of every _("...") or self._("...") call in
src/ and data/. Some text is translated through a variable (_(item_name), self._(enemy.name)), so item, spell and
enemy names are added from the game's own tables. tests/test_translations.py fails when any of these has no Korean
translation.

There's no compile step: the game reads base.po and compiles it in memory when it runs (src/catalog.py).
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:  # run as a script, only data/text/locales is on the path
    sys.path.insert(0, str(ROOT))

from src import catalog  # noqa: E402

LOCALES_DIR = Path(__file__).resolve().parent
KOREAN_PO = LOCALES_DIR / 'ko' / 'LC_MESSAGES' / 'base.po'
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
    "Debug keys:": "debug key",  # the title of the H help page that lists them
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
    that are drawn translated (src/translated_window.py), the options screen's and the options overlay's text, the
    shop stat preview's labels and the dungeon map's text."""
    from src.dungeon_map import overlay_texts as dungeon_map_texts
    from src.enemy_lookup import enemy_string_lookup
    from src.items import armor, shields, tools, weapons
    from src.controls_screen import screen_texts
    from src.message_log import screen_texts as log_texts
    from src.options_overlay import overlay_texts
    from src.options_screen import MESSAGE_SPEED_OPTIONS
    from src.shop_preview import preview_texts
    from src.quest_journal import journal_texts
    from src.spells import Spell
    from src.translated_window import layout_texts
    from src.windows import COMBAT_COMMAND_LAYOUT, COMMAND_LAYOUT, STATUS_LAYOUT, TITLE_MENU_LAYOUTS, \
        TITLE_MENU_LAYOUTS_WITH_AUTOSAVE, YES_NO_LAYOUT

    messages: dict[str, list[str]] = {}
    for source, table in (('src/items.py', weapons), ('src/items.py', armor), ('src/items.py', shields),
                          ('src/items.py', tools), ('src/enemy_lookup.py', enemy_string_lookup)):
        for name in table:
            messages.setdefault(name, []).append(source)
    for spell in Spell:
        if spell.value not in UNNAMED_SPELLS:
            messages.setdefault(spell.value, []).append('src/spells.py')
    for layout in (COMMAND_LAYOUT, COMBAT_COMMAND_LAYOUT, STATUS_LAYOUT, YES_NO_LAYOUT, *TITLE_MENU_LAYOUTS,
                   *TITLE_MENU_LAYOUTS_WITH_AUTOSAVE):
        for text in layout_texts(layout):
            if 'src/windows.py' not in messages.get(text.text, []):
                messages.setdefault(text.text, []).append('src/windows.py')
    for text in [prompt[2] for prompt in MESSAGE_SPEED_OPTIONS.prompt] + list(MESSAGE_SPEED_OPTIONS.labels):
        messages.setdefault(text, []).append('src/options_screen.py')
    for text in overlay_texts():
        if 'src/options_overlay.py' not in messages.get(text, []):
            messages.setdefault(text, []).append('src/options_overlay.py')
    for text in preview_texts():
        messages.setdefault(text, []).append('src/shop_preview.py')
    for text in journal_texts():
        messages.setdefault(text, []).append('src/quest_journal.py')
    for text in dungeon_map_texts():
        messages.setdefault(text, []).append('src/dungeon_map.py')
    for text in screen_texts():
        if 'src/controls_screen.py' not in messages.get(text, []):
            messages.setdefault(text, []).append('src/controls_screen.py')
    for text in log_texts():
        if 'src/message_log.py' not in messages.get(text, []):
            messages.setdefault(text, []).append('src/message_log.py')
    return messages


def extract_messages(root: Path = ROOT) -> dict[str, list[str]]:
    messages = extract_literal_messages(root)
    for msgid, locations in dynamic_messages().items():
        messages.setdefault(msgid, []).extend(locations)
    return messages


# .po reading and writing

def read_po(path: Path = KOREAN_PO) -> dict[str, str]:
    """msgid -> msgstr for every (non-obsolete) entry, header included under the empty msgid."""
    return catalog.read_po(path)


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
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
