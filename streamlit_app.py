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
Telescopio fijo: VLT 8 m — para comparación directa con el ETC de ESO.
"""

import json
import math
import streamlit as st
import plotly.graph_objects as go

from backend import (
    OPTICAL_FILTERS,
    TELESCOPE_DIAMETER_M,
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

section[data-testid="stSidebar"] {{
  background: var(--sidebar) !important;
  border-right: 1px solid var(--border) !important;
}}
section[data-testid="stSidebar"] .block-container {{
  padding-top: 1rem;
}}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div {{ color: var(--text); }}
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
  color: var(--text-muted) !important;
}}
section[data-testid="stSidebar"] .stSelectbox > div > div,
section[data-testid="stSidebar"] .stNumberInput input {{
  background: var(--surface-2) !important;
  border-color: var(--border) !important;
  color: var(--text) !important;
}}

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

.stButton > button {{
  border-radius: 999px !important;
  font-weight: 600 !important;
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
.eso-info-badge {{
  display: inline-block;
  background: var(--accent-soft);
  color: var(--accent);
  border: 1px solid var(--accent);
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 0.2rem 0.7rem;
  margin-bottom: 0.4rem;
}}
@media (max-width: 900px) {{
  .topbar-title {{ font-size: 1.42rem; }}
  .result-value {{ font-size: 2.35rem; }}
}}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🔭 Configuración")
    # ── Telescopio (fijo) ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Telescopio")
    st.markdown(f"""
<div class="eso-info-badge">Diámetro 8 m - Óptico - Filtro g  </div>
<div style="color:var(--text-muted);font-size:0.85rem;margin-top:0.3rem;">
</div>
""", unsafe_allow_html=True)

    # Obstrucción fija igual que el VLT real (~14 % del diámetro)
    obstruction = 0.14

    throughput = st.slider(
        "Transmisión total del sistema",
        min_value=0.1, max_value=1.0, value=0.36, step=0.01,
        help="Transmisión combinada de óptica, espejos y filtro.",
    )

    # ── Filtro y modo (fijos: r óptico) ──────────────────────────────────────
    mode = "Optical"
    filter_name = "g"
    filt = OPTICAL_FILTERS[filter_name]
    det = detector_for_filter(filt)


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
    airmass = st.slider(
        "Masa de aire (airmass)",
        min_value=1.0, max_value=3.0, value=1.0, step=0.05,
        help="Factor de extinción atmosférica X. Zenith = 1.0.",
    )
    use_auto_ap = st.checkbox(
        "Apertura automática (r = FWHM)",
        value=True,
        help="Calibrado para coincidir con la apertura del ETC de ESO (Ω ≈ 2.41 arcsec² para seeing 0.8\").",
    )
    if use_auto_ap:
        ap_radius = default_aperture_radius(seeing)
        ap_area = math.pi * ap_radius ** 2
        st.caption(f"Radio: **{ap_radius:.2f}** arcsec · Área: **{ap_area:.2f}** arcsec²")
    else:
        ap_radius = st.slider(
            "Radio de apertura (arcsec)",
            min_value=0.3, max_value=5.0,
            value=round(default_aperture_radius(seeing), 1),
            step=0.1,
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
    )
    if calc_mode == "S/N dado el tiempo de exposición":
        exp_time = st.number_input(
            "Tiempo de exposición (s)",
            min_value=0.1, max_value=1e6, value=60.0, step=10.0,
        )
        target_snr_input = None
    else:
        target_snr_input = st.number_input(
            "S/N objetivo",
            min_value=1.0, max_value=1000.0, value=10.0, step=1.0,
        )
        exp_time = None

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
top_left, _, _ = st.columns([10, 0.4, 1.2])

with top_left:
    st.markdown(f"""
<div class="topbar">
  <div class="kicker">Herramienta académica de observación · VLT 8 m</div>
  <div class="topbar-title">Calculadora de Tiempo de Exposición</div>
                <div class="meta-line">
