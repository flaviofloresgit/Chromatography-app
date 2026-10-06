"""
Chromatographic Quantification Engine.
Calculates normalized peak areas, percentages, and statistical summaries.
Decoupled from Streamlit or any web framework.
"""

from typing import List, Dict, Any, Optional
from ..models import PeakData, IdentificationResult


def calculate_relative_areas(peaks: List[PeakData], internal_standard_id: Optional[int] = None) -> float:
    """
    Computes and updates relative area % for each peak.
    If internal_standard_id is provided, areas can be referenced against it.
    Returns total integrated area.
    """
    if not peaks:
        return 0.0

    total_area = sum(p.area for p in peaks if p.area > 0)
    if total_area <= 0:
        return 0.0

    for p in peaks:
        if p.area > 0:
            p.relative_area_pct = (p.area / total_area) * 100.0
        else:
            p.relative_area_pct = 0.0

    return total_area


def compute_sample_statistics(
    peaks: List[PeakData],
    identifications: List[IdentificationResult]
) -> Dict[str, Any]:
    """
    Generates chromatographic and analytical statistics for a sample.
    """
    total_area = sum(p.area for p in peaks)
    peak_count = len(peaks)

    if not peaks or total_area <= 0:
        return {
            "total_area": 0.0,
            "peak_count": 0,
            "major_peaks_count": 0,
            "minor_peaks_count": 0,
            "trace_peaks_count": 0,
            "identified_area_pct": 0.0,
            "unidentified_area_pct": 100.0,
            "rt_range": (0.0, 0.0),
            "top_compounds": []
        }

    # Classification by abundance
    major_peaks = [p for p in peaks if p.relative_area_pct >= 5.0]
    minor_peaks = [p for p in peaks if 1.0 <= p.relative_area_pct < 5.0]
    trace_peaks = [p for p in peaks if p.relative_area_pct < 1.0]

    # Calculate identified % vs unidentified %
    id_map = {ident.peak_id: ident for ident in identifications}
    identified_area = sum(
        p.area for p in peaks 
        if p.peak_id in id_map and id_map[p.peak_id].compound_name and "unknown" not in id_map[p.peak_id].compound_name.lower()
    )
    identified_pct = (identified_area / total_area) * 100.0 if total_area > 0 else 0.0

    rts = [p.rt for p in peaks if p.rt > 0]
    rt_range = (min(rts), max(rts)) if rts else (0.0, 0.0)

    # Top 5 compounds by area
    sorted_peaks = sorted(peaks, key=lambda p: p.area, reverse=True)
    top_compounds = []
    for p in sorted_peaks[:5]:
        ident = id_map.get(p.peak_id)
        name = ident.compound_name if ident else f"Pico #{p.peak_id}"
        top_compounds.append({
            "peak_id": p.peak_id,
            "name": name,
            "rt": round(p.rt, 3),
            "area": p.area,
            "relative_area_pct": round(p.relative_area_pct, 2),
            "confidence": ident.confidence_level if ident else "N/A"
        })

    return {
        "total_area": total_area,
        "peak_count": peak_count,
        "major_peaks_count": len(major_peaks),
        "minor_peaks_count": len(minor_peaks),
        "trace_peaks_count": len(trace_peaks),
        "identified_area_pct": round(identified_pct, 2),
        "unidentified_area_pct": round(100.0 - identified_pct, 2),
        "rt_range": (round(rt_range[0], 2), round(rt_range[1], 2)),
        "top_compounds": top_compounds
    }
