"""
backend.py — Calculadora de Tiempo de Exposición (CTE) — Núcleo Científico
===========================================================================
Modelo simplificado según enunciado del proyecto.

Simplificaciones explícitas (del enunciado):
    - PSF gaussiana perfecta (no Moffat)
    - Cielo uniforme y constante
    - Sin extinción atmosférica
    - Sin ruido de scintilación
    - Sin saturación del detector
    - Sin jittering NIR
    - Pixel scale fija 0.20"/pix
    - Transmisión total constante T = 0.80

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
from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Constantes físicas fundamentales
# ---------------------------------------------------------------------------
H_PLANCK: float = 6.62607015e-34   # J·s   (CODATA 2018)
C_LIGHT: float  = 2.99792458e8     # m/s   (exacto)
AB_F0: float    = 3.630780548e-23  # W/m²/Hz  (flujo cero AB, Oke & Gunn 1983)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TelescopeParams:
    """Parámetros del telescopio primario y obstrucción central."""
    diameter_m: float
    obstruction_fraction: float = 0.14

    @property
    def collecting_area_m2(self) -> float:
        """Área efectiva de recolección [m²]: A = π(r_out² − r_in²)"""
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
    # Coeficiente de extinción — definido pero NO usado en compute_snr
    # (el enunciado establece que la extinción atmosférica no se modela)
    extinction_coeff: float = 0.0

    @property
    def lambda_eff_m(self) -> float:
        return self.lambda_eff_angstrom * 1e-10

    @property
    def delta_lambda_m(self) -> float:
        return self.delta_lambda_angstrom * 1e-10

    @property
    def lambda_eff_um(self) -> float:
        return self.lambda_eff_angstrom * 1e-4


@dataclass
class DetectorParams:
    """Características del detector (CCD o array IR)."""
    read_noise_e: float        # ruido de lectura  [e⁻/pix/lectura]
    dark_current_e_s: float    # corriente oscura  [e⁻/pix/s]
    pixel_scale_arcsec: float  # escala de placa   [arcsec/pix]
    quantum_efficiency: float  # eficiencia cuántica (0–1)


@dataclass
class ObservingConditions:
    """Parámetros de observación."""
    seeing_fwhm_arcsec: float
    aperture_radius_arcsec: float
    # T = 0.80 según enunciado del proyecto (valor típico filtros banda ancha)
    total_throughput: float = 0.80
    n_reads: int = 1
    airmass: float = 1.0   # conservado como parámetro; sin efecto en cálculo principal


# ---------------------------------------------------------------------------
# Configuraciones instrumentales
# Pixel scale fija en 0.20"/pix según enunciado del proyecto.
# (FORS2 real usa 0.252"/pix SR; el enunciado especifica 0.20"/pix)
# ---------------------------------------------------------------------------

OPTICAL_DETECTOR = DetectorParams(
    read_noise_e=3.15,
    dark_current_e_s=0.000583,
    pixel_scale_arcsec=0.20,   # fijado por enunciado
    quantum_efficiency=0.85,
)

NIR_DETECTOR = DetectorParams(
    read_noise_e=5.0,
    dark_current_e_s=0.01,
    pixel_scale_arcsec=0.20,   # fijado por enunciado
    quantum_efficiency=0.75,
)

# Filtros del modelo simplificado.
# sky_mag: valores representativos de Paranal para cada banda.
# extinction_coeff: definido para referencia pero NO se aplica en compute_snr.
OPTICAL_FILTERS: dict[str, FilterParams] = {
    "g":  FilterParams("g",  4730.0, 1340.0, 22.0,  "optical", extinction_coeff=0.17),
    "r":  FilterParams("r",  6550.0, 1650.0, 20.8,  "optical", extinction_coeff=0.07),
    "i":  FilterParams("i",  7680.0, 1380.0, 19.5,  "optical", extinction_coeff=0.03),
}

NIR_FILTERS: dict[str, FilterParams] = {
    "J":  FilterParams("J",  12520.0, 1600.0, 16.0, "nir", extinction_coeff=0.05),
    "H":  FilterParams("H",  16310.0, 2990.0, 14.0, "nir", extinction_coeff=0.03),
    "Ks": FilterParams("Ks", 21490.0, 3090.0, 13.0, "nir", extinction_coeff=0.07),
}

ALL_FILTERS: dict[str, FilterParams] = {**OPTICAL_FILTERS, **NIR_FILTERS}

# Diámetro del telescopio según enunciado: 8 m
TELESCOPE_DIAMETER_M: float = 8.0


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

    1. F_ν = F₀_AB · 10^(−m / 2.5)               [W/m²/Hz]
    2. F_λ = F_ν · c / λ²                          [W/m²/m]
    3. F_banda = F_λ · Δλ                           [W/m²]
    4. E_fotón = h·c / λ                            [J]
    5. Φ = F_banda / E_fotón                        [ph/s/m²]
    """
    f_nu    = AB_F0 * 10.0 ** (-mag_ab / 2.5)
    f_lam   = f_nu * C_LIGHT / lambda_eff_m ** 2
    f_band  = f_lam * delta_lambda_m
    e_ph    = H_PLANCK * C_LIGHT / lambda_eff_m
    return f_band / e_ph


