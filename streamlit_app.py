"""
frontend.py — Calculadora de Tiempo de Exposición (CTE) — Interfaz Streamlit
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
import json
import streamlit as st
import plotly.graph_objects as go

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
    ESO_FILTER_MAP,
    ESO_REFERENCE_VALUES,
    build_eso_payload,
    compare_with_eso,
    get_eso_reference,
    parse_eso_result,
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
        "plot_line2": "#0f766e",
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
        "plot_line2": "#2dd4bf",
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
# CSS global
# ---------------------------------------------------------------------------
st.markdown(f"""
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

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
body {{ color: var(--text); }}

.stApp {{
  background:
    radial-gradient(circle at top left, rgba(59,130,246,0.08), transparent 25%),
    linear-gradient(180deg, var(--bg) 0%, var(--bg-soft) 100%);
  color: var(--text);
}}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {{
  background: var(--sidebar) !important;
  border-right: 1px solid var(--border) !important;
}}
section[data-testid="stSidebar"] .block-container {{
  padding-top: 1rem;
}}
/* Etiquetas en sidebar */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div {{ color: var(--text); }}
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
  color: var(--text-muted) !important;
}}
/* Inputs en sidebar */
section[data-testid="stSidebar"] .stSelectbox > div > div,
section[data-testid="stSidebar"] .stNumberInput input {{
  background: var(--surface-2) !important;
  border-color: var(--border) !important;
  color: var(--text) !important;
}}

/* ── Tipografía ── */
h1, h2, h3 {{
  font-family: 'Source Serif 4', serif !important;
  color: var(--text);
  letter-spacing: -0.02em;
}}
h1 {{ font-size: 2rem; line-height: 1.04; }}
h2 {{ font-size: 1.3rem; line-height: 1.12; margin-top: 0.2rem; }}
h3 {{ font-size: 1.04rem; line-height: 1.18; }}
p, li, div, span, label {{ color: var(--text); }}
small, .stCaption, [data-testid="stCaptionContainer"] {{
  color: var(--text-muted) !important;
}}

/* ── Métricas ── */
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

/* ── Tabs ── */
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
}}
.stTabs [aria-selected="true"] {{
  background: var(--accent-soft) !important;
  color: var(--accent) !important;
}}
.stTabs [data-baseweb="tab-panel"] {{ padding-top: 1rem !important; }}

/* ── Botones ── */
.stButton > button {{
  border-radius: 999px !important;
  font-weight: 600 !important;
}}

/* ── Componentes propios ── */
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
.sky-limited        {{ background: var(--sky-bg);  color: var(--sky-text);  border-color: var(--sky-border); }}
.read-noise-limited {{ background: var(--read-bg); color: var(--read-text); border-color: var(--read-border); }}
.shot-noise-limited {{ background: var(--shot-bg); color: var(--shot-text); border-color: var(--shot-border); }}
.dark-limited       {{ background: var(--dark-bg); color: var(--dark-text); border-color: var(--dark-border); }}
.info-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
  gap: 0.8rem 1rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}}
