"""ANSI color helpers, box-drawing characters, and formatting utilities."""

import re

# ---- ANSI codes ----

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
WHITE = "\033[37m"

# Semantic color aliases
C_HEADER = CYAN
C_SUCCESS = GREEN
C_ERROR = RED
C_WARNING = YELLOW
C_ACCENT = MAGENTA
C_INFO = BLUE
C_BORDER = CYAN

# ---- Box-drawing characters ----

# Double-line (top-level containers: menus, stats)
D_TL, D_TR, D_BL, D_BR = "╔", "╗", "╚", "╝"
D_H, D_V = "═", "║"
D_LJ, D_RJ = "╠", "╣"
D_TJ, D_BJ = "╦", "╩"

# Single-line (question/result panels)
S_TL, S_TR, S_BL, S_BR = "┌", "┐", "└", "┘"
S_H, S_V = "─", "│"
S_LJ, S_RJ = "├", "┤"

# ---- Symbols ----

CHECK = "✓"
CROSS = "✗"
ARROW = "▶"
CLOCK = "⏱"

# ---- Constants ----

WIDTH = 50

# ---- Color helpers ----

def green_str(s: str) -> str:
    return f"{GREEN}{s}{RESET}"

def red_str(s: str) -> str:
    return f"{RED}{s}{RESET}"

def yellow_str(s: str) -> str:
    return f"{YELLOW}{s}{RESET}"

def cyan_str(s: str) -> str:
    return f"{CYAN}{s}{RESET}"

def magenta_str(s: str) -> str:
    return f"{MAGENTA}{s}{RESET}"

def blue_str(s: str) -> str:
    return f"{BLUE}{s}{RESET}"

def bold(s: str) -> str:
    return f"{BOLD}{s}{RESET}"

def dim(s: str) -> str:
    return f"{DIM}{s}{RESET}"

# Semantic wrappers

def c_header(s: str) -> str:
    return f"{C_HEADER}{s}{RESET}"

def c_success(s: str) -> str:
    return f"{C_SUCCESS}{s}{RESET}"

def c_error(s: str) -> str:
    return f"{C_ERROR}{s}{RESET}"

def c_warning(s: str) -> str:
    return f"{C_WARNING}{s}{RESET}"

def c_accent(s: str) -> str:
    return f"{C_ACCENT}{s}{RESET}"

def c_info(s: str) -> str:
    return f"{C_INFO}{s}{RESET}"

def c_border(s: str) -> str:
    return f"{C_BORDER}{s}{RESET}"

def c_dim(s: str) -> str:
    return f"{DIM}{s}{RESET}"

# ---- Display width (CJK-aware) ----

def display_width(s: str) -> int:
    stripped = re.sub(r"\033\[[0-9;]*m", "", s)
    w = 0
    for ch in stripped:
        cp = ord(ch)
        if (0x4E00 <= cp <= 0x9FFF or
                0x3000 <= cp <= 0x303F or
                0xFF00 <= cp <= 0xFFEF):
            w += 2
        else:
            w += 1
    return w

# ---- Box drawing ----

def box_top(title: str = "", width: int = WIDTH, style: str = "double") -> str:
    if style == "double":
        tl, h, tr = D_TL, D_H, D_TR
    else:
        tl, h, tr = S_TL, S_H, S_TR
    if not title:
        return c_border(f"{tl}{h * (width - 2)}{tr}")
    inner = width - 4
    title_visible = display_width(f" {title} ")
    left = max(0, (inner - title_visible) // 2)
    right = max(0, inner - title_visible - left)
    return c_border(f"{tl}{h * left} {title} {h * right}{tr}")

def box_bottom(width: int = WIDTH, style: str = "double") -> str:
    if style == "double":
        bl, h, br = D_BL, D_H, D_BR
    else:
        bl, h, br = S_BL, S_H, S_BR
    return c_border(f"{bl}{h * (width - 2)}{br}")

def box_sep(width: int = WIDTH, style: str = "double") -> str:
    if style == "double":
        lj, h, rj = D_LJ, D_H, D_RJ
    else:
        lj, h, rj = S_LJ, S_H, S_RJ
    return c_border(f"{lj}{h * (width - 2)}{rj}")

def box_line(content: str = "", width: int = WIDTH, align: str = "left",
             style: str = "double") -> str:
    v = D_V if style == "double" else S_V
    inner = width - 4
    vlen = display_width(content)
    if vlen > inner:
        content = _truncate_width(content, inner)
        vlen = inner
    if align == "center":
        left = max(0, (inner - vlen) // 2)
        right = max(0, inner - vlen - left)
        padded = f"{' ' * left}{content}{' ' * right}"
    elif align == "right":
        padded = f"{' ' * (inner - vlen)}{content}"
    else:
        padded = f"{content}{' ' * (inner - vlen)}"
    return f"{c_border(v)} {padded} {c_border(v)}"


def _truncate_width(s: str, max_width: int) -> str:
    """Truncate string to fit within max_width display width (CJK-aware)."""
    result = ""
    w = 0
    for ch in re.sub(r"\033\[[0-9;]*m", "", s):
        cp = ord(ch)
        ch_w = 2 if (0x4E00 <= cp <= 0x9FFF or
                      0x3000 <= cp <= 0x303F or
                      0xFF00 <= cp <= 0xFFEF) else 1
        if w + ch_w > max_width:
            break
        result += ch
        w += ch_w
    return result


def wrap_text(text: str, max_width: int) -> list[str]:
    """Wrap text into lines that fit within max_width display width (CJK-aware)."""
    lines: list[str] = []
    current = ""
    cur_w = 0

    for ch in text:
        if ch == "\n":
            lines.append(current)
            current = ""
            cur_w = 0
            continue
        cp = ord(ch)
        ch_w = 2 if (0x4E00 <= cp <= 0x9FFF or
                      0x3000 <= cp <= 0x303F or
                      0xFF00 <= cp <= 0xFFEF) else 1
        if cur_w + ch_w > max_width:
            lines.append(current)
            current = ch
            cur_w = ch_w
        else:
            current += ch
            cur_w += ch_w

    if current:
        lines.append(current)
    return lines if lines else [""]

# ---- Content formatting ----

def fmt_time_ms(ms: int) -> str:
    if ms < 1000:
        return f"{ms}ms"
    return f"{ms / 1000:.2f}s"

def colored_time_ms(ms: int) -> str:
    s = ms / 1000
    if s < 3:
        return c_success(f"{s:.2f}s")
    elif s < 10:
        return c_warning(f"{s:.2f}s")
    return c_error(f"{s:.2f}s")

def colored_accuracy(acc: float) -> str:
    pct = f"{acc * 100:.1f}%"
    if acc >= 0.85:
        return c_success(pct)
    elif acc >= 0.7:
        return c_warning(pct)
    return c_error(pct)

def success_mark() -> str:
    return c_success(f"  {CHECK} 正确")

def failure_mark(user_answer: str = "") -> str:
    base = c_error(f"  {CROSS} 错误")
    if user_answer:
        base += c_dim(f" (你的答案: {user_answer})")
    return base

def progress_tag(current: int, total: int) -> str:
    if total <= 0:
        return f"第{current}题"
    return f"[{current}/{total}]"
