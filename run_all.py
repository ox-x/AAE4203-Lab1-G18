"""
run_all.py -- AAE4203 Lab 1, Group 18.

Runs the complete chain:
  1. own field data (two u-center logs, Block X, 30 Oct 2026)
     - raw-data statistics and ablation of the SPP variants
     - validation against the receiver solution (UBX NAV-HPPOSECEF)
     - submission file G18_owndata.csv
  2. example dataset (Block X 2025, 186 epochs) as a regression test
  3. UrbanNav benchmark (urbannav_deep1, 1534 epochs) and G18_benchmark.csv
All numbers printed here are the ones quoted in the report.
"""

import json
import os
import numpy as np

import gnss
import spp

OUT = 'out'
FIG = 'fig'
os.makedirs(OUT, exist_ok=True)
os.makedirs(FIG, exist_ok=True)

# ----------------------------------------------------------------------------
# variant definitions (one change at a time, in this order)
# ----------------------------------------------------------------------------
BASE = dict(weight='none', elev_mask=10.0, cn0_mask=None, reject=False,
            max_removal=3, reject_thres=3.5, max_iter=10)

VARIANTS = [
    ('v1', 'GPS only, unweighted',        dict(systems=['G'], weight='none')),
    ('v2', '+ Galileo',                   dict(systems=['G', 'E'], weight='none')),
    ('v3', '+ BeiDou',                    dict(systems=['G', 'E', 'C'], weight='none')),
    ('v4', '+ elevation weighting',       dict(systems=['G', 'E', 'C'], weight='elev')),
    ('v5', '+ C/N0 weighting',            dict(systems=['G', 'E', 'C'], weight='snr')),
    ('v6', '+ residual outlier rejection', dict(systems=['G', 'E', 'C'], weight='snr', reject=True)),
    ('v7', '+ C/N0 mask 25 dB-Hz',        dict(systems=['G', 'E', 'C'], weight='snr', reject=True, cn0_mask=25.0)),
]


def cfg_for(change, x0):
    c = dict(BASE)
    c.update(change)
    c['x0'] = x0
    return c


# ----------------------------------------------------------------------------
# helper: statistics of a static solution
# ----------------------------------------------------------------------------
def static_stats(sols):
    xs = np.array([s['x'] for s in sols if s['ok']])
    mean = xs.mean(axis=0)
    enu = np.array([gnss.enu_offset(x, mean) for x in xs])
    return dict(n=len(xs), mean_ecef=mean.tolist(),
                mean=enu.mean(0).tolist(), std=enu.std(0, ddof=1).tolist(),
                rms2d=float(np.sqrt((enu[:, 0] ** 2 + enu[:, 1] ** 2).mean())),
                r95=float(np.percentile(np.hypot(enu[:, 0], enu[:, 1]), 95)),
                max2d=float(np.hypot(enu[:, 0], enu[:, 1]).max()),
                enu=enu)


# ----------------------------------------------------------------------------
# own data
# ----------------------------------------------------------------------------
def load_own():
    sess = [('data/own/COM5___4800_261030_085943.obs', 'data/own/COM5___4800_261030_085943.nav',
             'data/own/COM5___4800_261030_085943.ubx'),
            ('data/own/COM5___4800_261030_090654.obs', 'data/own/COM5___4800_261030_090654.nav',
             'data/own/COM5___4800_261030_090654.ubx')]
    epochs, ephs, ubx = [], {}, {}
    for obs_f, nav_f, ubx_f in sess:
        o = gnss.RinexObs(obs_f)
        epochs += o.epochs
        for k, v in gnss.read_rinex_nav(nav_f).items():
            ephs.setdefault(k, []).extend(v)
        ubx[obs_f] = gnss.read_hpposecef(ubx_f)
    for k in ephs:
        ephs[k].sort(key=lambda e: e.toes)
    epochs.sort(key=lambda e: e['tow'])
    return o, epochs, ephs, ubx


def receiver_track(ubx):
    """Receiver NAV-HPPOSECEF as (tow, ecef) tuples for both logs."""
    out = []
    for f, rec in ubx.items():
        for itow, x, y, z, hacc in rec:
            out.append((itow / 1000.0, np.array([x, y, z]), hacc))
    out.sort(key=lambda r: r[0])
    return out


def compare_to_receiver(sols, rec):
    tow = np.array([r[0] for r in rec])
    rows = []
    for s in sols:
        if not s['ok']:
            continue
        k = np.argmin(np.abs(tow - s['tow']))
        if abs(tow[k] - s['tow']) > 0.2:
            continue
        rows.append((s['tow'], s['x'], rec[k][1]))
    d = np.array([gnss.enu_offset(a, b) for _, a, b in rows])
    return dict(n=len(rows), mean=d.mean(0).tolist(), std=d.std(0, ddof=1).tolist(),
                rms2d=float(np.sqrt((d[:, 0] ** 2 + d[:, 1] ** 2).mean())),
                d=d, tow=[r[0] for r in rows])


