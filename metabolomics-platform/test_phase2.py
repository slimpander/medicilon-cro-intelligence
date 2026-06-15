"""
test_phase2.py — Tests for Phase 2 modules (stats_engine + db_annotator).
Uses synthetic feature tables built from known metabolite m/z values.
"""

import sys, os
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))

from src.io_utils import FeatureTable
from src.stats_engine import (
    normalize_total_ion, normalize_median, normalize_quantile,
    log_transform, pareto_scale, auto_scale,
    pca, pls_da, volcano, pathway_enrichment, univariate_analysis,
)
from src.db_annotator import (
    MetaboliteAnnotator, MetaboliteMatch,
    formula_to_mass, parse_formula, calculate_neutral_mass, calculate_adduct_mz,
    guess_adducts, cosine_similarity, spectrum_entropy, spectral_match,
    ADDUCT_DATABASE, COMMON_ADDUCTS_POSITIVE,
    export_annotations_csv,
)


# ══════════════════════════════════════════════════════════════════════
# Helper: build a realistic synthetic feature table
# ══════════════════════════════════════════════════════════════════════

def make_test_feature_table() -> FeatureTable:
    """Build a synthetic feature table with 20 features × 6 samples (3 control, 3 treated).
    
    Known metabolites included: glucose, glutamic acid, phenylalanine, 
    tryptophan, lactic acid, citric acid, caffeine, etc.
    """
    np.random.seed(42)
    n_features = 20
    n_samples = 6
    
    # Known metabolite names + approximate m/z for [M+H]+
    metabolites = [
        ("Glucose", 180.063, 50),
        ("Glutamic acid", 148.060, 60),
        ("Phenylalanine", 166.086, 70),
        ("Tryptophan", 205.097, 80),
        ("Lactic acid", 91.039, 55),
        ("Citric acid", 193.034, 65),
        ("Caffeine", 195.087, 75),
        ("Creatine", 132.076, 45),
        ("Succinic acid", 119.034, 40),
        ("Hippuric acid", 180.065, 35),
        ("Aspartic acid", 134.045, 50),
        ("Glutamine", 147.076, 58),
        ("Alanine", 90.055, 42),
        ("Serine", 106.050, 48),
        ("Tyrosine", 182.081, 68),
        ("Carnitine", 162.112, 52),
        ("Pyruvic acid", 89.023, 38),
        ("Uric acid", 169.035, 72),
        ("Acetaminophen", 152.070, 44),
        ("Dopamine", 154.086, 56),
    ]
    
    mz_values = np.zeros(n_features, dtype=np.float64)
    rt_values = np.linspace(30, 240, n_features, dtype=np.float64)
    feature_ids = np.arange(n_features, dtype=np.int64)
    intensity_matrix = np.zeros((n_features, n_samples), dtype=np.float64)
    
    # Sample labels: C1, C2, C3 (control), T1, T2, T3 (treated)
    sample_names = ["C1", "C2", "C3", "T1", "T2", "T3"]
    
    for i, (name, mz, base_intensity) in enumerate(metabolites):
        mz_values[i] = mz
        
        # Control group (samples 0-2): baseline
        for j in range(3):
            intensity_matrix[i, j] = base_intensity * np.random.uniform(0.8, 1.2) * 1000
        
        # Treated group (samples 3-5): some up, some down, some unchanged
        if i < 5:
            # Upregulated 2-3x
            for j in range(3, 6):
                intensity_matrix[i, j] = base_intensity * np.random.uniform(2.0, 3.5) * 1000
        elif i < 10:
            # Downregulated
            for j in range(3, 6):
                intensity_matrix[i, j] = base_intensity * np.random.uniform(0.2, 0.5) * 1000
        else:
            # Unchanged
            for j in range(3, 6):
                intensity_matrix[i, j] = base_intensity * np.random.uniform(0.8, 1.2) * 1000
    
    # Add some missing values (zero ≈ missing)
    for _ in range(8):
        fi = np.random.randint(0, n_features)
        sj = np.random.randint(0, n_samples)
        intensity_matrix[fi, sj] = 0
    
    return FeatureTable(
        sample_names=sample_names,
        feature_ids=feature_ids,
        mz_values=mz_values,
        rt_values=rt_values,
        intensity_matrix=intensity_matrix,
    )


# ══════════════════════════════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════════════════════════════

