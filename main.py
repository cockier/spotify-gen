# language: Python 3.11+, file: main.py, target: Windows 11 — Spotify account generator
# *nodriver browser automation + regret.world temp mail — boot sequence mirrors token gen*
import asyncio
import itertools
import multiprocessing
import os
import random
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kit.colors import Color, Gradient
from kit.styles import Style, BorderStyle
from core.tempmail  import TempMailAPI
from core.generator import SpotifyGenerator
from core.premium   import PremiumApplicator, load_accounts, load_vccs
from core.utils     import load_config, load_proxies

import requests as _requests

ROOT        = Path(__file__).parent
CONFIG_PATH = ROOT / "config.json"
OUTPUT_PATH = ROOT / "output" / "accounts.txt"
SOLVER_EXT  = ROOT / "solver"
PROXY_PATH  = ROOT / "data" / "proxies.txt"
VCC_PATH    = ROOT / "data" / "vcc.txt"

# ── brand palette (matches token gen POISON) ─────────────────────────────────
POISON_GRAD   = [(18, 0, 45), (72, 0, 140), (140, 30, 240), (190, 80, 255)]
POISON_DARK   = [(10, 0, 28), (45, 0, 90),  (90, 0, 180)]
POISON_ACCENT = Color.rgb(190, 80,  255)
POISON_CYAN   = Color.rgb(110, 220, 255)
POISON_GREEN  = Color.rgb(50,  220, 100)
POISON_WARN   = Color.rgb(255, 160,  40)
POISON_ERR    = Color.rgb(255,  55,  80)
POISON_DIM    = Color.rgb(55,   35,  85)
POISON_BORDER = Color.rgb(75,   20, 140)
POISON_MID    = Color.rgb(140,  30, 240)
SP_GREEN      = Color.rgb(30,  215,  96)   # Spotify green accent
_R            = Color.RESET

# ── ASCII art ─────────────────────────────────────────────────────────────────
_SP_ASCII = [
    r"███████╗██████╗  ██████╗ ████████╗██╗███████╗██╗   ██╗",
    r"██╔════╝██╔══██╗██╔═══██╗╚══██╔══╝██║██╔════╝╚██╗ ██╔╝",
    r"███████╗██████╔╝██║   ██║   ██║   ██║█████╗   ╚████╔╝ ",
    r"╚════██║██╔═══╝ ██║   ██║   ██║   ██║██╔══╝    ╚██╔╝  ",
    r"███████║██║     ╚██████╔╝   ██║   ██║██║        ██║   ",
    r"╚══════╝╚═╝      ╚═════╝    ╚═╝   ╚═╝╚═╝        ╚═╝   ",
]

_SPINNER_FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

_lock    = Lock()
_stats   = {"success": 0, "fail": 0, "verified": 0}
_prem_stats = {"success": 0, "fail": 0}
_cfg_ref: dict = {}


# ── TUI helpers ───────────────────────────────────────────────────────────────
def _tw() -> int:
    return shutil.get_terminal_size().columns

