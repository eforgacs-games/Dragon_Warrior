import glob
import os
import struct
from unittest import TestCase

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')


def png_chunk_types(path: str) -> list[bytes]:
    with open(path, 'rb') as png_file:
        data = png_file.read()
    chunk_types, position = [], 8  # skip the PNG signature
    while position < len(data):
        length, chunk_type = struct.unpack('>I4s', data[position:position + 8])
        chunk_types.append(chunk_type)
        if chunk_type == b'IEND':
            break
        position += 12 + length  # length, type, data, CRC
    return chunk_types


class TestPngAssets(TestCase):
    def test_no_png_carries_an_icc_colour_profile(self):
        # libpng prints "iCCP: known incorrect sRGB profile" every time such an image is loaded (the enemy sprites
        # did this at the start of every battle). The profile doesn't change the pixels, so assets shouldn't have one.
        paths = glob.glob(os.path.join(DATA_DIR, '**', '*.png'), recursive=True)
        self.assertTrue(paths)
        with_profile = [os.path.relpath(path, DATA_DIR) for path in paths if b'iCCP' in png_chunk_types(path)]
        self.assertEqual(with_profile, [])
