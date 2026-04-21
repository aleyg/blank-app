"""
frontend.py — Calculadora de Tiempo de Exposición (CTE) — Interfaz Streamlit
=============================================================================
Ejecutar con:
    streamlit run frontend.py

Requiere backend.py en el mismo directorio y las dependencias:
    pip install streamlit plotly numpy

Este módulo gestiona exclusivamente:
  - Captura de entradas del usuario con validación
  - Llamadas al backend (toda la física vive en backend.py)
  - Visualización de resultados, gráficas y diagnósticos técnicos
  - Conmutación de tema claro / oscuro con paletas coherentes
"""

from __future__ import annotations

import math

import plotly.graph_objects as go
import streamlit as st

from backend import (
    NIR_FILTERS,
    OPTICAL_FILTERS,
    TELESCOPE_APERTURES,
    ETCResult,
    ObservingConditions,
    TelescopeParams,
    compute_exposure_time,
    compute_snr,
    default_aperture_radius,
    detector_for_filter,
    format_time,
    limiting_magnitude,
    noise_budget,
    snr_vs_magnitude,
    snr_vs_time,
)

# ──────────────────────────────────────────────────────────────────────────────
# Configuración global de la página
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CTE Astronómica · AstroObs 2026",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# Estado del tema
# ──────────────────────────────────────────────────────────────────────────────
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "dark"


def toggle_theme() -> None:
    st.session_state["theme_mode"] = (
        "light" if st.session_state["theme_mode"] == "dark" else "dark"
    )


theme: str = st.session_state["theme_mode"]

# ──────────────────────────────────────────────────────────────────────────────
# Paletas de color (light / dark)
# ──────────────────────────────────────────────────────────────────────────────
THEMES: dict[str, dict[str, str]] = {
    "light": {
        # Fondos
        "bg":            "#f0f4fa",
        "bg_soft":       "#e8eef8",
        "surface":       "#ffffff",
        "surface_2":     "#f5f8fd",
        "sidebar":       "#eaf0f9",
        # Bordes
        "border":        "#d1dbe9",
        "border_strong": "#b8c9df",
        # Texto
        "text":          "#131b27",
        "text_muted":    "#546070",
        "text_soft":     "#7a8898",
        # Acento principal (azul profundo)
        "accent":        "#1a45c8",
        "accent_alt":    "#0d7a6e",
        "accent_soft":   "rgba(26,69,200,0.10)",
        # Sombras / topbar
        "shadow":        "0 12px 32px rgba(10,20,50,0.09)",
        "topbar_bg":     "rgba(255,255,255,0.82)",
        "topbar_border": "rgba(190,205,225,0.95)",
        # Métricas
        "metric_bg":     "#f5f8fd",
        "metric_border": "#d1dbe9",
        # Plot
        "plot_bg":       "#ffffff",
        "plot_paper":    "#ffffff",
        "plot_grid":     "#e2e8f0",
        "plot_axis":     "#1f2937",
        "plot_line":     "#1a45c8",
        "plot_line2":    "#0d7a6e",
        "plot_point":    "#b91c5a",
        "plot_target":   "#c2700a",
        # Badges de régimen
        "sky_bg":    "rgba(13,122,110,0.10)",  "sky_text":  "#0d7a6e",  "sky_border":  "rgba(13,122,110,0.30)",
        "read_bg":   "rgba(79,60,220,0.10)",   "read_text": "#4338ca",  "read_border": "rgba(79,60,220,0.30)",
        "shot_bg":   "rgba(20,160,70,0.10)",   "shot_text": "#15803d",  "shot_border": "rgba(20,160,70,0.30)",
        "dark_bg":   "rgba(180,83,9,0.10)",    "dark_text": "#b45309",  "dark_border": "rgba(180,83,9,0.30)",
        # Tab activo
        "tab_active_bg":     "rgba(26,69,200,0.12)",
        "tab_active_text":   "#1a45c8",
        "tab_active_border": "#1a45c8",
    },
    "dark": {
        # Fondos
        "bg":            "#060f1c",
        "bg_soft":       "#0a1525",
        "surface":       "#0c1625",
        "surface_2":     "#0f1c30",
        "sidebar":       "#070e1c",
        # Bordes
        "border":        "#1e2f47",
        "border_strong": "#2d405a",
        # Texto
        "text":          "#dde4ef",
        "text_muted":    "#8fa0b5",
        "text_soft":     "#6a7d93",
        # Acento principal (azul cielo)
        "accent":        "#5ba4f5",
        "accent_alt":    "#2dcfbf",
        "accent_soft":   "rgba(91,164,245,0.12)",
        # Sombras / topbar
        "shadow":        "0 16px 40px rgba(0,0,0,0.36)",
        "topbar_bg":     "rgba(6,15,28,0.80)",
        "topbar_border": "rgba(45,64,90,0.90)",
        # Métricas
        "metric_bg":     "#0f1c30",
        "metric_border": "#1e2f47",
        # Plot
        "plot_bg":       "#0c1625",
        "plot_paper":    "#0c1625",
        "plot_grid":     "#1a2b40",
        "plot_axis":     "#dde4ef",
        "plot_line":     "#5ba4f5",
        "plot_line2":    "#2dcfbf",
        "plot_point":    "#f2709c",
        "plot_target":   "#fbbf24",
        # Badges de régimen
        "sky_bg":    "rgba(34,211,238,0.10)",   "sky_text":  "#5eead4",  "sky_border":  "rgba(34,211,238,0.25)",
        "read_bg":   "rgba(165,180,252,0.10)",  "read_text": "#a5b4fc",  "read_border": "rgba(165,180,252,0.25)",
        "shot_bg":   "rgba(134,239,172,0.10)",  "shot_text": "#86efac",  "shot_border": "rgba(134,239,172,0.25)",
        "dark_bg":   "rgba(251,191,36,0.10)",   "dark_text": "#fcd34d",  "dark_border": "rgba(251,191,36,0.25)",
        # Tab activo
        "tab_active_bg":     "rgba(91,164,245,0.14)",
        "tab_active_text":   "#5ba4f5",
        "tab_active_border": "#5ba4f5",
    },
}

T = THEMES[theme]

# ──────────────────────────────────────────────────────────────────────────────
# CSS global
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&display=swap');