def error_vs_reference(sols, ref_pos):
    """2D/3D error against a single reference position (static dataset)."""
    e = np.array([gnss.enu_offset(s['x'], ref_pos) for s in sols if s['ok']])
    d3 = np.array([np.linalg.norm(s['x'] - ref_pos) for s in sols if s['ok']])
    d2 = np.hypot(e[:, 0], e[:, 1])
    return dict(n=len(e), mean2d=float(d2.mean()), rms2d=float(np.sqrt((d2 ** 2).mean())),
                mean3d=float(d3.mean()), rms3d=float(np.sqrt((d3 ** 2).mean())),
                p95_2d=float(np.percentile(d2, 95)), max2d=float(d2.max()),
                mean_enu=e.mean(0).tolist(), std_enu=e.std(0, ddof=1).tolist(), enu=e)


def main():
    print('=' * 78)
    print('OWN DATA')
    print('=' * 78)
    o, epochs, ephs, ubx = load_own()
    rec = receiver_track(ubx)
    x0 = o.approx_pos
    print(f'epochs {len(epochs)}  {epochs[0]["tow"]:.0f}-{epochs[-1]["tow"]:.0f} s '
          f'(week {epochs[0]["week"]})  duration {epochs[-1]["tow"]-epochs[0]["tow"]:.0f} s')
    print(f'receiver solutions {len(rec)}')

    results = {}
    for tag, desc, change in VARIANTS:
        sols = spp.run(epochs, ephs, cfg_for(change, x0))
        st = static_stats(sols)
        rc = compare_to_receiver(sols, rec)
        ok = [s for s in sols if s['ok']]
        results[tag] = dict(
            desc=desc, change=change,
            solved=st['n'], total=len(epochs),
            nsat=float(np.mean([s['n'] for s in ok])),
            hdop=float(np.mean([s['hdop'] for s in ok])),
            vdop=float(np.mean([s['vdop'] for s in ok])),
            resid=float(np.sqrt(np.mean([np.mean(s['resid'] ** 2) for s in ok]))),
            mean_ecef=st['mean_ecef'],
            std=st['std'], rms2d=st['rms2d'], r95=st['r95'], max2d=st['max2d'],
            mean=st['mean'], rec=dict(n=rc['n'], mean=rc['mean'], std=rc['std'], rms2d=rc['rms2d']),
            _enu=st['enu'], _sol=sols, _rec=rc)
        print(f'{tag} {desc:28s} n={st["n"]:3d} sats={results[tag]["nsat"]:5.1f} '
              f'HDOP={results[tag]["hdop"]:4.2f} resid={results[tag]["resid"]:5.2f} '
              f'scatter E/N/U={st["std"][0]:6.1f}/{st["std"][1]:6.1f}/{st["std"][2]:6.1f} '
              f'2D={st["rms2d"]:6.1f} | vs RX dE/dN/dU='
              f'{rc["mean"][0]:6.1f}/{rc["mean"][1]:6.1f}/{rc["mean"][2]:6.1f} '
              f'2D={rc["rms2d"]:6.1f} (n={rc["n"]})')

    best = results['v6']
    with open(os.path.join(OUT, 'ref_own.json'), 'w') as f:
        json.dump(dict(mean_ecef=best['mean_ecef']), f)
    # submission file
    with open(os.path.join(OUT, 'G18_owndata.csv'), 'w') as f:
        f.write('gps_week,gps_tow_s,x_ecef_m,y_ecef_m,z_ecef_m\n')
        for s in best['_sol']:
            if s['ok']:
                f.write(f'{s["week"]},{s["tow"]:.1f},{s["x"][0]:.3f},{s["x"][1]:.3f},{s["x"][2]:.3f}\n')
    print('wrote out/G18_owndata.csv')

    # raw-data statistics -----------------------------------------------------
    raw = raw_stats(epochs, ephs, best['_sol'])
    print('raw: epochs %d  mean sats %s  median C/N0 %s  low-C/N0 frac %.3f' % (
        raw['n_epochs'], {k: round(v, 2) for k, v in raw['mean_sat'].items()},
        raw['cn0_median'], raw['low_cn0_frac']))

    # ------------------------------------------------------------------
    print()
    print('=' * 78)
    print('EXAMPLE DATASET (regression test, 186 epochs, 2025)')
    print('=' * 78)
    ex = gnss.RinexObs('data/example/blockx_2025.obs')
    ex_eph = gnss.read_rinex_nav('data/example/blockx_2025.nav')
    ex_rec = np.array([[r[1], r[2], r[3]] for r in ref_receiver('data/example/NAV-HPPOSECEF.csv')])
    ex_ref = ex_rec.mean(axis=0)
    print(f'example epochs {len(ex.epochs)}  reference mean ECEF {np.round(ex_ref,2)}')
    ex_res = {}
    for tag, desc, change in VARIANTS:
        sols = spp.run(ex.epochs, ex_eph, cfg_for(change, ex.approx_pos))
        ev = error_vs_reference(sols, ex_ref)
        st = static_stats(sols)
        ex_res[tag] = dict(desc=desc, **{k: ev[k] for k in
                                         ('n', 'mean2d', 'rms2d', 'mean3d', 'rms3d', 'p95_2d', 'max2d',
                                          'mean_enu', 'std_enu')},
                           scatter=st['rms2d'], _enu=ev['enu'])
        print(f'{tag} {desc:28s} n={ev["n"]:3d} 2D RMSE={ev["rms2d"]:6.2f} 3D RMSE={ev["rms3d"]:6.2f} '
              f'P95 2D={ev["p95_2d"]:6.2f} biasE/N/U='
              f'{ev["mean_enu"][0]:6.1f}/{ev["mean_enu"][1]:6.1f}/{ev["mean_enu"][2]:6.1f}')

    # ------------------------------------------------------------------
    print()
    print('=' * 78)
    print('BENCHMARK (UrbanNav-HK-Deep-Urban-1, 1534 epochs)')
    print('=' * 78)
    bm = gnss.RinexObs('data/benchmark/urbannav_deep1.obs')
    bm_eph = gnss.read_rinex_nav('data/benchmark/urbannav_deep1.nav')
    bm_x0 = gnss.geo2ecef(np.deg2rad(22.3000), np.deg2rad(114.1720), 20.0)
    print(f'benchmark epochs {len(bm.epochs)}  week {bm.epochs[0]["week"]}  '
          f'tow {bm.epochs[0]["tow"]:.0f}-{bm.epochs[-1]["tow"]:.0f}')
    ion = gnss.read_iono_header('data/benchmark/urbannav_deep1.nav')
    bm_res = {}
    prev = None
    for tag, desc, change in VARIANTS:
        c = cfg_for(change, bm_x0)
        if 'GPSA' in ion:
            c['ion_a'], c['ion_b'] = ion['GPSA'], ion['GPSB']
        sols = spp.run(bm.epochs, bm_eph, c)
        ok = [s for s in sols if s['ok']]
        xs = np.array([s['x'] for s in ok])
        bm_res[tag] = dict(desc=desc, solved=len(ok), total=len(sols),
                           avail=100.0 * len(ok) / len(sols),
                           nsat=float(np.mean([s['n'] for s in ok])),
                           hdop=float(np.mean([s['hdop'] for s in ok])),
                           resid=float(np.sqrt(np.mean([np.mean(s['resid'] ** 2) for s in ok]))),
                           _sol=sols)
        print(f'{tag} {desc:28s} avail={bm_res[tag]["avail"]:5.1f}% ({len(ok)}/{len(sols)}) '
              f'sats={bm_res[tag]["nsat"]:5.1f} HDOP={bm_res[tag]["hdop"]:5.2f} '
              f'resid={bm_res[tag]["resid"]:6.2f}')
        if tag == 'v6':
            with open(os.path.join(OUT, 'G18_benchmark.csv'), 'w') as f:
                f.write('gps_week,gps_tow_s,x_ecef_m,y_ecef_m,z_ecef_m\n')
                for s in ok:
                    f.write(f'{s["week"]},{s["tow"]:.1f},{s["x"][0]:.3f},'
                            f'{s["x"][1]:.3f},{s["x"][2]:.3f}\n')
            print('wrote out/G18_benchmark.csv')

    # consistency between variants on the benchmark
    ref = {(s['week'], s['tow']): s['x'] for s in bm_res['v6']['_sol'] if s['ok']}
    for tag in bm_res:
        d = []
        xs = []
        for s in bm_res[tag]['_sol']:
            if not s['ok']:
                continue
            xs.append(s['x'])
            k = (s['week'], s['tow'])
            if k in ref:
                d.append(np.linalg.norm(gnss.enu_offset(s['x'], ref[k])[:2]))
        bm_res[tag]['dev_v6'] = float(np.sqrt(np.mean(np.square(d)))) if d else np.nan
        bm_res[tag]['dev_n'] = len(d)
        # kinematic jitter: epoch-to-epoch 2D step (proxy for noise)
        A = np.array(xs)
        if len(A) > 2:
            steps = np.array([np.linalg.norm(gnss.enu_offset(A[i + 1], A[i])[:2]) for i in range(len(A) - 1)])
            bm_res[tag]['jitter'] = float(np.median(steps))
        else:
            bm_res[tag]['jitter'] = np.nan
        print(f'    {tag}: RMS 2D deviation from v6 = {bm_res[tag]["dev_v6"]:7.1f} m '
              f'(n={bm_res[tag]["dev_n"]}), median epoch-to-epoch step = {bm_res[tag]["jitter"]:5.2f} m')

    # ---------------------------------------------------------------- save ---
    def clean(d):
        return {k: v for k, v in d.items() if not k.startswith('_')}

    blob = dict(own={k: clean(v) for k, v in results.items()}, raw=clean(raw),
                example={k: clean(v) for k, v in ex_res.items()},
                benchmark={k: clean(v) for k, v in bm_res.items()},
                own_ok=results['v6']['_sol'][0]['week'] if results['v6']['_sol'] else None)
    with open(os.path.join(OUT, 'stats.json'), 'w') as f:
        json.dump(blob, f, indent=1, default=float)

    # arrays for plotting
    np.savez(os.path.join(OUT, 'arrays.npz'),
             own_enu_v6=results['v6']['_enu'],
             own_sol_v6=np.array([s['x'] for s in results['v6']['_sol'] if s['ok']]),
             own_tow_v6=np.array([s['tow'] for s in results['v6']['_sol'] if s['ok']]),
             own_enu_v1=results['v1']['_enu'],
             own_rec_d=results['v6']['_rec']['d'],
             own_rec_tow=np.array(results['v6']['_rec']['tow']),
             ex_enu_v6=ex_res['v6']['_enu'], ex_ref=ex_ref)
    print('\nsaved out/stats.json')


