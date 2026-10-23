# PyInstaller spec for the release builds (.github/workflows/release.yml). From the repository root:
#     uv sync --group build
#     uv run pyinstaller dragon_warrior.spec --noconfirm
# builds dist/DragonWarrior/ (a folder with the DragonWarrior executable), and on macOS also dist/Dragon Warrior.app.
# Check a build with `dist/DragonWarrior/DragonWarrior --smoke-test --language English` (and `--language Korean`),
# headless with SDL_VIDEODRIVER=dummy and SDL_AUDIODRIVER=dummy (see src/smoke_test.py).
#
# The game finds data/ through src/paths.py, which uses sys._MEIPASS in a build, so the files are bundled at the same
# paths relative to it as in the repository. Saves go to a per-user folder in a build (src/paths.py default_save_dir).
import sys
from glob import glob
from os.path import dirname, join

ROOT = SPECPATH  # noqa: F821 - PyInstaller defines SPECPATH, the folder this file is in
NAME = 'DragonWarrior'

datas = [
    (join(ROOT, 'data', folder), join('data', folder))
    for folder in ('checkpoints', 'fonts', 'images', 'sound')
]
# The translations (the game compiles each .po in memory, src/catalog.py); the .pot and the catalog tools stay out
for po_file in glob(join(ROOT, 'data', 'text', 'locales', '*', 'LC_MESSAGES', '*.po')):
    datas.append((po_file, dirname(po_file[len(ROOT):].lstrip('/\\'))))

a = Analysis(  # noqa: F821
    [join(ROOT, 'src', 'game.py')],
    # src.* and data.text.* are imported from the repository root (src/game.py adds it to sys.path)
    pathex=[ROOT],
    datas=datas,
    # Not used by the game (pygame only imports numpy for surfarray and sndarray)
    excludes=['tkinter', 'numpy'],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    debug=False,
    strip=False,
    upx=False,
    # A console program, so --smoke-test can print and a crash shows a traceback rather than a dialog. On Windows,
    # hide-early hides the console the program opens when started from Explorer; one it was started from stays.
    # On macOS the .app below is windowed.
    console=sys.platform != 'darwin',
    hide_console='hide-early' if sys.platform == 'win32' else None,
)
coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=NAME,
)

if sys.platform == 'darwin':
    app = BUNDLE(  # noqa: F821
        coll,
        name='Dragon Warrior.app',
        bundle_identifier='io.github.eforgacs-games.dragon-warrior',
        info_plist={'NSHighResolutionCapable': True},
    )