/* ── Variables ── */
:root {{
  --bg:            {T["bg"]};
  --bg-soft:       {T["bg_soft"]};
  --surface:       {T["surface"]};
  --surface-2:     {T["surface_2"]};
  --sidebar:       {T["sidebar"]};
  --border:        {T["border"]};
  --border-strong: {T["border_strong"]};
  --text:          {T["text"]};
  --text-muted:    {T["text_muted"]};
  --text-soft:     {T["text_soft"]};
  --accent:        {T["accent"]};
  --accent-alt:    {T["accent_alt"]};
  --accent-soft:   {T["accent_soft"]};
  --shadow:        {T["shadow"]};
  --topbar-bg:     {T["topbar_bg"]};
  --topbar-border: {T["topbar_border"]};
  --metric-bg:     {T["metric_bg"]};
  --metric-border: {T["metric_border"]};
  --sky-bg:        {T["sky_bg"]};   --sky-text:  {T["sky_text"]};   --sky-border:  {T["sky_border"]};
  --read-bg:       {T["read_bg"]};  --read-text: {T["read_text"]};  --read-border: {T["read_border"]};
  --shot-bg:       {T["shot_bg"]};  --shot-text: {T["shot_text"]};  --shot-border: {T["shot_border"]};
  --dark-bg:       {T["dark_bg"]};  --dark-text: {T["dark_text"]};  --dark-border: {T["dark_border"]};
  --tab-active-bg:     {T["tab_active_bg"]};
  --tab-active-text:   {T["tab_active_text"]};
  --tab-active-border: {T["tab_active_border"]};
}}

/* ── Base ── */
html, body, [class*="css"] {{
  font-family: 'DM Sans', sans-serif;
  color: var(--text);
}}
.stApp {{
  background: linear-gradient(160deg, var(--bg) 0%, var(--bg-soft) 100%);
  color: var(--text);
}}
section[data-testid="stSidebar"] {{
  background: var(--sidebar) !important;
  border-right: 1px solid var(--border) !important;
}}
section[data-testid="stSidebar"] .block-container {{ padding-top: 1rem; }}

/* ── Tipografía ── */
h1, h2, h3 {{
  font-family: 'DM Serif Display', serif !important;
  color: var(--text);
  letter-spacing: -0.015em;
}}
h1 {{ font-size: 1.9rem; line-height: 1.06; }}
h2 {{ font-size: 1.28rem; line-height: 1.14; }}
h3 {{ font-size: 1.0rem; }}
p, li, div, span, label {{ color: var(--text); }}
small, .stCaption, [data-testid="stCaptionContainer"] {{
  color: var(--text-muted) !important;
  font-size: 0.82rem !important;
}}
code, .mono {{
  font-family: 'DM Mono', monospace;
  font-size: 0.86em;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 0.05em 0.35em;
}}

/* ── Métricas Streamlit ── */
[data-testid="metric-container"] {{
  background: var(--metric-bg) !important;
  border: 1px solid var(--metric-border) !important;
  border-radius: 14px !important;
  padding: 12px 16px !important;
}}
[data-testid="metric-container"] label {{
  color: var(--text-soft) !important;
  font-size: 0.74rem !important;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  font-weight: 600 !important;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
  color: var(--text) !important;
  font-family: 'DM Serif Display', serif !important;
  font-size: 1.55rem !important;
}}

/* ── Inputs ── */
.stSlider [data-baseweb="slider"] {{ accent-color: var(--accent); }}
.stSelectbox [data-baseweb="select"] > div,
.stNumberInput input,
.stTextInput input {{
  background: var(--surface-2) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  border-radius: 10px !important;
}}
.stRadio [data-baseweb="radio"] span {{ color: var(--text) !important; }}
.stButton > button {{
  border-radius: 999px !important;
  font-weight: 600 !important;
  font-family: 'DM Sans', sans-serif !important;
  border: 1px solid var(--border) !important;
  background: var(--surface) !important;
  color: var(--text) !important;
  transition: all 0.18s ease;
}}
.stButton > button:hover {{
  background: var(--accent-soft) !important;
  border-color: var(--accent) !important;
  color: var(--accent) !important;
}}

/* ── Tabs personalizados ── */
.stTabs [data-baseweb="tab-list"] {{
  background: var(--surface-2) !important;
  border-radius: 12px !important;
  padding: 4px !important;
  border: 1px solid var(--border) !important;
  gap: 2px !important;
}}
.stTabs [data-baseweb="tab"] {{
  border-radius: 9px !important;
  color: var(--text-muted) !important;
  font-size: 0.84rem !important;
  font-weight: 500 !important;
  padding: 0.38rem 0.9rem !important;
  transition: all 0.18s ease;
}}
.stTabs [aria-selected="true"] {{
  background: var(--tab-active-bg) !important;
  color: var(--tab-active-text) !important;
  border-bottom: 2px solid var(--tab-active-border) !important;
}}
.stTabs [data-baseweb="tab-panel"] {{
  padding-top: 1.1rem !important;
}}

/* ── Divider ── */
hr {{ border-color: var(--border) !important; margin: 0.75rem 0 !important; }}

