"""Test the metabolomics platform with a real mzML file."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from src.io_utils import MzMLReader, Spectrum
from src.peak_engine import PeakPicker, FeatureDetector
from src.alignment_engine import RTAligner
from src.grouping_engine import DensityFeatureGrouper, GapFiller, compute_feature_quality
from src.stats_engine import log_transform, pareto_scale, pca, volcano
from src.db_annotator import MetaboliteAnnotator

# Known metabolites in the test file
KNOWN = {
    90.0550:  "L-Alanine",
    148.0604: "L-Glutamic acid",
    166.0863: "L-Phenylalanine",
    193.0343: "Citric acid",
    205.0972: "L-Tryptophan",
    195.0877: "Caffeine",
    180.0655: "Hippuric acid",
    91.0390:  "L-Lactic acid",
    119.0339: "Succinic acid",
    132.0768: "Creatine",
    152.0706: "Acetaminophen",
    169.0356: "Uric acid",
}

print("=" * 60)
print("REAL mzML PIPELINE TEST")
print("=" * 60)

# 1. Read mzML
mzml_path = os.path.join("uploads", "test_metabolomics.mzML")
reader = MzMLReader(mzml_path)
tic_rts, tic_vals = reader.get_tic_chromatogram()
print(f"\n1. mzML READ")
print(f"   File: {mzml_path}")
print(f"   Spectra: {reader.total_spectra}")
print(f"   RT range: {tic_rts[0]:.1f} - {tic_rts[-1]:.1f}s")
print(f"   TIC range: {tic_vals.min():.0f} - {tic_vals.max():.0f}")

# 2. Peak picking
print(f"\n2. PEAK PICKING")
picker = PeakPicker(snr_threshold=3.0, min_intensity=1000)
spectra = list(reader.iter_spectra(ms_level=1))
all_peaks = [picker.detect_peaks(s) for s in spectra]
total_peaks = sum(len(p) for p in all_peaks)
print(f"   Total peaks across {len(spectra)} scans: {total_peaks}")

# Show peaks from a few scans
for scan_idx in [60, 136, 170]:  # near RT 30, 68, 85
    if scan_idx < len(all_peaks):
        top = sorted(all_peaks[scan_idx], key=lambda p: p.intensity, reverse=True)[:5]
        rt = scan_idx * 0.5
        print(f"   Scan {scan_idx} (RT={rt:.0f}s): {len(all_peaks[scan_idx])} peaks")
        for p in top[:3]:
            match = "?"
            for known_mz, name in KNOWN.items():
                if abs(p.mz - known_mz) < 0.03:
                    match = name
                    break
            print(f"      m/z={p.mz:.4f} int={p.intensity:.0f} SNR={p.snr:.1f} [{match}]")

# 3. Feature detection
print(f"\n3. FEATURE DETECTION")
rts = np.array([s.retention_time for s in spectra])
detector = FeatureDetector(mz_tolerance_da=0.02, min_scans=5, min_intensity=2000)
rois = detector.extract_rois(all_peaks, rts)
print(f"   ROIs detected: {len(rois)}")

# Match ROIs to known metabolites
matched = 0
for roi in sorted(rois, key=lambda r: r.max_intensity, reverse=True):
    for known_mz, name in KNOWN.items():
        if abs(roi.mz - known_mz) < 0.03:
            print(f"   [MATCH] {name:20s} m/z={roi.mz:.4f} (expected {known_mz:.4f}) "
                  f"RT={roi.rt_apex:.0f}s area={roi.peak_area:.0f} scans={roi.num_scans}")
            matched += 1
            break

print(f"   Matched: {matched}/{len(KNOWN)} known metabolites")

# 4. Feature grouping (single sample — simulate 3 replicates with shifts)
print(f"\n4. FEATURE GROUPING + GAP FILLING")
from src.io_utils import DetectedFeature

features = []
for roi in rois:
    snr_val = roi.max_intensity / (float(np.std(roi.intensities)) + 1.0) if len(roi.intensities) > 1 else 3.0
    q = min(1.0, roi.num_scans / 15)
    features.append(DetectedFeature(
        feature_id=roi.roi_id, mz=roi.mz, mz_min=roi.mz_min, mz_max=roi.mz_max,
        rt=roi.rt_apex, rt_min=roi.rt_start, rt_max=roi.rt_end,
        intensity=roi.max_intensity, area=roi.peak_area,
        snr=float(snr_val), peak_quality=float(q),
    ))

# Simulate 3 replicates
np.random.seed(42)
reps = [features]
for shift in [2, -1]:
    rep = []
    for f in features:
        rep.append(DetectedFeature(
            feature_id=f.feature_id, mz=f.mz + np.random.uniform(-0.002, 0.002),
            mz_min=f.mz_min, mz_max=f.mz_max,
            rt=f.rt + shift + np.random.uniform(-2, 2),
            rt_min=f.rt_min, rt_max=f.rt_max,
            intensity=f.intensity * np.random.uniform(0.85, 1.15),
            area=f.area, snr=f.snr, peak_quality=f.peak_quality,
        ))
    reps.append(rep)

grouper = DensityFeatureGrouper(mz_bandwidth_ppm=5.0, rt_bandwidth_sec=10.0)
ft = grouper.group(reps, ["Rep1", "Rep2", "Rep3"])
print(f"   Grouped: {ft.num_features} features x {ft.num_samples} samples")

gf = GapFiller()
ft_filled = gf.fill_by_knn(ft, k=3)
quality = compute_feature_quality(ft_filled)
print(f"   Avg quality: {np.mean(quality):.3f}")

# 5. Stats — PCA
print(f"\n5. PCA")
ft_log = log_transform(ft_filled, base=2)
ft_par = pareto_scale(ft_log)
pca_result = pca(ft_par, n_components=2)
print(f"   PC1: {pca_result.variance_explained[0]*100:.1f}%  PC2: {pca_result.variance_explained[1]*100:.1f}%")

# 6. Annotation
print(f"\n6. METABOLITE ANNOTATION")
annotator = MetaboliteAnnotator(mass_tolerance_ppm=10.0, mode="positive", use_online=False)
ann_features = []
for i in range(ft.num_features):
    ann_features.append(DetectedFeature(
        feature_id=i, mz=float(ft.mz_values[i]),
        mz_min=float(ft.mz_values[i]) - 0.01, mz_max=float(ft.mz_values[i]) + 0.01,
        rt=float(ft.rt_values[i]), rt_min=float(ft.rt_values[i]) - 5, rt_max=float(ft.rt_values[i]) + 5,
        intensity=float(np.max(ft.intensity_matrix[i, :])),
        area=float(np.sum(ft.intensity_matrix[i, :])), snr=5.0, peak_quality=0.8,
    ))

result = annotator.annotate_features(ann_features)
print(f"   Annotated: {result.annotated_count}/{result.total_features}")
print(f"   High confidence: {result.high_confidence_count}")

# Show top matches
for af in result.annotated_features[:15]:
    if af.top_match:
        m = af.top_match
        known_flag = ""
        for kmz, kname in KNOWN.items():
            if abs(af.mz - kmz) < 0.03:
                known_flag = f" [KNOWN: {kname}]"
                break
        print(f"   m/z={af.mz:.4f} -> {m.name:25s} ({m.adduct}) err={m.mass_error_ppm:.1f}ppm score={m.score:.3f}{known_flag}")

print(f"\n{'=' * 60}")
print(f"REAL mzML TEST COMPLETE")
print(f"  Matched metabolites: {matched}/{len(KNOWN)}")
print(f"  ROIs: {len(rois)}")
print(f"  Features grouped: {ft.num_features}")
print(f"  Annotated: {result.annotated_count}")
print(f"  PCA PC1+PC2: {sum(pca_result.variance_explained[:2])*100:.1f}% variance")
print(f"{'=' * 60}")
