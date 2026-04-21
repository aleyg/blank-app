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

import streamlit as st
import plotly.graph_objects as go

from backend import (
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
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Exposure Time Calculator",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Theme state
# ---------------------------------------------------------------------------
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "dark"

theme = st.session_state["theme_mode"]

# ---------------------------------------------------------------------------
# Theme tokens
# ---------------------------------------------------------------------------
THEMES = {
    "light": {
        "bg": "#f3f6fb",
        "bg_soft": "#eef2f8",
        "surface": "#ffffff",
        "surface_2": "#f8fafc",
        "sidebar": "#eef2f8",
        "border": "#d8e0ea",
        "border_strong": "#c4cfdb",
        "text": "#17212b",
        "text_muted": "#5f6c7b",
        "text_soft": "#7b8794",
        "accent": "#1d4ed8",
        "accent_2": "#0f766e",
        "accent_soft": "rgba(37, 99, 235, 0.10)",
        "shadow": "0 12px 28px rgba(15, 23, 42, 0.08)",
        "metric_bg": "#f8fafc",
        "metric_border": "#dbe3ec",
        "topbar_bg": "rgba(255,255,255,0.78)",
        "topbar_border": "rgba(203,213,225,0.8)",
        "plot_bg": "#ffffff",
        "plot_paper": "#ffffff",
        "plot_grid": "#e5e7eb",
        "plot_axis": "#1f2937",
        "plot_line": "#2563eb",
        "plot_point": "#be123c",
        "plot_target": "#d97706",
        "sky_bg": "rgba(13, 148, 136, 0.10)",
        "sky_text": "#0f766e",
        "sky_border": "rgba(13, 148, 136, 0.32)",
        "read_bg": "rgba(79, 70, 229, 0.10)",
        "read_text": "#4338ca",
        "read_border": "rgba(79, 70, 229, 0.32)",
        "shot_bg": "rgba(22, 163, 74, 0.10)",
        "shot_text": "#15803d",
        "shot_border": "rgba(22, 163, 74, 0.32)",
        "dark_bg": "rgba(180, 83, 9, 0.10)",
        "dark_text": "#b45309",
        "dark_border": "rgba(180, 83, 9, 0.32)",
    },
    "dark": {
        "bg": "#07101d",
        "bg_soft": "#0b1627",
        "surface": "#0d1728",
        "surface_2": "#101c31",
        "sidebar": "#08111f",
        "border": "#213149",
        "border_strong": "#334155",
        "text": "#e5e7eb",
        "text_muted": "#b2bdca",
        "text_soft": "#7f8a99",
        "accent": "#60a5fa",
        "accent_2": "#2dd4bf",
        "accent_soft": "rgba(96, 165, 250, 0.12)",
        "shadow": "0 16px 36px rgba(0, 0, 0, 0.28)",
        "metric_bg": "#101c31",
        "metric_border": "#22324a",
        "topbar_bg": "rgba(7,16,29,0.72)",
        "topbar_border": "rgba(51,65,85,0.75)",
        "plot_bg": "#0d1728",
        "plot_paper": "#0d1728",
        "plot_grid": "#23344c",
        "plot_axis": "#e5e7eb",
        "plot_line": "#60a5fa",
        "plot_point": "#f9a8d4",
        "plot_target": "#fbbf24",
        "sky_bg": "rgba(34, 211, 238, 0.10)",
        "sky_text": "#67e8f9",
        "sky_border": "rgba(34, 211, 238, 0.28)",
        "read_bg": "rgba(165, 180, 252, 0.10)",
        "read_text": "#c7d2fe",
        "read_border": "rgba(165, 180, 252, 0.28)",
        "shot_bg": "rgba(134, 239, 172, 0.10)",
        "shot_text": "#86efac",
        "shot_border": "rgba(134, 239, 172, 0.28)",
        "dark_bg": "rgba(251, 191, 36, 0.10)",
        "dark_text": "#fcd34d",
        "dark_border": "rgba(251, 191, 36, 0.28)",
    },
}

T = THEMES[theme]

# ---------------------------------------------------------------------------
# Theme toggle function
# ---------------------------------------------------------------------------
def toggle_theme():
    st.session_state["theme_mode"] = "light" if st.session_state["theme_mode"] == "dark" else "dark"

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Source+Serif+4:wght@400;600;700&display=swap');

:root {{
  --bg: {T["bg"]};
  --bg-soft: {T["bg_soft"]};
  --surface: {T["surface"]};
  --surface-2: {T["surface_2"]};
  --sidebar: {T["sidebar"]};
  --border: {T["border"]};
  --border-strong: {T["border_strong"]};
  --text: {T["text"]};
  --text-muted: {T["text_muted"]};
  --text-soft: {T["text_soft"]};
  --accent: {T["accent"]};
  --accent-2: {T["accent_2"]};
  --accent-soft: {T["accent_soft"]};
  --metric-bg: {T["metric_bg"]};
  --metric-border: {T["metric_border"]};
  --topbar-bg: {T["topbar_bg"]};
  --topbar-border: {T["topbar_border"]};
  --shadow: {T["shadow"]};

  --sky-bg: {T["sky_bg"]};
  --sky-text: {T["sky_text"]};
  --sky-border: {T["sky_border"]};

  --read-bg: {T["read_bg"]};
  --read-text: {T["read_text"]};
  --read-border: {T["read_border"]};

  --shot-bg: {T["shot_bg"]};
  --shot-text: {T["shot_text"]};
  --shot-border: {T["shot_border"]};

  --dark-bg: {T["dark_bg"]};
  --dark-text: {T["dark_text"]};
  --dark-border: {T["dark_border"]};
}}

html, body, [class*="css"] {{
  font-family: 'Inter', sans-serif;
}}

body {{
  color: var(--text);
}}

.stApp {{
  background:
    radial-gradient(circle at top left, rgba(59,130,246,0.08), transparent 26%),
    linear-gradient(180deg, var(--bg) 0%, var(--bg-soft) 100%);
  color: var(--text);
}}

section[data-testid="stSidebar"] {{
  background: var(--sidebar) !important;
  border-right: 1px solid var(--border);
}}

section[data-testid="stSidebar"] .block-container {{
  padding-top: 1.2rem;
}}

h1, h2, h3 {{
  font-family: 'Source Serif 4', serif !important;
  color: var(--text);
  letter-spacing: -0.02em;
}}

h1 {{
  font-size: 2rem;
  line-height: 1.05;
}}

h2 {{
  font-size: 1.3rem;
  line-height: 1.12;
}}

h3 {{
  font-size: 1.03rem;
  line-height: 1.15;
}}

p, li, div, span, label {{
  color: var(--text);
}}

small, .stCaption, [data-testid="stCaptionContainer"] {{
  color: var(--text-muted) !important;
}}

div[data-testid="metric-container"] {{
  background: var(--metric-bg);
  border: 1px solid var(--metric-border);
  border-radius: 16px;
  padding: 14px 16px;
}}

div[data-testid="metric-container"] label {{
  color: var(--text-soft) !important;
  font-size: 0.78rem !important;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}}

.topbar {{
  position: sticky;
  top: 0;
  z-index: 10;
  backdrop-filter: blur(14px);
  background: var(--topbar-bg);
  border: 1px solid var(--topbar-border);
  border-radius: 18px;
  padding: 0.95rem 1.1rem;
  margin-bottom: 1rem;
  box-shadow: var(--shadow);
}}

.kicker {{
  color: var(--accent);
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  margin-bottom: 0.18rem;
}}

.topbar-title {{
  font-family: 'Source Serif 4', serif;
  color: var(--text);
  font-size: 1.7rem;
  font-weight: 700;
  line-height: 1.05;
}}

.topbar-subtitle {{
  color: var(--text-muted);
  font-size: 0.92rem;
  margin-top: 0.20rem;
}}

.hero-meta {{
  color: var(--text-muted);
  font-size: 0.94rem;
  margin-top: 0.25rem;
  margin-bottom: 1rem;
}}

.result-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 1.25rem 1.25rem 1rem 1.25rem;
  box-shadow: var(--shadow);
  margin-bottom: 1rem;
}}