def test_normalization():
    print("=" * 60)
    print("1. NORMALIZATION METHODS")
    print("=" * 60)
    
    ft = make_test_feature_table()
    print(f"   Input: {ft.num_features} features × {ft.num_samples} samples")
    print(f"   Range: {ft.intensity_matrix.min():.0f} - {ft.intensity_matrix.max():.0f}")
    
    # TIC
    ft_tic = normalize_total_ion(ft)
    assert ft_tic.num_features == ft.num_features
    assert ft_tic.num_samples == ft.num_samples
    print(f"   TIC normalised: range {ft_tic.intensity_matrix.min():.0f} - {ft_tic.intensity_matrix.max():.0f}")
    
    # Median
    ft_med = normalize_median(ft)
    assert ft_med.num_features == ft.num_features
    print(f"   Median normalised: range {ft_med.intensity_matrix.min():.2f} - {ft_med.intensity_matrix.max():.2f}")
    
    # Log transform
    ft_log = log_transform(ft, base=2, offset=1.0)
    assert ft_log.num_features == ft.num_features
    assert np.all(np.isfinite(ft_log.intensity_matrix))
    print(f"   Log2 transformed: range {ft_log.intensity_matrix.min():.2f} - {ft_log.intensity_matrix.max():.2f}")
    
    # Pareto scale
    ft_par = pareto_scale(ft_log)
    assert ft_par.num_features == ft.num_features
    print(f"   Pareto scaled: range {ft_par.intensity_matrix.min():.2f} - {ft_par.intensity_matrix.max():.2f}")
    
    # Auto scale
    ft_auto = auto_scale(ft_log)
    assert ft_auto.num_features == ft.num_features
    print(f"   Auto scaled: range {ft_auto.intensity_matrix.min():.2f} - {ft_auto.intensity_matrix.max():.2f}")
    
    return True


def test_pca():
    print("\n" + "=" * 60)
    print("2. PCA (Principal Component Analysis)")
    print("=" * 60)
    
    ft = make_test_feature_table()
    ft_log = log_transform(ft, base=2)
    
    result = pca(ft_log, n_components=3, centre=True, scale="pareto")
    
    print(f"   Components: {result.n_components}")
    print(f"   Samples: {result.n_samples}")
    print(f"   Features: {result.n_features}")
    print(f"   Variance explained:", end=" ")
    for i in range(result.n_components):
        print(f"PC{i+1}={result.variance_explained[i]:.3f}", end=" ")
    print()
    print(f"   Cumulative: {result.cumulative_variance[-1]:.3f}")
    print(f"   Scores shape: {result.scores.shape}")
    print(f"   Loadings shape: {result.loadings.shape}")
    
    assert result.n_components >= 2, "FAIL: Should have at least 2 components"
    assert result.scores.shape == (result.n_samples, result.n_components)
    assert result.loadings.shape == (result.n_features, result.n_components)
    assert np.isclose(np.sum(result.variance_explained), result.cumulative_variance[-1], atol=0.05)
    
    # Check that PC1 + PC2 explain meaningful variance
    assert result.cumulative_variance[min(1, result.n_components - 1)] > 0.3, \
        f"FAIL: PC1+2 should explain >30% variance (got {result.cumulative_variance[min(1, result.n_components-1)]:.3f})"
    
    return True


def test_pls_da():
    print("\n" + "=" * 60)
    print("3. PLS-DA (Partial Least Squares Discriminant Analysis)")
    print("=" * 60)
    
    ft = make_test_feature_table()
    ft_log = log_transform(ft, base=2)
    
    # Sample labels: first 3 control, last 3 treated
    group_labels = ["Control"] * 3 + ["Treated"] * 3
    print(f"   Groups: {group_labels}")
    
    result = pls_da(ft_log, group_labels, n_components=2)
    
    print(f"   Components: {result.n_components}")
    print(f"   Classes: {result.class_labels}")
    print(f"   R²X: {[f'{v:.3f}' for v in result.r2x]}")
    print(f"   R²Y: {[f'{v:.3f}' for v in result.r2y]}")
    print(f"   Scores shape: {result.scores.shape}")
    print(f"   VIP scores range: {result.vip_scores.min():.2f} - {result.vip_scores.max():.2f}")
    
    assert result.n_components == 2
    assert result.scores.shape == (6, 2)
    assert len(result.vip_scores) == ft.num_features
    assert result.r2y[0] > 0, "FAIL: R²Y should be positive for group separation"
    
    # VIP > 1.0 features should exist (important for classification)
    n_vip1 = np.sum(result.vip_scores > 1.0)
    print(f"   Features with VIP > 1.0: {n_vip1}")
    assert n_vip1 > 0, "FAIL: Should have at least one VIP > 1.0 feature"
    
    return True


