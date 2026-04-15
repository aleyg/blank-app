"""
backend.py — Exposure Time Calculator (ETC) — Scientific Core
==============================================================
All functions are pure (no side-effects, no I/O) and return plain Python
objects so they can be called from any frontend (Streamlit, Flask, CLI …).

Physical model
--------------
S/N = S / sqrt(S + N_sky + N_dark + N_read²·n_pix)

where
  S        = object signal  [e⁻]
  N_sky    = sky background signal  [e⁻]
  N_dark   = dark-current signal  [e⁻]
  N_read²  = read-noise variance per pixel  [e⁻²]
  n_pix    = number of pixels in the aperture

References: ESO FORS ETC white-paper; Howell (2006) "Handbook of CCD Astronomy"
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
H_PLANCK = 6.626e-34   # J·s
C_LIGHT  = 3.0e8       # m/s
AB_F0    = 3.631e-23   # W/m²/Hz  (AB zero-point flux density)

# ---------------------------------------------------------------------------
# Data classes (parameter containers)
# ---------------------------------------------------------------------------

@dataclass
class TelescopeParams:
    """Primary mirror diameter and central obstruction."""
    diameter_m: float          # primary mirror [m]
    obstruction_fraction: float = 0.12   # linear fraction of diameter

    @property
    def collecting_area_m2(self) -> float:
        """Effective collecting area [m²]."""
        r_outer = self.diameter_m / 2.0
        r_inner = r_outer * self.obstruction_fraction
        return math.pi * (r_outer**2 - r_inner**2)


@dataclass
class FilterParams:
    """Photometric band definition."""
    name: str
    lambda_eff_angstrom: float   # effective wavelength [Å]
    delta_lambda_angstrom: float # bandwidth [Å]
    sky_mag_arcsec2: float       # sky surface brightness [AB mag/arcsec²]
    mode: Literal["optical", "nir"] = "optical"

    @property
    def lambda_eff_m(self) -> float:
        return self.lambda_eff_angstrom * 1e-10

    @property
    def delta_lambda_m(self) -> float:
        return self.delta_lambda_angstrom * 1e-10


@dataclass
class DetectorParams:
    """CCD / IR-array detector characteristics."""
    read_noise_e: float       # [e⁻/pix/read]
    dark_current_e_s: float   # [e⁻/pix/s]
    pixel_scale_arcsec: float # [arcsec/pix]
    quantum_efficiency: float # dimensionless [0–1]


@dataclass
class ObservingConditions:
    """Atmospheric and observational parameters."""
    seeing_fwhm_arcsec: float  # FWHM of the PSF [arcsec]
    aperture_radius_arcsec: float  # photometric aperture radius [arcsec]
    total_throughput: float = 0.80  # telescope + optics + filter transmission [0–1]
    n_reads: int = 1  # number of detector reads (for up-the-ramp in NIR, etc.)


# ---------------------------------------------------------------------------
# Pre-defined instrument configurations
# (easily extended by adding entries to these dicts)
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
    "g": FilterParams("g", 4800, 1400, 22.0, "optical"),
    "r": FilterParams("r", 6200, 1300, 20.8, "optical"),
    "i": FilterParams("i", 7600, 1500, 19.5, "optical"),
}

NIR_FILTERS: dict[str, FilterParams] = {
    "J":  FilterParams("J",  12500, 2600, 16.0, "nir"),
    "H":  FilterParams("H",  16500, 3000, 14.0, "nir"),
    "Ks": FilterParams("Ks", 22000, 3500, 13.0, "nir"),
}

ALL_FILTERS: dict[str, FilterParams] = {**OPTICAL_FILTERS, **NIR_FILTERS}


# ---------------------------------------------------------------------------
# Core physics functions
# ---------------------------------------------------------------------------

def mag_ab_to_photon_flux(mag_ab: float, lambda_eff_m: float,
                           delta_lambda_m: float) -> float:
    """
    Convert AB magnitude to photon flux [photons/s/m²].

    F_nu(AB) = 10^(-(mag+48.6)/2.5)  [erg/s/cm²/Hz]  →  SI  →  photon flux.

    Parameters
    ----------
    mag_ab          : AB magnitude of the source
    lambda_eff_m    : effective wavelength [m]
    delta_lambda_m  : filter bandwidth [m]

    Returns
    -------
    Photon flux [photons / s / m²]
    """
    # AB flux density in W/m²/Hz
    f_nu = AB_F0 * 10.0 ** (-(mag_ab) / 2.5)          # W/m²/Hz

    # Convert F_nu → F_lambda  [W/m²/m]
    f_lambda = f_nu * C_LIGHT / lambda_eff_m**2

    # Integrated flux in band  [W/m²]
    f_band = f_lambda * delta_lambda_m

    # Energy per photon  [J]
    e_photon = H_PLANCK * C_LIGHT / lambda_eff_m

    return f_band / e_photon   # photons / s / m²


def enclosed_energy_fraction(aperture_radius_arcsec: float,
                              seeing_fwhm_arcsec: float) -> float:
    """
    Fraction of light from a point source enclosed within a circular aperture,
    assuming a Gaussian PSF.

    EE(r) = 1 − exp(−r² / (2·σ²))
    σ = FWHM / (2·sqrt(2·ln2))
    """
    sigma = seeing_fwhm_arcsec / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    return 1.0 - math.exp(-aperture_radius_arcsec**2 / (2.0 * sigma**2))


def aperture_n_pixels(aperture_radius_arcsec: float,
                      pixel_scale_arcsec: float) -> float:
    """
    Number of pixels inside a circular aperture of given radius.
    n_pix = π · (r/plate_scale)²
    """
    r_pix = aperture_radius_arcsec / pixel_scale_arcsec
    return math.pi * r_pix**2


def sky_photon_rate(sky_mag_arcsec2: float,
                    lambda_eff_m: float,
                    delta_lambda_m: float,
                    collecting_area_m2: float,
                    throughput: float,
                    qe: float,
                    pixel_scale_arcsec: float) -> float:
    """
    Sky background electron rate per pixel [e⁻/s/pix].

    Converts sky surface brightness (mag/arcsec²) to a per-pixel rate.
    """
    flux_per_arcsec2 = mag_ab_to_photon_flux(sky_mag_arcsec2, lambda_eff_m,
                                              delta_lambda_m)
    pixel_area_arcsec2 = pixel_scale_arcsec**2
    return flux_per_arcsec2 * pixel_area_arcsec2 * collecting_area_m2 * throughput * qe


# ---------------------------------------------------------------------------
# Main calculation result
# ---------------------------------------------------------------------------

@dataclass
class ETCResult:
    """All outputs from a single ETC computation."""
    # Input echo (for display)
    object_mag: float
    exposure_time_s: float
    filter_name: str
    telescope_diameter_m: float

    # Signals [e⁻]
    signal_e: float
    sky_signal_e: float
    dark_signal_e: float
    read_noise_total_e2: float   # variance term: RON² × n_pix × n_reads

    # Derived
    snr: float
    n_pixels: float
    enclosed_energy: float
    noise_regime: str            # "sky-limited", "read-noise-limited", "dark-limited", "shot-noise-limited"

    # For solving t given S/N
    time_for_target_snr: float | None = None
    target_snr: float | None = None


# ---------------------------------------------------------------------------
# ETC engine
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
    Compute S/N for a given exposure time.

    Parameters
    ----------
    object_mag      : AB magnitude of the target
    exposure_time_s : integration time [s]
    telescope       : TelescopeParams instance
    filter_params   : FilterParams instance
    detector        : DetectorParams instance
    conditions      : ObservingConditions instance
    source_type     : 'point' or 'extended' (extended disables EE correction)

    Returns
    -------
    ETCResult
    """
    t = exposure_time_s
    A = telescope.collecting_area_m2
    lam = filter_params.lambda_eff_m
    dlam = filter_params.delta_lambda_m
    eta = conditions.total_throughput * detector.quantum_efficiency

    # --- Object signal [e⁻] ---
    photon_flux = mag_ab_to_photon_flux(object_mag, lam, dlam)  # ph/s/m²

    if source_type == "point":
        ee = enclosed_energy_fraction(conditions.aperture_radius_arcsec,
                                      conditions.seeing_fwhm_arcsec)
    else:
        # Extended: aperture collects all surface brightness within aperture area
        # EE fraction = 1 (no PSF concentration correction)
        ee = 1.0

    signal_e = photon_flux * A * eta * ee * t   # e⁻

    # --- Number of pixels in aperture ---
    n_pix = aperture_n_pixels(conditions.aperture_radius_arcsec,
                               detector.pixel_scale_arcsec)

    # --- Sky background [e⁻] ---
    sky_rate_per_pix = sky_photon_rate(
        filter_params.sky_mag_arcsec2, lam, dlam, A,
        conditions.total_throughput, detector.quantum_efficiency,
        detector.pixel_scale_arcsec,
    )
    sky_signal_e = sky_rate_per_pix * n_pix * t   # e⁻

    # --- Dark current [e⁻] ---
    dark_signal_e = detector.dark_current_e_s * n_pix * t   # e⁻

    # --- Read noise variance [e⁻²] ---
    read_noise_var = (detector.read_noise_e**2) * n_pix * conditions.n_reads

    # --- Total noise² ---
    total_noise2 = signal_e + sky_signal_e + dark_signal_e + read_noise_var

    # --- S/N ---
    snr = signal_e / math.sqrt(total_noise2) if total_noise2 > 0 else 0.0

    # --- Noise regime identification ---
    noise_regime = _identify_noise_regime(signal_e, sky_signal_e,
                                           dark_signal_e, read_noise_var)

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
    t_max: float = 1e6,
    tol: float = 1e-4,
) -> ETCResult:
    """
    Solve for the exposure time needed to reach a target S/N via bisection.

    Returns an ETCResult evaluated at the solved time, with
    ``time_for_target_snr`` and ``target_snr`` populated.
    """
    # Validate that t_max is sufficient
    result_max = compute_snr(object_mag, t_max, telescope, filter_params,
                              detector, conditions, source_type)
    if result_max.snr < target_snr:
        raise ValueError(
            f"Cannot reach S/N={target_snr:.1f} even at t={t_max:.0f} s "
            f"(max achievable S/N ≈ {result_max.snr:.1f}). "
            "Try a brighter object or a larger telescope."
        )

    # Bisection
    lo, hi = t_min, t_max
    for _ in range(60):
        mid = (lo + hi) / 2.0
        snr_mid = compute_snr(object_mag, mid, telescope, filter_params,
                               detector, conditions, source_type).snr
        if snr_mid < target_snr:
            lo = mid
        else:
            hi = mid
        if (hi - lo) / max(hi, 1e-9) < tol:
            break

    t_solved = (lo + hi) / 2.0
    result = compute_snr(object_mag, t_solved, telescope, filter_params,
                          detector, conditions, source_type)
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
    n_points: int = 200,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Return arrays (times, snrs) for plotting S/N vs. exposure time.
    """
    times = np.logspace(math.log10(t_start), math.log10(t_end), n_points)
    snrs = np.array([
        compute_snr(object_mag, float(t), telescope, filter_params,
                    detector, conditions, source_type).snr
        for t in times
    ])
    return times, snrs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _identify_noise_regime(signal_e: float, sky_e: float,
                             dark_e: float, rn2: float) -> str:
    """Return a string label for the dominant noise source."""
    terms = {
        "sky-limited":        sky_e,
        "shot-noise-limited": signal_e,
        "dark-limited":       dark_e,
        "read-noise-limited": rn2,
    }
    return max(terms, key=terms.get)


def detector_for_filter(f: FilterParams) -> DetectorParams:
    """Return the standard detector matching the filter mode."""
    return OPTICAL_DETECTOR if f.mode == "optical" else NIR_DETECTOR


def format_time(seconds: float) -> str:
    """Human-readable exposure time string."""
    if seconds < 60:
        return f"{seconds:.1f} s"
    if seconds < 3600:
        return f"{seconds/60:.1f} min"
    return f"{seconds/3600:.2f} h"
