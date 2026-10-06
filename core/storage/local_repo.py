"""
Local file-based repository fallback for sample history and analysis results.
Decoupled from Streamlit or any web framework.
"""

import os
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..models import (
    SampleAnalysis,
    SampleMetadata,
    PeakData,
    IdentificationResult,
    ChromatogramPoint,
    MassSpectrum,
    IonPeak
)
from .repository_interface import BaseSampleRepository


class LocalSampleRepository(BaseSampleRepository):
    """Local JSON/filesystem storage for chromatographic analysis history."""

    def __init__(self, storage_dir: str = "local_storage"):
        self.storage_dir = storage_dir
        self.samples_file = os.path.join(storage_dir, "samples.json")
        self.files_dir = os.path.join(storage_dir, "raw_files")
        self.chat_file = os.path.join(storage_dir, "chat_history.json")
        self._ensure_storage()

    def _ensure_storage(self):
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self.files_dir, exist_ok=True)
        if not os.path.exists(self.samples_file):
            with open(self.samples_file, "w", encoding="utf-8") as f:
                json.dump({}, f)
        if not os.path.exists(self.chat_file):
            with open(self.chat_file, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _load_samples(self) -> Dict[str, Any]:
        try:
            with open(self.samples_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_samples(self, data: Dict[str, Any]):
        with open(self.samples_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save_sample_analysis(
        self,
        analysis: SampleAnalysis,
        raw_file_bytes: Optional[bytes] = None,
        raw_filename: str = ""
    ) -> str:
        sample_id = analysis.sample_id or str(uuid.uuid4())
        analysis.sample_id = sample_id

        # Save raw file if provided
        saved_file_path = ""
        if raw_file_bytes and raw_filename:
            safe_name = f"{sample_id}_{raw_filename}"
            saved_file_path = os.path.join(self.files_dir, safe_name)
            with open(saved_file_path, "wb") as f:
                f.write(raw_file_bytes)

        samples = self._load_samples()

        # Serialize analysis
        record = {
            "sample_id": sample_id,
            "sample_name": analysis.metadata.sample_name,
            "sample_code": analysis.metadata.sample_code,
            "analysis_date": analysis.metadata.analysis_date,
            "column_type": analysis.metadata.column_type,
            "carrier_gas": analysis.metadata.carrier_gas,
            "flow_rate": analysis.metadata.flow_rate,
            "inlet_temperature": analysis.metadata.inlet_temperature,
            "oven_program": analysis.metadata.oven_program,
            "split_ratio": analysis.metadata.split_ratio,
            "operator": analysis.metadata.operator,
            "notes": analysis.metadata.notes,
            "original_file_name": raw_filename or analysis.metadata.original_file_name,
            "file_path": saved_file_path,
            "total_area": analysis.total_area,
            "peak_count": len(analysis.peaks),
            "summary_ai": analysis.summary_ai,
            "created_at": analysis.created_at,
            # Serialize peaks (without massive chromatogram points for fast listing)
            "peaks": [
                {
                    "peak_id": p.peak_id,
                    "rt": p.rt,
                    "area": p.area,
                    "relative_area_pct": p.relative_area_pct,
                    "spectrum": {
                        "peak_id": p.spectrum.peak_id,
                        "base_peak_mz": p.spectrum.base_peak_mz,
                        "base_peak_signal": p.spectrum.base_peak_signal,
                        "ions": [(ion.mz, ion.signal, ion.relative_intensity) for ion in p.spectrum.ions]
                    } if p.spectrum else None
                }
                for p in analysis.peaks
            ],
            "identifications": [ident.to_dict() for ident in analysis.identifications],
            "chromatogram_downsampled": [
                (pt.rt, pt.signal) for i, pt in enumerate(analysis.chromatogram) if i % 2 == 0
            ]
        }

        samples[sample_id] = record
        self._save_samples(samples)
        return sample_id

    def get_sample_analysis(self, sample_id: str) -> Optional[SampleAnalysis]:
        samples = self._load_samples()
        record = samples.get(sample_id)
        if not record:
            return None

        metadata = SampleMetadata(
            sample_name=record.get("sample_name", ""),
            sample_code=record.get("sample_code", ""),
            analysis_date=record.get("analysis_date", ""),
            column_type=record.get("column_type", ""),
            carrier_gas=record.get("carrier_gas", ""),
            flow_rate=record.get("flow_rate", ""),
            inlet_temperature=record.get("inlet_temperature", ""),
            oven_program=record.get("oven_program", ""),
            split_ratio=record.get("split_ratio", ""),
            operator=record.get("operator", ""),
            notes=record.get("notes", ""),
            original_file_name=record.get("original_file_name", "")
        )

        peaks = []
        for p_data in record.get("peaks", []):
            spec_data = p_data.get("spectrum")
            spectrum = None
            if spec_data:
                ions = [
                    IonPeak(mz=ion[0], signal=ion[1], relative_intensity=ion[2])
                    for ion in spec_data.get("ions", [])
                ]
                spectrum = MassSpectrum(
                    peak_id=spec_data["peak_id"],
                    ions=ions,
                    base_peak_mz=spec_data["base_peak_mz"],
                    base_peak_signal=spec_data["base_peak_signal"]
                )
            peaks.append(PeakData(
                peak_id=p_data["peak_id"],
                rt=p_data["rt"],
                area=p_data["area"],
                relative_area_pct=p_data["relative_area_pct"],
                spectrum=spectrum
            ))

        identifications = [
            IdentificationResult(**ident_data)
            for ident_data in record.get("identifications", [])
        ]

        chromatogram = [
            ChromatogramPoint(rt=pt[0], signal=pt[1])
            for pt in record.get("chromatogram_downsampled", [])
        ]

        return SampleAnalysis(
            sample_id=sample_id,
            metadata=metadata,
            chromatogram=chromatogram,
            peaks=peaks,
            identifications=identifications,
            total_area=record.get("total_area", 0.0),
            summary_ai=record.get("summary_ai", ""),
            created_at=record.get("created_at", "")
        )

    def list_samples(self) -> List[Dict[str, Any]]:
        samples = self._load_samples()
        items = []
        for sid, rec in samples.items():
            items.append({
                "sample_id": sid,
                "sample_name": rec.get("sample_name", "Sin nombre"),
                "sample_code": rec.get("sample_code", ""),
                "analysis_date": rec.get("analysis_date", ""),
                "peak_count": rec.get("peak_count", len(rec.get("peaks", []))),
                "total_area": rec.get("total_area", 0.0),
                "created_at": rec.get("created_at", ""),
                "operator": rec.get("operator", "")
            })
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    def delete_sample(self, sample_id: str) -> bool:
        samples = self._load_samples()
        if sample_id in samples:
            # Delete raw file if exists
            fpath = samples[sample_id].get("file_path")
            if fpath and os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except OSError:
                    pass
            del samples[sample_id]
            self._save_samples(samples)
            return True
        return False

    def save_chat_message(self, sample_id: str, role: str, content: str) -> None:
        try:
            with open(self.chat_file, "r", encoding="utf-8") as f:
                chats = json.load(f)
        except Exception:
            chats = {}

        if sample_id not in chats:
            chats[sample_id] = []
        chats[sample_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        with open(self.chat_file, "w", encoding="utf-8") as f:
            json.dump(chats, f, indent=2, ensure_ascii=False)

    def get_chat_history(self, sample_id: str) -> List[Dict[str, str]]:
        try:
            with open(self.chat_file, "r", encoding="utf-8") as f:
                chats = json.load(f)
                return chats.get(sample_id, [])
        except Exception:
            return []