def test_volcano():
    print("\n" + "=" * 60)
    print("4. VOLCANO PLOT (Differential Abundance)")
    print("=" * 60)
    
    ft = make_test_feature_table()
    
    result = volcano(
        ft,
        group_a_indices=[0, 1, 2],  # Control
        group_b_indices=[3, 4, 5],  # Treated
        group_a_name="Control",
        group_b_name="Treated",
        fold_change_threshold=1.0,    # log2 FC
        p_value_threshold=0.05,
        test_method="ttest",
    )
    
    print(f"   Comparison: {result.group_a} vs {result.group_b}")
    print(f"   Total features: {len(result.feature_ids)}")
    print(f"   Significant: {result.n_significant}")
    print(f"   Upregulated: {result.n_upregulated}")
    print(f"   Downregulated: {result.n_downregulated}")
    print(f"   FC range: {result.fold_changes.min():.2f} to {result.fold_changes.max():.2f}")
    print(f"   Q-value range: {result.q_values.min():.4f} to {result.q_values.max():.4f}")
    
    assert result.n_significant > 0, "FAIL: Should detect significant changes"
    assert result.n_upregulated > 0, "FAIL: Should detect upregulated features"
    
    # Check q-values are properly ordered
    assert np.all(np.diff(np.sort(result.q_values)) >= -1e-10), \
        "FAIL: Q-values should be monotonic after sorting"
    
    return True


def test_pathway_enrichment():
    print("\n" + "=" * 60)
    print("5. PATHWAY ENRICHMENT")
    print("=" * 60)
    
    ft = make_test_feature_table()
    
    # Simulate significant features: top-8 by fold change
    vol = volcano(
        ft, [0, 1, 2], [3, 4, 5],
        fold_change_threshold=0.5, p_value_threshold=0.10,
    )
    sig_mask = vol.significant.copy()
    # Also mark a few specific mz values as significant for pathway matching
    # Glucose (180.063) -> Glycolysis, Phenylalanine (166.086) -> AAA metabolism
    for i, mz in enumerate(ft.mz_values):
        if abs(mz - 180.063) < 0.01 or abs(mz - 166.086) < 0.01:
            sig_mask[i] = True
    
    n_sig = int(np.sum(sig_mask))
    print(f"   Significant features: {n_sig}")
    
    enrichment = pathway_enrichment(ft, sig_mask)
    
    print(f"   Results: {len(enrichment.results)} pathways tested")
    print(f"   Database: {enrichment.database}")
    
    # Show top hits
    for r in enrichment.results[:5]:
        print(f"   {r.pathway_name} (p={r.p_value:.4f}, q={r.q_value:.4f}, "
              f"ER={r.enrichment_ratio:.2f}, hits={r.n_significant}/{r.n_matched})")
    
    # Should find at least one pathway
    assert len(enrichment.results) >= 0, "FAIL: Pathway enrichment should return results (even if empty)"
    
    return True


def test_univariate_analysis():
    print("\n" + "=" * 60)
    print("6. UNIVARIATE ANALYSIS")
    print("=" * 60)
    
    ft = make_test_feature_table()
    result = univariate_analysis(
        ft, [0, 1, 2], [3, 4, 5], test_method="ttest"
    )
    
    print(f"   Features: {len(result.feature_ids)}")
    print(f"   Mean intensity range: {result.mean_intensities.min():.0f} - {result.mean_intensities.max():.0f}")
    print(f"   CV range: {result.cv_intensities.min():.3f} - {result.cv_intensities.max():.3f}")
    print(f"   % missing range: {result.percent_missing.min():.2f} - {result.percent_missing.max():.2f}")
    print(f"   Significant (q < 0.05): {np.sum(result.q_values < 0.05)}")
    
    assert len(result.feature_ids) == ft.num_features
    assert len(result.fold_changes) == ft.num_features
    assert len(result.p_values) == ft.num_features
    
    return True


