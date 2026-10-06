"""
High-performance SQLite index and matcher for NIST .MSP Library.
Indexes 240,000+ spectra for sub-millisecond retrieval of candidate matches.
Decoupled from Streamlit or any web framework.
"""

import os
import sqlite3
import json
from typing import List, Tuple, Dict, Optional, Callable
from ..models import MassSpectrum, NistCandidate
from .similarity import compute_spectral_similarity, spectrum_to_mz_pairs
from .msp_parser import parse_msp_entry_from_text


# Pre-seeded fallback reference compounds for common GC-MS peaks (air, solvents, alkanes, siloxanes)
COMMON_GCMS_REFERENCES = [
    {
        "name": "Nitrogen / Air",
        "formula": "N2",
        "mw": 28,
        "cas": "7727-37-9",
        "peaks": [(28, 999), (14, 140), (29, 8)]
    },
    {
        "name": "Oxygen / Air",
        "formula": "O2",
        "mw": 32,
        "cas": "7782-44-7",
        "peaks": [(32, 999), (16, 85)]
    },
    {
        "name": "Carbon Dioxide",
        "formula": "CO2",
        "mw": 44,
        "cas": "124-38-9",
        "peaks": [(44, 999), (28, 98), (16, 85), (12, 35)]
    },
    {
        "name": "Methanol",
        "formula": "CH4O",
        "mw": 32,
        "cas": "67-56-1",
        "peaks": [(31, 999), (32, 760), (29, 640), (15, 130), (28, 60)]
    },
    {
        "name": "Ethanol",
        "formula": "C2H6O",
        "mw": 46,
        "cas": "64-17-5",
        "peaks": [(31, 999), (45, 420), (29, 210), (46, 150), (27, 140), (43, 90)]
    },
    {
        "name": "Acetone",
        "formula": "C3H6O",
        "mw": 58,
        "cas": "67-64-1",
        "peaks": [(43, 999), (58, 280), (15, 120), (27, 40), (42, 35)]
    },
    {
        "name": "Dichloromethane (Methylene chloride)",
        "formula": "CH2Cl2",
        "mw": 84,
        "cas": "75-09-2",
        "peaks": [(49, 999), (84, 580), (86, 370), (51, 320), (47, 110), (35, 90)]
    },
    {
        "name": "Hexane",
        "formula": "C6H14",
        "mw": 86,
        "cas": "110-54-3",
        "peaks": [(57, 999), (43, 850), (41, 560), (29, 420), (27, 330), (56, 310), (86, 120)]
    },
    {
        "name": "Heptane",
        "formula": "C7H16",
        "mw": 100,
        "cas": "142-82-5",
        "peaks": [(43, 999), (57, 440), (71, 310), (41, 290), (29, 240), (100, 110)]
    },
    {
        "name": "Octane",
        "formula": "C8H18",
        "mw": 114,
        "cas": "111-65-9",
        "peaks": [(43, 999), (57, 460), (85, 280), (41, 270), (71, 260), (29, 210), (114, 90)]
    },
    {
        "name": "Nonane",
        "formula": "C9H20",
        "mw": 128,
        "cas": "111-84-2",
        "peaks": [(43, 999), (57, 540), (85, 230), (71, 220), (41, 210), (29, 180), (128, 80)]
    },
    {
        "name": "Decane",
        "formula": "C10H22",
        "mw": 142,
        "cas": "124-18-5",
        "peaks": [(57, 999), (43, 890), (71, 480), (85, 280), (41, 240), (29, 190), (142, 60)]
    },
    {
        "name": "Toluene",
        "formula": "C7H8",
        "mw": 92,
        "cas": "108-88-3",
        "peaks": [(91, 999), (92, 680), (65, 140), (39, 110), (51, 80)]
    },
    {
        "name": "Octamethylcyclotetrasiloxane (D4, Column Bleed)",
        "formula": "C8H24O4Si4",
        "mw": 296,
        "cas": "556-67-2",
        "peaks": [(281, 999), (73, 210), (282, 180), (133, 110), (265, 80), (207, 70)]
    },
    {
        "name": "Decamethylcyclopentasiloxane (D5, Column Bleed)",
        "formula": "C10H30O5Si5",
        "mw": 370,
        "cas": "541-02-6",
        "peaks": [(73, 999), (355, 620), (267, 180), (147, 140), (281, 110)]
    }
]


