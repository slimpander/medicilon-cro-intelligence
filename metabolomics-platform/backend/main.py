"""
Metabolomics Platform v0.2.0 — FastAPI Backend
================================================
Serves the untargeted metabolomics pipeline via REST API and hosts the Web UI.

Endpoints:
  - POST /api/upload        Upload mzML/vendor files
  - GET  /api/files         List uploaded files
  - POST /api/pipeline/run  Run full pipeline
  - POST /api/stats/pca     PCA analysis
  - POST /api/stats/plsda   PLS-DA analysis
  - POST /api/stats/volcano Volcano plot
  - POST /api/stats/pathway Pathway enrichment
  - POST /api/annotate      Metabolite annotation
  - GET  /api/export/csv    Export results
"""

from __future__ import annotations

import sys, os, json, shutil, tempfile, uuid, io, asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Ensure parent is on path for src imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import csv

from src.io_utils import Spectrum, FeatureTable, DetectedFeature, bin_spectrum, MzMLReader
from src.peak_engine import PeakPicker, FeatureDetector, PeakCandidate, ROI, PeakDetectionPipeline
from src.alignment_engine import RTAligner, ConsensusBuilder, groupwise_alignment
from src.grouping_engine import DensityFeatureGrouper, GapFiller, compute_feature_quality
from src.stats_engine import (
    normalize_total_ion, normalize_median, log_transform, pareto_scale, auto_scale,
    pca, pls_da, volcano, pathway_enrichment, univariate_analysis,
)
from src.db_annotator import MetaboliteAnnotator, export_annotations_csv

# ═══════════════════════════════════════════════════════════════
# App setup
# ═══════════════════════════════════════════════════════════════

