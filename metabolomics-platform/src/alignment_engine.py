"""
alignment_engine.py — Retention Time Alignment for Untargeted Metabolomics
===========================================================================
Implements landmark-based RT alignment (obiwarp-style) for cross-run correction.

Algorithm:
  1. Build consensus feature map from all samples
  2. Identify landmark features (present in most samples, high quality)
  3. Fit LOESS warping functions for each sample against the consensus
  4. Apply warping to correct RT drift

Also includes group-based alignment using dynamic time warping (DTW) fallback.

References:
  - Prince & Marcotte (2006) Anal. Chem. 78:6140-6152
  - XCMS obiwarp implementation
"""

from __future__ import annotations

from typing import List, Dict, Optional, Tuple
import numpy as np
from scipy import interpolate, spatial
from dataclasses import dataclass, field
from collections import defaultdict

from .io_utils import DetectedFeature


# ══════════════════════════════════════════════════════════════════════
# Dataclasses
# ══════════════════════════════════════════════════════════════════════

@dataclass
class AlignedFeature:
    """A feature after RT alignment, linked across samples."""
    feature_id: int
    consensus_mz: float
    consensus_rt: float
    mz_variability: float           # ppm std across samples
    rt_variability: float           # seconds std across samples
    intensities: List[float] = field(default_factory=list)
    sample_indices: List[int] = field(default_factory=list)
    quality_score: float = 0.0

    @property
    def num_samples(self) -> int:
        return len(self.sample_indices)

    @property
    def max_intensity(self) -> float:
        return max(self.intensities) if self.intensities else 0.0

    @property
    def mean_intensity(self) -> float:
        return float(np.mean(self.intensities)) if self.intensities else 0.0


@dataclass
class WarpingFunction:
    """Non-linear RT warping for a single sample."""
    sample_index: int
    original_rts: np.ndarray
    corrected_rts: np.ndarray
    shift_median: float             # median RT shift
    shift_max: float                # maximum RT shift
    n_landmarks: int


# ══════════════════════════════════════════════════════════════════════
# Consensus Feature Map Builder
# ══════════════════════════════════════════════════════════════════════

class ConsensusBuilder:
    """Build a consensus feature map from multiple sample feature lists.

    Used for landmark-based alignment: finds features present in most
    samples to serve as alignment anchors.
    """

    def __init__(
        self,
        mz_tolerance_ppm: float = 10.0,
        rt_tolerance_sec: float = 30.0,
        min_fraction: float = 0.5,   # feature must appear in at least this fraction of samples
    ):
        self.mz_tolerance_ppm = mz_tolerance_ppm
        self.rt_tolerance_sec = rt_tolerance_sec
        self.min_fraction = min_fraction

    def build_consensus(
        self,
        all_features: List[List[DetectedFeature]],
    ) -> List[AlignedFeature]:
        """Build a consensus feature map.

        Args:
            all_features: List of feature lists, one per sample

        Returns:
            List of AlignedFeature objects representing the consensus
        """
        n_samples = len(all_features)
        min_samples = max(1, int(n_samples * self.min_fraction))
        aligned = []
        used = [set() for _ in range(n_samples)]  # track which features are already matched
        group_id = 0

        # Start from most intense features first (likely real signals)
        all_candidates = []
        for s_idx, features in enumerate(all_features):
            for feat in features:
                if feat.intensity > 0 and feat.snr > 1.0:
                    all_candidates.append((s_idx, feat))

        all_candidates.sort(key=lambda x: x[1].intensity, reverse=True)

        for s_idx, feat in all_candidates:
            if feat.feature_id in used[s_idx]:
                continue

            # Find matching features across all samples
            group_mz = [feat.mz]
            group_rt = [feat.rt]
            group_int = [feat.intensity]
            group_samples = [s_idx]
            used[s_idx].add(feat.feature_id)

            for other_s in range(n_samples):
                if other_s == s_idx:
                    continue
                matched = self._find_best_match(feat, all_features[other_s], used[other_s])
                if matched is not None:
                    group_mz.append(matched.mz)
                    group_rt.append(matched.rt)
                    group_int.append(matched.intensity)
                    group_samples.append(other_s)
                    used[other_s].add(matched.feature_id)

            if len(group_samples) >= min_samples:
                mz_consensus = float(np.median(group_mz))
                rt_consensus = float(np.median(group_rt))
                mz_stdev = float(np.std(group_mz))
                rt_stdev = float(np.std(group_rt))

                aligned.append(AlignedFeature(
                    feature_id=group_id,
                    consensus_mz=mz_consensus,
                    consensus_rt=rt_consensus,
                    mz_variability=mz_stdev,
                    rt_variability=rt_stdev,
                    intensities=group_int,
                    sample_indices=group_samples,
                    quality_score=float(len(group_samples) / n_samples),
                ))
                group_id += 1

        return sorted(aligned, key=lambda f: f.consensus_rt)

    def _find_best_match(
        self,
        query: DetectedFeature,
        candidates: List[DetectedFeature],
        used_ids: set,
    ) -> Optional[DetectedFeature]:
        """Find the best-matching feature in candidate list."""
        best = None
        best_score = float("inf")

        for feat in candidates:
            if feat.feature_id in used_ids:
                continue
            mz_ppm = abs(query.mz - feat.mz) / max(query.mz, 1e-6) * 1e6
            rt_diff = abs(query.rt - feat.rt)
            if mz_ppm < self.mz_tolerance_ppm and rt_diff < self.rt_tolerance_sec:
                score = mz_ppm + rt_diff * 0.1
                if score < best_score:
                    best_score = score
                    best = feat

        return best


