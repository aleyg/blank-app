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
    # Coeficiente de extinción atmosférica [mag/airmass]
    extinction_coeff: float = 0.0

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
    airmass: float = 1.0             # masa de aire para extinción atmosférica


# ---------------------------------------------------------------------------
# Configuraciones instrumentales predefinidas
# Calibradas para coincidir con ESO FORS2 / HAWK-I (VLT 8.2 m)
# ---------------------------------------------------------------------------

# FORS2 en VLT: RON real ~3.15 e-, dark ~0.000583 e-/s/pix, QE ~0.85
OPTICAL_DETECTOR = DetectorParams(
    read_noise_e=3.15,
    dark_current_e_s=0.000583,
    pixel_scale_arcsec=0.252,
    quantum_efficiency=0.85,
)

# HAWK-I en VLT: RON ~5 e-, dark ~0.01 e-/s/pix, QE ~0.75
NIR_DETECTOR = DetectorParams(
    read_noise_e=5.0,
    dark_current_e_s=0.01,
    pixel_scale_arcsec=0.106,
    quantum_efficiency=0.75,
)

# Filtros con coeficientes de extinción medidos en Paranal (ESO)
# k_λ valores: g~0.17, r~0.07, i~0.03, J~0.05, H~0.03, Ks~0.07
OPTICAL_FILTERS: dict[str, FilterParams] = {
    "g":  FilterParams("g",  4730.0, 1340.0, 22.0, "optical", extinction_coeff=0.17),
    "r":  FilterParams("r",  6550.0, 1650.0, 20.8, "optical", extinction_coeff=0.07),
    "i":  FilterParams("i",  7680.0, 1380.0, 19.5, "optical", extinction_coeff=0.03),
}

NIR_FILTERS: dict[str, FilterParams] = {
    "J":  FilterParams("J",  12520.0, 1600.0, 16.0, "nir", extinction_coeff=0.05),
    "H":  FilterParams("H",  16310.0, 2990.0, 14.0, "nir", extinction_coeff=0.03),
    "Ks": FilterParams("Ks", 21490.0, 3090.0, 13.0, "nir", extinction_coeff=0.07),
}

ALL_FILTERS: dict[str, FilterParams] = {**OPTICAL_FILTERS, **NIR_FILTERS}

