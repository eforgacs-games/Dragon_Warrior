"""
The tests run headless: SDL's dummy drivers stand in for the window and the audio device.

This is set here rather than in a conftest.py so it also applies when the tests are run without pytest (e.g.
`python -m unittest` or an IDE's unittest runner): both import this package before any test module.
"""
import os

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