.info-item {{ display: flex; flex-direction: column; gap: 0.12rem; }}
.info-item-label {{
  color: var(--text-soft);
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}
.info-item-value {{ color: var(--text); font-size: 0.9rem; font-weight: 600; }}
.html-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 1rem 1rem 0.9rem 1rem;
  box-shadow: var(--shadow);
  margin-bottom: 1rem;
}}
.table-clean table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
.table-clean th, .table-clean td {{
  text-align: left;
  padding: 0.48rem 0.25rem;
  border-bottom: 1px solid var(--border);
}}
.table-clean th {{ color: var(--text-soft); font-weight: 600; }}
/* Caja ecuación — solo para contenido HTML puro, NO mezclar con st.latex */
.eq-wrap {{
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 0.85rem 0.85rem 0.6rem 0.85rem;
  margin: 0.65rem 0 1rem 0;
}}
.note-list {{
  color: var(--text-muted);
  font-size: 0.92rem;
  line-height: 1.65;
  margin-top: 0.75rem;
}}
/* Separador sidebar */
.sidebar-sep {{
  border: none;
  border-top: 1px solid var(--border);
  margin: 0.6rem 0;
}}
@media (max-width: 900px) {{
  .topbar-title {{ font-size: 1.42rem; }}
  .result-value {{ font-size: 2.35rem; }}
}}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — mismo estilo que el código de referencia
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🔭 Configuración")
    st.caption("Óptico / Infrarrojo cercano · Modelo inspirado en ESO")

    # ── Telescopio ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Telescopio")
    diam = st.selectbox(
        "Apertura del primario (m)",
        options=TELESCOPE_APERTURES,
        index=1,
        format_func=lambda x: f"{x:.1f} m",
        help="Diámetro del espejo primario. Opciones del proyecto: 2.0, 3.5, 6.5, 8.0 m.",
    )
    obstruction = st.slider(
        "Obstrucción central (fracción lineal)",
        min_value=0.0, max_value=0.4, value=0.12, step=0.01,
        help="Fracción del diámetro primario bloqueada por el espejo secundario.",
    )
    throughput = st.slider(
        "Transmisión total del sistema",
        min_value=0.1, max_value=1.0, value=0.80, step=0.01,
        help="Transmisión combinada de óptica, espejos y filtro.",
    )

    # ── Filtro y modo ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Filtro y modo")
    mode = st.radio("Modo de observación", ["Optical", "Near-IR"], horizontal=True)
    filter_dict = OPTICAL_FILTERS if mode == "Optical" else NIR_FILTERS
    filter_name = st.selectbox("Filtro", list(filter_dict.keys()))
    filt = filter_dict[filter_name]
    det = detector_for_filter(filt)

    lam_label = (
        f"{filt.lambda_eff_angstrom*1e-4:.2f} μm"
        if filt.mode == "nir"
        else f"{filt.lambda_eff_angstrom:.0f} Å"
    )
    st.caption(
        f"λ_eff = {lam_label} · "
        f"Δλ = {filt.delta_lambda_angstrom:.0f} Å · "
        f"Cielo = {filt.sky_mag_arcsec2:.1f} mag/arcsec²"
    )

    # ── Fuente ───────────────────────────────────────────────────────────────
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
        min_value=0.0, max_value=35.0, value=20.0, step=0.5,
        help="Magnitud AB del objeto en el filtro seleccionado.",
    )

    # ── Condiciones de observación ───────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Condiciones de observación")
    seeing = st.slider(
        "Seeing FWHM (arcsec)",
        min_value=0.3, max_value=3.0, value=0.80, step=0.05,
    )
    use_auto_ap = st.checkbox(
        "Apertura automática (r = 1.2 × FWHM)",
        value=True,
        help="Recomendado: optimiza el S/N en régimen de cielo.",
    )
    if use_auto_ap:
        ap_radius = default_aperture_radius(seeing)
        st.caption(f"Radio de apertura: **{ap_radius:.2f}** arcsec")
    else:
        ap_radius = st.slider(
            "Radio de apertura (arcsec)",
            min_value=0.3, max_value=5.0,
            value=round(default_aperture_radius(seeing), 1),
            step=0.1,
            help="Radio de la apertura fotométrica circular.",
        )
    n_reads = st.number_input(
        "Número de lecturas del detector",
        min_value=1, max_value=50, value=1,
        help="Para muestreo NIR up-the-ramp, usar > 1.",
    )

    # ── Modo de cálculo ──────────────────────────────────────────────────────
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
            min_value=0.1, max_value=1e6, value=600.0, step=10.0,
        )
        target_snr_input = None
    else:
        target_snr_input = st.number_input(
            "S/N objetivo",
            min_value=1.0, max_value=1000.0, value=10.0, step=1.0,
        )
        exp_time = None

    # ── Rango gráfica ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Rango de la gráfica")
    t_start_log = st.slider("t_min  log₁₀(s)", 0.0, 3.0, 0.5, 0.1)
    t_end_log   = st.slider("t_max  log₁₀(s)", 1.0, 5.0, 3.6, 0.1)

    # ── Botón tema ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.button(
        "🌙 Modo oscuro" if theme == "light" else "☀️ Modo claro",
        help="Cambiar tema",
        on_click=toggle_theme,
        use_container_width=True,
    )

# ---------------------------------------------------------------------------
# Barra superior
# ---------------------------------------------------------------------------
top_left, top_mid, top_right = st.columns([10, 0.4, 1.2])

with top_left:
    st.markdown("""
<div class="topbar">
  <div class="kicker">Herramienta académica de observación</div>
  <div class="topbar-title">Calculadora de Tiempo de Exposición</div>
  <div class="topbar-subtitle">
    Interfaz fotométrica para estimar tiempo de exposición o relación señal-ruido
    en observaciones ópticas y de infrarrojo cercano.
  </div>
</div>
""", unsafe_allow_html=True)

mode_label = "Óptico" if mode == "Optical" else "Infrarrojo cercano"
st.markdown(f"""
<div class="meta-line">
<strong>Modo {mode_label}</strong> · Filtro <strong>{filter_name}</strong> ·
Telescopio <strong>{diam:.1f} m</strong> · Objeto <strong>{object_mag:.1f} AB mag</strong>
</div>
""", unsafe_allow_html=True)

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
error_msg = None
result = None
try:
    if calc_mode == "S/N dado el tiempo de exposición":
        result = compute_snr(object_mag, exp_time, telescope, filt, det, conditions, src)
    else:
        result = compute_exposure_time(
            object_mag, target_snr_input, telescope, filt, det, conditions, src
        )
except ValueError as exc:
    error_msg = str(exc)

# ---------------------------------------------------------------------------
# Utilidad ticks logarítmicos
# ---------------------------------------------------------------------------
def build_log_ticks(tmin, tmax):
    exponents = range(int(math.floor(math.log10(tmin))),
                      int(math.ceil(math.log10(tmax))) + 1)
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

