#!/usr/bin/env python3
"""آپلود چندبخشی فایل بزرگ به نشست resumable گوگل‌درایو (پروتکل X-Goog-Upload).

استفاده: UPLOAD_URI='...' python3 upload_resumable.py output/master_final.mp4 [--chunk-mib 8] [--max-chunks N]
وضعیت از روی هدر X-Goog-Upload-Status / X-Goog-Upload-Size-Received خوانده می‌شود.
"""
import argparse, http.client, os, sys, time
from pathlib import Path
from urllib.parse import urlparse

def req(uri, body, headers):
    u = urlparse(uri)
    conn = http.client.HTTPSConnection(u.hostname, 443, timeout=180)
    path = u.path + "?" + u.query
    conn.request("PUT", path, body=body, headers=headers)
    r = conn.getresponse()
    data = r.read()
    hdrs = {k.lower(): v for k, v in r.getheaders()}
    conn.close()
    return r.status, hdrs, data

def query(uri):
    st, h, data = req(uri, b"", {"X-Goog-Upload-Command": "query", "Content-Length": "0"})
    print("QUERY", st, {k: v for k, v in h.items() if "goog" in k or k == "range"}, data[:200])
    if "x-goog-upload-size-received" in h:
        return int(h["x-goog-upload-size-received"])
    if "range" in h and "-" in h["range"]:
        return int(h["range"].rsplit("-", 1)[1]) + 1
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--chunk-mib", type=float, default=8.0)
    ap.add_argument("--max-chunks", type=int, default=0)
    a = ap.parse_args()
    uri = os.environ["UPLOAD_URI"]
    f = Path(a.file); total = f.stat().st_size
    chunk = int(a.chunk_mib * 1024 * 1024)
    assert chunk % (256 * 1024) == 0, "chunk must be multiple of 256KiB"
    off = query(uri) or 0
    print(f"start offset={off} total={total} chunk={chunk}")
    sent = 0; t0 = time.time()
    with open(f, "rb") as fh:
        fh.seek(off)
        while off < total:
            data = fh.read(chunk)
            last = off + len(data) >= total
            headers = {
                "X-Goog-Upload-Offset": str(off),
                "X-Goog-Upload-Command": "upload, finalize" if last else "upload",
                "X-Goog-Upload-Total-Size": str(total),
                "Content-Type": "video/mp4",
            }
            st, h, resp = req(uri, data, headers)
            status = h.get("x-goog-upload-status", "")
            recv = h.get("x-goog-upload-size-received")
            print(f"PUT off={off} len={len(data)} -> HTTP {st} status={status!r} received={recv} {resp[:160]!r}", flush=True)
            if st >= 400:
                print("ERROR body:", resp[:2000]); sys.exit(2)
            q = query(uri)
            off = q if q is not None else off + len(data)
            fh.seek(off)
            sent += 1
            if status.lower() == "final" or (last and st in (200, 201)):
                break
            if a.max_chunks and sent >= a.max_chunks:
                print(f"paused by --max-chunks at offset {off} ({off / total:.1%}) in {time.time() - t0:.0f}s"); return
    print(f"DONE offset={off}/{total} in {time.time() - t0:.0f}s")
    print("FINAL QUERY:", query(uri))

if __name__ == "__main__":
    main()
