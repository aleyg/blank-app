"""
frontend.py — Exposure Time Calculator (ETC) — Streamlit Interface
===================================================================
Run with:
    streamlit run frontend.py

This module is responsible exclusively for:
  - Capturing user inputs (sidebar widgets)
  - Calling backend functions
  - Displaying results, plots and diagnostics

No physics lives here. All science is imported from backend.py.
"""

import math

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import streamlit as st

from backend import (
    ALL_FILTERS,
    NIR_FILTERS,
    OPTICAL_FILTERS,
    ETCResult,
    ObservingConditions,
    TelescopeParams,
    compute_exposure_time,
    compute_snr,
    detector_for_filter,
    format_time,
    snr_vs_time,
)

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Exposure Time Calculator",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — dark observatory aesthetic
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
h1, h2, h3 {
    font-family: 'Space Mono', monospace !important;
    letter-spacing: -0.03em;
}
.stApp {
    background: #0a0e17;
    color: #e2e8f0;
}
section[data-testid="stSidebar"] {
    background: #0f1623 !important;
    border-right: 1px solid #1e293b;
}
/* Metric cards */
div[data-testid="metric-container"] {
    background: #111827;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 12px 18px;
}
/* Result box */
.result-box {
    background: linear-gradient(135deg, #0f2a4a 0%, #0a1628 100%);
    border: 1px solid #1d4ed8;
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 20px;
}
.snr-value {
    font-family: 'Space Mono', monospace;
    font-size: 3.2rem;
    font-weight: 700;
    color: #60a5fa;
    line-height: 1.0;
}
.regime-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-family: 'Space Mono', monospace;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.sky-limited      { background:#164e63; color:#67e8f9; border:1px solid #0e7490; }
.read-noise-limited { background:#312e81; color:#a5b4fc; border:1px solid #4338ca; }
.shot-noise-limited { background:#14532d; color:#86efac; border:1px solid #15803d; }
.dark-limited      { background:#431407; color:#fdba74; border:1px solid #c2410c; }
.info-row { display:flex; gap:24px; flex-wrap:wrap; margin-top:14px; }
.info-item { font-size:0.82rem; color:#94a3b8; }
.info-item span { color:#e2e8f0; font-weight:600; }
hr.dim { border:none; border-top:1px solid #1e293b; margin:18px 0; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar — all inputs
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("# 🔭 ETC")
    st.markdown("**Exposure Time Calculator**")
    st.caption("Optical / Near-IR · ESO-inspired model")
    st.markdown("---")

    # --- Telescope ---
    st.markdown("### Telescope")
    diam = st.number_input(
        "Primary diameter (m)",
        min_value=0.1, max_value=40.0, value=1.0, step=0.1,
        help="Effective aperture of the primary mirror in meters.",
    )
    obstruction = st.slider(
        "Central obstruction (linear fraction)",
        min_value=0.0, max_value=0.4, value=0.12, step=0.01,
        help="Fraction of the primary diameter blocked by the secondary mirror.",
    )
    throughput = st.slider(
        "Total system throughput",
        min_value=0.1, max_value=1.0, value=0.80, step=0.01,
        help="Combined transmission of telescope optics, mirrors and filter.",
    )

    st.markdown("---")
    # --- Filter / Instrument ---
    st.markdown("### Filter & Mode")
    mode = st.radio("Observing mode", ["Optical", "Near-IR"], horizontal=True)
    filter_dict = OPTICAL_FILTERS if mode == "Optical" else NIR_FILTERS
    filter_name = st.selectbox("Filter", list(filter_dict.keys()))
    filt = filter_dict[filter_name]
    det  = detector_for_filter(filt)

    st.caption(
        f"λ_eff = {filt.lambda_eff_angstrom:.0f} Å  ·  "
        f"Δλ = {filt.delta_lambda_angstrom:.0f} Å  ·  "
        f"Sky = {filt.sky_mag_arcsec2:.1f} mag/arcsec²"
    )

    st.markdown("---")
    # --- Source ---
    st.markdown("### Source")
    source_type = st.radio("Source type", ["Point source", "Extended"],
                            horizontal=True)
    src = "point" if source_type == "Point source" else "extended"
    object_mag = st.number_input(
        "Object magnitude (AB)",
        min_value=0.0, max_value=35.0, value=20.0, step=0.1,
        help="AB magnitude of the target in the selected filter.",
    )

    st.markdown("---")
    # --- Observing conditions ---
    st.markdown("### Observing Conditions")
    seeing = st.slider(
        "Seeing FWHM (arcsec)",
        min_value=0.3, max_value=3.0, value=1.0, step=0.05,
    )
    ap_radius = st.slider(
        "Aperture radius (arcsec)",
        min_value=0.3, max_value=5.0, value=1.5, step=0.1,
        help="Radius of the circular photometric aperture.",
    )
    n_reads = st.number_input(
        "Number of detector reads",
        min_value=1, max_value=50, value=1,
        help="For NIR up-the-ramp sampling, set > 1.",
    )

    st.markdown("---")
    # --- Calculation mode ---
    st.markdown("### Calculation Mode")
    calc_mode = st.radio(
        "Solve for …",
        ["S/N given exposure time", "Exposure time given S/N"],
        help="Choose whether you specify time or target S/N.",
    )

    if calc_mode == "S/N given exposure time":
        exp_time = st.number_input(
            "Exposure time (s)",
            min_value=0.1, max_value=1e6, value=600.0, step=10.0,
        )
        target_snr_input = None
    else:
        target_snr_input = st.number_input(
            "Target S/N",
            min_value=1.0, max_value=1000.0, value=10.0, step=1.0,
        )
        exp_time = None

    # --- S/N vs t plot range ---
    st.markdown("---")
    st.markdown("### Plot range")
    t_start_log = st.slider("t_min  log₁₀(s)", 0.0, 3.0, 0.5, 0.1)
    t_end_log   = st.slider("t_max  log₁₀(s)", 1.0, 5.0, 3.6, 0.1)

    run_btn = st.button("▶  Calculate", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Assemble parameter objects
# ---------------------------------------------------------------------------

telescope  = TelescopeParams(diameter_m=diam, obstruction_fraction=obstruction)
conditions = ObservingConditions(
    seeing_fwhm_arcsec=seeing,
    aperture_radius_arcsec=ap_radius,
    total_throughput=throughput,
    n_reads=n_reads,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown("# Exposure Time Calculator")
st.markdown(
    f"**{mode} mode** · Filter **{filter_name}** · "
    f"Telescope **{diam:.1f} m** · "
    f"Object **{object_mag:.1f} AB mag**"
)
st.markdown("---")

# ---------------------------------------------------------------------------
# Run calculation
# ---------------------------------------------------------------------------

if run_btn or True:   # compute on every interaction (Streamlit's default model)
    try:
        if calc_mode == "S/N given exposure time":
            result: ETCResult = compute_snr(
                object_mag, exp_time, telescope, filt, det, conditions, src
            )
        else:
            result: ETCResult = compute_exposure_time(
                object_mag, target_snr_input, telescope, filt, det, conditions, src
            )

        error_msg = None
    except ValueError as exc:
        error_msg = str(exc)
        result = None

    # -----------------------------------------------------------------------
    # Display results
    # -----------------------------------------------------------------------

    col_main, col_side = st.columns([3, 2], gap="large")

    with col_main:

        if error_msg:
            st.error(f"⚠️  {error_msg}")
        else:
            # --- Primary result box ---
            regime_css = result.noise_regime.replace(" ", "-").replace("/", "-")
            regime_label = result.noise_regime

            if calc_mode == "S/N given exposure time":
                primary_label = "Signal-to-Noise Ratio"
                primary_value = f"{result.snr:.2f}"
                secondary = f"Exposure time: {format_time(result.exposure_time_s)}"
            else:
                primary_label = "Required Exposure Time"
                primary_value = format_time(result.time_for_target_snr)
                secondary = f"Achieved S/N = {result.snr:.2f}  (target: {result.target_snr:.1f})"

            st.markdown(f"""
<div class="result-box">
  <div style="font-size:0.8rem;color:#64748b;letter-spacing:0.08em;text-transform:uppercase;
              font-family:'Space Mono',monospace;margin-bottom:6px;">{primary_label}</div>
  <div class="snr-value">{primary_value}</div>
  <div style="color:#94a3b8;margin-top:6px;font-size:0.9rem;">{secondary}</div>
  <div style="margin-top:12px;">
    <span class="regime-badge {regime_css}">{regime_label}</span>
  </div>
  <div class="info-row">
    <div class="info-item">Signal <span>{result.signal_e:.1f} e⁻</span></div>
    <div class="info-item">Sky noise <span>{result.sky_signal_e:.1f} e⁻</span></div>
    <div class="info-item">Dark current <span>{result.dark_signal_e:.2f} e⁻</span></div>
    <div class="info-item">RON² × n_pix <span>{result.read_noise_total_e2:.1f} e⁻²</span></div>
    <div class="info-item">Aperture pixels <span>{result.n_pixels:.1f}</span></div>
    <div class="info-item">Enclosed energy <span>{result.enclosed_energy*100:.1f} %</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

            # --- Metrics row ---
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Coll. area", f"{telescope.collecting_area_m2:.3f} m²")
            mc2.metric("QE", f"{det.quantum_efficiency*100:.0f} %")
            mc3.metric("Read noise", f"{det.read_noise_e} e⁻/pix")
            mc4.metric("Dark current", f"{det.dark_current_e_s} e⁻/s/pix")

        # --- S/N vs time plot ---
        st.markdown("### S/N vs. Exposure Time")

        t_arr, snr_arr = snr_vs_time(
            object_mag, telescope, filt, det, conditions, src,
            t_start=10**t_start_log, t_end=10**t_end_log,
        )

        fig, ax = plt.subplots(figsize=(8, 4))
        fig.patch.set_facecolor("#0a0e17")
        ax.set_facecolor("#0f1623")

        ax.plot(t_arr, snr_arr, color="#60a5fa", lw=2.2, label="S/N")

        # Overplot current operating point
        if result and not error_msg:
            t_op  = result.time_for_target_snr if result.time_for_target_snr else result.exposure_time_s
            snr_op = result.snr
            ax.axvline(t_op, color="#f472b6", lw=1.2, ls="--", alpha=0.8)
            ax.axhline(snr_op, color="#f472b6", lw=1.2, ls="--", alpha=0.8)
            ax.scatter([t_op], [snr_op], color="#f472b6", s=80, zorder=5,
                       label=f"Operating point ({format_time(t_op)}, S/N={snr_op:.1f})")

        if target_snr_input and calc_mode == "Exposure time given S/N":
            ax.axhline(target_snr_input, color="#fbbf24", lw=1.0, ls=":",
                       alpha=0.7, label=f"Target S/N = {target_snr_input:.0f}")

        ax.set_xscale("log")
        ax.set_xlabel("Exposure time (s)", color="#94a3b8", fontsize=11)
        ax.set_ylabel("S/N", color="#94a3b8", fontsize=11)
        ax.tick_params(colors="#64748b")
        for spine in ax.spines.values():
            spine.set_color("#1e293b")
        ax.xaxis.set_major_formatter(mticker.ScalarFormatter())
        ax.xaxis.set_minor_formatter(mticker.NullFormatter())
        ax.grid(True, color="#1e293b", linewidth=0.6, which="both")
        legend = ax.legend(framealpha=0.0, labelcolor="#94a3b8", fontsize=9)
        ax.set_title(
            f"mag={object_mag:.1f} AB · {filt.name}-band · Ø{diam:.1f} m",
            color="#64748b", fontsize=9, pad=8
        )
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    # -----------------------------------------------------------------------
    # Side column — detector & filter info
    # -----------------------------------------------------------------------
    with col_side:
        st.markdown("### Detector Parameters")
        st.markdown(f"""
| Parameter | Value |
|-----------|-------|
| Read noise | {det.read_noise_e} e⁻/pix |
| Dark current | {det.dark_current_e_s} e⁻/s/pix |
| Pixel scale | {det.pixel_scale_arcsec} arcsec/pix |
| Quantum efficiency | {det.quantum_efficiency*100:.0f} % |
""")
        st.markdown("### Filter Parameters")
        st.markdown(f"""
| Parameter | Value |
|-----------|-------|
| Band | {filt.name} |
| λ_eff | {filt.lambda_eff_angstrom:.0f} Å |
| Δλ | {filt.delta_lambda_angstrom:.0f} Å |
| Sky brightness | {filt.sky_mag_arcsec2:.1f} mag/arcsec² |
| Mode | {filt.mode} |
""")
        st.markdown("### Physical Model")
        st.latex(r"""
\frac{S}{N} = \frac{S}{\sqrt{S + N_\mathrm{sky} + N_\mathrm{dark} + \sigma_\mathrm{RON}^2 \cdot n_\mathrm{pix} \cdot n_\mathrm{reads}}}
""")
        st.markdown("""
**Terms:**
- **S** = object signal [e⁻]
- **N_sky** = sky background [e⁻]  
- **N_dark** = dark current [e⁻]  
- **σ_RON² · n_pix** = read-noise variance [e⁻²]

**Noise regimes:**
- 🔵 **Sky-limited** — sky dominates (most observations)
- 🟣 **Read-noise-limited** — short exposures / faint sky
- 🟢 **Shot-noise-limited** — bright sources
- 🟠 **Dark-limited** — long exposures, low sky
""")

        st.markdown("### Assumptions & Limitations")
        st.caption("""
- Gaussian PSF; real PSFs include wings (Moffat profile)
- No atmospheric dispersion or extinction
- Single-filter, single-epoch model
- Sky surface brightness is fixed (no moon-phase correction)
- Flat detector response within the filter bandpass
""")
