"""Probe (not a check): the two Parquet layouts and the content digest on full-range uint16 planes.

ADR 0008's evidence for the choice of layout (PQ2) and the cost of the content digest (PQ6) on
JUMP-like data, the case the owner named. Synthetic and seeded: 90 channel planes of
1080 x 1080 uint16 pixels over the whole 0..65535 range (a background mode, a long bright tail
and saturated pixels), close to the study's JUMP planes (median 22,326 distinct values, 34 % of
the bins). It times the vectorised writer of PQ8 (``np.bincount`` + ``np.flatnonzero``, no
per-bin Python loop), the size of the list layout of version 6 and of the long layout of the
study, and a vectorised content digest checked against the reference one.

``python -I tools/plane_histograms_v6/probe_full_range.py`` (needs numpy and pyarrow). Prints a
Markdown table; numbers depend on the machine. Nothing imports it.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import struct
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import make_tables as mt  # noqa: E402

v6 = mt.v6
PLANES, SIDE, CHANNELS = 18, 1080, ("Actin", "DNA", "ER", "Mito", "RNA")


def planes(seed: int = 20261117):
    rng = np.random.default_rng(seed)
    for image in range(PLANES):
        out = {}
        for k, cid in enumerate(CHANNELS):
            n = SIDE * SIDE
            base = rng.normal(1500 + 400 * k, 250, n)
            bright = rng.exponential(2500 + 600 * k, n)
            pixels = np.where(rng.random(n) < 0.35, base + bright, base)
            pixels[rng.random(n) < 0.002] = 65535  # saturated
            out[cid] = np.clip(np.rint(pixels), 0, 65535).astype(np.uint16)
        yield image, out


def histogram(pixels: np.ndarray):
    """The PQ8 writer step: exact bins by np.bincount, the non-zero ones by np.flatnonzero."""
    lo, hi = int(pixels.min()), int(pixels.max())
    dense = np.bincount(pixels.ravel() - lo if lo else pixels.ravel(), minlength=hi - lo + 1)
    index = np.flatnonzero(dense)
    return lo, hi, index.astype(np.int32), dense[index].astype(np.int64)


def build_tables(records):
    ids = sorted(CHANNELS)
    columns = v6.table_columns(ids)
    data = {name: [] for name, _ in columns}
    long = {"plane_id": [], "channel": [], "bin": [], "count": []}
    for image, by_channel in records:
        meta = mt.plane(f"img{image:02d}", 0, "CTRL", "uint16", 16, list(CHANNELS), SIDE * SIDE, 65536)
        for name, value in meta.items():
            data[name].append(value)
        for cid in ids:
            lo, hi, index, counts = by_channel[cid]
            values = (str(lo), str(hi), SIDE * SIDE, str(lo), str(hi), 0, 0.0, 0.0, 0, 0.0, 0.0)
            for (name, _), value in zip(v6.channel_columns(cid)[:-2], values, strict=True):
                data[name].append(value)
            data[f"Histogram_Bins_{cid}"].append(pa.array(index, pa.int32()))
            data[f"Histogram_Counts_{cid}"].append(pa.array(counts, pa.int64()))
            long["plane_id"].append(np.full(index.size, image, np.int32))
            long["channel"].append(np.full(index.size, ids.index(cid), np.int32))
            long["bin"].append(index)
            long["count"].append(counts)
    arrays = []
    for name, kind in columns:
        if kind.startswith("list"):
            chunks = data[name]
            offsets = np.concatenate([[0], np.cumsum([len(c) for c in chunks])]).astype(np.int32)
            arrays.append(pa.ListArray.from_arrays(pa.array(offsets), pa.concat_arrays(chunks)))
        else:
            arrays.append(pa.array(data[name], mt.ARROW[kind]))
    wide = pa.Table.from_arrays(arrays, schema=pa.schema([(n, mt.ARROW[k]) for n, k in columns]))
    long_table = pa.table({key: np.concatenate(value) for key, value in long.items()})
    return wide, long_table


def fast_content_sha256(table: pa.Table) -> str:
    """The PQ6 digest with NumPy per column (equal to ``v6.content_sha256``; checked below)."""
    h = hashlib.sha256(v6.CONTENT_PREAMBLE + struct.pack("<QQ", table.num_rows, table.num_columns))
    for field in table.schema:
        kind = v6._type_name(field.type)
        name = field.name.encode()
        h.update(struct.pack("<Q", len(name)) + name + struct.pack("<B", v6._TYPE_CODE[kind]))
        column = table.column(field.name).combine_chunks()
        if not kind.startswith("list"):
            out = io.BytesIO()
            for value in column.to_pylist():  # one value per plane: a short loop
                if value is None:
                    out.write(b"\x00")
                elif kind == "string":
                    out.write(b"\x01" + struct.pack("<Q", len(value.encode())) + value.encode())
                else:
                    out.write(b"\x01" + struct.pack("<q" if kind == "int64" else "<d", value))
            h.update(out.getvalue())
            continue
        offsets = column.offsets.to_numpy()
        values = column.values.to_numpy().astype("<i4" if kind == "list<int32>" else "<i8")
        valid = column.is_valid().to_numpy(zero_copy_only=False)
        for row in range(len(column)):  # one slice per plane, no per-bin loop
            if not valid[row]:
                h.update(b"\x00")
                continue
            part = values[offsets[row]:offsets[row + 1]]
            h.update(b"\x01" + struct.pack("<Q", part.size) + part.tobytes())
    return h.hexdigest()


def main() -> None:
    records, t_hist = [], 0.0
    for image, by_channel in planes():
        start = time.perf_counter()
        records.append((image, {cid: histogram(p) for cid, p in by_channel.items()}))
        t_hist += time.perf_counter() - start
    wide, long_table = build_tables(records)
    distinct = [r[1][c][2].size for r in records for c in CHANNELS]
    rows = []
    with tempfile.TemporaryDirectory() as folder:
        for label, table in (("v6 list columns (one row per plane)", wide), ("long (study layout)", long_table)):
            path = Path(folder) / "t.parquet"
            start = time.perf_counter()
            pq.write_table(table, path, **{k: v for k, v in mt.PROFILE.items() if label.startswith("v6") or k == "compression"})
            t_write = time.perf_counter() - start
            start = time.perf_counter()
            pq.read_table(path)
            t_read = time.perf_counter() - start
            rows.append((label, path.stat().st_size / 1024, t_write * 1e3, t_read * 1e3))
        path = Path(folder) / "t.parquet"
        pq.write_table(wide, path, **mt.PROFILE)
        start = time.perf_counter()
        table = v6.read_table(path)
        t_check = time.perf_counter() - start
        start = time.perf_counter()
        fast = fast_content_sha256(table)
        t_fast = time.perf_counter() - start
        start = time.perf_counter()
        reference = v6.content_sha256(table)
        t_ref = time.perf_counter() - start
    assert fast == reference
    print(f"{len(distinct)} channel planes, distinct values per plane median {int(np.median(distinct)):,} "
          f"({np.median(distinct) / 65536:.0%} of the bins); pyarrow {pa.__version__}, numpy {np.__version__}")
    print(f"histograms (np.bincount + np.flatnonzero, 90 planes): {t_hist * 1e3:.0f} ms\n")
    print("| layout | KiB | write ms | read ms |\n|---|---:|---:|---:|")
    for label, kib, w, r in rows:
        print(f"| {label} | {kib:,.0f} | {w:.0f} | {r:.0f} |")
    print(f"\nreference reader (all checks, pure Python): {t_check * 1e3:.0f} ms; content digest: "
          f"vectorised {t_fast * 1e3:.0f} ms, reference {t_ref * 1e3:.0f} ms (equal)")


if __name__ == "__main__":
    main()
