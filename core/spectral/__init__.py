"""
Spectral matching and NIST library utilities.
"""

from .similarity import compute_spectral_similarity, spectrum_to_mz_pairs
from .msp_parser import parse_msp_entry_from_text, stream_msp_entries
from .library_index import NistLibraryMatcher

__all__ = [
    "compute_spectral_similarity",
    "spectrum_to_mz_pairs",
    "parse_msp_entry_from_text",
    "stream_msp_entries",
    "NistLibraryMatcher"
]
