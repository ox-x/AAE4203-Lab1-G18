# AAE4203 Lab 1 — GNSS Single Point Positioning (Group 18)

Course: **AAE4203 Guidance and Navigation**, The Hong Kong Polytechnic University,
Semester 1 2026/27.

Group 18 (receiver kit K08): CHIU Sung Lim (23078005D), RAMOS CRUZ Axel Daniel
(26009386X), YU Mengzhi (24102853D), ZHANG Borui (24102982D).

Report: [`report/AAE4203_Lab1_GNSS_Report_G18.pdf`](report/AAE4203_Lab1_GNSS_Report_G18.pdf)

This repository contains the raw measurements, the converters, the single point
positioning (SPP) solver written from scratch, the figures and the scripts that
reproduce both submitted CSV files.

---

## 1. What this is

580 epochs (9 min 56 s at 1 Hz) of raw u-blox ZED-F9P data were logged next to
Block X on 30 October 2026 and processed with a weighted least-squares SPP
solver: broadcast-ephemeris orbits, satellite clock, Klobuchar ionosphere,
Saastamoinen troposphere, one receiver clock per constellation, elevation and
C/N0 weighting, and residual-based fault exclusion. The same chain is then run
on the Block X 2025 example dataset (regression test) and on
UrbanNav-HK-Deep-Urban-1 (benchmark).

## 2. Results

Own data, 580 static epochs, 22.3056° N 114.1800° E (2D RMS about the mean of
the solution; the difference column is against the receiver's own
`UBX-NAV-HPPOSECEF` solution):

| Version | Change | Sats | HDOP | 2D scatter (m) | vs receiver (m) |
|---|---|---|---|---|---|
| v1 | GPS only, unweighted | 5.4 | 2.47 | 42.9 | 41.5 |
| v2 | + Galileo | 11.9 | 1.12 | 30.7 | 29.9 |
| v3 | + BeiDou | 18.7 | 0.82 | 24.1 | 18.6 |
| v4 | + elevation weighting | 18.7 | 0.82 | 23.0 | 16.9 |
| v5 | + C/N0 weighting | 18.7 | 0.82 | 20.5 | 7.7 |
| v6 | + outlier rejection (final) | 18.1 | 0.85 | 20.8 | **7.0** |
| v7 | + C/N0 mask 25 dB-Hz (diagnostic) | 16.3 | 1.04 | 21.3 | 7.0 |

Example dataset (186 epochs, Block X 2025): v1 2D/3D RMSE 25.6 m / 80.7 m on the
113 epochs it can solve, v6 16.1 m / 23.5 m on all 186 epochs.

UrbanNav benchmark (1534 epochs): availability 96.1 % (v1) → 99.8 % (v6), mean
satellite count 5.7 → 15.6, mean HDOP 2.79 → 1.23. The scoring reference
trajectory is withheld by the teaching team, so absolute RMSE and rank are
assigned on the leaderboard and are not quoted here.

## 3. Repository layout

```
.
├── gnss.py            RINEX 3 obs/nav readers, broadcast ephemeris, Klobuchar,
│                      Saastamoinen, ECEF/ENU, UBX NAV-HPPOSECEF reader
├── spp.py             weighted least-squares SPP, one clock per constellation,
│                      elevation / C/N0 weighting, RAIM-like fault exclusion
├── run_all.py         runs the 7 versions on own + example + benchmark data,
│                      writes out/stats.json and the two submission CSVs
├── plots.py           every figure of the report
├── make_report.py     builds the .docx report from out/stats.json
├── data/
│   ├── own/           raw UBX log + RTKCONV output (obs/nav), 30 Oct 2026
│   ├── example/       Block X 2025 example dataset + reference results
│   └── benchmark/     urbannav_deep1.obs / .nav
├── fig/               figures used in the report
├── out/               G18_owndata.csv, G18_benchmark.csv, stats.json, run log
└── report/            the submitted report (PDF + editable DOCX)
```

## 4. Reproduce

```bash
python -m pip install -r requirements.txt
python run_all.py       # ~3 min: statistics + both CSV files
python plots.py         # ~1 min: figures into fig/
python make_report.py   # rebuilds the .docx (needs out/stats.json)
```

Python 3.10+; developed and verified with Python 3.13 / NumPy 2.1 on Windows.
`run_all.py` is deterministic — rerunning it reproduces the numbers above, which
is how the report tables were generated.

## 5. Data

| Path | Source |
|---|---|
| `data/own/*` | our own field session, 30 Oct 2026, 09:00:27–09:10:23 GPST, u-blox ZED-F9P |
| `data/example/*` | course example dataset (Block X, 2025), from `weisongwen/AAE4203-S12627` |
| `data/benchmark/*` | UrbanNav-HK-Deep-Urban-1 inputs, same course repository |

The HK SatRef base-station file downloaded for our session covers the wrong hour
(17:00 GPST instead of 09:00) and is therefore not used; the report documents
this as an input check.

## 6. Notes

* BeiDou ephemerides are broadcast in BDT: `toe` needs `+1356` weeks and `+14 s`,
  `toc` needs **only** `+14 s` — adding the week offset to `toc` multiplies the
  `af1·Δt` term into a 12.8 ms clock error.
* RINEX 3 observation fields are 16 characters wide but the value occupies only
  the first 14; the last two are LLI and SSI.
* RINEX 3 navigation records are sometimes written without separating spaces and
  with sparse (blank) fields; `gnss.read_rinex_nav` assigns every number to its
  19-column slot instead of splitting on whitespace.
* The RTKCONV-generated navigation header carries no broadcast ionospheric
  coefficients, so default mid-latitude Klobuchar values are used for our own
  data. The benchmark navigation file does carry `GPSA`/`GPSB` and those are used.

## 7. AI use

A generative AI assistant was used for drafting the parsers and the solver, for
explanations of the BeiDou ICD, and for debugging; every output was verified on
the example dataset before the benchmark. Details are in Section 6 of the report
and the key prompts in Appendix A.
