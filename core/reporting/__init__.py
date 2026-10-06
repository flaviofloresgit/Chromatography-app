"""
Reporting package for chromatography laboratory exports (PDF, etc).
"""

from .pdf_generator import generate_analysis_pdf

__all__ = ["generate_analysis_pdf"]