def enclosed_energy_fraction(
    aperture_radius_arcsec: float,
    seeing_fwhm_arcsec: float,
) -> float:
    """
    Fracción de energía encerrada (EE) — PSF gaussiana (según enunciado).

        σ = FWHM / (2√(2 ln 2))
        EE(r) = 1 − exp(−r² / 2σ²)

    Limitación: las PSFs reales tienen alas más extensas que una gaussiana.
    """
    sigma = seeing_fwhm_arcsec / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    return 1.0 - math.exp(-aperture_radius_arcsec ** 2 / (2.0 * sigma ** 2))


def aperture_n_pixels(
    aperture_radius_arcsec: float,
    pixel_scale_arcsec: float,
) -> float:
    """
    Número de píxeles en apertura circular:
        n_pix = π · (r_ap / s_pix)²
    """
    r_pix = aperture_radius_arcsec / pixel_scale_arcsec
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

        dot_N_sky = Φ(m_sky) · Ω_pix · A · η
    """
    flux   = mag_ab_to_photon_flux(sky_mag_arcsec2, lambda_eff_m, delta_lambda_m)
    omega  = pixel_scale_arcsec ** 2
    eta    = throughput * qe
    return flux * omega * collecting_area_m2 * eta


# ---------------------------------------------------------------------------
# Contenedor de resultados
# ---------------------------------------------------------------------------

@dataclass
class ETCResult:
    """Todos los valores de salida de un cálculo CTE."""
    object_mag: float
    exposure_time_s: float
    filter_name: str
    telescope_diameter_m: float

    signal_e: float
    sky_signal_e: float
    dark_signal_e: float
    read_noise_total_e2: float

    snr: float
    n_pixels: float
    enclosed_energy: float
    noise_regime: str

    time_for_target_snr: Optional[float] = None
    target_snr: Optional[float] = None

    sky_rate_per_pix_e_s: float = 0.0
    object_photon_flux: float = 0.0
    sky_max_e_pix: float = 0.0
    source_max_e_pix: float = 0.0

    @property
    def total_noise_e(self) -> float:
        return math.sqrt(
            self.signal_e + self.sky_signal_e
            + self.dark_signal_e + self.read_noise_total_e2
        )

    @property
    def snr_sky_limited(self) -> float:
        return self.signal_e / math.sqrt(self.sky_signal_e) if self.sky_signal_e > 0 else 0.0

    @property
    def snr_shot_limited(self) -> float:
        return math.sqrt(self.signal_e) if self.signal_e > 0 else 0.0


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
    psf_model: str = "gaussian",   # conservado para compatibilidad; siempre gaussiana
) -> ETCResult:
    """
    Calcula S/N para un tiempo de exposición dado.

    Simplificaciones del modelo (según enunciado):
    - PSF gaussiana perfecta
    - Sin extinción atmosférica (object_mag se usa directamente)
    - Cielo uniforme y constante
    - Sin ruido de scintilación
    - Sin saturación del detector
    - Pixel scale fija 0.20"/pix
    - Transmisión total constante T = 0.80
    """
    t   = exposure_time_s
    A   = telescope.collecting_area_m2
    lam = filter_params.lambda_eff_m
    dlam= filter_params.delta_lambda_m
    eta = conditions.total_throughput * detector.quantum_efficiency

    # ── Señal del objeto [e⁻] ─────────────────────────────────────────────
    # SIN extinción atmosférica (limitación explícita del enunciado)
    photon_flux = mag_ab_to_photon_flux(object_mag, lam, dlam)

    if source_type == "point":
        ee = enclosed_energy_fraction(
            conditions.aperture_radius_arcsec,
            conditions.seeing_fwhm_arcsec,
        )
    else:
        ee = 1.0

    signal_e = photon_flux * A * eta * ee * t

    # ── Número de píxeles ─────────────────────────────────────────────────
    n_pix = aperture_n_pixels(
        conditions.aperture_radius_arcsec,
        detector.pixel_scale_arcsec,
    )

    # ── Fondo de cielo [e⁻] ──────────────────────────────────────────────
    # Cielo uniforme y constante (limitación del enunciado)
    sky_rate = sky_electron_rate_per_pixel(
        filter_params.sky_mag_arcsec2,
        lam, dlam, A,
        conditions.total_throughput,
        detector.quantum_efficiency,
        detector.pixel_scale_arcsec,
    )
    sky_signal_e = sky_rate * n_pix * t

    # ── Corriente oscura [e⁻] ────────────────────────────────────────────
    dark_signal_e = detector.dark_current_e_s * n_pix * t

    # ── Varianza RON [e⁻²] ───────────────────────────────────────────────
    read_noise_var = detector.read_noise_e ** 2 * n_pix * conditions.n_reads

    # ── S/N ──────────────────────────────────────────────────────────────
    total_noise2 = signal_e + sky_signal_e + dark_signal_e + read_noise_var
    snr = signal_e / math.sqrt(total_noise2) if total_noise2 > 0 else 0.0

    noise_regime = _identify_noise_regime(signal_e, sky_signal_e, dark_signal_e, read_noise_var)

    # Fracción pico por píxel (gaussiana)
    sigma_pix = (conditions.seeing_fwhm_arcsec / detector.pixel_scale_arcsec) / (
        2.0 * math.sqrt(2.0 * math.log(2.0))
    )
    peak_fraction = (
        1.0 - math.exp(-0.5 / sigma_pix ** 2)
    ) if source_type == "point" else (1.0 / n_pix if n_pix > 0 else 0.0)
    source_max_e_pix = photon_flux * A * eta * peak_fraction * t

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
    psf_model: str = "gaussian",
    t_min: float = 0.1,
    t_max: float = 1_000_000.0,
    tol: float = 1e-5,
) -> ETCResult:
    """Bisección numérica para encontrar t tal que S/N(t) = target_snr."""
    result_max = compute_snr(object_mag, t_max, telescope, filter_params, detector, conditions, source_type)
    if result_max.snr < target_snr:
        raise ValueError(
            f"No se puede alcanzar S/N = {target_snr:.1f} "
            f"ni siquiera en t = {format_time(t_max)} "
            f"(S/N máximo ≈ {result_max.snr:.1f})."
        )
    lo, hi = t_min, t_max
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if compute_snr(object_mag, mid, telescope, filter_params, detector, conditions, source_type).snr < target_snr:
            lo = mid
        else:
            hi = mid
        if (hi - lo) / max(hi, 1e-12) < tol:
            break
    t_solved = (lo + hi) / 2.0
    result = compute_snr(object_mag, t_solved, telescope, filter_params, detector, conditions, source_type)
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
    psf_model: str = "gaussian",
    t_start: float = 1.0,
    t_end: float = 100_000.0,
    n_points: int = 300,
) -> tuple[np.ndarray, np.ndarray]:
    times = np.logspace(math.log10(t_start), math.log10(t_end), n_points)
    snrs  = np.array([
        compute_snr(object_mag, float(t), telescope, filter_params, detector, conditions, source_type).snr
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
    psf_model: str = "gaussian",
    mag_start: float = 14.0,
    mag_end: float = 28.0,
    n_points: int = 200,
) -> tuple[np.ndarray, np.ndarray]:
    mags = np.linspace(mag_start, mag_end, n_points)
    snrs = np.array([
        compute_snr(float(m), exposure_time_s, telescope, filter_params, detector, conditions, source_type).snr
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
    psf_model: str = "gaussian",
    mag_min: float = 10.0,
    mag_max: float = 35.0,
    tol: float = 1e-4,
) -> float:
    if compute_snr(mag_max, exposure_time_s, telescope, filter_params, detector, conditions, source_type).snr >= target_snr:
        return mag_max
    lo, hi = mag_min, mag_max
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if compute_snr(mid, exposure_time_s, telescope, filter_params, detector, conditions, source_type).snr > target_snr:
            lo = mid
        else:
            hi = mid
        if abs(hi - lo) < tol:
            break
    return (lo + hi) / 2.0


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------

def _identify_noise_regime(signal_e, sky_e, dark_e, rn2) -> str:
    terms = {
        "sky-limited":        sky_e,
        "shot-noise-limited": signal_e,
        "dark-limited":       dark_e,
        "read-noise-limited": rn2,
    }
    return max(terms, key=lambda k: terms[k])


def detector_for_filter(f: FilterParams) -> DetectorParams:
    return OPTICAL_DETECTOR if f.mode == "optical" else NIR_DETECTOR


def default_aperture_radius(seeing_fwhm_arcsec: float) -> float:
    """r_ap = FWHM (calibrado con apertura ESO ETC Ω ≈ 2.41 arcsec² para seeing 0.8")."""
    return seeing_fwhm_arcsec


def format_time(seconds: float) -> str:
    if seconds < 1.0:   return f"{seconds*1000:.0f} ms"
    if seconds < 60.0:  return f"{seconds:.1f} s"
    if seconds < 3600.0:return f"{seconds/60:.1f} min"
    return f"{seconds/3600:.2f} h"


def noise_budget(result: ETCResult) -> dict[str, float]:
    total_var = (result.signal_e + result.sky_signal_e
                 + result.dark_signal_e + result.read_noise_total_e2)
    if total_var == 0:
        return {"shot_noise": 0, "sky": 0, "dark": 0, "read_noise": 0, "total_var": 0}
    return {
        "shot_noise":  100.0 * result.signal_e            / total_var,
        "sky":         100.0 * result.sky_signal_e        / total_var,
        "dark":        100.0 * result.dark_signal_e       / total_var,
        "read_noise":  100.0 * result.read_noise_total_e2 / total_var,
        "total_var":   total_var,
    }


# ---------------------------------------------------------------------------
# Validación rápida
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tel  = TelescopeParams(diameter_m=TELESCOPE_DIAMETER_M)
    filt = OPTICAL_FILTERS["g"]
    det  = detector_for_filter(filt)
    cond = ObservingConditions(
        seeing_fwhm_arcsec=0.8,
        aperture_radius_arcsec=default_aperture_radius(0.8),
        total_throughput=0.80,
    )
    r = compute_snr(20.0, 60.0, tel, filt, det, cond)
    print(f"Filtro g · 20 AB · 60 s · D=8 m · T=0.80 · s=0.8\"")
    print(f"S/N = {r.snr:.2f}  |  Régimen: {r.noise_regime}")
    print(f"Señal: {r.signal_e:.0f} e⁻  |  Cielo: {r.sky_signal_e:.0f} e⁻")
    print(f"Npix: {r.n_pixels:.1f}  |  EE: {r.enclosed_energy*100:.1f}%")
    print(f"Área: {tel.collecting_area_m2:.3f} m²  |  Pixel: {det.pixel_scale_arcsec}\"/pix")