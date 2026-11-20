# pt-term

A vim-inspired periodic table and [NIST Atomic Spectra Database (ASD)](https://physics.nist.gov/PhysRefData/ASD/levels_form.html) energy-level viewer for your terminal, built with Python [`curses`](https://docs.python.org/3/library/curses.html).

This is completely vibecoded. By design, I have not looked at any of the code by hand.

## Features

- **Full 118-element table** with categories, ground-state electron configurations (including the common exceptions), block/group/period metadata, and lanthanide/actinide placement.
- **Scales to the terminal.** Cells stay visually square as the window grows (1×2 up to 5×10 characters, showing Z, symbol, name and mass as space allows), with equal visual gaps between periods and groups.
- **Vim-style navigation and command mode**: `hjkl` / arrow keys, `w`/`b`, `0`/`$`/`gg`/`G` (with counts), `/` search with `n`/`N`, `c`/`C` category highlighting, and `:` Ex commands (`:q`, `:wq`, `:qa`, `ZZ` all work).
- **NIST ASD energy levels**: press `Enter` (or double-click / right-click) on an element, pick an ionization stage, and the levels are fetched from NIST, cached locally, or read from your own pre-downloaded files. Units `cm⁻¹`, `eV`, `Ry`, `Eh`; energy or NIST ordering; colour-coded output.
- **Line estimates** in the level viewer (`f` / `F`): M1 fine-structure lines with an empirical A-value, and candidate allowed (E1) lines with a hydrogenic A-value estimate.
- **Mouse support**, cell opacity and light/dark blending, and a **lite mode** for slow terminals.

## Requirements

- Python 3, standard library only. [`certifi`](https://pypi.org/project/certifi/) is used if installed, which fixes HTTPS certificate errors on some macOS Python installs.
- A terminal with `curses` support. 256 colours are recommended for the opacity blending; 8-colour and monochrome terminals work with simpler colours.
- Minimum terminal size 56×16.

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

To launch it as `periodic`, copy it onto your `PATH`, e.g. `cp periodic.py ~/.local/bin/periodic`.

## Keybindings and commands

### Periodic table view

| Key / command | Action |
| --- | --- |
| `h` `j` `k` `l` / arrows | Move across the grid (counts work, e.g. `5l`) |
| `w` / `b` | Next / previous element by atomic number |
| `0` / `^` / `$` | Start / end of the current row |
| `gg` / `G` | First / last element (`26G` jumps to Z = 26) |
| `/`, `n`, `N` | Search symbol, name or number; next / previous match |
| `c` / `C` | Cycle the category highlight forward / backward |
| `Esc` | Clear matches, highlight and pending count |
| `Enter` | Open the ionization-stage picker for the selected element |
| `L` | Toggle lite mode |
| `?` | Show keybinding help |
| `q`, `ZZ` / `ZQ`, `:q`, `:wq`, `:qa` | Quit |

### Mouse

- **Table**: click selects; double-click or right-click opens the stage picker; the wheel moves up and down. Clicks in the gaps between cells count as the nearest cell.
- **Stage picker / level lists**: click a row to select it, double-click or right-click a stage to query it, and use the wheel to scroll. In the level viewer, clicking the header row cycles the energy unit.
- While mouse reporting is on, the terminal's own text selection is captured. Turn it off with `:set nomouse`, or hold Option (iTerm2) to select text.

### Ex commands (`:`)

| Command | Action |
| --- | --- |
| `:26`, `:Fe`, `:iron` | Jump to an element |
| `:levels [stage]`, `:e [element] [stage]` | Open energy levels, e.g. `:levels II`, `:e Fe III`, `:e Fe 2+` |
| `:set [no]mouse` | Enable or disable mouse handling |
| `:set [no]spacing` | Gaps between cells on / off |
| `:set [no]lite` | Lite mode on / off |
| `:set aspect=<1.0-3.0>` | Font height:width ratio used to keep cells square (default 2.0). Raise it if cells look tall, lower it if they look wide |
| `:set opacity=<10-100>` | Cell fill opacity on 256-colour terminals |
| `:set background=<light\|dark>` | Background tone used for the opacity blending |
| `:set opacity` | Show the current display settings |
| `:noh`, `:help` | Clear search matches / open help |

### Stage picker

Lists every ionization stage with its charge, electron count and isoelectronic sequence (e.g. Fe XXIV, Li-like). `j`/`k` to move, `Enter` to query, `3<Enter>` or `:3` for stage III, `q` to cancel.

### Energy-level viewer

| Key | Action |
| --- | --- |
| `j` / `k` / arrows, `Ctrl-d` / `Ctrl-u`, `Ctrl-f` / `Ctrl-b`, `gg` / `G` | Navigate (counts work, `12G` goes to row 12) |
| `/`, `n`, `N` | Search configuration or term; next / previous |
| `u` | Cycle units: `cm⁻¹`, `eV`, `Ry`, `Eh` |
| `o` | Toggle sorting by energy vs. NIST order |
| `c` | Colour coding on / off (see below) |
| `f` | Cycle line tags: M1 → E1 → off |
| `F` | Full line list for the current mode (M1 if tags are off) |
| `t` | Cycle the minimum A-value shown |
| `a` | Vacuum / air wavelengths |
| `r` | Refetch from NIST ASD, bypassing the cache |
| `q`, `Esc`, `:q`, `ZZ` | Back to the picker / table (`:qa` quits the app) |

**Colour coding.** Configuration is coloured by its outermost written subshell (s, p, d, f). The term is coloured by parity (even, or odd, marked `*` by NIST). Energy runs from red (low) to blue (high), like photon colour. The ionization limit is shown in yellow, and derived or uncertain levels (`[ ]`, `( )`) are dimmed.

## Line estimates

These are quick, order-of-magnitude guides for spotting potentially important lines. They are not a substitute for real atomic-structure calculations or evaluated data.

### M1 lines (`f` once)

These are lines between levels of the same configuration and LS term with ΔJ = ±1. They use the empirical formula

A_ul = 1.3 s⁻¹ (λ_ul / 4 µm)⁻³ f(J, L, S)

where J = J_u, and

- f = (J² − (L−S)²)((L+S+1)² − J²) / (12J(2J+1)) for J_u = J_l + 1
- f = ((J+1)² − (L−S)²)((L+S+1)² − (J+1)²) / (12(J+1)(2J+1)) for J_u = J_l − 1

This is a pure-LS estimate, so expect it to degrade for heavy or highly charged ions. As spot checks, it gives about 62 s⁻¹ for the Fe XIV 5303 Å coronal line, 1.0×10⁻⁴ and 2.7×10⁻⁵ s⁻¹ for [O III] 52 and 88 µm, and 2.2×10⁻³ s⁻¹ for [Fe II] 26 µm.

> **TODO:** add the reference for the empirical M1 formula above.

### E1 (allowed) lines (`f` twice)

**Candidates** must satisfy all of:
- parity changes
- |ΔJ| ≤ 1, excluding 0 → 0
- LS-allowed when both terms are LS: ΔS = 0, |ΔL| ≤ 1, no S → S. Pairs with a non-LS term (jK, jj) are kept and marked `jj`.
- the two configurations differ by a single electron, n_a l_a ← n_b l_b, with |Δl| = 1

**A-value.** The A-value is converted from an oscillator strength with the standard relation A_ki = 6.670×10¹⁵ (g_i/g_k) f_ik / λ² (λ in Å), as given in the [NIST Atomic Spectroscopy compendium](https://www.nist.gov/pml/atomic-spectroscopy-compendium-basic-ideas-notation-data-and-formulas/atomic-spectroscopy). The one-electron oscillator strength is estimated hydrogenically, using effective quantum numbers n* = ζ √(Ry / (E_limit − E)) (ζ = ion stage) taken from the ionization limit in the level list:

| Case | Oscillator strength | Tag |
| --- | --- | --- |
| Same shell (Δn = 0) | f₀ = (ΔE/Ry)/3 · l_>/(2l_a+1) · σ², with σ = (3/2)(n̄*/ζ)√(n̄*² − l_>²) | `dn0` |
| Δn ≠ 0 | Kramers' semiclassical formula with a Gaunt factor of 0.8, f_K = 0.8 · 32/(3π√3) · 1/(n_lo⁵ n_hi³) · (1/n_lo² − 1/n_hi²)⁻³, with integer n from the configuration, then capped as f = min(f_K, f₀, 1) | `kram`, or `cap` when f₀ was the smaller |
| No ionization limit in the list | f = min(f_K, 1), or 1 | `f=1` |

The result is then:
- scaled by the occupancy factor N_b × (vacancies in n_a l_a)/(2(2l_a+1))
- shared among the allowed lower levels of each lower configuration in proportion to (2J_l+1)

A `?` after the tag marks a d or f orbital with n*² ≤ l(l+1), where the hydrogenic picture is poor.

**Inner-subshell jumps (`ci`).** These are lines of the type ns np^(k+1) → ns² np^k, such as C II 2s2p² → 2s²2p or Se III 4s4p³ → 4s²4p². Here the electron fills a hole in an inner s subshell, so it can't be given the binding energy of the outermost electron. For these lines:
- the p electron uses the valence binding of the lower level, E_limit − E_lower
- the s electron is bound more deeply by the excitation energy, E_limit − E_lower + ΔE

This brings C II 1335.7 Å to 2.8×10⁸ s⁻¹ (NIST 2.9×10⁸). In heavier ions, though, ns np^(k+1) mixes strongly with ns² np^(k−1) nd, and the two contributions cancel. That cancellation is beyond any hydrogenic estimate. For Se III 4s4p³ → 4s²4p², the estimate is about 8×10⁸ s⁻¹, against about 5×10⁷ from multiconfiguration calculations. So `ci` lines are shown in the warning colour: treat them as an upper bound that may be an order of magnitude too high.

**Typical accuracy** against NIST:
- strong resonance lines (Na D, Lyα, Ca II H & K, Mg II): within about 10%
- Δn ≠ 0 lines: often 2–3× high
- fine-structure splits within a multiplet: crude, because the (2J_l+1) sharing ignores the LS 6j factors

### Where the tags appear

- **Level list.** With tags on, each upper level shows its strongest line: the lower J (M1) or the lower level's row number `→#n` (E1), then λ, A and, for E1, the method tag. `+N` means N more lines. In narrow windows the configuration column is hidden to make room.
- **`F` list.** Every line, strongest first, sortable by wavelength (`s`). `Enter` jumps to the upper level.
- **Colours.** Wavelengths are coloured like the photon (infrared dim red, ultraviolet dim violet), and A-values by strength. Method tags are green when the hydrogenic formula was used, yellow when the value was capped, and red for `?` and `ci`.
- **Air wavelengths** (`a`) use the refractive-index formula of [Morton (2000), ApJS 130, 403](https://doi.org/10.1086/317349) above 2000 Å.

## Environment variables and cache

| Variable | Effect |
| --- | --- |
| `PERIODIC_LEVELS_DIR` | Directory checked first for pre-downloaded NIST files named `levels_cm_<El>+<charge>.txt`, e.g. `levels_cm_Fe+0.txt` for Fe I |
| `PERIODIC_OPACITY` | Initial cell opacity, `10`–`100` (default `70`) |
| `PERIODIC_ASPECT` | Font height:width ratio for square cells, `1.0`–`3.0` (default `2.0`) |
| `PERIODIC_SPACING` | Set to `0` to start with no gaps between cells |
| `PERIODIC_LITE` | Set to `1` to start in lite mode |
| `PERIODIC_NO_MOUSE` | Set to `1` to disable mouse events at startup |
| `PERIODIC_CACHE_MB` | Size cap for the cache directory (default `500`) |
| `COLORFGBG` | If your terminal sets it, used to detect a light background |

**Cache.** `~/.cache/periodic/` stores fetched NIST responses. If a reply can't be parsed, the full reply is saved to `last_reply.txt` there. The directory is kept under `PERIODIC_CACHE_MB`: the files with the oldest timestamps are removed first, and reading a cached file refreshes its timestamp, so recently used files survive. `PERIODIC_LEVELS_DIR` is never touched.

## Performance

The program handles a keypress in a millisecond or two. Redraws are skipped while input is queued (held keys, trackpad scrolling), and the screen catches up when it stops. If the display still feels sluggish, the terminal's rendering is the bottleneck. macOS Terminal is notably slower than iTerm2, Ghostty, kitty, WezTerm or Alacritty, especially with a translucent or blurred background. Try:

- `L` (lite mode), which drops the solid cell fills and starts level lists without colour
- a smaller window
- turning off window transparency

## Caveats

- Atomic masses, electron configurations and the E1/M1 estimates are built in or approximate; check anything important against [NIST ASD](https://physics.nist.gov/PhysRefData/ASD/levels_form.html).
- Energy levels come straight from NIST ASD, so their quality and completeness are NIST's.