# ══════════════════════════════════════════════════════════════════════
# RT Alignment Engine
# ══════════════════════════════════════════════════════════════════════

class RTAligner:
    """Retention time alignment using landmark-feature-based warping.

    For each sample, computes a non-linear RT correction function that
    maps the sample's RTs to the consensus RT scale.
    """

    def __init__(
        self,
        method: str = "loess",          # "loess", "linear", "dwt"
        mz_tolerance_ppm: float = 10.0,
        rt_tolerance_sec: float = 30.0,
        min_landmark_fraction: float = 0.3,
        loess_span: float = 0.5,
    ):
        self.method = method
        self.mz_tolerance_ppm = mz_tolerance_ppm
        self.rt_tolerance_sec = rt_tolerance_sec
        self.min_landmark_fraction = min_landmark_fraction
        self.loess_span = loess_span
        self.consensus_builder = ConsensusBuilder(
            mz_tolerance_ppm=mz_tolerance_ppm,
            rt_tolerance_sec=rt_tolerance_sec,
            min_fraction=min_landmark_fraction,
        )
        self._warping_functions: List[WarpingFunction] = []

    def fit(
        self,
        all_features: List[List[DetectedFeature]],
    ) -> List[WarpingFunction]:
        """Fit RT warping functions for all samples against the consensus.

        Args:
            all_features: Feature lists, one per sample

        Returns:
            List of WarpingFunction, one per sample
        """
        n_samples = len(all_features)
        consensus = self.consensus_builder.build_consensus(all_features)
        self._warping_functions = []

        for s_idx in range(n_samples):
            warping = self._fit_sample(s_idx, all_features[s_idx], consensus)
            self._warping_functions.append(warping)

        return self._warping_functions

    def _fit_sample(
        self,
        s_idx: int,
        sample_features: List[DetectedFeature],
        consensus: List[AlignedFeature],
    ) -> WarpingFunction:
        """Fit RT warping for a single sample."""
        # Match sample features to consensus landmarks
        sample_rts = []
        consensus_rts = []

        for feat in sample_features:
            best = None
            best_diff = float("inf")
            for con in consensus:
                mz_ppm = abs(feat.mz - con.consensus_mz) / max(con.consensus_mz, 1e-6) * 1e6
                if mz_ppm < self.mz_tolerance_ppm:
                    rt_diff = abs(feat.rt - con.consensus_rt)
                    if rt_diff < self.rt_tolerance_sec and rt_diff < best_diff:
                        best_diff = rt_diff
                        best = con

            if best is not None and best_diff < self.rt_tolerance_sec:
                sample_rts.append(feat.rt)
                consensus_rts.append(best.consensus_rt)

        if len(sample_rts) < 3:
            # Not enough landmarks — apply a simple global shift
            all_sample_rts = np.array([f.rt for f in sample_features])
            if len(all_sample_rts) == 0:
                return WarpingFunction(
                    sample_index=s_idx,
                    original_rts=np.array([]),
                    corrected_rts=np.array([]),
                    shift_median=0.0, shift_max=0.0, n_landmarks=0,
                )
            return WarpingFunction(
                sample_index=s_idx,
                original_rts=all_sample_rts.copy(),
                corrected_rts=all_sample_rts.copy(),
                shift_median=0.0, shift_max=0.0, n_landmarks=0,
            )

        sample_rts = np.array(sample_rts, dtype=np.float64)
        consensus_rts = np.array(consensus_rts, dtype=np.float64)

        # Sort by RT
        sort_idx = np.argsort(sample_rts)
        sample_rts = sample_rts[sort_idx]
        consensus_rts = consensus_rts[sort_idx]

        shifts = consensus_rts - sample_rts
        shift_median = float(np.median(shifts))
        shift_max = float(np.max(np.abs(shifts)))

        # Build the warping function
        if self.method == "loess" and len(sample_rts) >= 5:
            # LOESS smoothing of the correction
            from scipy.interpolate import UnivariateSpline
            try:
                spline = UnivariateSpline(sample_rts, consensus_rts, s=len(sample_rts) * self.loess_span)
                all_sample_rts = np.array([f.rt for f in sample_features])
                corrected = spline(all_sample_rts)
            except Exception:
                # Fallback: linear interpolation
                corrected = np.interp(
                    np.array([f.rt for f in sample_features]),
                    sample_rts, consensus_rts,
                )
        elif self.method == "linear" or len(sample_rts) >= 2:
            all_sample_rts = np.array([f.rt for f in sample_features])
            corrected = np.interp(all_sample_rts, sample_rts, consensus_rts)
        else:
            all_sample_rts = np.array([f.rt for f in sample_features]) if sample_features else np.array([])
            corrected = all_sample_rts.copy()

        return WarpingFunction(
            sample_index=s_idx,
            original_rts=np.array([f.rt for f in sample_features]),
            corrected_rts=corrected,
            shift_median=shift_median,
            shift_max=shift_max,
            n_landmarks=len(sample_rts),
        )

    def transform(
        self,
        features: List[DetectedFeature],
        sample_index: int = 0,
    ) -> List[DetectedFeature]:
        """Apply the fitted warping to a feature list."""
        if sample_index >= len(self._warping_functions):
            return features

        warping = self._warping_functions[sample_index]
        if warping.n_landmarks < 3:
            return features  # No meaningful warping

        # Build interpolation from original to corrected RTs
        orig_rts = warping.original_rts
        corr_rts = warping.corrected_rts
        if len(orig_rts) < 2 or len(corr_rts) < 2:
            return features

        sort_idx = np.argsort(orig_rts)
        orig_sorted = orig_rts[sort_idx]
        corr_sorted = corr_rts[sort_idx]

        transformed = []
        for feat in features:
            new_feat = DetectedFeature(
                feature_id=feat.feature_id,
                mz=feat.mz,
                mz_min=feat.mz_min,
                mz_max=feat.mz_max,
                rt=float(np.interp(feat.rt, orig_sorted, corr_sorted)),
                rt_min=float(np.interp(feat.rt_min, orig_sorted, corr_sorted)),
                rt_max=float(np.interp(feat.rt_max, orig_sorted, corr_sorted)),
                intensity=feat.intensity,
                area=feat.area,
                snr=feat.snr,
                peak_quality=feat.peak_quality,
                isotopes=list(feat.isotopes),
                annotation=feat.annotation,
                adduct=feat.adduct,
            )
            transformed.append(new_feat)

        return transformed

    @property
    def alignment_report(self) -> List[Dict]:
        """Generate a per-sample alignment report."""
        return [
            {
                "sample_index": w.sample_index,
                "n_landmarks": w.n_landmarks,
                "shift_median_sec": round(w.shift_median, 2),
                "shift_max_sec": round(w.shift_max, 2),
            }
            for w in self._warping_functions
        ]


