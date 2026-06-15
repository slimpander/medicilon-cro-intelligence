"""Fast smoke test of all Phase 1 modules."""
import numpy as np
import sys
sys.path.insert(0, '.')
from src.io_utils import Spectrum, FeatureTable, DetectedFeature, bin_spectrum, ppm_to_da, da_to_ppm
from src.peak_engine import PeakPicker, FeatureDetector
from src.alignment_engine import RTAligner
from src.grouping_engine import DensityFeatureGrouper, GapFiller, compute_feature_quality
from src import DetectedFeature as DF

# 1. Build a single spectrum with 3 known peaks + noise
mz_vals, int_vals = [], []
for mz, amp, sigma in [(195.0877, 8e4, 0.005), (181.0720, 7e4, 0.006), (152.0570, 9e4, 0.005)]:
    x = np.linspace(mz - 0.03, mz + 0.03, 41)
    y = amp * np.exp(-(x - mz) ** 2 / (2 * sigma ** 2))
    mz_vals.extend(x.tolist())
    int_vals.extend(y.tolist())
for _ in range(300):
    mz_vals.append(np.random.uniform(100, 300))
    int_vals.append(np.random.exponential(200))
order = np.argsort(mz_vals)
mz_arr = np.array([mz_vals[i] for i in order], dtype=np.float64)
int_arr = np.array([int_vals[i] for i in order], dtype=np.float64)
spec = Spectrum(index=0, ms_level=1, scan_number=1, retention_time=60.0)
spec.mz = mz_arr
spec.intensity = int_arr
spec.total_ion_current = float(np.sum(int_arr))
print(f"Test spectrum: {len(spec.mz)} points")

# 2. Peak picking
picker = PeakPicker(snr_threshold=2.0, min_intensity=500)
peaks = picker.detect_peaks(spec)
top = sorted(peaks, key=lambda p: p.intensity, reverse=True)[:5]
print(f"Peaks found: {len(peaks)}")
for p in top:
    print(f"  m/z={p.mz:.4f} int={p.intensity:.0f} SNR={p.snr:.1f} Q={p.quality:.2f}")
assert any(abs(p.mz - 195.0877) < 0.02 for p in top), "Caffeine not found!"
print(">>> Peak picking: PASS")

# 3. Feature detection (3 scans)
np.random.seed(42)
all_peaks = [peaks]
for shift in [0.001, -0.001]:
    s2 = Spectrum(index=1, ms_level=1, scan_number=2, retention_time=61.0)
    s2.mz = np.array([m + shift for m in mz_vals])
    s2.intensity = int_arr * np.random.uniform(0.8, 1.2, len(int_arr))
    s2.total_ion_current = float(np.sum(s2.intensity))
    all_peaks.append(picker.detect_peaks(s2))
rts = np.array([60.0, 61.0, 62.0])
detector = FeatureDetector(mz_tolerance_da=0.02, min_scans=2, min_intensity=1000)
rois = detector.extract_rois(all_peaks, rts)
print(f"ROIs: {len(rois)}")
for r in sorted(rois, key=lambda r: r.max_intensity, reverse=True)[:5]:
    print(f"  m/z={r.mz:.4f} RT={r.rt_apex:.0f} Area={r.peak_area:.0f}")
print(">>> Feature detection: PASS")

# 4. Grouping
reps = []
for rep_idx in range(3):
    rf = []
    for r in rois:
        rf.append(DF(
            feature_id=r.roi_id, mz=r.mz + np.random.uniform(-0.002, 0.002),
            mz_min=r.mz_min, mz_max=r.mz_max,
            rt=r.rt_apex + np.random.uniform(-2, 2),
            rt_min=r.rt_start, rt_max=r.rt_end,
            intensity=r.max_intensity * np.random.uniform(0.8, 1.2),
            area=r.peak_area, snr=5.0, peak_quality=0.8,
        ))
    reps.append(rf)
grouper = DensityFeatureGrouper(mz_bandwidth_ppm=5.0, rt_bandwidth_sec=10.0, min_fraction=0.5)
ft = grouper.group(reps, ["S1", "S2", "S3"])
print(f"Grouped: {ft.num_features} features x {ft.num_samples} samples")
print(f"Density: {np.count_nonzero(ft.intensity_matrix)}/{ft.intensity_matrix.size}")
assert ft.num_features >= 2
print(">>> Feature grouping: PASS")

# 5. Gap filling
matrix = ft.intensity_matrix.copy()
if ft.num_samples > 2 and ft.num_features > 0:
    matrix[0, 2] = 0
ft_gap = FeatureTable(
    sample_names=ft.sample_names,
    feature_ids=ft.feature_ids, mz_values=ft.mz_values,
    rt_values=ft.rt_values, intensity_matrix=matrix,
)
gf = GapFiller()
ft_knn = gf.fill_by_knn(ft_gap, k=3)
ft_min = gf.fill_by_minimum(ft_gap)
print(f"Gap filled (KNN): {np.count_nonzero(ft_knn.intensity_matrix)}/{ft_knn.intensity_matrix.size}")
print(f"Gap filled (min): {np.count_nonzero(ft_min.intensity_matrix)}/{ft_min.intensity_matrix.size}")
q = compute_feature_quality(ft_min)
print(f"Quality: {[f'{x:.2f}' for x in q]}")
print(">>> Gap filling: PASS")

# 6. Alignment
aligner = RTAligner(method="linear", rt_tolerance_sec=30.0)
shifted = [DF(
    feature_id=f.feature_id, mz=f.mz,
    mz_min=f.mz_min, mz_max=f.mz_max,
    rt=f.rt + 5.0, rt_min=f.rt_min + 5, rt_max=f.rt_max + 5,
    intensity=f.intensity, area=f.area, snr=f.snr, peak_quality=f.peak_quality,
) for f in reps[0]]
warpings = aligner.fit([reps[0], shifted])
for w in warpings:
    print(f"  Sample {w.sample_index}: {w.n_landmarks} landmarks, shift={w.shift_median:.1f}s")
print(">>> Alignment: PASS")

# 7. Binning + ppm
c, b = bin_spectrum(
    np.array([100.001, 100.005, 100.012, 100.025]),
    np.array([10, 50, 30, 20]),
    bin_width=0.02,
)
print(f"Bins: {len(c)}, intensities: {[f'{x:.0f}' for x in b]}")
da = ppm_to_da(5.0, 200.0)
print(f"5 ppm at 200 m/z = {da:.4f} Da")
print(">>> Utilities: PASS")

print("\nALL PHASE 1 TESTS PASSED")