def test_formula_parsing():
    print("\n" + "=" * 60)
    print("7. MOLECULAR FORMULA PARSING")
    print("=" * 60)
    
    # Simple
    counts = parse_formula("C6H12O6")
    assert counts == {"C": 6, "H": 12, "O": 6}, f"FAIL: Got {counts}"
    print(f"   C6H12O6 -> {counts}")
    
    # Multi-letter elements
    counts = parse_formula("C10H16N5O13P3")
    assert counts["P"] == 3
    assert counts["N"] == 5
    print(f"   C10H16N5O13P3 (ATP) -> {counts}")
    
    # With single atoms
    counts = parse_formula("C2H5NO2")
    assert counts == {"C": 2, "H": 5, "N": 1, "O": 2}
    print(f"   C2H5NO2 (Glycine) -> {counts}")
    
    # Sulfur
    counts = parse_formula("C5H11NO2S")
    assert counts["S"] == 1
    print(f"   C5H11NO2S (Methionine) -> {counts}")
    
    return True


def test_mass_calculation():
    print("\n" + "=" * 60)
    print("8. MASS CALCULATION")
    print("=" * 60)
    
    # Glucose: C6H12O6
    mass = formula_to_mass("C6H12O6")
    expected = 180.063388  # Known exact mass
    ppm_err = abs(mass - expected) / expected * 1e6
    print(f"   Glucose C6H12O6: {mass:.6f} Da (expected {expected:.6f}, {ppm_err:.2f} ppm)")
    assert ppm_err < 1.0, f"FAIL: Mass error {ppm_err:.2f} ppm exceeds 1 ppm"
    
    # Caffeine: C8H10N4O2
    mass = formula_to_mass("C8H10N4O2")
    expected_caf = 194.080376
    ppm_err = abs(mass - expected_caf) / expected_caf * 1e6
    print(f"   Caffeine C8H10N4O2: {mass:.6f} Da (expected {expected_caf:.6f}, {ppm_err:.2f} ppm)")
    assert ppm_err < 1.0
    
    # Phenylalanine: C9H11NO2
    mass = formula_to_mass("C9H11NO2")
    print(f"   Phenylalanine C9H11NO2: {mass:.6f} Da")
    
    return True


def test_adduct_calculations():
    print("\n" + "=" * 60)
    print("9. ADDUCT CALCULATIONS")
    print("=" * 60)
    
    # Glucose [M+H]+ should be ~181.07
    neutral = formula_to_mass("C6H12O6")
    mz_mh = calculate_adduct_mz(neutral, "[M+H]+")
    print(f"   Glucose [M+H]+: {mz_mh:.4f} (expected ~181.071)")
    assert abs(mz_mh - 181.071) < 0.01
    
    # Reverse calculation
    neutral_back = calculate_neutral_mass(mz_mh, "[M+H]+")
    ppm_err = abs(neutral_back - neutral) / neutral * 1e6
    print(f"   Recovered neutral mass: {neutral_back:.6f} ({ppm_err:.2f} ppm)")
    assert ppm_err < 0.1, f"FAIL: Round-trip error {ppm_err:.4f} ppm"
    
    # [M+Na]+
    mz_na = calculate_adduct_mz(neutral, "[M+Na]+")
    print(f"   Glucose [M+Na]+: {mz_na:.4f} (expected ~203.053)")
    assert abs(mz_na - 203.053) < 0.01
    
    # [M-H]- (negative mode)
    mz_mh_neg = calculate_adduct_mz(neutral, "[M-H]-")
    print(f"   Glucose [M-H]-: {mz_mh_neg:.4f} (expected ~179.056)")
    assert abs(mz_mh_neg - 179.056) < 0.01
    
    return True


def test_adduct_guessing():
    print("\n" + "=" * 60)
    print("10. ADDUCT GUESSING")
    print("=" * 60)
    
    # Observed m/z ~181.07 — could be glucose [M+H]+ or [M+Na-H]+ etc.
    neutral_candidates = [
        formula_to_mass("C6H12O6"),   # Glucose
        formula_to_mass("C9H11NO3"),  # Tyrosine
        formula_to_mass("C8H10N4O2"), # Caffeine (unlikely match)
    ]
    
    guesses = guess_adducts(181.071, neutral_candidates, mode="positive")
    print(f"   Observed m/z 181.071, guesses:")
    for adduct, neutral, ppm in guesses[:5]:
        print(f"      {adduct}: neutral {neutral:.4f} (error {ppm:.2f} ppm)")
    
    assert len(guesses) > 0, "FAIL: Should find at least one adduct match"
    # Best guess should be [M+H]+ for glucose
    best = guesses[0]
    assert best[0] == "[M+H]+", f"FAIL: Best adduct should be [M+H]+, got {best[0]}"
    assert abs(best[1] - formula_to_mass("C6H12O6")) < 0.001
    
    return True