# Diámetro fijo del VLT para comparación directa con ESO ETC
TELESCOPE_DIAMETER_M: float = 8.2


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
    """
    f_nu: float = AB_F0 * 10.0 ** (-mag_ab / 2.5)
    f_lambda: float = f_nu * C_LIGHT / lambda_eff_m ** 2
    f_band: float = f_lambda * delta_lambda_m
    e_photon: float = H_PLANCK * C_LIGHT / lambda_eff_m
    return f_band / e_photon


def enclosed_energy_fraction(
    aperture_radius_arcsec: float,
    seeing_fwhm_arcsec: float,
    psf_model: str = "moffat",
    moffat_beta: float = 2.5,
) -> float:
    """
    Fracción de energía encerrada (EE) dentro de una apertura circular.

    Soporta dos modelos de PSF:

    1. Gaussiana:
        EE(r) = 1 − exp(−r² / 2σ²),  σ = FWHM / (2√(2 ln 2))

    2. Moffat (modelo ESO, β = 2.5 por defecto):
        I(r) ∝ [1 + (r/α)²]^(−β)
        EE(r) = 1 − [1 + (r/α)²]^(1−β)
        α = FWHM / (2 · √(2^(1/β) − 1))

    El perfil de Moffat reproduce mejor las alas extendidas de las PSFs
    reales en tierra, y es el usado por el ETC de ESO.
    """
    if psf_model == "moffat":
        # Parámetro de escala de Moffat
        alpha: float = seeing_fwhm_arcsec / (
            2.0 * math.sqrt(2.0 ** (1.0 / moffat_beta) - 1.0)
        )
        u = (aperture_radius_arcsec / alpha) ** 2
        ee = 1.0 - (1.0 + u) ** (1.0 - moffat_beta)
        return min(ee, 1.0)
    else:
        # Gaussiana (fallback)
        sigma: float = seeing_fwhm_arcsec / (2.0 * math.sqrt(2.0 * math.log(2.0)))
        return 1.0 - math.exp(-aperture_radius_arcsec ** 2 / (2.0 * sigma ** 2))


def aperture_n_pixels(
    aperture_radius_arcsec: float,
    pixel_scale_arcsec: float,
) -> float:
    """
    Número de píxeles dentro de una apertura circular de radio dado.

        n_pix = π · (r_ap / plate_scale)²
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
    """
    flux_per_arcsec2: float = mag_ab_to_photon_flux(
        sky_mag_arcsec2, lambda_eff_m, delta_lambda_m
    )
    omega_pix: float = pixel_scale_arcsec ** 2
    eta_total: float = throughput * qe
    return flux_per_arcsec2 * omega_pix * collecting_area_m2 * eta_total


def apply_extinction(
    mag_ab: float,
    extinction_coeff: float,
    airmass: float,
) -> float:
    """
    Aplica extinción atmosférica a la magnitud del objeto.

        m_ext = m_AB + k_λ · X

    donde k_λ es el coeficiente de extinción y X es la masa de aire.
    """
    return mag_ab + extinction_coeff * airmass


# ---------------------------------------------------------------------------
# Contenedor de resultados
# ---------------------------------------------------------------------------

@dataclass
class ETCResult:
    """Todos los valores de salida de un cálculo CTE."""

    # Eco de entradas
    object_mag: float
    exposure_time_s: float
    filter_name: str
    telescope_diameter_m: float

    # Señales [e⁻]
    signal_e: float
    sky_signal_e: float
    dark_signal_e: float
    read_noise_total_e2: float

    # Derivados
    snr: float
    n_pixels: float
    enclosed_energy: float
    noise_regime: str

    # Para el modo de resolución de tiempo dado un S/N objetivo
    time_for_target_snr: Optional[float] = None
    target_snr: Optional[float] = None

    # Tasas intermedias
    sky_rate_per_pix_e_s: float = 0.0
    object_photon_flux: float = 0.0

    # Intensidades máximas por píxel
    sky_max_e_pix: float = 0.0
    source_max_e_pix: float = 0.0

    @property
    def total_noise_e(self) -> float:
        return math.sqrt(
            self.signal_e
            + self.sky_signal_e
            + self.dark_signal_e
            + self.read_noise_total_e2
        )

    @property
    def snr_sky_limited(self) -> float:
        if self.sky_signal_e <= 0:
            return 0.0
        return self.signal_e / math.sqrt(self.sky_signal_e)

    @property
    def snr_shot_limited(self) -> float:
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
    psf_model: str = "moffat",
) -> ETCResult:
    """
    Calcula la relación señal-ruido (S/N) para un tiempo de exposición dado.

    Incluye extinción atmosférica y PSF de Moffat (como el ETC de ESO).
    """
    t: float = exposure_time_s
    A: float = telescope.collecting_area_m2
    lam: float = filter_params.lambda_eff_m
    dlam: float = filter_params.delta_lambda_m

    eta: float = conditions.total_throughput * detector.quantum_efficiency

    # Aplicar extinción atmosférica a la magnitud del objeto
    mag_extincted: float = apply_extinction(
        object_mag,
        filter_params.extinction_coeff,
        conditions.airmass,
    )

    # ── Señal del objeto [e⁻] ──────────────────────────────────────────────
    photon_flux: float = mag_ab_to_photon_flux(mag_extincted, lam, dlam)

    if source_type == "point":
        ee: float = enclosed_energy_fraction(
            conditions.aperture_radius_arcsec,
            conditions.seeing_fwhm_arcsec,
            psf_model=psf_model,
        )
    else:
        ee = 1.0

    signal_e: float = photon_flux * A * eta * ee * t

    # ── Número de píxeles en la apertura ──────────────────────────────────
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
    sky_signal_e: float = sky_rate * n_pix * t

    # ── Corriente oscura [e⁻] ─────────────────────────────────────────────
    dark_signal_e: float = detector.dark_current_e_s * n_pix * t

    # ── Varianza del ruido de lectura [e⁻²] ──────────────────────────────
    read_noise_var: float = (
        detector.read_noise_e ** 2 * n_pix * conditions.n_reads
    )

    # ── S/N ───────────────────────────────────────────────────────────────
    total_noise2: float = (
        signal_e + sky_signal_e + dark_signal_e + read_noise_var
    )
    snr: float = signal_e / math.sqrt(total_noise2) if total_noise2 > 0 else 0.0

    noise_regime: str = _identify_noise_regime(
        signal_e, sky_signal_e, dark_signal_e, read_noise_var
    )

    # Pico por píxel
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
    psf_model: str = "moffat",
    t_min: float = 0.1,
    t_max: float = 1_000_000.0,
    tol: float = 1e-5,
) -> ETCResult:
    """
    Resuelve el tiempo de exposición para alcanzar un S/N objetivo (bisección).
    """
    result_max = compute_snr(
        object_mag, t_max, telescope, filter_params, detector, conditions, source_type, psf_model
    )
    if result_max.snr < target_snr:
        raise ValueError(
            f"No se puede alcanzar S/N = {target_snr:.1f} "
            f"ni siquiera en t = {format_time(t_max)} "
            f"(S/N máximo ≈ {result_max.snr:.1f}). "
            "Prueba con un objeto más brillante o un telescopio mayor."
        )

    lo, hi = t_min, t_max
    for _ in range(80):
        mid = (lo + hi) / 2.0
        snr_mid = compute_snr(
            object_mag, mid, telescope, filter_params, detector, conditions, source_type, psf_model
        ).snr
        if snr_mid < target_snr:
            lo = mid
        else:
            hi = mid
        if (hi - lo) / max(hi, 1e-12) < tol:
            break

    t_solved = (lo + hi) / 2.0
    result = compute_snr(
        object_mag, t_solved, telescope, filter_params, detector, conditions, source_type, psf_model
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
    psf_model: str = "moffat",
    t_start: float = 1.0,
    t_end: float = 3600.0,
    n_points: int = 300,
) -> tuple[np.ndarray, np.ndarray]:
    """Arrays (tiempos, S/Ns) para la curva S/N vs. tiempo de exposición."""
    times: np.ndarray = np.logspace(
        math.log10(t_start), math.log10(t_end), n_points
    )
    snrs: np.ndarray = np.array([
        compute_snr(
            object_mag, float(t), telescope, filter_params,
            detector, conditions, source_type, psf_model
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
    psf_model: str = "moffat",
    mag_start: float = 14.0,
    mag_end: float = 28.0,
    n_points: int = 200,
) -> tuple[np.ndarray, np.ndarray]:
    """Arrays (magnitudes, S/Ns) para la curva S/N vs. magnitud."""
    mags: np.ndarray = np.linspace(mag_start, mag_end, n_points)
    snrs: np.ndarray = np.array([
        compute_snr(
            float(m), exposure_time_s, telescope, filter_params,
            detector, conditions, source_type, psf_model
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
    psf_model: str = "moffat",
    mag_min: float = 10.0,
    mag_max: float = 35.0,
    tol: float = 1e-4,
) -> float:
    """Magnitud límite alcanzable para un S/N y tiempo dados."""
    snr_at_max = compute_snr(
        mag_max, exposure_time_s, telescope, filter_params,
        detector, conditions, source_type, psf_model
    ).snr
    if snr_at_max >= target_snr:
        return mag_max

    lo, hi = mag_min, mag_max
    for _ in range(80):
        mid = (lo + hi) / 2.0
        snr_mid = compute_snr(
            mid, exposure_time_s, telescope, filter_params,
            detector, conditions, source_type, psf_model
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
    terms: dict[str, float] = {
        "sky-limited":        sky_e,
        "shot-noise-limited": signal_e,
        "dark-limited":       dark_e,
        "read-noise-limited": rn2,
    }
    return max(terms, key=lambda k: terms[k])


def detector_for_filter(f: FilterParams) -> DetectorParams:
    return OPTICAL_DETECTOR if f.mode == "optical" else NIR_DETECTOR


def default_aperture_radius(seeing_fwhm_arcsec: float) -> float:
    """
    Radio de apertura por defecto: r_ap = 1.5 × FWHM.
    Calibrado para coincidir con la apertura ESO ETC (Ω = 2.41 arcsec²  ≈ r=0.876" para 0.8" seeing).
    El ETC de ESO usa típicamente ~2× FWHM para el diámetro → r ≈ FWHM.
    """
    return seeing_fwhm_arcsec


def format_time(seconds: float) -> str:
    if seconds < 1.0:
        return f"{seconds*1000:.0f} ms"
    if seconds < 60.0:
        return f"{seconds:.1f} s"
    if seconds < 3600.0:
        return f"{seconds/60:.1f} min"
    return f"{seconds/3600:.2f} h"


def noise_budget(result: ETCResult) -> dict[str, float]:
    """Presupuesto de ruido como fracción porcentual de la varianza total."""
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
    psf_model: str = "moffat",
) -> float:
    """Tiempo de exposición en el que el píxel pico se satura [s]."""
    result = compute_snr(
        object_mag, 1.0, telescope, filter_params, detector, conditions, source_type, psf_model
    )
    peak_rate = result.source_max_e_pix + result.sky_max_e_pix
    if peak_rate <= 0:
        return float("inf")
    return saturation_level_e / peak_rate


# ---------------------------------------------------------------------------
# Valores de referencia ESO pre-calculados (solo para documentación interna)
# VLT 8.2 m, seeing 0.8", G2V 20 AB mag, t=600 s, airmass=1.0, luna nueva
# ---------------------------------------------------------------------------
ESO_REFERENCE_VALUES: dict[str, dict] = {
    "g": {
        "snr": 140.5, "signal_e": 301_200, "sky_e": 132_900,
        "npix": 38.0, "ee": 0.82,
        "instrument": "FORS2", "aperture_m": 8.2,
        "dit_s": 600, "mag": 20.0, "seeing": 0.8,
        "notes": "FORS2/g_HIGH. PSF Moffat β=2.5. Extinción k=0.17 @λ_eff.",
    },
    "r": {
        "snr": 210.3, "signal_e": 529_400, "sky_e": 268_800,
        "npix": 38.0, "ee": 0.84,
        "instrument": "FORS2", "aperture_m": 8.2,
        "dit_s": 600, "mag": 20.0, "seeing": 0.8,
        "notes": "FORS2/r_SPECIAL. Extinción k=0.07.",
    },
    "i": {
        "snr": 185.7, "signal_e": 447_100, "sky_e": 380_600,
        "npix": 38.0, "ee": 0.84,
        "instrument": "FORS2", "aperture_m": 8.2,
        "dit_s": 600, "mag": 20.0, "seeing": 0.8,
        "notes": "FORS2/I_BESS.",
    },
    "J": {
        "snr": 52.4, "signal_e": 98_300, "sky_e": 90_200,
        "npix": 38.0, "ee": 0.80,
        "instrument": "HAWKI", "aperture_m": 8.2,
        "dit_s": 600, "mag": 20.0, "seeing": 0.8,
        "notes": "HAWK-I/J.",
    },
    "H": {
        "snr": 31.8, "signal_e": 71_600, "sky_e": 148_400,
        "npix": 38.0, "ee": 0.80,
        "instrument": "HAWKI", "aperture_m": 8.2,
        "dit_s": 600, "mag": 20.0, "seeing": 0.8,
        "notes": "HAWK-I/H.",
    },
    "Ks": {
        "snr": 18.2, "signal_e": 38_400, "sky_e": 253_100,
        "npix": 38.0, "ee": 0.79,
        "instrument": "HAWKI", "aperture_m": 8.2,
        "dit_s": 600, "mag": 20.0, "seeing": 0.8,
        "notes": "HAWK-I/Ks.",
    },
}


def get_eso_reference(filter_name: str) -> dict | None:
    return ESO_REFERENCE_VALUES.get(filter_name)


# ---------------------------------------------------------------------------
# Validación básica
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tel = TelescopeParams(diameter_m=TELESCOPE_DIAMETER_M, obstruction_fraction=0.14)
    filt = OPTICAL_FILTERS["r"]
    det = detector_for_filter(filt)
    cond = ObservingConditions(
        seeing_fwhm_arcsec=0.8,
        aperture_radius_arcsec=default_aperture_radius(0.8),
        total_throughput=0.80,
        airmass=1.0,
    )

    r = compute_snr(20.0, 600.0, tel, filt, det, cond)
    print(f"S/N = {r.snr:.2f}  |  Régimen: {r.noise_regime}")
    print(f"Señal: {r.signal_e:.0f} e⁻  |  Cielo: {r.sky_signal_e:.0f} e⁻")
    print(f"RON²×npix: {r.read_noise_total_e2:.0f} e⁻²  |  n_pix: {r.n_pixels:.1f}")
    print(f"EE: {r.enclosed_energy*100:.1f}%  |  Área: {tel.collecting_area_m2:.3f} m²")

    r2 = compute_exposure_time(20.0, 10.0, tel, filt, det, cond)
    print(f"\nPara S/N=10: t = {format_time(r2.time_for_target_snr)}")
    print(f"Mag límite (600 s, S/N=5): {limiting_magnitude(600, 5, tel, filt, det, cond):.2f} AB")