app = FastAPI(
    title="Metabolomics Platform",
    version="0.3.0",
    description="Untargeted Metabolomics Analysis Pipeline"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory state for demo/synthetic data
_synthetic_data: Optional[Dict] = None
_last_pipeline_result: Optional[Dict] = None
_uploaded_files: List[Dict] = []


# ═══════════════════════════════════════════════════════════════
# Pydantic models
# ═══════════════════════════════════════════════════════════════

class PipelineParams(BaseModel):
    snr_threshold: float = 3.0
    min_intensity: float = 500.0
    peak_width_min: float = 0.005
    peak_width_max: float = 0.5
    mz_tolerance_da: float = 0.02
    min_scans: int = 5
    mz_bandwidth_ppm: float = 5.0
    rt_bandwidth_sec: float = 10.0
    alignment_method: str = "loess"
    gap_fill_method: str = "knn"
    generate_synthetic: bool = True
    n_synthetic_metabolites: int = 15
    n_synthetic_scans: int = 200
    filenames: Optional[List[str]] = None
    group_labels: Optional[List[str]] = None

class BatchPipelineParams(BaseModel):
    snr_threshold: float = 3.0
    min_intensity: float = 500.0
    peak_width_min: float = 0.005
    peak_width_max: float = 0.5
    mz_tolerance_da: float = 0.02
    min_scans: int = 5
    mz_bandwidth_ppm: float = 5.0
    rt_bandwidth_sec: float = 10.0
    alignment_method: str = "loess"
    gap_fill_method: str = "knn"
    filenames: List[str]
    group_labels: List[str]

class StatsParams(BaseModel):
    n_components: int = 3
    scale: str = "pareto"
    group_labels: Optional[List[str]] = None
    group_a_indices: Optional[List[int]] = None
    group_b_indices: Optional[List[int]] = None
    fold_change_threshold: float = 1.0
    p_value_threshold: float = 0.05
    test_method: str = "ttest"

class AnnotationParams(BaseModel):
    mass_tolerance_ppm: float = 10.0
    mode: str = "positive"
    use_online: bool = False
    max_matches: int = 5

class PathwayParams(BaseModel):
    significance_mask: Optional[List[bool]] = None
    mz_tolerance_ppm: float = 10.0
    database: str = "KEGG"


# ═══════════════════════════════════════════════════════════════
# Synthetic data generator
# ═══════════════════════════════════════════════════════════════

KNOWN_PEAKS = [
    {"name": "Caffeine",         "mz": 195.0877, "rt": 150, "intensity": 8e4},
    {"name": "Theobromine",      "mz": 181.0720, "rt": 120, "intensity": 7e4},
    {"name": "Acetaminophen",    "mz": 152.0570, "rt": 200, "intensity": 9e4},
    {"name": "4-Aminobenzoic",   "mz": 138.0550, "rt": 90,  "intensity": 5e4},
    {"name": "Paraxanthine",     "mz": 181.0725, "rt": 160, "intensity": 4e4},
    {"name": "Hippuric Acid",    "mz": 180.0655, "rt": 140, "intensity": 6e4},
]

def generate_synthetic_data(params: PipelineParams) -> Dict:
    """Generate synthetic metabolomics data for testing."""
    import numpy as np
    np.random.seed(42)

    known = KNOWN_PEAKS[:params.n_synthetic_metabolites]
    n_scans = params.n_synthetic_scans
    chromatographic_width = 8.0

    spectra = []
    rts_list = []
    for scan_idx in range(n_scans):
        rt = scan_idx * 1.0
        rts_list.append(rt)
        peaks_mz = []
        peaks_int = []
        for pk in known:
            rt_diff = rt - pk["rt"]
            intensity = pk["intensity"] * np.exp(-rt_diff ** 2 / (2 * chromatographic_width ** 2))
            if intensity > 100:
                x = np.linspace(pk["mz"] - 0.025, pk["mz"] + 0.025, 21)
                y = intensity * np.exp(-((x - pk["mz"]) ** 2) / (2 * 0.005 ** 2))
                peaks_mz.extend(x.tolist())
                peaks_int.extend(y.tolist())
        for _ in range(200):
            peaks_mz.append(np.random.uniform(100, 300))
            peaks_int.append(np.random.exponential(300))
        order = np.argsort(peaks_mz)
        mz_arr = np.array([peaks_mz[i] for i in order], dtype=np.float64)
        int_arr = np.array([peaks_int[i] for i in order], dtype=np.float64)
        spec = Spectrum(index=scan_idx, ms_level=1, scan_number=scan_idx + 1, retention_time=rt, polarity="positive")
        spec.mz = mz_arr
        spec.intensity = int_arr
        spec.total_ion_current = float(np.sum(int_arr))
        spectra.append(spec)

    rts = np.array(rts_list, dtype=np.float64)

    # Create 3 replicates with RT shifts
    reps = []
    shifts = [0, 3, -2]
    for rep_idx, shift in enumerate(shifts):
        rep_spectra = []
        for spec in spectra:
            s2 = Spectrum(
                index=spec.index, ms_level=1, scan_number=spec.scan_number,
                retention_time=spec.retention_time + shift, polarity="positive",
            )
            s2.mz = spec.mz + np.random.uniform(-0.001, 0.001, len(spec.mz))
            s2.intensity = spec.intensity * np.random.uniform(0.85, 1.15, len(spec.intensity))
            s2.total_ion_current = float(np.sum(s2.intensity))
            rep_spectra.append(s2)
        reps.append(rep_spectra)

    sample_names = ["Rep1", "Rep2", "Rep3"]

    return {
        "spectra": spectra,
        "replicates": reps,
        "rts": rts,
        "sample_names": sample_names,
        "known_peaks": known,
    }


def run_pipeline_on_spectra(spectra_list, rts, params: PipelineParams) -> Dict:
    """Run full pipeline on a list of spectra."""
    picker = PeakPicker(
        snr_threshold=params.snr_threshold,
        min_intensity=params.min_intensity,
        peak_width_range=(params.peak_width_min, params.peak_width_max),
    )
    detector = FeatureDetector(
        mz_tolerance_da=params.mz_tolerance_da,
        min_scans=params.min_scans,
        min_intensity=params.min_intensity,
    )

    all_peaks = [picker.detect_peaks(s) for s in spectra_list]
    rois = detector.extract_rois(all_peaks, rts)

    features = []
    for roi in rois:
        snr_val = roi.max_intensity / (float(np.std(roi.intensities)) + 1.0) if len(roi.intensities) > 1 else 1.0
        quality = min(1.0, roi.num_scans / max(params.min_scans * 3, 1))
        features.append(DetectedFeature(
            feature_id=roi.roi_id, mz=roi.mz,
            mz_min=roi.mz_min, mz_max=roi.mz_max,
            rt=roi.rt_apex, rt_min=roi.rt_start, rt_max=roi.rt_end,
            intensity=roi.max_intensity, area=roi.peak_area,
            snr=float(snr_val), peak_quality=float(quality),
        ))

    return {
        "total_peaks": sum(len(p) for p in all_peaks),
        "rois": len(rois),
        "features": len(features),
        "peak_summary": [
            {"mz": round(r.mz, 4), "rt": round(r.rt_apex, 1), "intensity": round(r.max_intensity, 0), "area": round(r.peak_area, 0), "scans": r.num_scans}
            for r in sorted(rois, key=lambda r: r.max_intensity, reverse=True)[:20]
        ],
        "feature_ids": [f.feature_id for f in features],
        "mz_values": [round(f.mz, 4) for f in features],
        "rt_values": [round(f.rt, 1) for f in features],
        "intensities": [round(f.intensity, 0) for f in features],
    }


# ═══════════════════════════════════════════════════════════════
# Real data loader (mzML files)
# ═══════════════════════════════════════════════════════════════

def _load_real_data_from_file(filename: str) -> Dict:
    """Load real mzML data from an uploaded file."""
    filepath = UPLOAD_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filename}")

    reader = MzMLReader(str(filepath))
    spectra = list(reader.iter_spectra(ms_level=1))
    if not spectra:
        raise ValueError(f"No MS1 spectra found in {filename}")

    rts = np.array([s.retention_time for s in spectra], dtype=np.float64)
    meta = reader.metadata

    return {
        "spectra": spectra,
        "replicates": [spectra],
        "rts_per_rep": [rts],
        "rts": rts,
        "sample_names": [Path(filename).stem],
        "known_peaks": [],
        "instrument": meta.get("instrument", "") or "Unknown",
        "file_size_mb": meta.get("file_size_mb", 0),
        "total_scans": len(spectra),
        "data_source": "mzML file",
    }


