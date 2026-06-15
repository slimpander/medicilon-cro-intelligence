"""
grouping_engine.py — Feature Grouping & Gap Filling
=====================================================
Groups aligned features across samples into a unified feature matrix.

Algorithm:
  1. Collect all features from all samples
  2. Density-based clustering in (m/z, RT) space
  3. Build sample × feature intensity matrix
  4. Gap filling: re-integrate raw data at feature positions

References:
  - XCMS group.density (peakGroups method)
  - Smith et al. (2006) Anal. Chem. 78:779-787
"""

from __future__ import annotations

from typing import List, Dict, Optional, Tuple, Callable
import numpy as np
from scipy import spatial, stats
from dataclasses import dataclass, field
from collections import defaultdict

from .io_utils import DetectedFeature, FeatureTable


# ══════════════════════════════════════════════════════════════════════
# Feature Grouper
# ══════════════════════════════════════════════════════════════════════

@dataclass
class FeatureGroup:
    """A group of matching features across samples."""
    group_id: int
    consensus_mz: float
    consensus_rt: float
    mz_std: float
    rt_std: float
    sample_intensities: Dict[int, float] = field(default_factory=dict)  # sample_idx → intensity
    sample_areas: Dict[int, float] = field(default_factory=dict)
    num_samples: int = 0
    is_filled: Dict[int, bool] = field(default_factory=dict)  # True if value was gap-filled

    @property
    def detection_rate(self) -> float:
        return self.num_samples / max(len(self.sample_intensities), 1)

    @property
    def median_intensity(self) -> float:
        vals = list(self.sample_intensities.values())
        return float(np.median(vals)) if vals else 0.0

    @property
    def cv_intensity(self) -> float:
        """Coefficient of variation across samples."""
        vals = list(self.sample_intensities.values())
        if len(vals) < 2:
            return 0.0
        std = float(np.std(vals))
        mean = float(np.mean(vals))
        return std / max(mean, 1e-6)


class DensityFeatureGrouper:
    """Density-based feature grouping across samples.

    Groups features by their proximity in (m/z, RT) space using
    kernel density estimation to set dynamic grouping windows.
    """

    def __init__(
        self,
        mz_bandwidth_ppm: float = 5.0,
        rt_bandwidth_sec: float = 10.0,
        min_fraction: float = 0.5,
        max_groups: int = 10000,
    ):
        self.mz_bandwidth_ppm = mz_bandwidth_ppm
        self.rt_bandwidth_sec = rt_bandwidth_sec
        self.min_fraction = min_fraction
        self.max_groups = max_groups

    def group(
        self,
        all_features: List[List[DetectedFeature]],
        sample_names: Optional[List[str]] = None,
    ) -> FeatureTable:
        """Group features across samples into a FeatureTable.

        Args:
            all_features: List of feature lists, one per sample
            sample_names: Optional sample names

        Returns:
            FeatureTable with intensity matrix
        """
        n_samples = len(all_features)
        if sample_names is None:
            sample_names = [f"Sample_{i+1}" for i in range(n_samples)]

        # Collect all features with sample origin
        all_points = []
        feature_map = []  # (sample_idx, DetectedFeature)
        for s_idx, features in enumerate(all_features):
            for feat in features:
                if feat.intensity > 0:
                    all_points.append((feat.mz, feat.rt))
                    feature_map.append((s_idx, feat))

        if not all_points:
            return FeatureTable(sample_names=list(sample_names))

        all_points = np.array(all_points, dtype=np.float64)
        n_points = len(all_points)

        # Scale coordinates for bandwidth-adaptive clustering
        median_mz = float(np.median(all_points[:, 0]))
        mz_scale = self.mz_bandwidth_ppm / 1e6 * max(median_mz, 1.0)

        pts_scaled = all_points.copy()
        pts_scaled[:, 0] /= max(mz_scale, 1e-10)
        pts_scaled[:, 1] /= max(self.rt_bandwidth_sec, 1e-10)

        # KDTree for efficient neighbour search
        tree = spatial.KDTree(pts_scaled)
        pairs = tree.query_ball_tree(tree, r=1.0)

        # Connected components clustering
        from scipy.sparse import csr_matrix, eye
        from scipy.sparse.csgraph import connected_components

        row, col = [], []
        for i, neighbours in enumerate(pairs):
            for j in neighbours:
                if i != j:
                    row.append(i)
                    col.append(j)

        if not row:
            # No connections — each feature is its own group
            labels = np.arange(n_points)
            n_components = n_points
        else:
            graph = csr_matrix(
                (np.ones(len(row), dtype=np.float64), (np.array(row), np.array(col))),
                shape=(n_points, n_points),
            )
            n_components, labels = connected_components(graph, directed=False)

        # Build feature groups
        groups = []
        group_id = 0

        for cluster_id in range(min(n_components, self.max_groups)):
            mask = labels == cluster_id
            cluster_points = all_points[mask]
            cluster_intensities = {}

            for idx in np.where(mask)[0]:
                s_idx, feat = feature_map[idx]
                # Keep highest intensity per sample
                if s_idx not in cluster_intensities or feat.intensity > cluster_intensities[s_idx]:
                    cluster_intensities[s_idx] = feat.intensity

            if len(cluster_intensities) >= max(1, int(n_samples * self.min_fraction)):
                group = FeatureGroup(
                    group_id=group_id,
                    consensus_mz=float(np.median(cluster_points[:, 0])),
                    consensus_rt=float(np.median(cluster_points[:, 1])),
                    mz_std=float(np.std(cluster_points[:, 0])),
                    rt_std=float(np.std(cluster_points[:, 1])),
                    sample_intensities=dict(cluster_intensities),
                    num_samples=len(cluster_intensities),
                )
                groups.append(group)
                group_id += 1

        # Sort by m/z
        groups.sort(key=lambda g: g.consensus_mz)

        # Build feature table
        n_features = len(groups)
        feature_ids = np.arange(n_features, dtype=np.int64)
        mz_values = np.array([g.consensus_mz for g in groups], dtype=np.float64)
        rt_values = np.array([g.consensus_rt for g in groups], dtype=np.float64)
        intensity_matrix = np.zeros((n_features, n_samples), dtype=np.float64)

        for i, group in enumerate(groups):
            for s_idx, intensity in group.sample_intensities.items():
                intensity_matrix[i, s_idx] = intensity

        return FeatureTable(
            sample_names=list(sample_names),
            feature_ids=feature_ids,
            mz_values=mz_values,
            rt_values=rt_values,
            intensity_matrix=intensity_matrix,
        )


