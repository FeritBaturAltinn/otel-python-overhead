import csv
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

RESULTS = Path("results")
MEASURE_SECONDS = 30  # length of the measure phase in load.js
PATTERN = re.compile(r"^(none|noexport|otlp)-(\d+)-(\d+)\.json$")
MODES = ["none", "noexport", "otlp"]

# ---- load raw results ----
rows = []
for f in sorted(RESULTS.glob("*.json")):
    m = PATTERN.match(f.name)
    if not m:
        continue
    mode, spans, rep = m.group(1), int(m.group(2)), int(m.group(3))
    metrics = json.loads(f.read_text())["metrics"]
    dur = metrics["http_req_duration{phase:measure}"]
    count = metrics["http_reqs{phase:measure}"]["count"]
    rows.append({
        "mode": mode, "spans": spans, "rep": rep,
        "mean_ms": dur["avg"], "p95_ms": dur["p(95)"], "p99_ms": dur["p(99)"],
        "rps": count / MEASURE_SECONDS,
    })
if not rows:
    raise SystemExit("No result files found in results/ - run run_all.ps1 first.")

with open(RESULTS / "raw.csv", "w", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

# ---- aggregate over repetitions ----
def stats(mode, spans, key):
    vals = [r[key] for r in rows if r["mode"] == mode and r["spans"] == spans]
    return np.median(vals), (np.percentile(vals, 75) - np.percentile(vals, 25)), len(vals)

span_counts = sorted({r["spans"] for r in rows})
print(f"{'mode':10} {'spans':>5} {'mean ms':>9} {'sd':>7} {'p99 ms':>8} {'req/s':>8} {'runs':>5}")
summary = []
for mode in MODES:
    for n in span_counts:
        mean, sd, k = stats(mode, n, "mean_ms")
        p99, _, _ = stats(mode, n, "p99_ms")
        rps, _, _ = stats(mode, n, "rps")
        summary.append((mode, n, mean, sd, p99, rps, k))
        print(f"{mode:10} {n:5d} {mean:9.3f} {sd:7.3f} {p99:8.3f} {rps:8.0f} {k:5d}")

with open(RESULTS / "summary.csv", "w", newline="") as fh:
    writer = csv.writer(fh)
    writer.writerow(["mode", "spans", "mean_ms", "sd_ms", "p99_ms", "req_per_s", "runs"])
    writer.writerows(summary)

# ---- linear fit: latency = intercept + slope * spans ----
print("\nLinear fit of mean latency against spans per request")
fits = {}
for mode in MODES:
    xs = span_counts
    ys = [stats(mode, n, "mean_ms")[0] for n in span_counts]
    slope, intercept = np.polyfit(xs, ys, 1)
    fits[mode] = (slope, intercept)
    print(f"{mode:10} slope = {slope * 1000:8.2f} us/span   intercept = {intercept:6.3f} ms")

print("\nOverhead relative to 'none'")
for mode in ["noexport", "otlp"]:
    per_span = (fits[mode][0] - fits["none"][0]) * 1000
    fixed = fits[mode][1] - fits["none"][1]
    print(f"{mode:10} extra cost per span = {per_span:7.2f} us   fixed cost per request = {fixed:6.3f} ms")

# ---- plot ----
plt.figure(figsize=(7, 4.5))
for mode in MODES:
    ns = span_counts
    ms = [stats(mode, n, "mean_ms")[0] for n in ns]
    sds = [stats(mode, n, "mean_ms")[1] for n in ns]
    plt.errorbar(ns, ms, yerr=sds, marker="o", capsize=3, label=mode)
plt.xlabel("spans per request")
plt.ylabel("mean latency (ms)")
plt.title("Latency vs. spans per request")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(RESULTS / "latency_vs_spans.png", dpi=150)
print("\nSaved results/latency_vs_spans.png, summary.csv and raw.csv")