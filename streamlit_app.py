"""
frontend.py — Calculadora de Tiempo de Exposición (ETC) — Interfaz Streamlit
=============================================================================
Ejecutar con:
    streamlit run frontend.py

Este módulo se encarga exclusivamente de:
  - Capturar entradas del usuario
  - Llamar funciones del backend
  - Mostrar resultados, gráficas y diagnósticos

Toda la física vive en backend.py.
"""

import math
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
# Configuración general
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Calculadora de Tiempo de Exposición",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Estado del tema
# ---------------------------------------------------------------------------
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "dark"


def toggle_theme():
    st.session_state["theme_mode"] = (
        "light" if st.session_state["theme_mode"] == "dark" else "dark"
    )


theme = st.session_state["theme_mode"]

# ---------------------------------------------------------------------------
# Paletas
# ---------------------------------------------------------------------------
THEMES = {
    "light": {
        "bg": "#f3f6fb",
        "bg_soft": "#edf2f8",
        "surface": "#ffffff",
        "surface_2": "#f8fafc",
        "sidebar": "#eef3f9",
        "border": "#d9e1ec",
        "border_strong": "#c7d2df",
        "text": "#18212b",
        "text_muted": "#607080",
        "text_soft": "#7c8897",
        "accent": "#1d4ed8",
        "accent_alt": "#0f766e",
        "accent_soft": "rgba(37,99,235,0.10)",
        "shadow": "0 12px 28px rgba(15,23,42,0.08)",
        "topbar_bg": "rgba(255,255,255,0.78)",
        "topbar_border": "rgba(203,213,225,0.95)",
        "metric_bg": "#f8fafc",
        "metric_border": "#dbe4ef",
        "plot_bg": "#ffffff",
        "plot_paper": "#ffffff",
        "plot_grid": "#e5e7eb",
        "plot_axis": "#1f2937",
        "plot_line": "#2563eb",
        "plot_point": "#be185d",
        "plot_target": "#d97706",
        "sky_bg": "rgba(13,148,136,0.10)",
        "sky_text": "#0f766e",
        "sky_border": "rgba(13,148,136,0.34)",
        "read_bg": "rgba(79,70,229,0.10)",
        "read_text": "#4338ca",
        "read_border": "rgba(79,70,229,0.34)",
        "shot_bg": "rgba(22,163,74,0.10)",
        "shot_text": "#15803d",
        "shot_border": "rgba(22,163,74,0.34)",
        "dark_bg": "rgba(180,83,9,0.10)",
        "dark_text": "#b45309",
        "dark_border": "rgba(180,83,9,0.34)",
    },
    "dark": {
        "bg": "#07101d",
        "bg_soft": "#0b1627",
        "surface": "#0d1728",
        "surface_2": "#101c31",
        "sidebar": "#08111f",
        "border": "#22324a",
        "border_strong": "#334155",
        "text": "#e5e7eb",
        "text_muted": "#b3bfcb",
        "text_soft": "#7f8a99",
        "accent": "#60a5fa",
        "accent_alt": "#2dd4bf",
        "accent_soft": "rgba(96,165,250,0.12)",
        "shadow": "0 16px 36px rgba(0,0,0,0.30)",
        "topbar_bg": "rgba(7,16,29,0.74)",
        "topbar_border": "rgba(51,65,85,0.82)",
        "metric_bg": "#101c31",
        "metric_border": "#22324a",
        "plot_bg": "#0d1728",
        "plot_paper": "#0d1728",
        "plot_grid": "#23344c",
        "plot_axis": "#e5e7eb",
        "plot_line": "#60a5fa",
        "plot_point": "#f9a8d4",
        "plot_target": "#fbbf24",
        "sky_bg": "rgba(34,211,238,0.10)",
        "sky_text": "#67e8f9",
        "sky_border": "rgba(34,211,238,0.28)",
        "read_bg": "rgba(165,180,252,0.10)",
        "read_text": "#c7d2fe",
        "read_border": "rgba(165,180,252,0.28)",
        "shot_bg": "rgba(134,239,172,0.10)",
        "shot_text": "#86efac",
        "shot_border": "rgba(134,239,172,0.28)",
        "dark_bg": "rgba(251,191,36,0.10)",
        "dark_text": "#fcd34d",
        "dark_border": "rgba(251,191,36,0.28)",
    },
}

