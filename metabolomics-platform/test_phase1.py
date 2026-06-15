"""
test_phase1.py — Full pipeline test with synthetic data.
Tests each module independently with controlled inputs.
"""

import sys, os
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))

from src.io_utils import Spectrum, FeatureTable, DetectedFeature, bin_spectrum, ppm_to_da, da_to_ppm
from src.peak_engine import PeakPicker, FeatureDetector, ROI, PeakDetectionPipeline
from src.alignment_engine import RTAligner, ConsensusBuilder, groupwise_alignment
from src.grouping_engine import DensityFeatureGrouper, GapFiller, compute_feature_quality


def make_gaussian_peak(mz: float, intensity: float, width_da: float = 0.01) -> tuple:
    """Create a small Gaussian peak at given m/z."""
    x = np.linspace(mz - 5 * width_da, mz + 5 * width_da, 21)
    y = intensity * np.exp(-((x - mz) ** 2) / (2 * width_da ** 2))
    return x, y


def make_synthetic_spectra(
    known_peaks: list,
    n_scans: int = 200,
    rt_per_scan: float = 1.0,
    chromatographic_width: float = 8.0,
) -> tuple:
    """Generate synthetic spectra with known chromatographic peaks.
    
    known_peaks: list of dicts with keys: name, mz, rt, intensity
    Returns: (all_spectra, retention_times)
    """
    spectra = []
    rts = []
    for scan_idx in range(n_scans):
        rt = scan_idx * rt_per_scan
        rts.append(rt)
        
        peaks_mz = []
        peaks_int = []
        
        for pk in known_peaks:
            rt_diff = rt - pk["rt"]
            intensity = pk["intensity"] * np.exp(-rt_diff ** 2 / (2 * chromatographic_width ** 2))
            if intensity > 100:
                # Add Gaussian shape around the peak m/z
                px, py = make_gaussian_peak(pk["mz"], intensity)
                peaks_mz.extend(px.tolist())
                peaks_int.extend(py.tolist())
        
        # Add noise
        for _ in range(200):
            noise_mz = np.random.uniform(100, 300)
            noise_int = np.random.exponential(300)
            peaks_mz.append(noise_mz)
            peaks_int.append(noise_int)
        
        # Sort by m/z
        order = np.argsort(peaks_mz)
        mz_arr = np.array([peaks_mz[i] for i in order], dtype=np.float64)
        int_arr = np.array([peaks_int[i] for i in order], dtype=np.float64)
        
        spec = Spectrum(
            index=scan_idx, ms_level=1, scan_number=scan_idx + 1,
            retention_time=rt, polarity="positive",
        )
        spec.mz = mz_arr
        spec.intensity = int_arr
        spec.total_ion_current = float(np.sum(int_arr))
        spectra.append(spec)
    
    return spectra, np.array(rts)


KNOWN_PEAKS = [
    {"name": "Caffeine",         "mz": 195.0877, "rt": 150, "intensity": 8e4},
    {"name": "Theobromine",      "mz": 181.0720, "rt": 120, "intensity": 7e4},
    {"name": "Acetaminophen",    "mz": 152.0570, "rt": 200, "intensity": 9e4},
    {"name": "4-Aminobenzoic",   "mz": 138.0550, "rt": 90,  "intensity": 5e4},
    {"name": "Paraxanthine",     "mz": 181.0725, "rt": 160, "intensity": 4e4},
    {"name": "Hippuric Acid",    "mz": 180.0655, "rt": 140, "intensity": 6e4},
]


