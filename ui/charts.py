"""
Interactive Plotly charts for GC-MS Total Ion Chromatograms (TIC) and Mass Spectra.
"""

from typing import List, Optional, Tuple, Dict
import plotly.graph_objects as go
from core.models import ChromatogramPoint, PeakData, IdentificationResult, MassSpectrum


def plot_interactive_chromatogram(
    chromatogram: List[ChromatogramPoint],
    peaks: List[PeakData],
    identifications: List[IdentificationResult],
    selected_peak_id: Optional[int] = None
) -> go.Figure:
    """
    Renders an interactive Plotly chromatogram with peak markers and compound tooltips.
    """
    fig = go.Figure()

    # 1. Total Ion Chromatogram (TIC) curve
    if chromatogram:
        rts = [p.rt for p in chromatogram]
        signals = [p.signal for p in chromatogram]

        fig.add_trace(go.Scatter(
            x=rts,
            y=signals,
            mode="lines",
            name="Cromatograma (TIC)",
            line=dict(color="#2563EB", width=1.5),
            fill="tozeroy",
            fillcolor="rgba(37, 99, 235, 0.08)",
            hovertemplate="<b>RT:</b> %{x:.3f} min<br><b>Señal:</b> %{y:,.0f}<extra></extra>"
        ))

    # 2. Peak markers for integrated peaks
    if peaks:
        id_map = {ident.peak_id: ident for ident in identifications}
        peak_rts = []
        peak_signals = []
        hover_texts = []
        marker_colors = []

        # Find closest signal in chromatogram for accurate peak marker height
        chrom_dict = {round(p.rt, 2): p.signal for p in chromatogram} if chromatogram else {}

        for p in peaks:
            ident = id_map.get(p.peak_id)
            c_name = ident.compound_name if ident else f"Pico #{p.peak_id}"
            conf = ident.confidence_level if ident else "N/A"

            # Height estimation
            sig = chrom_dict.get(round(p.rt, 2))
            if not sig and chromatogram:
                # Find nearest
                nearest = min(chromatogram, key=lambda x: abs(x.rt - p.rt))
                sig = nearest.signal
            elif not sig:
                sig = p.area

            peak_rts.append(p.rt)
            peak_signals.append(sig)

            hover_texts.append(
                f"<b>Pico #{p.peak_id}: {c_name}</b><br>"
                f"RT: {p.rt:.3f} min<br>"
                f"Área: {p.area:,.0f} ({p.relative_area_pct:.2f}%)<br>"
                f"Confianza: {conf}"
            )

            if selected_peak_id is not None and p.peak_id == selected_peak_id:
                marker_colors.append("#DC2626")  # Selected = Red
            else:
                marker_colors.append("#0F766E")  # Teal

        fig.add_trace(go.Scatter(
            x=peak_rts,
            y=peak_signals,
            mode="markers",
            name="Picos Integrados",
            marker=dict(
                size=8,
                color=marker_colors,
                symbol="circle",
                line=dict(width=1.5, color="#FFFFFF")
            ),
            hovertext=hover_texts,
            hoverinfo="text"
        ))

    # Highlight selected peak with vertical line if requested
    if selected_peak_id is not None:
        sel_peak = next((p for p in peaks if p.peak_id == selected_peak_id), None)
        if sel_peak:
            fig.add_vline(
                x=sel_peak.rt,
                line_width=1.5,
                line_dash="dash",
                line_color="#DC2626",
                annotation_text=f"Pico #{sel_peak.peak_id} ({sel_peak.rt:.2f} min)",
                annotation_position="top left",
                annotation_font=dict(size=11, color="#DC2626")
            )

    fig.update_layout(
        title=dict(
            text="Cromatograma de Iones Totales (TIC) - PerkinElmer Clarus 690",
            font=dict(size=14, color="#0F172A", family="Inter")
        ),
        xaxis=dict(
            title="Tiempo de Retención RT (minutos)",
            showgrid=True,
            gridcolor="#F1F5F9",
            zeroline=False
        ),
        yaxis=dict(
            title="Señal / Abundancia",
            showgrid=True,
            gridcolor="#F1F5F9",
            zeroline=False
        ),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        height=380,
        margin=dict(l=50, r=30, t=50, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="closest"
    )

    return fig


def plot_mass_spectrum(
    spectrum: MassSpectrum,
    compound_name: str = "",
    reference_ions: Optional[List[Tuple[float, float]]] = None
) -> go.Figure:
    """
    Renders an interactive mass spectrum bar chart with m/z ion annotations.
    """
    fig = go.Figure()

    if not spectrum or not spectrum.ions:
        fig.add_annotation(text="No hay espectro de masas disponible para este pico", showarrow=False)
        fig.update_layout(height=300)
        return fig

    # Experimental Spectrum
    mzs = [ion.mz for ion in spectrum.ions]
    intensities = [ion.relative_intensity for ion in spectrum.ions]

    fig.add_trace(go.Bar(
        x=mzs,
        y=intensities,
        name="Espectro Observado (Muestra)",
        marker_color="#2563EB",
        width=0.8,
        hovertemplate="<b>m/z:</b> %{x:.1f}<br><b>Intensidad Relativa:</b> %{y:.1f} / 1000<extra></extra>"
    ))

    # Annotate top 6 prominent ions
    top_ions = sorted(spectrum.ions, key=lambda x: x.relative_intensity, reverse=True)[:6]
    annotations = []
    for ion in top_ions:
        if ion.relative_intensity > 30:  # Only annotate meaningful ions
            annotations.append(dict(
                x=ion.mz,
                y=ion.relative_intensity,
                text=f"<b>{int(round(ion.mz))}</b>",
                showarrow=True,
                arrowhead=0,
                arrowsize=0.3,
                arrowwidth=0.8,
                arrowcolor="#64748B",
                ax=0,
                ay=-15,
                font=dict(size=9, color="#1E293B", family="JetBrains Mono")
            ))

    title_text = f"Espectro de Masas EI (70 eV) - Pico #{spectrum.peak_id}"
    if compound_name:
        title_text += f": {compound_name}"

    fig.update_layout(
        title=dict(
            text=title_text,
            font=dict(size=13, color="#0F172A", family="Inter")
        ),
        xaxis=dict(
            title="Relación Masa/Carga (m/z)",
            showgrid=True,
            gridcolor="#F8FAFC",
            dtick=20,
            range=[max(0, min(mzs) - 10), max(mzs) + 15]
        ),
        yaxis=dict(
            title="Abundancia Relativa (Norm. a 1000)",
            showgrid=True,
            gridcolor="#F8FAFC",
            range=[0, 1100]
        ),
        annotations=annotations,
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        height=320,
        margin=dict(l=45, r=25, t=45, b=40)
    )

    return fig