T = THEMES[theme]

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
  --accent-alt: {T["accent_alt"]};
  --accent-soft: {T["accent_soft"]};
  --shadow: {T["shadow"]};
  --topbar-bg: {T["topbar_bg"]};
  --topbar-border: {T["topbar_border"]};
  --metric-bg: {T["metric_bg"]};
  --metric-border: {T["metric_border"]};

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
    radial-gradient(circle at top left, rgba(59,130,246,0.08), transparent 25%),
    linear-gradient(180deg, var(--bg) 0%, var(--bg-soft) 100%);
  color: var(--text);
}}

section[data-testid="stSidebar"] {{
  background: var(--sidebar) !important;
  border-right: 1px solid var(--border);
}}

section[data-testid="stSidebar"] .block-container {{
  padding-top: 1.15rem;
}}

h1, h2, h3 {{
  font-family: 'Source Serif 4', serif !important;
  color: var(--text);
  letter-spacing: -0.02em;
}}

h1 {{
  font-size: 2rem;
  line-height: 1.04;
}}

h2 {{
  font-size: 1.3rem;
  line-height: 1.12;
  margin-top: 0.2rem;
}}

h3 {{
  font-size: 1.04rem;
  line-height: 1.18;
}}

p, li, div, span, label {{
  color: var(--text);
}}

small, .stCaption, [data-testid="stCaptionContainer"] {{
  color: var(--text-muted) !important;
}}

[data-testid="metric-container"] {{
  background: var(--metric-bg);
  border: 1px solid var(--metric-border);
  border-radius: 16px;
  padding: 14px 16px;
}}

[data-testid="metric-container"] label {{
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
  margin-bottom: 0.16rem;
}}

.topbar-title {{
  font-family: 'Source Serif 4', serif;
  color: var(--text);
  font-size: 1.72rem;
  font-weight: 700;
  line-height: 1.02;
}}

.topbar-subtitle {{
  color: var(--text-muted);
  font-size: 0.92rem;
  margin-top: 0.22rem;
}}

.meta-line {{
  color: var(--text-muted);
  font-size: 0.94rem;
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

.plot-shell {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 1rem 1rem 0.55rem 1rem;
  box-shadow: var(--shadow);
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
  grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
  gap: 0.8rem 1rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}}

.info-item {{
  display: flex;
  flex-direction: column;
  gap: 0.12rem;
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

.html-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 1rem 1rem 0.9rem 1rem;
  box-shadow: var(--shadow);
  margin-bottom: 1rem;
}}

.table-clean table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}}

.table-clean th, .table-clean td {{
  text-align: left;
  padding: 0.48rem 0.25rem;
  border-bottom: 1px solid var(--border);
}}

.table-clean th {{
  color: var(--text-soft);
  font-weight: 600;
}}

.eq-wrap {{
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 0.85rem 0.85rem 0.35rem 0.85rem;
  margin-top: 0.65rem;
}}

.note-list {{
  color: var(--text-muted);
  font-size: 0.92rem;
  line-height: 1.65;
  margin-top: 0.75rem;
}}

button[kind="primary"] {{
  border-radius: 999px !important;
  font-weight: 600 !important;
}}

.stButton > button {{
  border-radius: 999px !important;
}}

