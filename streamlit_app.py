"""
frontend.py — Calculadora de Tiempo de Exposición (CTE) — Interfaz Streamlit
=============================================================================
Ejecutar con:   streamlit run frontend.py

Modelo simplificado según enunciado:
  - Telescopio 8 m, filtro g óptico (fijos)
  - PSF gaussiana, sin extinción, T=0.80, pixel=0.20"/pix
"""

import json
import math
import streamlit as st
import plotly.graph_objects as go

from backend import (
    OPTICAL_FILTERS,
    TELESCOPE_DIAMETER_M,
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
# Configuración de página
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Calculadora de Tiempo de Exposición",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# Tema
# ──────────────────────────────────────────────────────────────────────────────
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "dark"

def toggle_theme():
    st.session_state["theme_mode"] = (
        "light" if st.session_state["theme_mode"] == "dark" else "dark"
    )

theme = st.session_state["theme_mode"]

THEMES = {
    "light": {
        "bg":"#f3f6fb","bg_soft":"#edf2f8","surface":"#ffffff","surface_2":"#f8fafc",
        "sidebar":"#eef3f9","border":"#d9e1ec","border_strong":"#c7d2df",
        "text":"#18212b","text_muted":"#607080","text_soft":"#7c8897",
        "accent":"#1d4ed8","accent_alt":"#0f766e","accent_soft":"rgba(37,99,235,0.10)",
        "shadow":"0 12px 28px rgba(15,23,42,0.08)",
        "topbar_bg":"rgba(255,255,255,0.78)","topbar_border":"rgba(203,213,225,0.95)",
        "metric_bg":"#f8fafc","metric_border":"#dbe4ef",
        "plot_bg":"#ffffff","plot_paper":"#ffffff","plot_grid":"#e5e7eb",
        "plot_axis":"#1f2937","plot_line":"#2563eb","plot_line2":"#0f766e",
        "plot_point":"#be185d","plot_target":"#d97706",
        "sky_bg":"rgba(13,148,136,0.10)","sky_text":"#0f766e","sky_border":"rgba(13,148,136,0.34)",
        "read_bg":"rgba(79,70,229,0.10)","read_text":"#4338ca","read_border":"rgba(79,70,229,0.34)",
        "shot_bg":"rgba(22,163,74,0.10)","shot_text":"#15803d","shot_border":"rgba(22,163,74,0.34)",
        "dark_bg":"rgba(180,83,9,0.10)","dark_text":"#b45309","dark_border":"rgba(180,83,9,0.34)",
    },
    "dark": {
        "bg":"#07101d","bg_soft":"#0b1627","surface":"#0d1728","surface_2":"#101c31",
        "sidebar":"#08111f","border":"#22324a","border_strong":"#334155",
        "text":"#e5e7eb","text_muted":"#b3bfcb","text_soft":"#7f8a99",
        "accent":"#60a5fa","accent_alt":"#2dd4bf","accent_soft":"rgba(96,165,250,0.12)",
        "shadow":"0 16px 36px rgba(0,0,0,0.30)",
        "topbar_bg":"rgba(7,16,29,0.74)","topbar_border":"rgba(51,65,85,0.82)",
        "metric_bg":"#101c31","metric_border":"#22324a",
        "plot_bg":"#0d1728","plot_paper":"#0d1728","plot_grid":"#23344c",
        "plot_axis":"#e5e7eb","plot_line":"#60a5fa","plot_line2":"#2dd4bf",
        "plot_point":"#f9a8d4","plot_target":"#fbbf24",
        "sky_bg":"rgba(34,211,238,0.10)","sky_text":"#67e8f9","sky_border":"rgba(34,211,238,0.28)",
        "read_bg":"rgba(165,180,252,0.10)","read_text":"#c7d2fe","read_border":"rgba(165,180,252,0.28)",
        "shot_bg":"rgba(134,239,172,0.10)","shot_text":"#86efac","shot_border":"rgba(134,239,172,0.28)",
        "dark_bg":"rgba(251,191,36,0.10)","dark_text":"#fcd34d","dark_border":"rgba(251,191,36,0.28)",
    },
}
T = THEMES[theme]

# ──────────────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Source+Serif+4:wght@400;600;700&display=swap');
:root {{
  --bg:{T["bg"]};--bg-soft:{T["bg_soft"]};--surface:{T["surface"]};--surface-2:{T["surface_2"]};
  --sidebar:{T["sidebar"]};--border:{T["border"]};--border-strong:{T["border_strong"]};
  --text:{T["text"]};--text-muted:{T["text_muted"]};--text-soft:{T["text_soft"]};
  --accent:{T["accent"]};--accent-alt:{T["accent_alt"]};--accent-soft:{T["accent_soft"]};
  --shadow:{T["shadow"]};--topbar-bg:{T["topbar_bg"]};--topbar-border:{T["topbar_border"]};
  --metric-bg:{T["metric_bg"]};--metric-border:{T["metric_border"]};
  --sky-bg:{T["sky_bg"]};--sky-text:{T["sky_text"]};--sky-border:{T["sky_border"]};
  --read-bg:{T["read_bg"]};--read-text:{T["read_text"]};--read-border:{T["read_border"]};
  --shot-bg:{T["shot_bg"]};--shot-text:{T["shot_text"]};--shot-border:{T["shot_border"]};
  --dark-bg:{T["dark_bg"]};--dark-text:{T["dark_text"]};--dark-border:{T["dark_border"]};
}}
html,body,[class*="css"]{{font-family:'Inter',sans-serif;}}
body{{color:var(--text);}}
.stApp{{background:radial-gradient(circle at top left,rgba(59,130,246,0.08),transparent 25%),linear-gradient(180deg,var(--bg) 0%,var(--bg-soft) 100%);color:var(--text);}}
section[data-testid="stSidebar"]{{background:var(--sidebar)!important;border-right:1px solid var(--border)!important;}}
section[data-testid="stSidebar"] label,section[data-testid="stSidebar"] p,section[data-testid="stSidebar"] span,section[data-testid="stSidebar"] div{{color:var(--text);}}
section[data-testid="stSidebar"] .stCaption,[data-testid="stCaptionContainer"]{{color:var(--text-muted)!important;}}
h1,h2,h3{{font-family:'Source Serif 4',serif!important;color:var(--text);letter-spacing:-0.02em;}}
h2{{font-size:1.3rem;line-height:1.12;}}h3{{font-size:1.04rem;}}
p,li,div,span,label{{color:var(--text);}}
small,.stCaption,[data-testid="stCaptionContainer"]{{color:var(--text-muted)!important;}}
[data-testid="metric-container"]{{background:var(--metric-bg);border:1px solid var(--metric-border);border-radius:16px;padding:14px 16px;}}
[data-testid="metric-container"] label{{color:var(--text-soft)!important;font-size:0.78rem!important;text-transform:uppercase;letter-spacing:0.06em;}}
.stTabs [data-baseweb="tab-list"]{{background:var(--surface-2)!important;border-radius:12px!important;padding:4px!important;border:1px solid var(--border)!important;gap:2px!important;}}
.stTabs [data-baseweb="tab"]{{border-radius:9px!important;color:var(--text-muted)!important;font-size:0.84rem!important;font-weight:500!important;padding:0.38rem 0.9rem!important;}}
.stTabs [aria-selected="true"]{{background:var(--accent-soft)!important;color:var(--accent)!important;}}
.stTabs [data-baseweb="tab-panel"]{{padding-top:1rem!important;}}
.stButton>button{{border-radius:999px!important;font-weight:600!important;}}
.topbar{{position:sticky;top:0;z-index:10;backdrop-filter:blur(14px);background:var(--topbar-bg);border:1px solid var(--topbar-border);border-radius:18px;padding:0.95rem 1.1rem;margin-bottom:1rem;box-shadow:var(--shadow);}}
.kicker{{color:var(--accent);font-size:0.76rem;font-weight:700;letter-spacing:0.10em;text-transform:uppercase;margin-bottom:0.16rem;}}
.topbar-title{{font-family:'Source Serif 4',serif;color:var(--text);font-size:1.72rem;font-weight:700;line-height:1.02;}}
.topbar-subtitle{{color:var(--text-muted);font-size:0.92rem;margin-top:0.22rem;}}
.meta-line{{color:var(--text-muted);font-size:0.94rem;margin-bottom:1rem;}}
.result-card{{background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:1.25rem;box-shadow:var(--shadow);margin-bottom:1rem;}}
.plot-shell{{background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:1rem;box-shadow:var(--shadow);}}
.section-kicker{{color:var(--accent);font-size:0.75rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.2rem;}}
.result-label{{color:var(--text-soft);font-size:0.76rem;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;}}
.result-value{{font-family:'Source Serif 4',serif;color:var(--accent);font-size:3rem;font-weight:700;line-height:1.0;margin-top:0.3rem;}}
.result-subtitle{{color:var(--text-muted);font-size:0.94rem;margin-top:0.35rem;}}
.regime-badge{{display:inline-flex;align-items:center;padding:0.28rem 0.78rem;border-radius:999px;font-size:0.72rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;border:1px solid transparent;margin-top:0.85rem;}}
.sky-limited{{background:var(--sky-bg);color:var(--sky-text);border-color:var(--sky-border);}}
.read-noise-limited{{background:var(--read-bg);color:var(--read-text);border-color:var(--read-border);}}
.shot-noise-limited{{background:var(--shot-bg);color:var(--shot-text);border-color:var(--shot-border);}}
.dark-limited{{background:var(--dark-bg);color:var(--dark-text);border-color:var(--dark-border);}}
.info-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:0.8rem 1rem;margin-top:1rem;padding-top:1rem;border-top:1px solid var(--border);}}
.info-item{{display:flex;flex-direction:column;gap:0.12rem;}}
.info-item-label{{color:var(--text-soft);font-size:0.76rem;text-transform:uppercase;letter-spacing:0.05em;}}
.info-item-value{{color:var(--text);font-size:0.9rem;font-weight:600;}}
.html-card{{background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:1rem;box-shadow:var(--shadow);margin-bottom:1rem;}}
.table-clean table{{width:100%;border-collapse:collapse;font-size:0.88rem;}}
.table-clean th,.table-clean td{{text-align:left;padding:0.48rem 0.25rem;border-bottom:1px solid var(--border);}}
.table-clean th{{color:var(--text-soft);font-weight:600;}}
.eq-wrap{{background:var(--surface-2);border:1px solid var(--border);border-radius:14px;padding:0.85rem 0.85rem 0.6rem 0.85rem;margin:0.65rem 0 1rem 0;}}
.note-list{{color:var(--text-muted);font-size:0.92rem;line-height:1.65;margin-top:0.75rem;}}
.limit-box{{border:1px solid rgba(251,191,36,0.35);background:rgba(251,191,36,0.07);border-radius:14px;padding:0.85rem 1rem;margin:0.5rem 0 0.8rem 0;}}
.limit-title{{font-weight:700;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.07em;color:{T["dark_text"]};margin-bottom:0.3rem;}}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Parámetros fijos del modelo (enunciado)
# ──────────────────────────────────────────────────────────────────────────────
FILTER_NAME  = "g"
filt = OPTICAL_FILTERS[FILTER_NAME]
det  = detector_for_filter(filt)
obstruction  = 0.14

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔭 Configuración")
    st.caption("Telescopio 8 m · Filtro g óptico · Modelo simplificado")

    st.markdown("---")
    st.markdown("### Telescopio y filtro")
    st.markdown(f"""
<div style="background:var(--accent-soft);border:1px solid var(--accent);border-radius:10px;
     padding:0.6rem 0.8rem;font-size:0.85rem;color:var(--accent);margin-bottom:0.5rem;">
   D = 8 m · Filtro <strong>g</strong> · T = 0.80 · s_pix = 0.20"/pix
</div>
""", unsafe_allow_html=True)

    throughput = st.slider(
        "Transmisión total T (enunciado: 0.80)",
        min_value=0.10, max_value=1.0, value=0.80, step=0.01,
        help="Según el enunciado T=0.80 es el valor por defecto.",
    )

    st.markdown("---")
    st.markdown("### Fuente")
    source_type = st.radio("Tipo de fuente", ["Fuente puntual", "Extendida"], horizontal=True)
    src = "point" if source_type == "Fuente puntual" else "extended"
    object_mag = st.number_input(
        "Magnitud del objeto (AB mag)",
        min_value=0.0, max_value=35.0, value=20.0, step=0.5,
    )

    st.markdown("---")
    st.markdown("### Condiciones de observación")
    seeing = st.slider("Seeing FWHM (arcsec)", min_value=0.3, max_value=3.0, value=0.80, step=0.05)
    airmass = st.slider("Masa de aire", min_value=1.0, max_value=3.0, value=1.0, step=0.05,
                        help="Conservado como parámetro. Sin efecto en S/N (sin extinción).")
    use_auto_ap = st.checkbox("Apertura automática (r = FWHM)", value=True)
    if use_auto_ap:
        ap_radius = default_aperture_radius(seeing)
        st.caption(f"Radio: **{ap_radius:.2f}\"** · Área: **{math.pi*ap_radius**2:.2f} arcsec²**")
    else:
        ap_radius = st.slider("Radio de apertura (arcsec)", 0.3, 5.0,
                              round(default_aperture_radius(seeing), 1), 0.1)
    n_reads = st.number_input("Lecturas del detector", min_value=1, max_value=50, value=1)

    st.markdown("---")
    st.markdown("### Modo de cálculo")
    calc_mode = st.radio("Resolver para …",
        ["S/N dado el tiempo de exposición", "Tiempo de exposición dado el S/N"])
    if calc_mode == "S/N dado el tiempo de exposición":
        exp_time = st.number_input("Tiempo de exposición (s)",
                                   min_value=0.1, max_value=1e6, value=60.0, step=10.0)
        target_snr_input = None
    else:
        target_snr_input = st.number_input("S/N objetivo",
                                           min_value=1.0, max_value=1000.0, value=10.0, step=1.0)
        exp_time = None

    st.markdown("---")
    st.button("🌙 Modo oscuro" if theme == "light" else "☀️ Modo claro",
              on_click=toggle_theme, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# Topbar
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="topbar">
  <div class="kicker">Herramienta académica · Modelo simplificado según enunciado</div>
  <div class="topbar-title">Calculadora de Tiempo de Exposición</div>
  <div class="topbar-subtitle">
    Telescopio <strong>8 m</strong> · Filtro <strong>g</strong> óptico ·
    PSF gaussiana · Sin extinción atmosférica · T = {throughput:.2f} · s_pix = 0.20"/pix
  </div>
</div>
<div class="meta-line">
  Objeto <strong>{object_mag:.1f} AB mag</strong> · Seeing <strong>{seeing:.2f}"</strong> ·
  Airmass <strong>{airmass:.2f}</strong>
  <span style="color:var(--text-soft);font-size:0.82rem;"> (sin efecto — extinción no modelada)</span>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Parámetros y cálculo
# ──────────────────────────────────────────────────────────────────────────────
telescope  = TelescopeParams(diameter_m=TELESCOPE_DIAMETER_M, obstruction_fraction=obstruction)
conditions = ObservingConditions(
    seeing_fwhm_arcsec=seeing,
    aperture_radius_arcsec=ap_radius,
    total_throughput=throughput,
    n_reads=int(n_reads),
    airmass=airmass,
)

error_msg, result = None, None
try:
    if calc_mode == "S/N dado el tiempo de exposición":
        result = compute_snr(object_mag, exp_time, telescope, filt, det, conditions, src)
    else:
        result = compute_exposure_time(object_mag, target_snr_input, telescope, filt, det, conditions, src)
except ValueError as exc:
    error_msg = str(exc)

# ──────────────────────────────────────────────────────────────────────────────
# Ticks log
# ──────────────────────────────────────────────────────────────────────────────
def build_log_ticks(tmin, tmax):
    exps = range(int(math.floor(math.log10(tmin))), int(math.ceil(math.log10(tmax)))+1)
    ticks, labels = [], []
    for e in exps:
        v = 10**e
        if tmin <= v <= tmax:
            ticks.append(v)
            labels.append(f"{int(v)} s" if v < 60 else (f"{int(v/60)} min" if v < 3600 else f"{int(v/3600)} h"))
    return ticks, labels

# ──────────────────────────────────────────────────────────────────────────────
# Tabs
# ──────────────────────────────────────────────────────────────────────────────
tab_results, tab_curves, tab_budget, tab_validation, tab_model = st.tabs([
    "📊 Resultados", "📈 Curvas S/N", "🎛️ Presupuesto de ruido",
    "🔬 Validación ESO", "📐 Modelo físico",
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
            rc = result.noise_regime.replace(" ","-").replace("/","-")

            if calc_mode == "S/N dado el tiempo de exposición":
                plabel = "Relación señal-ruido"
                pvalue = f"{result.snr:.2f}"
                psub   = f"Tiempo de exposición: {format_time(result.exposure_time_s)}"
            else:
                plabel = "Tiempo de exposición requerido"
                pvalue = format_time(result.time_for_target_snr)
                psub   = f"S/N alcanzado = {result.snr:.2f}  (objetivo: {result.target_snr:.1f})"

            st.markdown(f"""
<div class="result-card">
  <div class="section-kicker">Resultado principal</div>
  <div class="result-label">{plabel}</div>
  <div class="result-value">{pvalue}</div>
  <div class="result-subtitle">{psub}</div>
  <span class="regime-badge {rc}">{result.noise_regime}</span>
  <div class="info-grid">
    <div class="info-item"><div class="info-item-label">Señal objeto</div>
      <div class="info-item-value">{result.signal_e:.1f} e⁻</div></div>
    <div class="info-item"><div class="info-item-label">Señal cielo</div>
      <div class="info-item-value">{result.sky_signal_e:.1f} e⁻</div></div>
    <div class="info-item"><div class="info-item-label">Corriente oscura</div>
      <div class="info-item-value">{result.dark_signal_e:.4f} e⁻</div></div>
    <div class="info-item"><div class="info-item-label">RON² × n_pix × n_reads</div>
      <div class="info-item-value">{result.read_noise_total_e2:.1f} e⁻²</div></div>
    <div class="info-item"><div class="info-item-label">Píxeles apertura</div>
      <div class="info-item-value">{result.n_pixels:.1f} pix</div></div>
    <div class="info-item"><div class="info-item-label">Energía encerrada (EE)</div>
      <div class="info-item-value">{result.enclosed_energy*100:.1f} %</div></div>
    <div class="info-item"><div class="info-item-label">Régimen</div>
      <div class="info-item-value">{result.noise_regime}</div></div>
    <div class="info-item"><div class="info-item-label">Ruido total RMS</div>
      <div class="info-item-value">{result.total_noise_e:.1f} e⁻</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

            # Alerta de régimen
            REGIME_INFO = {
                "sky-limited":       (T["sky_bg"],  T["sky_border"],  T["sky_text"],  "🔵",
                    "S/N ∝ √t — domina el fondo de cielo. Duplicar t mejora S/N un factor √2 ≈ 1.41."),
                "read-noise-limited":(T["read_bg"], T["read_border"], T["read_text"], "🟣",
                    "S/N ∝ t — domina el ruido de lectura. Exposiciones más largas mejoran el S/N linealmente."),
                "shot-noise-limited":(T["shot_bg"], T["shot_border"], T["shot_text"], "🟢",
                    "S/N ∝ √t — domina el shot noise del objeto. Régimen óptimo de operación."),
                "dark-limited":      (T["dark_bg"], T["dark_border"], T["dark_text"], "🟠",
                    "S/N ∝ √t — domina la corriente oscura. Poco frecuente con FORS2 (dark muy bajo)."),
            }
            if result.noise_regime in REGIME_INFO:
                bg, bd, tc, ic, msg = REGIME_INFO[result.noise_regime]
                st.markdown(f"""
<div style="background:{bg};border:1px solid {bd};border-radius:14px;padding:0.85rem 1rem;margin-bottom:0.8rem;">
  <div style="font-weight:700;color:{tc};font-size:0.83rem;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:0.25rem;">
    {ic} {result.noise_regime}
  </div>
  <div style="color:{T['text']};font-size:0.9rem;line-height:1.55;">{msg}</div>
</div>
""", unsafe_allow_html=True)

            # Métricas detector
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Área colectora",      f"{telescope.collecting_area_m2:.3f} m²")
            m2.metric("Eficiencia cuántica", f"{det.quantum_efficiency*100:.0f} %")
            m3.metric("Ruido de lectura",    f"{det.read_noise_e} e⁻/pix")
            m4.metric("Corriente oscura",    f"{det.dark_current_e_s:.6f} e⁻/s/pix")

            # Magnitud límite
            st.markdown("---")
            cl1, cl2 = st.columns([3, 1])
            with cl1:
                st.markdown("#### Magnitud límite (S/N = 5)")
                st.caption("Objeto más débil detectable con S/N ≥ 5 para el tiempo actual.")
            with cl2:
                try:
                    t_ref = result.time_for_target_snr or result.exposure_time_s
                    ml = limiting_magnitude(t_ref, 5.0, telescope, filt, det, conditions, src)
                    st.metric("Mag. límite", f"{ml:.2f} AB")
                except Exception:
                    st.caption("No calculable.")

    with col_side:
        st.markdown("## Detalles técnicos")

        st.markdown(f"""
<div class="html-card">
  <div class="section-kicker">Detector</div>
  <h3 style="margin-top:0;">Parámetros</h3>
  <div class="table-clean"><table>
    <thead><tr><th>Parámetro</th><th>Valor</th></tr></thead>
    <tbody>
      <tr><td>Ruido de lectura</td><td>{det.read_noise_e} e⁻/pix</td></tr>
      <tr><td>Corriente oscura</td><td>{det.dark_current_e_s} e⁻/s/pix</td></tr>
      <tr><td>Escala de píxel</td><td>{det.pixel_scale_arcsec} arcsec/pix</td></tr>
      <tr><td>Eficiencia cuántica</td><td>{det.quantum_efficiency*100:.0f} %</td></tr>
    </tbody>
  </table></div>
</div>
""", unsafe_allow_html=True)

        st.markdown(f"""
<div class="html-card">
  <div class="section-kicker">Filtro g — Configuración espectral</div>
  <h3 style="margin-top:0;">Parámetros</h3>
  <div class="table-clean"><table>
    <thead><tr><th>Parámetro</th><th>Valor</th></tr></thead>
    <tbody>
      <tr><td>Banda</td><td>{filt.name}</td></tr>
      <tr><td>λ_eff</td><td>{filt.lambda_eff_angstrom:.0f} Å</td></tr>
      <tr><td>Δλ</td><td>{filt.delta_lambda_angstrom:.0f} Å</td></tr>
      <tr><td>Brillo del cielo</td><td>{filt.sky_mag_arcsec2:.1f} mag/arcsec²</td></tr>
      <tr><td>k_λ (ref.)</td><td>{filt.extinction_coeff:.2f} mag/airmass *</td></tr>
    </tbody>
  </table></div>
  <div style="color:var(--text-muted);font-size:0.78rem;margin-top:0.4rem;">
    * k_λ definido pero no aplicado (sin extinción en el modelo).
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Limitaciones del modelo (enunciado)</div>
  <h3 style="margin-top:0;">Simplificaciones explícitas</h3>
  <div class="note-list">
    ✗ PSF gaussiana perfecta (no Moffat real)<br>
    ✗ Cielo uniforme y constante<br>
    ✗ Sin extinción atmosférica<br>
    ✗ Sin ruido de scintilación<br>
    ✗ Sin saturación del detector<br>
    ✗ Sin jittering NIR<br>
    ✗ Pixel scale fija 0.20"/pix<br>
    ✗ Transmisión constante T = 0.80<br><br>
    ✅ S/N sky-limited: S/N ∝ √t<br>
    ✅ S/N read-noise-limited: S/N ∝ t<br>
    ✅ RON y corriente oscura incluidos
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CURVAS S/N
# ══════════════════════════════════════════════════════════════════════════════
with tab_curves:
    t_start, t_end = 1.0, 100_000.0
    sub1, sub2 = st.tabs(["S/N vs. tiempo", "S/N vs. magnitud"])

    with sub1:
        t_arr, snr_arr = snr_vs_time(object_mag, telescope, filt, det, conditions, src,
                                     t_start=t_start, t_end=t_end)
        tvs, tls = build_log_ticks(t_start, t_end)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t_arr, y=snr_arr, mode="lines", name="Curva S/N",
                                 line=dict(color=T["plot_line"], width=3),
                                 hovertemplate="t = %{x:.1f} s<br>S/N = %{y:.2f}<extra></extra>"))
        if result and not error_msg:
            t_op = result.time_for_target_snr or result.exposure_time_s
            fig.add_trace(go.Scatter(x=[t_op], y=[result.snr], mode="markers",
                                     name="Punto de operación",
                                     marker=dict(color=T["plot_point"], size=11,
                                                 line=dict(width=1, color=T["plot_paper"])),
                                     hovertemplate=f"t={t_op:.1f} s<br>S/N={result.snr:.2f}<extra></extra>"))
            fig.add_vline(x=t_op, line_width=1.2, line_dash="dash", line_color=T["plot_point"], opacity=0.8)
            fig.add_hline(y=result.snr, line_width=1.2, line_dash="dash", line_color=T["plot_point"], opacity=0.8)
        if target_snr_input and calc_mode != "S/N dado el tiempo de exposición":
            fig.add_hline(y=target_snr_input, line_width=1.1, line_dash="dot",
                          line_color=T["plot_target"],
                          annotation_text=f"S/N objetivo = {target_snr_input:.0f}",
                          annotation_position="top left")
        fig.update_layout(
            template="plotly_dark" if theme=="dark" else "plotly_white",
            height=520, margin=dict(l=55,r=28,t=78,b=58),
            paper_bgcolor=T["plot_paper"], plot_bgcolor=T["plot_bg"],
            font=dict(family="Inter, sans-serif", size=13, color=T["plot_axis"]),
            title=dict(text=f"Filtro g · {object_mag:.1f} AB mag · D=8 m · T={throughput:.2f} · s={seeing:.2f}\"",
                       font=dict(size=14, color=T["plot_axis"]), x=0.02, xanchor="left", y=0.97),
            legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0.0,
                        bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
        )
        fig.update_xaxes(type="log", title="Tiempo de exposición",
                         tickmode="array", tickvals=tvs, ticktext=tls,
                         showgrid=True, gridcolor=T["plot_grid"], zeroline=False)
        fig.update_yaxes(title="Relación señal-ruido",
                         showgrid=True, gridcolor=T["plot_grid"], zeroline=False)
        st.markdown('<div class="plot-shell">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with sub2:
        t_ref_mag = (result.time_for_target_snr or result.exposure_time_s) if result else (exp_time or 60.0)
        mag_arr, snr_m = snr_vs_magnitude(t_ref_mag, telescope, filt, det, conditions, src)
        fig_m = go.Figure()
        fig_m.add_trace(go.Scatter(x=mag_arr, y=snr_m, mode="lines", name="S/N(mag)",
                                   line=dict(color=T["plot_line2"], width=2.5),
                                   hovertemplate="mag = %{x:.2f}<br>S/N = %{y:.2f}<extra></extra>"))
        fig_m.add_hline(y=5.0, line_width=1.2, line_dash="dot",
                        line_color=T["plot_target"], opacity=0.85,
                        annotation_text="S/N = 5 (mag. límite)", annotation_position="top right")
        if result and not error_msg:
            fig_m.add_vline(x=object_mag, line_width=1, line_dash="dash",
                            line_color=T["plot_point"], opacity=0.7)
        fig_m.update_layout(
            template="plotly_dark" if theme=="dark" else "plotly_white",
            height=460, margin=dict(l=55,r=28,t=78,b=58),
            paper_bgcolor=T["plot_paper"], plot_bgcolor=T["plot_bg"],
            font=dict(family="Inter, sans-serif", size=13, color=T["plot_axis"]),
            title=dict(text=f"S/N vs. magnitud · t = {format_time(t_ref_mag)} · D=8 m",
                       font=dict(size=14, color=T["plot_axis"]), x=0.02, xanchor="left", y=0.97),
            legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0.0,
                        bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
        )
        fig_m.update_xaxes(title="Magnitud AB", autorange="reversed",
                           showgrid=True, gridcolor=T["plot_grid"], zeroline=False)
        fig_m.update_yaxes(title="Relación señal-ruido",
                           showgrid=True, gridcolor=T["plot_grid"], zeroline=False)
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
        st.caption("Fracción de la varianza total de cada fuente. El término dominante define el régimen.")

        fig_pie = go.Figure(go.Pie(
            labels=["Shot noise\n(objeto)", "Fondo de cielo", "Corriente oscura", "Ruido de lectura"],
            values=[budget["shot_noise"], budget["sky"], budget["dark"], budget["read_noise"]],
            hole=0.52,
            marker=dict(colors=[T["plot_line"], T["plot_line2"], T["plot_target"], T["plot_point"]],
                        line=dict(color=T["plot_bg"], width=2)),
            textinfo="label+percent",
            textfont=dict(size=12, family="Inter, sans-serif", color=T["plot_axis"]),
            hovertemplate="%{label}<br>%{value:.1f}% de la varianza<extra></extra>",
        ))
        fig_pie.update_layout(
            template="plotly_dark" if theme=="dark" else "plotly_white",
            paper_bgcolor=T["plot_paper"], plot_bgcolor=T["plot_bg"],
            font=dict(family="Inter, sans-serif", size=12, color=T["plot_axis"]),
            height=380, margin=dict(l=16,r=16,t=50,b=20),
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5,
                        xanchor="left", x=1.02, bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
            title=dict(text="Contribuciones al ruido", font=dict(size=14, color=T["plot_axis"]),
                       x=0.01, y=0.97, xanchor="left"),
            annotations=[dict(text=f"<b>S/N</b><br>{result.snr:.1f}", x=0.5, y=0.5,
                              font=dict(size=16, color=T["plot_axis"], family="Source Serif 4, serif"),
                              showarrow=False)],
        )

        cp, ct = st.columns([1.3, 1])
        with cp:
            st.markdown('<div class="plot-shell">', unsafe_allow_html=True)
            st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)
        with ct:
            RDESC = {
                "sky-limited":        "Cielo domina. S/N ∝ √t.",
                "read-noise-limited": "RON domina. S/N ∝ t. Usar exposiciones más largas.",
                "shot-noise-limited": "Shot noise del objeto domina. S/N ∝ √t.",
                "dark-limited":       "Corriente oscura domina. S/N ∝ √t.",
            }
            st.markdown(f"""
<div class="html-card">
  <div class="section-kicker">Tabla de varianza</div>
  <h3 style="margin-top:0;">Términos de ruido</h3>
  <div class="table-clean"><table>
    <thead><tr><th>Fuente</th><th>Varianza (e⁻²)</th><th>%</th></tr></thead>
    <tbody>
      <tr><td>Shot noise</td><td>{result.signal_e:.1f}</td><td>{budget['shot_noise']:.1f}%</td></tr>
      <tr><td>Cielo</td><td>{result.sky_signal_e:.1f}</td><td>{budget['sky']:.1f}%</td></tr>
      <tr><td>Dark current</td><td>{result.dark_signal_e:.4f}</td><td>{budget['dark']:.3f}%</td></tr>
      <tr><td>Ruido de lectura</td><td>{result.read_noise_total_e2:.1f}</td><td>{budget['read_noise']:.1f}%</td></tr>
      <tr style="font-weight:600;"><td>Total</td><td>{budget['total_var']:.1f}</td><td>100%</td></tr>
    </tbody>
  </table></div>
</div>
<div class="html-card">
  <div class="section-kicker">Régimen dominante</div>
  <span class="regime-badge {result.noise_regime.replace(' ','-').replace('/','-')}">{result.noise_regime}</span>
  <div class="note-list" style="margin-top:0.6rem;">{RDESC.get(result.noise_regime,"")}</div>
</div>
""", unsafe_allow_html=True)
    else:
        st.info("Ejecuta un cálculo en la pestaña **Resultados**.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — VALIDACIÓN ESO
# ══════════════════════════════════════════════════════════════════════════════
with tab_validation:
    st.markdown("## Validación contra ETC de ESO")
    st.markdown("""
<div class="html-card">
  <div class="section-kicker">Flujo de trabajo</div>
  <h3 style="margin-top:0;">Cómo usar esta pestaña</h3>
  <div class="note-list">
    <strong>Paso 1 —</strong> Abre el <a href="https://etc.eso.org/observing/etc/fors" target="_blank"
    style="color:var(--accent);">ETC de ESO (FORS2)</a> y ejecuta tu cálculo.<br><br>
    <strong>Paso 2 —</strong> Pega el <strong>JSON de input</strong> del ETC (para leer magnitud, tiempo, seeing).<br><br>
    <strong>Paso 3 —</strong> Copia los valores del <strong>cuadro de resultados</strong> del ETC en los campos de abajo.<br><br>
    <strong>Paso 4 —</strong> Haz clic en <strong>🔬 Comparar</strong>.
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("### 1 · JSON de input del ETC de ESO")
    st.caption("La app extrae magnitud, tiempo, airmass y seeing automáticamente.")
    default_json = """{
  "target": {
    "morphology": {"morphologytype": "point"},
    "sed": {"sedtype": "spectrum",
      "spectrum": {"spectrumtype": "template", "params": {"catalog": "MARCS", "id": "5750:4.5"}},
      "extinctionav": 0},
    "brightness": {"brightnesstype": "mag", "magband": "V", "mag": 20, "magsys": "AB"}
  },
  "sky": {"airmass": 1, "fli": 0, "waterVapour": 30, "moonDistance": 90},
  "seeing": {"turbulence_category": 50, "aperturepix": 0},
  "instrument": {"DET.READ.CLKIND": "200kHz,2x2,low", "INS.FILT1.NAME": "GG435+81",
    "SEQ.CCD": "R", "INS.COLL.NAID": "COLL_HR+7", "ins_configuration": "img_nopol"},
  "timesnr": {"DET.WIN1.UIT1": 60, "snr": 18},
  "output": {"psf": {"psf": false}},
  "instrumentName": "fors"
}"""
    input_json_str = st.text_area("JSON de input", value=default_json, height=200,
                                  label_visibility="collapsed")

    _mag_in = object_mag; _texp_in = float(exp_time or 60.0)
    _air_in = airmass;    _see_in  = seeing
    try:
        _j = json.loads(input_json_str)
        _mag_in  = float(_j.get("target",{}).get("brightness",{}).get("mag", object_mag))
        _texp_in = float(_j.get("timesnr",{}).get("DET.WIN1.UIT1", exp_time or 60.0))
        _air_in  = float(_j.get("sky",{}).get("airmass", airmass))
        _turb    = int(_j.get("seeing",{}).get("turbulence_category", 50))
        _see_in  = {20:0.5, 30:0.65, 50:0.8, 70:1.0, 85:1.4}.get(_turb, 0.8)
        st.success(f"✅ JSON leído — mag={_mag_in} AB · t={_texp_in:.0f} s · airmass={_air_in} · seeing≈{_see_in}\"")
    except Exception as _e:
        st.warning(f"JSON no válido ({_e}). Usando valores del sidebar.")

    st.markdown("---")
    st.markdown("### 2 · Resultados del ETC de ESO")
    st.caption("Copia los valores del cuadro de resultados del ETC. Deja en 0 los que no aparezcan.")

    c1,c2,c3,c4,c5 = st.columns(5)
    eso_snr    = c1.number_input("S/N",            min_value=0.0, value=308.0,    step=1.0,    format="%.1f")
    eso_signal = c2.number_input("Starget [e⁻]",   min_value=0.0, value=123000.0, step=100.0,  format="%.0f")
    eso_sky    = c3.number_input("Ssky [e⁻]",      min_value=0.0, value=36000.0,  step=100.0,  format="%.0f")
    eso_npix   = c4.number_input("Npix",           min_value=0.0, value=38.0,     step=1.0,    format="%.0f")
    eso_ee     = c5.number_input("EE (fracción)",  min_value=0.0, max_value=1.0,  value=0.987, step=0.001, format="%.3f")

    c6,c7,c8,c9,c10 = st.columns(5)
    eso_ron     = c6.number_input("RON [e⁻/pix]",       min_value=0.0, value=3.15,     step=0.01,   format="%.2f")
    eso_dark    = c7.number_input("Dark [e⁻/s/pix]",    min_value=0.0, value=0.000583, step=0.0001, format="%.6f")
    eso_omega   = c8.number_input("Apertura Ω [arcsec²]",min_value=0.0, value=2.41,    step=0.01,   format="%.2f")
    eso_sky_pix = c9.number_input("Sky max [e⁻/pix]",   min_value=0.0, value=946.0,   step=1.0,    format="%.0f")
    eso_tgt_pix = c10.number_input("Target max [e⁻/pix]",min_value=0.0,value=10500.0, step=100.0,  format="%.0f")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔬 Comparar con nuestra CTE", type="primary"):
        try:
            _ap = math.sqrt(eso_omega/math.pi) if eso_omega > 0 else default_aperture_radius(_see_in)
            _c  = ObservingConditions(seeing_fwhm_arcsec=_see_in, aperture_radius_arcsec=_ap,
                                      total_throughput=throughput, n_reads=int(n_reads), airmass=_air_in)
            _t  = TelescopeParams(diameter_m=TELESCOPE_DIAMETER_M, obstruction_fraction=obstruction)
            _r  = compute_snr(float(_mag_in), float(_texp_in), _t, filt, det, _c, src)

            def _pct(o,e): return 100*(o-e)/e if e and e!=0 else None
            def _fp(p):    return ("+" if p>=0 else "")+f"{p:.1f} %" if p is not None else "—"
            def _fc(p):    return ("color:#86efac" if abs(p)<10 else "color:#fcd34d" if abs(p)<25 else "color:#f9a8d4") if p is not None else ""

            rows = [
                ("S/N",                   f"{_r.snr:.1f}",              f"{eso_snr:.1f}",     _pct(_r.snr,           eso_snr   if eso_snr>0 else None)),
                ("Señal objeto [e⁻]",     f"{_r.signal_e:,.0f}",       f"{eso_signal:,.0f}", _pct(_r.signal_e,      eso_signal if eso_signal>0 else None)),
                ("Señal cielo [e⁻]",      f"{_r.sky_signal_e:,.0f}",   f"{eso_sky:,.0f}",    _pct(_r.sky_signal_e,  eso_sky    if eso_sky>0 else None)),
                ("Píxeles en apertura",   f"{_r.n_pixels:.1f}",        f"{eso_npix:.0f}",    _pct(_r.n_pixels,      eso_npix   if eso_npix>0 else None)),
                ("Energía encerrada (EE)",f"{_r.enclosed_energy:.3f}", f"{eso_ee:.3f}",      _pct(_r.enclosed_energy,eso_ee    if eso_ee>0 else None)),
            ]
            rows_html = "".join(f"""
      <tr><td>{l}</td><td style="font-family:monospace;">{o}</td>
          <td style="font-family:monospace;">{e}</td>
          <td style="font-family:monospace;font-weight:600;{_fc(p)}">{_fp(p)}</td></tr>"""
                for l,o,e,p in rows)

            st.markdown(f"""
<div class="html-card">
  <div class="section-kicker">Filtro g · D=8 m · {_mag_in} AB · {_texp_in:.0f} s · seeing {_see_in:.2f}" · Ω={eso_omega:.2f} arcsec²</div>
  <h3 style="margin-top:0;">Tabla de comparación</h3>
  <div class="table-clean"><table>
    <thead><tr><th>Cantidad</th><th>Nuestra CTE</th><th>ETC de ESO</th><th>Diferencia</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table></div>
  <div class="note-list" style="margin-top:0.65rem;">
    <span style="color:#86efac;">■</span> &lt;10% &nbsp;
    <span style="color:#fcd34d;">■</span> 10–25% &nbsp;
    <span style="color:#f9a8d4;">■</span> &gt;25%
  </div>
</div>
""", unsafe_allow_html=True)

            st.markdown("#### Parámetros del detector")
            d1,d2,d3,d4 = st.columns(4)
            d1.metric("RON — ESO",       f"{eso_ron:.2f} e⁻/pix",    delta=f"{det.read_noise_e-eso_ron:+.2f} (CTE)")
            d2.metric("Dark — ESO",      f"{eso_dark:.6f} e⁻/s/pix", delta=f"{det.dark_current_e_s-eso_dark:+.6f} (CTE)")
            d3.metric("Sky max — ESO",   f"{eso_sky_pix:.0f} e⁻/pix",delta=f"{_r.sky_max_e_pix-eso_sky_pix:+.0f} (CTE)")
            d4.metric("Target max — ESO",f"{eso_tgt_pix:.0f} e⁻/pix",delta=f"{_r.source_max_e_pix-eso_tgt_pix:+.0f} (CTE)")

            # Gráfica de barras
            bl = []; bo = []; be = []
            for lbl, ov, ev in [("S/N",_r.snr,eso_snr), ("Señal [e⁻]",_r.signal_e,eso_signal), ("Cielo [e⁻]",_r.sky_signal_e,eso_sky)]:
                if ev > 0: bl.append(lbl); bo.append(ov); be.append(ev)
            if bl:
                fb = go.Figure()
                fb.add_trace(go.Bar(name="Nuestra CTE", x=bl, y=bo, marker_color=T["plot_line"],
                                    text=[f"{v:,.1f}" for v in bo], textposition="outside"))
                fb.add_trace(go.Bar(name="ETC de ESO",  x=bl, y=be, marker_color=T["plot_point"],
                                    text=[f"{v:,.1f}" for v in be], textposition="outside"))
                fb.update_layout(template="plotly_dark" if theme=="dark" else "plotly_white",
                                 barmode="group", height=360,
                                 margin=dict(l=50,r=20,t=55,b=40),
                                 paper_bgcolor=T["plot_paper"], plot_bgcolor=T["plot_bg"],
                                 font=dict(family="Inter, sans-serif", size=12, color=T["plot_axis"]),
                                 title=dict(text="CTE vs ETC ESO", font=dict(size=14), x=0.01, xanchor="left", y=0.97),
                                 legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0.0,
                                             bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
                                 yaxis=dict(showgrid=True, gridcolor=T["plot_grid"], zeroline=False))
                st.markdown('<div class="plot-shell">', unsafe_allow_html=True)
                st.plotly_chart(fb, use_container_width=True, config={"displayModeBar": False})
                st.markdown("</div>", unsafe_allow_html=True)

        except Exception as ex:
            st.error(f"Error al calcular: {ex}")

    st.markdown("---")
    st.markdown("""
<div class="html-card">
  <div class="section-kicker">Origen de las diferencias esperadas</div>
  <h3 style="margin-top:0;">¿Por qué no coinciden exactamente?</h3>
  <div class="table-clean"><table>
    <thead><tr><th>Factor</th><th>ETC de ESO</th><th>Nuestra CTE</th><th>Impacto</th></tr></thead>
    <tbody>
      <tr><td>PSF / EE</td><td>Moffat β=2.5 calibrado</td><td>Gaussiana perfecta</td><td>3–10%</td></tr>
      <tr><td>Extinción atmosférica</td><td>k(λ)·X incluida</td><td>No incluida</td><td>5–20%</td></tr>
      <tr><td>Espectro de cielo</td><td>Noll et al. 2012 (OH, O₂…)</td><td>Brillo AB plano</td><td>10–40%</td></tr>
      <tr><td>SED del objeto</td><td>Plantilla estelar (MARCS)</td><td>Fuente plana en F_ν</td><td>5–15%</td></tr>
      <tr><td>Throughput</td><td>Curvas reales T(λ)·QE(λ)</td><td>T constante = 0.80</td><td>5–10%</td></tr>
      <tr><td>Pixel scale</td><td>FORS2: 0.252"/pix</td><td>Enunciado: 0.20"/pix</td><td>~60% en Npix</td></tr>
    </tbody>
  </table></div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — MODELO FÍSICO
# ══════════════════════════════════════════════════════════════════════════════
with tab_model:
    cm1, cm2 = st.columns([1.1, 1])

    with cm1:
        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Ecuación fundamental</div>
  <h3 style="margin-top:0;">Relación señal-ruido</h3>
  <div class="note-list">Estadística de Poisson aplicada a cada fuente de ruido:</div>
</div>""", unsafe_allow_html=True)
        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"\frac{S}{N}=\frac{S}{\sqrt{S+N_\mathrm{sky}+N_\mathrm{dark}+\sigma_\mathrm{RON}^2 n_\mathrm{pix} n_\mathrm{reads}}}")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Regímenes asintóticos</div>
  <h3 style="margin-top:0;">Comportamiento límite</h3>
  <div class="note-list">Cuando domina el cielo (N<sub>sky</sub> ≫ resto):</div>
</div>""", unsafe_allow_html=True)
        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"\left(\frac{S}{N}\right)_\mathrm{sky}\approx\frac{S}{\sqrt{N_\mathrm{sky}}}\propto\sqrt{t}")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="note-list" style="margin:0 0 0.5rem 0;">Cuando domina el ruido de lectura (σ²<sub>RON</sub>·n<sub>pix</sub> ≫ resto):</div>', unsafe_allow_html=True)
        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"\left(\frac{S}{N}\right)_\mathrm{RON}\approx\frac{\Phi A\eta\,EE\,t}{\sigma_\mathrm{RON}\sqrt{n_\mathrm{pix}}}\propto t")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Cadena de conversión</div>
  <h3 style="margin-top:0;">Magnitud AB → señal [e⁻]</h3>
</div>""", unsafe_allow_html=True)
        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"F_\nu=F_0^\mathrm{AB}\cdot10^{-m_\mathrm{AB}/2.5}\quad[W\,m^{-2}\,Hz^{-1}]")
        st.latex(r"\Phi=\frac{F_\nu\cdot c\cdot\Delta\lambda}{\lambda_\mathrm{eff}^2}\cdot\frac{\lambda_\mathrm{eff}}{hc}\quad[\mathrm{ph\,s^{-1}\,m^{-2}}]")
        st.latex(r"S=\Phi\cdot A_\mathrm{eff}\cdot\eta\cdot EE(r_\mathrm{ap})\cdot t\quad[e^-]")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="note-list">⚠️ Sin extinción atmosférica (limitación del enunciado): m<sub>AB</sub> se usa directamente.</div>', unsafe_allow_html=True)

    with cm2:
        st.markdown("""
<div class="html-card">
  <div class="section-kicker">PSF gaussiana (enunciado)</div>
  <h3 style="margin-top:0;">Energía encerrada</h3>
  <div class="note-list">⚠️ Simplificación: PSFs reales tienen alas más extensas.</div>
</div>""", unsafe_allow_html=True)
        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"\sigma=\frac{\mathrm{FWHM}}{2\sqrt{2\ln2}}")
        st.latex(r"EE(r_\mathrm{ap})=1-\exp\!\left(-\frac{r_\mathrm{ap}^2}{2\sigma^2}\right)")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Telescopio · D = 8 m</div>
  <h3 style="margin-top:0;">Área efectiva</h3>
</div>""", unsafe_allow_html=True)
        st.markdown('<div class="eq-wrap">', unsafe_allow_html=True)
        st.latex(r"A_\mathrm{eff}=\frac{\pi D^2}{4}(1-\epsilon^2)\quad D=8\,\mathrm{m},\;\epsilon=0.14")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Simplificaciones del enunciado</div>
  <h3 style="margin-top:0;">Lo que el modelo NO incluye</h3>
  <div class="table-clean"><table>
    <thead><tr><th>Efecto omitido</th><th>Impacto</th></tr></thead>
    <tbody>
      <tr><td>Extinción atmosférica</td><td>5–20 % en señal</td></tr>
      <tr><td>PSF Moffat (alas reales)</td><td>EE ~3–10% menor</td></tr>
      <tr><td>Ruido de scintilación</td><td>Despreciable &gt;1 s</td></tr>
      <tr><td>Saturación del detector</td><td>Objetos brillantes</td></tr>
      <tr><td>Jittering NIR</td><td>Ks: variación 2–3×</td></tr>
      <tr><td>T(λ) y QE(λ) espectrales</td><td>5–10 % en señal</td></tr>
    </tbody>
  </table></div>
</div>""", unsafe_allow_html=True)

        st.markdown("""
<div class="html-card">
  <div class="section-kicker">Referencias</div>
  <h3 style="margin-top:0;">Bibliografía</h3>
  <div class="note-list">
    · Howell (2006) <em>Handbook of CCD Astronomy</em>, 2ª ed.<br>
    · Rieke (2003) <em>Detection of Light</em>, Cambridge UP<br>
    · Oke &amp; Gunn (1983) ApJ 266, 713<br>
    · ESO FORS ETC — <a href="https://etc.eso.org/fors" target="_blank"
      style="color:var(--accent);">etc.eso.org/fors</a>
  </div>
</div>""", unsafe_allow_html=True)