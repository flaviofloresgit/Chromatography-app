"""
Parser for NIST .MSP format mass spectral libraries.
Decoupled from Streamlit or any web framework.
"""

from typing import List, Tuple, Dict, Optional, Iterator
import re


def parse_peaks_line(line: str) -> List[Tuple[float, float]]:
    """
    Parses a line of peaks formatted as 'mz intensity; mz intensity; ...' or 'mz:intensity'.
    """
    peaks: List[Tuple[float, float]] = []
    # Common separators in MSP: ';' or ' ' or '\t'
    entries = line.split(";")
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split()
        if len(parts) >= 2:
            try:
                mz = float(parts[0])
                intensity = float(parts[1])
                peaks.append((mz, intensity))
            except ValueError:
                continue
    return peaks


def parse_msp_entry_from_text(block: str) -> Optional[Dict]:
    """
    Parses a single MSP block string into a structured dictionary.
    """
    entry = {
        "name": "",
        "formula": "",
        "mw": 0.0,
        "cas": "",
        "peaks": [],
        "base_peak": 0.0,
        "top_ions": []
    }
    
    lines = block.splitlines()
    reading_peaks = False

    for line in lines:
        line_s = line.strip()
        if not line_s:
            continue

        if line_s.startswith("Name:"):
            entry["name"] = line_s[5:].strip()
        elif line_s.startswith("Formula:"):
            entry["formula"] = line_s[8:].strip()
        elif line_s.startswith("MW:"):
            try:
                entry["mw"] = float(line_s[3:].strip())
            except ValueError:
                pass
        elif line_s.startswith("CAS#:"):
            # CAS might be followed by NIST#: e.g. "CAS#: 1333-74-0; NIST#: 245692"
            raw_cas = line_s[5:].strip()
            if ";" in raw_cas:
                raw_cas = raw_cas.split(";")[0].strip()
            entry["cas"] = raw_cas
        elif line_s.startswith("Num Peaks:"):
            reading_peaks = True
        elif reading_peaks:
            peaks = parse_peaks_line(line_s)
            entry["peaks"].extend(peaks)

    if not entry["name"] or not entry["peaks"]:
        return None

    # Determine base peak & top ions
    entry["peaks"].sort(key=lambda x: x[1], reverse=True)
    if entry["peaks"]:
        entry["base_peak"] = entry["peaks"][0][0]
        entry["top_ions"] = [int(round(p[0])) for p in entry["peaks"][:5]]

    return entry


def stream_msp_entries(file_path: str) -> Iterator[Tuple[Dict, int, int]]:
    """
    Generator that streams entries from a .MSP file.
    Yields (entry_dict, byte_offset, byte_length)
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        current_lines = []
        start_offset = 0
        current_offset = 0

        for line in f:
            line_len = len(line.encode("utf-8"))
            line_s = line.strip()

            if line_s.startswith("Name:") and current_lines:
                # Process previous block
                block_text = "\n".join(current_lines)
                block_len = current_offset - start_offset
                entry = parse_msp_entry_from_text(block_text)
                if entry:
                    yield entry, start_offset, block_len
                current_lines = [line]
                start_offset = current_offset
            else:
                current_lines.append(line)

            current_offset += line_len

        # Last entry
        if current_lines:
            block_text = "\n".join(current_lines)
            block_len = current_offset - start_offset
            entry = parse_msp_entry_from_text(block_text)
            if entry:
                yield entry, start_offset, block_len