.card-section {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 1rem 1rem 0.85rem 1rem;
  box-shadow: var(--shadow);
  margin-bottom: 1rem;
}}

.section-kicker {{
  color: var(--accent);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 0.2rem;
}}

.result-label {{
  color: var(--text-soft);
  font-size: 0.76rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}}

.result-value {{
  font-family: 'Source Serif 4', serif;
  color: var(--accent);
  font-size: 3rem;
  font-weight: 700;
  line-height: 1.0;
  margin-top: 0.3rem;
}}

.result-subtitle {{
  color: var(--text-muted);
  font-size: 0.94rem;
  margin-top: 0.35rem;
}}

.regime-badge {{
  display: inline-flex;
  align-items: center;
  padding: 0.28rem 0.78rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border: 1px solid transparent;
  margin-top: 0.85rem;
}}

.sky-limited {{
  background: var(--sky-bg);
  color: var(--sky-text);
  border-color: var(--sky-border);
}}

.read-noise-limited {{
  background: var(--read-bg);
  color: var(--read-text);
  border-color: var(--read-border);
}}

.shot-noise-limited {{
  background: var(--shot-bg);
  color: var(--shot-text);
  border-color: var(--shot-border);
}}

.dark-limited {{
  background: var(--dark-bg);
  color: var(--dark-text);
  border-color: var(--dark-border);
}}

