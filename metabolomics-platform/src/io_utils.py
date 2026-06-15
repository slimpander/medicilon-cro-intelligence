"""
io_utils.py — mzML Reader, MSConvert Wrapper, Feature Table I/O
================================================================
Handles all raw data ingestion for the untargeted metabolomics platform.

Supports:
  - mzML via pymzml (native)
  - Vendor raw formats via MSConvert CLI wrapper
  - Feature table I/O (CSV, TSV, XLSX)
  - Spectrum-level iterators with memory-efficient chunking
"""

from __future__ import annotations

import csv
import io
import os
import re
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Iterator, Tuple, Union
from dataclasses import dataclass, field
import numpy as np


# ══════════════════════════════════════════════════════════════════════
# Dataclasses
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Spectrum:
    """A single mass spectrum (MS1 or MS2)."""
    index: int
    ms_level: int
    scan_number: int
    retention_time: float          # seconds
    precursor_mz: Optional[float] = None
    precursor_charge: Optional[int] = None
    polarity: str = "positive"
    mz: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    intensity: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    total_ion_current: float = 0.0
    source_file: str = ""

    def __post_init__(self):
        if len(self.mz) > 0 and len(self.intensity) > 0:
            self.total_ion_current = float(np.sum(self.intensity))

    @property
    def num_peaks(self) -> int:
        return len(self.mz)

    @property
    def base_peak_mz(self) -> float:
        if len(self.intensity) == 0:
            return 0.0
        return float(self.mz[np.argmax(self.intensity)])

    @property
    def base_peak_intensity(self) -> float:
        if len(self.intensity) == 0:
            return 0.0
        return float(np.max(self.intensity))

    def centroid(self, window_size: int = 5, threshold: float = 0.0) -> "Spectrum":
        """Return a centroided copy of this spectrum using local maxima detection."""
        if len(self.mz) < 3:
            return self
        mz_arr, int_arr = self.mz, self.intensity
        # Local maxima: each point > its neighbours within window
        half = window_size // 2
        n = len(mz_arr)
        centroided_mz = []
        centroided_int = []
        for i in range(half, n - half):
            local_slice = int_arr[i - half : i + half + 1]
            if int_arr[i] == np.max(local_slice) and int_arr[i] >= threshold:
                # Centroid mass: weighted average around the peak
                w = int_arr[i - 1 : i + 2]
                m = mz_arr[i - 1 : i + 2]
                if np.sum(w) > 0:
                    centre_mz = float(np.average(m, weights=w))
                    centroided_mz.append(centre_mz)
                    centroided_int.append(float(int_arr[i]))
        result = Spectrum(
            index=self.index,
            ms_level=self.ms_level,
            scan_number=self.scan_number,
            retention_time=self.retention_time,
            precursor_mz=self.precursor_mz,
            precursor_charge=self.precursor_charge,
            polarity=self.polarity,
            source_file=self.source_file,
        )
        result.mz = np.array(centroided_mz, dtype=np.float64)
        result.intensity = np.array(centroided_int, dtype=np.float64)
        result.total_ion_current = float(np.sum(result.intensity)) if len(result.intensity) > 0 else 0.0
        return result

    def filter_by_mz_range(self, mz_min: float, mz_max: float) -> "Spectrum":
        """Filter spectrum to a given m/z window."""
        mask = (self.mz >= mz_min) & (self.mz <= mz_max)
        result = Spectrum(
            index=self.index, ms_level=self.ms_level,
            scan_number=self.scan_number, retention_time=self.retention_time,
            precursor_mz=self.precursor_mz, precursor_charge=self.precursor_charge,
            polarity=self.polarity, source_file=self.source_file,
        )
        result.mz = self.mz[mask].copy()
        result.intensity = self.intensity[mask].copy()
        result.total_ion_current = float(np.sum(result.intensity)) if len(result.intensity) > 0 else 0.0
        return result


@dataclass
class DetectedFeature:
    """A detected chromatographic feature (peak in m/z-RT space)."""
    feature_id: int
    mz: float
    mz_min: float
    mz_max: float
    rt: float                        # seconds, apex
    rt_min: float
    rt_max: float
    intensity: float
    area: float
    snr: float
    peak_quality: float              # 0-1
    isotopes: List[Dict] = field(default_factory=list)
    annotation: Optional[str] = None
    adduct: Optional[str] = None