def _load_real_data_from_files(
    filenames: List[str],
    group_labels: Optional[List[str]] = None,
) -> Dict:
    """Load multiple mzML files, each as one sample/replicate."""
    all_reps = []
    all_rts_per_rep = []
    sample_names = []
    total_scans = 0

    for i, fname in enumerate(filenames):
        filepath = UPLOAD_DIR / fname
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {fname}")

        reader = MzMLReader(str(filepath))
        spectra = list(reader.iter_spectra(ms_level=1))
        if not spectra:
            raise ValueError(f"No MS1 spectra found in {fname}")

        rts = np.array([s.retention_time for s in spectra], dtype=np.float64)
        all_reps.append(spectra)
        all_rts_per_rep.append(rts)
        total_scans += len(spectra)

        if group_labels and i < len(group_labels):
            sample_names.append(group_labels[i])
        else:
            sample_names.append(Path(fname).stem)

    return {
        "spectra": all_reps[0],
        "replicates": all_reps,
        "rts_per_rep": all_rts_per_rep,
        "rts": all_rts_per_rep[0],
        "sample_names": sample_names,
        "known_peaks": [],
        "file_count": len(filenames),
        "total_scans": total_scans,
        "data_source": "mzML files",
    }


# ═══════════════════════════════════════════════════════════════
# API Routes — File Management
# ═══════════════════════════════════════════════════════════════