.info-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.8rem 1rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}}

.info-item {{
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}}

.info-item-label {{
  color: var(--text-soft);
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

.info-item-value {{
  color: var(--text);
  font-size: 0.9rem;
  font-weight: 600;
}}

.meta-line {{
  color: var(--text-muted);
  font-size: 0.93rem;
  margin-bottom: 0.9rem;
}}

.eq-box {{
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 0.85rem 0.85rem 0.35rem 0.85rem;
  margin: 0.5rem 0 0.8rem 0;
}}

.table-clean table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}}

.table-clean th, .table-clean td {{
  text-align: left;
  padding: 0.5rem 0.25rem;
  border-bottom: 1px solid var(--border);
}}

.table-clean th {{
  color: var(--text-soft);
  font-weight: 600;
}}

button[kind="primary"] {{
  border-radius: 999px !important;
  font-weight: 600 !important;
}}

.stButton > button {{
  border-radius: 999px !important;
}}

.plot-wrapper {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 0.9rem 0.9rem 0.4rem 0.9rem;
  box-shadow: var(--shadow);
}}

@media (max-width: 900px) {{
  .topbar-title {{
    font-size: 1.4rem;
  }}
  .result-value {{
    font-size: 2.35rem;
  }}
}}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🔭 Configuration")
    st.caption("Optical / Near-IR · ESO-inspired model")

    st.markdown("---")
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
    st.markdown("### Filter & Mode")
    mode = st.radio("Observing mode", ["Optical", "Near-IR"], horizontal=True)
    filter_dict = OPTICAL_FILTERS if mode == "Optical" else NIR_FILTERS
    filter_name = st.selectbox("Filter", list(filter_dict.keys()))
    filt = filter_dict[filter_name]
    det = detector_for_filter(filt)

    st.caption(
        f"λ_eff = {filt.lambda_eff_angstrom:.0f} Å · "
        f"Δλ = {filt.delta_lambda_angstrom:.0f} Å · "
        f"Sky = {filt.sky_mag_arcsec2:.1f} mag/arcsec²"
    )

    st.markdown("---")
    st.markdown("### Source")
    source_type = st.radio("Source type", ["Point source", "Extended"], horizontal=True)
    src = "point" if source_type == "Point source" else "extended"

    object_mag = st.number_input(
        "Object magnitude (AB)",
        min_value=0.0, max_value=35.0, value=20.0, step=0.1,
        help="AB magnitude of the target in the selected filter.",
    )

    st.markdown("---")
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

    st.markdown("---")
    st.markdown("### Plot range")
    t_start_log = st.slider("t_min  log₁₀(s)", 0.0, 3.0, 0.5, 0.1)
    t_end_log = st.slider("t_max  log₁₀(s)", 1.0, 5.0, 3.6, 0.1)

# ---------------------------------------------------------------------------
# Top bar
# ---------------------------------------------------------------------------
top_left, top_spacer, top_right = st.columns([10, 1, 1.2])

