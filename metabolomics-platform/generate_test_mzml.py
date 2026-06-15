"""Generate a realistic test mzML file for metabolomics testing."""
import numpy as np
import os, sys

try:
    from pymzml import Writer
except ImportError:
    print("pymzml not available, creating minimal mzML XML manually...")
    Writer = None

# Realistic metabolites with known [M+H]+ m/z and retention times
METABOLITES = [
    {"name": "L-Alanine",          "formula": "C3H7NO2",   "mz": 90.0550,  "rt": 45,   "area": 5e5},
    {"name": "L-Glutamic acid",    "formula": "C5H9NO4",   "mz": 148.0604, "rt": 52,   "area": 8e5},
    {"name": "L-Phenylalanine",    "formula": "C9H11NO2",  "mz": 166.0863, "rt": 68,   "area": 9e5},
    {"name": "Citric acid",        "formula": "C6H8O7",    "mz": 193.0343, "rt": 58,   "area": 7e5},
    {"name": "L-Tryptophan",       "formula": "C11H12N2O2","mz": 205.0972, "rt": 72,   "area": 1e6},
    {"name": "Caffeine",           "formula": "C8H10N4O2", "mz": 195.0877, "rt": 85,   "area": 1.2e6},
    {"name": "Hippuric acid",      "formula": "C9H9NO3",   "mz": 180.0655, "rt": 78,   "area": 6e5},
    {"name": "L-Lactic acid",      "formula": "C3H6O3",    "mz": 91.0390,  "rt": 40,   "area": 4e5},
    {"name": "Succinic acid",      "formula": "C4H6O4",    "mz": 119.0339, "rt": 48,   "area": 5e5},
    {"name": "Creatine",           "formula": "C4H9N3O2",  "mz": 132.0768, "rt": 43,   "area": 6e5},
    {"name": "Acetaminophen",      "formula": "C8H9NO2",   "mz": 152.0706, "rt": 82,   "area": 9e5},
    {"name": "Uric acid",          "formula": "C5H4N4O3",  "mz": 169.0356, "rt": 55,   "area": 7e5},
]

OUTPUT = os.path.join(os.path.dirname(__file__) or ".", "uploads", "test_metabolomics.mzML")

