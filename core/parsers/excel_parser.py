"""
Parser for Chromatography Excel exports (Clarus 690 GC-MS / TurboMass / AMDIS).
Decoupled from Streamlit or any web framework.
"""

import io
from typing import Union, BinaryIO, Tuple, List, Dict
import pandas as pd
from ..models import ChromatogramPoint, PeakData, MassSpectrum, IonPeak


def _find_sheet_by_keywords(available_sheets: List[str], keywords: List[str]) -> str:
    """Finds a sheet name matching one of the provided keywords (case-insensitive)."""
    for sheet in available_sheets:
        s_lower = sheet.lower().strip()
        for kw in keywords:
            if kw.lower() in s_lower:
                return sheet
    return ""


def parse_chromatography_excel(
    file_source: Union[str, BinaryIO, bytes]
) -> Tuple[List[ChromatogramPoint], List[PeakData], float]:
    """
    Parses a GC-MS Excel file containing 3 sheets:
    1. Chromatogram (RT, Signal)
    2. Peaks (ID Peak, RT, Area)
    3. Mass spectrum (ID Peak, m/z, Signal)

    Returns:
        (chromatogram_points, list_of_peaks, total_area)
    """
    # Load excel file using pandas with openpyxl
    if isinstance(file_source, bytes):
        file_source = io.BytesIO(file_source)

    excel_file = pd.ExcelFile(file_source, engine="openpyxl")
    sheet_names = excel_file.sheet_names

    if len(sheet_names) < 3:
        raise ValueError(
            f"El archivo Excel debe tener al menos 3 hojas (Cromatograma, Picos, Espectro de masas). "
            f"Hojas encontradas: {sheet_names}"
        )

    # 1. IDENTIFY SHEETS
    # Sheet 1: Chromatogram / TIC
    sheet_chrom = _find_sheet_by_keywords(sheet_names, ["chromatogram", "cromatograma", "tic", "signal", "rt"])
    if not sheet_chrom:
        sheet_chrom = sheet_names[0]

    # Sheet 2: Peaks / Integration
    sheet_peaks = _find_sheet_by_keywords(sheet_names, ["peak", "pico", "integrat", "area"])
    if not sheet_peaks:
        sheet_peaks = sheet_names[1]

    # Sheet 3: Mass spectrum / MS
    sheet_ms = _find_sheet_by_keywords(sheet_names, ["mass", "spectrum", "espectro", "m/z", "mz", "ms"])
    if not sheet_ms:
        sheet_ms = sheet_names[2]

    # 2. PARSE CHROMATOGRAM (Sheet 1)
    df_chrom = pd.read_excel(excel_file, sheet_name=sheet_chrom)
    # Normalize column names
    col_map_chrom = {c: str(c).strip().lower() for c in df_chrom.columns}
    rt_col = next((c for c, name in col_map_chrom.items() if "rt" in name or "ret" in name or "time" in name or "tiempo" in name), df_chrom.columns[0])
    sig_col = next((c for c, name in col_map_chrom.items() if "sig" in name or "intens" in name or "abund" in name or "señal" in name or "sen" in name), df_chrom.columns[1])

    chromatogram_points: List[ChromatogramPoint] = []
    # Drop NaNs and ensure numeric
    df_chrom_clean = df_chrom[[rt_col, sig_col]].dropna()
    for _, row in df_chrom_clean.iterrows():
        try:
            rt_val = float(row[rt_col])
            sig_val = float(row[sig_col])
            chromatogram_points.append(ChromatogramPoint(rt=rt_val, signal=sig_val))
        except (ValueError, TypeError):
            continue

    # Sort chromatogram by RT
    chromatogram_points.sort(key=lambda p: p.rt)

    # 3. PARSE PEAKS (Sheet 2)
    df_peaks = pd.read_excel(excel_file, sheet_name=sheet_peaks)
    col_map_peaks = {c: str(c).strip().lower() for c in df_peaks.columns}
    id_col = next((c for c, name in col_map_peaks.items() if "id" in name or "peak" in name or "pico" in name), df_peaks.columns[0])
    rt_col_p = next((c for c, name in col_map_peaks.items() if "rt" in name or "ret" in name or "time" in name or "tiempo" in name), df_peaks.columns[1])
    area_col = next((c for c, name in col_map_peaks.items() if "area" in name or "área" in name), df_peaks.columns[2])

    peaks_dict: Dict[int, PeakData] = {}
    total_area = 0.0

    df_peaks_clean = df_peaks[[id_col, rt_col_p, area_col]].dropna()
    for _, row in df_peaks_clean.iterrows():
        try:
            pid = int(float(row[id_col]))
            rt = float(row[rt_col_p])
            area = float(row[area_col])
            if area < 0:
                continue
            total_area += area
            peaks_dict[pid] = PeakData(peak_id=pid, rt=rt, area=area)
        except (ValueError, TypeError):
            continue

    # Calculate initial relative area %
    if total_area > 0:
        for p in peaks_dict.values():
            p.relative_area_pct = (p.area / total_area) * 100.0

    # 4. PARSE MASS SPECTRA (Sheet 3)
    df_ms = pd.read_excel(excel_file, sheet_name=sheet_ms)
    col_map_ms = {c: str(c).strip().lower() for c in df_ms.columns}
    ms_id_col = next((c for c, name in col_map_ms.items() if "id" in name or "peak" in name or "pico" in name), df_ms.columns[0])
    mz_col = next((c for c, name in col_map_ms.items() if "m/z" in name or "mz" in name or "mass" in name or "masa" in name), df_ms.columns[1])
    ms_sig_col = next((c for c, name in col_map_ms.items() if "sig" in name or "intens" in name or "abund" in name or "señal" in name or "sen" in name), df_ms.columns[2])

    # Group spectra by peak ID
    peak_ions_raw: Dict[int, List[Tuple[float, float]]] = {}
    df_ms_clean = df_ms[[ms_id_col, mz_col, ms_sig_col]].dropna()

    for _, row in df_ms_clean.iterrows():
        try:
            pid = int(float(row[ms_id_col]))
            mz = float(row[mz_col])
            sig = float(row[ms_sig_col])
            if pid not in peak_ions_raw:
                peak_ions_raw[pid] = []
            peak_ions_raw[pid].append((mz, sig))
        except (ValueError, TypeError):
            continue

    # Build MassSpectrum objects and attach to PeakData
    for pid, raw_ions in peak_ions_raw.items():
        if not raw_ions:
            continue
        # Find base peak
        base_peak_sig = max(sig for _, sig in raw_ions) if raw_ions else 0.0
        base_peak_mz = 0.0
        ions_list: List[IonPeak] = []

        for mz, sig in raw_ions:
            rel_int = (sig / base_peak_sig * 1000.0) if base_peak_sig > 0 else 0.0
            if sig == base_peak_sig and base_peak_mz == 0.0:
                base_peak_mz = mz
            ions_list.append(IonPeak(mz=mz, signal=sig, relative_intensity=rel_int))

        # Sort ions by m/z
        ions_list.sort(key=lambda x: x.mz)

        spectrum = MassSpectrum(
            peak_id=pid,
            ions=ions_list,
            base_peak_mz=base_peak_mz,
            base_peak_signal=base_peak_sig
        )

        if pid in peaks_dict:
            peaks_dict[pid].spectrum = spectrum
        else:
            # Peak was in MS sheet but not in peaks sheet; create entry
            peaks_dict[pid] = PeakData(
                peak_id=pid,
                rt=0.0,
                area=0.0,
                relative_area_pct=0.0,
                spectrum=spectrum
            )

    # Sort peaks by Peak ID or RT
    peaks_list = sorted(peaks_dict.values(), key=lambda p: (p.rt if p.rt > 0 else p.peak_id))

    return chromatogram_points, peaks_list, total_area