@media (max-width: 900px) {{
  .topbar-title {{
    font-size: 1.42rem;
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
    st.markdown("## 🔭 Configuración")
    st.caption("Óptico / Infrarrojo cercano · Modelo inspirado en ESO")

    st.markdown("---")
    st.markdown("### Telescopio")
    diam = st.number_input(
        "Diámetro primario (m)",
        min_value=0.1,
        max_value=40.0,
        value=1.0,
        step=0.1,
        help="Apertura efectiva del espejo primario en metros.",
    )
    obstruction = st.slider(
        "Obstrucción central (fracción lineal)",
        min_value=0.0,
        max_value=0.4,
        value=0.12,
        step=0.01,
        help="Fracción del diámetro primario bloqueada por el espejo secundario.",
    )
    throughput = st.slider(
        "Transmisión total del sistema",
        min_value=0.1,
        max_value=1.0,
        value=0.80,
        step=0.01,
        help="Transmisión combinada de óptica, espejos y filtro.",
    )

    st.markdown("---")
    st.markdown("### Filtro y modo")
    mode = st.radio("Modo de observación", ["Optical", "Near-IR"], horizontal=True)
    filter_dict = OPTICAL_FILTERS if mode == "Optical" else NIR_FILTERS
    filter_name = st.selectbox("Filtro", list(filter_dict.keys()))
    filt = filter_dict[filter_name]
    det = detector_for_filter(filt)

    st.caption(
        f"λ_eff = {filt.lambda_eff_angstrom:.0f} Å · "
        f"Δλ = {filt.delta_lambda_angstrom:.0f} Å · "
        f"Cielo = {filt.sky_mag_arcsec2:.1f} mag/arcsec²"
    )

    st.markdown("---")
    st.markdown("### Fuente")
    source_type = st.radio(
        "Tipo de fuente",
        ["Fuente puntual", "Extendida"],
        horizontal=True,
    )
    src = "point" if source_type == "Fuente puntual" else "extended"

    object_mag = st.number_input(
        "Magnitud del objeto (AB)",
        min_value=0.0,
        max_value=35.0,
        value=20.0,
        step=0.1,
        help="Magnitud AB del objeto en el filtro seleccionado.",
    )

    st.markdown("---")
    st.markdown("### Condiciones de observación")
    seeing = st.slider(
        "Seeing FWHM (arcsec)",
        min_value=0.3,
        max_value=3.0,
        value=1.0,
        step=0.05,
    )
    ap_radius = st.slider(
        "Radio de apertura (arcsec)",
        min_value=0.3,
        max_value=5.0,
        value=1.5,
        step=0.1,
        help="Radio de la apertura fotométrica circular.",
    )
    n_reads = st.number_input(
        "Número de lecturas del detector",
        min_value=1,
        max_value=50,
        value=1,
        help="Para muestreo NIR up-the-ramp, usar > 1.",
    )

    st.markdown("---")
    st.markdown("### Modo de cálculo")
    calc_mode = st.radio(
        "Resolver para …",
        ["S/N dado el tiempo de exposición", "Tiempo de exposición dado el S/N"],
        help="Elige si deseas fijar el tiempo o el S/N objetivo.",
    )

    if calc_mode == "S/N dado el tiempo de exposición":
        exp_time = st.number_input(
            "Tiempo de exposición (s)",
            min_value=0.1,
            max_value=1e6,
            value=600.0,
            step=10.0,
        )
        target_snr_input = None
    else:
        target_snr_input = st.number_input(
            "S/N objetivo",
            min_value=1.0,
            max_value=1000.0,
            value=10.0,
            step=1.0,
        )
        exp_time = None

    st.markdown("---")
    st.markdown("### Rango de la gráfica")
    t_start_log = st.slider("t_min  log₁₀(s)", 0.0, 3.0, 0.5, 0.1)
    t_end_log = st.slider("t_max  log₁₀(s)", 1.0, 5.0, 3.6, 0.1)

# ---------------------------------------------------------------------------
# Barra superior
# ---------------------------------------------------------------------------
top_left, top_mid, top_right = st.columns([10, 0.4, 1.2])

with top_left:
    st.markdown(
        """
<div class="topbar">
  <div class="kicker">Herramienta académica de observación</div>
  <div class="topbar-title">Calculadora de Tiempo de Exposición</div>
  <div class="topbar-subtitle">
    Interfaz fotométrica para estimar tiempo de exposición o relación señal-ruido en observaciones ópticas y de infrarrojo cercano.
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

mode_label = "Óptico" if mode == "Optical" else "Infrarrojo cercano"

st.markdown(
    f"""
<div class="meta-line">
<strong>Modo {mode_label}</strong> · Filtro <strong>{filter_name}</strong> ·
Telescopio <strong>{diam:.1f} m</strong> · Objeto <strong>{object_mag:.1f} AB mag</strong>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Ensamblado de parámetros
# ---------------------------------------------------------------------------
telescope = TelescopeParams(diameter_m=diam, obstruction_fraction=obstruction)
conditions = ObservingConditions(
    seeing_fwhm_arcsec=seeing,
    aperture_radius_arcsec=ap_radius,
    total_throughput=throughput,
    n_reads=n_reads,
)

# ---------------------------------------------------------------------------
# Cálculo principal
# ---------------------------------------------------------------------------
try:
    if calc_mode == "S/N dado el tiempo de exposición":
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
# Utilidad para ticks logarítmicos menos amontonados
# ---------------------------------------------------------------------------
def build_log_ticks(tmin, tmax):
    exponents = range(int(math.floor(math.log10(tmin))), int(math.ceil(math.log10(tmax))) + 1)
    ticks = []
    labels = []
    for e in exponents:
        val = 10 ** e
        if tmin <= val <= tmax:
            ticks.append(val)
            if val < 60:
                labels.append(f"{int(val)} s")
            elif val < 3600:
                labels.append(f"{int(val/60)} min")
            else:
                labels.append(f"{int(val/3600)} h")
    return ticks, labels

# ---------------------------------------------------------------------------
# Layout principal
# ---------------------------------------------------------------------------
col_main, col_side = st.columns([3.35, 1.75], gap="large")

with col_main:
    st.markdown("## Resultados")

    if error_msg:
        st.error(f"⚠️ {error_msg}")
    else:
        regime_css = result.noise_regime.replace(" ", "-").replace("/", "-")
        regime_label = result.noise_regime

        if calc_mode == "S/N dado el tiempo de exposición":
            primary_label = "Relación señal-ruido"
            primary_value = f"{result.snr:.2f}"
            secondary = f"Tiempo de exposición: {format_time(result.exposure_time_s)}"
        else:
            primary_label = "Tiempo de exposición requerido"
            primary_value = format_time(result.time_for_target_snr)
            secondary = (
                f"S/N alcanzado = {result.snr:.2f} "
                f"(objetivo: {result.target_snr:.1f})"
            )

        st.markdown(
            f"""
<div class="result-card">
  <div class="section-kicker">Resultado principal</div>
  <div class="result-label">{primary_label}</div>
  <div class="result-value">{primary_value}</div>
  <div class="result-subtitle">{secondary}</div>
  <span class="regime-badge {regime_css}">{regime_label}</span>

  <div class="info-grid">
    <div class="info-item">
      <div class="info-item-label">Señal</div>
      <div class="info-item-value">{result.signal_e:.1f} e⁻</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">Señal de cielo</div>
      <div class="info-item-value">{result.sky_signal_e:.1f} e⁻</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">Corriente oscura</div>
      <div class="info-item-value">{result.dark_signal_e:.2f} e⁻</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">RON² × n_pix</div>
      <div class="info-item-value">{result.read_noise_total_e2:.1f} e⁻²</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">Píxeles de apertura</div>
      <div class="info-item-value">{result.n_pixels:.1f}</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">Energía encerrada</div>
      <div class="info-item-value">{result.enclosed_energy*100:.1f} %</div>
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Área colectora", f"{telescope.collecting_area_m2:.3f} m²")
        m2.metric("Eficiencia cuántica", f"{det.quantum_efficiency*100:.0f} %")
        m3.metric("Ruido de lectura", f"{det.read_noise_e} e⁻/pix")
        m4.metric("Corriente oscura", f"{det.dark_current_e_s} e⁻/s/pix")

    st.markdown("## Relación S/N en función del tiempo de exposición")

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

    tickvals, ticktext = build_log_ticks(10 ** t_start_log, 10 ** t_end_log)

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=t_arr,
            y=snr_arr,
            mode="lines",
            name="Curva S/N",
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
                name="Punto de operación",
                marker=dict(
                    color=T["plot_point"],
                    size=10,
                    line=dict(width=1, color=T["plot_paper"]),
                ),
                hovertemplate=(
                    f"Punto de operación<br>t = {t_op:.2f} s<br>"
                    f"S/N = {snr_op:.2f}<extra></extra>"
                ),
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

    if target_snr_input and calc_mode == "Tiempo de exposición dado el S/N":
        fig.add_hline(
            y=target_snr_input,
            line_width=1.1,
            line_dash="dot",
            line_color=T["plot_target"],
            annotation_text=f"S/N objetivo = {target_snr_input:.0f}",
            annotation_position="top left",
        )

    fig.update_layout(
        template="plotly_dark" if theme == "dark" else "plotly_white",
        height=520,
        margin=dict(l=55, r=28, t=78, b=58),
        paper_bgcolor=T["plot_paper"],
        plot_bgcolor=T["plot_bg"],
        font=dict(
            family="Inter, sans-serif",
            size=13,
            color=T["plot_axis"],
        ),
        title=dict(
            text=f"Filtro {filt.name} · {object_mag:.1f} AB mag · D = {diam:.1f} m",
            font=dict(size=15, color=T["plot_axis"]),
            x=0.02,
            xanchor="left",
            y=0.97,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="left",
            x=0.0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=12),
        ),
    )

    fig.update_xaxes(
        type="log",
        title="Tiempo de exposición",
        tickmode="array",
        tickvals=tickvals,
        ticktext=ticktext,
        showgrid=True,
        gridcolor=T["plot_grid"],
        zeroline=False,
        linecolor=T["plot_grid"],
        tickfont=dict(size=11),
        title_font=dict(size=13),
    )

    fig.update_yaxes(
        title="Relación señal-ruido",
        showgrid=True,
        gridcolor=T["plot_grid"],
        zeroline=False,
        linecolor=T["plot_grid"],
        tickfont=dict(size=11),
        title_font=dict(size=13),
    )

    st.markdown('<div class="plot-shell">', unsafe_allow_html=True)
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False},
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col_side:
    st.markdown("## Detalles técnicos")

    detector_card = f"""
<div class="html-card">
  <div class="section-kicker">Instrumento</div>
  <h3 style="margin-top:0;">Parámetros del detector</h3>
  <div class="table-clean">
    <table>
      <thead>
        <tr><th>Parámetro</th><th>Valor</th></tr>
      </thead>
      <tbody>
        <tr><td>Ruido de lectura</td><td>{det.read_noise_e} e⁻/pix</td></tr>
        <tr><td>Corriente oscura</td><td>{det.dark_current_e_s} e⁻/s/pix</td></tr>
        <tr><td>Escala de píxel</td><td>{det.pixel_scale_arcsec} arcsec/pix</td></tr>
        <tr><td>Eficiencia cuántica</td><td>{det.quantum_efficiency*100:.0f} %</td></tr>
      </tbody>
    </table>
  </div>
</div>
"""
    st.markdown(detector_card, unsafe_allow_html=True)

    filter_card = f"""
<div class="html-card">
  <div class="section-kicker">Configuración espectral</div>
  <h3 style="margin-top:0;">Parámetros del filtro</h3>
  <div class="table-clean">
    <table>
      <thead>
        <tr><th>Parámetro</th><th>Valor</th></tr>
      </thead>
      <tbody>
        <tr><td>Banda</td><td>{filt.name}</td></tr>
        <tr><td>λ_eff</td><td>{filt.lambda_eff_angstrom:.0f} Å</td></tr>
        <tr><td>Δλ</td><td>{filt.delta_lambda_angstrom:.0f} Å</td></tr>
        <tr><td>Brillo del cielo</td><td>{filt.sky_mag_arcsec2:.1f} mag/arcsec²</td></tr>
        <tr><td>Modo</td><td>{filt.mode}</td></tr>
      </tbody>
    </table>
  </div>
</div>
"""
    st.markdown(filter_card, unsafe_allow_html=True)

    st.markdown(
        """
<div class="html-card">
  <div class="section-kicker">Modelo teórico</div>
  <h3 style="margin-top:0;">Modelo físico</h3>
  <div class="note-list">
    La relación señal-ruido se calcula a partir de la señal del objeto, el fondo de cielo,
    la corriente oscura y la contribución del ruido de lectura integrada en la apertura fotométrica.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
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
<div class="html-card">
  <div class="section-kicker">Interpretación</div>
  <h3 style="margin-top:0;">Términos y regímenes de ruido</h3>
  <div class="note-list">
    <strong>S</strong> = señal del objeto [e⁻]<br>
    <strong>N_sky</strong> = contribución del cielo [e⁻]<br>
    <strong>N_dark</strong> = corriente oscura [e⁻]<br>
    <strong>σ_RON² · n_pix · n_reads</strong> = varianza por ruido de lectura [e⁻²]<br><br>

    🔵 <strong>Sky-limited</strong> — domina el fondo de cielo<br>
    🟣 <strong>Read-noise-limited</strong> — dominan exposiciones cortas o cielo tenue<br>
    🟢 <strong>Shot-noise-limited</strong> — domina la señal intrínseca de la fuente<br>
    🟠 <strong>Dark-limited</strong> — domina la corriente oscura
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    assumptions_card = """
<div class="html-card">
  <div class="section-kicker">Alcance del modelo</div>
  <h3 style="margin-top:0;">Supuestos y limitaciones</h3>
  <div class="note-list">
    - PSF gaussiana; PSFs reales pueden mostrar alas más extendidas<br>
    - No se incluye dispersión atmosférica ni extinción<br>
    - Modelo de una sola época y un solo filtro<br>
    - Brillo de cielo fijo<br>
    - Respuesta plana del detector dentro de la banda seleccionada
  </div>
</div>
"""
    st.markdown(assumptions_card, unsafe_allow_html=True)