def _center_raw(text: str, width: int = 0) -> str:
    w   = width or _tw()
    raw = re.sub(r"\033\[[0-9;]*m", "", text)
    pad = max(0, (w - len(raw)) // 2)
    return " " * pad + text

def _spin_ok(label: str, duration: float = 0.5):
    frames = itertools.cycle(_SPINNER_FRAMES)
    end_at = time.time() + duration
    while time.time() < end_at:
        f = next(frames)
        sys.stdout.write(
            f"\r  {POISON_MID}{f}{_R}  {POISON_DIM}{label}{_R}          "
        )
        sys.stdout.flush()
        time.sleep(0.055)
    sys.stdout.write(
        f"\r  {POISON_GREEN}✓{_R}  {Color.BRIGHT_WHITE}{label}{_R}          \n"
    )
    sys.stdout.flush()

def _type_line(text: str, delay: float = 0.012):
    parts = re.split(r"(\033\[[0-9;]*m)", text)
    for part in parts:
        if part.startswith("\033["):
            sys.stdout.write(part)
            sys.stdout.flush()
        else:
            for ch in part:
                sys.stdout.write(ch)
                sys.stdout.flush()
                time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()

def _prompt(text: str) -> str:
    return input(
        f"  {POISON_ACCENT}❯{_R}  {POISON_DIM}{text}{_R}  "
    ).strip()

def _kv(key: str, val: str, vc=None):
    vc = vc or Color.BRIGHT_WHITE
    print(f"  {POISON_MID}{key}{_R}  {POISON_DIM}→{_R}  {vc}{val}{_R}")


# ── boot sequence ─────────────────────────────────────────────────────────────
def boot_sequence():
    os.system("cls" if os.name == "nt" else "clear")
    tw = _tw()
    print()

    n = len(_SP_ASCII)
    for i, raw_line in enumerate(_SP_ASCII):
        t       = i / max(n - 1, 1)
        seg     = min(int(t * (len(POISON_GRAD) - 1)), len(POISON_GRAD) - 2)
        lt      = t * (len(POISON_GRAD) - 1) - seg
        sr, sg, sb = POISON_GRAD[seg]
        er, eg, eb = POISON_GRAD[seg + 1]
        cr = int(sr + lt * (er - sr))
        cg = int(sg + lt * (eg - sg))
        cb = int(sb + lt * (eb - sb))
        colored = f"{Color.rgb(cr, cg, cb)}{raw_line}{_R}"
        sys.stdout.write(_center_raw(colored, tw) + "\n")
        sys.stdout.flush()
        time.sleep(0.048)

    print()

    credits = (
        f"{POISON_DIM}spotify account generator  ·  "
        f"{POISON_ACCENT}github.com/cockier{_R}"
        f"{POISON_DIM}  ·  "
        f"{SP_GREEN}regret.world{_R}"
    )
    _type_line(_center_raw(credits, tw), delay=0.007)
    print()

    rule_w = min(tw, 70)
    rule_s = Color.multi_gradient("─" * rule_w, *POISON_GRAD)
    print(_center_raw(rule_s, tw))
    print()
    time.sleep(0.12)

    checks = [
        ("loading modules",              0.40),
        ("initialising browser engine",  0.52),
        ("connecting to mail services",  0.48),
        ("all systems ready",            0.32),
    ]
    for label, dur in checks:
        _spin_ok(label, dur)
        time.sleep(0.05)

    print()
    print(_center_raw(rule_s, tw))
    print()
    time.sleep(0.08)


# ── webhook ───────────────────────────────────────────────────────────────────
def _send_webhook(result: dict) -> None:
    url = _cfg_ref.get("webhook_url", "")
    if not url:
        return
    try:
        status = "Verified" if result.get("verified") else "Unverified"
        embed  = {
            "title":  "✅ Spotify Account Created",
            "color":  0x1DB954 if result.get("verified") else 0xFFAA00,
            "fields": [
                {"name": "📧 Email",    "value": f"`{result['email']}`",                      "inline": False},
                {"name": "🔑 Password", "value": f"`{result['password']}`",                   "inline": True},
                {"name": "👤 Name",     "value": f"`{result['display']}`",                    "inline": True},
                {"name": "🆔 UUID",     "value": f"`{result.get('uuid') or 'n/a'}`",          "inline": False},
                {"name": "📌 Status",   "value": status,                                      "inline": True},
            ],
            "footer":    {"text": _cfg_ref.get("webhook_footer", "regret.world")},
            "timestamp": datetime.utcnow().isoformat(),
        }
        _requests.post(
            url,
            json={"embeds": [embed], "username": _cfg_ref.get("webhook_username", "spotify-gen")},
            timeout=10,
        )
    except Exception:
        pass


# ── per-account worker ────────────────────────────────────────────────────────
async def _run_one(
    mail_api:    TempMailAPI,
    solver_path: Optional[Path],
    nopecha_key: str,
    headless:    bool,
    proxies:     list,
    idx:         int,
) -> None:
    proxy = random.choice(proxies) if proxies else None
    gen   = SpotifyGenerator(
        mail_api    = mail_api,
        output_path = OUTPUT_PATH,
        solver_ext  = solver_path,
        proxy       = proxy,
        headless    = headless,
        nopecha_key = nopecha_key,
    )

    def log(msg):
        ts = time.strftime("%H:%M:%S")
        with _lock:
            sys.stdout.write(
                f"\r  {POISON_MID}[{idx:02d}]{_R}  {POISON_DIM}{msg}{_R}          \n"
            )
            sys.stdout.flush()

    result = await gen.run_one(log_fn=log)

    with _lock:
        if result["success"]:
            _stats["success"] += 1
            if result.get("verified"):
                _stats["verified"] += 1
            tag = f"{POISON_GREEN}verified{_R}" if result["verified"] else f"{POISON_WARN}unverified{_R}"
            print(f"  {POISON_DIM}{'─' * 44}{_R}")
            _kv("email   ", result["email"],    SP_GREEN)
            _kv("password", result["password"], POISON_CYAN)
            _kv("name    ", result["display"],  Color.BRIGHT_WHITE)
            if result.get("uuid"):
                _kv("uuid    ", result["uuid"], POISON_ACCENT)
            _kv("status  ", "verified" if result["verified"] else "unverified",
                POISON_GREEN if result["verified"] else POISON_WARN)
            _kv("provider", "regret.world",     POISON_DIM)
            print(f"  {POISON_DIM}{'─' * 44}{_R}")
            _send_webhook(result)
        else:
            _stats["fail"] += 1
            print(f"  {POISON_ERR}✗{_R}  {Color.BRIGHT_WHITE}account #{idx} failed{_R}")

    await asyncio.sleep(random.uniform(1.0, 3.0))


async def _run_batch(cfg: dict, proxies: list, count: int, threads: int) -> None:
    mail_api    = TempMailAPI(api_key=cfg["rw_key"])
    solver_path = SOLVER_EXT if SOLVER_EXT.exists() else None
    headless    = cfg.get("headless", False)
    nopecha_key = cfg.get("nopecha_key", "")

    sem = asyncio.Semaphore(threads)

    async def _worker(idx: int):
        async with sem:
            await _run_one(mail_api, solver_path, nopecha_key, headless, proxies, idx)

    await asyncio.gather(*[asyncio.create_task(_worker(i + 1)) for i in range(count)])


def run_batch(cfg: dict, proxies: list, count: int, threads: int) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_batch(cfg, proxies, count, threads))
    finally:
        loop.close()


