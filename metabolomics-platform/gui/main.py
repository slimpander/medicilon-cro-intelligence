"""
Metabolomics Platform v0.2.0 — Desktop GUI (PySide6)
======================================================
3-tab interface: Pipeline | Statistics | Annotation
"""

import sys, os, json, threading
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSpinBox, QDoubleSpinBox, QTextEdit,
    QSplitter, QFileDialog, QProgressBar, QGroupBox, QGridLayout,
    QStatusBar, QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor, QPalette

from src.io_utils import FeatureTable, DetectedFeature
from src.peak_engine import PeakPicker, FeatureDetector
from src.alignment_engine import RTAligner
from src.grouping_engine import DensityFeatureGrouper, GapFiller, compute_feature_quality
from src.stats_engine import (
    log_transform, pareto_scale, auto_scale,
    pca, pls_da, volcano, pathway_enrichment,
)
from src.db_annotator import MetaboliteAnnotator


# Synthetic data (same as backend)
KNOWN_PEAKS = [
    {"name": "Caffeine", "mz": 195.0877, "rt": 150, "intensity": 8e4},
    {"name": "Theobromine", "mz": 181.0720, "rt": 120, "intensity": 7e4},
    {"name": "Acetaminophen", "mz": 152.0570, "rt": 200, "intensity": 9e4},
    {"name": "4-Aminobenzoic", "mz": 138.0550, "rt": 90, "intensity": 5e4},
    {"name": "Paraxanthine", "mz": 181.0725, "rt": 160, "intensity": 4e4},
    {"name": "Hippuric Acid", "mz": 180.0655, "rt": 140, "intensity": 6e4},
]


class PipelineWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        try:
            np.random.seed(42)
            n_scans = self.params.get("n_scans", 200)
            n_peaks = self.params.get("n_peaks", 6)
            known = KNOWN_PEAKS[:n_peaks]
            cw = 8.0

            self.progress.emit("Generating synthetic spectra...")
            spectra, rts_list = [], []
            for scan_idx in range(n_scans):
                rt = scan_idx * 1.0
                rts_list.append(rt)
                pmz, pint = [], []
                for pk in known:
                    rt_diff = rt - pk["rt"]
                    intensity = pk["intensity"] * np.exp(-rt_diff**2 / (2 * cw**2))
                    if intensity > 100:
                        x = np.linspace(pk["mz"] - 0.025, pk["mz"] + 0.025, 21)
                        y = intensity * np.exp(-((x - pk["mz"])**2) / (2 * 0.005**2))
                        pmz.extend(x.tolist())
                        pint.extend(y.tolist())
                for _ in range(200):
                    pmz.append(np.random.uniform(100, 300))
                    pint.append(np.random.exponential(300))
                order = np.argsort(pmz)
                mz_arr = np.array([pmz[i] for i in order], dtype=np.float64)
                int_arr = np.array([pint[i] for i in order], dtype=np.float64)
                from src.io_utils import Spectrum
                spec = Spectrum(index=scan_idx, ms_level=1, scan_number=scan_idx+1, retention_time=rt, polarity="positive")
                spec.mz = mz_arr
                spec.intensity = int_arr
                spec.total_ion_current = float(np.sum(int_arr))
                spectra.append(spec)

            rts = np.array(rts_list, dtype=np.float64)

            # Replicates
            shifts = [0, 3, -2]
            reps = []
            for rep_idx, shift in enumerate(shifts):
                rep_specs = []
                for spec in spectra:
                    s2 = Spectrum(index=spec.index, ms_level=1, scan_number=spec.scan_number,
                                  retention_time=spec.retention_time + shift, polarity="positive")
                    s2.mz = spec.mz + np.random.uniform(-0.001, 0.001, len(spec.mz))
                    s2.intensity = spec.intensity * np.random.uniform(0.85, 1.15, len(spec.intensity))
                    s2.total_ion_current = float(np.sum(s2.intensity))
                    rep_specs.append(s2)
                reps.append(rep_specs)

            self.progress.emit("Peak picking...")
            picker = PeakPicker(
                snr_threshold=self.params.get("snr", 3.0),
                min_intensity=self.params.get("min_intensity", 500),
                peak_width_range=(self.params.get("pw_min", 0.005), self.params.get("pw_max", 0.5)),
            )
            detector = FeatureDetector(
                mz_tolerance_da=self.params.get("mz_tol", 0.02),
                min_scans=self.params.get("min_scans", 5),
                min_intensity=self.params.get("min_intensity", 500),
            )

            self.progress.emit("Feature detection...")
            all_features_reps = []
            roi_counts = []
            for rep_specs in reps:
                all_peaks = [picker.detect_peaks(s) for s in rep_specs]
                rois = detector.extract_rois(all_peaks, rts)
                roi_counts.append(len(rois))
                feats = []
                for roi in rois:
                    snr_val = roi.max_intensity / (float(np.std(roi.intensities)) + 1.0) if len(roi.intensities) > 1 else 1.0
                    q = min(1.0, roi.num_scans / max(self.params.get("min_scans", 5) * 3, 1))
                    feats.append(DetectedFeature(
                        feature_id=roi.roi_id, mz=roi.mz, mz_min=roi.mz_min, mz_max=roi.mz_max,
                        rt=roi.rt_apex, rt_min=roi.rt_start, rt_max=roi.rt_end,
                        intensity=roi.max_intensity, area=roi.peak_area,
                        snr=float(snr_val), peak_quality=float(q),
                    ))
                all_features_reps.append(feats)

            self.progress.emit("RT alignment...")
            aligner = RTAligner(method=self.params.get("align_method", "loess"))
            warpings = aligner.fit(all_features_reps)

            self.progress.emit("Feature grouping...")
            grouper = DensityFeatureGrouper(
                mz_bandwidth_ppm=self.params.get("mz_bw", 5.0),
                rt_bandwidth_sec=self.params.get("rt_bw", 10.0),
            )
            ft = grouper.group(all_features_reps, ["Rep1", "Rep2", "Rep3"])

            gf = GapFiller()
            ft_filled = gf.fill_by_knn(ft, k=3)
            quality = compute_feature_quality(ft_filled)

            top_features = []
            for i in sorted(range(ft.num_features), key=lambda x: quality[x], reverse=True)[:20]:
                top_features.append({
                    "id": int(ft.feature_ids[i]),
                    "mz": round(float(ft.mz_values[i]), 4),
                    "rt": round(float(ft.rt_values[i]), 1),
                    "intensities": [round(float(ft_filled.intensity_matrix[i, j]), 0) for j in range(3)],
                    "quality": round(float(quality[i]), 3),
                })

            self.finished.emit({
                "total_peaks": sum(len(p) for p in all_peaks),
                "rois_per_rep": roi_counts,
                "grouped_features": ft.num_features,
                "sample_names": ["Rep1", "Rep2", "Rep3"],
                "alignment": [
                    {"sample": i, "landmarks": w.n_landmarks, "shift_median": round(w.shift_median, 2), "shift_max": round(w.shift_max, 2)}
                    for i, w in enumerate(warpings)
                ],
                "top_features": top_features,
                "quality": [round(float(q), 3) for q in quality[:20]],
                "feature_table": ft_filled,
            })

        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n{traceback.format_exc()}")


class MetabolomicsGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Metabolomics Platform v0.2.0")
        self.setMinimumSize(1100, 750)
        self._result = None
        self._ft = None
        self._setup_ui()
        self._apply_light_theme()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._make_pipeline_tab(), "Pipeline")
        self.tabs.addTab(self._make_stats_tab(), "Statistics")
        self.tabs.addTab(self._make_annotation_tab(), "Annotation")
        layout.addWidget(self.tabs)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready — click Run Pipeline to start")

    def _make_pipeline_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # Parameters group
        params_group = QGroupBox("Pipeline Parameters")
        grid = QGridLayout()

        self.snr_spin = QDoubleSpinBox(); self.snr_spin.setRange(1, 20); self.snr_spin.setValue(3); self.snr_spin.setSingleStep(0.5)
        self.int_spin = QDoubleSpinBox(); self.int_spin.setRange(0, 1e6); self.int_spin.setValue(500); self.int_spin.setSingleStep(100)
        self.pwmin_spin = QDoubleSpinBox(); self.pwmin_spin.setRange(0.001, 0.1); self.pwmin_spin.setValue(0.005); self.pwmin_spin.setDecimals(4); self.pwmin_spin.setSingleStep(0.001)
        self.pwmax_spin = QDoubleSpinBox(); self.pwmax_spin.setRange(0.01, 2.0); self.pwmax_spin.setValue(0.5); self.pwmax_spin.setSingleStep(0.05)
        self.mztol_spin = QDoubleSpinBox(); self.mztol_spin.setRange(0.001, 0.5); self.mztol_spin.setValue(0.02); self.mztol_spin.setDecimals(4); self.mztol_spin.setSingleStep(0.005)
        self.scans_spin = QSpinBox(); self.scans_spin.setRange(1, 50); self.scans_spin.setValue(5)
        self.mzbw_spin = QDoubleSpinBox(); self.mzbw_spin.setRange(1, 50); self.mzbw_spin.setValue(5)
        self.rtbw_spin = QDoubleSpinBox(); self.rtbw_spin.setRange(1, 60); self.rtbw_spin.setValue(10)
        self.nmet_spin = QSpinBox(); self.nmet_spin.setRange(1, 6); self.nmet_spin.setValue(6)
        self.nscans_spin = QSpinBox(); self.nscans_spin.setRange(50, 1000); self.nscans_spin.setValue(200); self.nscans_spin.setSingleStep(50)

        widgets = [
            ("SNR Threshold", self.snr_spin), ("Min Intensity", self.int_spin),
            ("Peak Width Min (Da)", self.pwmin_spin), ("Peak Width Max (Da)", self.pwmax_spin),
            ("m/z Tolerance (Da)", self.mztol_spin), ("Min Scans", self.scans_spin),
            ("m/z Bandwidth (ppm)", self.mzbw_spin), ("RT Bandwidth (s)", self.rtbw_spin),
            ("N Metabolites", self.nmet_spin), ("N Scans", self.nscans_spin),
        ]
        for i, (label, widget) in enumerate(widgets):
            grid.addWidget(QLabel(label), i // 2, (i % 2) * 2)
            grid.addWidget(widget, i // 2, (i % 2) * 2 + 1)

        params_group.setLayout(grid)
        layout.addWidget(params_group)

        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("Run Pipeline")
        self.run_btn.clicked.connect(self._run_pipeline)
        btn_layout.addWidget(self.run_btn)
        self.progress_label = QLabel("")
        btn_layout.addWidget(self.progress_label)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Results area
        self.pipeline_output = QTextEdit()
        self.pipeline_output.setReadOnly(True)
        self.pipeline_output.setFont(QFont("Consolas", 9))
        layout.addWidget(self.pipeline_output)

        # Feature table
        self.ft_table = QTableWidget()
        self.ft_table.setColumnCount(7)
        self.ft_table.setHorizontalHeaderLabels(["ID", "m/z", "RT (s)", "Rep1", "Rep2", "Rep3", "Quality"])
        self.ft_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.ft_table)

        return w

    def _make_stats_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # PCA section
        pca_group = QGroupBox("PCA — Principal Component Analysis")
        pca_layout = QVBoxLayout()
        pca_ctrl = QHBoxLayout()
        self.pca_components = QSpinBox(); self.pca_components.setRange(1, 6); self.pca_components.setValue(3)
        pca_ctrl.addWidget(QLabel("Components:"))
        pca_ctrl.addWidget(self.pca_components)
        self.pca_scale = QComboBox(); self.pca_scale.addItems(["pareto", "auto", "none"])
        pca_ctrl.addWidget(QLabel("Scaling:"))
        pca_ctrl.addWidget(self.pca_scale)
        self.pca_btn = QPushButton("Run PCA")
        self.pca_btn.clicked.connect(self._run_pca)
        pca_ctrl.addWidget(self.pca_btn)
        pca_ctrl.addStretch()
        pca_layout.addLayout(pca_ctrl)
        self.pca_output = QTextEdit()
        self.pca_output.setReadOnly(True)
        self.pca_output.setFont(QFont("Consolas", 9))
        pca_layout.addWidget(self.pca_output)
        pca_group.setLayout(pca_layout)
        layout.addWidget(pca_group)

        # Volcano section
        volc_group = QGroupBox("Volcano Plot — Differential Abundance")
        volc_layout = QVBoxLayout()
        volc_ctrl = QHBoxLayout()
        self.volc_fc = QDoubleSpinBox(); self.volc_fc.setRange(0.1, 5); self.volc_fc.setValue(1.0); self.volc_fc.setSingleStep(0.1)
        volc_ctrl.addWidget(QLabel("FC threshold (log2):"))
        volc_ctrl.addWidget(self.volc_fc)
        self.volc_pval = QDoubleSpinBox(); self.volc_pval.setRange(0.001, 1); self.volc_pval.setValue(0.05); self.volc_pval.setDecimals(3); self.volc_pval.setSingleStep(0.01)
        volc_ctrl.addWidget(QLabel("P-value:"))
        volc_ctrl.addWidget(self.volc_pval)
        self.volc_btn = QPushButton("Run Volcano")
        self.volc_btn.clicked.connect(self._run_volcano)
        volc_ctrl.addWidget(self.volc_btn)
        volc_ctrl.addStretch()
        volc_layout.addLayout(volc_ctrl)
        self.volc_output = QTextEdit()
        self.volc_output.setReadOnly(True)
        self.volc_output.setFont(QFont("Consolas", 9))
        volc_layout.addWidget(self.volc_output)
        volc_group.setLayout(volc_layout)
        layout.addWidget(volc_group)

        layout.addStretch()
        return w

    def _make_annotation_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        ann_group = QGroupBox("Metabolite Annotation")
        ann_layout = QVBoxLayout()
        ann_ctrl = QHBoxLayout()
        self.anno_ppm = QDoubleSpinBox(); self.anno_ppm.setRange(1, 50); self.anno_ppm.setValue(10.0)
        ann_ctrl.addWidget(QLabel("Mass tolerance (ppm):"))
        ann_ctrl.addWidget(self.anno_ppm)
        self.anno_mode = QComboBox(); self.anno_mode.addItems(["positive", "negative"])
        ann_ctrl.addWidget(QLabel("Mode:"))
        ann_ctrl.addWidget(self.anno_mode)
        self.anno_btn = QPushButton("Annotate Features")
        self.anno_btn.clicked.connect(self._run_annotation)
        ann_ctrl.addWidget(self.anno_btn)
        ann_ctrl.addStretch()
        ann_layout.addLayout(ann_ctrl)
        ann_group.setLayout(ann_layout)
        layout.addWidget(ann_group)

        self.anno_table = QTableWidget()
        self.anno_table.setColumnCount(7)
        self.anno_table.setHorizontalHeaderLabels(["m/z", "RT", "Match", "Formula", "Adduct", "Error (ppm)", "Score"])
        self.anno_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.anno_table)

        return w

    def _run_pipeline(self):
        self.run_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Running...")
        self.pipeline_output.clear()

        params = {
            "snr": self.snr_spin.value(), "min_intensity": self.int_spin.value(),
            "pw_min": self.pwmin_spin.value(), "pw_max": self.pwmax_spin.value(),
            "mz_tol": self.mztol_spin.value(), "min_scans": self.scans_spin.value(),
            "mz_bw": self.mzbw_spin.value(), "rt_bw": self.rtbw_spin.value(),
            "n_peaks": self.nmet_spin.value(), "n_scans": self.nscans_spin.value(),
            "align_method": "loess",
        }

        self.worker = PipelineWorker(params)
        self.worker.progress.connect(lambda msg: self.progress_label.setText(msg))
        self.worker.finished.connect(self._on_pipeline_done)
        self.worker.error.connect(self._on_pipeline_error)
        self.worker.start()

    def _on_pipeline_done(self, result):
        self._result = result
        self._ft = result.get("feature_table")
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Done!")
        self.status_bar.showMessage(f"Pipeline complete: {result['grouped_features']} features, {result['total_peaks']} peaks")

        out = []
        out.append(f"=== Pipeline Results ===")
        out.append(f"Total peaks detected: {result['total_peaks']}")
        out.append(f"ROIs per replicate: {result['rois_per_rep']}")
        out.append(f"Grouped features: {result['grouped_features']}")
        out.append(f"")
        out.append(f"=== Alignment ===")
        for a in result['alignment']:
            out.append(f"  {a['sample']}: {a['landmarks']} landmarks, shift={a['shift_median']}s")
        self.pipeline_output.setText("\n".join(out))

        # Feature table
        self.ft_table.setRowCount(len(result['top_features']))
        for row, f in enumerate(result['top_features']):
            self.ft_table.setItem(row, 0, QTableWidgetItem(str(f['id'])))
            self.ft_table.setItem(row, 1, QTableWidgetItem(str(f['mz'])))
            self.ft_table.setItem(row, 2, QTableWidgetItem(str(f['rt'])))
            for j, v in enumerate(f['intensities']):
                self.ft_table.setItem(row, 3 + j, QTableWidgetItem(str(v)))
            self.ft_table.setItem(row, 6, QTableWidgetItem(str(f['quality'])))

    def _on_pipeline_error(self, msg):
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Error!")
        self.pipeline_output.setText(f"ERROR:\n{msg}")
        QMessageBox.critical(self, "Pipeline Error", msg)

    def _run_pca(self):
        if self._ft is None:
            QMessageBox.warning(self, "No Data", "Run the pipeline first.")
            return

        try:
            ft_log = log_transform(self._ft, base=2)
            ft_scaled = pareto_scale(ft_log) if self.pca_scale.currentText() == "pareto" else \
                        auto_scale(ft_log) if self.pca_scale.currentText() == "auto" else ft_log

            result = pca(ft_scaled, n_components=self.pca_components.value())

            out = []
            out.append("=== PCA Results ===")
            for i in range(result.n_components):
                out.append(f"PC{i+1}: {result.variance_explained[i]*100:.1f}% variance "
                          f"(cumulative: {result.cumulative_variance[i]*100:.1f}%)")
            out.append("")
            out.append("=== PC Scores ===")
            for i, sample in enumerate(self._result['sample_names']):
                scores_str = "  ".join(f"{result.scores[i, j]:.3f}" for j in range(min(3, result.n_components)))
                out.append(f"{sample}: {scores_str}")
            self.pca_output.setText("\n".join(out))
        except Exception as e:
            self.pca_output.setText(f"PCA Error: {e}")

    def _run_volcano(self):
        if self._ft is None:
            QMessageBox.warning(self, "No Data", "Run the pipeline first.")
            return

        try:
            result = volcano(
                self._ft, [0, 1, 2], [3, 4, 5],
                fold_change_threshold=self.volc_fc.value(),
                p_value_threshold=self.volc_pval.value(),
                test_method="ttest",
            )

            out = []
            out.append(f"=== Volcano Plot: Rep (1-3) vs Rep (4-6) ===")
            out.append(f"Total features: {len(result.feature_ids)}")
            out.append(f"Significant: {result.n_significant} "
                      f"(up: {result.n_upregulated}, down: {result.n_downregulated})")
            out.append("")
            out.append("=== Top Changed Features ===")
            sig_order = np.argsort(np.abs(result.fold_changes))[::-1]
            for i in sig_order[:15]:
                if result.significant[i]:
                    direction = "UP" if result.upregulated[i] else "DOWN"
                    out.append(f"  m/z={result.mz_values[i]:.4f}  FC={result.fold_changes[i]:+.2f}  "
                              f"p={result.p_values[i]:.4f}  q={result.q_values[i]:.4f}  [{direction}]")
            self.volc_output.setText("\n".join(out))
        except Exception as e:
            self.volc_output.setText(f"Volcano Error: {e}")

    def _run_annotation(self):
        if self._ft is None:
            QMessageBox.warning(self, "No Data", "Run the pipeline first.")
            return

        try:
            annotator = MetaboliteAnnotator(
                mass_tolerance_ppm=self.anno_ppm.value(),
                mode=self.anno_mode.currentText(),
                use_online=False,
            )

            features = []
            for i in range(self._ft.num_features):
                features.append(DetectedFeature(
                    feature_id=int(self._ft.feature_ids[i]),
                    mz=float(self._ft.mz_values[i]),
                    mz_min=float(self._ft.mz_values[i]) - 0.01,
                    mz_max=float(self._ft.mz_values[i]) + 0.01,
                    rt=float(self._ft.rt_values[i]),
                    rt_min=float(self._ft.rt_values[i]) - 5,
                    rt_max=float(self._ft.rt_values[i]) + 5,
                    intensity=float(np.max(self._ft.intensity_matrix[i, :])),
                    area=float(np.sum(self._ft.intensity_matrix[i, :])),
                    snr=5.0, peak_quality=0.8,
                ))

            result = annotator.annotate_features(features)

            self.anno_table.setRowCount(len(result.annotated_features))
            for row, af in enumerate(result.annotated_features):
                self.anno_table.setItem(row, 0, QTableWidgetItem(f"{af.mz:.4f}"))
                self.anno_table.setItem(row, 1, QTableWidgetItem(f"{af.rt:.1f}"))
                if af.top_match:
                    m = af.top_match
                    self.anno_table.setItem(row, 2, QTableWidgetItem(m.name))
                    self.anno_table.setItem(row, 3, QTableWidgetItem(m.formula))
                    self.anno_table.setItem(row, 4, QTableWidgetItem(m.adduct or "-"))
                    self.anno_table.setItem(row, 5, QTableWidgetItem(f"{m.mass_error_ppm:.1f}"))
                    self.anno_table.setItem(row, 6, QTableWidgetItem(f"{m.score:.3f}"))
                else:
                    self.anno_table.setItem(row, 2, QTableWidgetItem("Unknown"))

            self.status_bar.showMessage(f"Annotation: {result.annotated_count}/{result.total_features} annotated, {result.high_confidence_count} high-confidence")

        except Exception as e:
            QMessageBox.critical(self, "Annotation Error", str(e))

    def _apply_light_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(248, 249, 251))
        palette.setColor(QPalette.WindowText, QColor(30, 41, 59))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(248, 249, 251))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ToolTipText, QColor(30, 41, 59))
        palette.setColor(QPalette.Text, QColor(30, 41, 59))
        palette.setColor(QPalette.Button, QColor(255, 255, 255))
        palette.setColor(QPalette.ButtonText, QColor(30, 41, 59))
        palette.setColor(QPalette.BrightText, QColor(220, 38, 38))
        palette.setColor(QPalette.Link, QColor(37, 99, 235))
        palette.setColor(QPalette.Highlight, QColor(37, 99, 235))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)
        self.setStyleSheet("""
            QGroupBox { font-weight: 600; border: 1px solid #e2e8f0; border-radius: 8px; margin-top: 14px; padding-top: 18px; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #1e293b; }
            QTableWidget { gridline-color: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 6px; }
            QHeaderView::section { background: #f8f9fb; border: none; border-bottom: 2px solid #e2e8f0; padding: 8px 12px; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; }
            QTableWidget::item { padding: 6px 12px; }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { 
                background: #f8f9fb; border: 1px solid #e2e8f0; border-radius: 4px; padding: 6px 10px;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: #2563eb; }
            QPushButton { background: #2563eb; color: white; border: none; border-radius: 5px; padding: 8px 16px; font-weight: 500; }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton:disabled { background: #94a3b8; }
            QStatusBar { background: #f8f9fb; border-top: 1px solid #e2e8f0; color: #64748b; }
            QTabWidget::pane { border: 1px solid #e2e8f0; border-radius: 8px; }
            QTabBar::tab { background: #f8f9fb; border: 1px solid #e2e8f0; padding: 8px 18px; margin-right: 2px; border-radius: 6px 6px 0 0; color: #64748b; }
            QTabBar::tab:selected { background: white; color: #2563eb; border-bottom: 2px solid #2563eb; }
            QTextEdit { background: #f8f9fb; border: 1px solid #e2e8f0; border-radius: 6px; font-family: 'Consolas', monospace; }
            QProgressBar { border: none; border-radius: 4px; background: #e2e8f0; height: 4px; }
            QProgressBar::chunk { background: #2563eb; border-radius: 4px; }
        """)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    gui = MetabolomicsGUI()
    gui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
