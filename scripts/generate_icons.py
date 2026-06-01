"""
Generates minimal PNG icons for the PWA using only Python stdlib.
Run once: python scripts/generate_icons.py
"""

import struct
import zlib
from pathlib import Path

ICONS_DIR = Path(__file__).parent.parent / "docs" / "icons"


def make_png(width, height, r, g, b):
    """Create a solid-colour RGB PNG using only struct + zlib."""
    def chunk(tag, data):
        c = tag + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)

    sig  = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))

    raw = b''
    row = bytes([r, g, b] * width)
    for _ in range(height):
        raw += b'\x00' + row   # filter type: None

    idat = chunk(b'IDAT', zlib.compress(raw, 9))
    iend = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend


def run():
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    # Theme colour #0f172a → 15, 23, 42
    bg = (15, 23, 42)

    sizes = [
        ("apple-touch-icon.png", 180),
        ("icon-192.png",         192),
        ("icon-512.png",         512),
    ]

    for filename, size in sizes:
        path = ICONS_DIR / filename
        path.write_bytes(make_png(size, size, *bg))
        print(f"Written {path} ({size}×{size})")


if __name__ == "__main__":
    run()
