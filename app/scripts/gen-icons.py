#!/usr/bin/env python3
"""Regenerate public/icons/*.png. Stdlib only (no PIL): hand-rolled PNG writer.

Design: dark olive field square with a faint map grid, a khaki trench zigzag
cutting across, and a signal-red position marker at the line's center peak.
"""
import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "public" / "icons"

DESK = (32, 36, 22)
GRID = (48, 53, 32)
PAPER = (217, 207, 173)
SIGNAL = (214, 75, 33)


def png(width, height, rows):
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def render(size, pad_frac=0.0):
    """pad_frac shrinks the artwork toward the center (maskable safe zone)."""
    pad = int(size * pad_frac)
    inner = size - 2 * pad
    grid_step = max(4, inner // 8)
    line_w = max(1, inner // 14)
    dot_r = max(2, inner // 9)
    amp = inner // 6
    cy = size // 2
    cx = size // 2
    period = max(4, inner // 3)

    def zig_y(x):
        # triangle wave centred on cy
        t = ((x - pad) % period) / period
        tri = 2 * abs(t - 0.5) - 0.5  # -0.5..0.5
        return cy + int(2 * amp * tri)

    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            color = DESK
            if pad <= x < size - pad and pad <= y < size - pad:
                if (x - pad) % grid_step == 0 or (y - pad) % grid_step == 0:
                    color = GRID
                zy = zig_y(x)
                if abs(y - zy) <= line_w:
                    color = PAPER
                dx, dy = x - cx, y - cy
                d2 = dx * dx + dy * dy
                if d2 <= dot_r * dot_r:
                    color = SIGNAL
                elif d2 <= (dot_r + max(1, line_w // 2)) ** 2:
                    color = PAPER
            row += bytes(color)
        rows.append(row)
    return png(size, size, rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for size in (16, 32, 48, 128, 192, 512):
        (OUT / f"icon-{size}.png").write_bytes(render(size))
        print(f"icon-{size}.png")
    (OUT / "icon-maskable-512.png").write_bytes(render(512, pad_frac=0.18))
    print("icon-maskable-512.png")


if __name__ == "__main__":
    main()