@dataclass
class FeatureTable:
    """Sample × feature matrix with metadata."""
    sample_names: List[str] = field(default_factory=list)
    feature_ids: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.int64))
    mz_values: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    rt_values: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    intensity_matrix: np.ndarray = field(default_factory=lambda: np.array([[], []], dtype=np.float64))  # features × samples

    @property
    def num_features(self) -> int:
        return len(self.feature_ids)

    @property
    def num_samples(self) -> int:
        return len(self.sample_names)

    def filter_by_min_occurrence(self, min_pct: float = 0.5) -> "FeatureTable":
        """Keep only features present in at least min_pct of samples."""
        n_required = max(1, int(self.num_samples * min_pct))
        mask = np.sum(self.intensity_matrix > 0, axis=1) >= n_required
        return FeatureTable(
            sample_names=list(self.sample_names),
            feature_ids=self.feature_ids[mask].copy(),
            mz_values=self.mz_values[mask].copy(),
            rt_values=self.rt_values[mask].copy(),
            intensity_matrix=self.intensity_matrix[mask, :].copy(),
        )

    def to_csv(self, path: str):
        """Save feature table as CSV."""
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            header = ['feature_id', 'mz', 'rt'] + list(self.sample_names)
            writer.writerow(header)
            for i in range(self.num_features):
                row = [self.feature_ids[i], f"{self.mz_values[i]:.5f}", f"{self.rt_values[i]:.2f}"]
                row.extend(f"{v:.2f}" for v in self.intensity_matrix[i, :])
                writer.writerow(row)

    @classmethod
    def from_csv(cls, path: str) -> "FeatureTable":
        """Load feature table from CSV."""
        with open(path, 'r', newline='') as f:
            reader = csv.reader(f)
            header = next(reader)
            sample_names = header[3:]
            rows = list(reader)
        n_features = len(rows)
        n_samples = len(sample_names)
        feature_ids = np.zeros(n_features, dtype=np.int64)
        mz_values = np.zeros(n_features, dtype=np.float64)
        rt_values = np.zeros(n_features, dtype=np.float64)
        intensity_matrix = np.zeros((n_features, n_samples), dtype=np.float64)
        for i, row in enumerate(rows):
            feature_ids[i] = int(row[0])
            mz_values[i] = float(row[1])
            rt_values[i] = float(row[2])
            for j in range(n_samples):
                intensity_matrix[i, j] = float(row[3 + j])
        return cls(
            sample_names=sample_names,
            feature_ids=feature_ids, mz_values=mz_values,
            rt_values=rt_values, intensity_matrix=intensity_matrix,
        )


# ══════════════════════════════════════════════════════════════════════
# mzML Reader
# ══════════════════════════════════════════════════════════════════════