# ══════════════════════════════════════════════════════════════════════
# Gap Filler
# ══════════════════════════════════════════════════════════════════════

class GapFiller:
    """Fill missing values in the feature matrix.

    Two strategies:
      1. Re-integration: Go back to raw data, integrate intensity at the
         expected m/z and RT for each missing value
      2. Imputation: Statistical methods (KNN, minimum, mean) for when
         raw data re-integration is not possible
    """

    def __init__(
        self,
        integration_mz_window_da: float = 0.02,
        integration_rt_window_sec: float = 15.0,
    ):
        self.integration_mz_window_da = integration_mz_window_da
        self.integration_rt_window_sec = integration_rt_window_sec

    def fill_by_integration(
        self,
        feature_table: FeatureTable,
        readers: List,  # List of MzMLReader (one per sample)
        all_features: List[List[DetectedFeature]],
    ) -> FeatureTable:
        """Fill missing values by re-integrating raw data.

        For each zero/NaN value in the intensity matrix, go back to the
        raw spectra and integrate the signal at the expected position.

        Args:
            feature_table: FeatureTable with missing values (zeros)
            readers: MzMLReader instances, one per sample
            all_features: Original feature lists per sample

        Returns:
            FeatureTable with gaps filled by integration
        """
        n_features = feature_table.num_features
        n_samples = feature_table.num_samples
        filled_matrix = feature_table.intensity_matrix.copy()

        for i in range(n_features):
            mz = feature_table.mz_values[i]
            rt = feature_table.rt_values[i]
            mz_min = mz - self.integration_mz_window_da
            mz_max = mz + self.integration_mz_window_da
            rt_min = rt - self.integration_rt_window_sec
            rt_max = rt + self.integration_rt_window_sec

            for s_idx in range(n_samples):
                if filled_matrix[i, s_idx] > 0:
                    continue  # Already has a value

                if s_idx >= len(readers):
                    continue

                try:
                    integrated = self._integrate_region(
                        readers[s_idx], mz_min, mz_max, rt_min, rt_max
                    )
                    filled_matrix[i, s_idx] = max(integrated, 0.0)
                except Exception:
                    pass  # Leave as zero, will be imputed later

        return FeatureTable(
            sample_names=list(feature_table.sample_names),
            feature_ids=feature_table.feature_ids.copy(),
            mz_values=feature_table.mz_values.copy(),
            rt_values=feature_table.rt_values.copy(),
            intensity_matrix=filled_matrix,
        )

    def _integrate_region(
        self,
        reader,  # MzMLReader
        mz_min: float,
        mz_max: float,
        rt_min: float,
        rt_max: float,
    ) -> float:
        """Integrate total ion current in an m/z-RT window."""
        total = 0.0
        for spec in reader.iter_spectra(
            ms_level=1,
            mz_range=(mz_min, mz_max),
            rt_range=(rt_min, rt_max),
        ):
            total += spec.total_ion_current
        return total

    def fill_by_knn(
        self,
        feature_table: FeatureTable,
        k: int = 5,
    ) -> FeatureTable:
        """Fill missing values by KNN imputation.

        Uses the k-nearest features (in m/z-RT space) to estimate
        missing values.

        Args:
            feature_table: FeatureTable with zeros for missing
            k: Number of neighbours for imputation

        Returns:
            FeatureTable with gaps filled by KNN
        """
        if feature_table.num_features < k + 1:
            return feature_table

        n_features = feature_table.num_features
        n_samples = feature_table.num_samples
        filled_matrix = feature_table.intensity_matrix.copy()

        # Scale coordinates for distance
        mz_scale = max(np.median(feature_table.mz_values), 1.0) * 5e-6
        rt_scale = 15.0

        coords = np.column_stack([
            feature_table.mz_values / mz_scale,
            feature_table.rt_values / rt_scale,
        ])

        tree = spatial.KDTree(coords)

        for i in range(n_features):
            for j in range(n_samples):
                if filled_matrix[i, j] > 0:
                    continue

                # Find k nearest neighbours
                dists, indices = tree.query(coords[i], k=k + 1)
                # Skip self (idx 0)
                neighbours = []
                for ni in indices[1:]:
                    if ni < n_features and filled_matrix[ni, j] > 0:
                        neighbours.append(filled_matrix[ni, j])

                if neighbours:
                    # Weighted by inverse distance
                    if len(dists) > len(neighbours) + 1:
                        neighbour_dists = dists[1:len(neighbours) + 1]
                    else:
                        neighbour_dists = dists[1:len(neighbours) + 1] if len(dists) > 1 else np.array([1.0] * len(neighbours))
                    weights = 1.0 / (neighbour_dists[:len(neighbours)] + 1e-6)
                    weights /= weights.sum()
                    filled_matrix[i, j] = float(np.average(neighbours, weights=weights))

        return FeatureTable(
            sample_names=list(feature_table.sample_names),
            feature_ids=feature_table.feature_ids.copy(),
            mz_values=feature_table.mz_values.copy(),
            rt_values=feature_table.rt_values.copy(),
            intensity_matrix=filled_matrix,
        )

    def fill_by_minimum(
        self,
        feature_table: FeatureTable,
        min_fraction: float = 0.2,
    ) -> FeatureTable:
        """Simple fill: replace zeros with a small fraction of the feature's minimum observed value.

        Args:
            feature_table: FeatureTable with zeros
            min_fraction: Fraction of minimum to use as fill value
        """
        filled_matrix = feature_table.intensity_matrix.copy()
        for i in range(feature_table.num_features):
            nonzero = filled_matrix[i, :][filled_matrix[i, :] > 0]
            if len(nonzero) > 0:
                fill_value = float(np.min(nonzero)) * min_fraction
                filled_matrix[i, filled_matrix[i, :] == 0] = fill_value

        return FeatureTable(
            sample_names=list(feature_table.sample_names),
            feature_ids=feature_table.feature_ids.copy(),
            mz_values=feature_table.mz_values.copy(),
            rt_values=feature_table.rt_values.copy(),
            intensity_matrix=filled_matrix,
        )


# ══════════════════════════════════════════════════════════════════════
# Feature Quality Metrics
# ══════════════════════════════════════════════════════════════════════

def compute_feature_quality(
    feature_table: FeatureTable,
) -> np.ndarray:
    """Compute quality scores for each feature in the table.

    Scores based on: detection rate, intensity consistency (CV),
    peak shape quality.
    """
    n_features = feature_table.num_features
    n_samples = feature_table.num_samples
    matrix = feature_table.intensity_matrix
    quality = np.zeros(n_features, dtype=np.float64)

    for i in range(n_features):
        row = matrix[i, :]
        nonzero = row[row > 0]
        detection_rate = len(nonzero) / n_samples

        if len(nonzero) > 1:
            cv = float(np.std(nonzero)) / max(float(np.mean(nonzero)), 1e-6)
            cv_score = max(0.0, 1.0 - cv)
        else:
            cv_score = 0.0

        intensity_score = min(1.0, np.log10(max(float(np.median(nonzero)), 1.0)) / 6.0) if len(nonzero) > 0 else 0.0

        quality[i] = detection_rate * 0.4 + cv_score * 0.3 + intensity_score * 0.3

    return quality
