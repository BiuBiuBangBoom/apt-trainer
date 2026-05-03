"""ANSI color helpers."""

RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
WHITE = "\033[37m"


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
