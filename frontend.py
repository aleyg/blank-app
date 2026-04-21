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
# Theme Management - Professional Dark/Light Toggle
# ---------------------------------------------------------------------------
if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

def set_theme(theme):
    """Set application theme (dark/light)"""
    st.session_state.theme = theme
    st.rerun()

# Theme toggle button in header
col_header_left, col_header_right = st.columns([3, 1])
with col_header_left:
    st.markdown("# 🔭 Exposure Time Calculator")
with col_header_right:
    theme_btn = st.button(
        "🌙" if st.session_state.theme == 'dark' else "☀️", 
        key="theme_toggle",
        help="Toggle Light/Dark Theme",
        use_container_width=False
    )
    if theme_btn:
        new_theme = 'light' if st.session_state.theme == 'dark' else 'dark'
        set_theme(new_theme)

# Dynamic CSS based on theme
theme_colors = {
    'dark': {
        'bg_primary': '#0a0e17',
        'bg_secondary': '#0f1623',
        'bg_tertiary': '#111827',
        'text_primary': '#e2e8f0',
        'text_secondary': '#94a3b8',
        'text_muted': '#64748b',
        'border': '#1e293b',
        'border_accent': '#1e3a5f',
        'accent_primary': '#60a5fa',
        'accent_secondary': '#1d4ed8',
        'success': '#10b981',
        'warning': '#f59e0b',
        'gradient': 'linear-gradient(135deg, #0f2a4a 0%, #0a1628 100%)'
    },
    'light': {
        'bg_primary': '#f8fafc',
        'bg_secondary': '#f1f5f9',
        'bg_tertiary': '#ffffff',
        'text_primary': '#0f172a',
        'text_secondary': '#475569',
        'text_muted': '#64748b',
        'border': '#e2e8f0',
        'border_accent': '#cbd5e1',
        'accent_primary': '#3b82f6',
        'accent_secondary': '#1d4ed8',
        'success': '#059669',
        'warning': '#d97706',
        'gradient': 'linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 100%)'
    }
}

colors = theme_colors[st.session_state.theme]

css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Mono:wght@400;500;700&display=swap');

:root {{
  --bg-primary: {colors['bg_primary']};
  --bg-secondary: {colors['bg_secondary']};
  --bg-tertiary: {colors['bg_tertiary']};
  --text-primary: {colors['text_primary']};
  --text-secondary: {colors['text_secondary']};
  --text-muted: {colors['text_muted']};
  --border: {colors['border']};
  --border-accent: {colors['border_accent']};
  --accent-primary: {colors['accent_primary']};
  --accent-secondary: {colors['accent_secondary']};
}}

* {{
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}}

h1, h2, h3, h4 {{
  font-family: 'Space Mono', 'Roboto Mono', monospace !important;
  letter-spacing: -0.02em;
  font-weight: 600;
}}

.stApp {{
  background: var(--bg-primary);
  color: var(--text-primary);
}}

section[data-testid="stSidebar"] {{
  background: var(--bg-secondary) !important;
  border-right: 1px solid var(--border);
}}

div[data-testid="metric-container"] {{
  background: var(--bg-tertiary);
  border: 1px solid var(--border-accent);
  border-radius: 12px;
  padding: 1rem 1.25rem;
}}

.result-box {{
  background: {colors['gradient']};
  border: 1px solid var(--accent-secondary);
  border-radius: 16px;
  padding: 2rem 2.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0,0, 0.1);
}}

.snr-value {{
  font-family: 'Space Mono', monospace;
  font-size: 3.5rem;
  font-weight: 700;
  color: var(--accent-primary);
  line-height: 1;
  margin: 0.25rem 0;
}}

