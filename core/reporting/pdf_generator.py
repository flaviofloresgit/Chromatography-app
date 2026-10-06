"""
Professional PDF Report Generator for GC-MS Chromatography Analysis.
Uses ReportLab and Matplotlib to produce laboratory test reports.
Decoupled from Streamlit or any web framework.
"""

import io
import os
from typing import Optional, List
from datetime import datetime
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
    HRFlowable
)

from ..models import SampleAnalysis, PeakData, IdentificationResult, ChromatogramPoint


def generate_chromatogram_image(
    chromatogram: List[ChromatogramPoint],
    peaks: List[PeakData],
    identifications: List[IdentificationResult]
) -> io.BytesIO:
    """Renders a high-resolution chromatogram chart into a BytesIO PNG."""
    fig, ax = plt.subplots(figsize=(8.5, 3.2), dpi=200)

    # Plot TIC curve
    if chromatogram:
        rts = [p.rt for p in chromatogram]
        signals = [p.signal for p in chromatogram]
        ax.plot(rts, signals, color="#1E3A8A", linewidth=1.2, label="TIC (Total Ion Chromatogram)")
        ax.fill_between(rts, 0, signals, color="#3B82F6", alpha=0.15)
    elif peaks:
        # Fallback if raw chromatogram was downsampled to none
        rts = [p.rt for p in peaks]
        areas = [p.area for p in peaks]
        ax.stem(rts, areas, linefmt="#1E3A8A", markerfmt="o", basefmt="gray")

    # Annotate top 8 major peaks with compound names or peak IDs
    id_map = {ident.peak_id: ident for ident in identifications}
    top_peaks = sorted(peaks, key=lambda p: p.area, reverse=True)[:8]

    # Find max signal for annotation offset
    max_sig = max([p.signal for p in chromatogram]) if chromatogram else (max([p.area for p in peaks]) if peaks else 1)

    for p in top_peaks:
        ident = id_map.get(p.peak_id)
        label = ident.compound_name[:15] if ident and ident.compound_name else f"P{p.peak_id}"
        ax.annotate(
            f"{label}\n({p.rt:.2f}m)",
            xy=(p.rt, max_sig * 0.8),
            xytext=(p.rt, max_sig * 0.95),
            arrowprops=dict(facecolor="#DC2626", edgecolor="#DC2626", arrowstyle="->", lw=1),
            fontsize=6.5,
            ha="center",
            va="bottom",
            color="#0F172A",
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#F8FAFC", edgecolor="#CBD5E1", alpha=0.85)
        )

    ax.set_title("Cromatograma de Iones Totales (TIC) - Clarus 690 GC-MS", fontsize=10, fontweight="bold", pad=8, color="#1E293B")
    ax.set_xlabel("Tiempo de Retención (minutos)", fontsize=8, labelpad=4, color="#334155")
    ax.set_ylabel("Abundancia / Señal", fontsize=8, labelpad=4, color="#334155")
    ax.tick_params(axis="both", which="major", labelsize=7.5)
    ax.grid(True, linestyle="--", alpha=0.4, color="#E2E8F0")

    # Clean borders
    for spine in ax.spines.values():
        spine.set_color("#CBD5E1")

    plt.tight_layout()
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format="png", bbox_inches="tight")
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer


def generate_analysis_pdf(analysis: SampleAnalysis) -> bytes:
    """
    Builds an executive PDF laboratory report for a given SampleAnalysis.
    Returns the raw PDF bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    color_primary = colors.HexColor("#0F172A")    # Slate 900
    color_accent = colors.HexColor("#1D4ED8")     # Blue 700
    color_muted = colors.HexColor("#475569")      # Slate 600
    color_bg_light = colors.HexColor("#F8FAFC")   # Slate 50
    color_border = colors.HexColor("#E2E8F0")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=color_primary
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=color_accent
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=color_accent,
        spaceBefore=10,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=color_primary
    )

    body_bold = ParagraphStyle(
        "BodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=color_primary
    )

    small_style = ParagraphStyle(
        "SmallMuted",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=color_muted
    )

    table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
        textColor=colors.white,
        alignment=1
    )

    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=color_primary
    )

    table_cell_center = ParagraphStyle(
        "TableCellCenter",
        parent=table_cell,
        alignment=1
    )

    elements = []

    # 1. HEADER
    header_data = [
        [
            Paragraph("<b>INFORME DE ENSAYO CROMATOGRÁFICO GC-MS</b>", title_style),
            Paragraph(f"<b>FECHA:</b> {analysis.metadata.analysis_date}<br/><b>INFORME #:</b> {analysis.sample_id[:8].upper()}", small_style)
        ],
        [
            Paragraph("Laboratorio de Análisis Instrumental • Identificación Espectral por IA & NIST", subtitle_style),
            Paragraph(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", small_style)
        ]
    ]
    t_header = Table(header_data, colWidths=[400, 140])
    t_header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(t_header)
    elements.append(HRFlowable(width="100%", thickness=1.5, color=color_accent, spaceBefore=4, spaceAfter=8))

    # 2. SAMPLE & INSTRUMENTAL METADATA BOX
    m = analysis.metadata
    meta_data = [
        [
            Paragraph("<b>Muestra:</b>", body_bold), Paragraph(m.sample_name or "N/A", body_style),
            Paragraph("<b>Equipo:</b>", body_bold), Paragraph("PerkinElmer Clarus 690 / SQ 8 MS (EI 70 eV)", body_style)
        ],
        [
            Paragraph("<b>Código Muestra:</b>", body_bold), Paragraph(m.sample_code or "N/A", body_style),
            Paragraph("<b>Columna:</b>", body_bold), Paragraph(m.column_type or "Elite-5MS", body_style)
        ],
        [
            Paragraph("<b>Gas Portador:</b>", body_bold), Paragraph(f"{m.carrier_gas} ({m.flow_rate})", body_style),
            Paragraph("<b>Programa Horno:</b>", body_bold), Paragraph(m.oven_program or "N/A", body_style)
        ],
        [
            Paragraph("<b>Inyector / Split:</b>", body_bold), Paragraph(f"{m.inlet_temperature} / {m.split_ratio}", body_style),
            Paragraph("<b>Operador / Notas:</b>", body_bold), Paragraph(f"{m.operator or 'N/A'} • {m.notes or ''}", body_style)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[80, 185, 85, 190])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color_bg_light),
        ("BOX", (0, 0), (-1, -1), 0.5, color_border),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, color_border),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 8))

    # 3. CHROMATOGRAM GRAPH
    try:
        chart_img_buf = generate_chromatogram_image(analysis.chromatogram, analysis.peaks, analysis.identifications)
        elements.append(Image(chart_img_buf, width=7.5 * inch, height=2.8 * inch))
        elements.append(Spacer(1, 6))
    except Exception:
        pass

    # 4. EXECUTIVE SUMMARY BOX
    id_map = {ident.peak_id: ident for ident in analysis.identifications}
    total_area = sum(p.area for p in analysis.peaks)
    identified_area = sum(p.area for p in analysis.peaks if p.peak_id in id_map and id_map[p.peak_id].compound_name and "unknown" not in id_map[p.peak_id].compound_name.lower())
    purity_pct = (identified_area / total_area * 100.0) if total_area > 0 else 0.0

    summary_ai = analysis.summary_ai or "Análisis cromatográfico procesado con espectrometría de masas Clarus SQ 8 y red neuronal Gemini AI."
    summary_paragraph = Paragraph(f"<b>Evaluación Analítica de la IA:</b> {summary_ai}", body_style)

    summary_table_data = [
        [
            Paragraph(f"<b>Total Picos:</b> {len(analysis.peaks)}", body_style),
            Paragraph(f"<b>Área Total:</b> {total_area:,.0f}", body_style),
            Paragraph(f"<b>Pureza Asignada:</b> {purity_pct:.1f}%", body_style),
            Paragraph(f"<b>Picos Mayores (>5%):</b> {sum(1 for p in analysis.peaks if p.relative_area_pct >= 5.0)}", body_style),
        ],
        [
            summary_paragraph, "", "", ""
        ]
    ]
    t_summary = Table(summary_table_data, colWidths=[130, 140, 130, 140])
    t_summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F8FAFC")),
        ("SPAN", (0, 1), (-1, 1)),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
        ("INNERGRID", (0, 0), (-1, 0), 0.25, colors.HexColor("#BFDBFE")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_summary)
    elements.append(Spacer(1, 8))

    # 5. COMPOUNDS IDENTIFICATION TABLE
    elements.append(Paragraph("<b>TABLA DE CUANTIFICACIÓN E IDENTIFICACIÓN DE COMPUESTOS</b>", section_heading))

    table_rows = [
        [
            Paragraph("ID", table_header),
            Paragraph("RT (min)", table_header),
            Paragraph("Área", table_header),
            Paragraph("Área %", table_header),
            Paragraph("Compuesto Identificado", table_header),
            Paragraph("Fórmula", table_header),
            Paragraph("PM", table_header),
            Paragraph("CAS", table_header),
            Paragraph("NIST %", table_header),
            Paragraph("Conf.", table_header)
        ]
    ]

    for p in sorted(analysis.peaks, key=lambda x: (x.rt if x.rt > 0 else x.peak_id)):
        ident = id_map.get(p.peak_id)
        c_name = ident.compound_name if ident else f"Pico #{p.peak_id}"
        formula = ident.formula if ident else "-"
        mw_str = f"{ident.molecular_weight:.1f}" if ident and ident.molecular_weight > 0 else "-"
        cas = ident.cas_number if ident else "-"
        nist_s = f"{ident.nist_similarity:.1f}%" if ident and ident.nist_similarity > 0 else "-"
        conf = ident.confidence_level if ident else "Low"

        table_rows.append([
            Paragraph(str(p.peak_id), table_cell_center),
            Paragraph(f"{p.rt:.3f}", table_cell_center),
            Paragraph(f"{p.area:,.0f}", table_cell),
            Paragraph(f"<b>{p.relative_area_pct:.2f}%</b>", table_cell_center),
            Paragraph(f"<b>{c_name}</b>", table_cell),
            Paragraph(formula, table_cell_center),
            Paragraph(mw_str, table_cell_center),
            Paragraph(cas, table_cell_center),
            Paragraph(nist_s, table_cell_center),
            Paragraph(conf, table_cell_center),
        ])

    col_widths = [24, 42, 60, 42, 160, 52, 34, 52, 40, 34]
    t_compounds = Table(table_rows, colWidths=col_widths, repeatRows=1)
    
    # Table styling with alternating rows
    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), color_accent),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("INNERGRID", (0, 0), (-1, -1), 0.2, color_border),
        ("BOX", (0, 0), (-1, -1), 0.5, color_primary),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    for r_idx in range(1, len(table_rows)):
        if r_idx % 2 == 0:
            t_style.append(("BACKGROUND", (0, r_idx), (-1, r_idx), color_bg_light))
    t_compounds.setStyle(TableStyle(t_style))
    elements.append(t_compounds)
    elements.append(Spacer(1, 10))

    # 6. SIGNATURE BLOCK
    sig_data = [
        [
            Paragraph("___________________________________<br/><b>Analista Instrumental</b><br/>" + (m.operator or "Especialista GC-MS"), body_style),
            Paragraph("___________________________________<br/><b>Responsable de Laboratorio</b><br/>Control de Calidad / Aprobado", body_style)
        ]
    ]
    t_sig = Table(sig_data, colWidths=[270, 270])
    t_sig.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(KeepTogether(t_sig))

    # Build document
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