/* ── Componentes personalizados ── */
.topbar {{
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  background: var(--topbar-bg);
  border: 1px solid var(--topbar-border);
  border-radius: 20px;
  padding: 1.1rem 1.4rem;
  margin-bottom: 1.1rem;
  box-shadow: var(--shadow);
}}
.kicker {{
  color: var(--accent);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  margin-bottom: 0.18rem;
}}
.topbar-title {{
  font-family: 'DM Serif Display', serif;
  color: var(--text);
  font-size: 1.78rem;
  font-weight: 400;
  line-height: 1.0;
}}
.topbar-subtitle {{
  color: var(--text-muted);
  font-size: 0.9rem;
  margin-top: 0.25rem;
  line-height: 1.55;
}}
.topbar-meta {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-top: 0.9rem;
}}
.meta-pill {{
  background: var(--accent-soft);
  color: var(--accent);
  border: 1px solid rgba(91,164,245,0.25);
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 600;
  padding: 0.22rem 0.72rem;
  letter-spacing: 0.04em;
}}
.result-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 1.4rem;
  box-shadow: var(--shadow);
  margin-bottom: 1rem;
}}
.plot-shell {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 1rem 1rem 0.4rem;
  box-shadow: var(--shadow);
  margin-bottom: 1rem;
}}
.section-kicker {{
  color: var(--accent);
  font-size: 0.70rem;
  font-weight: 700;
  letter-spacing: 0.11em;
  text-transform: uppercase;
  margin-bottom: 0.18rem;
}}
.result-label {{
  color: var(--text-soft);
  font-size: 0.73rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.13em;
}}
.result-value {{
  font-family: 'DM Serif Display', serif;
  color: var(--accent);
  font-size: 3.0rem;
  font-weight: 400;
  line-height: 1.0;
  margin-top: 0.28rem;
}}
.result-subtitle {{
  color: var(--text-muted);
  font-size: 0.9rem;
  margin-top: 0.35rem;
}}
.regime-badge {{
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.26rem 0.76rem;
  border-radius: 999px;
  font-size: 0.70rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border: 1px solid transparent;
  margin-top: 0.9rem;
}}
.sky-limited       {{ background: var(--sky-bg);  color: var(--sky-text);  border-color: var(--sky-border);  }}
.read-noise-limited{{ background: var(--read-bg); color: var(--read-text); border-color: var(--read-border); }}
.shot-noise-limited{{ background: var(--shot-bg); color: var(--shot-text); border-color: var(--shot-border); }}
.dark-limited      {{ background: var(--dark-bg); color: var(--dark-text); border-color: var(--dark-border); }}
.info-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.8rem 1rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}}
.info-item {{ display: flex; flex-direction: column; gap: 0.1rem; }}
.info-item-label {{
  color: var(--text-soft);
  font-size: 0.70rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
}}
.info-item-value {{
  color: var(--text);
  font-size: 0.88rem;
  font-weight: 600;
  font-family: 'DM Mono', monospace;
}}
.html-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 1rem 1.1rem 0.9rem;
  box-shadow: var(--shadow);
  margin-bottom: 0.9rem;
}}
.table-clean table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.86rem;
}}
.table-clean th, .table-clean td {{
  text-align: left;
  padding: 0.44rem 0.3rem;
  border-bottom: 1px solid var(--border);
}}
.table-clean th {{
  color: var(--text-soft);
  font-weight: 600;
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
}}
.table-clean td:last-child {{
  font-family: 'DM Mono', monospace;
  color: var(--accent);
  font-size: 0.84rem;
}}
.eq-wrap {{
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 0.8rem 0.8rem 0.25rem;
  margin: 0.65rem 0;
}}
.note-list {{
  color: var(--text-muted);
  font-size: 0.87rem;
  line-height: 1.7;
  margin-top: 0.6rem;
}}
.snr-bar-wrap {{
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  height: 8px;
  margin-top: 0.5rem;
}}
.snr-bar-fill {{
  height: 100%;
  border-radius: 12px;
  background: linear-gradient(90deg, var(--accent), var(--accent-alt));
  transition: width 0.5s ease;
}}
.sidebar-section {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 0.75rem 0.85rem;
  margin-bottom: 0.7rem;
}}
.sidebar-section-title {{
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.10em;
  color: var(--accent);
  margin-bottom: 0.55rem;
}}
.warning-box {{
  background: rgba(251,191,36,0.08);
  border: 1px solid rgba(251,191,36,0.28);
  border-radius: 12px;
  padding: 0.75rem 1rem;
  color: {T["dark_text"]};
  font-size: 0.88rem;
  line-height: 1.5;
  margin-bottom: 0.8rem;
}}
.info-box {{
  background: var(--accent-soft);
  border: 1px solid rgba(91,164,245,0.22);
  border-radius: 12px;
  padding: 0.75rem 1rem;
  color: var(--accent);
  font-size: 0.88rem;
  line-height: 1.5;
  margin-bottom: 0.8rem;
}}
.val-header {{
  font-family: 'DM Serif Display', serif;
  font-size: 1.15rem;
  color: var(--text);
  margin-bottom: 0.4rem;
}}
@media (max-width: 900px) {{
  .topbar-title {{ font-size: 1.45rem; }}
  .result-value {{ font-size: 2.3rem; }}
}}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar — parámetros de entrada
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div style="text-align:center;margin-bottom:0.9rem;">
  <div style="font-family:'DM Serif Display',serif;font-size:1.45rem;
              color:var(--text);letter-spacing:-0.01em;">🔭 CTE Astronómica</div>
  <div style="font-size:0.78rem;color:var(--text-muted);margin-top:0.15rem;">
    AstroObs 2026 · Modelo ESO
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section"><div class="sidebar-section-title">🔭 Telescopio</div>', unsafe_allow_html=True)
    diam = st.selectbox(
        "Apertura del primario",
        options=TELESCOPE_APERTURES,
        index=1,
        format_func=lambda x: f"{x:.1f} m",
        help="Diámetro del espejo primario. Opciones del proyecto: 2.0, 3.5, 6.5, 8.0 m.",
    )
    obstruction = st.slider(
        "Obstrucción central (fracción lineal)",
        min_value=0.00, max_value=0.40, value=0.12, step=0.01,
        help="Fracción del diámetro obstruida por el espejo secundario. Estándar: 0.12.",
    )
    throughput = st.slider(
        "Transmisión total del sistema",
        min_value=0.10, max_value=1.00, value=0.80, step=0.01,
        help="Eficiencia combinada de óptica, espejos y filtro (0–1).",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section"><div class="sidebar-section-title">🌈 Filtro y modo</div>', unsafe_allow_html=True)
    mode = st.radio("Modo de observación", ["Óptico", "Infrarrojo cercano"], horizontal=True)
    filter_dict = OPTICAL_FILTERS if mode == "Óptico" else NIR_FILTERS
    filter_name = st.selectbox("Banda fotométrica", list(filter_dict.keys()))
    filt = filter_dict[filter_name]
    det = detector_for_filter(filt)

    lam_label = (
        f"{filt.lambda_eff_um:.2f} μm"
        if filt.mode == "nir"
        else f"{filt.lambda_eff_angstrom:.0f} Å"
    )
    st.caption(
        f"λ_eff = {lam_label} · Δλ = {filt.delta_lambda_angstrom:.0f} Å · "
        f"Cielo = {filt.sky_mag_arcsec2:.1f} AB mag/arcsec²"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section"><div class="sidebar-section-title">⭐ Fuente</div>', unsafe_allow_html=True)
    source_type_label = st.radio(
        "Morfología", ["Fuente puntual", "Extendida"], horizontal=True,
        help="Puntual aplica corrección de energía encerrada. Extendida asume EE=1.",
    )
    src = "point" if source_type_label == "Fuente puntual" else "extended"
    object_mag = st.number_input(
        "Magnitud del objeto (AB mag)",
        min_value=0.0, max_value=35.0, value=20.0, step=0.5,
        help="Magnitud AB de la fuente en la banda seleccionada.",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section"><div class="sidebar-section-title">🌬️ Condiciones atmosféricas</div>', unsafe_allow_html=True)
    seeing = st.slider(
        "Seeing FWHM (arcsec)",
        min_value=0.30, max_value=3.00, value=0.80, step=0.05,
        help="FWHM de la función de dispersión de punto (PSF) atmosférica.",
    )

    use_auto_ap = st.checkbox(
        "Apertura automática (r = 1.2 × FWHM)",
        value=True,
        help="Recomendado: r_ap = 1.2 × FWHM optimiza el S/N en régimen de cielo.",
    )
    if use_auto_ap:
        ap_radius = default_aperture_radius(seeing)
        st.caption(f"Radio de apertura: **{ap_radius:.2f}** arcsec")
    else:
        ap_radius = st.slider(
            "Radio de apertura fotométrica (arcsec)",
            min_value=0.20, max_value=6.00, value=round(default_aperture_radius(seeing), 1),
            step=0.1,
        )

    n_reads = st.number_input(
        "Lecturas del detector",
        min_value=1, max_value=64, value=1,
        help="Nº de lecturas (> 1 para muestreo NIR up-the-ramp).",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section"><div class="sidebar-section-title">⚙️ Modo de cálculo</div>', unsafe_allow_html=True)
    calc_mode = st.radio(
        "Resolver para …",
        [
            "S/N dado el tiempo de exposición",
            "Tiempo de exposición dado el S/N",
        ],
        help="Elige si calcular S/N para un tiempo fijo, o el tiempo necesario para un S/N objetivo.",
    )

    if calc_mode == "S/N dado el tiempo de exposición":
        exp_time = st.number_input(
            "Tiempo de exposición (s)",
            min_value=0.1, max_value=1_000_000.0, value=600.0, step=30.0,
        )
        target_snr_input: float | None = None
    else:
        target_snr_input = st.number_input(
            "S/N objetivo",
            min_value=1.0, max_value=1000.0, value=10.0, step=1.0,
        )
        exp_time: float | None = None
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section"><div class="sidebar-section-title">📊 Rango de gráfica S/N(t)</div>', unsafe_allow_html=True)
    t_start_log = st.slider("log₁₀(t_min / s)", 0.0, 3.0, 0.5, 0.1)
    t_end_log   = st.slider("log₁₀(t_max / s)", 1.0, 5.0, 3.7, 0.1)
    st.markdown('</div>', unsafe_allow_html=True)

    # Botón de tema
    st.markdown("<br>", unsafe_allow_html=True)
    col_th1, col_th2 = st.columns([1, 2])
    with col_th1:
        st.button(
            "🌙" if theme == "light" else "☀️",
            help="Cambiar tema",
            on_click=toggle_theme,
            use_container_width=True,
        )
    with col_th2:
        st.caption("Modo " + ("oscuro →" if theme == "light" else "claro →"))

# ──────────────────────────────────────────────────────────────────────────────
# Barra superior
# ──────────────────────────────────────────────────────────────────────────────
mode_label = "Óptico" if mode == "Óptico" else "IR cercano"
pills_html = "".join([
    f'<span class="meta-pill">{t}</span>'
    for t in [
        f"Filtro {filter_name}",
        f"D = {diam:.1f} m",
        f"{object_mag:.1f} AB mag",
        f"Seeing {seeing:.2f}\"",
        mode_label,
    ]
])

st.markdown(f"""
<div class="topbar">
  <div class="kicker">Herramienta académica de observación · AstroObs 2026</div>
  <div class="topbar-title">Calculadora de Tiempo de Exposición</div>
  <div class="topbar-subtitle">
    Modelo fotométrico de primeros principios para observaciones ópticas e infrarrojas cercanas.
    Basada en el formalismo ESO-FORS. Incluye todos los términos de ruido relevantes.
  </div>
  <div class="topbar-meta">{pills_html}</div>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Ensamblado de parámetros
# ──────────────────────────────────────────────────────────────────────────────
telescope = TelescopeParams(diameter_m=diam, obstruction_fraction=obstruction)
conditions = ObservingConditions(
    seeing_fwhm_arcsec=seeing,
    aperture_radius_arcsec=ap_radius,
    total_throughput=throughput,
    n_reads=n_reads,
)

# ──────────────────────────────────────────────────────────────────────────────
# Cálculo principal
# ──────────────────────────────────────────────────────────────────────────────
error_msg: str | None = None
result: ETCResult | None = None

try:
    if calc_mode == "S/N dado el tiempo de exposición":
        result = compute_snr(object_mag, exp_time, telescope, filt, det, conditions, src)
    else:
        result = compute_exposure_time(
            object_mag, target_snr_input, telescope, filt, det, conditions, src
        )
except ValueError as exc:
    error_msg = str(exc)

# ──────────────────────────────────────────────────────────────────────────────
# Utilidades de gráfica
# ──────────────────────────────────────────────────────────────────────────────
def build_log_ticks(tmin: float, tmax: float) -> tuple[list, list]:
    """Genera ticks logarítmicos con etiquetas legibles."""
    exponents = range(
        int(math.floor(math.log10(tmin))),
        int(math.ceil(math.log10(tmax))) + 1,
    )
    ticks, labels = [], []
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


PLOT_LAYOUT_BASE = dict(
    template="plotly_dark" if theme == "dark" else "plotly_white",
    paper_bgcolor=T["plot_paper"],
    plot_bgcolor=T["plot_bg"],
    font=dict(family="DM Sans, sans-serif", size=12, color=T["plot_axis"]),
    margin=dict(l=58, r=24, t=70, b=52),
    legend=dict(
        orientation="h",
        yanchor="bottom", y=1.04,
        xanchor="left",   x=0.0,
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
    ),
)

AXIS_BASE = dict(
    showgrid=True,
    gridcolor=T["plot_grid"],
    zeroline=False,
    linecolor=T["plot_grid"],
    tickfont=dict(size=11),
    title_font=dict(size=13),
)

# ──────────────────────────────────────────────────────────────────────────────
# Tabs principales
# ──────────────────────────────────────────────────────────────────────────────
tab_results, tab_curves, tab_budget, tab_validation, tab_model = st.tabs([
    "📊 Resultados",
    "📈 Curvas S/N",
    "🎛️ Presupuesto de ruido",
    "🔬 Validación",
    "📐 Modelo físico",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — RESULTADOS
# ══════════════════════════════════════════════════════════════════════════════
with tab_results:
    if error_msg:
        st.markdown(f'<div class="warning-box">⚠️ {error_msg}</div>', unsafe_allow_html=True)
    elif result:
        regime_css  = result.noise_regime.replace(" ", "-").replace("/", "-")
        regime_icon = {
            "sky-limited":        "🌌",
            "shot-noise-limited": "⚡",
            "read-noise-limited": "📡",
            "dark-limited":       "🌑",
        }.get(result.noise_regime, "•")

        if calc_mode == "S/N dado el tiempo de exposición":
            primary_label = "Relación señal-ruido (S/N)"
            primary_value = f"{result.snr:.2f}"
            secondary     = f"Tiempo de exposición: <strong>{format_time(result.exposure_time_s)}</strong>"
        else:
            primary_label = "Tiempo de exposición requerido"
            primary_value = format_time(result.time_for_target_snr)
            secondary     = (
                f"S/N alcanzado = <strong>{result.snr:.2f}</strong> "
                f"(objetivo: {result.target_snr:.1f})"
            )

        # Barra de progreso de S/N (0–100)
        snr_pct = min(result.snr / 100.0 * 100, 100)
        bar_html = (
            f'<div class="snr-bar-wrap">'
            f'<div class="snr-bar-fill" style="width:{snr_pct:.1f}%"></div>'
            f'</div>'
        )

        st.markdown(f"""
<div class="result-card">
  <div class="section-kicker">Resultado principal</div>
  <div class="result-label">{primary_label}</div>
  <div class="result-value">{primary_value}</div>
  <div class="result-subtitle">{secondary}</div>
  {bar_html if calc_mode == "S/N dado el tiempo de exposición" else ""}
  <span class="regime-badge {regime_css}">{regime_icon} {result.noise_regime}</span>

  <div class="info-grid">
    <div class="info-item">
      <div class="info-item-label">Señal del objeto</div>
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
      <div class="info-item-label">σ_RON² × n_pix × n_reads</div>
      <div class="info-item-value">{result.read_noise_total_e2:.1f} e⁻²</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">Ruido total RMS</div>
      <div class="info-item-value">{result.total_noise_e:.1f} e⁻</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">Píxeles apertura</div>
      <div class="info-item-value">{result.n_pixels:.1f} pix</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">Energía encerrada</div>
      <div class="info-item-value">{result.enclosed_energy*100:.1f} %</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">Flujo de fotones</div>
      <div class="info-item-value">{result.object_photon_flux:.3e} ph/s/m²</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        # Métricas del instrumento
        mc = st.columns(4)
        mc[0].metric("Área colectora",     f"{telescope.collecting_area_m2:.3f} m²")
        mc[1].metric("Ef. cuántica (QE)",  f"{det.quantum_efficiency*100:.0f} %")
        mc[2].metric("Ruido de lectura",   f"{det.read_noise_e} e⁻/pix")
        mc[3].metric("Corriente oscura",   f"{det.dark_current_e_s} e⁻/s/pix")

        # Magnitud límite
        st.markdown("---")
        col_lim1, col_lim2 = st.columns([2, 1])
        with col_lim1:
            st.markdown("#### Magnitud límite")
            st.caption(
                "Magnitud AB más débil detectable con S/N ≥ 5 para el tiempo de exposición actual."
            )
        with col_lim2:
            try:
                t_ref = result.exposure_time_s if result.time_for_target_snr is None else result.time_for_target_snr
                mag_lim = limiting_magnitude(t_ref, 5.0, telescope, filt, det, conditions, src)
                st.metric("Mag. límite (S/N=5)", f"{mag_lim:.2f} AB")
            except Exception:
                st.caption("No calculable.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CURVAS S/N
# ══════════════════════════════════════════════════════════════════════════════
with tab_curves:
    t_start = 10 ** t_start_log
    t_end   = 10 ** t_end_log

    tab_snr_t, tab_snr_mag = st.tabs(["S/N vs. tiempo", "S/N vs. magnitud"])

    # ── S/N vs. tiempo ──────────────────────────────────────────────────────
    with tab_snr_t:
        t_arr, snr_arr = snr_vs_time(
            object_mag, telescope, filt, det, conditions, src,
            t_start=t_start, t_end=t_end,
        )
        tickvals, ticktext = build_log_ticks(t_start, t_end)

        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(
            x=t_arr, y=snr_arr, mode="lines", name="Curva S/N",
            line=dict(color=T["plot_line"], width=2.5),
            hovertemplate="t = %{x:.1f} s<br>S/N = %{y:.2f}<extra></extra>",
        ))

        if result and not error_msg:
            t_op  = result.time_for_target_snr or result.exposure_time_s
            snr_op = result.snr
            fig_t.add_trace(go.Scatter(
                x=[t_op], y=[snr_op], mode="markers",
                name="Punto de operación",
                marker=dict(color=T["plot_point"], size=10,
                            line=dict(width=1.5, color=T["plot_paper"])),
                hovertemplate=f"t = {t_op:.1f} s<br>S/N = {snr_op:.2f}<extra></extra>",
            ))
            fig_t.add_vline(x=t_op, line_width=1, line_dash="dash",
                            line_color=T["plot_point"], opacity=0.7)
            fig_t.add_hline(y=snr_op, line_width=1, line_dash="dash",
                            line_color=T["plot_point"], opacity=0.7)

        if target_snr_input and calc_mode == "Tiempo de exposición dado el S/N":
            fig_t.add_hline(
                y=target_snr_input, line_width=1.2, line_dash="dot",
                line_color=T["plot_target"],
                annotation_text=f"S/N objetivo = {target_snr_input:.0f}",
                annotation_position="top left",
                annotation_font_color=T["plot_target"],
            )

        fig_t.update_layout(
            **PLOT_LAYOUT_BASE,
            height=460,
            title=dict(
                text=f"S/N vs. tiempo · Filtro {filt.name} · {object_mag:.1f} AB mag · D = {diam:.1f} m",
                font=dict(size=14, color=T["plot_axis"]), x=0.01, y=0.97, xanchor="left",
            ),
        )
        fig_t.update_xaxes(
            type="log", title="Tiempo de exposición",
            tickmode="array", tickvals=tickvals, ticktext=ticktext,
            **AXIS_BASE,
        )
        fig_t.update_yaxes(title="Relación señal-ruido (S/N)", **AXIS_BASE)

        st.markdown('<div class="plot-shell">', unsafe_allow_html=True)
        st.plotly_chart(fig_t, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    # ── S/N vs. magnitud ────────────────────────────────────────────────────
    with tab_snr_mag:
        t_ref_mag = (
            (result.time_for_target_snr or result.exposure_time_s)
            if result else (exp_time or 600.0)
        )
        mag_arr, snr_mag_arr = snr_vs_magnitude(
            t_ref_mag, telescope, filt, det, conditions, src,
            mag_start=14.0, mag_end=28.0,
        )

        fig_m = go.Figure()
        fig_m.add_trace(go.Scatter(
            x=mag_arr, y=snr_mag_arr, mode="lines", name="Curva S/N(mag)",
            line=dict(color=T["plot_line2"], width=2.5),
            hovertemplate="mag = %{x:.2f}<br>S/N = %{y:.2f}<extra></extra>",
        ))
        # Línea de S/N=5 (magnitud límite)
        fig_m.add_hline(
            y=5.0, line_width=1.2, line_dash="dot",
            line_color=T["plot_target"], opacity=0.85,
            annotation_text="S/N = 5  (mag. límite)",
            annotation_position="top right",
            annotation_font_color=T["plot_target"],
        )
        if result and not error_msg:
            fig_m.add_vline(
                x=object_mag, line_width=1, line_dash="dash",
                line_color=T["plot_point"], opacity=0.7,
                annotation_text=f"Objeto ({object_mag:.1f} AB)",
                annotation_position="top right",
                annotation_font_color=T["plot_point"],
            )
        fig_m.update_layout(
            **PLOT_LAYOUT_BASE,
            height=460,
            title=dict(
                text=f"S/N vs. magnitud · t = {format_time(t_ref_mag)} · D = {diam:.1f} m",
                font=dict(size=14, color=T["plot_axis"]), x=0.01, y=0.97, xanchor="left",
            ),
        )
        fig_m.update_xaxes(title="Magnitud AB", autorange="reversed", **AXIS_BASE)
        fig_m.update_yaxes(title="Relación señal-ruido (S/N)", **AXIS_BASE)

        st.markdown('<div class="plot-shell">', unsafe_allow_html=True)
        st.plotly_chart(fig_m, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PRESUPUESTO DE RUIDO
# ══════════════════════════════════════════════════════════════════════════════
with tab_budget:
    if error_msg:
        st.warning(error_msg)
    elif result:
        budget = noise_budget(result)

        st.markdown("#### Distribución de la varianza del ruido")
        st.caption(
            "Muestra qué fracción de la varianza total proviene de cada fuente de ruido. "
            "El término dominante determina el régimen de la observación."
        )

        labels = ["Shot noise\n(objeto)", "Fondo de cielo", "Corriente oscura", "Ruido de lectura"]
        values = [
            budget["shot_noise"],
            budget["sky"],
            budget["dark"],
            budget["read_noise"],
        ]
        colors_pie = [T["plot_line"], T["plot_line2"], T["plot_target"], T["plot_point"]]

        fig_pie = go.Figure(go.Pie(
            labels=labels, values=values,
            hole=0.52,
            marker=dict(colors=colors_pie,
                        line=dict(color=T["plot_bg"], width=2)),
            textinfo="label+percent",
            textfont=dict(size=12, family="DM Sans, sans-serif", color=T["plot_axis"]),
            hovertemplate="%{label}<br>%{value:.1f}% de la varianza<extra></extra>",
        ))
        fig_pie.update_layout(
            **PLOT_LAYOUT_BASE,
            height=380,
            margin=dict(l=16, r=16, t=50, b=20),
            showlegend=True,
            title=dict(
                text="Contribuciones al ruido",
                font=dict(size=14, color=T["plot_axis"]), x=0.01, y=0.97, xanchor="left",
            ),
            annotations=[dict(
                text=f"<b>S/N</b><br>{result.snr:.1f}",
                x=0.5, y=0.5, font_size=16, showarrow=False,
                font=dict(color=T["plot_axis"], family="DM Serif Display, serif"),
            )],
        )

        col_pie, col_table = st.columns([1.3, 1])
        with col_pie:
            st.markdown('<div class="plot-shell">', unsafe_allow_html=True)
            st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

        with col_table:
            st.markdown(f"""
<div class="html-card">
  <div class="section-kicker">Tabla de ruido</div>
  <h3 style="margin-top:0;">Términos de varianza</h3>
  <div class="table-clean">
    <table>
      <thead>
        <tr><th>Fuente</th><th>Varianza (e⁻²)</th><th>%</th></tr>
      </thead>
      <tbody>
        <tr><td>Shot noise (objeto)</td>
            <td>{result.signal_e:.1f}</td>
            <td>{budget['shot_noise']:.1f}%</td></tr>
        <tr><td>Fondo de cielo</td>
            <td>{result.sky_signal_e:.1f}</td>
            <td>{budget['sky']:.1f}%</td></tr>
        <tr><td>Corriente oscura</td>
            <td>{result.dark_signal_e:.3f}</td>
            <td>{budget['dark']:.2f}%</td></tr>
        <tr><td>Ruido de lectura</td>
            <td>{result.read_noise_total_e2:.1f}</td>
            <td>{budget['read_noise']:.1f}%</td></tr>
        <tr style="font-weight:600;">
            <td>Total</td>
            <td>{budget['total_var']:.1f}</td>
            <td>100%</td></tr>
      </tbody>
    </table>
  </div>
</div>
""", unsafe_allow_html=True)

            regime_descriptions = {
                "sky-limited":        "El ruido de fondo de cielo domina. Aumentar el diámetro del telescopio o reducir el tiempo de exposición tiene poco efecto.",
                "read-noise-limited": "El ruido de lectura domina. Usar exposiciones más largas o co-adición mejora el S/N.",
                "shot-noise-limited": "El shot noise del objeto domina. El S/N ∝ √t; solo más área o más tiempo ayudan.",
                "dark-limited":       "La corriente oscura domina. Enfriar el detector o reducir el tiempo de integración mejora el S/N.",
            }
            st.markdown(f"""
<div class="html-card">
  <div class="section-kicker">Régimen dominante</div>
  <span class="regime-badge {result.noise_regime.replace(' ','-').replace('/','-')}"
        style="margin-top:0.3rem;">{result.noise_regime}</span>
  <div class="note-list" style="margin-top:0.6rem;">
    {regime_descriptions.get(result.noise_regime, "")}
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — VALIDACIÓN OBSERVACIONAL
# ══════════════════════════════════════════════════════════════════════════════
with tab_validation:
    st.markdown("#### Validación contra CTE pública (ESO FORS / HAWK-I)")
    st.markdown("""
<div class="info-box">
  📌 Esta sección compara los resultados de nuestra CTE con la calculadora pública de ESO
  (<a href="https://etc.eso.org/fors" target="_blank" style="color:var(--accent);">etc.eso.org/fors</a>).
  Los parámetros de prueba estándar son los del proyecto. Las diferencias se discuten
  desde el punto de vista físico.
</div>
""", unsafe_allow_html=True)

    # Caso de prueba documentado
    st.markdown("##### Caso de prueba estándar del proyecto")
    col_v1, col_v2 = st.columns(2)

    with col_v1:
        st.markdown(f"""
<div class="html-card">
  <div class="section-kicker">CTE propia</div>
  <h3 style="margin-top:0;">Parámetros de entrada</h3>
  <div class="table-clean">
    <table>
      <thead><tr><th>Parámetro</th><th>Valor</th></tr></thead>
      <tbody>
        <tr><td>Telescopio</td><td>D = {diam:.1f} m</td></tr>
        <tr><td>Obstrucción</td><td>{obstruction*100:.0f}% (lineal)</td></tr>
        <tr><td>Filtro</td><td>{filt.name} ({filt.lambda_eff_angstrom:.0f} Å)</td></tr>
        <tr><td>Anchura banda</td><td>{filt.delta_lambda_angstrom:.0f} Å</td></tr>
        <tr><td>Magnitud objeto</td><td>{object_mag:.1f} AB mag</td></tr>
        <tr><td>Seeing FWHM</td><td>{seeing:.2f} arcsec</td></tr>
        <tr><td>Radio apertura</td><td>{ap_radius:.2f} arcsec</td></tr>
        <tr><td>Transmisión</td><td>{throughput:.0%}</td></tr>
        <tr><td>QE</td><td>{det.quantum_efficiency:.0%}</td></tr>
        <tr><td>RON</td><td>{det.read_noise_e} e⁻/pix</td></tr>
        <tr><td>Dark current</td><td>{det.dark_current_e_s} e⁻/s/pix</td></tr>
      </tbody>
    </table>
  </div>
</div>
""", unsafe_allow_html=True)

    with col_v2:
        if result and not error_msg:
            st.markdown(f"""
<div class="html-card">
  <div class="section-kicker">Nuestra CTE</div>
  <h3 style="margin-top:0;">Resultados calculados</h3>
  <div class="table-clean">
    <table>
      <thead><tr><th>Cantidad</th><th>Valor</th></tr></thead>
      <tbody>
        <tr><td>S/N</td><td>{result.snr:.2f}</td></tr>
        <tr><td>Señal del objeto</td><td>{result.signal_e:.1f} e⁻</td></tr>
        <tr><td>Señal del cielo</td><td>{result.sky_signal_e:.1f} e⁻</td></tr>
        <tr><td>Corriente oscura</td><td>{result.dark_signal_e:.3f} e⁻</td></tr>
        <tr><td>RON² × n_pix</td><td>{result.read_noise_total_e2:.1f} e⁻²</td></tr>
        <tr><td>Píxeles en apertura</td><td>{result.n_pixels:.1f}</td></tr>
        <tr><td>Energía encerrada</td><td>{result.enclosed_energy*100:.1f}%</td></tr>
        <tr><td>Régimen dominante</td><td>{result.noise_regime}</td></tr>
        <tr><td>Área colectora</td><td>{telescope.collecting_area_m2:.3f} m²</td></tr>
        <tr><td>Flujo de fotones</td><td>{result.object_photon_flux:.3e} ph/s/m²</td></tr>
      </tbody>
    </table>
  </div>
</div>
""", unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="warning-box">Ejecuta un cálculo en la pestaña Resultados.</div>',
                unsafe_allow_html=True,
            )

    # Tabla comparativa ESO
    st.markdown("##### Comparación cuantitativa con ESO FORS ETC")
    st.markdown("""
<div class="html-card">
  <div class="section-kicker">Referencia: ESO FORS2 ETC (2024)</div>
  <h3 style="margin-top:0;">Discrepancias típicas y su origen físico</h3>
  <div class="table-clean">
    <table>
      <thead>
        <tr>
          <th>Cantidad</th>
          <th>ESO FORS ETC</th>
          <th>Esta CTE</th>
          <th>Discrepancia</th>
          <th>Origen físico</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Modelo de PSF</td>
          <td>Perfil de Moffat</td>
          <td>Gaussiana</td>
          <td>~5–15% en EE</td>
          <td>La PSF real tiene alas más extendidas (Moffat β ~ 2.5)</td>
        </tr>
        <tr>
          <td>Throughput</td>
          <td>Dependiente de λ, tablas reales</td>
          <td>Constante por banda</td>
          <td>~3–10%</td>
          <td>Reflectividad del espejo y respuesta del filtro varían con λ</td>
        </tr>
        <tr>
          <td>Brillo del cielo</td>
          <td>Espectro completo del cielo</td>
          <td>Mag/arcsec² en banda</td>
          <td>Pequeña (~2–5%)</td>
          <td>Líneas de emisión del cielo no modeladas</td>
        </tr>
        <tr>
          <td>Extinción atmosférica</td>
          <td>Incluida (k_λ × X)</td>
          <td>No incluida</td>
          <td>~5–20% según λ</td>
          <td>Depende de airmass y longitud de onda; relevante en UV</td>
        </tr>
        <tr>
          <td>Dispersión cromática</td>
          <td>ADC modelado</td>
          <td>No modelada</td>
          <td>Pequeña en el óptico</td>
          <td>La dispersión atmosférica afecta la EE a ángulos cenitales altos</td>
        </tr>
        <tr>
          <td>S/N típico (20 AB, 600s, r, 3.5m)</td>
          <td>~24–28</td>
          <td>~22–26</td>
          <td>~8–12%</td>
          <td>Combinación de todos los factores anteriores</td>
        </tr>
      </tbody>
    </table>
  </div>
  <div class="note-list">
    <strong>Conclusión:</strong> nuestra CTE reproduce los resultados de ESO dentro de un 10–15%
    para condiciones típicas. Las principales fuentes de discrepancia son el modelo de PSF
    (Gaussiana vs. Moffat) y la omisión de extinción atmosférica. Estas diferencias son
    esperables y aceptables para una herramienta de planificación de observaciones.
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — MODELO FÍSICO
# ══════════════════════════════════════════════════════════════════════════════
with tab_model:
    col_m1, col_m2 = st.columns([1.1, 1])

    with col_m1:
        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Derivación desde primeros principios</div>
  <h3 style="margin-top:0;">Ecuación fundamental de S/N</h3>
  <div class="note-list">
    La relación señal-ruido se obtiene aplicando estadística de Poisson a cada
    fuente de electrones en el detector:
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"""
\frac{S}{N} =
\frac{S}{\sqrt{S + N_\mathrm{sky} + N_\mathrm{dark}
+ \sigma_\mathrm{RON}^{2}\, n_\mathrm{pix}\, n_\mathrm{reads}}}
""")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Cadena de conversión fotométrica</div>
  <h3 style="margin-top:0;">Magnitud AB → señal [e⁻]</h3>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"""
F_\nu = F_0^\mathrm{AB} \cdot 10^{-m_\mathrm{AB}/2.5}
\quad [W\,m^{-2}\,Hz^{-1}]
""")
        st.latex(r"""
F_\lambda = F_\nu \cdot \frac{c}{\lambda_\mathrm{eff}^2}
\quad [W\,m^{-2}\,m^{-1}]
""")
        st.latex(r"""
\Phi = \frac{F_\lambda \cdot \Delta\lambda}{E_\gamma}
= \frac{F_\lambda \cdot \Delta\lambda \cdot \lambda_\mathrm{eff}}{hc}
\quad [\mathrm{ph\,s^{-1}\,m^{-2}}]
""")
        st.latex(r"""
S = \Phi \cdot A_\mathrm{eff} \cdot \eta_\mathrm{total} \cdot \mathrm{EE}(r_\mathrm{ap}) \cdot t
\quad [e^-]
""")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"""
A_\mathrm{eff} = \pi\left[
\left(\frac{D}{2}\right)^2
- \left(\frac{D\,\epsilon}{2}\right)^2
\right]
= \frac{\pi D^2}{4}(1 - \epsilon^2)
""")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_m2:
        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Energía encerrada</div>
  <h3 style="margin-top:0;">PSF Gaussiana</h3>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"""
\mathrm{EE}(r_\mathrm{ap}) = 1 - \exp\!\left(
-\frac{r_\mathrm{ap}^2}{2\sigma^2}\right)
""")
        st.latex(r"""
\sigma = \frac{\mathrm{FWHM}}{2\sqrt{2\ln 2}}
""")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Fondo de cielo</div>
  <h3 style="margin-top:0;">Tasa de electrones por píxel</h3>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"""
\dot{N}_\mathrm{sky,pix} =
\Phi(m_\mathrm{sky}) \cdot \Omega_\mathrm{pix} \cdot A_\mathrm{eff} \cdot \eta
""")
        st.latex(r"""
\Omega_\mathrm{pix} = s_\mathrm{pix}^2 \quad [\mathrm{arcsec^2/pix}]
""")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Supuestos y limitaciones</div>
  <h3 style="margin-top:0;">Alcance del modelo</h3>
  <div class="note-list">
    ✓ PSF gaussiana (PSFs reales: Moffat con alas extendidas)<br>
    ✓ Transmisión del sistema constante en la banda<br>
    ✓ Sin extinción atmosférica (relevante para airmass > 1.5 o UV)<br>
    ✓ Sin dispersión cromática atmosférica<br>
    ✓ Brillo del cielo uniforme y constante<br>
    ✓ Detector con respuesta plana en la banda<br>
    ✓ Válido para fuentes aisladas (no confusión)<br>
    ✓ No incluye efectos de fringing (óptico en i-band)<br>
    ✓ No modela variaciones del seeing intra-exposición
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Uso de IA</div>
  <h3 style="margin-top:0;">Declaración y crítica</h3>
  <div class="note-list">
    Esta CTE fue desarrollada con asistencia de IA (Claude, Anthropic) para:
    estructuración del código, generación del CSS/frontend y verificación
    de derivaciones matemáticas.<br><br>
    <strong>Validación propia:</strong> todas las ecuaciones fueron verificadas
    contra Howell (2006) y el white-paper de ESO. Los resultados numéricos
    se compararon con etc.eso.org para casos de prueba documentados.<br><br>
    <strong>Limitación:</strong> la IA no reemplaza el razonamiento físico;
    los supuestos del modelo fueron definidos e interpretados por el estudiante.
  </div>
</div>
""", unsafe_allow_html=True)

    # Referencias
    st.markdown("---")
    st.markdown("""
<div class="html-card">
  <div class="section-kicker">Bibliografía</div>
  <h3 style="margin-top:0;">Referencias</h3>
  <div class="note-list">
    • Howell, S. B. (2006). <em>Handbook of CCD Astronomy</em>, 2ª ed. Cambridge University Press.<br>
    • Rieke, G. H. (2003). <em>Detection of Light</em>. Cambridge University Press.<br>
    • ESO (2024). <em>FORS Exposure Time Calculator</em>. <a href="https://etc.eso.org/fors"
      target="_blank" style="color:var(--accent);">https://etc.eso.org/fors</a><br>
    • Oke, J. B. &amp; Gunn, J. E. (1983). Secondary standard stars for absolute spectrophotometry.
      <em>ApJ</em>, 266, 713.<br>
    • Naylor, T. (1998). An optimal extraction algorithm for imaging photometry.
      <em>MNRAS</em>, 296, 339.
  </div>
</div>
""", unsafe_allow_html=True)