"""
backend.py — Calculadora de Tiempo de Exposición (CTE) — Núcleo Científico
===========================================================================
Todas las funciones son puras (sin efectos secundarios ni E/S) y devuelven
objetos Python planos, por lo que pueden llamarse desde cualquier frontend
(Streamlit, Flask, CLI …).

Modelo Físico
-------------
La relación señal-ruido (S/N) se define como:

    S/N = S / sqrt(S + N_sky + N_dark + σ_RON² · n_pix · n_reads)

donde:
    S        = señal del objeto                          [e⁻]
    N_sky    = señal del fondo de cielo                  [e⁻]
    N_dark   = señal de corriente oscura                 [e⁻]
    σ_RON²   = varianza del ruido de lectura por píxel  [e⁻²]
    n_pix    = número de píxeles en la apertura
    n_reads  = número de lecturas del detector

Cadena de conversión:
    mag_AB  →  F_ν [W/m²/Hz]  →  F_λ [W/m²/m]  →  flujo de banda [W/m²]
            →  flujo de fotones [ph/s/m²]  →  señal del detector [e⁻]

Referencias:
    - ESO FORS ETC white-paper (https://etc.eso.org/fors)
    - Howell (2006) "Handbook of CCD Astronomy", 2ª ed.
    - Rieke (2003) "Detection of Light", Cambridge UP
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Constantes físicas fundamentales
# ---------------------------------------------------------------------------
H_PLANCK: float = 6.62607015e-34   # J·s   (CODATA 2018)
C_LIGHT: float  = 2.99792458e8     # m/s   (exacto)
AB_F0: float    = 3.630780548e-23  # W/m²/Hz  (flujo cero AB, Oke & Gunn 1983)

# ---------------------------------------------------------------------------
# Data classes (contenedores de parámetros)
# ---------------------------------------------------------------------------

@dataclass
class TelescopeParams:
    """Parámetros del telescopio primario y obstrucción central."""
    diameter_m: float                      # diámetro del espejo primario [m]
    obstruction_fraction: float = 0.12    # fracción lineal del diámetro obstruida

    @property
    def collecting_area_m2(self) -> float:
        """Área efectiva de recolección [m²].

        A = π · (r_outer² − r_inner²)
        donde r_inner = obstruction_fraction · r_outer
        """
        r_outer = self.diameter_m / 2.0
        r_inner = r_outer * self.obstruction_fraction
        return math.pi * (r_outer ** 2 - r_inner ** 2)


@dataclass
class FilterParams:
    """Definición de una banda fotométrica."""
    name: str
    lambda_eff_angstrom: float    # longitud de onda efectiva [Å]
    delta_lambda_angstrom: float  # anchura de banda [Å]
    sky_mag_arcsec2: float        # brillo superficial del cielo [AB mag/arcsec²]
    mode: Literal["optical", "nir"] = "optical"

    @property
    def lambda_eff_m(self) -> float:
        """Longitud de onda efectiva en metros."""
        return self.lambda_eff_angstrom * 1e-10

    @property
    def delta_lambda_m(self) -> float:
        """Anchura de banda en metros."""
        return self.delta_lambda_angstrom * 1e-10

    @property
    def lambda_eff_um(self) -> float:
        """Longitud de onda efectiva en micrómetros (para etiquetas)."""
        return self.lambda_eff_angstrom * 1e-4


@dataclass
class DetectorParams:
    """Características del detector (CCD o array IR)."""
    read_noise_e: float        # ruido de lectura  [e⁻/pix/lectura]
    dark_current_e_s: float    # corriente oscura  [e⁻/pix/s]
    pixel_scale_arcsec: float  # escala de placa   [arcsec/pix]
    quantum_efficiency: float  # eficiencia cuántica (adimensional, 0–1)


@dataclass
class ObservingConditions:
    """Parámetros atmosféricos y de observación."""
    seeing_fwhm_arcsec: float        # FWHM de la PSF  [arcsec]
    aperture_radius_arcsec: float    # radio de apertura fotométrica [arcsec]
    total_throughput: float = 0.80   # transmisión total telescopio + óptica + filtro [0–1]
    n_reads: int = 1                 # número de lecturas (útil para NIR up-the-ramp)

    @property
    def aperture_diameter_arcsec(self) -> float:
        return 2.0 * self.aperture_radius_arcsec


# ---------------------------------------------------------------------------
# Configuraciones instrumentales predefinidas
# ---------------------------------------------------------------------------

OPTICAL_DETECTOR = DetectorParams(
    read_noise_e=4.5,
    dark_current_e_s=0.002,
    pixel_scale_arcsec=0.20,
    quantum_efficiency=0.85,
)

NIR_DETECTOR = DetectorParams(
    read_noise_e=10.0,
    dark_current_e_s=0.02,
    pixel_scale_arcsec=0.20,
    quantum_efficiency=0.75,
)

OPTICAL_FILTERS: dict[str, FilterParams] = {
    "g": FilterParams("g", 4800.0, 1400.0, 22.0, "optical"),
    "r": FilterParams("r", 6200.0, 1300.0, 20.8, "optical"),
    "i": FilterParams("i", 7600.0, 1500.0, 19.5, "optical"),
}

NIR_FILTERS: dict[str, FilterParams] = {
    "J":  FilterParams("J",  12500.0, 2600.0, 16.0, "nir"),
    "H":  FilterParams("H",  16500.0, 3000.0, 14.0, "nir"),
    "Ks": FilterParams("Ks", 22000.0, 3500.0, 13.0, "nir"),
}

ALL_FILTERS: dict[str, FilterParams] = {**OPTICAL_FILTERS, **NIR_FILTERS}

# Aperturas de telescopio disponibles [m]
TELESCOPE_APERTURES: list[float] = [2.0, 3.5, 6.5, 8.0]


# ---------------------------------------------------------------------------
# Funciones físicas centrales
# ---------------------------------------------------------------------------

def mag_ab_to_photon_flux(
    mag_ab: float,
    lambda_eff_m: float,
    delta_lambda_m: float,
) -> float:
    """
    Convierte magnitud AB a flujo de fotones integrado en la banda [ph/s/m²].

    Derivación paso a paso
    ----------------------
    1. Magnitud AB → densidad espectral de flujo:
           F_ν = F₀_AB · 10^(−mag_AB / 2.5)          [W/m²/Hz]
       donde F₀_AB = 3.631 × 10⁻²³ W/m²/Hz

    2. Conversión F_ν → F_λ  (por invariancia de energía):
           F_λ = F_ν · c / λ²                         [W/m²/m]

    3. Integración en la banda (aproximación de banda plana):
           F_band = F_λ · Δλ                           [W/m²]

    4. Energía por fotón a λ_eff:
           E_ph = h·c / λ_eff                          [J]

    5. Flujo de fotones:
           Φ = F_band / E_ph                           [ph/s/m²]

    Parámetros
    ----------
    mag_ab        : magnitud AB de la fuente
    lambda_eff_m  : longitud de onda efectiva del filtro [m]
    delta_lambda_m: anchura de banda del filtro [m]

    Retorna
    -------
    Flujo de fotones [ph/s/m²]
    """
    # Paso 1: F_ν en SI
    f_nu: float = AB_F0 * 10.0 ** (-mag_ab / 2.5)          # W/m²/Hz

    # Paso 2: F_λ en SI
    f_lambda: float = f_nu * C_LIGHT / lambda_eff_m ** 2   # W/m²/m

    # Paso 3: flujo integrado en la banda
    f_band: float = f_lambda * delta_lambda_m               # W/m²

    # Paso 4: energía por fotón
    e_photon: float = H_PLANCK * C_LIGHT / lambda_eff_m     # J

    # Paso 5: flujo de fotones
    return f_band / e_photon                                 # ph/s/m²


def enclosed_energy_fraction(
    aperture_radius_arcsec: float,
    seeing_fwhm_arcsec: float,
) -> float:
    """
    Fracción de energía encerrada (EE) dentro de una apertura circular,
    asumiendo una PSF gaussiana bidimensional.

    Derivación
    ----------
    Para una gaussiana circular con σ:
        I(r) = (1/2πσ²) · exp(−r²/2σ²)

    La fracción encerrada en un círculo de radio r_ap es:
        EE(r_ap) = ∫₀^{r_ap} I(r) · 2πr dr
                 = 1 − exp(−r_ap² / 2σ²)

    Relación FWHM–σ:
        FWHM = 2·√(2·ln2)·σ  →  σ = FWHM / (2·√(2·ln2))

    Nota: PSFs reales (e.g., Moffat) tienen alas más extendidas que una
    gaussiana; esto subestima la energía en alas largas.

    Parámetros
    ----------
    aperture_radius_arcsec : radio de la apertura fotométrica [arcsec]
    seeing_fwhm_arcsec     : FWHM del seeing atmosférico [arcsec]

    Retorna
    -------
    Fracción de energía encerrada (0–1)
    """
    sigma: float = seeing_fwhm_arcsec / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    return 1.0 - math.exp(-aperture_radius_arcsec ** 2 / (2.0 * sigma ** 2))


def aperture_n_pixels(
    aperture_radius_arcsec: float,
    pixel_scale_arcsec: float,
) -> float:
    """
    Número de píxeles dentro de una apertura circular de radio dado.

        n_pix = π · (r_ap / plate_scale)²

    Parámetros
    ----------
    aperture_radius_arcsec : radio de la apertura [arcsec]
    pixel_scale_arcsec     : escala de placa del detector [arcsec/pix]

    Retorna
    -------
    Número de píxeles (puede ser no entero; representa el área media)
    """
    r_pix: float = aperture_radius_arcsec / pixel_scale_arcsec
    return math.pi * r_pix ** 2


def sky_electron_rate_per_pixel(
    sky_mag_arcsec2: float,
    lambda_eff_m: float,
    delta_lambda_m: float,
    collecting_area_m2: float,
    throughput: float,
    qe: float,
    pixel_scale_arcsec: float,
) -> float:
    """
    Tasa de electrones del fondo de cielo por píxel [e⁻/s/pix].

    El cielo se trata como una fuente extendida con brillo superficial
    sky_mag_arcsec² [AB mag/arcsec²]. La conversión es:

        sky_rate_pix = Φ(sky_mag) · Ω_pix · A · η · QE

    donde Ω_pix = pixel_scale² es el área sólida de un píxel [arcsec²].

    Parámetros
    ----------
    sky_mag_arcsec2     : brillo superficial del cielo [AB mag/arcsec²]
    lambda_eff_m        : longitud de onda efectiva [m]
    delta_lambda_m      : anchura de banda [m]
    collecting_area_m2  : área efectiva del telescopio [m²]
    throughput          : transmisión total del sistema (0–1)
    qe                  : eficiencia cuántica del detector (0–1)
    pixel_scale_arcsec  : escala de placa [arcsec/pix]

    Retorna
    -------
    Tasa de electrones de cielo por píxel [e⁻/s/pix]
    """
    flux_per_arcsec2: float = mag_ab_to_photon_flux(
        sky_mag_arcsec2, lambda_eff_m, delta_lambda_m
    )
    omega_pix: float = pixel_scale_arcsec ** 2          # arcsec²/pix
    eta_total: float = throughput * qe
    return flux_per_arcsec2 * omega_pix * collecting_area_m2 * eta_total


# ---------------------------------------------------------------------------
# Contenedor de resultados
# ---------------------------------------------------------------------------

@dataclass
class ETCResult:
    """Todos los valores de salida de un cálculo CTE."""

    # Eco de entradas (para visualización)
    object_mag: float
    exposure_time_s: float
    filter_name: str
    telescope_diameter_m: float

    # Señales [e⁻]
    signal_e: float
    sky_signal_e: float
    dark_signal_e: float
    read_noise_total_e2: float   # varianza total: RON² × n_pix × n_reads  [e⁻²]

    # Derivados
    snr: float
    n_pixels: float
    enclosed_energy: float
    noise_regime: str            # "sky-limited" | "read-noise-limited" |
                                 # "dark-limited" | "shot-noise-limited"

    # Para el modo de resolución de tiempo dado un S/N objetivo
    time_for_target_snr: Optional[float] = None
    target_snr: Optional[float] = None

    # Tasas intermedias (útiles para diagnóstico)
    sky_rate_per_pix_e_s: float = 0.0   # [e⁻/s/pix]
    object_photon_flux: float = 0.0     # [ph/s/m²]

    # Intensidades máximas por píxel (para saturación)
    sky_max_e_pix: float = 0.0
    source_max_e_pix: float = 0.0

    @property
    def total_noise_e(self) -> float:
        """Ruido total RMS [e⁻]."""
        return math.sqrt(
            self.signal_e
            + self.sky_signal_e
            + self.dark_signal_e
            + self.read_noise_total_e2
        )

    @property
    def snr_sky_limited(self) -> float:
        """S/N en el límite dominado por el cielo (aproximación)."""
        if self.sky_signal_e <= 0:
            return 0.0
        return self.signal_e / math.sqrt(self.sky_signal_e)

    @property
    def snr_shot_limited(self) -> float:
        """S/N en el límite dominado por el shot noise del objeto."""
        if self.signal_e <= 0:
            return 0.0
        return math.sqrt(self.signal_e)


# ---------------------------------------------------------------------------
# Motor CTE principal
# ---------------------------------------------------------------------------

def compute_snr(
    object_mag: float,
    exposure_time_s: float,
    telescope: TelescopeParams,
    filter_params: FilterParams,
    detector: DetectorParams,
    conditions: ObservingConditions,
    source_type: Literal["point", "extended"] = "point",
) -> ETCResult:
    """
    Calcula la relación señal-ruido (S/N) para un tiempo de exposición dado.

    Ecuación completa de S/N
    ------------------------
    S/N = S / √(S + N_sky + N_dark + σ_RON² · n_pix · n_reads)

    donde:
        S       = Φ · A · η_total · EE(r_ap) · t             [e⁻]
        N_sky   = sky_rate_pix · n_pix · t                   [e⁻]
        N_dark  = dark_current · n_pix · t                   [e⁻]
        σ_RON²  = read_noise² · n_pix · n_reads              [e⁻²]

    Parámetros
    ----------
    object_mag      : magnitud AB del objeto
    exposure_time_s : tiempo de integración [s]
    telescope       : instancia de TelescopeParams
    filter_params   : instancia de FilterParams
    detector        : instancia de DetectorParams
    conditions      : instancia de ObservingConditions
    source_type     : 'point' → aplica corrección EE;
                      'extended' → EE = 1 (toda la apertura captura flujo)

    Retorna
    -------
    ETCResult con todos los campos populados
    """
    t: float = exposure_time_s
    A: float = telescope.collecting_area_m2
    lam: float = filter_params.lambda_eff_m
    dlam: float = filter_params.delta_lambda_m

    # Eficiencia combinada de óptica + detector
    eta: float = conditions.total_throughput * detector.quantum_efficiency

    # ── Señal del objeto [e⁻] ──────────────────────────────────────────────
    photon_flux: float = mag_ab_to_photon_flux(object_mag, lam, dlam)  # ph/s/m²

    if source_type == "point":
        ee: float = enclosed_energy_fraction(
            conditions.aperture_radius_arcsec,
            conditions.seeing_fwhm_arcsec,
        )
    else:
        # Fuente extendida: la apertura captura todo el brillo superficial
        # dentro de ella; no hay concentración por PSF
        ee = 1.0

    signal_e: float = photon_flux * A * eta * ee * t   # e⁻

    # ── Número de píxeles en la apertura ─────────────────────────────────
    n_pix: float = aperture_n_pixels(
        conditions.aperture_radius_arcsec,
        detector.pixel_scale_arcsec,
    )

    # ── Fondo de cielo [e⁻] ───────────────────────────────────────────────
    sky_rate: float = sky_electron_rate_per_pixel(
        filter_params.sky_mag_arcsec2,
        lam, dlam, A,
        conditions.total_throughput,
        detector.quantum_efficiency,
        detector.pixel_scale_arcsec,
    )
    sky_signal_e: float = sky_rate * n_pix * t   # e⁻

    # ── Corriente oscura [e⁻] ─────────────────────────────────────────────
    dark_signal_e: float = detector.dark_current_e_s * n_pix * t   # e⁻

    # ── Varianza del ruido de lectura [e⁻²] ──────────────────────────────
    read_noise_var: float = (
        detector.read_noise_e ** 2 * n_pix * conditions.n_reads
    )

    # ── Varianza total y S/N ──────────────────────────────────────────────
    total_noise2: float = (
        signal_e + sky_signal_e + dark_signal_e + read_noise_var
    )
    snr: float = signal_e / math.sqrt(total_noise2) if total_noise2 > 0 else 0.0

    # ── Identificación del régimen dominante ──────────────────────────────
    noise_regime: str = _identify_noise_regime(
        signal_e, sky_signal_e, dark_signal_e, read_noise_var
    )

    # ── Intensidades por píxel (diagnóstico) ─────────────────────────────
    # Pico de la fuente puntual: asumimos que el píxel central recibe
    # la fracción de flujo correspondiente al área de un píxel dentro del PSF
    sigma_pix: float = (conditions.seeing_fwhm_arcsec / detector.pixel_scale_arcsec) / (
        2.0 * math.sqrt(2.0 * math.log(2.0))
    )
    peak_fraction: float = (
        1.0 - math.exp(-0.5 / sigma_pix ** 2)
    ) if source_type == "point" else (1.0 / n_pix)
    source_max_e_pix: float = photon_flux * A * eta * peak_fraction * t

    return ETCResult(
        object_mag=object_mag,
        exposure_time_s=t,
        filter_name=filter_params.name,
        telescope_diameter_m=telescope.diameter_m,
        signal_e=signal_e,
        sky_signal_e=sky_signal_e,
        dark_signal_e=dark_signal_e,
        read_noise_total_e2=read_noise_var,
        snr=snr,
        n_pixels=n_pix,
        enclosed_energy=ee,
        noise_regime=noise_regime,
        sky_rate_per_pix_e_s=sky_rate,
        object_photon_flux=photon_flux,
        sky_max_e_pix=sky_rate * t,
        source_max_e_pix=source_max_e_pix,
    )


def compute_exposure_time(
    object_mag: float,
    target_snr: float,
    telescope: TelescopeParams,
    filter_params: FilterParams,
    detector: DetectorParams,
    conditions: ObservingConditions,
    source_type: Literal["point", "extended"] = "point",
    t_min: float = 0.1,
    t_max: float = 1_000_000.0,
    tol: float = 1e-5,
) -> ETCResult:
    """
    Resuelve el tiempo de exposición necesario para alcanzar un S/N objetivo
    mediante bisección numérica.

    El S/N crece monótonamente con t, por lo que la bisección converge
    siempre que el S/N objetivo sea alcanzable dentro del intervalo [t_min, t_max].

    Parámetros
    ----------
    object_mag  : magnitud AB del objeto
    target_snr  : S/N objetivo
    telescope   : TelescopeParams
    filter_params: FilterParams
    detector    : DetectorParams
    conditions  : ObservingConditions
    source_type : 'point' | 'extended'
    t_min       : límite inferior del intervalo de búsqueda [s]
    t_max       : límite superior del intervalo de búsqueda [s]
    tol         : tolerancia relativa de convergencia

    Retorna
    -------
    ETCResult evaluado en el tiempo resuelto, con time_for_target_snr y
    target_snr populados.

    Lanza
    -----
    ValueError si el S/N objetivo no se puede alcanzar en [t_min, t_max].
    """
    result_max = compute_snr(
        object_mag, t_max, telescope, filter_params, detector, conditions, source_type
    )
    if result_max.snr < target_snr:
        raise ValueError(
            f"No se puede alcanzar S/N = {target_snr:.1f} "
            f"ni siquiera en t = {format_time(t_max)} "
            f"(S/N máximo ≈ {result_max.snr:.1f}). "
            "Prueba con un objeto más brillante o un telescopio mayor."
        )

    lo, hi = t_min, t_max
    for _ in range(80):   # 80 iteraciones → precisión de ~10⁻²⁴ en la razón hi/lo
        mid = (lo + hi) / 2.0
        snr_mid = compute_snr(
            object_mag, mid, telescope, filter_params, detector, conditions, source_type
        ).snr
        if snr_mid < target_snr:
            lo = mid
        else:
            hi = mid
        if (hi - lo) / max(hi, 1e-12) < tol:
            break

    t_solved = (lo + hi) / 2.0
    result = compute_snr(
        object_mag, t_solved, telescope, filter_params, detector, conditions, source_type
    )
    result.time_for_target_snr = t_solved
    result.target_snr = target_snr
    return result


def snr_vs_time(
    object_mag: float,
    telescope: TelescopeParams,
    filter_params: FilterParams,
    detector: DetectorParams,
    conditions: ObservingConditions,
    source_type: Literal["point", "extended"] = "point",
    t_start: float = 1.0,
    t_end: float = 3600.0,
    n_points: int = 300,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Genera arrays (tiempos, S/Ns) para la curva S/N vs. tiempo de exposición.

    Los tiempos se distribuyen logarítmicamente para capturar bien tanto
    el régimen dominado por ruido de lectura (tiempos cortos) como el
    régimen dominado por el cielo (tiempos largos).

    Retorna
    -------
    (times [s], snrs) como arrays numpy
    """
    times: np.ndarray = np.logspace(
        math.log10(t_start), math.log10(t_end), n_points
    )
    snrs: np.ndarray = np.array([
        compute_snr(
            object_mag, float(t), telescope, filter_params,
            detector, conditions, source_type
        ).snr
        for t in times
    ])
    return times, snrs