class MzMLReader:
    """Memory-efficient reader for mzML files using pymzml.

    Supports iterative access — never loads the entire file into memory.
    Suitable for 500MB+ files from Thermo/Sciex/Waters/Agilent/Bruker.
    """

    def __init__(self, filepath: str):
        self.filepath = str(Path(filepath).resolve())
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"mzML file not found: {self.filepath}")
        self._run = None
        self._total_spectra = None
        self._metadata = None

    @property
    def metadata(self) -> Dict:
        """Lazily load file metadata."""
        if self._metadata is None:
            self._load_metadata()
        return self._metadata

    @property
    def total_spectra(self) -> int:
        if self._total_spectra is None:
            # Fast count: iterate without parsing peaks
            self._total_spectra = sum(1 for _ in self._iter_raw())
        return self._total_spectra

    def _iter_raw(self):
        import pymzml
        if self._run is None:
            self._run = pymzml.run.Reader(self.filepath)
        return self._run

    def _load_metadata(self):
        """Extract file-level metadata from the mzML header."""
        try:
            run = self._iter_raw()
            # Access the mzML obo metadata
            meta = {
                "filepath": self.filepath,
                "filename": Path(self.filepath).name,
                "file_size_mb": round(os.path.getsize(self.filepath) / (1024 * 1024), 1),
                "instrument": "",
                "ms_levels": set(),
                "polarities": set(),
                "rt_range": [float("inf"), float("-inf")],
                "mz_range": [float("inf"), float("-inf")],
            }
            # Try to extract instrument name from the mzML source
            try:
                meta["instrument"] = getattr(run, "description", "") or ""
            except Exception:
                meta["instrument"] = ""
        except Exception:
            meta = {"filepath": self.filepath, "filename": Path(self.filepath).name, "error": "Could not parse metadata"}
        self._metadata = meta

    def iter_spectra(
        self,
        ms_level: int = 1,
        mz_range: Optional[Tuple[float, float]] = None,
        rt_range: Optional[Tuple[float, float]] = None,
    ) -> Iterator[Spectrum]:
        """Iterate over spectra matching the given filters.

        Args:
            ms_level: MS level (1 for MS1 survey, 2 for MS/MS)
            mz_range: Optional (mz_min, mz_max) filter
            rt_range: Optional (rt_min_sec, rt_max_sec) filter
        """
        import pymzml
        try:
            run = self._iter_raw()
            source_name = Path(self.filepath).name
            idx = 0
            for scan in run:
                try:
                    spec_ms_level = scan.get('ms level', 1)
                    if spec_ms_level != ms_level:
                        continue
                except Exception:
                    continue

                rt = float(scan.get("scan start time", 0.0))
                if rt_range and (rt < rt_range[0] or rt > rt_range[1]):
                    continue

                # Get m/z and intensity arrays
                try:
                    mz_arr = scan.mz.copy() if hasattr(scan, 'mz') else np.array([])
                    int_arr = scan.i.copy() if hasattr(scan, 'i') else np.array([])
                except Exception:
                    continue

                if len(mz_arr) == 0:
                    continue

                if mz_range:
                    mask = (mz_arr >= mz_range[0]) & (mz_arr <= mz_range[1])
                    mz_arr = mz_arr[mask]
                    int_arr = int_arr[mask]

                polarity = "positive"
                try:
                    pol = scan.get("polarity", "+")
                    if hasattr(pol, 'lower'):
                        polarity = "positive" if "+" in str(pol) else "negative"
                except Exception:
                    pass

                precursor_mz = None
                precursor_charge = None
                if ms_level > 1:
                    try:
                        precursor_mz = float(scan.get("selected ion m/z", 0))
                        precursor_charge = int(scan.get("charge", 1))
                    except Exception:
                        pass

                spec = Spectrum(
                    index=idx,
                    ms_level=spec_ms_level,
                    scan_number=scan.get("num", idx + 1),
                    retention_time=rt,
                    precursor_mz=precursor_mz,
                    precursor_charge=precursor_charge,
                    polarity=polarity,
                    source_file=source_name,
                )
                spec.mz = mz_arr.astype(np.float64)
                spec.intensity = int_arr.astype(np.float64)
                spec.total_ion_current = float(np.sum(spec.intensity)) if len(spec.intensity) > 0 else 0.0
                yield spec
                idx += 1
        except Exception as e:
            raise RuntimeError(f"Error reading mzML file: {e}") from e

    def get_spectrum(self, index: int, ms_level: int = 1) -> Optional[Spectrum]:
        """Retrieve a specific spectrum by index."""
        for i, spec in enumerate(self.iter_spectra(ms_level=ms_level)):
            if i == index:
                return spec
        return None

    def get_tic_chromatogram(self, ms_level: int = 1) -> Tuple[np.ndarray, np.ndarray]:
        """Return (retention_times, total_ion_current) as arrays."""
        rts = []
        tics = []
        for spec in self.iter_spectra(ms_level=ms_level):
            rts.append(spec.retention_time)
            tics.append(spec.total_ion_current)
        return np.array(rts, dtype=np.float64), np.array(tics, dtype=np.float64)

    def get_bpc_chromatogram(self, ms_level: int = 1) -> Tuple[np.ndarray, np.ndarray]:
        """Return (retention_times, base_peak_intensity) as arrays."""
        rts = []
        bpcs = []
        for spec in self.iter_spectra(ms_level=ms_level):
            rts.append(spec.retention_time)
            bpcs.append(spec.base_peak_intensity)
        return np.array(rts, dtype=np.float64), np.array(bpcs, dtype=np.float64)


# ══════════════════════════════════════════════════════════════════════
# MSConvert Wrapper (vendor raw → mzML)
# ══════════════════════════════════════════════════════════════════════

