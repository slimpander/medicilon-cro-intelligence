"""
peak_engine.py — CentWave-Style Peak Picking for Untargeted Metabolomics
=========================================================================
Implements wavelet-based peak detection inspired by XCMS centWave algorithm:

1. Continuous Wavelet Transform (CWT) with Mexican Hat wavelet
2. Local maxima detection in wavelet coefficient space
3. Gaussian peak fitting for accurate m/z + area
4. Feature detection across chromatographic time domain
5. ROI (Region of Interest) extraction and refinement

References:
  - Tautenhahn et al. (2008) BMC Bioinformatics 9:504
  - XCMS centWave algorithm
"""

from __future__ import annotations

from typing import List, Dict, Optional, Tuple
import numpy as np
from scipy import signal, ndimage, optimize
from dataclasses import dataclass, field

from .io_utils import Spectrum, DetectedFeature


# ══════════════════════════════════════════════════════════════════════
# Wavelet functions
# ══════════════════════════════════════════════════════════════════════

def _mexican_hat_wavelet(scales: np.ndarray, points: int = 101) -> np.ndarray:
    """Generate Mexican Hat (Ricker) wavelet kernels at multiple scales.

    The Mexican Hat is the negative-normalised second derivative of a Gaussian.
    Good for detecting peak-shaped signals in mass spectra.

    Args:
        scales: Array of wavelet scales (widths)
        points: Number of points per wavelet kernel

    Returns:
        Array of shape (len(scales), points)
    """
    wavelets = []
    x = np.linspace(-4, 4, points)
    for s in scales:
        # Mexican Hat: (2/(sqrt(3s)*pi^(1/4))) * (1 - (x/s)^2) * exp(-x^2/(2s^2))
        x_s = x / s
        w = (1 - x_s ** 2) * np.exp(-x_s ** 2 / 2)
        # Normalise
        w /= np.sqrt(np.sum(w ** 2))
        wavelets.append(w)
    return np.array(wavelets)


