"""
Reusable UI components for Streamlit views.
"""

import streamlit as st
from typing import Dict, Any, Optional
from core.models import IdentificationResult, PeakData


def render_header(title: str, subtitle: str, badges: Optional[list] = None):
    """Renders the top application hero header with status pills."""
    badges_html = ""
    if badges:
        badges_html = "<div style='margin-top: 0.65rem; display: flex; gap: 0.5rem; flex-wrap: wrap;'>"
        for b_text, b_type in badges:
            badges_html += f"<span class='badge badge-{b_type}'>{b_text}</span>"
        badges_html += "</div>"

    html = f"""
    <div class="lab-header">
        <h1>{title}</h1>
        <p>{subtitle}</p>
        {badges_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_metric_card(label: str, value: str, subtext: str = ""):
    """Renders a modern metric card."""
    sub_html = f"<div class='metric-sub'>{subtext}</div>" if subtext else ""
    html = f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {sub_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_confidence_badge(level: str, score: Optional[float] = None) -> str:
    """Returns HTML for a confidence badge."""
    lvl = level.lower().strip()
    badge_cls = "badge-medium"
    if "high" in lvl or "alto" in lvl:
        badge_cls = "badge-high"
    elif "low" in lvl or "bajo" in lvl:
        badge_cls = "badge-low"

    score_str = f" ({score:.1f}%)" if score is not None and score > 0 else ""
    return f"<span class='badge {badge_cls}'>{level}{score_str}</span>"


def render_peak_details_card(peak: PeakData, ident: Optional[IdentificationResult]):
    """Renders a card with chemical and spectral reasoning for a selected peak."""
    if not ident:
        st.info(f"No hay identificación registrada para el Pico #{peak.peak_id}")
        return

    badge_html = render_confidence_badge(ident.confidence_level, ident.confidence_score)
    nist_str = f"{ident.nist_similarity:.1f}%" if ident.nist_similarity > 0 else "N/A"
    mw_str = f"{ident.molecular_weight:.1f} g/mol" if ident.molecular_weight > 0 else "N/A"

    html = f"""
    <div class="compound-box">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
            <div>
                <h3 style="margin: 0; color: #0F172A; font-size: 1.15rem; font-weight: 700;">
                    Pico #{peak.peak_id}: {ident.compound_name}
                </h3>
                <div style="font-size: 0.8rem; color: #64748B; margin-top: 0.2rem;">
                    <b>IUPAC:</b> {ident.iupac_name or 'N/A'} • <b>Familia:</b> {ident.chemical_family or 'Orgánico general'}
                </div>
            </div>
            <div>{badge_html}</div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.6rem; margin: 0.75rem 0; background: white; padding: 0.65rem 0.85rem; border-radius: 8px; border: 1px solid #E2E8F0;">
            <div><span style="font-size: 0.72rem; color: #64748B;">TIEMPO RETENCIÓN (RT)</span><br><b>{peak.rt:.3f} min</b></div>
            <div><span style="font-size: 0.72rem; color: #64748B;">ÁREA RELATIVA (%)</span><br><b>{peak.relative_area_pct:.2f}%</b></div>
            <div><span style="font-size: 0.72rem; color: #64748B;">FÓRMULA / PM</span><br><b>{ident.formula or 'N/A'} ({mw_str})</b></div>
            <div><span style="font-size: 0.72rem; color: #64748B;">NÚMERO CAS</span><br><b>{ident.cas_number or 'N/A'}</b></div>
            <div><span style="font-size: 0.72rem; color: #64748B;">SIMILITUD NIST</span><br><b>{nist_str}</b></div>
        </div>
        <div style="font-size: 0.84rem; color: #1E293B; margin-top: 0.6rem;">
            <b>Justificación Espectral (IA):</b> {ident.fragmentation_rationale or 'Asignado por biblioteca NIST.'}
        </div>
        <div style="font-size: 0.82rem; color: #475569; margin-top: 0.35rem;">
            <b>Comportamiento Cromatográfico:</b> {ident.retention_behavior_analysis or 'Coherente con fase no polar Elite-5MS.'}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