def test_peak_picking():
    print("=" * 60)
    print("1. PEAK PICKING (centWave-style wavelet)")
    print("=" * 60)
    
    spectra, rts = make_synthetic_spectra(KNOWN_PEAKS, n_scans=200)
    print(f"   Generated {len(spectra)} spectra")
    print(f"   RT range: {rts[0]:.0f}–{rts[-1]:.0f}s")
    
    # Test on a single spectrum near caffeine apex
    scan_apex = 150
    spec = spectra[scan_apex]
    print(f"\n   Scan {scan_apex} @ RT={rts[scan_apex]:.0f}s: {len(spec.mz)} data points")
    
    picker = PeakPicker(snr_threshold=2.0, min_intensity=500)
    peaks = picker.detect_peaks(spec)
    print(f"   Peaks detected: {len(peaks)}")
    
    top = sorted(peaks, key=lambda p: p.intensity, reverse=True)[:8]
    print("   Top 8 peaks:")
    for p in top:
        print(f"      m/z={p.mz:.4f}  int={p.intensity:.0f}  SNR={p.snr:.1f}  Q={p.quality:.2f}  FWHM={p.fwhm:.4f}")
    
    # Check that caffeine was found
    caffeine_peaks = [p for p in peaks if abs(p.mz - 195.0877) < 0.02]
    assert len(caffeine_peaks) > 0, "FAIL: Caffeine peak not detected!"
    print(f"\n   Caffeine detected: m/z={caffeine_peaks[0].mz:.4f} (expected 195.0877)")
    
    # Check peak quality
    assert caffeine_peaks[0].quality > 0.5, f"FAIL: Caffeine quality too low ({caffeine_peaks[0].quality:.2f})"
    assert caffeine_peaks[0].snr > 3, f"FAIL: Caffeine SNR too low ({caffeine_peaks[0].snr:.1f})"
    
    return True


def test_feature_detection():
    print("\n" + "=" * 60)
    print("2. FEATURE DETECTION (chromatographic ROI)")
    print("=" * 60)
    
    spectra, rts = make_synthetic_spectra(KNOWN_PEAKS, n_scans=200)
    
    picker = PeakPicker(snr_threshold=2.0, min_intensity=500)
    all_peaks = [picker.detect_peaks(s) for s in spectra]
    total = sum(len(p) for p in all_peaks)
    print(f"   Total peaks across all scans: {total}")
    
    detector = FeatureDetector(mz_tolerance_da=0.02, min_scans=5, min_intensity=1000)
    rois = detector.extract_rois(all_peaks, rts)
    print(f"   ROIs extracted: {len(rois)}")
    
    top_rois = sorted(rois, key=lambda r: r.max_intensity, reverse=True)[:8]
    print("   Top ROIs:")
    for r in top_rois:
        print(f"      m/z={r.mz:.4f}  RT={r.rt_apex:.0f}s  Area={r.peak_area:.0f}  Scans={r.num_scans}")
    
    # Should have found at least 3 of the known peaks as ROIs
    roi_mzs = [r.mz for r in rois]
    found = 0
    for pk in KNOWN_PEAKS:
        matches = [m for m in roi_mzs if abs(m - pk["mz"]) < 0.02]
        if matches:
            found += 1
            print(f"   Found: {pk['name']} at m/z {matches[0]:.4f}")
    
    assert found >= 3, f"FAIL: Only {found}/6 known peaks found as ROIs"
    return True


