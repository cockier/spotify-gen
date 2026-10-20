# spotify-gen

browser-based spotify account generator — nodriver (undetected chromium) + [regret.world](https://regret.world) temp mail + nopecha captcha solver.

two modes: **gen accounts** and **apply premium** via VCC.

---

## requirements

- python 3.11+
- chrome / edge / brave installed (nodriver hooks into your local browser)
- [nopecha](https://nopecha.com) API key
- [regret.world](https://regret.world) API key

---

## setup

```
pip install -r requirements.txt
```

copy `config.json` and fill in your keys:

```json
{
  "rw_key":           "your-regret-world-key",
  "nopecha_key":      "your-nopecha-key",
  "headless":         false,
  "verify_timeout":   120,
  "poll_interval":    3,
  "use_proxy":        false,
  "webhook_url":      "",
  "webhook_footer":   "regret.world",
  "webhook_username": "spotify-gen"
}
```

**proxies** (optional) — drop them in `data/proxies.txt`, one per line (`ip:port` or `user:pass@ip:port`). the tool rotates them randomly across threads.

**nopecha extension** — the `solver/` folder is loaded automatically as a chromium extension. it handles hCaptcha on the signup page. set your key in `config.json` and the init tab fires before each signup run.

---

## usage

```
python main.py
```

boot sequence runs, then you pick a mode:

```
[1]  gen accounts
[2]  apply premium
```

### mode 1 — gen accounts

prompts for account count and thread count (max 10 concurrent). each thread:

1. creates a disposable inbox via regret.world
2. launches an undetected chromium instance
3. walks the spotify signup flow (email → password → profile → consent)
4. waits for post-signup redirect — extracts UUID from the `ubi` param when present
5. saves to `output/accounts.txt` as `email:password:displayname:status`

fires a discord webhook per account if `webhook_url` is set.

### mode 2 — apply premium

reads accounts from `output/accounts.txt` and VCCs from `data/vcc.txt` (one per line), then applies a premium trial to each account. VCCs cycle across accounts if there are fewer cards than accounts.

---

## output

```
output/accounts.txt   →   email:password:displayname:status
```

status is `verified` or `unverified` depending on whether the post-signup redirect was confirmed.

---

## project layout

```
spotify-gen/
├── main.py               boot + TUI + orchestration
├── config.json           keys, flags, webhook config
├── core/
│   ├── generator.py      nodriver signup flow
│   ├── premium.py        VCC premium applicator
│   ├── tempmail.py       regret.world inbox + polling
│   └── utils.py          random name/pass/DOB gen, proxy parsing, file I/O
├── kit/
│   ├── colors.py         RGB + gradient terminal colors
│   └── styles.py         border / layout helpers
├── solver/               nopecha chromium extension (loaded at runtime)
├── data/
│   ├── proxies.txt       one proxy per line (optional)
│   └── vcc.txt           one VCC per line (for premium mode)
└── output/
    └── accounts.txt      generated accounts land here
```

---

## notes

- offsets and selectors are pinned to the current signup flow — re-derive after Spotify updates the DOM
- nopecha handles hCaptcha; if the key is missing or the solver ext is absent the captcha step will stall
- headless mode works but is more likely to trigger bot detection — keep it `false` for better success rate
- threads share one event loop per process via `asyncio.Semaphore` — don't go above 5–6 on a single IP without rotating proxies
