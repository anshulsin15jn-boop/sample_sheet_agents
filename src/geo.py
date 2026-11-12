"""Read sample metadata from the header of a GEO series matrix file.

A series matrix file is a gzipped text file. Its header has one line per metadata field, and each
line holds one value per sample, in quotes and separated by tabs, for example:

    !Sample_title	"asthma patient 1"	"healthy control 2"
    !Sample_characteristics_ch1	"disease state: asthma"	"disease state: control"

The expression numbers come after the line `!series_matrix_table_begin`. We never need them,
so `stream_header` reads only until that line and then stops the download.
"""
from __future__ import annotations

import re
import zlib

import requests

TABLE_BEGIN = "!series_matrix_table_begin"


def stream_header(url: str, max_bytes: int = 30_000_000, timeout: int = 60) -> str:
    """Download a gzipped series matrix file only up to the expression table and return the header."""
    dec = zlib.decompressobj(16 + zlib.MAX_WBITS)   # 16 + MAX_WBITS means "expect a gzip wrapper"
    text = ""
    got = 0
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        for chunk in r.iter_content(64 * 1024):
            got += len(chunk)
            text += dec.decompress(chunk).decode("utf-8", errors="replace")
            i = text.find(TABLE_BEGIN)
            if i >= 0:
                return text[:i]
            if got > max_bytes:
                raise RuntimeError(f"header not found in first {max_bytes} bytes of {url}")
    return text


def _split_line(line: str) -> tuple[str, list[str]]:
    parts = line.rstrip("\r\n").split("\t")
    return parts[0], [p.strip().strip('"').strip() for p in parts[1:]]


def parse_header(text: str) -> dict:
    """Parse header text into series info and per sample metadata rows.

    Returns {"series_title": str, "samples": [GSM ids], "rows": [row dicts]} where each row is
    {"row_id", "name", "values"} with one value per sample. Rows are:
      title       the sample title
      source      the source name (ch1)
      char_0 ...  each !Sample_characteristics_ch1 line, in file order. The index matches the
                  `trait_row` numbering used in the GenoTEX expert code.
    """
    series_title = ""
    samples: list[str] = []
    title: list[str] | None = None
    source: list[str] | None = None
    chars: list[list[str]] = []
    for line in text.splitlines():
        if not line.startswith("!"):
            continue
        key, vals = _split_line(line)
        if key == "!Series_title" and not series_title:
            series_title = vals[0] if vals else ""
        elif key == "!Sample_geo_accession":
            samples = vals
        elif key == "!Sample_title":
            title = vals
        elif key == "!Sample_source_name_ch1":
            source = vals
        elif key == "!Sample_characteristics_ch1":
            chars.append(vals)
    rows = []
    if title is not None:
        rows.append({"row_id": "title", "name": "sample title", "values": title})
    if source is not None:
        rows.append({"row_id": "source", "name": "source name", "values": source})
    for i, vals in enumerate(chars):
        rows.append({"row_id": f"char_{i}", "name": f"characteristics line {i}", "values": vals})
    n = len(samples)
    for r in rows:   # pad or trim so every row has exactly one value per sample
        r["values"] = (r["values"] + [""] * n)[:n]
    return {"series_title": series_title, "samples": samples, "rows": rows}


def matrix_url(gse: str, filename: str) -> str:
    """NCBI FTP (over https) location of a series matrix file, e.g. GSE182nnn/GSE182797/matrix/."""
    stub = gse[:-3] + "nnn" if len(gse) > 6 else "GSEnnn"
    return f"https://ftp.ncbi.nlm.nih.gov/geo/series/{stub}/{gse}/matrix/{filename}"


def parse_expert_trait_row(code_text: str) -> int | None | str:
    """Find the last `trait_row = ...` assignment in GenoTEX expert code (read as text, never run).

    Returns an int, None, or "unparsed" if no simple assignment is found.
    """
    hits = re.findall(r"^\s*trait_row\s*=\s*(\d+|None)\b", code_text, flags=re.M)
    if not hits:
        return "unparsed"
    return None if hits[-1] == "None" else int(hits[-1])
