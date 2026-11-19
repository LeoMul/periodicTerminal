# pt-term

A vim-inspired periodic table and NIST Atomic Spectra Database (ASD) energy-level viewer for your terminal, built with Python `curses`[cite: 1].
This is completely vibecoded. By design, I have not looked at any of the code by hand.
## Features

- **Full 118-element table** with categories, electron configurations (including exceptions), block/group/period metadata, and lanthanide/actinide placement[cite: 1].
- **Vim-style navigation & command mode**: `hjkl` / arrow keys, `w`/`b`, `0`/`$`/`gg`/`G` (with counts), `/` search with `n`/`N`, `c`/`C` category highlighting, and `:` Ex commands[cite: 1].
- **NIST ASD energy levels**: press `Enter` (or double-click / right-click) on an element to pick an ionization stage and fetch energy levels, with local caching (`~/.cache/periodic`), offline/local file overrides, unit switching (`cm-1`, `eV`, `Ry`), and sorting[cite: 1].
- **Mouse support & appearance tuning**: click to select, wheel to scroll, and adjust cell opacity (`10`–`100`) or light/dark background blending[cite: 1].

## Requirements

- Python 3 (standard library only; `certifi` is optional if your Python environment needs extra CA certificates for HTTPS)[cite: 1].
- A terminal supporting `curses` (256-color recommended for opacity blending)[cite: 1].

## Usage

```bash
chmod +x periodic.py
./periodic.py [element]
```

Examples:

```bash
./periodic.py          # start at Hydrogen (Z = 1)
./periodic.py Fe       # jump to Iron by symbol
./periodic.py 26       # jump to Iron by atomic number
./periodic.py iron     # search by name
```

## Keybindings & Commands

### Periodic Table View

| Key / Command | Action |
| --- | --- |
| `h` `j` `k` `l` / Arrows | Move across grid (supports counts, e.g., `5l`) |
| `w` / `b` | Next / previous element by atomic number |
| `0` / `^` / `$` | Start / end of current row |
| `gg` / `G` | First / last element (`26G` jumps to `Z = 26`) |
| `/` , `n` , `N` | Search symbol, name, or number; next / previous match |
| `c` / `C` / `Esc` | Cycle category highlight forward / backward; clear highlights & counts |
| `Enter` | Open ionization stage picker for the selected element |
| `?` | Show keybinding help |
| `q` , `ZZ` / `ZQ` , `:q` , `:qa` | Quit |

### Ex Commands (`:`)

- `:<Z|Symbol|Name>` — jump to an element (e.g., `:26`, `:Fe`, `:iron`)[cite: 1].
- `:levels [stage]` or `:e [Element] [stage]` — open energy levels (e.g., `:levels II`, `:e Fe III`)[cite: 1].
- `:set [no]mouse` — enable or disable mouse handling[cite: 1].
- `:set opacity=<10-100>` — set cell fill opacity on 256-color terminals[cite: 1].
- `:set background=<light|dark>` — set background tone used for opacity blending[cite: 1].
- `:noh` / `:help` — clear search matches / open help[cite: 1].

### Energy Levels Viewer

- `j` / `k` / Arrows, `Ctrl-d` / `Ctrl-u`, `Ctrl-f` / `Ctrl-b`, `gg` / `G` — navigate levels[cite: 1].
- `/` , `n` , `N` — search configuration or term, and jump next / previous[cite: 1].
- `u` — cycle energy units (`cm-1`, `eV`, `Ry`)[cite: 1].
- `o` — toggle sorting by energy vs. NIST order[cite: 1].
- `r` — force-refetch from NIST ASD, bypassing cache[cite: 1].
- `q` / `Esc` / `:q` / `ZZ` — return to table (`:qa` quits the app)[cite: 1].

## Environment Variables & Cache

- `PERIODIC_LEVELS_DIR` — directory checked first for pre-downloaded NIST files named `levels_cm_<El>+<charge>.txt` (e.g., `levels_cm_Fe+0.txt`)[cite: 1].
- `PERIODIC_OPACITY` — initial cell opacity (`10`–`100`, default `70`)[cite: 1].
- `PERIODIC_NO_MOUSE` — set to `1` to disable mouse events on startup[cite: 1].
- `COLORFGBG` — used as a fallback hint to detect light vs. dark terminal backgrounds[cite: 1].
- Cache location: `~/.cache/periodic/` stores fetched NIST responses and `last_reply.txt` if parsing fails[cite: 1].
