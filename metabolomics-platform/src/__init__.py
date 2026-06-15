"""
Metabolomics Platform v0.2.0
=============================
Untargeted metabolomics analysis pipeline for complex proteomics-derived metrics.

Core modules:
  - io_utils:      mzML reading, vendor format conversion, feature table I/O
  - peak_engine:   Wavelet-based peak picking (centWave-style)
  - alignment_engine: Landmark-based RT alignment (obiwarp-style)
  - grouping_engine: Density-based feature grouping + gap filling
  - stats_engine:  PCA, PLS-DA, volcano plots, pathway enrichment
  - db_annotator:  HMDB/METLIN/MassBank metabolite matching
"""

__version__ = "0.3.0"
__author__ = "Metabolomics Platform Team"

from .io_utils import (
    MzMLReader,
    MSConvertWrapper,
    Spectrum,
    DetectedFeature,
    FeatureTable,
    bin_spectrum,
    ppm_to_da,
    da_to_ppm,
)

from .peak_engine import (
    PeakPicker,
    FeatureDetector,
    PeakCandidate,
    ROI,
    PeakDetectionPipeline,
)

from .alignment_engine import (
    RTAligner,
    ConsensusBuilder,
    AlignedFeature,
    WarpingFunction,
    groupwise_alignment,
)

from .grouping_engine import (
    DensityFeatureGrouper,
    GapFiller,
    FeatureGroup,
    compute_feature_quality,
)

from .stats_engine import (
    normalize_total_ion,
    normalize_median,
    normalize_quantile,
    log_transform,
    pareto_scale,
    auto_scale,
    pca,
    pls_da,
    volcano,
    pathway_enrichment,
    univariate_analysis,
    PCAResult,
    PLSDAResult,
    VolcanoResult,
    PathwayResult,
    EnrichmentResult,
    UnivariateResult,
)

from .db_annotator import (
    MetaboliteAnnotator,
    MetaboliteMatch,
    AnnotatedFeature,
    AnnotationResult,
    ADDUCT_DATABASE,
    COMMON_ADDUCTS_POSITIVE,
    COMMON_ADDUCTS_NEGATIVE,
    formula_to_mass,
    parse_formula,
    calculate_neutral_mass,
    calculate_adduct_mz,
    guess_adducts,
    cosine_similarity,
    spectrum_entropy,
    spectral_match,
    export_annotations_csv,
)