def test_feature_grouping():
    print("\n" + "=" * 60)
    print("3. FEATURE GROUPING (density-based)")
    print("=" * 60)
    
    spectra, rts = make_synthetic_spectra(KNOWN_PEAKS, n_scans=200)
    picker = PeakPicker(snr_threshold=2.0, min_intensity=500)
    all_peaks = [picker.detect_peaks(s) for s in spectra]
    detector = FeatureDetector(mz_tolerance_da=0.02, min_scans=5, min_intensity=1000)
    rois = detector.extract_rois(all_peaks, rts)
    
    # Convert ROIs to DetectedFeatures
    features = []
    for roi in rois:
        features.append(DetectedFeature(
            feature_id=roi.roi_id, mz=roi.mz,
            mz_min=roi.mz_min, mz_max=roi.mz_max,
            rt=roi.rt_apex, rt_min=roi.rt_start, rt_max=roi.rt_end,
            intensity=roi.max_intensity, area=roi.peak_area,
            snr=5.0, peak_quality=0.8,
        ))
    
    print(f"   Base features: {len(features)}")
    
    # Simulate 3 technical replicates with small RT/mz shifts
    reps = []
    for rep_idx in range(3):
        rep_features = []
        for f in features:
            rep_features.append(DetectedFeature(
                feature_id=f.feature_id,
                mz=f.mz + np.random.uniform(-0.003, 0.003),
                mz_min=f.mz_min, mz_max=f.mz_max,
                rt=f.rt + np.random.uniform(-3, 3) * rep_idx,
                rt_min=f.rt_min, rt_max=f.rt_max,
                intensity=f.intensity * np.random.uniform(0.8, 1.2),
                area=f.area, snr=f.snr, peak_quality=f.peak_quality,
            ))
        reps.append(rep_features)
    
    grouper = DensityFeatureGrouper(mz_bandwidth_ppm=5.0, rt_bandwidth_sec=10.0, min_fraction=0.5)
    ft = grouper.group(reps, ["Rep1", "Rep2", "Rep3"])
    
    print(f"   Grouped features: {ft.num_features}")
    print(f"   Feature density: {np.count_nonzero(ft.intensity_matrix)}/{ft.intensity_matrix.size}")
    
    assert ft.num_features >= 3, f"FAIL: Only {ft.num_features} grouped features"
    assert ft.num_samples == 3, f"FAIL: Wrong number of samples ({ft.num_samples})"
    return True


def test_gap_filling():
    print("\n" + "=" * 60)
    print("4. GAP FILLING")
    print("=" * 60)
    
    # Create a simple feature table with known gaps
    matrix = np.array([
        [1000, 1100, 0],
        [500, 0, 520],
        [0, 800, 780],
        [300, 320, 0],
        [0, 0, 200],
    ], dtype=np.float64)
    
    ft = FeatureTable(
        sample_names=["S1", "S2", "S3"],
        feature_ids=np.arange(5),
        mz_values=np.array([100.0, 150.0, 200.0, 250.0, 300.0]),
        rt_values=np.array([50.0, 100.0, 150.0, 200.0, 250.0]),
        intensity_matrix=matrix,
    )
    
    print(f"   Original: {np.count_nonzero(matrix)}/15 values present")
    
    gf = GapFiller()
    
    # KNN fill
    ft_knn = gf.fill_by_knn(ft, k=3)
    filled_knn = np.count_nonzero(ft_knn.intensity_matrix)
    print(f"   After KNN fill (k=3): {filled_knn}/15 values present")
    
    # Minimum fill
    ft_min = gf.fill_by_minimum(ft, min_fraction=0.2)
    filled_min = np.count_nonzero(ft_min.intensity_matrix)
    print(f"   After minimum fill: {filled_min}/15 values present")
    
    assert filled_knn >= 10, f"FAIL: KNN fill only restored {filled_knn}/15 values"
    assert filled_min == 15, f"FAIL: Minimum fill should fill all values"
    
    # Quality scores
    quality = compute_feature_quality(ft_min)
    print(f"   Quality scores: {[f'{q:.2f}' for q in quality]}")
    assert np.max(quality) >= 0.5, f"FAIL: Best quality too low"
    return True