# ── premium applicator batch ──────────────────────────────────────────────────
def _run_premium_one(
    account: dict,
    vcc,
    headless: bool,
    idx: int,
) -> None:
    applicator = PremiumApplicator(
        output_path = OUTPUT_PATH,
        vcc_path    = VCC_PATH,
        headless    = headless,
    )

    def log(msg):
        with _lock:
            sys.stdout.write(
                f"\r  {POISON_MID}[{idx:02d}]{_R}  {POISON_DIM}{msg}{_R}          \n"
            )
            sys.stdout.flush()

    result = applicator.apply_one(account, vcc, log_fn=log)

    with _lock:
        if result["success"]:
            _prem_stats["success"] += 1
            print(f"  {POISON_DIM}{'─' * 44}{_R}")
            _kv("email  ", result["email"],  SP_GREEN)
            _kv("status ", result["status"], POISON_GREEN)
            print(f"  {POISON_DIM}{'─' * 44}{_R}")
        else:
            _prem_stats["fail"] += 1
            print(f"  {POISON_ERR}✗{_R}  {Color.BRIGHT_WHITE}account #{idx} failed{_R}")


def _run_premium_batch(accounts: list, vccs: list, headless: bool) -> None:
    import concurrent.futures, itertools as _it
    if not accounts:
        print(f"  {POISON_ERR}✗{_R}  no accounts found in output/accounts.txt")
        return
    if not vccs:
        print(f"  {POISON_ERR}✗{_R}  no VCCs found in data/vcc.txt")
        return

    # cycle VCCs across accounts
    vcc_cycle = _it.cycle(vccs)
    pairs     = [(acc, next(vcc_cycle)) for acc in accounts]

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        futs = [ex.submit(_run_premium_one, acc, vcc, headless, i + 1)
                for i, (acc, vcc) in enumerate(pairs)]
        for fut in concurrent.futures.as_completed(futs):
            try:
                fut.result()
            except Exception as exc:
                with _lock:
                    print(f"  {POISON_ERR}✗{_R}  thread error: {exc}")
                _prem_stats["fail"] += 1


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    multiprocessing.freeze_support()
    boot_sequence()

    if not CONFIG_PATH.exists():
        print(f"  {POISON_ERR}✗{_R}  config.json not found")
        sys.exit(1)

    cfg     = load_config(CONFIG_PATH)
    proxies = load_proxies(PROXY_PATH)
    _cfg_ref.update(cfg)

    rw_key  = cfg.get("rw_key", "")
    nop_key = cfg.get("nopecha_key", "")
    headless = cfg.get("headless", False)

    print(f"  {POISON_GREEN}✓{_R}  {Color.BRIGHT_WHITE}regret.world{_R}  {POISON_DIM}disposable inbox{_R}")
    print(f"  {POISON_GREEN}✓{_R}  {Color.BRIGHT_WHITE}nopecha{_R}       {POISON_DIM}captcha solver{_R}")
    print()

    tw     = _tw()
    rule_s = Color.multi_gradient("─" * min(tw, 70), *POISON_DARK)
    print(_center_raw(rule_s, tw))
    print()

    _kv("rw key  ", f"{rw_key[:8]}{'*' * 12}",     POISON_CYAN)
    _kv("nopecha ", f"{nop_key[:6]}{'*' * 10}",     POISON_CYAN)
    _kv("proxies ", f"{len(proxies)} loaded",        Color.BRIGHT_WHITE)
    _kv("headless", str(headless),                   Color.BRIGHT_WHITE)
    _kv("webhook ", "set" if cfg.get("webhook_url") else "off", Color.BRIGHT_WHITE)
    print()
    print(_center_raw(rule_s, tw))
    print()

    # ── mode selection ────────────────────────────────────────────────────────
    print(f"  {POISON_ACCENT}[1]{_R}  {Color.BRIGHT_WHITE}gen accounts{_R}")
    print(f"  {POISON_ACCENT}[2]{_R}  {Color.BRIGHT_WHITE}apply premium{_R}")
    print()
    mode_raw = _prompt("select mode")
    mode = mode_raw.lower().strip()

    print()
    print(_center_raw(rule_s, tw))
    print()

    # ── apply premium ─────────────────────────────────────────────────────────
    if mode in ("2", "apply premium", "premium", "apply"):
        accounts = load_accounts(OUTPUT_PATH)
        vccs     = load_vccs(VCC_PATH)

        _kv("accounts", f"{len(accounts)} loaded", Color.BRIGHT_WHITE)
        _kv("vccs    ", f"{len(vccs)} loaded",     Color.BRIGHT_WHITE)
        _kv("vcc file", "data/vcc.txt",             POISON_DIM)
        print()

        if not accounts:
            print(f"  {POISON_ERR}✗{_R}  no accounts in output/accounts.txt — gen some first")
            _prompt("press enter to exit")
            return
        if not vccs:
            print(f"  {POISON_ERR}✗{_R}  no VCCs in data/vcc.txt — add cards first")
            _prompt("press enter to exit")
            return

        print(f"  {POISON_ACCENT}▸{_R}  {POISON_DIM}applying premium to {_R}{Color.BRIGHT_WHITE}{len(accounts)}{_R}{POISON_DIM} account(s){_R}")
        print()

        _run_premium_batch(accounts, vccs, headless)

        print()
        print(_center_raw(rule_s, tw))
        print()
        _kv("applied ", str(_prem_stats["success"]), POISON_GREEN)
        _kv("failed  ", str(_prem_stats["fail"]),    POISON_ERR)
        print()
        _prompt("press enter to exit")
        return

    # ── gen accounts ──────────────────────────────────────────────────────────
    try:
        count = int(_prompt("accounts to create"))
    except (ValueError, EOFError):
        count = 1

    try:
        threads = int(_prompt("concurrent threads  "))
        threads = max(1, min(threads, 10))
    except (ValueError, EOFError):
        threads = 1

    print()
    print(_center_raw(rule_s, tw))
    print()

    print(f"  {POISON_ACCENT}▸{_R}  {POISON_DIM}generating {_R}{Color.BRIGHT_WHITE}{count}{_R}{POISON_DIM} account(s) — {threads} thread(s){_R}")
    print()

    run_batch(cfg, proxies, count, threads)

    print()
    print(_center_raw(rule_s, tw))
    print()
    _kv("success ", str(_stats["success"]), POISON_GREEN)
    _kv("verified", str(_stats["verified"]), SP_GREEN)
    _kv("failed  ", str(_stats["fail"]),    POISON_ERR)
    _kv("total   ", str(_stats["success"] + _stats["fail"]), Color.BRIGHT_WHITE)
    print()
    print(f"  {POISON_GREEN}✓{_R}  {Color.BRIGHT_WHITE}saved → output/accounts.txt{_R}")
    print()
    _prompt("press enter to exit")


if __name__ == "__main__":
    main()