@app.get("/api/files")
async def list_files():
    """List uploaded files."""
    files = []
    for f in UPLOAD_DIR.iterdir():
        if f.is_file():
            files.append({
                "name": f.name,
                "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    return {"files": files}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload an mzML or vendor raw file."""
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    filepath = UPLOAD_DIR / file.filename
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)
    _uploaded_files.append({
        "name": file.filename,
        "path": str(filepath),
        "size_mb": round(len(content) / (1024 * 1024), 2),
    })
    return {"status": "ok", "filename": file.filename, "size_mb": round(len(content) / (1024 * 1024), 2)}


@app.delete("/api/files/{filename}")
async def delete_file(filename: str):
    """Delete an uploaded file."""
    filepath = UPLOAD_DIR / filename
    if filepath.exists():
        filepath.unlink()
        return {"status": "deleted"}
    raise HTTPException(404, "File not found")


@app.get("/api/files/info/{filename}")
async def file_info(filename: str):
    """Get metadata for an uploaded mzML file."""
    filepath = UPLOAD_DIR / filename
    if not filepath.exists():
        raise HTTPException(404, "File not found")

    try:
        reader = MzMLReader(str(filepath))
        meta = reader.metadata
        total = reader.total_spectra
        rts, tics = reader.get_tic_chromatogram(ms_level=1)
        rts_bpc, bpcs = reader.get_bpc_chromatogram(ms_level=1)

        return {
            "filename": filename,
            "file_size_mb": meta.get("file_size_mb", 0),
            "instrument": meta.get("instrument", "Unknown"),
            "total_spectra": total,
            "ms_levels": sorted(meta.get("ms_levels", {1})),
            "polarities": sorted(meta.get("polarities", {"positive"})),
            "rt_range_sec": [
                0.0 if v == float("inf") or v == float("-inf") else v
                for v in meta.get("rt_range", [0, 0])
            ],
            "tic_max": round(float(np.max(tics)) if len(tics) > 0 else 0, 0),
            "bpc_max": round(float(np.max(bpcs)) if len(bpcs) > 0 else 0, 0),
            "tic_chromatogram": {
                "rts": [round(float(r), 2) for r in rts[::max(1, len(rts) // 200)]],
                "tics": [round(float(t), 0) for t in tics[::max(1, len(tics) // 200)]],
            } if len(rts) > 0 else None,
        }
    except Exception as e:
        return {"filename": filename, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# API Routes — Pipeline
# ═══════════════════════════════════════════════════════════════

@app.post("/api/pipeline/run")
async def run_pipeline(params: PipelineParams):
    """Run the full metabolomics pipeline.

    Supports three modes:
      1. Synthetic data (generate_synthetic=True, default)
      2. Single real mzML file (filenames=["file.mzML"])
      3. Multiple real mzML files as replicates (filenames=["a.mzML", "b.mzML"])
    """
    global _synthetic_data, _last_pipeline_result

    # Determine data source
    if params.filenames and len(params.filenames) > 0:
        if len(params.filenames) == 1:
            data = _load_real_data_from_file(params.filenames[0])
        else:
            data = _load_real_data_from_files(params.filenames, params.group_labels)
    elif params.generate_synthetic:
        _synthetic_data = generate_synthetic_data(params)
        data = _synthetic_data
    elif _synthetic_data is None:
        raise HTTPException(400, "No data available. Enable generate_synthetic or upload files first.")
    else:
        data = _synthetic_data

    reps = data["replicates"]
    rts_per_rep = data.get("rts_per_rep", [data["rts"]] * len(reps))

    # Run pipeline on all replicates
    rep_results = []
    all_features = []
    for rep_idx in range(len(reps)):
        spectra_list = reps[rep_idx]
        rep_rts = rts_per_rep[rep_idx] if rep_idx < len(rts_per_rep) else rts_per_rep[0]

        result = run_pipeline_on_spectra(spectra_list, rep_rts, params)
        rep_results.append(result)

        # Build DetectedFeatures
        feat_list = []
        for i, (mz, rt, intensity, area) in enumerate(zip(
            result["mz_values"], result["rt_values"],
            result["intensities"], [r["area"] for r in result["peak_summary"]]
        )):
            feat_list.append(DetectedFeature(
                feature_id=i, mz=mz, mz_min=mz - 0.01, mz_max=mz + 0.01,
                rt=rt, rt_min=rt - 5, rt_max=rt + 5,
                intensity=intensity, area=area, snr=5.0, peak_quality=0.8,
            ))
        all_features.append(feat_list)

    # Alignment (skip if only 1 sample)
    alignment_report = []
    if len(reps) > 1:
        aligner = RTAligner(method=params.alignment_method)
        warpings = aligner.fit(all_features)
        alignment_report = [
            {"sample": i, "landmarks": w.n_landmarks, "shift_median": round(w.shift_median, 2), "shift_max": round(w.shift_max, 2)}
            for i, w in enumerate(warpings)
        ]

    # Grouping
    grouper = DensityFeatureGrouper(
        mz_bandwidth_ppm=params.mz_bandwidth_ppm,
        rt_bandwidth_sec=params.rt_bandwidth_sec,
    )
    ft = grouper.group(all_features, data["sample_names"])

    # Gap filling
    gf = GapFiller()
    if params.gap_fill_method == "knn":
        ft_filled = gf.fill_by_knn(ft, k=3)
    elif params.gap_fill_method == "minimum":
        ft_filled = gf.fill_by_minimum(ft)
    else:
        ft_filled = ft

    quality = compute_feature_quality(ft_filled)

    # Build response
    _last_pipeline_result = {
        "replicates": rep_results,
        "alignment": alignment_report,
        "grouped_features": ft.num_features,
        "n_samples": ft.num_samples,
        "sample_names": ft.sample_names,
        "feature_matrix_shape": list(ft_filled.intensity_matrix.shape),
        "missing_pct": round(float(np.sum(ft.intensity_matrix == 0)) / max(ft.intensity_matrix.size, 1) * 100, 1),
        "quality_scores": [round(float(q), 3) for q in quality],
        "top_features": [
            {
                "id": int(ft.feature_ids[i]),
                "mz": round(float(ft.mz_values[i]), 4),
                "rt": round(float(ft.rt_values[i]), 1),
                "intensities": [round(float(ft_filled.intensity_matrix[i, j]), 0) for j in range(ft.num_samples)],
                "quality": round(float(quality[i]), 3),
            }
            for i in sorted(range(ft.num_features), key=lambda x: quality[x], reverse=True)[:20]
        ],
        "known_peaks": data.get("known_peaks", []),
        "pipeline_params": params.model_dump(),
        "data_source": data.get("data_source", "synthetic"),
    }

    return _last_pipeline_result


@app.post("/api/pipeline/batch")
async def run_batch_pipeline(params: BatchPipelineParams):
    """Run pipeline on multiple mzML files with cross-file alignment.

    Each file is processed independently, then features are aligned
    and grouped across all files into a unified feature table.
    """
    global _last_pipeline_result

    if not params.filenames:
        raise HTTPException(400, "At least one filename required")

    if len(params.group_labels) != len(params.filenames):
        raise HTTPException(
            400,
            f"Number of group labels ({len(params.group_labels)}) must match "
            f"number of files ({len(params.filenames)})"
        )

    # Load all files
    data = _load_real_data_from_files(params.filenames, params.group_labels)
    reps = data["replicates"]
    rts_per_rep = data["rts_per_rep"]
    sample_names = data["sample_names"]

    # Process each file independently
    rep_results = []
    all_features = []
    file_summaries = []

    for rep_idx in range(len(reps)):
        spectra_list = reps[rep_idx]
        rep_rts = rts_per_rep[rep_idx]

        result = run_pipeline_on_spectra(spectra_list, rep_rts, params)
        rep_results.append(result)
        file_summaries.append({
            "file": params.filenames[rep_idx],
            "label": sample_names[rep_idx],
            "total_peaks": result["total_peaks"],
            "rois": result["rois"],
            "features": result["features"],
        })

        feat_list = []
        for i, (mz, rt, intensity, area) in enumerate(zip(
            result["mz_values"], result["rt_values"],
            result["intensities"], [r["area"] for r in result["peak_summary"]]
        )):
            feat_list.append(DetectedFeature(
                feature_id=i, mz=mz, mz_min=mz - 0.01, mz_max=mz + 0.01,
                rt=rt, rt_min=rt - 5, rt_max=rt + 5,
                intensity=intensity, area=area, snr=5.0, peak_quality=0.8,
            ))
        all_features.append(feat_list)

    # Cross-file alignment
    aligner = RTAligner(method=params.alignment_method)
    warpings = aligner.fit(all_features)
    alignment_report = [
        {"file": params.filenames[i], "label": sample_names[i],
         "landmarks": w.n_landmarks, "shift_median": round(w.shift_median, 2),
         "shift_max": round(w.shift_max, 2)}
        for i, w in enumerate(warpings)
    ]

    # Group across all files
    grouper = DensityFeatureGrouper(
        mz_bandwidth_ppm=params.mz_bandwidth_ppm,
        rt_bandwidth_sec=params.rt_bandwidth_sec,
    )
    ft = grouper.group(all_features, sample_names)

    # Gap filling
    gf = GapFiller()
    if params.gap_fill_method == "knn":
        ft_filled = gf.fill_by_knn(ft, k=3)
    elif params.gap_fill_method == "minimum":
        ft_filled = gf.fill_by_minimum(ft)
    else:
        ft_filled = ft

    quality = compute_feature_quality(ft_filled)

    # Build response
    _last_pipeline_result = {
        "replicates": rep_results,
        "file_summaries": file_summaries,
        "alignment": alignment_report,
        "grouped_features": ft.num_features,
        "n_samples": ft.num_samples,
        "sample_names": ft.sample_names,
        "feature_matrix_shape": list(ft_filled.intensity_matrix.shape),
        "missing_pct": round(float(np.sum(ft.intensity_matrix == 0)) / max(ft.intensity_matrix.size, 1) * 100, 1),
        "quality_scores": [round(float(q), 3) for q in quality],
        "top_features": [
            {
                "id": int(ft.feature_ids[i]),
                "mz": round(float(ft.mz_values[i]), 4),
                "rt": round(float(ft.rt_values[i]), 1),
                "intensities": [round(float(ft_filled.intensity_matrix[i, j]), 0) for j in range(ft.num_samples)],
                "quality": round(float(quality[i]), 3),
            }
            for i in sorted(range(ft.num_features), key=lambda x: quality[x], reverse=True)[:20]
        ],
        "known_peaks": [],
        "pipeline_params": params.model_dump(),
        "data_source": "batch_mzML",
    }

    return _last_pipeline_result


# ═══════════════════════════════════════════════════════════════
# API Routes — Statistics
# ═══════════════════════════════════════════════════════════════

@app.post("/api/stats/pca")
async def run_pca(params: StatsParams):
    """Run PCA on the last pipeline result."""
    global _last_pipeline_result
    if _last_pipeline_result is None:
        raise HTTPException(400, "Run pipeline first")

    ft = _build_feature_table(_last_pipeline_result)

    if ft.num_samples < 2:
        raise HTTPException(400, f"PCA requires at least 2 samples (got {ft.num_samples}). Run pipeline with multiple files or use synthetic mode.")

    ft_log = log_transform(ft, base=2)
    ft_scaled = pareto_scale(ft_log) if params.scale == "pareto" else auto_scale(ft_log) if params.scale == "auto" else ft_log

    result = pca(ft_scaled, n_components=min(params.n_components, ft.num_samples, ft.num_features))

    return {
        "n_components": result.n_components,
        "variance_explained": [round(float(v), 4) for v in result.variance_explained],
        "cumulative_variance": [round(float(v), 4) for v in result.cumulative_variance],
        "scores": [[round(float(s), 4) for s in row] for row in result.scores.tolist()],
        "loadings": [[round(float(l), 4) for l in row] for row in result.loadings.T.tolist()],
        "sample_names": _last_pipeline_result.get("sample_names", []),
        "feature_mz": [round(float(m), 4) for m in ft.mz_values],
        "feature_rt": [round(float(r), 1) for r in ft.rt_values],
    }


@app.post("/api/stats/plsda")
async def run_plsda(params: StatsParams):
    """Run PLS-DA on the last pipeline result."""
    global _last_pipeline_result
    if _last_pipeline_result is None:
        raise HTTPException(400, "Run pipeline first")

    ft = _build_feature_table(_last_pipeline_result)
    ft_log = log_transform(ft, base=2)

    if params.group_labels is None:
        params.group_labels = _last_pipeline_result.get("sample_names", [])

    # Validate group_labels match sample count
    n_samples = ft.num_samples
    if len(params.group_labels) != n_samples:
        raise HTTPException(
            400,
            f"Number of group labels ({len(params.group_labels)}) must match "
            f"number of samples ({n_samples}). "
            f"Pipeline result has samples: {ft.sample_names}. "
            f"Provide exactly {n_samples} labels."
        )

    try:
        result = pls_da(ft_log, params.group_labels, n_components=min(params.n_components, 3))

        return {
            "n_components": result.n_components,
            "class_labels": result.class_labels,
            "r2x": [round(float(v), 4) for v in result.r2x],
            "r2y": [round(float(v), 4) for v in result.r2y],
            "scores": [[round(float(s), 4) for s in row] for row in result.scores.tolist()],
            "vip_scores": [round(float(v), 4) for v in result.vip_scores],
            "feature_mz": [round(float(m), 4) for m in ft.mz_values],
        }
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"PLS-DA failed: {e}")


@app.post("/api/stats/volcano")
async def run_volcano(params: StatsParams):
    """Run volcano plot analysis."""
    global _last_pipeline_result
    if _last_pipeline_result is None:
        raise HTTPException(400, "Run pipeline first")

    ft = _build_feature_table(_last_pipeline_result)

    if params.group_a_indices is None:
        n = ft.num_samples
        params.group_a_indices = list(range(n // 2))
    if params.group_b_indices is None:
        n = ft.num_samples
        params.group_b_indices = list(range(n // 2, n))

    result = volcano(
        ft, params.group_a_indices, params.group_b_indices,
        fold_change_threshold=params.fold_change_threshold,
        p_value_threshold=params.p_value_threshold,
        test_method=params.test_method,
    )

    return {
        "group_a": result.group_a,
        "group_b": result.group_b,
        "n_significant": result.n_significant,
        "n_upregulated": result.n_upregulated,
        "n_downregulated": result.n_downregulated,
        "features": [
            {
                "id": int(result.feature_ids[i]),
                "mz": round(float(result.mz_values[i]), 4),
                "rt": round(float(result.rt_values[i]), 1),
                "log2_fc": round(float(result.fold_changes[i]), 4),
                "p_value": float(result.p_values[i]),
                "q_value": float(result.q_values[i]),
                "significant": bool(result.significant[i]),
                "direction": "up" if result.upregulated[i] else "down" if result.downregulated[i] else "ns",
            }
            for i in range(len(result.feature_ids))
        ],
    }


@app.post("/api/stats/pathway")
async def run_pathway(params: PathwayParams):
    """Run pathway enrichment analysis."""
    global _last_pipeline_result
    if _last_pipeline_result is None:
        raise HTTPException(400, "Run pipeline first")

    ft = _build_feature_table(_last_pipeline_result)

    if params.significance_mask is None:
        # Default: top 50% by quality
        quality = compute_feature_quality(ft)
        median_q = np.median(quality)
        params.significance_mask = (quality >= median_q).tolist()

    sig_mask = np.array(params.significance_mask, dtype=bool)

    enrichment = pathway_enrichment(ft, sig_mask, database=params.database)

    return {
        "total_features": enrichment.total_features,
        "significant_features": enrichment.significant_features,
        "database": enrichment.database,
        "pathways": [
            {
                "id": r.pathway_id,
                "name": r.pathway_name,
                "total": r.n_total_in_pathway,
                "matched": r.n_matched,
                "hits": r.n_significant,
                "expected": round(r.expected, 2),
                "p_value": float(r.p_value),
                "q_value": float(r.q_value),
                "enrichment_ratio": round(r.enrichment_ratio, 2),
            }
            for r in enrichment.results
        ],
    }


# ═══════════════════════════════════════════════════════════════
# API Routes — Annotation
# ═══════════════════════════════════════════════════════════════

@app.post("/api/annotate")
async def annotate_features(params: AnnotationParams):
    """Annotate features from the last pipeline run."""
    global _last_pipeline_result
    if _last_pipeline_result is None:
        raise HTTPException(400, "Run pipeline first")

    ft = _build_feature_table(_last_pipeline_result)

    annotator = MetaboliteAnnotator(
        mass_tolerance_ppm=params.mass_tolerance_ppm,
        mode=params.mode,
        use_online=params.use_online,
    )

    # Build DetectedFeature list
    features = []
    for i in range(ft.num_features):
        features.append(DetectedFeature(
            feature_id=int(ft.feature_ids[i]),
            mz=float(ft.mz_values[i]),
            mz_min=float(ft.mz_values[i]) - 0.01,
            mz_max=float(ft.mz_values[i]) + 0.01,
            rt=float(ft.rt_values[i]),
            rt_min=float(ft.rt_values[i]) - 5,
            rt_max=float(ft.rt_values[i]) + 5,
            intensity=float(np.max(ft.intensity_matrix[i, :])),
            area=float(np.sum(ft.intensity_matrix[i, :])),
            snr=5.0,
            peak_quality=0.8,
        ))

    result = annotator.annotate_features(features, max_matches_per_feature=params.max_matches)

    return {
        "total": result.total_features,
        "annotated": result.annotated_count,
        "high_confidence": result.high_confidence_count,
        "databases": result.databases_queried,
        "databases_with_hits": result.databases_with_hits,
        "online_requested": result.online_requested,
        "online_available": result.online_available,
        "online_errors": result.online_errors,
        "features": [
            {
                "id": af.feature_id,
                "mz": round(af.mz, 4),
                "rt": round(af.rt, 1),
                "adduct_guess": af.adduct_guess,
                "neutral_mass": round(af.neutral_mass, 4) if af.neutral_mass else None,
                "top_match": {
                    "name": af.top_match.name,
                    "formula": af.top_match.formula,
                    "database": af.top_match.database,
                    "accession": af.top_match.accession,
                    "adduct": af.top_match.adduct,
                    "mass_error_ppm": af.top_match.mass_error_ppm,
                    "score": af.top_match.score,
                } if af.top_match else None,
                "all_matches": [
                    {
                        "name": m.name, "formula": m.formula, "database": m.database,
                        "adduct": m.adduct, "mass_error_ppm": m.mass_error_ppm,
                        "score": m.score, "rank": m.rank,
                    }
                    for m in af.matches
                ],
            }
            for af in result.annotated_features
        ],
    }


# ═══════════════════════════════════════════════════════════════
# API Routes — Export
# ═══════════════════════════════════════════════════════════════

@app.get("/api/export/csv")
async def export_csv():
    """Export the feature table as CSV."""
    global _last_pipeline_result
    if _last_pipeline_result is None:
        raise HTTPException(400, "Run pipeline first")

    ft = _build_feature_table(_last_pipeline_result)

    output = io.StringIO()
    writer = csv.writer(output)
    header = ['feature_id', 'mz', 'rt'] + ft.sample_names
    writer.writerow(header)
    for i in range(ft.num_features):
        row = [
            int(ft.feature_ids[i]),
            f"{ft.mz_values[i]:.5f}",
            f"{ft.rt_values[i]:.2f}",
        ]
        row.extend(f"{ft.intensity_matrix[i, j]:.2f}" for j in range(ft.num_samples))
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=feature_table.csv"},
    )


@app.get("/api/export/annotations")
async def export_annotations():
    """Export annotations as CSV."""
    global _last_pipeline_result
    
    # Quick re-annotate
    ft = _build_feature_table(_last_pipeline_result)
    annotator = MetaboliteAnnotator(use_online=False)
    features = []
    for i in range(ft.num_features):
        features.append(DetectedFeature(
            feature_id=int(ft.feature_ids[i]),
            mz=float(ft.mz_values[i]),
            mz_min=float(ft.mz_values[i]) - 0.01,
            mz_max=float(ft.mz_values[i]) + 0.01,
            rt=float(ft.rt_values[i]),
            rt_min=float(ft.rt_values[i]) - 5,
            rt_max=float(ft.rt_values[i]) + 5,
            intensity=float(np.max(ft.intensity_matrix[i, :])),
            area=float(np.sum(ft.intensity_matrix[i, :])),
            snr=5.0, peak_quality=0.8,
        ))
    result = annotator.annotate_features(features)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "feature_id", "mz", "rt", "intensity",
        "match_rank", "name", "formula", "adduct", "mass_error_ppm", "score", "database",
    ])
    for af in result.annotated_features:
        if af.matches:
            for m in af.matches[:3]:
                writer.writerow([
                    af.feature_id, f"{af.mz:.4f}", f"{af.rt:.1f}", f"{af.intensity:.0f}",
                    m.rank, m.name, m.formula, m.adduct or "",
                    f"{m.mass_error_ppm:.2f}", f"{m.score:.3f}", m.database,
                ])
        else:
            writer.writerow([
                af.feature_id, f"{af.mz:.4f}", f"{af.rt:.1f}", f"{af.intensity:.0f}",
                "", "Unknown", "", "", "", "", "",
            ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=annotations.csv"},
    )


# ═══════════════════════════════════════════════════════════════
# Health / Info
# ═══════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    """Health check with platform info."""
    return {
        "status": "ok",
        "version": "0.3.0",
        "has_data": _last_pipeline_result is not None,
        "data_source": _last_pipeline_result.get("data_source", "synthetic") if _last_pipeline_result else None,
        "modules": ["io_utils", "peak_engine", "alignment_engine", "grouping_engine", "stats_engine", "db_annotator"],
        "endpoints": [
            "pipeline/run", "pipeline/batch", "stats/pca", "stats/plsda",
            "stats/volcano", "stats/pathway", "annotate", "export/csv",
            "files/upload", "files/list", "files/info/{filename}",
        ],
    }


# ═══════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════

def _build_feature_table(result: Dict) -> FeatureTable:
    """Build a FeatureTable from a pipeline result dict."""
    n_features = result["grouped_features"]
    n_samples = result["n_samples"]
    mz_values = np.array([f["mz"] for f in result["top_features"]], dtype=np.float64)
    rt_values = np.array([f["rt"] for f in result["top_features"]], dtype=np.float64)
    feature_ids = np.arange(n_features, dtype=np.int64)

    if n_features > len(mz_values):
        # Pad with zeros for features beyond top_20
        mz_values = np.pad(mz_values, (0, n_features - len(mz_values)), constant_values=0)
        rt_values = np.pad(rt_values, (0, n_features - len(rt_values)), constant_values=0)

    intensity_matrix = np.zeros((n_features, n_samples), dtype=np.float64)
    for i, f in enumerate(result["top_features"]):
        for j, v in enumerate(f["intensities"]):
            intensity_matrix[i, j] = v

    return FeatureTable(
        sample_names=result["sample_names"],
        feature_ids=feature_ids,
        mz_values=mz_values,
        rt_values=rt_values,
        intensity_matrix=intensity_matrix,
    )


# ═══════════════════════════════════════════════════════════════
# Static files (Web UI)
# ═══════════════════════════════════════════════════════════════

frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


# ═══════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8002))
    print(f"""
  Metabolomics Platform v0.2.0
  http://localhost:{port}
  API docs: http://localhost:{port}/docs
""")
    uvicorn.run(app, host="0.0.0.0", port=port)