class NistLibraryMatcher:
    """Manages NIST database querying and candidate matching."""

    def __init__(self, msp_path: str = "database/Base de Datos NIST.MSP", db_path: str = "database/nist_library.sqlite"):
        self.msp_path = msp_path
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Creates SQLite tables if they do not exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nist_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    formula TEXT,
                    mw REAL,
                    cas TEXT,
                    base_peak INTEGER,
                    top_ions TEXT,
                    offset INTEGER,
                    length INTEGER
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nist_base_peak ON nist_index(base_peak)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nist_mw ON nist_index(mw)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nist_name ON nist_index(name)")
            conn.commit()

    def is_indexed(self) -> bool:
        """Returns True if the index table has records."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM nist_index")
                count = cursor.fetchone()[0]
                return count > 1000
        except Exception:
            return False

    def get_index_count(self) -> int:
        """Returns the number of indexed spectra."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM nist_index")
                return cursor.fetchone()[0]
        except Exception:
            return 0

    def build_index(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> int:
        """
        Parses the MSP file and builds the SQLite index.
        Takes ~5-15 seconds for 240,000+ spectra.
        """
        if not os.path.exists(self.msp_path):
            return 0

        total_bytes = os.path.getsize(self.msp_path)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM nist_index")
            conn.commit()

            batch = []
            count = 0
            
            with open(self.msp_path, "r", encoding="utf-8", errors="ignore") as f:
                cur_name = ""
                cur_formula = ""
                cur_mw = 0.0
                cur_cas = ""
                reading_peaks = False
                peaks_accumulator = []
                entry_start_offset = 0
                current_offset = 0

                for line in f:
                    line_len = len(line.encode("utf-8"))
                    line_s = line.strip()

                    if line_s.startswith("Name:"):
                        # If we have a previous entry, save it
                        if cur_name and peaks_accumulator:
                            peaks_accumulator.sort(key=lambda x: x[1], reverse=True)
                            base_peak = int(round(peaks_accumulator[0][0]))
                            top_ions_str = ",".join(str(int(round(p[0]))) for p in peaks_accumulator[:6])
                            entry_len = current_offset - entry_start_offset
                            batch.append((cur_name, cur_formula, cur_mw, cur_cas, base_peak, top_ions_str, entry_start_offset, entry_len))
                            count += 1

                            if len(batch) >= 10000:
                                cursor.executemany("""
                                    INSERT INTO nist_index (name, formula, mw, cas, base_peak, top_ions, offset, length)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """, batch)
                                conn.commit()
                                batch.clear()
                                if progress_callback:
                                    progress_callback(current_offset, total_bytes)

                        # Start new entry
                        cur_name = line_s[5:].strip()
                        cur_formula = ""
                        cur_mw = 0.0
                        cur_cas = ""
                        reading_peaks = False
                        peaks_accumulator = []
                        entry_start_offset = current_offset

                    elif line_s.startswith("Formula:"):
                        cur_formula = line_s[8:].strip()
                    elif line_s.startswith("MW:"):
                        try:
                            cur_mw = float(line_s[3:].strip())
                        except ValueError:
                            cur_mw = 0.0
                    elif line_s.startswith("CAS#:"):
                        cas_raw = line_s[5:].strip()
                        if ";" in cas_raw:
                            cas_raw = cas_raw.split(";")[0].strip()
                        cur_cas = cas_raw
                    elif line_s.startswith("Num Peaks:"):
                        reading_peaks = True
                    elif reading_peaks:
                        if not line_s:
                            reading_peaks = False
                        else:
                            for item in line_s.split(";"):
                                item_s = item.strip()
                                if item_s:
                                    tokens = item_s.split()
                                    if len(tokens) >= 2:
                                        try:
                                            peaks_accumulator.append((float(tokens[0]), float(tokens[1])))
                                        except ValueError:
                                            pass

                    current_offset += line_len

                # Final entry
                if cur_name and peaks_accumulator:
                    peaks_accumulator.sort(key=lambda x: x[1], reverse=True)
                    base_peak = int(round(peaks_accumulator[0][0]))
                    top_ions_str = ",".join(str(int(round(p[0]))) for p in peaks_accumulator[:6])
                    entry_len = current_offset - entry_start_offset
                    batch.append((cur_name, cur_formula, cur_mw, cur_cas, base_peak, top_ions_str, entry_start_offset, entry_len))
                    count += 1

                if batch:
                    cursor.executemany("""
                        INSERT INTO nist_index (name, formula, mw, cas, base_peak, top_ions, offset, length)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, batch)
                    conn.commit()

        return count

    def search_candidates(self, spectrum: MassSpectrum, top_k: int = 5) -> List[NistCandidate]:
        """
        Finds the top NIST candidate compounds for a given mass spectrum.
        Uses Stein-Scott cosine similarity (dot-product).
        """
        if not spectrum or not spectrum.ions:
            return []

        query_pairs = spectrum_to_mz_pairs(spectrum)
        base_mz = int(round(spectrum.base_peak_mz))
        top_mz_list = spectrum.get_prominent_mz_list(4)

        candidates: List[NistCandidate] = []

        # 1. Search indexed SQLite if available
        if self.is_indexed() and os.path.exists(self.msp_path):
            try:
                candidate_records = []
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    # Query records with matching base peak (+/- 1) or prominent ions
                    query = """
                        SELECT name, formula, mw, cas, offset, length
                        FROM nist_index
                        WHERE base_peak IN (?, ?, ?)
                        LIMIT 60
                    """
                    cursor.execute(query, (base_mz, base_mz - 1, base_mz + 1))
                    candidate_records.extend(cursor.fetchall())

                    # If few records, search by second prominent ion
                    if len(candidate_records) < 15 and len(top_mz_list) > 1:
                        ion2 = top_mz_list[1]
                        cursor.execute("""
                            SELECT name, formula, mw, cas, offset, length
                            FROM nist_index
                            WHERE base_peak = ?
                            LIMIT 30
                        """, (ion2,))
                        candidate_records.extend(cursor.fetchall())

                # Deduplicate records by offset
                seen_offsets = set()
                unique_records = []
                for rec in candidate_records:
                    if rec[4] not in seen_offsets:
                        seen_offsets.add(rec[4])
                        unique_records.append(rec)

                # Open MSP file and compute spectral similarity for candidate records
                with open(self.msp_path, "r", encoding="utf-8", errors="ignore") as f:
                    for name, formula, mw, cas, offset, length in unique_records:
                        f.seek(offset)
                        block_text = f.read(length)
                        entry_data = parse_msp_entry_from_text(block_text)
                        if entry_data and entry_data.get("peaks"):
                            score = compute_spectral_similarity(query_pairs, entry_data["peaks"])
                            candidates.append(NistCandidate(
                                name=name,
                                formula=formula,
                                mw=mw,
                                cas=cas,
                                similarity_score=round(score, 1),
                                base_peak=entry_data["base_peak"]
                            ))

            except Exception as e:
                # If error in DB search, fall through to fallback
                pass

        # 2. Check fallback common GC-MS references
        for ref in COMMON_GCMS_REFERENCES:
            score = compute_spectral_similarity(query_pairs, ref["peaks"])
            if score > 20.0:
                candidates.append(NistCandidate(
                    name=ref["name"],
                    formula=ref["formula"],
                    mw=float(ref["mw"]),
                    cas=ref["cas"],
                    similarity_score=round(score, 1),
                    base_peak=ref["peaks"][0][0]
                ))

        # Sort all candidates by similarity score descending
        candidates.sort(key=lambda c: c.similarity_score, reverse=True)

        # Deduplicate candidates by compound name
        unique_candidates: List[NistCandidate] = []
        seen_names = set()
        for cand in candidates:
            name_key = cand.name.lower().strip()
            if name_key not in seen_names:
                seen_names.add(name_key)
                unique_candidates.append(cand)
            if len(unique_candidates) >= top_k:
                break

        return unique_candidates
