# pt-term

A vim-inspired periodic table and [NIST Atomic Spectra Database (ASD)](https://physics.nist.gov/PhysRefData/ASD/levels_form.html) energy-level viewer for your terminal, built with Python [`curses`](https://docs.python.org/3/library/curses.html).

This is completely vibecoded. By design, I have not looked at any of the code by hand.

## Features

- **Full 118-element table** with categories, ground-state electron configurations (including the common exceptions), block/group/period metadata, and lanthanide/actinide placement.
- **Scales to the terminal.** Cells stay visually square as the window grows (1×2 up to 5×10 characters, showing Z, symbol, name and mass as space allows), with equal visual gaps between periods and groups.
- **Vim-style navigation and command mode**: `hjkl` / arrow keys, `w`/`b`, `0`/`$`/`gg`/`G` (with counts), `/` search with `n`/`N`, `c`/`C` category highlighting, and `:` Ex commands (`:q`, `:wq`, `:qa`, `ZZ` all work).
- **NIST ASD energy levels**: press `Enter` (or double-click / right-click) on an element, pick an ionization stage, and the levels are fetched from NIST, cached locally, or read from your own pre-downloaded files. Units `cm⁻¹`, `eV`, `Ry`, `Eh`; energy or NIST ordering; colour-coded output.
- **Line estimates and NIST transition probabilities** in the level viewer (`f` / `F`): M1 fine-structure lines with an empirical A-value, candidate allowed (E1) lines with a hydrogenic A-value estimate, and NIST ASD A-values shown alongside them wherever NIST has the line.
- **Mouse support**, cell opacity and light/dark blending, and a **lite mode** for slow terminals.

## Requirements

- Python 3, standard library only. [`certifi`](https://pypi.org/project/certifi/) is used if installed, which fixes HTTPS certificate errors on some macOS Python installs.
- A terminal with `curses` support. 256 colours are recommended for the opacity blending; 8-colour and monochrome terminals work with simpler colours.
- Minimum terminal size 56×16.

## Usage

Install it once somewhere on your `PATH`:

```bash
chmod +x periodic.py
cp periodic.py ~/.local/bin/periodic      # or any other directory on your PATH
```

Then just type:

```bash
periodic
```

It opens at hydrogen. You can also start on a particular element:

```bash
periodic Fe       # by symbol
periodic 26       # by atomic number
periodic iron     # by name
```

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
| `f` | Cycle line tags: M1 → E1 → NIST → off |
| `F` | Full line list for the current mode (M1 if tags are off) |
| `s` (in the `F` list) | Cycle sort: A, wavelength; in the NIST list also worst estimate-vs-NIST agreement first |
| `t` | Cycle the minimum A-value shown |
| `a` | Vacuum / air wavelengths |
| `r` | Refetch the levels from NIST ASD, bypassing the cache (the lines are refetched on the next visit to the NIST state) |
| `q`, `Esc`, `:q`, `ZZ` | Back to the picker / table (`:qa` quits the app) |

**Colour coding.** Configuration is coloured by its outermost written subshell, with a distinct colour for each of s, p, d, f, g, h, i and k; the header legend lists only the subshells that occur in the current level list. The term is coloured by parity (even, or odd, marked `*` by NIST). Energy runs from red (low) to blue (high), like photon colour. The ionization limit is shown in yellow, and derived or uncertain levels (`[ ]`, `( )`) are dimmed.

## Line estimates

These are quick, order-of-magnitude guides for spotting potentially important lines. They are not a substitute for real atomic-structure calculations or evaluated data.

### M1 lines (`f` once)

These are lines between levels of the same configuration and LS term with $\Delta J = \pm 1$. They use the empirical formula

```math
A_{ul} = 1.3\ \mathrm{s^{-1}} \left( \frac{\lambda_{ul}}{4\ \mu\mathrm{m}} \right)^{-3} f(J, L, S),
```

where $J = J_u$ and

```math
f(J, L, S) =
\begin{cases}
\dfrac{\left(J^2 - (L-S)^2\right)\left((L+S+1)^2 - J^2\right)}{12\,J\,(2J+1)}, & J_u = J_l + 1, \\[2ex]
\dfrac{\left((J+1)^2 - (L-S)^2\right)\left((L+S+1)^2 - (J+1)^2\right)}{12\,(J+1)(2J+1)}, & J_u = J_l - 1.
\end{cases}
```

This is a pure-LS estimate, so expect it to degrade for heavy or highly charged ions. As spot checks, it gives about $62\ \mathrm{s^{-1}}$ for the Fe XIV 5303 Å coronal line, $1.0\times10^{-4}$ and $2.7\times10^{-5}\ \mathrm{s^{-1}}$ for [O III] 52 and 88 µm, and $2.2\times10^{-3}\ \mathrm{s^{-1}}$ for [Fe II] 26 µm.

The factor $f(J, L, S)$ is the M1 line strength for transitions within an LS term, divided by the upper-level degeneracy, following [Pasternack (1940), ApJ 92, 129](https://ui.adsabs.harvard.edu/abs/1940ApJ....92..129P), [Shortley (1940), Phys. Rev. 57, 225](https://doi.org/10.1103/PhysRev.57.225) and [Bahcall & Wolf (1968), ApJ 152, 701](https://ui.adsabs.harvard.edu/abs/1968ApJ...152..701B). The prefactor comes from the standard M1 conversion

```math
A_{ul} = \frac{2.6973\times10^{13}}{\lambda^3}\,\frac{S}{2J_u+1}\ \mathrm{s^{-1}}, \qquad \lambda \text{ in Å},\ S \text{ in } \mu_B^2,
```

which at $\lambda = 4\ \mu\mathrm{m}$, with $S/(2J_u+1) = 3f$, gives $1.26 \approx 1.3\ \mathrm{s^{-1}}$.

### E1 (allowed) lines (`f` twice)

**Candidates** must satisfy all of:
- parity changes
- $\lvert \Delta J \rvert \le 1$, excluding $0 \to 0$
- LS-allowed when both terms are LS: $\Delta S = 0$, $\lvert \Delta L \rvert \le 1$, no $S \to S$. Pairs with a non-LS term (jK, jj) are kept and marked `jj`.
- the two configurations differ by a single electron, $n_a l_a \leftarrow n_b l_b$, with $\lvert \Delta l \rvert = 1$

**A-value.** The A-value is converted from an oscillator strength with the standard relation, as given in the [NIST Atomic Spectroscopy compendium](https://www.nist.gov/pml/atomic-spectroscopy-compendium-basic-ideas-notation-data-and-formulas/atomic-spectroscopy):

```math
A_{ki} = \frac{6.670\times10^{15}}{\lambda^2}\,\frac{g_i}{g_k}\,f_{ik}\ \mathrm{s^{-1}}, \qquad \lambda \text{ in Å}.
```

The one-electron oscillator strength is estimated hydrogenically, using effective quantum numbers taken from the ionization limit in the level list:

```math
n^* = \zeta \sqrt{\frac{\mathrm{Ry}}{E_\text{limit} - E}}, \qquad \zeta = \text{ion stage}.
```

| Case | Oscillator strength | Tag |
| --- | --- | --- |
| Same shell ($\Delta n = 0$) | $f_0 = \dfrac{\Delta E}{3\ \mathrm{Ry}} \cdot \dfrac{l_>}{2l_a+1}\ \sigma^2$, with $\sigma = \dfrac{3}{2}\ \dfrac{\bar n^{\ast}}{\zeta}\sqrt{\bar n^{\ast 2} - l_>^2}$ | `dn0` |
| $\Delta n \ne 0$ | Exact hydrogenic $f_H(n_a l_a \to n_b l_b)$ with the integer $n$ of the configuration, blended with $f_0$ by how much of the integer $\Delta n$ survives in the effective quantum numbers: $f = f_0^{1-x} f_H^{x}$, with $x = \Delta n^{\ast} / \Delta n$ clipped to $[0, 1]$. Large quantum defects shrink $\Delta n^{\ast}$, and the line then behaves more like a same-shell line | `hyd` ($x > 0.9$), `mix` |
| No ionization limit in the list | $f = f_H$ for $\Delta n \ne 0$, otherwise $1$ | `hyd`, `f=1` |
| Any of the above reaching $f \ge 1$ | capped at $1$ | `f=1` |

The result is then scaled by the occupancy factor

```math
N_b \times \frac{\text{vacancies in } n_a l_a}{2(2l_a+1)},
```

and split among the lower levels with LS recoupling (Wigner 6j) factors. Each factor sums to 1, so an upper level's total decay rate is unchanged and only its distribution between lines is affected:

- **J branching** within a multiplet, whenever both terms are LS, normalised over $J_l$:

```math
F_J = (2J_l+1)\begin{Bmatrix} L_u & J_u & S \\ J_l & L_l & 1 \end{Bmatrix}^2
```

- **Term branching** when both configurations show the same parent term $L_c$ (e.g. `3d6.(5D).4p` → `3d6.(5D).4s`), or the core is closed, normalised over the lower terms the parent allows:

```math
F_\text{term} = (2L_l+1)\begin{Bmatrix} l_b & L_u & L_c \\ L_l & l_a & 1 \end{Bmatrix}^2
```

- **No stated parent** (e.g. `4s2.4p2`, `3d7`): the lower terms present share by $(2L_l+1)(2S+1)$, and the line is tagged `~`.
- **Any non-LS term** in the group: fallback to $(2J_l+1)$ sharing.

The 6j symbols use Racah's formula and are cached, so this costs almost nothing.

A `?` after the tag marks a d or f orbital with $n^{\ast 2} \le l(l+1)$, where the hydrogenic picture is poor; a `~` marks a line whose lower-term split had no parent to go on.

**Inner-subshell jumps (`ci`).** These are lines of the type $ns\ np^{k+1} \to ns^2\ np^k$, such as C II $2s2p^2 \to 2s^2 2p$ or Se III $4s4p^3 \to 4s^2 4p^2$. Here the electron fills a hole in an inner s subshell, so it can't be given the binding energy of the outermost electron. For these lines:
- the p electron uses the valence binding of the lower level, $E_\text{limit} - E_\text{lower}$
- the s electron is bound more deeply by the excitation energy, $E_\text{limit} - E_\text{lower} + \Delta E$

This brings C II 1335.7 Å to $2.8\times10^{8}\ \mathrm{s^{-1}}$ (NIST $2.9\times10^{8}$). In heavier ions, though, $ns\ np^{k+1}$ mixes strongly with $ns^2\ np^{k-1}\ nd$, and the two contributions cancel. That cancellation is beyond any hydrogenic estimate. For Se III $4s4p^3 \to 4s^2 4p^2$, the estimate is about $8\times10^{8}\ \mathrm{s^{-1}}$, against about $5\times10^{7}$ from multiconfiguration calculations. So `ci` lines are shown in the warning colour: treat them as an upper bound that may be an order of magnitude too high.

**Typical accuracy** against reference values:
- Lyα and Hα: exact
- strong resonance lines (Na D, Ca II H & K, Mg II): within about 10%
- most $\Delta n \ne 0$ lines (Na $4s \to 3p$, Ca II 8542/8662 Å, Se III $4p5s \to 4p^2$): within about 2×
- fine-structure splits within a multiplet: correct in pure LS (Hα components exact, C II 1334/1336 Å within 4%, the Ca II infrared triplet ratios and Fe II 2600/2626 Å right); heavier ions drift as intermediate coupling sets in

**Known failures:**
- `ci` lines (above): can be ~10× too high
- alkali principal-series lines beyond the first, such as Na 3303 Å ($4p \to 3s$): about 35× too high, because a strong cancellation in the real radial integral has no hydrogenic counterpart
- lines from a singlet upper level of $ns\ np \to ns^2$, such as Mg I 2852 Å: about 3–4× too low, because the strength of the whole configuration is spread over all upper terms, not concentrated by spin selection

### NIST transition probabilities

NIST is only queried when you select the NIST state (`f` three times). That makes one request per ion for NIST ASD's lines with transition probabilities (allowed and forbidden), cached like the levels. `PERIODIC_LINES_DIR` is checked first for files named `lines_<El>+<charge>.txt`. The M1 and E1 states show our estimates only: they never touch the network or NIST data on disk. After `r`, the next visit to the NIST state refetches the lines. Each NIST line is matched to the level list by upper and lower energy and J, to within about 0.05 cm⁻¹; configuration and term strings aren't relied on.

- **The NIST state** lists every NIST line with an A-value. NIST's A (used for cuts, sorting and "strongest line") is shown with its accuracy grade, e.g. `N:B+`, followed by our estimate where we have one for the same pair of levels (`est -` where we don't).
- **NIST-only lines.** Lines our selection rules don't produce, such as intercombination, two-electron and E2/M2 lines, appear in the NIST list with an empty estimate column; NIST's `Type` column is shown.
- **The `F` list** shows `A_NIST`, the grade, `A_est` and `est/N` side by side. Ratios outside 1/3–3 are highlighted, and the status line gives the median est/NIST ratio for the ion. Sorting by worst agreement (`s` twice) brings the lines where the estimate fails most to the top.
- **If NIST can't be reached,** the NIST state says so in the status line; the M1 and E1 states are unaffected.

### Where the tags appear

- **Level list.** With tags on, each upper level shows its strongest line: the lower J (M1) or the lower level's row number `→#n` (E1, NIST), then λ and A. Next comes the source: the E1 method tag or `est` in the M1 and E1 states, or `N:<grade>` in the NIST state, which is followed by our estimate as `est …`. `+N` means N more lines from that upper level in the current list, above the current cut. It therefore differs between states: the E1 list contains different lines from the NIST list, and hides $A < 10^{6}\ \mathrm{s^{-1}}$ by default. In narrow windows the configuration column is hidden to make room, and the `est …` part may be cut off; the `F` list always shows both values.
- **`F` list.** Every line, strongest first, sortable by wavelength (`s`). `Enter` jumps to the upper level.
- **Colours.** Wavelengths are coloured like the photon (infrared dim red, ultraviolet dim violet), and A-values by strength. Method tags are green when a hydrogenic estimate was used (`dn0`, `hyd`, `mix`), yellow when the value was capped, and red for `?` and `ci`.
- **Wavelength units.** Vacuum by default. Allowed (E1) lines, in the E1 state and E1-type lines in the NIST state, are given in nm (µm beyond 10 µm). M1 and other forbidden lines use Å below 1 µm and µm above.
- **Air wavelengths** (`a`) use the refractive-index formula of [Morton (2000), ApJS 130, 403](https://doi.org/10.1086/317349) above 2000 Å.

## Environment variables and cache

| Variable | Effect |
| --- | --- |
| `PERIODIC_LEVELS_DIR` | Directory checked first for pre-downloaded NIST files named `levels_cm_<El>+<charge>.txt`, e.g. `levels_cm_Fe+0.txt` for Fe I |
| `PERIODIC_LINES_DIR` | Directory checked first for pre-downloaded NIST lines files named `lines_<El>+<charge>.txt`, e.g. `lines_Fe+1.txt` for Fe II |
| `PERIODIC_OPACITY` | Initial cell opacity, `10`–`100` (default `70`) |
| `PERIODIC_ASPECT` | Font height:width ratio for square cells, `1.0`–`3.0` (default `2.0`) |
| `PERIODIC_SPACING` | Set to `0` to start with no gaps between cells |
| `PERIODIC_LITE` | Set to `1` to start in lite mode |
| `PERIODIC_NO_MOUSE` | Set to `1` to disable mouse events at startup |
| `PERIODIC_CACHE_MB` | Size cap for the cache directory (default `500`) |
| `COLORFGBG` | If your terminal sets it, used to detect a light background |

**Cache.** `~/.cache/periodic/` stores fetched NIST responses, both levels and lines. If a reply can't be parsed, the full reply is saved to `last_reply.txt` there. The directory is kept under `PERIODIC_CACHE_MB`: the files with the oldest timestamps are removed first, and reading a cached file refreshes its timestamp, so recently used files survive. `PERIODIC_LEVELS_DIR` is never touched.

## Performance

The program handles a keypress in a millisecond or two. Redraws are skipped while input is queued (held keys, trackpad scrolling), and the screen catches up when it stops. If the display still feels sluggish, the terminal's rendering is the bottleneck. macOS Terminal is notably slower than iTerm2, Ghostty, kitty, WezTerm or Alacritty, especially with a translucent or blurred background. Try:

- `L` (lite mode), which drops the solid cell fills and starts level lists without colour
- a smaller window
- turning off window transparency

## Caveats

- Atomic masses, electron configurations and the E1/M1 estimates are built in or approximate; check anything important against [NIST ASD](https://physics.nist.gov/PhysRefData/ASD/levels_form.html).
- Energy levels come straight from NIST ASD, so their quality and completeness are NIST's.