<strong>Modo Óptico</strong> · Filtro <strong>r</strong> ·
Telescopio <strong> 8 m</strong> · Objeto <strong>{object_mag:.1f} AB mag</strong> ·
Airmass <strong>{airmass:.2f}</strong>
</div>
</div>
              
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Ensamblado de parámetros
# ---------------------------------------------------------------------------
telescope = TelescopeParams(diameter_m=TELESCOPE_DIAMETER_M, obstruction_fraction=obstruction)
conditions = ObservingConditions(
    seeing_fwhm_arcsec=seeing,
    aperture_radius_arcsec=ap_radius,
    total_throughput=throughput,
    n_reads=n_reads,
    airmass=airmass,
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
# Tabs
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

            # Extinción aplicada
            ext_applied = filt.extinction_coeff * airmass
            mag_eff = object_mag + ext_applied

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
      <div class="info-item-value">{result.dark_signal_e:.4f} e⁻</div>
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
      <div class="info-item-label">Energía encerrada (EE)</div>
      <div class="info-item-value">{result.enclosed_energy*100:.1f} %</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">Extinción (k · X)</div>
      <div class="info-item-value">{ext_applied:.3f} mag</div>
    </div>
    <div class="info-item">
      <div class="info-item-label">Mag. efectiva (extinguida)</div>
      <div class="info-item-value">{mag_eff:.2f} AB</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Área colectora",    f"{telescope.collecting_area_m2:.3f} m²")
            m2.metric("Eficiencia cuántica", f"{det.quantum_efficiency*100:.0f} %")
            m3.metric("Ruido de lectura",  f"{det.read_noise_e} e⁻/pix")
            m4.metric("Corriente oscura",  f"{det.dark_current_e_s:.6f} e⁻/s/pix")

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
  <div class="section-kicker">Instrumento · ESO FORS2 / HAWK-I</div>
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
        <tr><td>Extinción k_λ</td><td>{filt.extinction_coeff:.2f} mag/airmass</td></tr>
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
  <div class="section-kicker">Calibración del modelo</div>
  <h3 style="margin-top:0;">Mejoras vs. modelo simple</h3>
  <div class="note-list">
    ✓ PSF de Moffat (β = 2.5) — como el ETC de ESO<br>
    ✓ Extinción atmosférica por banda (k_λ · X)<br>
    ✓ RON y dark calibrados con FORS2 / HAWK-I<br>
    ✓ λ_eff y Δλ de filtros ESO reales<br>
    ✓ Escala de píxel FORS2 (0.252") / HAWK-I (0.106")<br>
    ✗ Sin QE(λ) espectral detallada<br>
    ✗ Sin emisión térmica del telescopio (NIR Ks)
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CURVAS S/N
# ══════════════════════════════════════════════════════════════════════════════
with tab_curves:
    t_start = 1.0
    t_end   = 100_000.0

    tab_snr_t, tab_snr_mag = st.tabs(["S/N vs. tiempo", "S/N vs. magnitud"])

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
                text=f"Filtro {filt.name} · {object_mag:.1f} AB mag · VLT 8 m · Airmass {airmass:.2f}",
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
        
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_snr_mag:
        t_ref_mag = (
            (result.time_for_target_snr or result.exposure_time_s)
            if result else (exp_time or 60.0)
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
                text=f"S/N vs. magnitud · t = {format_time(t_ref_mag)} · VLT 8 m",
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
            
            st.plotly_chart(fig_pie, use_container_width=True,
                            config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

        with col_tbl:
            regime_descriptions = {
                "sky-limited":        "El fondo de cielo domina. Apertura más pequeña o cielo más oscuro ayudan.",
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
        <tr><td>Dark current</td><td>{result.dark_signal_e:.4f}</td><td>{budget['dark']:.3f}%</td></tr>
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
# ══════════════════════════════════════════════════════════════════════════════
# TAB — VALIDACIÓN ESO
# ══════════════════════════════════════════════════════════════════════════════
with tab_validation:
    st.markdown("## Validación contra ETC de ESO")

    st.markdown("""
<div class="html-card">
  <div class="section-kicker">Flujo de trabajo</div>
  <h3 style="margin-top:0;">Cómo usar esta pestaña</h3>
  <div class="note-list">
    <strong>Paso 1 —</strong> Abre el
    <a href="https://etc.eso.org/observing/etc/fors" target="_blank" style="color:var(--accent);">
    ETC de ESO (FORS2)</a>, configura tu observación y ejecuta el cálculo.<br><br>
    <strong>Paso 2 —</strong> Pega el <strong>JSON de input</strong> que usaste en el ETC
    (para que la app lea automáticamente magnitud, tiempo, airmass y seeing).<br><br>
    <strong>Paso 3 —</strong> Copia los valores del <strong>cuadro de resultados</strong>
    que muestra el ETC (Starget, Ssky, S/N, Npix, EE…) en los campos numéricos de abajo.<br><br>
    <strong>Paso 4 —</strong> Haz clic en <strong>🔬 Comparar</strong>.
  </div>
</div>
""", unsafe_allow_html=True)



    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN A — JSON de INPUT (para leer parámetros automáticamente)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 1 · JSON de input del ETC de ESO")
    st.caption("Pega el JSON de configuración que usaste en el ETC. La app leerá magnitud, tiempo, airmass y seeing automáticamente.")

    default_input_json = """{
  "target": {
    "morphology": {"morphologytype": "point"},
    "sed": {
      "sedtype": "spectrum",
      "spectrum": {"spectrumtype": "template", "params": {"catalog": "MARCS", "id": "5750:4.5"}},
      "extinctionav": 0
    },
    "brightness": {"brightnesstype": "mag", "magband": "V", "mag": 20, "magsys": "AB"}
  },
  "sky": {"airmass": 1, "fli": 0, "waterVapour": 30, "moonDistance": 90},
  "seeing": {"turbulence_category": 50, "aperturepix": 0},
  "instrument": {
    "DET.READ.CLKIND": "200kHz,2x2,low",
    "INS.FILT1.NAME": "GG435+81",
    "SEQ.CCD": "R",
    "INS.COLL.NAID": "COLL_HR+7",
    "ins_configuration": "img_nopol"
  },
  "timesnr": {"DET.WIN1.UIT1": 60, "snr": 18},
  "output": {"psf": {"psf": false}},
  "instrumentName": "fors"
}"""

    input_json_str = st.text_area(
        "JSON de input",
        value=default_input_json,
        height=220,
        label_visibility="collapsed",
    )

    # Parsear input JSON y extraer parámetros
    _mag_in, _texp_in, _air_in, _see_in = object_mag, float(exp_time or 60.0), airmass, seeing
    _input_ok = False
    try:
        _jin = json.loads(input_json_str)
        _mag_in  = float(_jin.get("target", {}).get("brightness", {}).get("mag", object_mag))
        _texp_in = float(_jin.get("timesnr", {}).get("DET.WIN1.UIT1", exp_time or 60.0))
        _air_in  = float(_jin.get("sky", {}).get("airmass", airmass))
        _turb    = int(_jin.get("seeing", {}).get("turbulence_category", 50))
        _seeing_map = {20: 0.5, 30: 0.65, 50: 0.8, 70: 1.0, 85: 1.4}
        _see_in  = _seeing_map.get(_turb, 0.8)
        _input_ok = True
        st.success(
            f"✅ JSON leído — mag = **{_mag_in}** AB · "
            f"t = **{_texp_in:.0f} s** · airmass = **{_air_in}** · "
            f"seeing ≈ **{_see_in}\"** (cat. {_turb})"
        )
    except Exception as _e:
        st.warning(f"JSON de input no válido ({_e}). Se usarán los valores del sidebar.")

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN B — OUTPUT del ETC de ESO (campos manuales)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 2 · Resultados del ETC de ESO")
    st.caption(
        "Copia los valores que muestra el ETC de ESO en su cuadro de resultados. "
        "Deja en 0 los campos que no aparezcan."
    )

    # Fila 1: señales principales
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        eso_snr    = st.number_input("S/N",             min_value=0.0, value=308.0,   step=1.0,    format="%.1f")
    with col2:
        eso_signal = st.number_input("Starget [e⁻]",    min_value=0.0, value=123000.0, step=100.0,  format="%.0f")
    with col3:
        eso_sky    = st.number_input("Ssky [e⁻]",       min_value=0.0, value=36000.0,  step=100.0,  format="%.0f")
    with col4:
        eso_npix   = st.number_input("Npix",            min_value=0.0, value=38.0,    step=1.0,    format="%.0f")
    with col5:
        eso_ee     = st.number_input("EE (fracción)",   min_value=0.0, max_value=1.0, value=0.987, step=0.001,  format="%.3f")

    # Fila 2: detector
    col6, col7, col8, col9, col10 = st.columns(5)
    with col6:
        eso_ron    = st.number_input("RON [e⁻/pix]",   min_value=0.0, value=3.15,    step=0.01,   format="%.2f")
    with col7:
        eso_dark   = st.number_input("Dark [e⁻/s/pix]",min_value=0.0, value=0.000583,step=0.0001, format="%.6f")
    with col8:
        eso_omega  = st.number_input("Apertura Ω [arcsec²]", min_value=0.0, value=2.41, step=0.01, format="%.2f")
    with col9:
        eso_sky_pix= st.number_input("Sky max [e⁻/pix]",min_value=0.0,value=946.0,  step=1.0,    format="%.0f")
    with col10:
        eso_tgt_pix= st.number_input("Target max [e⁻/pix]",min_value=0.0,value=10500.0,step=100.0,format="%.0f")

    st.markdown("<br>", unsafe_allow_html=True)
    comparar = st.button("🔬 Comparar con nuestra CTE", type="primary")

    # ══════════════════════════════════════════════════════════════════════════
    # PROCESAMIENTO Y COMPARACIÓN
    # ══════════════════════════════════════════════════════════════════════════
    if comparar:
        try:
            # Recalcular CTE con los parámetros extraídos del input JSON
            _ap_r = math.sqrt(eso_omega / math.pi) if eso_omega > 0 else default_aperture_radius(_see_in)
            _cond = ObservingConditions(
                seeing_fwhm_arcsec=_see_in,
                aperture_radius_arcsec=_ap_r,
                total_throughput=throughput,
                n_reads=int(n_reads),
                airmass=_air_in,
            )
            _tel = TelescopeParams(diameter_m=TELESCOPE_DIAMETER_M, obstruction_fraction=obstruction)
            _r   = compute_snr(float(_mag_in), float(_texp_in), _tel, filt, det, _cond, src)

            # Helpers
            def _pct(ours, eso_val):
                if eso_val and eso_val != 0:
                    return 100.0 * (ours - eso_val) / eso_val
                return None

            def _fmt_pct(p):
                if p is None: return "—"
                return f"{'+'if p>=0 else ''}{p:.1f} %"

            def _td_color(p):
                if p is None: return ""
                if abs(p) < 10:  return "color:#86efac"
                if abs(p) < 25:  return "color:#fcd34d"
                return "color:#f9a8d4"

            # Tabla de comparación
            comparisons = [
                ("S/N",                  f"{_r.snr:.1f}",                    f"{eso_snr:.1f}",     _pct(_r.snr,             eso_snr   if eso_snr   > 0 else None)),
                ("Señal objeto [e⁻]",    f"{_r.signal_e:,.0f}",              f"{eso_signal:,.0f}", _pct(_r.signal_e,        eso_signal if eso_signal > 0 else None)),
                ("Señal cielo [e⁻]",     f"{_r.sky_signal_e:,.0f}",          f"{eso_sky:,.0f}",    _pct(_r.sky_signal_e,    eso_sky    if eso_sky    > 0 else None)),
                ("Píxeles en apertura",  f"{_r.n_pixels:.1f}",               f"{eso_npix:.0f}",    _pct(_r.n_pixels,        eso_npix   if eso_npix   > 0 else None)),
                ("Energía encerrada (EE)",f"{_r.enclosed_energy:.3f}",       f"{eso_ee:.3f}",      _pct(_r.enclosed_energy, eso_ee     if eso_ee     > 0 else None)),
            ]

            rows_html = ""
            for label, ours_str, eso_str, p in comparisons:
                rows_html += f"""
      <tr>
        <td>{label}</td>
        <td style="font-family:monospace;">{ours_str}</td>
        <td style="font-family:monospace;">{eso_str}</td>
        <td style="font-family:monospace;font-weight:600;{_td_color(p)}">{_fmt_pct(p)}</td>
      </tr>"""

            st.markdown(f"""
<div class="html-card">
  <div class="section-kicker">
    Filtro {filter_name} · VLT 8 m · {_mag_in} AB · {_texp_in:.0f} s · airmass {_air_in} · seeing {_see_in:.2f}" · Ω = {eso_omega:.2f} arcsec²
  </div>
  <h3 style="margin-top:0;">Tabla de comparación</h3>
  <div class="table-clean">
    <table>
      <thead>
        <tr>
          <th>Cantidad</th>
          <th>Nuestra CTE</th>
          <th>ETC de ESO</th>
          <th>Diferencia relativa</th>
        </tr>
      </thead>
      <tbody>{rows_html}
      </tbody>
    </table>
  </div>
  <div class="note-list" style="margin-top:0.65rem;">
    <span style="color:#86efac;">■</span> &lt; 10 % &nbsp;&nbsp;
    <span style="color:#fcd34d;">■</span> 10–25 % &nbsp;&nbsp;
    <span style="color:#f9a8d4;">■</span> &gt; 25 %
  </div>
</div>
""", unsafe_allow_html=True)

            # Métricas detalladas del detector (comparación directa)
            st.markdown("#### Parámetros del detector")
            dc1, dc2, dc3, dc4 = st.columns(4)
            dc1.metric("RON — ESO",        f"{eso_ron:.2f} e⁻/pix",      delta=f"{det.read_noise_e - eso_ron:+.2f} (CTE)")
            dc2.metric("Dark — ESO",        f"{eso_dark:.6f} e⁻/s/pix",  delta=f"{det.dark_current_e_s - eso_dark:+.6f} (CTE)")
            dc3.metric("Sky max — ESO",     f"{eso_sky_pix:.0f} e⁻/pix", delta=f"{_r.sky_max_e_pix - eso_sky_pix:+.0f} (CTE)")
            dc4.metric("Target max — ESO",  f"{eso_tgt_pix:.0f} e⁻/pix", delta=f"{_r.source_max_e_pix - eso_tgt_pix:+.0f} (CTE)")

        except Exception as exc:
            st.error(f"Error al calcular: {exc}")

    # ── Explicación de discrepancias ─────────────────────────────────────────
    st.markdown("---")
    st.markdown("""
<div class="html-card">
  <div class="section-kicker">Origen de las diferencias</div>
  <h3 style="margin-top:0;">¿Por qué no coinciden exactamente?</h3>
  <div class="table-clean">
    <table>
      <thead>
        <tr><th>Factor</th><th>ETC de ESO</th><th>Nuestra CTE</th><th>Impacto típico</th></tr>
      </thead>
      <tbody>
        <tr><td>Espectro de cielo</td><td>Noll et al. 2012 (líneas OH, O₂, Na…)</td><td>Brillo AB plano por banda</td><td>10–40 %</td></tr>
        <tr><td>SED del objeto</td><td>Plantilla estelar (MARCS, Pickles…)</td><td>Fuente plana en F_ν (AB)</td><td>5–15 %</td></tr>
        <tr><td>Throughput</td><td>Curvas reales T(λ) · QE(λ)</td><td>Valor constante por banda</td><td>5–10 %</td></tr>
        <tr><td>Extinción</td><td>k(λ) espectral completo</td><td>k_λ promedio por banda</td><td>2–8 %</td></tr>
        <tr><td>PSF / EE</td><td>Perfil Moffat calibrado con datos VLT</td><td>Moffat β = 2.5 analítico</td><td>3–10 %</td></tr>
      </tbody>
    </table>
  </div>
  <div class="note-list" style="margin-top:0.75rem;">
    Una diferencia de ≤ 15 % en S/N es aceptable para un modelo analítico simplificado.
    La discrepancia dominante suele ser el espectro de cielo de Paranal.
  </div>
</div>
""", unsafe_allow_html=True)

with tab_model:
    col_m1, col_m2 = st.columns([1.1, 1])

    with col_m1:
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

        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"""
\frac{S}{N} =
\frac{S}{
\sqrt{S + N_\mathrm{sky} + N_\mathrm{dark}
+ \sigma_\mathrm{RON}^{2}\, n_\mathrm{pix}\, n_\mathrm{reads}
}}
""")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Cadena de conversión fotométrica</div>
  <h3 style="margin-top:0;">Magnitud AB → señal [e⁻]</h3>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"m_\mathrm{ext} = m_\mathrm{AB} + k_\lambda \cdot X \quad \text{(extinción)}")
        st.latex(r"F_\nu = F_0^\mathrm{AB} \cdot 10^{-m_\mathrm{ext}/2.5} \quad [W\,m^{-2}\,Hz^{-1}]")
        st.latex(r"\Phi = \frac{F_\nu \cdot c \cdot \Delta\lambda}{\lambda_\mathrm{eff}^2} \cdot \frac{\lambda_\mathrm{eff}}{hc} \quad [\mathrm{ph\,s^{-1}\,m^{-2}}]")
        st.latex(r"S = \Phi \cdot A_\mathrm{eff} \cdot \eta_\mathrm{total} \cdot \mathrm{EE}(r_\mathrm{ap}) \cdot t \quad [e^-]")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Telescopio VLT</div>
  <h3 style="margin-top:0;">Área efectiva de recolección</h3>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"A_\mathrm{eff} = \frac{\pi D^2}{4}(1-\epsilon^2) \quad D=8\,\mathrm{m},\;\epsilon=0.14")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_m2:
        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Energía encerrada · PSF de Moffat</div>
  <h3 style="margin-top:0;">Perfil de Moffat (β = 2.5)</h3>
  <div class="note-list">
    El ETC de ESO usa un perfil de Moffat (β = 2.5) que reproduce mejor
    las alas extendidas de la PSF atmosférica real, a diferencia de la
    gaussiana que subestima la EE en aperturas grandes.
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"I(r) \propto \left[1 + \left(\frac{r}{\alpha}\right)^2\right]^{-\beta}")
        st.latex(r"\mathrm{EE}(r) = 1 - \left[1 + \left(\frac{r}{\alpha}\right)^2\right]^{1-\beta}")
        st.latex(r"\alpha = \frac{\mathrm{FWHM}}{2\sqrt{2^{1/\beta}-1}}, \quad \beta=2.5")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Extinción atmosférica</div>
  <h3 style="margin-top:0;">Ley de Bouguer-Beer</h3>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"m_\mathrm{ext} = m_0 + k_\lambda \cdot X")
        st.latex(r"k_g=0.17,\; k_r=0.07,\; k_i=0.03 \quad [\mathrm{mag/airmass}]")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Calibración vs. ESO ETC</div>
  <h3 style="margin-top:0;">Parámetros ajustados</h3>
  <div class="table-clean">
    <table>
      <thead><tr><th>Parámetro</th><th>Nuestro modelo</th><th>ESO ETC</th></tr></thead>
      <tbody>
        <tr><td>PSF</td><td>Moffat β=2.5</td><td>Moffat β=2.5</td></tr>
        <tr><td>Extinción</td><td>k_λ · X</td><td>k_λ · X</td></tr>
        <tr><td>RON FORS2</td><td>3.15 e⁻</td><td>3.15 e⁻</td></tr>
        <tr><td>Dark FORS2</td><td>5.83×10⁻⁴ e⁻/s</td><td>5.83×10⁻⁴ e⁻/s</td></tr>
        <tr><td>Pix. FORS2</td><td>0.252 "/pix</td><td>0.252 "/pix</td></tr>
        <tr><td>RON HAWK-I</td><td>5 e⁻</td><td>5 e⁻</td></tr>
      </tbody>
    </table>
  </div>
</div>
""", unsafe_allow_html=True)

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
    · Trujillo et al. (2001) MNRAS 328, 977 (perfil de Moffat)
  </div>
</div>
""", unsafe_allow_html=True)