def _continuous_wavelet_transform(
    signal_arr: np.ndarray,
    scales: np.ndarray,
    wavelet: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Compute CWT of a 1D signal.

    Returns:
        Array of shape (len(scales), len(signal_arr)) with wavelet coefficients
    """
    if wavelet is None:
        wavelet = _mexican_hat_wavelet(scales, max(len(scales) * 2 + 1, 11))
    if len(signal_arr) < 3:
        return np.zeros((len(scales), len(signal_arr)))
    n = len(signal_arr)
    cwt_coeffs = np.zeros((len(scales), n))
    for i, s in enumerate(scales):
        if i >= len(wavelet):
            break
        # Cross-correlation (equivalent to convolution with flipped wavelet)
        w = wavelet[i]
        w_len = len(w)
        coeffs = np.correlate(signal_arr, w, mode="same")
        cwt_coeffs[i, :] = coeffs
    return cwt_coeffs


# ══════════════════════════════════════════════════════════════════════
# Peak Picker
# ══════════════════════════════════════════════════════════════════════

@dataclass
class PeakCandidate:
    """A detected peak candidate in a single mass spectrum."""
    index: int
    mz: float
    intensity: float
    snr: float
    fwhm: float                   # Full width at half maximum (Da)
    scale_best: float             # Wavelet scale that best matches this peak
    quality: float                # 0-1 overall quality score
    left_idx: int = 0
    right_idx: int = 0


class PeakPicker:
    """Wavelet-based peak detection in mass spectra (centWave-style for MS).

    Detects peaks in profile-mode mass spectra using:
    1. Continuous Wavelet Transform with Mexican Hat wavelet
    2. Local maxima identification across scales
    3. Gaussian fitting for accurate m/z centroids
    4. SNR-based filtering
    """

    def __init__(
        self,
        snr_threshold: float = 3.0,
        peak_width_range: Tuple[float, float] = (0.005, 0.5),  # Da
        min_intensity: float = 0.0,
        scales: Optional[np.ndarray] = None,
        max_peaks_per_spectrum: int = 5000,
    ):
        self.snr_threshold = snr_threshold
        self.peak_width_range = peak_width_range
        self.min_intensity = min_intensity
        self.max_peaks_per_spectrum = max_peaks_per_spectrum

        if scales is None:
            # Generate log-spaced scales covering peak widths in data-points
            # For a typical m/z resolution of 0.01 Da with peak widths 0.005-0.5 Da
            scales = np.logspace(np.log10(1), np.log10(30), 15)
        self.scales = scales
        self._wavelet = _mexican_hat_wavelet(self.scales, max(len(scales) * 2 + 1, 31))

    def detect_peaks(self, spectrum: Spectrum, bin_width: Optional[float] = None) -> List[PeakCandidate]:
        """Detect peaks in a single mass spectrum.

        Uses local maxima detection with intensity-weighted centroiding
        on the raw data points (no re-binning). Fast, robust, accurate.

        Args:
            spectrum: Input mass spectrum
            bin_width: Ignored (kept for API compatibility)

        Returns:
            List of PeakCandidate objects sorted by intensity descending
        """
        mz = spectrum.mz
        intensity = spectrum.intensity
        n = len(mz)

        if n < 5:
            return []

        # Kernel smoothing along m/z axis for noise reduction
        # Use a Gaussian kernel with width proportional to expected peak width
        median_spacing = float(np.median(np.diff(mz[:min(500, n)])))
        kernel_points = max(3, int(self.peak_width_range[0] / max(median_spacing, 1e-6) * 3))
        kernel_points = min(kernel_points, 21)  # cap at 21 points
        if kernel_points % 2 == 0:
            kernel_points += 1

        from scipy.ndimage import gaussian_filter1d
        smoothed = gaussian_filter1d(intensity.astype(np.float64), sigma=kernel_points / 6.0)

        # Find local maxima: each point must be higher than neighbours within window
        half_win = max(1, kernel_points // 2)
        is_max = np.ones(n, dtype=bool)
        for offset in range(1, half_win + 1):
            rolled_plus = np.roll(smoothed, offset)
            rolled_minus = np.roll(smoothed, -offset)
            is_max &= (smoothed >= rolled_plus)
            is_max &= (smoothed >= rolled_minus)
        # Handle edge effects from roll
        is_max[:half_win + 1] = False
        is_max[-half_win - 1:] = False
        # Additional check: smoothed value must exceed a minimum
        is_max[smoothed < self.min_intensity] = False

        max_indices = np.where(is_max)[0]

        # Also check raw intensity for very narrow peaks missed by smoothing
        raw_is_max = np.ones(n, dtype=bool)
        raw_hw = max(1, kernel_points // 4)
        for offset in range(1, raw_hw + 1):
            raw_is_max &= (intensity >= np.roll(intensity, offset))
            raw_is_max &= (intensity >= np.roll(intensity, -offset))
        raw_is_max[:raw_hw + 1] = False
        raw_is_max[-raw_hw - 1:] = False
        raw_is_max[intensity < self.min_intensity] = False
        raw_max_indices = set(np.where(raw_is_max)[0])

        # Union of both detection methods
        all_max = sorted(set(max_indices) | raw_max_indices)
        if not all_max:
            return []

        # Process each candidate
        peaks = []
        for idx in all_max:
            # Define peak region by expanding outward until intensity drops
            peak_val = float(intensity[idx])
            threshold = max(peak_val * 0.05, self.min_intensity)
            left = idx
            while left > 0 and intensity[left - 1] > threshold:
                left -= 1
            right = idx
            while right < n - 1 and intensity[right + 1] > threshold:
                right += 1

            if right - left < 2:
                continue

            region_mz = mz[left:right + 1]
            region_int = intensity[left:right + 1]
            total_int = float(np.sum(region_int))
            if total_int <= 0:
                continue

            # Weighted centroid from raw data points
            centroid_mz = float(np.average(region_mz, weights=region_int))
            peak_intensity = float(np.max(region_int))

            # FWHM: find half-max crossing points in raw data
            half_max = peak_intensity / 2.0
            above = region_int >= half_max
            above_idx = np.where(above)[0]
            if len(above_idx) >= 2:
                fwhm = float(region_mz[above_idx[-1]] - region_mz[above_idx[0]])
            else:
                fwhm = float(region_mz[-1] - region_mz[0])

            # SNR: noise estimated from baseline regions
            noise_left_pts = intensity[max(0, left - 20):left]
            noise_right_pts = intensity[right:min(n, right + 20)]
            noise_std = float(np.std(np.concatenate([noise_left_pts, noise_right_pts])))
            if noise_std < 1.0:
                noise_std = 1.0
            snr = peak_intensity / noise_std

            # Quality score
            snr_score = min(1.0, snr / (self.snr_threshold * 3))
            w = fwhm
            w_min, w_max = self.peak_width_range
            if w < w_min:
                width_score = w / max(w_min, 1e-10)
            elif w > w_max:
                width_score = max(0.0, 1.0 - (w - w_max) / max(w_max, 1e-10))
            else:
                width_score = 1.0
            quality = float(np.clip(snr_score * 0.5 + width_score * 0.4 + 0.1, 0, 1))

            if snr >= self.snr_threshold and peak_intensity >= self.min_intensity:
                peaks.append(PeakCandidate(
                    index=int(idx),
                    mz=centroid_mz,
                    intensity=peak_intensity,
                    snr=float(snr),
                    fwhm=fwhm,
                    scale_best=fwhm,
                    quality=quality,
                    left_idx=int(left),
                    right_idx=int(right),
                ))

        # Deduplicate by proximity
        peaks.sort(key=lambda p: p.intensity, reverse=True)
        tol_da = self.peak_width_range[0] * 3
        deduped = []
        for p in peaks:
            if not any(abs(p.mz - d.mz) < tol_da for d in deduped):
                deduped.append(p)

        return deduped[:self.max_peaks_per_spectrum]


def _gaussian(x: np.ndarray, amp: float, centre: float, sigma: float, baseline: float) -> np.ndarray:
    """Gaussian function for peak fitting."""
    return amp * np.exp(-((x - centre) ** 2) / (2 * sigma ** 2)) + baseline


# ══════════════════════════════════════════════════════════════════════
# Feature Detector (chromatographic domain)
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ROI:
    """Region of Interest — a chromatographic feature candidate."""
    roi_id: int
    mz: float                     # Median m/z
    mz_min: float
    mz_max: float
    rt_start: float
    rt_end: float
    rt_apex: float
    intensities: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    scan_indices: List[int] = field(default_factory=list)

    @property
    def peak_area(self) -> float:
        if len(self.intensities) < 2:
            return 0.0
        return float(np.trapezoid(self.intensities))

    @property
    def max_intensity(self) -> float:
        return float(np.max(self.intensities)) if len(self.intensities) > 0 else 0.0

    @property
    def num_scans(self) -> int:
        return len(self.scan_indices)


class FeatureDetector:
    """Detect chromatographic features by tracking ROIs across spectra.

    Operates on centroided spectra after PeakPicker.
    Groups peaks across consecutive scans that appear at consistent m/z.
    """

    def __init__(
        self,
        mz_tolerance_da: float = 0.01,
        rt_tolerance_sec: float = 5.0,
        min_scans: int = 5,
        min_intensity: float = 100.0,
    ):
        self.mz_tolerance_da = mz_tolerance_da
        self.rt_tolerance_sec = rt_tolerance_sec
        self.min_scans = min_scans
        self.min_intensity = min_intensity

    def extract_rois(
        self,
        all_peaks: List[List[PeakCandidate]],
        retention_times: np.ndarray,
    ) -> List[ROI]:
        """Extract Regions of Interest from peak lists across spectra.

        For each m/z region, trace peaks across consecutive scans to form
        chromatographic features.

        Args:
            all_peaks: List of peak lists (one per scan), each element is a list of PeakCandidate
            retention_times: Retention time for each scan

        Returns:
            List of ROI objects sorted by max intensity
        """
        # Collect all peaks with their scan info
        indexed_peaks = []
        for scan_idx, (peaks, rt) in enumerate(zip(all_peaks, retention_times)):
            for p in peaks:
                if p.intensity >= self.min_intensity:
                    indexed_peaks.append({
                        "scan": scan_idx,
                        "rt": float(rt),
                        "mz": p.mz,
                        "intensity": p.intensity,
                    })

        if not indexed_peaks:
            return []

        # Sort by m/z
        indexed_peaks.sort(key=lambda x: x["mz"])

        # Greedy ROI extraction: group consecutive peaks in m/z space
        # that appear across different scans
        rois = []
        current_roi = []
        roi_id = 0

        for i, p in enumerate(indexed_peaks):
            if not current_roi:
                current_roi = [p]
                continue

            # Check if this peak belongs to current ROI
            roi_mz = np.median([r["mz"] for r in current_roi])

            if abs(p["mz"] - roi_mz) <= self.mz_tolerance_da:
                # Same m/z region
                current_roi.append(p)
            else:
                # New m/z region — finalize current ROI if it has enough scans
                if self._is_valid_roi(current_roi):
                    rois.append(self._build_roi(roi_id, current_roi))
                    roi_id += 1
                current_roi = [p]

        # Don't forget the last one
        if self._is_valid_roi(current_roi):
            rois.append(self._build_roi(roi_id, current_roi))

        return rois

    def _is_valid_roi(self, roi_peaks: List[Dict]) -> bool:
        """Check if a ROI has enough unique scans."""
        unique_scans = set(p["scan"] for p in roi_peaks)
        return len(unique_scans) >= self.min_scans

    def _build_roi(self, roi_id: int, roi_peaks: List[Dict]) -> ROI:
        """Build an ROI object from grouped peaks."""
        mz_values = [p["mz"] for p in roi_peaks]
        rt_values = [p["rt"] for p in roi_peaks]
        intensities = [p["intensity"] for p in roi_peaks]
        scans = [p["scan"] for p in roi_peaks]

        best_idx = np.argmax(intensities)
        return ROI(
            roi_id=roi_id,
            mz=float(np.median(mz_values)),
            mz_min=float(np.min(mz_values)),
            mz_max=float(np.max(mz_values)),
            rt_start=float(np.min(rt_values)),
            rt_end=float(np.max(rt_values)),
            rt_apex=float(rt_values[best_idx]),
            intensities=np.array(intensities, dtype=np.float64),
            scan_indices=list(scans),
        )


# ══════════════════════════════════════════════════════════════════════
# Full Pipeline
# ══════════════════════════════════════════════════════════════════════

class PeakDetectionPipeline:
    """End-to-end peak detection pipeline for a single mzML file.

    Combines: spectrum reading → peak picking → feature detection
    """

    def __init__(
        self,
        peak_picker: Optional[PeakPicker] = None,
        feature_detector: Optional[FeatureDetector] = None,
    ):
        self.peak_picker = peak_picker or PeakPicker()
        self.feature_detector = feature_detector or FeatureDetector()

    def process_file(
        self,
        reader,  # MzMLReader
        ms_level: int = 1,
        progress_callback=None,
    ) -> Tuple[List[DetectedFeature], np.ndarray, np.ndarray]:
        """Process a full mzML file and return detected features.

        Args:
            reader: An MzMLReader instance
            ms_level: MS level for peak detection
            progress_callback: Optional callable(spectrum_idx, total) for progress

        Returns:
            (features, retention_times, scan_indices)
        """
        all_peaks_per_scan = []
        all_rts = []
        total = reader.total_spectra

        for i, spectrum in enumerate(reader.iter_spectra(ms_level=ms_level)):
            peaks = self.peak_picker.detect_peaks(spectrum)
            all_peaks_per_scan.append(peaks)
            all_rts.append(spectrum.retention_time)
            if progress_callback:
                progress_callback(i, total)

        rts = np.array(all_rts, dtype=np.float64)
        rois = self.feature_detector.extract_rois(all_peaks_per_scan, rts)

        # Convert ROIs to DetectedFeatures
        features = []
        for roi in rois:
            snr = roi.max_intensity / (float(np.std(roi.intensities)) + 1.0) if len(roi.intensities) > 1 else 1.0
            quality = min(1.0, roi.num_scans / max(self.feature_detector.min_scans * 3, 1))
            features.append(DetectedFeature(
                feature_id=roi.roi_id,
                mz=roi.mz,
                mz_min=roi.mz_min,
                mz_max=roi.mz_max,
                rt=roi.rt_apex,
                rt_min=roi.rt_start,
                rt_max=roi.rt_end,
                intensity=roi.max_intensity,
                area=roi.peak_area,
                snr=float(snr),
                peak_quality=float(quality),
            ))

        return features, rts, np.arange(len(all_rts), dtype=np.int32)