def ref_receiver(path):
    """read NAV-HPPOSECEF.csv (cm + 0.1 mm) -> list of (tow, x, y, z) in m."""
    out = []
    with open(path) as f:
        next(f)
        for line in f:
            p = line.strip().split(',')
            if len(p) < 6:
                continue
            itow = float(p[2])
            out.append((itow / 1000.0, float(p[3]) / 100.0, float(p[4]) / 100.0, float(p[5]) / 100.0))
    return out


def raw_stats(epochs, ephs, sols):
    """Satellite visibility, C/N0, elevation and DOP statistics."""
    x0 = None
    for s in sols:
        if s['ok']:
            x0 = s['x']
            break
    lat0, lon0, h0 = gnss.ecef2geo(x0)
    per_epoch = {'G': [], 'E': [], 'C': [], 'R': []}
    cn0_all, el_all, az_all, cn0_sys = [], [], [], {'G': [], 'E': [], 'C': [], 'R': []}
    el_used, cn0_used = [], []
    for ep in epochs:
        cnt = {'G': 0, 'E': 0, 'C': 0, 'R': 0}
        for prn, v in ep['sat'].items():
            s = prn[0]
            if s not in cnt:
                continue
            snr = v.get(spp.SNR_OBS.get(s, ''), np.nan)
            if not np.isnan(snr) and snr > 0:
                cnt[s] += 1
                cn0_all.append(snr)
                cn0_sys[s].append(snr)
        for s in cnt:
            per_epoch[s].append(cnt[s])
    # elevation from the first epoch
    ep = epochs[len(epochs) // 2]
    t = ep['week'] * 604800 + ep['tow']
    sky = []
    for prn, v in ep['sat'].items():
        code, rho = spp.get_code(v, prn[0])
        if code is None:
            continue
        e = gnss.pick_eph(ephs, prn[0], prn, t)
        if e is None:
            continue
        p, _ = gnss.sat_pos_clock(e, t - rho / gnss.C_LIGHT)
        az, el = gnss.azel(p - x0, lat0, lon0)
        cn0 = v.get(spp.SNR_OBS.get(prn[0], ''), np.nan)
        sky.append((prn, np.degrees(az), np.degrees(el), cn0))
        if not np.isnan(cn0):
            el_all.append(np.degrees(el))
    d = dict(
        n_epochs=len(epochs),
        mean_sat={s: float(np.mean(v)) for s, v in per_epoch.items()},
        max_sat={s: int(np.max(v)) for s, v in per_epoch.items()},
        cn0_median={s: float(np.median(v)) for s, v in cn0_sys.items() if v},
        cn0_mean=float(np.mean(cn0_all)), cn0_p10=float(np.percentile(cn0_all, 10)),
        cn0_p90=float(np.percentile(cn0_all, 90)),
        low_cn0_frac=float(np.mean(np.array(cn0_all) < 30.0)),
        sky=sky, per_epoch=per_epoch, tow=[e['tow'] for e in epochs])
    return d


if __name__ == '__main__':
    main()