# ---------------------------------------------------------------------------
# Layout principal — Tabs
# ---------------------------------------------------------------------------
tab_results, tab_curves, tab_budget, tab_validation, tab_model = st.tabs([
    "📊 Resultados",
    "📈 Curvas S/N",
    "🎛️ Presupuesto de ruido",
    "🔬 Validación ESO",
    "📐 Modelo físico",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — RESULTADOS
# ══════════════════════════════════════════════════════════════════════════════
with tab_results:
    col_main, col_side = st.columns([3.35, 1.75], gap="large")

    with col_main:
        st.markdown("## Resultados")

        if error_msg:
            st.error(f"⚠️ {error_msg}")
        elif result:
            regime_css   = result.noise_regime.replace(" ", "-").replace("/", "-")
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

            st.markdown(f"""
<div class="result-card">
  <div class="section-kicker">Resultado principal</div>
  <div class="result-label">{primary_label}</div>
  <div class="result-value">{primary_value}</div>
  <div class="result-subtitle">{secondary}</div>
  <span class="regime-badge {regime_css}">{regime_label}</span>
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
      <div class="info-item-label">RON² × n_pix × n_reads</div>
      <div class="info-item-value">{result.read_noise_total_e2:.1f} e⁻²</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">Píxeles de apertura</div>
      <div class="info-item-value">{result.n_pixels:.1f} pix</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">Energía encerrada</div>
      <div class="info-item-value">{result.enclosed_energy*100:.1f} %</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Área colectora",    f"{telescope.collecting_area_m2:.3f} m²")
            m2.metric("Eficiencia cuántica", f"{det.quantum_efficiency*100:.0f} %")
            m3.metric("Ruido de lectura",  f"{det.read_noise_e} e⁻/pix")
            m4.metric("Corriente oscura",  f"{det.dark_current_e_s} e⁻/s/pix")

            # Magnitud límite
            st.markdown("---")
            col_lim1, col_lim2 = st.columns([3, 1])
            with col_lim1:
                st.markdown("#### Magnitud límite (S/N = 5)")
                st.caption(
                    "Objeto más débil detectable con S/N ≥ 5 para el tiempo de exposición actual."
                )
            with col_lim2:
                try:
                    t_ref = (
                        result.time_for_target_snr
                        if result.time_for_target_snr
                        else result.exposure_time_s
                    )
                    mag_lim = limiting_magnitude(
                        t_ref, 5.0, telescope, filt, det, conditions, src
                    )
                    st.metric("Mag. límite", f"{mag_lim:.2f} AB")
                except Exception:
                    st.caption("No calculable.")

    with col_side:
        st.markdown("## Detalles técnicos")

        st.markdown(f"""
<div class="html-card">
  <div class="section-kicker">Instrumento</div>
  <h3 style="margin-top:0;">Parámetros del detector</h3>
  <div class="table-clean">
    <table>
      <thead><tr><th>Parámetro</th><th>Valor</th></tr></thead>
      <tbody>
        <tr><td>Ruido de lectura</td><td>{det.read_noise_e} e⁻/pix</td></tr>
        <tr><td>Corriente oscura</td><td>{det.dark_current_e_s} e⁻/s/pix</td></tr>
        <tr><td>Escala de píxel</td><td>{det.pixel_scale_arcsec} arcsec/pix</td></tr>
        <tr><td>Eficiencia cuántica</td><td>{det.quantum_efficiency*100:.0f} %</td></tr>
      </tbody>
    </table>
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown(f"""
<div class="html-card">
  <div class="section-kicker">Configuración espectral</div>
  <h3 style="margin-top:0;">Parámetros del filtro</h3>
  <div class="table-clean">
    <table>
      <thead><tr><th>Parámetro</th><th>Valor</th></tr></thead>
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
""", unsafe_allow_html=True)

        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Interpretación</div>
  <h3 style="margin-top:0;">Regímenes de ruido</h3>
  <div class="note-list">
    🔵 <strong>Sky-limited</strong> — domina el fondo de cielo<br>
    🟣 <strong>Read-noise-limited</strong> — exposiciones cortas o cielo tenue<br>
    🟢 <strong>Shot-noise-limited</strong> — domina la señal del objeto<br>
    🟠 <strong>Dark-limited</strong> — domina la corriente oscura
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Alcance del modelo</div>
  <h3 style="margin-top:0;">Supuestos y limitaciones</h3>
  <div class="note-list">
    · PSF gaussiana (reales tienen alas más extensas)<br>
    · Sin extinción atmosférica ni dispersión cromática<br>
    · Modelo de una sola época y un solo filtro<br>
    · Brillo de cielo fijo por banda<br>
    · Respuesta plana del detector en la banda
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CURVAS S/N
# ══════════════════════════════════════════════════════════════════════════════
with tab_curves:
    t_start = 10 ** t_start_log
    t_end   = 10 ** t_end_log

    tab_snr_t, tab_snr_mag = st.tabs(["S/N vs. tiempo", "S/N vs. magnitud"])

    # ── S/N vs. tiempo ───────────────────────────────────────────────────────
    with tab_snr_t:
        t_arr, snr_arr = snr_vs_time(
            object_mag, telescope, filt, det, conditions, src,
            t_start=t_start, t_end=t_end,
        )
        tickvals, ticktext = build_log_ticks(t_start, t_end)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=t_arr, y=snr_arr, mode="lines", name="Curva S/N",
            line=dict(color=T["plot_line"], width=3),
            hovertemplate="t = %{x:.2f} s<br>S/N = %{y:.2f}<extra></extra>",
        ))

        if result and not error_msg:
            t_op   = result.time_for_target_snr if result.time_for_target_snr else result.exposure_time_s
            snr_op = result.snr
            fig.add_trace(go.Scatter(
                x=[t_op], y=[snr_op], mode="markers", name="Punto de operación",
                marker=dict(color=T["plot_point"], size=10,
                            line=dict(width=1, color=T["plot_paper"])),
                hovertemplate=(
                    f"Punto de operación<br>t = {t_op:.2f} s<br>"
                    f"S/N = {snr_op:.2f}<extra></extra>"
                ),
            ))
            fig.add_vline(x=t_op, line_width=1.2, line_dash="dash",
                          line_color=T["plot_point"], opacity=0.85)
            fig.add_hline(y=snr_op, line_width=1.2, line_dash="dash",
                          line_color=T["plot_point"], opacity=0.85)

        if target_snr_input and calc_mode == "Tiempo de exposición dado el S/N":
            fig.add_hline(
                y=target_snr_input, line_width=1.1, line_dash="dot",
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
            font=dict(family="Inter, sans-serif", size=13, color=T["plot_axis"]),
            title=dict(
                text=f"Filtro {filt.name} · {object_mag:.1f} AB mag · D = {diam:.1f} m",
                font=dict(size=15, color=T["plot_axis"]),
                x=0.02, xanchor="left", y=0.97,
            ),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.03,
                xanchor="left", x=0.0,
                bgcolor="rgba(0,0,0,0)", font=dict(size=12),
            ),
        )
        fig.update_xaxes(
            type="log", title="Tiempo de exposición",
            tickmode="array", tickvals=tickvals, ticktext=ticktext,
            showgrid=True, gridcolor=T["plot_grid"],
            zeroline=False, linecolor=T["plot_grid"],
            tickfont=dict(size=11), title_font=dict(size=13),
        )
        fig.update_yaxes(
            title="Relación señal-ruido",
            showgrid=True, gridcolor=T["plot_grid"],
            zeroline=False, linecolor=T["plot_grid"],
            tickfont=dict(size=11), title_font=dict(size=13),
        )
        st.markdown('<div class="plot-shell">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    # ── S/N vs. magnitud ─────────────────────────────────────────────────────
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
            x=mag_arr, y=snr_mag_arr, mode="lines", name="S/N(mag)",
            line=dict(color=T["plot_line2"], width=2.5),
            hovertemplate="mag = %{x:.2f}<br>S/N = %{y:.2f}<extra></extra>",
        ))
        fig_m.add_hline(
            y=5.0, line_width=1.2, line_dash="dot",
            line_color=T["plot_target"], opacity=0.85,
            annotation_text="S/N = 5 (mag. límite)",
            annotation_position="top right",
        )
        if result and not error_msg:
            fig_m.add_vline(
                x=object_mag, line_width=1, line_dash="dash",
                line_color=T["plot_point"], opacity=0.7,
            )
        fig_m.update_layout(
            template="plotly_dark" if theme == "dark" else "plotly_white",
            height=460,
            margin=dict(l=55, r=28, t=78, b=58),
            paper_bgcolor=T["plot_paper"],
            plot_bgcolor=T["plot_bg"],
            font=dict(family="Inter, sans-serif", size=13, color=T["plot_axis"]),
            title=dict(
                text=f"S/N vs. magnitud · t = {format_time(t_ref_mag)} · D = {diam:.1f} m",
                font=dict(size=15, color=T["plot_axis"]),
                x=0.02, xanchor="left", y=0.97,
            ),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.03,
                xanchor="left", x=0.0,
                bgcolor="rgba(0,0,0,0)", font=dict(size=12),
            ),
        )
        fig_m.update_xaxes(
            title="Magnitud AB", autorange="reversed",
            showgrid=True, gridcolor=T["plot_grid"],
            zeroline=False, linecolor=T["plot_grid"],
            tickfont=dict(size=11), title_font=dict(size=13),
        )
        fig_m.update_yaxes(
            title="Relación señal-ruido",
            showgrid=True, gridcolor=T["plot_grid"],
            zeroline=False, linecolor=T["plot_grid"],
            tickfont=dict(size=11), title_font=dict(size=13),
        )
        st.markdown('<div class="plot-shell">', unsafe_allow_html=True)
        st.plotly_chart(fig_m, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PRESUPUESTO DE RUIDO
# ══════════════════════════════════════════════════════════════════════════════
with tab_budget:
    if error_msg:
        st.error(f"⚠️ {error_msg}")
    elif result:
        budget = noise_budget(result)
        st.markdown("#### Distribución de la varianza del ruido")
        st.caption(
            "Fracción de la varianza total proveniente de cada fuente de ruido. "
            "El término dominante define el régimen de la observación."
        )

        labels_pie = ["Shot noise\n(objeto)", "Fondo de cielo",
                      "Corriente oscura", "Ruido de lectura"]
        values_pie = [budget["shot_noise"], budget["sky"],
                      budget["dark"], budget["read_noise"]]
        colors_pie = [T["plot_line"], T["plot_line2"], T["plot_target"], T["plot_point"]]

        fig_pie = go.Figure(go.Pie(
            labels=labels_pie, values=values_pie,
            hole=0.52,
            marker=dict(colors=colors_pie,
                        line=dict(color=T["plot_bg"], width=2)),
            textinfo="label+percent",
            textfont=dict(size=12, family="Inter, sans-serif", color=T["plot_axis"]),
            hovertemplate="%{label}<br>%{value:.1f}% de la varianza<extra></extra>",
        ))
        fig_pie.update_layout(
            template="plotly_dark" if theme == "dark" else "plotly_white",
            paper_bgcolor=T["plot_paper"],
            plot_bgcolor=T["plot_bg"],
            font=dict(family="Inter, sans-serif", size=12, color=T["plot_axis"]),
            height=380,
            margin=dict(l=16, r=16, t=50, b=20),
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle", y=0.5,
                xanchor="left",   x=1.02,
                bgcolor="rgba(0,0,0,0)",
                font=dict(size=11),
            ),
            title=dict(
                text="Contribuciones al ruido",
                font=dict(size=14, color=T["plot_axis"]),
                x=0.01, y=0.97, xanchor="left",
            ),
            annotations=[dict(
                text=f"<b>S/N</b><br>{result.snr:.1f}",
                x=0.5, y=0.5,
                font=dict(size=16, color=T["plot_axis"],
                          family="Source Serif 4, serif"),
                showarrow=False,
            )],
        )

        col_pie, col_tbl = st.columns([1.3, 1])
        with col_pie:
            st.markdown('<div class="plot-shell">', unsafe_allow_html=True)
            st.plotly_chart(fig_pie, use_container_width=True,
                            config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

        with col_tbl:
            regime_descriptions = {
                "sky-limited":        "El fondo de cielo domina. Mayor telescopio ayuda; reducir apertura también.",
                "read-noise-limited": "RON domina. Usar exposiciones más largas o co-adición mejora el S/N.",
                "shot-noise-limited": "Shot noise del objeto domina. S/N ∝ √t; más área o más tiempo ayudan.",
                "dark-limited":       "Corriente oscura domina. Enfriar el detector o reducir t mejora el S/N.",
            }
            st.markdown(f"""
<div class="html-card">
  <div class="section-kicker">Tabla de varianza</div>
  <h3 style="margin-top:0;">Términos de ruido</h3>
  <div class="table-clean">
    <table>
      <thead><tr><th>Fuente</th><th>Varianza (e⁻²)</th><th>%</th></tr></thead>
      <tbody>
        <tr><td>Shot noise</td><td>{result.signal_e:.1f}</td><td>{budget['shot_noise']:.1f}%</td></tr>
        <tr><td>Cielo</td><td>{result.sky_signal_e:.1f}</td><td>{budget['sky']:.1f}%</td></tr>
        <tr><td>Dark current</td><td>{result.dark_signal_e:.3f}</td><td>{budget['dark']:.2f}%</td></tr>
        <tr><td>Ruido de lectura</td><td>{result.read_noise_total_e2:.1f}</td><td>{budget['read_noise']:.1f}%</td></tr>
        <tr style="font-weight:600;"><td>Total</td><td>{budget['total_var']:.1f}</td><td>100%</td></tr>
      </tbody>
    </table>
  </div>
</div>
<div class="html-card">
  <div class="section-kicker">Régimen dominante</div>
  <span class="regime-badge {result.noise_regime.replace(' ','-').replace('/','-')}"
        style="margin-top:0.3rem;">{result.noise_regime}</span>
  <div class="note-list" style="margin-top:0.6rem;">
    {regime_descriptions.get(result.noise_regime, "")}
  </div>
</div>
""", unsafe_allow_html=True)
    else:
        st.info("Ejecuta un cálculo primero en la pestaña **Resultados**.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — MODELO FÍSICO
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — VALIDACIÓN ESO
# ══════════════════════════════════════════════════════════════════════════════
with tab_validation:
    st.markdown("## Validación contra ETC de ESO")
    st.markdown("""
<div class="html-card">
  <div class="section-kicker">Cómo usar esta pestaña</div>
  <h3 style="margin-top:0;">Flujo de trabajo en dos pasos</h3>
  <div class="note-list">
    <strong>Paso 1 — Obtener datos ESO (en tu máquina):</strong><br>
    &nbsp;&nbsp;Ejecuta <code>eso_validation.py</code> incluido en el proyecto:<br>
    &nbsp;&nbsp;<code>python eso_validation.py -f g r i J H Ks -m 20.0 -t 600 -o eso_results.json</code><br><br>
    <strong>Paso 2 — Cargar resultados aquí:</strong><br>
    &nbsp;&nbsp;Sube el archivo <code>eso_results.json</code> generado usando el botón de abajo.<br><br>
    Si no puedes ejecutar el script, también puedes ver la comparación con los
    <strong>valores de referencia estáticos</strong> pre-calculados desde el ETC de ESO
    (VLT 8.2 m, seeing 0.8", G2V 20 AB mag, t=600 s).
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Instrucciones CLI ───────────────────────────────────────────────────
    with st.expander("📋 Comandos de ejemplo para eso_validation.py"):
        st.code("""# Todos los filtros con parámetros por defecto
python eso_validation.py

# Solo filtros ópticos, objeto de 21 AB mag, 900 s
python eso_validation.py -f g r i -m 21.0 -t 900

# NIR con seeing diferente
python eso_validation.py -f J H Ks --seeing 0.6 -o eso_nir.json

# Servidor alternativo (si etc.eso.org no responde)
python eso_validation.py -s https://etctestpub.eso.org
""", language="bash")

    st.markdown("---")

    # ── Carga de archivo JSON de ESO ────────────────────────────────────────
    col_up, col_ref = st.columns([1, 1], gap="large")

    with col_up:
        st.markdown("### Cargar resultados ESO")
        uploaded_file = st.file_uploader(
            "Archivo JSON generado por eso_validation.py",
            type=["json"],
            help="Sube el archivo eso_results.json producido por eso_validation.py",
        )

    with col_ref:
        st.markdown("### O usar valores de referencia estáticos")
        use_static = st.checkbox(
            "Usar valores pre-calculados (VLT 8.2 m, G2V 20 AB, t=600 s)",
            value=True,
            help="Valores obtenidos directamente del ETC de ESO como referencia fija.",
        )

    # ── Obtener datos de referencia ─────────────────────────────────────────
    eso_data: dict = {}  # filter -> parsed dict

    if uploaded_file is not None:
        try:
            raw_upload = json.load(uploaded_file)
            # Extraer por filtro
            for filt, fdata in raw_upload.get("filters", {}).items():
                if fdata.get("snr") is not None:
                    eso_data[filt] = {
                        "snr":        fdata.get("snr"),
                        "signal_e":   fdata.get("signal_e"),
                        "sky_e":      fdata.get("sky_e"),
                        "npix":       fdata.get("npix"),
                        "ee":         fdata.get("ee"),
                        "instrument": fdata.get("instrument", "ESO"),
                        "aperture_m": 8.2,
                        "source":     "Archivo cargado",
                    }
            if eso_data:
                st.success(f"✅ Cargados {len(eso_data)} filtros del archivo.")
            else:
                st.warning("El archivo no contiene resultados válidos.")
        except Exception as exc:
            st.error(f"Error al leer el archivo: {exc}")

    if use_static and not eso_data:
        for filt, ref in ESO_REFERENCE_VALUES.items():
            eso_data[filt] = {
                "snr":        ref["snr"],
                "signal_e":   ref["signal_e"],
                "sky_e":      ref["sky_e"],
                "npix":       ref["npix"],
                "ee":         ref["ee"],
                "instrument": ref["instrument"],
                "aperture_m": ref["aperture_m"],
                "source":     "Referencia estática ESO",
                "notes":      ref.get("notes", ""),
            }

    # ── Tabla de comparación ────────────────────────────────────────────────
    if eso_data and result and not error_msg:
        st.markdown("---")
        st.markdown("### Comparación cuantitativa")

        # Construir resultado nuestro para el filtro actual
        our_filt_name = filter_name  # filtro seleccionado en sidebar

        if our_filt_name in eso_data:
            ref = eso_data[our_filt_name]

            # Diferencias
            def pct(ours, theirs):
                if theirs and theirs != 0:
                    return 100.0 * (ours - theirs) / theirs
                return None

            def fmt_pct(p):
                if p is None:
                    return "N/A"
                sign = "+" if p >= 0 else ""
                return f"{sign}{p:.1f}%"

            def diff_color(p):
                if p is None:
                    return ""
                return "color:#86efac" if abs(p) < 10 else ("color:#fcd34d" if abs(p) < 25 else "color:#f9a8d4")

            rows = [
                ("S/N",                  result.snr,              ref.get("snr"),       ""),
                ("Señal objeto [e⁻]",    result.signal_e,         ref.get("signal_e"),  ""),
                ("Señal cielo [e⁻]",     result.sky_signal_e,     ref.get("sky_e"),     ""),
                ("Píxeles apertura",      result.n_pixels,         ref.get("npix"),      ""),
                ("Energía encerrada",     result.enclosed_energy,  ref.get("ee"),        ""),
            ]

            rows_html = ""
            for label, ours, theirs, _ in rows:
                p = pct(ours, theirs)
                theirs_str = f"{theirs:.2f}" if isinstance(theirs, float) else (str(theirs) if theirs else "N/A")
                rows_html += f"""
        <tr>
          <td>{label}</td>
          <td style="font-family:monospace;">{ours:.2f}</td>
          <td style="font-family:monospace;">{theirs_str}</td>
          <td style="font-family:monospace;{diff_color(p)}">{fmt_pct(p)}</td>
        </tr>"""

            instrument_label = ref.get("instrument", "ESO")
            aperture_label   = ref.get("aperture_m", 8.2)
            source_label     = ref.get("source", "ESO ETC")

            st.markdown(f"""
<div class="html-card">
  <div class="section-kicker">Filtro {our_filt_name} · Nuestra CTE ({diam:.1f} m) vs {instrument_label} ({aperture_label:.1f} m)</div>
  <h3 style="margin-top:0;">Resultados numéricos — {source_label}</h3>
  <div class="table-clean">
    <table>
      <thead>
        <tr>
          <th>Cantidad</th>
          <th>Nuestra CTE</th>
          <th>ESO {instrument_label}</th>
          <th>Diferencia</th>
        </tr>
      </thead>
      <tbody>{rows_html}
      </tbody>
    </table>
  </div>
  <div class="note-list" style="margin-top:0.8rem;">
    {ref.get("notes", "")}
  </div>
</div>
""", unsafe_allow_html=True)

        else:
            st.info(
                f"El filtro **{our_filt_name}** no está en los datos ESO cargados. "
                "Activa 'Usar valores de referencia estáticos' o carga un archivo que incluya este filtro."
            )

        # ── Gráfica comparativa de S/N para todos los filtros disponibles ───
        st.markdown("### S/N comparativo — todos los filtros")

        filtros_comunes = [f for f in eso_data if f in {**OPTICAL_FILTERS, **NIR_FILTERS}]

        if filtros_comunes:
            our_snrs, eso_snrs, labels_bar = [], [], []

            for f in filtros_comunes:
                fobj    = ({**OPTICAL_FILTERS, **NIR_FILTERS})[f]
                det_f   = detector_for_filter(fobj)
                r_f     = compute_snr(
                    object_mag,
                    result.exposure_time_s if result.time_for_target_snr is None else result.time_for_target_snr,
                    telescope, fobj, det_f, conditions, src,
                )
                our_snrs.append(r_f.snr)
                eso_snrs.append(eso_data[f].get("snr") or 0)
                labels_bar.append(f)

            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                name=f"Nuestra CTE ({diam:.1f} m)",
                x=labels_bar, y=our_snrs,
                marker_color=T["plot_line"],
                text=[f"{v:.1f}" for v in our_snrs],
                textposition="outside",
            ))
            fig_bar.add_trace(go.Bar(
                name=f"ESO ETC ({eso_data[filtros_comunes[0]].get('aperture_m', 8.2):.1f} m)",
                x=labels_bar, y=eso_snrs,
                marker_color=T["plot_point"],
                text=[f"{v:.1f}" for v in eso_snrs],
                textposition="outside",
            ))
            fig_bar.update_layout(
                template="plotly_dark" if theme == "dark" else "plotly_white",
                barmode="group",
                height=400,
                margin=dict(l=50, r=20, t=60, b=40),
                paper_bgcolor=T["plot_paper"],
                plot_bgcolor=T["plot_bg"],
                font=dict(family="Inter, sans-serif", size=12, color=T["plot_axis"]),
                title=dict(
                    text=f"S/N por filtro · {object_mag:.1f} AB mag · t={format_time(result.exposure_time_s if result.time_for_target_snr is None else result.time_for_target_snr)}",
                    font=dict(size=14, color=T["plot_axis"]),
                    x=0.01, xanchor="left", y=0.97,
                ),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.04,
                    xanchor="left", x=0.0,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=12),
                ),
                yaxis=dict(
                    title="S/N",
                    showgrid=True, gridcolor=T["plot_grid"],
                    zeroline=False,
                ),
                xaxis=dict(title="Filtro"),
            )
            st.markdown('<div class="plot-shell">', unsafe_allow_html=True)
            st.plotly_chart(fig_bar, use_container_width=True,
                            config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Explicación de discrepancias ─────────────────────────────────────
        st.markdown("### Explicación de discrepancias físicas")
        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Análisis comparativo</div>
  <h3 style="margin-top:0;">Origen de las diferencias</h3>
  <div class="table-clean">
    <table>
      <thead>
        <tr><th>Factor</th><th>ESO ETC</th><th>Nuestra CTE</th><th>Impacto típico</th></tr>
      </thead>
      <tbody>
        <tr>
          <td>Modelo de PSF</td>
          <td>Moffat (β ≈ 2.5)</td>
          <td>Gaussiana</td>
          <td>5–15% en EE y señal</td>
        </tr>
        <tr>
          <td>Apertura telescopio</td>
          <td>VLT 8.2 m / NTT 3.5 m</td>
          <td>Seleccionable (2–8 m)</td>
          <td>Escala como D²</td>
        </tr>
        <tr>
          <td>Throughput</td>
          <td>Curvas reales QE(λ), T(λ)</td>
          <td>Constante por banda</td>
          <td>3–10%</td>
        </tr>
        <tr>
          <td>Extinción atmosférica</td>
          <td>Incluida (k_λ × airmass)</td>
          <td>No incluida</td>
          <td>5–20% según λ y airmass</td>
        </tr>
        <tr>
          <td>Brillo del cielo</td>
          <td>Espectro completo ESO</td>
          <td>Mag/arcsec² fija por banda</td>
          <td>2–8%</td>
        </tr>
        <tr>
          <td>SED del objeto</td>
          <td>Plantilla G2V (Pickles)</td>
          <td>Fuente plana en F_ν (AB)</td>
          <td>Varía con color del objeto</td>
        </tr>
      </tbody>
    </table>
  </div>
  <div class="note-list" style="margin-top:0.8rem;">
    Una discrepancia de ≤ 15% en S/N es esperada y aceptable para una CTE simplificada.
    Las diferencias más grandes en NIR (J, H, Ks) se deben principalmente a la emisión
    térmica del telescopio y al modelo de corriente oscura del array IR, que no están
    incluidos en nuestro modelo simplificado.
  </div>
</div>
""", unsafe_allow_html=True)

    elif not result:
        st.info("Ejecuta primero un cálculo en la pestaña **📊 Resultados**.")
    elif not eso_data:
        st.info("Activa los valores de referencia estáticos o carga un archivo JSON de ESO.")


with tab_model:
    col_m1, col_m2 = st.columns([1.1, 1])

    with col_m1:
        # ── Bloque 1: ecuación fundamental ──────────────────────────────────
        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Derivación desde primeros principios</div>
  <h3 style="margin-top:0;">Ecuación fundamental de S/N</h3>
  <div class="note-list">
    La relación señal-ruido se obtiene aplicando estadística de Poisson
    a cada fuente de electrones en el detector:
  </div>
</div>
""", unsafe_allow_html=True)

        # st.latex fuera del html-card para que Streamlit lo renderice
        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"""
\frac{S}{N} =
\frac{S}{
\sqrt{S + N_\mathrm{sky} + N_\mathrm{dark}
+ \sigma_\mathrm{RON}^{2}\, n_\mathrm{pix}\, n_\mathrm{reads}
}}
""")
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Bloque 2: cadena de conversión ──────────────────────────────────
        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Cadena de conversión fotométrica</div>
  <h3 style="margin-top:0;">Magnitud AB → señal [e⁻]</h3>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"F_\nu = F_0^\mathrm{AB} \cdot 10^{-m_\mathrm{AB}/2.5} \quad [W\,m^{-2}\,Hz^{-1}]")
        st.latex(r"F_\lambda = F_\nu \cdot \frac{c}{\lambda_\mathrm{eff}^2} \quad [W\,m^{-2}\,m^{-1}]")
        st.latex(r"\Phi = \frac{F_\lambda \cdot \Delta\lambda \cdot \lambda_\mathrm{eff}}{hc} \quad [\mathrm{ph\,s^{-1}\,m^{-2}}]")
        st.latex(r"S = \Phi \cdot A_\mathrm{eff} \cdot \eta_\mathrm{total} \cdot \mathrm{EE}(r_\mathrm{ap}) \cdot t \quad [e^-]")
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Bloque 3: área efectiva ──────────────────────────────────────────
        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Telescopio</div>
  <h3 style="margin-top:0;">Área efectiva de recolección</h3>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"A_\mathrm{eff} = \pi\!\left[\left(\frac{D}{2}\right)^{\!2} - \left(\frac{D\epsilon}{2}\right)^{\!2}\right] = \frac{\pi D^2}{4}(1-\epsilon^2)")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_m2:
        # ── Bloque 4: energía encerrada ──────────────────────────────────────
        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Energía encerrada</div>
  <h3 style="margin-top:0;">PSF gaussiana bidimensional</h3>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"\mathrm{EE}(r_\mathrm{ap}) = 1 - \exp\!\left(-\frac{r_\mathrm{ap}^2}{2\sigma^2}\right)")
        st.latex(r"\sigma = \frac{\mathrm{FWHM}}{2\sqrt{2\ln 2}}")
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Bloque 5: cielo ──────────────────────────────────────────────────
        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Fondo de cielo</div>
  <h3 style="margin-top:0;">Tasa de electrones por píxel</h3>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"\dot{N}_\mathrm{sky,pix} = \Phi(m_\mathrm{sky}) \cdot \Omega_\mathrm{pix} \cdot A_\mathrm{eff} \cdot \eta")
        st.latex(r"\Omega_\mathrm{pix} = s_\mathrm{pix}^2 \quad [\mathrm{arcsec^2\,pix^{-1}}]")
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Bloque 6: supuestos ──────────────────────────────────────────────
        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Supuestos y limitaciones</div>
  <h3 style="margin-top:0;">Alcance del modelo</h3>
  <div class="note-list">
    ✓ PSF gaussiana (PSFs reales: perfil de Moffat con alas extendidas)<br>
    ✓ Transmisión constante en la banda (sin dependencia espectral)<br>
    ✓ Sin extinción atmosférica (relevante para airmass &gt; 1.5 o UV)<br>
    ✓ Sin dispersión cromática atmosférica<br>
    ✓ Brillo del cielo uniforme y constante<br>
    ✓ Detector con respuesta plana en la banda<br>
    ✓ Válido para fuentes aisladas (sin confusión de fuentes)<br>
    ✓ No incluye efectos de fringing en banda i
  </div>
</div>
""", unsafe_allow_html=True)

        # ── Bloque 7: referencias ────────────────────────────────────────────
        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Bibliografía</div>
  <h3 style="margin-top:0;">Referencias</h3>
  <div class="note-list">
    · Howell (2006) <em>Handbook of CCD Astronomy</em>, 2ª ed.<br>
    · Rieke (2003) <em>Detection of Light</em>, Cambridge UP<br>
    · ESO FORS ETC — <a href="https://etc.eso.org/fors" target="_blank"
      style="color:var(--accent);">etc.eso.org/fors</a><br>
    · Oke &amp; Gunn (1983) ApJ 266, 713<br>
    · Naylor (1998) MNRAS 296, 339
  </div>
</div>
""", unsafe_allow_html=True)