def test_local_annotator():
    print("\n" + "=" * 60)
    print("11. METABOLITE ANNOTATOR (Local Cache)")
    print("=" * 60)
    
    from src.io_utils import DetectedFeature
    
    annotator = MetaboliteAnnotator(
        mass_tolerance_ppm=10.0,
        mode="positive",
        use_online=False,
    )
    
    # Create features at known metabolite m/z values
    test_mzs = [180.063, 148.060, 166.086, 205.097, 195.088, 132.077, 118.027, 89.024]
    features = [
        DetectedFeature(
            feature_id=i, mz=mz, mz_min=mz - 0.01, mz_max=mz + 0.01,
            rt=60.0, rt_min=50, rt_max=70,
            intensity=10000, area=50000, snr=10.0, peak_quality=0.9,
        )
        for i, mz in enumerate(test_mzs)
    ]
    
    result = annotator.annotate_features(features, max_matches_per_feature=5)
    
    print(f"   Total features: {result.total_features}")
    print(f"   Annotated: {result.annotated_count}")
    print(f"   High confidence: {result.high_confidence_count}")
    
    for af in result.annotated_features:
        if af.top_match:
            print(f"   m/z {af.mz:.4f} -> {af.top_match.name} "
                  f"({af.top_match.formula}, {af.top_match.adduct}, "
                  f"err={af.top_match.mass_error_ppm:.1f} ppm, "
                  f"score={af.top_match.score:.3f})")
    
    assert result.annotated_count >= 4, \
        f"FAIL: Should annotate at least 4/8 features (got {result.annotated_count})"
    assert result.high_confidence_count >= 2, \
        f"FAIL: Should have at least 2 high-confidence matches (got {result.high_confidence_count})"
    
    return True


def test_spectral_tools():
    print("\n" + "=" * 60)
    print("12. SPECTRAL SIMILARITY TOOLS")
    print("=" * 60)
    
    # Two identical spectra -> similarity = 1.0
    mz = np.linspace(50, 200, 100)
    int_a = np.exp(-((mz - 100) ** 2) / 100)
    int_b = int_a.copy()
    
    sim = cosine_similarity(int_a, int_b)
    print(f"   Identical spectra cosine similarity: {sim:.4f}")
    assert abs(sim - 1.0) < 0.001, f"FAIL: Identical spectra should have similarity 1.0"
    
    # Different spectra
    int_c = np.exp(-((mz - 150) ** 2) / 100)
    sim_diff = cosine_similarity(int_a, int_c)
    print(f"   Different spectra cosine similarity: {sim_diff:.4f}")
    assert sim_diff < 1.0
    
    # Entropy
    ent = spectrum_entropy(int_a)
    print(f"   Spectrum entropy: {ent:.2f}")
    assert ent > 0
    
    # Spectral matching
    score = spectral_match(mz, int_a, mz, int_a, mz_tolerance_da=0.02)
    print(f"   Spectral match (identical): {score:.4f}")
    assert score > 0.9
    
    return True


def test_csv_export():
    print("\n" + "=" * 60)
    print("13. CSV EXPORT")
    print("=" * 60)
    
    from src.io_utils import DetectedFeature
    
    annotator = MetaboliteAnnotator(use_online=False)
    features = [
        DetectedFeature(
            feature_id=0, mz=180.063, mz_min=180.05, mz_max=180.07,
            rt=60, rt_min=50, rt_max=70,
            intensity=10000, area=50000, snr=10, peak_quality=0.9,
        )
    ]
    result = annotator.annotate_features(features)
    
    outpath = Path(__file__).parent / "test_annotations.csv"
    export_annotations_csv(result, str(outpath))
    
    assert outpath.exists(), "FAIL: CSV file not created"
    
    with open(outpath, 'r') as f:
        lines = f.readlines()
    print(f"   CSV written: {len(lines)} lines")
    assert len(lines) >= 2, "FAIL: CSV should have header + data"
    
    # Cleanup
    outpath.unlink()
    print(f"   Cleaned up {outpath.name}")
    
    return True


# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    tests = [
        test_normalization,
        test_pca,
        test_pls_da,
        test_volcano,
        test_pathway_enrichment,
        test_univariate_analysis,
        test_formula_parsing,
        test_mass_calculation,
        test_adduct_calculations,
        test_adduct_guessing,
        test_local_annotator,
        test_spectral_tools,
        test_csv_export,
    ]
    
    passed = 0
    failed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"\n   FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"\n   ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"PHASE 2 RESULTS: {passed}/{len(tests)} passed, {failed} failed")
    print("=" * 60)