with top_left:
    st.markdown(
        """
<div class="topbar">
  <div class="kicker">Academic Observation Toolkit</div>
  <div class="topbar-title">Exposure Time Calculator</div>
  <div class="topbar-subtitle">
    Photometric ETC for optical and near-infrared observations with dynamic theming and publication-grade visual output.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

with top_right:
    st.write("")
    st.write("")
    st.button(
        "🌙" if theme == "light" else "☀️",
        help="Cambiar tema",
        on_click=toggle_theme,
        use_container_width=True,
    )

st.markdown(
    f"""
<div class="meta-line">
<strong>{mode} mode</strong> · Filter <strong>{filter_name}</strong> ·
Telescope <strong>{diam:.1f} m</strong> · Target <strong>{object_mag:.1f} AB mag</strong>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Assemble parameter objects
# ---------------------------------------------------------------------------
telescope = TelescopeParams(diameter_m=diam, obstruction_fraction=obstruction)
conditions = ObservingConditions(
    seeing_fwhm_arcsec=seeing,
    aperture_radius_arcsec=ap_radius,
    total_throughput=throughput,
    n_reads=n_reads,
)

# ---------------------------------------------------------------------------
# Run calculation
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
col_main, col_side = st.columns([3.2, 1.8], gap="large")

with col_main:
    st.markdown("## Results")

    if error_msg:
        st.error(f"⚠️ {error_msg}")
    else:
        regime_css = result.noise_regime.replace(" ", "-").replace("/", "-")
        regime_label = result.noise_regime

        if calc_mode == "S/N given exposure time":
            primary_label = "Signal-to-noise ratio"
            primary_value = f"{result.snr:.2f}"
            secondary = f"Exposure time: {format_time(result.exposure_time_s)}"
        else:
            primary_label = "Required exposure time"
            primary_value = format_time(result.time_for_target_snr)
            secondary = (
                f"Achieved S/N = {result.snr:.2f} "
                f"(target: {result.target_snr:.1f})"
            )

        st.markdown(
            f"""
<div class="result-card">
  <div class="section-kicker">Primary output</div>
  <div class="result-label">{primary_label}</div>
  <div class="result-value">{primary_value}</div>
  <div class="result-subtitle">{secondary}</div>
  <span class="regime-badge {regime_css}">{regime_label}</span>

  <div class="info-grid">
    <div class="info-item">
      <div class="info-item-label">Signal</div>
      <div class="info-item-value">{result.signal_e:.1f} e⁻</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">Sky signal</div>
      <div class="info-item-value">{result.sky_signal_e:.1f} e⁻</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">Dark current</div>
      <div class="info-item-value">{result.dark_signal_e:.2f} e⁻</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">RON² × n_pix</div>
      <div class="info-item-value">{result.read_noise_total_e2:.1f} e⁻²</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">Aperture pixels</div>
      <div class="info-item-value">{result.n_pixels:.1f}</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">Enclosed energy</div>
      <div class="info-item-value">{result.enclosed_energy*100:.1f} %</div>
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Collecting area", f"{telescope.collecting_area_m2:.3f} m²")
        m2.metric("Quantum efficiency", f"{det.quantum_efficiency*100:.0f} %")
        m3.metric("Read noise", f"{det.read_noise_e} e⁻/pix")
        m4.metric("Dark current", f"{det.dark_current_e_s} e⁻/s/pix")

    st.markdown("## S/N as a function of exposure time")

    t_arr, snr_arr = snr_vs_time(
        object_mag,
        telescope,
        filt,
        det,
        conditions,
        src,
        t_start=10 ** t_start_log,
        t_end=10 ** t_end_log,
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=t_arr,
            y=snr_arr,
            mode="lines",
            name="S/N curve",
            line=dict(color=T["plot_line"], width=3),
            hovertemplate="t = %{x:.2f} s<br>S/N = %{y:.2f}<extra></extra>",
        )
    )

    if result and not error_msg:
        t_op = result.time_for_target_snr if result.time_for_target_snr else result.exposure_time_s
        snr_op = result.snr

        fig.add_trace(
            go.Scatter(
                x=[t_op],
                y=[snr_op],
                mode="markers",
                name="Operating point",
                marker=dict(color=T["plot_point"], size=10, line=dict(width=1, color=T["plot_paper"])),
                hovertemplate=f"Operating point<br>t = {t_op:.2f} s<br>S/N = {snr_op:.2f}<extra></extra>",
            )
        )

        fig.add_vline(
            x=t_op,
            line_width=1.2,
            line_dash="dash",
            line_color=T["plot_point"],
            opacity=0.85,
        )
        fig.add_hline(
            y=snr_op,
            line_width=1.2,
            line_dash="dash",
            line_color=T["plot_point"],
            opacity=0.85,
        )

    if target_snr_input and calc_mode == "Exposure time given S/N":
        fig.add_hline(
            y=target_snr_input,
            line_width=1.1,
            line_dash="dot",
            line_color=T["plot_target"],
            annotation_text=f"Target S/N = {target_snr_input:.0f}",
            annotation_position="top left",
        )

    fig.update_layout(
        template="plotly_dark" if theme == "dark" else "plotly_white",
        height=430,
        margin=dict(l=30, r=25, t=50, b=30),
        paper_bgcolor=T["plot_paper"],
        plot_bgcolor=T["plot_bg"],
        font=dict(family="Inter, sans-serif", size=13, color=T["plot_axis"]),
        title=dict(
            text=f"{filt.name}-band · {object_mag:.1f} AB mag · D = {diam:.1f} m",
            font=dict(size=15, color=T["plot_axis"]),
            x=0.02,
            xanchor="left",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0.0,
            bgcolor="rgba(0,0,0,0)",
        ),
    )

    fig.update_xaxes(
        type="log",
        title="Exposure time (s)",
        showgrid=True,
        gridcolor=T["plot_grid"],
        zeroline=False,
        linecolor=T["plot_grid"],
        tickfont=dict(size=12),
        title_font=dict(size=13),
    )

    fig.update_yaxes(
        title="Signal-to-noise ratio",
        showgrid=True,
        gridcolor=T["plot_grid"],
        zeroline=False,
        linecolor=T["plot_grid"],
        tickfont=dict(size=12),
        title_font=dict(size=13),
    )

    st.markdown('<div class="plot-wrapper">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

with col_side:
    st.markdown("## Technical details")

    with st.container():
        st.markdown('<div class="card-section">', unsafe_allow_html=True)
        st.markdown("### Detector Parameters")
        st.markdown(
            f"""
<div class="table-clean">
<table>
<thead>
<tr><th>Parameter</th><th>Value</th></tr>
</thead>
<tbody>
<tr><td>Read noise</td><td>{det.read_noise_e} e⁻/pix</td></tr>
<tr><td>Dark current</td><td>{det.dark_current_e_s} e⁻/s/pix</td></tr>
<tr><td>Pixel scale</td><td>{det.pixel_scale_arcsec} arcsec/pix</td></tr>
<tr><td>Quantum efficiency</td><td>{det.quantum_efficiency*100:.0f} %</td></tr>
</tbody>
</table>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="card-section">', unsafe_allow_html=True)
        st.markdown("### Filter Parameters")
        st.markdown(
            f"""
<div class="table-clean">
<table>
<thead>
<tr><th>Parameter</th><th>Value</th></tr>
</thead>
<tbody>
<tr><td>Band</td><td>{filt.name}</td></tr>
<tr><td>λ_eff</td><td>{filt.lambda_eff_angstrom:.0f} Å</td></tr>
<tr><td>Δλ</td><td>{filt.delta_lambda_angstrom:.0f} Å</td></tr>
<tr><td>Sky brightness</td><td>{filt.sky_mag_arcsec2:.1f} mag/arcsec²</td></tr>
<tr><td>Mode</td><td>{filt.mode}</td></tr>
</tbody>
</table>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="card-section">', unsafe_allow_html=True)
        st.markdown("### Physical Model")
        st.markdown('<div class="eq-box">', unsafe_allow_html=True)
        st.latex(
            r"""
\frac{S}{N} =
\frac{S}{
\sqrt{
S + N_\mathrm{sky} + N_\mathrm{dark}
+ \sigma_\mathrm{RON}^{2}\, n_\mathrm{pix}\, n_\mathrm{reads}
}}
"""
        )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(
            """
**Terms**
- **S** = object signal [e⁻]
- **N_sky** = sky background [e⁻]
- **N_dark** = dark current [e⁻]
- **σ_RON² · n_pix · n_reads** = read-noise variance [e⁻²]

**Noise regimes**
- 🔵 **Sky-limited** — sky dominates
- 🟣 **Read-noise-limited** — short exposures or faint sky
- 🟢 **Shot-noise-limited** — bright-source dominated
- 🟠 **Dark-limited** — dark-current dominated
"""
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="card-section">', unsafe_allow_html=True)
        st.markdown("### Assumptions & Limitations")
        st.caption(
            """
- Gaussian PSF; real PSFs may include broader wings
- No atmospheric dispersion or extinction
- Single-filter, single-epoch model
- Fixed sky surface brightness
- Flat detector response within the selected bandpass
"""
        )
        st.markdown('</div>', unsafe_allow_html=True)