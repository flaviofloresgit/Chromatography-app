"""
Supabase repository implementation for cloud sample storage, history and file uploads.
Decoupled from Streamlit or any web framework.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..models import (
    SampleAnalysis,
    SampleMetadata,
    PeakData,
    IdentificationResult,
    ChromatogramPoint
)
from .repository_interface import BaseSampleRepository

try:
    from supabase import create_client, Client
    SUPABASE_LIB_AVAILABLE = True
except ImportError:
    SUPABASE_LIB_AVAILABLE = False


class SupabaseSampleRepository(BaseSampleRepository):
    """PostgreSQL and Cloud Storage persistence via Supabase."""

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        bucket_name: str = "chromatography-files"
    ):
        self.url = supabase_url or os.getenv("SUPABASE_URL", "")
        self.key = supabase_key or os.getenv("SUPABASE_KEY", "")
        self.bucket_name = bucket_name or os.getenv("SUPABASE_STORAGE_BUCKET", "chromatography-files")
        self.client: Optional[Client] = None

        if SUPABASE_LIB_AVAILABLE and self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
            except Exception:
                self.client = None

    def is_connected(self) -> bool:
        """Returns True if the Supabase client is connected."""
        return self.client is not None

    def save_sample_analysis(
        self,
        analysis: SampleAnalysis,
        raw_file_bytes: Optional[bytes] = None,
        raw_filename: str = ""
    ) -> str:
        if not self.client:
            raise ConnectionError("No se ha inicializado la conexión a Supabase.")

        storage_path = ""
        # 1. Upload raw file to Supabase Storage if provided
        if raw_file_bytes and raw_filename:
            storage_path = f"raw_samples/{analysis.sample_id}_{raw_filename}"
            try:
                self.client.storage.from_(self.bucket_name).upload(
                    path=storage_path,
                    file=raw_file_bytes,
                    file_options={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
                )
            except Exception:
                # If file already exists or upload fails, continue with DB insert
                pass

        # 2. Insert into samples table
        sample_record = {
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
            "storage_file_path": storage_path,
            "total_area": analysis.total_area,
            "peak_count": len(analysis.peaks)
        }

        res = self.client.table("samples").insert(sample_record).execute()
        if not res.data:
            raise RuntimeError("Fallo al insertar la muestra en la tabla 'samples'.")

        db_sample_id = res.data[0]["id"]
        analysis.sample_id = db_sample_id

        # 3. Batch insert peaks
        peaks_payload = [
            {
                "sample_id": db_sample_id,
                "peak_id": p.peak_id,
                "retention_time": p.rt,
                "area": p.area,
                "relative_area_pct": p.relative_area_pct
            }
            for p in analysis.peaks
        ]
        if peaks_payload:
            self.client.table("peaks").insert(peaks_payload).execute()

        # 4. Batch insert identifications
        idents_payload = [
            {
                "sample_id": db_sample_id,
                "peak_id": ident.peak_id,
                "compound_name": ident.compound_name,
                "iupac_name": ident.iupac_name,
                "cas_number": ident.cas_number,
                "formula": ident.formula,
                "molecular_weight": ident.molecular_weight,
                "confidence_level": ident.confidence_level,
                "confidence_score": ident.confidence_score,
                "nist_similarity": ident.nist_similarity,
                "identification_source": ident.identification_source,
                "chemical_family": ident.chemical_family,
                "retention_behavior_analysis": ident.retention_behavior_analysis,
                "fragmentation_rationale": ident.fragmentation_rationale,
                "key_ions": ident.key_ions,
                "alternative_candidates": ident.alternative_candidates
            }
            for ident in analysis.identifications
        ]
        if idents_payload:
            self.client.table("identifications").insert(idents_payload).execute()

        return db_sample_id

    def get_sample_analysis(self, sample_id: str) -> Optional[SampleAnalysis]:
        if not self.client:
            return None

        # Fetch sample row
        res_sample = self.client.table("samples").select("*").eq("id", sample_id).execute()
        if not res_sample.data:
            return None
        rec = res_sample.data[0]

        metadata = SampleMetadata(
            sample_name=rec.get("sample_name", ""),
            sample_code=rec.get("sample_code", ""),
            analysis_date=rec.get("analysis_date", ""),
            column_type=rec.get("column_type", ""),
            carrier_gas=rec.get("carrier_gas", ""),
            flow_rate=rec.get("flow_rate", ""),
            inlet_temperature=rec.get("inlet_temperature", ""),
            oven_program=rec.get("oven_program", ""),
            split_ratio=rec.get("split_ratio", ""),
            operator=rec.get("operator", ""),
            notes=rec.get("notes", ""),
            original_file_name=rec.get("original_file_name", "")
        )

        # Fetch peaks
        res_peaks = self.client.table("peaks").select("*").eq("sample_id", sample_id).order("peak_id").execute()
        peaks = [
            PeakData(
                peak_id=p["peak_id"],
                rt=p["retention_time"],
                area=p["area"],
                relative_area_pct=p["relative_area_pct"]
            )
            for p in res_peaks.data
        ]

        # Fetch identifications
        res_idents = self.client.table("identifications").select("*").eq("sample_id", sample_id).order("peak_id").execute()
        identifications = [
            IdentificationResult(
                peak_id=item["peak_id"],
                rt=next((p.rt for p in peaks if p.peak_id == item["peak_id"]), 0.0),
                area=next((p.area for p in peaks if p.peak_id == item["peak_id"]), 0.0),
                relative_area_pct=next((p.relative_area_pct for p in peaks if p.peak_id == item["peak_id"]), 0.0),
                compound_name=item["compound_name"],
                iupac_name=item.get("iupac_name", ""),
                cas_number=item.get("cas_number", ""),
                formula=item.get("formula", ""),
                molecular_weight=item.get("molecular_weight", 0.0),
                confidence_level=item.get("confidence_level", "Medium"),
                confidence_score=item.get("confidence_score", 0.0),
                nist_similarity=item.get("nist_similarity", 0.0),
                identification_source=item.get("identification_source", ""),
                chemical_family=item.get("chemical_family", ""),
                retention_behavior_analysis=item.get("retention_behavior_analysis", ""),
                fragmentation_rationale=item.get("fragmentation_rationale", ""),
                key_ions=item.get("key_ions", []),
                alternative_candidates=item.get("alternative_candidates", [])
            )
            for item in res_idents.data
        ]

        return SampleAnalysis(
            sample_id=sample_id,
            metadata=metadata,
            peaks=peaks,
            identifications=identifications,
            total_area=rec.get("total_area", 0.0),
            created_at=rec.get("created_at", "")
        )

    def list_samples(self) -> List[Dict[str, Any]]:
        if not self.client:
            return []

        res = self.client.table("samples").select("id, sample_name, sample_code, analysis_date, peak_count, total_area, created_at, operator").order("created_at", desc=True).execute()
        return [
            {
                "sample_id": item["id"],
                "sample_name": item.get("sample_name", "Sin nombre"),
                "sample_code": item.get("sample_code", ""),
                "analysis_date": item.get("analysis_date", ""),
                "peak_count": item.get("peak_count", 0),
                "total_area": item.get("total_area", 0.0),
                "created_at": item.get("created_at", ""),
                "operator": item.get("operator", "")
            }
            for item in res.data
        ]

    def delete_sample(self, sample_id: str) -> bool:
        if not self.client:
            return False

        res = self.client.table("samples").delete().eq("id", sample_id).execute()
        return len(res.data) > 0

    def save_chat_message(self, sample_id: str, role: str, content: str) -> None:
        if not self.client:
            return

        self.client.table("chat_messages").insert({
            "sample_id": sample_id,
            "role": role,
            "content": content
        }).execute()

    def get_chat_history(self, sample_id: str) -> List[Dict[str, str]]:
        if not self.client:
            return []

        res = self.client.table("chat_messages").select("role, content, created_at").eq("sample_id", sample_id).order("created_at", desc=False).execute()
        return [
            {"role": item["role"], "content": item["content"]}
            for item in res.data
        ]
