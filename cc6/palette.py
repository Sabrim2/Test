# ui/palette.py
"""
Single source of truth for colours and fonts.

VS Code "Dark+" style greys with purple accents.
Change a value here and the whole app follows.
"""

# ---------------- surfaces ----------------
BG          = "#1e1e1e"   # editor background / page background
SURFACE     = "#252526"   # cards, table body
SURFACE_ALT = "#2d2d30"   # inputs, headers, hovered surfaces
SIDEBAR     = "#202021"   # activity bar
BORDER      = "#3c3c3c"   # visible dividers
BORDER_SOFT = "#2f2f33"   # grid lines

# ---------------- text ----------------
FG          = "#d4d4d4"
FG_STRONG   = "#f2f2f2"
FG_MUTED    = "#8b8b93"
FG_DISABLED = "#5a5a60"

# ---------------- accent (purple) ----------------
ACCENT       = "#8A5CF6"
ACCENT_HOVER = "#A47BFF"
ACCENT_DIM   = "#5b3ea8"
ACCENT_SOFT  = "#33294a"   # selection tint
ACCENT_TEXT  = "#c9b6f5"

# ---------------- table ----------------
GROUP_BG   = "#1b1b22"
GROUP_FG   = ACCENT_TEXT
HEADER_BG  = "#2d2d30"
HEADER_FG  = "#e6e6e6"
ROW_EVEN   = "#1e1e1e"
ROW_ILL    = "#232326"   # "odd" / banded row
GRID_LINE  = BORDER_SOFT
SELECT_BG  = ACCENT_SOFT
SELECT_BD  = ACCENT_HOVER
FOCUS_BD   = "#d3bcff"

# ---------------- issue highlights ----------------
# Excel fill  ->  dark-theme background / foreground
ISSUE_BG = {
    "yellow": "#5c4a12",   # FFFF00  out of order sequence
    "red":    "#5e1f1f",   # FF0000  missing message
    "orange": "#66430f",   # FFA500  missing packetswitch data
}
ISSUE_FG = {
    "yellow": "#f2d98a",
    "red":    "#ff9d9d",
    "orange": "#ffc38a",
}
ISSUE_DOT = {              # bright swatch colours (legend / KPI bars)
    "yellow": "#e3c04a",
    "red":    "#e05c5c",
    "orange": "#e08b3c",
}

# ---------------- state colours ----------------
OK      = "#4ec9b0"
WARN    = "#e3c04a"
DANGER  = "#e05c5c"

# ---------------- fonts ----------------
FONT        = ("Segoe UI", 9)
FONT_BOLD   = ("Segoe UI", 9, "bold")
FONT_SMALL  = ("Segoe UI", 8)
FONT_TITLE  = ("Segoe UI", 16, "bold")
FONT_KPI    = ("Segoe UI", 17, "bold")
FONT_MONO   = ("Consolas", 9)

# ---------------- metrics ----------------
ROW_H     = 22
GROUP_H   = 24
COL_H     = 26