def test_alignment():
    print("\n" + "=" * 60)
    print("5. RT ALIGNMENT (landmark-based)")
    print("=" * 60)
    
    spectra, rts = make_synthetic_spectra(KNOWN_PEAKS, n_scans=200)
    picker = PeakPicker(snr_threshold=2.0, min_intensity=500)
    all_peaks = [picker.detect_peaks(s) for s in spectra]
    detector = FeatureDetector(mz_tolerance_da=0.02, min_scans=5, min_intensity=1000)
    rois = detector.extract_rois(all_peaks, rts)
    
    # Create 3 replicates with systematic RT shifts (simulating drift)
    reps = []
    shifts = [0, 5, -3]  # seconds drift per replicate
    for rep_idx, shift in enumerate(shifts):
        rep_features = []
        for r in rois:
            rep_features.append(DetectedFeature(
                feature_id=r.roi_id, mz=r.mz,
                mz_min=r.mz_min, mz_max=r.mz_max,
                rt=r.rt_apex + shift,
                rt_min=r.rt_start + shift,
                rt_max=r.rt_end + shift,
                intensity=r.max_intensity, area=r.peak_area,
                snr=5.0, peak_quality=0.8,
            ))
        reps.append(rep_features)
    
    aligner = RTAligner(method="loess", mz_tolerance_ppm=10.0, rt_tolerance_sec=30.0)
    warpings = aligner.fit(reps)
    
    print("   Alignment report:")
    for w in warpings:
        print(f"      Sample {w.sample_index}: {w.n_landmarks} landmarks, "
              f"median shift={w.shift_median:.1f}s, max shift={w.shift_max:.1f}s")
    
    # Check that shifts were detected
    assert warpings[0].n_landmarks >= 2, f"FAIL: Not enough landmarks for sample 0"
    # Sample 1 should have a positive shift correction
    assert abs(warpings[1].shift_median) > 1.0, f"FAIL: Expected significant shift for sample 1"
    
    # Test transform
    transformed = aligner.transform(reps[1], sample_index=1)
    print(f"   Transformed sample 1: {len(transformed)} features")
    if len(transformed) > 0:
        original_rts = [f.rt + shifts[1] for f in reps[1][:3]]
        corrected_rts = [f.rt for f in transformed[:3]]
        print(f"   Original RTs (first 3): {[f'{r:.1f}' for r in original_rts]}")
        print(f"   Corrected RTs:          {[f'{r:.1f}' for r in corrected_rts]}")
    
    return True


def test_binning():
    print("\n" + "=" * 60)
    print("6. SPECTRUM BINNING")
    print("=" * 60)
    
    mz = np.array([100.001, 100.005, 100.012, 100.025, 100.030, 200.100])
    intensity = np.array([10, 50, 30, 20, 5, 100])
    
    centres, binned = bin_spectrum(mz, intensity, bin_width=0.02)
    print(f"   Bins: {len(centres)}")
    print(f"   m/z centres: {[f'{c:.3f}' for c in centres]}")
    print(f"   Intensities: {[f'{i:.0f}' for i in binned]}")
    
    # First bin should contain mz 100.001, 100.005, 100.012
    assert binned[0] > 0, "FAIL: First bin should have intensity"
    assert binned[1] > 0, "FAIL: Second bin should have intensity"
    return True


def test_ppm_conversion():
    print("\n" + "=" * 60)
    print("7. UNIT CONVERSIONS")
    print("=" * 60)
    
    da = ppm_to_da(5.0, 200.0)
    print(f"   5 ppm at m/z 200 = {da:.4f} Da")
    assert abs(da - 0.001) < 0.001, "FAIL: 5 ppm at 200 should be ~0.001 Da"
    
    ppm = da_to_ppm(0.02, 200.0)
    print(f"   0.02 Da at m/z 200 = {ppm:.1f} ppm")
    assert abs(ppm - 100.0) < 1.0, "FAIL: 0.02 Da at 200 should be ~100 ppm"
    return True


if __name__ == "__main__":
    tests = [
        test_peak_picking,
        test_feature_detection,
        test_feature_grouping,
        test_gap_filling,
        test_alignment,
        test_binning,
        test_ppm_conversion,
    ]
    
    passed = 0
    failed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"\n   {e}")
            failed += 1
        except Exception as e:
            print(f"\n   ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} passed, {failed} failed")
    print("=" * 60)
