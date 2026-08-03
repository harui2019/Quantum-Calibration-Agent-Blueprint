# VLM Guidelines

How `vlm_inspect` actually works in this system, and what to ask it for each plot type produced by the experiments in `03_Experiment_API.md`.

## How `vlm_inspect` Works

`vlm_inspect(experiment_id, prompt)` (`tools/vlm_tool.py`):

1. Loads every plot stored for that experiment (`core/storage.list_plots`) — this reads the `plots` list saved with the result (`05_Result_Format.md`). If a wrapper never populated `plots`, this returns nothing and `vlm_inspect` fails with `"No plots found in experiment"` — that's a bug in the wrapper, not something to work around by re-running.
2. Renders each plot to a base64 PNG. `"plotly"`-format plots are rasterized via `plotly` + `kaleido` at **640×480** by default (`vlm/renderer.py`). `"png"`-format plots (all current `qblox_*` wrappers) are already PNG and used as-is, at whatever resolution they were saved (see below).
3. Sends **all** plots from the experiment to the VLM in one call, with a combined prompt.
4. Returns `{"status", "analysis", "plots_analyzed", "plot_count"}`.

**Format gotcha**: the renderer only recognizes `"plotly"`, `"png"`, `"jpeg"`, `"jpg"` as plot formats — not `"base64"`, even though that string is also technically valid for the UI's own rendering. If a script tags a plot `"format": "base64"`, the UI will still show it but `vlm_inspect` will silently skip it as "unsupported format." Always use `png_plot_entry()` (which sets `"format": "png"`) for real PNG data — never hand-write `"format": "base64"`.

The VLM itself is configured under the top-level `vlm:` key in `config.yaml`, independent of the model driving the agent's own reasoning loop (`QCA_MODEL` env var / `server.py`) — check `config.yaml` if `vlm_inspect` calls fail outright rather than returning a low-quality analysis; that's a separate model/endpoint from the one you're running in.

## Plot Resolution / Format by Experiment

| Experiment | Figure(s) | Size (matplotlib inches @ dpi=160) | Content |
|---|---|---|---|
| `qblox_resonator_spectroscopy` | 2-panel per qubit | 11×4.5 → ~1760×720 px | Left: \|S21\| vs frequency with fit + resonance marker. Right: I/Q scatter |
| `qblox_resonator_punchout_*` | 1 heatmap per qubit | 8×5 → ~1280×800 px | Attenuation/amplitude (y) vs frequency (x), normalized magnitude, tracked resonance line, recommended operating point marked |
| `qblox_time_of_flight` | 1 trace per qubit | 8×5 → ~1280×800 px | Magnitude vs acquisition time, fitted delay marked with a vertical line |
| `qblox_qubit_spectroscopy` | 1 plot, single panel | 8×5 → ~1280×800 px | Rotated signal vs drive frequency, Lorentzian fit overlaid, `fitted_f01` marked with a vertical line when the fit succeeds |

All matplotlib plots use labeled axes with units already baked in (GHz, dB, ns, V) and a `fig.suptitle`/`ax.set_title` naming the experiment and qubit — you don't need to ask the VLM to identify which qubit or experiment a plot belongs to, that's already in the image and in `plot_names`.

## What To Ask the VLM, By Plot Type

**Resonator spectroscopy (|S21| + fit)**
- Is there a single clear dip, multiple dips (multiplexed crosstalk or a stray resonance), or no visible dip at all?
- Does the fit curve track the data closely, or does it visibly diverge (indicates `fit_success=True` but a bad fit — R² alone can miss this)?
- Is the dip well inside the scan window, or pinned near an edge (matches `edge_margin_fraction`/`resonance_near_scan_edge`)?

**Qubit spectroscopy (rotated signal + Lorentzian fit)**
- Is there a single clear peak, or multiple peaks (could indicate a stray transition, `f12`, or a neighboring qubit's crosstalk)?
- Does the fit track the peak shape, or is it fitting to noise (low SNR peak that still reports `fit_success=True`)?
- Is the peak near either edge of the swept window — a sign `f01_width_mhz` should be widened and recentered?

**Punchout heatmap**
- Does the resonance frequency (dashed line) shift smoothly with attenuation/amplitude, or jump discontinuously?
- Is there a visible transition between a low-power (dispersive) and high-power (bare) regime, and does the recommended operating point (dotted line) sit in a stable region rather than right at a transition?
- Is contrast visibly washed out at the recommended point, contradicting `normalized_contrast`?

**Time of flight trace**
- Is there a clean step/edge in magnitude at the fitted delay, or a gradual/ambiguous rise?
- Is the pre-trigger baseline flat and low, or noisy/nonzero (indicates leakage or an attenuation problem — see `08_Common_Failures.md`)?

**General signal-quality checks applicable to any of the above**
- Saturation (flat-topped peaks/dips, clipped-looking traces)
- Excess noise relative to signal amplitude
- Periodic/oscillatory artifacts unrelated to the expected physics (interference, aliasing)

## Using the Result

`vlm_inspect`'s `analysis` field is free text — treat it as a second, independent opinion alongside the deterministic `accepted`/`failure_reasons`/`r_squared` fields already in the result, not a replacement for them. The numeric thresholds are what actually gate `apply_update`; the VLM is for catching things thresholds can miss (multiple resonances, saturation, an obviously wrong fit that still scores well numerically) or for explaining *why* something failed in a way a human can act on. When the two disagree — e.g. `accepted: true` but the VLM flags something odd — say so explicitly rather than picking one silently.