class MSConvertWrapper:
    """CLI wrapper for ProteoWizard msconvert.

    Converts vendor formats (.raw, .wiff, .d, .lcd, etc.) to mzML.
    Requires ProteoWizard to be installed and on PATH.
    """

    VENDOR_EXTENSIONS = {
        ".raw": "Thermo",
        ".wiff": "Sciex",
        ".wiff2": "Sciex",
        ".d": "Agilent/Bruker",
        ".lcd": "Shimadzu",
        ".mzxml": "mzXML (legacy)",
    }

    def __init__(self, msconvert_path: str = "msconvert"):
        self.msconvert = shutil.which(msconvert_path) or msconvert_path

    @property
    def is_available(self) -> bool:
        """Check if msconvert is installed and accessible."""
        try:
            subprocess.run(
                [self.msconvert, "--help"],
                capture_output=True, timeout=10
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def detect_vendor(self, filepath: str) -> str:
        """Detect the vendor from the file extension."""
        ext = Path(filepath).suffix.lower()
        return self.VENDOR_EXTENSIONS.get(ext, "Unknown")

    def convert(
        self,
        input_path: str,
        output_dir: Optional[str] = None,
        peak_picking: bool = True,
        peak_picking_level: int = 1,
        compression: bool = False,
        timeout: int = 600,
    ) -> str:
        """Convert a vendor raw file to mzML.

        Args:
            input_path: Path to the raw file
            output_dir: Output directory (default: same as input)
            peak_picking: Apply centroiding during conversion
            peak_picking_level: MS level for peak picking (1 = MS1, 2 = MS1+MS2)
            compression: gzip output (mzML.gz)
            timeout: Maximum wait time in seconds

        Returns:
            Path to the output mzML file
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if not self.is_available:
            raise RuntimeError(
                "msconvert not found. Install ProteoWizard from: "
                "https://proteowizard.sourceforge.io/download.html"
            )

        input_path = str(Path(input_path).resolve())
        if output_dir is None:
            output_dir = str(Path(input_path).parent)
        else:
            output_dir = str(Path(output_dir))
            os.makedirs(output_dir, exist_ok=True)

        vendor = self.detect_vendor(input_path)
        base_name = Path(input_path).stem

        cmd = [self.msconvert, input_path, "-o", output_dir, "--mzML"]
        if peak_picking:
            cmd.extend(["--filter", f"peakPicking true {peak_picking_level}-"])
        if compression:
            cmd.append("-z")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode != 0:
                stderr = result.stderr.strip()
                raise RuntimeError(f"msconvert failed (exit {result.returncode}): {stderr}")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"msconvert timed out after {timeout}s on {input_path}")
        except FileNotFoundError:
            raise RuntimeError(f"msconvert executable not found: {self.msconvert}")

        # Find the output file
        ext = ".mzML.gz" if compression else ".mzML"
        expected = os.path.join(output_dir, base_name + ext)
        if os.path.exists(expected):
            return expected
        # msconvert might use lowercase extension
        for f in Path(output_dir).glob(f"{base_name}*{ext.lower()}"):
            return str(f)
        for f in Path(output_dir).glob(f"{base_name}*.mzML"):
            return str(f)
        raise RuntimeError(f"Output mzML file not found after successful conversion")


# ══════════════════════════════════════════════════════════════════════
# Utility functions
# ══════════════════════════════════════════════════════════════════════

def ppm_to_da(ppm: float, mz: float) -> float:
    """Convert ppm tolerance to Da at a given m/z."""
    return ppm * mz / 1e6


def da_to_ppm(da: float, mz: float) -> float:
    """Convert Da tolerance to ppm at a given m/z."""
    if mz == 0:
        return float("inf")
    return da / mz * 1e6


def bin_spectrum(
    mz: np.ndarray,
    intensity: np.ndarray,
    bin_width: float = 0.01,
    mz_min: Optional[float] = None,
    mz_max: Optional[float] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Bin a spectrum by summing intensities in m/z bins."""
    if mz_min is None:
        mz_min = float(np.min(mz))
    if mz_max is None:
        mz_max = float(np.max(mz))
    num_bins = int(np.ceil((mz_max - mz_min) / bin_width))
    binned = np.zeros(num_bins, dtype=np.float64)
    bin_centres = np.linspace(mz_min + bin_width / 2, mz_max - bin_width / 2, num_bins)
    for m, i in zip(mz, intensity):
        idx = int((m - mz_min) / bin_width)
        if 0 <= idx < num_bins:
            binned[idx] += i
    return bin_centres, binned