.regime-badge {{
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 1rem;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-family: 'Space Mono', monospace;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}}
.sky-limited {{ background: #164e63; color: #67e8f9; border: 1px solid #0e7490; }}
.read-noise-limited {{ background: #312e81; color: #a5b4fc; border: 1px solid #4338ca; }}
.shot-noise-limited {{ background: #14532d; color: #86efac; border: 1px solid #15803d; }}
.dark-limited {{ background: #431407; color: #fdba74; border: 1px solid #c2410c; }}

.info-row {{
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
  margin-top: 1rem;
}}
.info-item {{
  font-size: 0.875rem;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 0.25rem;
}}
.info-item span {{
  color: var(--text-primary);
  font-weight: 600;
}}

hr {{
  border: none;
  border-top: 1px solid var(--border);
  margin: 1.5rem 0;
}}

.stMetric > label {{
  color: var(--text-secondary) !important;
  font-weight: 500;
}}
.stMetric > div > div {{
  color: var(--text-primary) !important;
}}

button[kind="primary"] {{
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  border: none;
  border-radius: 12px;
  font-weight: 600;
  box-shadow: 0 4px 14px 0 rgba(59, 130, 246, 0.4);
}}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — Professional Input Controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🔭 Telescope Configuration")
    
    col_tel1, col_tel2 = st.columns(2)
    with col_tel1:
        diam = st.number_input(
            "Aperture (m)", min_value=0.1, max_value=40.0, 
            value=1.0, step=0.1, format="%.1f"
        )
    with col_tel2:
        obstruction = st.slider("Obstruction", 0.0, 0.4, 0.12, 0.01)
    
    throughput = st.slider("Throughput", 0.1, 1.0, 0.80, 0.01)
    
    st.divider()
    
    st.markdown("### 🌈 Filter & Instrument")
    col_mode1, col_mode2 = st.columns([2, 1])
    with col_mode1:
        mode = st.radio("Mode", ["Optical", "Near-IR"], horizontal=True)
    with col_mode2:
        filter_dict = OPTICAL_FILTERS if mode == "Optical" else NIR_FILTERS
        filter_name = st.selectbox("Filter", list(filter_dict.keys()), label_visibility="collapsed")
    
    filt = filter_dict[filter_name]
    det = detector_for_filter(filt)
    
    st.caption(f"**{filt.name}** | λ={filt.lambda_eff_angstrom/1000:.1f} nm | "
              f"Δλ={filt.delta_lambda_angstrom/1000:.0f} nm | "
              f"Sky={filt.sky_mag_arcsec2:.1f} mag/″²")
    
    st.divider()
    
    st.markdown("### ⭐ Target Source")
    source_type = st.radio("Type", ["Point source", "Extended"], horizontal=True)
    src = "point" if source_type == "Point source" else "extended"
    
    object_mag = st.number_input("Magnitude (AB)", 0.0, 35.0, 20.0, 0.1)
    
    st.divider()
    
    st.markdown("### ☁️ Observing Conditions")
    seeing = st.slider("Seeing (″)", 0.3, 3.0, 1.0, 0.05)
    ap_radius = st.slider("Aperture (″)", 0.3, 5.0, 1.5, 0.1)
    n_reads = st.number_input("N_reads", 1, 50, 1)
    
    st.divider()
    
    st.markdown("### ⚙️ Calculation")
    calc_mode = st.radio("Solve for", ["S/N", "Time"], horizontal=True,
                        format_func=lambda x: "S/N given t" if x == "S/N" else "t given S/N")
    
    if calc_mode == "S/N":
        exp_time = st.number_input("Exposure (s)", 0.1, 1e6, 600.0, 10.0)
        target_snr_input = None
    else:
        target_snr_input = st.number_input("Target S/N", 1.0, 1000.0, 10.0, 1.0)
        exp_time = None
    
    st.divider()
    
    # Plot range
    t_start_log = st.slider("t_min (log₁₀ s)", 0.0, 3.0, 0.5, 0.1)
    t_end_log = st.slider("t_max (log₁₀ s)", 1.0, 5.0, 3.6, 0.1)
    
    st.markdown("---")
    run_btn = st.button("🚀 Compute Exposure Time", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Parameter Assembly
# ---------------------------------------------------------------------------
telescope = TelescopeParams(diameter_m=diam, obstruction_fraction=obstruction)
conditions = ObservingConditions(
    seeing_fwhm_arcsec=seeing,
    aperture_radius_arcsec=ap_radius,
    total_throughput=throughput,
    n_reads=n_reads,
)

# ---------------------------------------------------------------------------
# Header Summary
# ---------------------------------------------------------------------------
st.markdown(f"""
**{mode} · {filter_name} · {diam:.1f}m · {object_mag:.1f} AB**
""")
st.divider()

# ---------------------------------------------------------------------------
# Main Computation & Results
# ---------------------------------------------------------------------------
if run_btn:
    try:
        if calc_mode == "S/N":
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
else:
    result = None
    error_msg = None

# Layout columns
col_main, col_side = st.columns([3, 2], gap="large")

with col_main:
    if error_msg:
        st.error(f"⚠️ {error_msg}")
    elif result:
        # Primary Results Card
        regime_css = result.noise_regime.replace(" ", "-").lower().replace("/", "-")
        regime_label = result.noise_regime
        
        if calc_mode == "S/N":
            primary_label = "Signal-to-Noise Ratio"
            primary_value = f"{result.snr:.1f}"
            secondary = f"Exposure: {format_time(result.exposure_time_s)}"
        else:
            primary_label = "Required Exposure"
            primary_value = format_time(result.time_for_target_snr)
            secondary = f"S/N = {result.snr:.1f} (target: {result.target_snr:.0f})"

        st.markdown(f"""
        <div class="result-box">
            <div style="font-size: 0.85rem; color: var(--text-secondary); 
                       letter-spacing: 0.1em; text-transform: uppercase;
                       font-family: 'Space Mono', monospace; margin-bottom: 0.5rem;">
                {primary_label}
            </div>
            <div class="snr-value">{primary_value}</div>
            <div style="color: var(--text-secondary); margin: 0.75rem 0 1rem 0; font-size: 1rem;">
                {secondary}
            </div>
            <div style="margin-bottom: 1.25rem;">
                <span class="regime-badge {regime_css}">{regime_label}</span>
            </div>
            <div class="info-row">
                <div class="info-item">Signal <span>{result.signal_e:.0f} e⁻</span></div>
                <div class="info-item">Sky <span>{result.sky_signal_e:.0f} e⁻</span></div>
                <div class="info-item">Dark <span>{result.dark_signal_e:.2f} e⁻</span></div>
                <div class="info-item">Read Noise <span>{result.read_noise_total_e2:.0f} e⁻²</span></div>
                <div class="info-item">Pixels <span>{result.n_pixels:.0f}</span></div>
                <div class="info-item">EE <span>{result.enclosed_energy*100:.1f}%</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Key Metrics
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Area", f"{telescope.collecting_area_m2:.2f} m²")
        mc2.metric("QE", f"{det.quantum_efficiency*100:.0f}%")
        mc3.metric("Read Noise", f"{det.read_noise_e:.1f} e⁻")
        mc4.metric("Dark Current", f"{det.dark_current_e_s:.3f} e⁻/s")
        
        # S/N vs Time Plot
        st.markdown("### S/N vs Exposure Time")
        t_arr, snr_arr = snr_vs_time(
            object_mag, telescope, filt, det, conditions, src,
            t_start=10**t_start_log, t_end=10**t_end_log,
        )
        
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor(colors['bg_primary'])
        ax.set_facecolor(colors['bg_secondary'])
        
        ax.plot(t_arr, snr_arr, color=colors['accent_primary'], lw=2.5, label="S/N")
        
        if result:
            t_op = result.time_for_target_snr if result.time_for_target_snr else result.exposure_time_s
            snr_op = result.snr
            ax.axvline(t_op, color="#f472b6", lw=2, ls="--", alpha=0.8, label="Operating Point")
            ax.axhline(snr_op, color="#f472b6", lw=2, ls="--", alpha=0.8)
            ax.scatter([t_op], [snr_op], color="#f472b6", s=100, zorder=5, edgecolors='white', linewidth=1)
        
        if target_snr_input:
            ax.axhline(target_snr_input, color=colors['warning'], lw=2, ls=":", alpha=0.8, label=f"Target S/N")
        
        ax.set_xscale("log")
        ax.set_xlabel("Exposure Time (s)", color=colors['text_secondary'], fontsize=12)
        ax.set_ylabel("Signal-to-Noise Ratio", color=colors['text_secondary'], fontsize=12)
        ax.tick_params(colors=colors['text_muted'])
        for spine in ax.spines.values():
            spine.set_color(colors['border'])
        ax.grid(True, color=colors['border'], linewidth=0.8, alpha=0.3)
        ax.legend(framealpha=0.9, facecolor=colors['bg_tertiary'], edgecolor=colors['border'], fontsize=10)
        ax.set_title(
            f"{object_mag:.1f} AB · {filt.name} · {diam:.1f}m",
            color=colors['text_muted'], fontsize=12, pad=15
        )
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

with col_side:
    st.markdown("### Detector")
    st.markdown(f"""
    | Parameter | Value |
    |-----------|-------|
    | Read Noise | {det.read_noise_e:.1f} e⁻/pix |
    | Dark Current | {det.dark_current_e_s:.3f} e⁻/s/pix |
    | Pixel Scale | {det.pixel_scale_arcsec:.2f}″/pix |
    | Quantum Eff. | {det.quantum_efficiency*100:.0f}% |
    """)
    
    st.markdown("### Filter")
    st.markdown(f"""
    | Parameter | Value |
    |-----------|-------|
    | Band | {filt.name} |
    | λ<sub>eff</sub> | {filt.lambda_eff_angstrom:.0f} Å |
    | Δλ | {filt.delta_lambda_angstrom:.0f} Å |
    | Sky | {filt.sky_mag_arcsec2:.1f} mag/″² |
    | Mode | {filt.mode} |
    """)
    
    st.markdown("### Model")
    st.latex(r"""
    $$ \frac{S}{N} = \frac{S}{\sqrt{S + n_\mathrm{sky} + n_\mathrm{dark} + \sigma^2_\mathrm{RON} \cdot n_\mathrm{pix} \cdot n_\mathrm{reads}}} $$
    """)
    
    with st.expander("Noise Regimes", expanded=False):
        st.markdown("""
        - **🟢 Sky-limited** — Sky background dominates  
        - **🟣 Read-noise-limited** — Short exposures
        - **🟡 Shot-noise-limited** — Bright sources  
        - **🔴 Dark-limited** — Very long exposures
        """)
    
    st.markdown("### Assumptions")
    st.caption("""
    - Gaussian PSF (Moffat more realistic)  
    - No airmass extinction
    - Single filter/epoch
    - Fixed sky brightness
    - Flat QE in bandpass
    """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: var(--text-muted); font-size: 0.8rem;'>"
    "Astronomical Exposure Time Calculator | Professional Astronomy Tools</div>", 
    unsafe_allow_html=True
)