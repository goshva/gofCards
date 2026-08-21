from __future__ import annotations

import hashlib
import re

# GoFuture ships no team badges at all, so a stable crest is generated per club.
# Everything is derived from the team external id, which means the same club
# always gets the same crest and it never depends on row order or sync time.

PALETTE: list[tuple[str, str]] = [
    ("#1e3a8a", "#60a5fa"),
    ("#7f1d1d", "#f87171"),
    ("#14532d", "#4ade80"),
    ("#78350f", "#fbbf24"),
    ("#4c1d95", "#c084fc"),
    ("#134e4a", "#2dd4bf"),
    ("#831843", "#f472b6"),
    ("#1e293b", "#94a3b8"),
    ("#3f2d0c", "#eab308"),
    ("#0c4a6e", "#38bdf8"),
    ("#3b0764", "#a855f7"),
    ("#064e3b", "#34d399"),
    ("#7c2d12", "#fb923c"),
    ("#172554", "#818cf8"),
    ("#4a044e", "#e879f9"),
    ("#365314", "#a3e635"),
]

STYLES = ("bend", "pale", "chevron", "fess")


def monogram(title: str) -> str:
    words = [w for w in re.split(r"[^0-9A-Za-zА-Яа-яЁё]+", title or "") if w]
    if not words:
        return "FC"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def _digest(external_id: str) -> bytes:
    return hashlib.sha256(external_id.encode()).digest()


def crest_svg(title: str, external_id: str) -> str:
    """A shield crest: two-tone charge, monogram, founding-style star row."""
    digest = _digest(external_id)
    dark, light = PALETTE[digest[0] % len(PALETTE)]
    style = STYLES[digest[1] % len(STYLES)]
    stars = 1 + digest[2] % 3
    letters = monogram(title)

    charges = {
        "bend": f'<path d="M8 118 L118 8 L118 52 L52 118 Z" fill="{light}" opacity="0.9"/>',
        "pale": f'<rect x="49" y="6" width="30" height="112" fill="{light}" opacity="0.9"/>',
        "chevron": f'<path d="M64 30 L118 74 L118 104 L64 60 L10 104 L10 74 Z" fill="{light}" opacity="0.9"/>',
        "fess": f'<rect x="6" y="48" width="116" height="30" fill="{light}" opacity="0.9"/>',
    }

    star_row = ""
    if stars:
        step = 15
        start = 64 - (stars - 1) * step / 2
        star_row = "".join(
            f'<circle cx="{start + i * step:.1f}" cy="104" r="3.2" fill="#ffffff" opacity="0.85"/>'
            for i in range(stars)
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 136" width="128" height="136" role="img" aria-label="{title}">
  <defs>
    <clipPath id="shield">
      <path d="M64 2 L124 20 V70 C124 104 96 124 64 134 C32 124 4 104 4 70 V20 Z"/>
    </clipPath>
    <linearGradient id="sheen" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.18"/>
      <stop offset="60%" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <g clip-path="url(#shield)">
    <rect width="128" height="136" fill="{dark}"/>
    {charges[style]}
    <rect width="128" height="136" fill="url(#sheen)"/>
  </g>
  <path d="M64 2 L124 20 V70 C124 104 96 124 64 134 C32 124 4 104 4 70 V20 Z"
        fill="none" stroke="#f8fafc" stroke-opacity="0.75" stroke-width="3"/>
  <text x="64" y="80" text-anchor="middle" font-family="Inter, Segoe UI, Arial, sans-serif"
        font-size="42" font-weight="800" fill="#f8fafc"
        style="paint-order:stroke" stroke="{dark}" stroke-width="4">{letters}</text>
  {star_row}
</svg>
"""


def crest_color(external_id: str) -> str:
    """Accent colour of the crest, reused by the UI for club labels."""
    return PALETTE[_digest(external_id)[0] % len(PALETTE)][1]