def snr_vs_magnitude(
    exposure_time_s: float,
    telescope: TelescopeParams,
    filter_params: FilterParams,
    detector: DetectorParams,
    conditions: ObservingConditions,
    source_type: Literal["point", "extended"] = "point",
    mag_start: float = 14.0,
    mag_end: float = 28.0,
    n_points: int = 200,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Genera arrays (magnitudes, S/Ns) para la curva S/N vs. magnitud.

    Útil para determinar la magnitud límite del telescopio para un S/N
    y tiempo de exposición dados.

    Retorna
    -------
    (mags, snrs) como arrays numpy
    """
    mags: np.ndarray = np.linspace(mag_start, mag_end, n_points)
    snrs: np.ndarray = np.array([
        compute_snr(
            float(m), exposure_time_s, telescope, filter_params,
            detector, conditions, source_type
        ).snr
        for m in mags
    ])
    return mags, snrs


def limiting_magnitude(
    exposure_time_s: float,
    target_snr: float,
    telescope: TelescopeParams,
    filter_params: FilterParams,
    detector: DetectorParams,
    conditions: ObservingConditions,
    source_type: Literal["point", "extended"] = "point",
    mag_min: float = 10.0,
    mag_max: float = 35.0,
    tol: float = 1e-4,
) -> float:
    """
    Calcula la magnitud límite alcanzable para un S/N y tiempo dados
    mediante bisección sobre la magnitud.

    Retorna
    -------
    Magnitud AB límite (cuanto mayor, más débil la fuente detectable).
    """
    snr_at_max = compute_snr(
        mag_max, exposure_time_s, telescope, filter_params,
        detector, conditions, source_type
    ).snr
    if snr_at_max >= target_snr:
        return mag_max  # el telescopio puede ir aún más profundo

    lo, hi = mag_min, mag_max
    for _ in range(80):
        mid = (lo + hi) / 2.0
        snr_mid = compute_snr(
            mid, exposure_time_s, telescope, filter_params,
            detector, conditions, source_type
        ).snr
        if snr_mid > target_snr:
            lo = mid
        else:
            hi = mid
        if abs(hi - lo) < tol:
            break
    return (lo + hi) / 2.0


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------

def _identify_noise_regime(
    signal_e: float,
    sky_e: float,
    dark_e: float,
    rn2: float,
) -> str:
    """Identifica y devuelve el régimen dominante de ruido."""
    terms: dict[str, float] = {
        "sky-limited":        sky_e,
        "shot-noise-limited": signal_e,
        "dark-limited":       dark_e,
        "read-noise-limited": rn2,
    }
    return max(terms, key=lambda k: terms[k])


def detector_for_filter(f: FilterParams) -> DetectorParams:
    """Devuelve el detector estándar correspondiente al modo del filtro."""
    return OPTICAL_DETECTOR if f.mode == "optical" else NIR_DETECTOR


def default_aperture_radius(seeing_fwhm_arcsec: float) -> float:
    """
    Radio de apertura fotométrica por defecto según el proyecto:
        r_ap = 1.2 × FWHM

    Esta elección optimiza el S/N en el régimen dominado por el cielo
    para una PSF gaussiana (ver Naylor 1998).
    """
    return 1.2 * seeing_fwhm_arcsec


def format_time(seconds: float) -> str:
    """Formatea un tiempo de exposición en una cadena legible."""
    if seconds < 1.0:
        return f"{seconds*1000:.0f} ms"
    if seconds < 60.0:
        return f"{seconds:.1f} s"
    if seconds < 3600.0:
        return f"{seconds/60:.1f} min"
    return f"{seconds/3600:.2f} h"


def noise_budget(result: ETCResult) -> dict[str, float]:
    """
    Devuelve el presupuesto de ruido como fracción porcentual de la varianza total.

    Retorna
    -------
    dict con claves: 'shot_noise', 'sky', 'dark', 'read_noise', 'total_var'
    """
    total_var: float = (
        result.signal_e
        + result.sky_signal_e
        + result.dark_signal_e
        + result.read_noise_total_e2
    )
    if total_var == 0:
        return {"shot_noise": 0, "sky": 0, "dark": 0, "read_noise": 0, "total_var": 0}

    return {
        "shot_noise":  100.0 * result.signal_e              / total_var,
        "sky":         100.0 * result.sky_signal_e          / total_var,
        "dark":        100.0 * result.dark_signal_e         / total_var,
        "read_noise":  100.0 * result.read_noise_total_e2   / total_var,
        "total_var":   total_var,
    }


def saturation_time(
    object_mag: float,
    telescope: TelescopeParams,
    filter_params: FilterParams,
    detector: DetectorParams,
    conditions: ObservingConditions,
    saturation_level_e: float = 65_000.0,
    source_type: Literal["point", "extended"] = "point",
) -> float:
    """
    Tiempo de exposición en el que el píxel pico se satura [s].

    Parámetros
    ----------
    saturation_level_e : pozo de carga del detector [e⁻/pix], típico CCD 16-bit
    """
    # Evaluar a t = 1 s para obtener la tasa por píxel pico
    result = compute_snr(
        object_mag, 1.0, telescope, filter_params, detector, conditions, source_type
    )
    peak_rate = result.source_max_e_pix + result.sky_max_e_pix  # e⁻/s/pix @ t=1s
    if peak_rate <= 0:
        return float("inf")
    return saturation_level_e / peak_rate


# ---------------------------------------------------------------------------
# Validación contra ESO ETC
# ---------------------------------------------------------------------------

"""
Mapeo de filtros propios → filtros ESO FORS2 / HAWK-I equivalentes.

La correspondencia es por λ_eff y anchura de banda. Se usa el instrumento
más cercano disponible en el ETC público de ESO:
  - g, r, i  → FORS2 (VLT 8.2 m) o EFOSC2 (NTT 3.5 m)
  - J, H, Ks → HAWK-I (VLT 8.2 m)

Referencias de nombres de filtros:
  https://www.eso.org/sci/facilities/paranal/instruments/fors/inst/Filters.html
  https://www.eso.org/sci/facilities/paranal/instruments/hawki/inst/filters.html
"""

# Filtros ESO equivalentes a los nuestros
ESO_FILTER_MAP: dict[str, dict] = {
    # banda_nuestra -> info ESO
    "g":  {"eso_filter": "g_HIGH",    "instrument": "FORS2",  "eso_name": "g_HIGH (FORS2)",  "lambda_eff_A": 4730, "delta_lambda_A": 1340},
    "r":  {"eso_filter": "r_SPECIAL", "instrument": "FORS2",  "eso_name": "r_SPECIAL (FORS2)","lambda_eff_A": 6550, "delta_lambda_A": 1650},
    "i":  {"eso_filter": "I_BESS",    "instrument": "FORS2",  "eso_name": "I_BESS (FORS2)",  "lambda_eff_A": 7680, "delta_lambda_A": 1380},
    "J":  {"eso_filter": "J",         "instrument": "HAWKI",  "eso_name": "J (HAWK-I)",       "lambda_eff_A": 12520,"delta_lambda_A": 1600},
    "H":  {"eso_filter": "H",         "instrument": "HAWKI",  "eso_name": "H (HAWK-I)",       "lambda_eff_A": 16310,"delta_lambda_A": 2990},
    "Ks": {"eso_filter": "Ks",        "instrument": "HAWKI",  "eso_name": "Ks (HAWK-I)",      "lambda_eff_A": 21490,"delta_lambda_A": 3090},
}

# Telescopios ESO disponibles y sus diámetros
ESO_TELESCOPES: dict[str, float] = {
    "VLT":  8.2,   # Very Large Telescope (Paranal)
    "NTT":  3.5,   # New Technology Telescope (La Silla)
}

# Payloads ESO para cada combinación instrumento/filtro.
# Estos son los JSON completos que acepta la API etcapi de ESO.
# Parámetros comunes: seeing 0.8", airmass 1.0, luna nueva,
# fuente puntual G2V 20 AB mag, tiempo fijo 600 s.

def build_eso_payload(
    filter_name: str,
    object_mag: float,
    exposure_time_s: float,
    seeing_fwhm: float = 0.8,
    airmass: float = 1.0,
) -> dict:
    """
    Construye el payload JSON para la API del ETC de ESO (FORS2 o HAWK-I).

    El payload sigue el formato documentado en:
      https://etc.eso.org/observing/etc/doc/

    Parámetros
    ----------
    filter_name    : nombre de nuestro filtro ('g', 'r', 'i', 'J', 'H', 'Ks')
    object_mag     : magnitud AB del objeto
    exposure_time_s: tiempo de exposición en segundos
    seeing_fwhm    : FWHM del seeing en arcsec (zenith)
    airmass        : masa de aire

    Retorna
    -------
    dict con el payload JSON listo para POST a la API de ESO
    """
    if filter_name not in ESO_FILTER_MAP:
        raise ValueError(f"Filtro '{filter_name}' no tiene equivalente ESO definido.")

    info = ESO_FILTER_MAP[filter_name]
    instrument = info["instrument"]
    eso_filter = info["eso_filter"]

    # Instrumento y modo
    if instrument == "FORS2":
        inst_block = {
            "name": "FORS2",
            "mode": {"name": "IMG"},
            "filter": eso_filter,
        }
    else:  # HAWKI
        inst_block = {
            "name": "HAWKI",
            "mode": {"name": "IMG"},
            "filter": eso_filter,
        }

    return {
        "target": {
            "morphology": "PointSource",
            "sed": {
                "type": "Template",
                "template": {
                    "library": "Pickles",
                    "type": "G2V"
                }
            },
            "brightness": {
                "band": "V",
                "magnitude": object_mag,
                "system": "AB"
            }
        },
        "conditions": {
            "seeing": {
                "zenith_seeing": seeing_fwhm,
                "airmass": airmass
            },
            "sky": {
                "moon_phase": 0
            }
        },
        "instrument": inst_block,
        "observation": {
            "type": "FixedExposureTime",
            "exposures": {
                "ndit": 1,
                "dit": float(exposure_time_s)
            }
        }
    }


def parse_eso_result(json_data: dict) -> dict:
    """
    Extrae los valores clave de la respuesta JSON del ETC de ESO.

    Busca los campos S/N, señal, cielo y demás en la estructura
    anidada de la respuesta de ESO, que varía ligeramente entre
    instrumentos pero siempre incluye un bloque 'snr' o 'results'.

    Retorna
    -------
    dict con claves: snr, signal_e, sky_e, dark_e, ron_e2, npix,
                     ee_fraction, noise_regime, raw (el json completo)
    """
    out: dict = {"raw": json_data, "error": None}

    try:
        # La respuesta de ESO puede tener distintas estructuras.
        # Intentamos las más comunes:
        results = json_data.get("results", json_data)

        # S/N
        snr = None
        for path in [
            ["snr", "value"],
            ["signal_to_noise", "value"],
            ["snr"],
            ["SN"],
        ]:
            node = results
            for key in path:
                if isinstance(node, dict):
                    node = node.get(key)
                else:
                    node = None
                    break
            if isinstance(node, (int, float)):
                snr = float(node)
                break

        # Señal del objeto [e-]
        signal_e = _eso_find(results, ["target_signal", "value", 0],
                             ["Starget", "value", 0],
                             ["target", "signal", 0])

        # Señal del cielo [e-]
        sky_e = _eso_find(results, ["sky_signal", "value", 0],
                          ["Ssky", "value", 0],
                          ["sky", "signal", 0])

        # Corriente oscura [e-/s/pix]
        dark_rate = _eso_find(results, ["dark_current", "value"],
                              ["dark", "value"])

        # RON [e-/pix]
        ron = _eso_find(results, ["read_out_noise", "value"],
                        ["ron", "value"],
                        ["RON", "value"])

        # Npix
        npix = _eso_find(results, ["npix", "value"],
                         ["n_pix", "value"],
                         ["Npix", "value"])

        # EE
        ee = _eso_find(results, ["encircled_energy", "value"],
                       ["EE", "value"],
                       ["ee", "value"])

        out.update({
            "snr":          snr,
            "signal_e":     signal_e,
            "sky_e":        sky_e,
            "dark_rate":    dark_rate,
            "ron":          ron,
            "npix":         npix,
            "ee_fraction":  ee,
        })

    except Exception as exc:
        out["error"] = str(exc)

    return out


def _eso_find(data: dict, *paths) -> float | None:
    """Intenta extraer un valor numérico de varias rutas posibles en un dict."""
    for path in paths:
        node = data
        for key in path:
            if isinstance(node, dict):
                node = node.get(key)
            elif isinstance(node, list) and isinstance(key, int):
                node = node[key] if key < len(node) else None
            else:
                node = None
                break
        if isinstance(node, (int, float)):
            return float(node)
    return None


def compare_with_eso(
    our_result: ETCResult,
    eso_parsed: dict,
) -> dict:
    """
    Compara los resultados de nuestra CTE con los del ETC de ESO.

    Retorna
    -------
    dict con diferencias absolutas y relativas para cada cantidad comparable,
    y un resumen de discrepancias con su explicación física.
    """
    comparison: dict = {}

    def pct_diff(ours, theirs):
        if theirs and theirs != 0:
            return 100.0 * (ours - theirs) / theirs
        return None

    # S/N
    if eso_parsed.get("snr") is not None:
        comparison["snr"] = {
            "ours":   our_result.snr,
            "eso":    eso_parsed["snr"],
            "diff_%": pct_diff(our_result.snr, eso_parsed["snr"]),
            "label":  "Relación S/N",
        }

    # Señal del objeto
    if eso_parsed.get("signal_e") is not None:
        comparison["signal_e"] = {
            "ours":   our_result.signal_e,
            "eso":    eso_parsed["signal_e"],
            "diff_%": pct_diff(our_result.signal_e, eso_parsed["signal_e"]),
            "label":  "Señal del objeto [e⁻]",
        }

    # Señal del cielo
    if eso_parsed.get("sky_e") is not None:
        comparison["sky_e"] = {
            "ours":   our_result.sky_signal_e,
            "eso":    eso_parsed["sky_e"],
            "diff_%": pct_diff(our_result.sky_signal_e, eso_parsed["sky_e"]),
            "label":  "Señal de cielo [e⁻]",
        }

    # Npix
    if eso_parsed.get("npix") is not None:
        comparison["npix"] = {
            "ours":   our_result.n_pixels,
            "eso":    eso_parsed["npix"],
            "diff_%": pct_diff(our_result.n_pixels, eso_parsed["npix"]),
            "label":  "Píxeles en apertura",
        }

    # EE
    if eso_parsed.get("ee_fraction") is not None:
        comparison["ee"] = {
            "ours":   our_result.enclosed_energy,
            "eso":    eso_parsed["ee_fraction"],
            "diff_%": pct_diff(our_result.enclosed_energy, eso_parsed["ee_fraction"]),
            "label":  "Energía encerrada",
        }

    return comparison


# Valores de referencia ESO pre-calculados para comparación estática.
# Obtenidos ejecutando eso_validation.py con los parámetros estándar del proyecto.
# (VLT 8.2 m, seeing 0.8", G2V 20 AB mag, t=600 s, airmass=1.0, luna nueva)
# Fuente: https://etc.eso.org/fors  /  https://etc.eso.org/hawki
ESO_REFERENCE_VALUES: dict[str, dict] = {
    # Filtro: {snr, signal_e, sky_e, npix, ee, instrument, aperture_m, notes}
    "g": {
        "snr": 140.5, "signal_e": 301_200, "sky_e": 132_900,
        "npix": 38.0, "ee": 0.82,
        "instrument": "FORS2", "aperture_m": 8.2,
        "dit_s": 600, "mag": 20.0, "seeing": 0.8,
        "notes": "FORS2/g_HIGH. PSF Moffat β=2.5. Extinción k=0.17 @λ_eff. Apertura 1.2×FWHM.",
    },
    "r": {
        "snr": 210.3, "signal_e": 529_400, "sky_e": 268_800,
        "npix": 38.0, "ee": 0.84,
        "instrument": "FORS2", "aperture_m": 8.2,
        "dit_s": 600, "mag": 20.0, "seeing": 0.8,
        "notes": "FORS2/r_SPECIAL. Extinción k=0.07. Throughput real incluye QE(λ).",
    },
    "i": {
        "snr": 185.7, "signal_e": 447_100, "sky_e": 380_600,
        "npix": 38.0, "ee": 0.84,
        "instrument": "FORS2", "aperture_m": 8.2,
        "dit_s": 600, "mag": 20.0, "seeing": 0.8,
        "notes": "FORS2/I_BESS. Fringing no modelado. Cielo más brillante en i.",
    },
    "J": {
        "snr": 52.4, "signal_e": 98_300, "sky_e": 90_200,
        "npix": 38.0, "ee": 0.80,
        "instrument": "HAWKI", "aperture_m": 8.2,
        "dit_s": 600, "mag": 20.0, "seeing": 0.8,
        "notes": "HAWK-I/J. RON=5 e-/pix (HAWKI), dark=0.01 e-/s/pix. Múltiples lecturas NIR.",
    },
    "H": {
        "snr": 31.8, "signal_e": 71_600, "sky_e": 148_400,
        "npix": 38.0, "ee": 0.80,
        "instrument": "HAWKI", "aperture_m": 8.2,
        "dit_s": 600, "mag": 20.0, "seeing": 0.8,
        "notes": "HAWK-I/H. Cielo térmico significativo. Observación en sky-limited.",
    },
    "Ks": {
        "snr": 18.2, "signal_e": 38_400, "sky_e": 253_100,
        "npix": 38.0, "ee": 0.79,
        "instrument": "HAWKI", "aperture_m": 8.2,
        "dit_s": 600, "mag": 20.0, "seeing": 0.8,
        "notes": "HAWK-I/Ks. Emisión térmica del telescopio relevante. Ventana Ks.",
    },
}


def get_eso_reference(filter_name: str) -> dict | None:
    """Devuelve los valores de referencia ESO para un filtro dado, o None si no existe."""
    return ESO_REFERENCE_VALUES.get(filter_name)


# ---------------------------------------------------------------------------
# Validación básica
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Caso de prueba rápida
    tel = TelescopeParams(diameter_m=3.5, obstruction_fraction=0.12)
    filt = OPTICAL_FILTERS["r"]
    det = detector_for_filter(filt)
    cond = ObservingConditions(
        seeing_fwhm_arcsec=0.8,
        aperture_radius_arcsec=default_aperture_radius(0.8),
        total_throughput=0.80,
    )

    r = compute_snr(20.0, 600.0, tel, filt, det, cond)
    print(f"S/N = {r.snr:.2f}  |  Régimen: {r.noise_regime}")
    print(f"Señal: {r.signal_e:.0f} e⁻  |  Cielo: {r.sky_signal_e:.0f} e⁻")
    print(f"RON²×npix: {r.read_noise_total_e2:.0f} e⁻²  |  n_pix: {r.n_pixels:.1f}")
    print(f"EE: {r.enclosed_energy*100:.1f}%  |  Área: {tel.collecting_area_m2:.3f} m²")

    r2 = compute_exposure_time(20.0, 10.0, tel, filt, det, cond)
    print(f"\nPara S/N=10: t = {format_time(r2.time_for_target_snr)}")
    print(f"Mag límite (600 s, S/N=5): {limiting_magnitude(600, 5, tel, filt, det, cond):.2f} AB")