def generate_mzml_manual():
    """Write minimal compliant mzML XML manually."""
    mzml = ['<?xml version="1.0" encoding="utf-8"?>']
    mzml.append('<mzML xmlns="http://psi.hupo.org/ms/mzml" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://psi.hupo.org/ms/mzml http://psidev.info/files/ms/mzML/xsd/mzML1.1.0.xsd" version="1.1.0">')
    mzml.append('<cvList count="2">')
    mzml.append('<cv id="MS" fullName="PSI-MS" version="4.1.0" URI="http://psidev.cvs.sourceforge.net/viewvc/*checkout*/psidev/psi/psi-ms/mzML/controlledVocabulary/psi-ms.obo"/>')
    mzml.append('<cv id="UO" fullName="UNIT-ONTOLOGY" version="1.0" URI="http://obo.cvs.sourceforge.net/*checkout*/obo/obo/ontology/phenotype/unit.obo"/>')
    mzml.append('</cvList>')
    mzml.append('<fileDescription><fileContent><cvParam cvRef="MS" accession="MS:1000579" name="MS1 spectrum" /></fileContent></fileDescription>')
    mzml.append('<softwareList count="1"><software id="MetabolomicsPlatform" version="0.2.0"><cvParam cvRef="MS" accession="MS:1000799" name="custom unreleased software tool" /></software></softwareList>')
    mzml.append('<instrumentConfigurationList count="1"><instrumentConfiguration id="IC1"><cvParam cvRef="MS" accession="MS:1000031" name="instrument model" /></instrumentConfiguration></instrumentConfigurationList>')
    mzml.append('<dataProcessingList count="1"><dataProcessing id="DP1"><processingMethod order="1" softwareRef="MetabolomicsPlatform" /></dataProcessing></dataProcessingList>')

    mzml.append('<run id="run1" defaultInstrumentConfigurationRef="IC1" defaultSourceFileRef="SF1">')
    mzml.append('<sourceFileList count="1"><sourceFile id="SF1" name="test_metabolomics.mzML" location="file:///test_metabolomics.mzML"><cvParam cvRef="MS" accession="MS:1000560" name="mzML format" /></sourceFile></sourceFileList>')

    mzml.append('<spectrumList count="300" defaultDataProcessingRef="DP1">')

    np.random.seed(42)
    for scan_idx in range(300):
        rt = scan_idx * 0.5  # seconds, 0.5s per scan → 150s total
        peaks_mz = []
        peaks_int = []

        # Metabolite peaks with chromatographic elution profiles
        for met in METABOLITES:
            rt_diff = rt - met["rt"]
            # Gaussian chromatographic peak
            chrom_intensity = met["area"] * np.exp(-rt_diff ** 2 / (2 * 8.0 ** 2))
            if chrom_intensity > 500:
                # Add Gaussian peak with fine sampling
                x = np.linspace(met["mz"] - 0.03, met["mz"] + 0.03, 61)
                y = chrom_intensity * np.exp(-((x - met["mz"]) ** 2) / (2 * 0.005 ** 2)) * (0.9 + 0.2 * np.random.random())
                peaks_mz.extend(x.tolist())
                peaks_int.extend(y.tolist())

        # Background noise — use more points for finer m/z sampling
        for _ in range(1500):
            noise_mz = np.random.uniform(80, 250)
            noise_int = np.random.exponential(200)
            peaks_mz.append(noise_mz)
            peaks_int.append(noise_int)

        # Sort by m/z
        order = np.argsort(peaks_mz)
        mz_arr = [peaks_mz[i] for i in order]
        int_arr = [peaks_int[i] for i in order]

        # Write binary data (base64 encoded) — separate m/z and intensity arrays
        import struct, base64
        mz_binary = struct.pack(f'<{len(mz_arr)}d', *mz_arr)
        int_binary = struct.pack(f'<{len(int_arr)}d', *int_arr)
        mz_enc = base64.b64encode(mz_binary).decode('ascii')
        int_enc = base64.b64encode(int_binary).decode('ascii')

        tic = sum(int_arr)
        base_peak = max(int_arr) if int_arr else 0
        base_peak_idx = int_arr.index(base_peak) if int_arr else 0
        base_peak_mz = mz_arr[base_peak_idx] if int_arr else 0

        mzml.append(f'<spectrum index="{scan_idx}" id="scan={scan_idx+1}" defaultArrayLength="{len(mz_arr)}" dataProcessingRef="DP1">')
        mzml.append(f'<cvParam cvRef="MS" accession="MS:1000579" name="MS1 spectrum" />')
        mzml.append(f'<cvParam cvRef="MS" accession="MS:1000511" name="ms level" value="1" />')
        mzml.append(f'<cvParam cvRef="MS" accession="MS:1000130" name="positive scan" />')
        mzml.append(f'<cvParam cvRef="MS" accession="MS:1000016" name="scan start time" value="{rt:.6f}" unitCvRef="UO" unitAccession="UO:0000010" unitName="second" />')
        mzml.append(f'<cvParam cvRef="MS" accession="MS:1000285" name="total ion current" value="{tic:.6f}" />')
        mzml.append(f'<cvParam cvRef="MS" accession="MS:1000504" name="base peak m/z" value="{base_peak_mz:.6f}" />')
        mzml.append(f'<cvParam cvRef="MS" accession="MS:1000505" name="base peak intensity" value="{base_peak:.6f}" />')

        mzml.append('<binaryDataArrayList count="2">')
        mzml.append('<binaryDataArray encodedLength="0" arrayLength="0">')
        mzml.append('<cvParam cvRef="MS" accession="MS:1000514" name="m/z array" />')
        mzml.append('<cvParam cvRef="MS" accession="MS:1000523" name="64-bit float" />')
        mzml.append('<cvParam cvRef="MS" accession="MS:1000576" name="no compression" />')
        mzml.append(f'<binary>{mz_enc}</binary>')
        mzml.append('</binaryDataArray>')
        mzml.append('<binaryDataArray encodedLength="0" arrayLength="0">')
        mzml.append('<cvParam cvRef="MS" accession="MS:1000515" name="intensity array" />')
        mzml.append('<cvParam cvRef="MS" accession="MS:1000523" name="64-bit float" />')
        mzml.append('<cvParam cvRef="MS" accession="MS:1000576" name="no compression" />')
        mzml.append(f'<binary>{int_enc}</binary>')
        mzml.append('</binaryDataArray>')
        mzml.append('</binaryDataArrayList>')
        mzml.append('</spectrum>')

    mzml.append('</spectrumList>')
    mzml.append('</run>')
    mzml.append('</mzML>')

    with open(OUTPUT, 'w') as f:
        f.write('\n'.join(mzml))

    return os.path.getsize(OUTPUT)


if __name__ == "__main__":
    size = generate_mzml_manual()
    print(f"Generated: {OUTPUT}")
    print(f"Size: {size:,} bytes ({size/1024:.0f} KB)")
    print(f"Contains: {len(METABOLITES)} known metabolites, 300 MS1 scans")
    for m in METABOLITES:
        print(f"  {m['name']:20s} m/z={m['mz']:.4f}  RT={m['rt']:.0f}s  area={m['area']:.0f}")
