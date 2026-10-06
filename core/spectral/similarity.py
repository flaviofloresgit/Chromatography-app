"""
Spectral similarity calculations for Mass Spectrometry (GC-MS).
Implements the Stein-Scott / Cosine similarity (Dot Product) matching algorithm.
Decoupled from Streamlit or any web framework.
"""

import math
from typing import List, Tuple, Dict
from ..models import IonPeak, MassSpectrum, NistCandidate


def compute_spectral_similarity(
    query_spectrum: List[Tuple[float, float]],
    library_spectrum: List[Tuple[float, float]],
    m_exp: float = 0.6,
    n_exp: float = 2.0
) -> float:
    """
    Computes the weighted cosine similarity (Stein-Scott / NIST algorithm)
    between a query spectrum and a library spectrum.
    
    Each ion weight W = (Intensity ^ m_exp) * (m/z ^ n_exp)
    Similarity = (sum(W_q * W_lib))^2 / (sum(W_q^2) * sum(W_lib^2)) * 100.0

    Returns:
        similarity_score: float from 0.0 to 100.0%
    """
    if not query_spectrum or not library_spectrum:
        return 0.0

    # Build dictionaries mapping rounded integer m/z to intensity
    q_dict: Dict[int, float] = {}
    for mz, intens in query_spectrum:
        mz_int = int(round(mz))
        q_dict[mz_int] = q_dict.get(mz_int, 0.0) + intens

    lib_dict: Dict[int, float] = {}
    for mz, intens in library_spectrum:
        mz_int = int(round(mz))
        lib_dict[mz_int] = lib_dict.get(mz_int, 0.0) + intens

    # Normalize max intensity to 1000 in both spectra
    max_q = max(q_dict.values()) if q_dict else 1.0
    max_lib = max(lib_dict.values()) if lib_dict else 1.0

    if max_q == 0 or max_lib == 0:
        return 0.0

    # Collect all unique m/z
    all_mz = set(q_dict.keys()).union(set(lib_dict.keys()))

    dot_product = 0.0
    sum_q_sq = 0.0
    sum_lib_sq = 0.0

    for mz in all_mz:
        iq = (q_dict.get(mz, 0.0) / max_q) * 1000.0
        ilib = (lib_dict.get(mz, 0.0) / max_lib) * 1000.0

        # Weighted intensity
        wq = (iq ** m_exp) * (mz ** n_exp) if iq > 0 else 0.0
        wlib = (ilib ** m_exp) * (mz ** n_exp) if ilib > 0 else 0.0

        dot_product += wq * wlib
        sum_q_sq += wq * wq
        sum_lib_sq += wlib * wlib

    denominator = sum_q_sq * sum_lib_sq
    if denominator <= 0:
        return 0.0

    # Dot product similarity (0.0 to 100.0%)
    similarity = (dot_product * dot_product) / denominator * 100.0
    return min(100.0, max(0.0, similarity))


def spectrum_to_mz_pairs(spectrum: MassSpectrum) -> List[Tuple[float, float]]:
    """Converts MassSpectrum object to list of (mz, signal) pairs."""
    return [(ion.mz, ion.signal) for ion in spectrum.ions]