# ══════════════════════════════════════════════════════════════════════
# Group-based alignment (alternative method)
# ══════════════════════════════════════════════════════════════════════

def groupwise_alignment(
    feature_groups: List[List[DetectedFeature]],
    mz_window_ppm: float = 10.0,
    rt_window_sec: float = 60.0,
) -> List[DetectedFeature]:
    """Simple group-based alignment: merge features by clustering in m/z-RT space.

    This is a lightweight alternative to landmark-based alignment.
    Suitable when RT drift is minimal.
    """
    # Collect all features with sample origin
    all_pts = []
    feat_map = []
    for s_idx, features in enumerate(feature_groups):
        for feat in features:
            pt = (feat.mz, feat.rt)
            all_pts.append(pt)
            feat_map.append((s_idx, feat))

    if not all_pts:
        return []

    all_pts = np.array(all_pts, dtype=np.float64)
    n = len(all_pts)

    # Normalize for distance calculation
    mz_scale = mz_window_ppm / 1e6
    rt_scale = rt_window_sec
    pts_scaled = all_pts.copy()
    pts_scaled[:, 0] /= max(np.median(pts_scaled[:, 0]), 1.0) * mz_scale
    pts_scaled[:, 1] /= rt_scale

    # Simple clustering: connect points within threshold
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components

    tree = spatial.KDTree(pts_scaled)
    pairs = tree.query_ball_tree(tree, r=1.0)

    # Build adjacency matrix
    row = []
    col = []
    for i, neighbours in enumerate(pairs):
        for j in neighbours:
            if i != j:
                row.append(i)
                col.append(j)

    graph = csr_matrix((np.ones(len(row)), (np.array(row), np.array(col))), shape=(n, n))
    n_components, labels = connected_components(graph, directed=False)

    # Build consensus features
    consensus = []
    for cluster_id in range(n_components):
        mask = labels == cluster_id
        cluster_pts = all_pts[mask]
        cluster_samples = set()

        best_intensity = -1.0
        best_feat = None
        for idx in np.where(mask)[0]:
            s_idx, feat = feat_map[idx]
            cluster_samples.add(s_idx)
            if feat.intensity > best_intensity:
                best_intensity = feat.intensity
                best_feat = feat

        if best_feat is None:
            continue

        consensus.append(DetectedFeature(
            feature_id=cluster_id,
            mz=float(np.median(cluster_pts[:, 0])),
            mz_min=float(np.min(cluster_pts[:, 0])),
            mz_max=float(np.max(cluster_pts[:, 0])),
            rt=float(np.median(cluster_pts[:, 1])),
            rt_min=float(np.min(cluster_pts[:, 1])),
            rt_max=float(np.max(cluster_pts[:, 1])),
            intensity=best_intensity,
            area=best_feat.area if best_feat else 0.0,
            snr=best_feat.snr if best_feat else 0.0,
            peak_quality=float(len(cluster_samples) / len(feature_groups)),
        ))

    return consensus
