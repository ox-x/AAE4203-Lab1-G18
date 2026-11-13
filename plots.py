"""
plots.py -- figures for the AAE4203 Lab 1 report (Group 18).
All panels are produced from the same code that generates the statistics in
out/stats.json, so figures and tables cannot drift apart.
"""

import json
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import gnss
import spp

plt.rcParams.update({
    'font.size': 8, 'axes.titlesize': 8.5, 'axes.labelsize': 8,
    'legend.fontsize': 7, 'xtick.labelsize': 7, 'ytick.labelsize': 7,
    'axes.grid': True, 'grid.alpha': 0.3, 'grid.linewidth': 0.5,
    'figure.dpi': 200, 'savefig.dpi': 300, 'savefig.bbox': 'tight',
    'axes.spines.top': False, 'axes.spines.right': False,
})

FIG = 'fig'
COL = {'G': '#1f77b4', 'E': '#2ca02c', 'C': '#d62728', 'R': '#ff7f0e'}
BASE = dict(weight='none', elev_mask=10.0, cn0_mask=None, reject=False,
            max_removal=3, reject_thres=3.5, max_iter=10)


def cfg(change, x0, **kw):
    c = dict(BASE); c.update(change); c['x0'] = x0; c.update(kw); return c


# ---------------------------------------------------------------- own data ---
def load_own():
    sess = [('data/own/COM5___4800_261030_085943.obs', 'data/own/COM5___4800_261030_085943.nav',
             'data/own/COM5___4800_261030_085943.ubx'),
            ('data/own/COM5___4800_261030_090654.obs', 'data/own/COM5___4800_261030_090654.nav',
             'data/own/COM5___4800_261030_090654.ubx')]
    epochs, ephs, ubx = [], {}, {}
    for o_f, n_f, u_f in sess:
        o = gnss.RinexObs(o_f)
        epochs += o.epochs
        for k, v in gnss.read_rinex_nav(n_f).items():
            ephs.setdefault(k, []).extend(v)
        ubx[o_f] = gnss.read_hpposecef(u_f)
    for k in ephs:
        ephs[k].sort(key=lambda e: e.toes)
    epochs.sort(key=lambda e: e['tow'])
    return o, epochs, ephs, ubx


def fig_sky(epochs, ephs, x0):
    ep = epochs[len(epochs) // 2]
    t = ep['week'] * 604800 + ep['tow']
    lat0, lon0, _ = gnss.ecef2geo(x0)
    fig = plt.figure(figsize=(3.4, 3.5))
    ax = fig.add_subplot(111, projection='polar')
    ax.set_theta_zero_location('N'); ax.set_theta_direction(-1)
    ax.set_rlim(0, 90)
    ax.set_rticks([30, 60])
    ax.set_yticklabels([])
    for r in (30, 60):
        ax.text(np.radians(8), r + 2, f'{90 - r:.0f}°', fontsize=6, ha='center')
    ax.set_xticks(np.radians([0, 45, 90, 135, 180, 225, 270, 315]))
    ax.set_xticklabels(['', '45°', '', '135°', '180°', '225°', '270°', '315°'])
    ax.tick_params(labelsize=6.5)
    ax.grid(alpha=0.4)
    pts = []
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
        pts.append((np.degrees(az), 90 - np.degrees(el), cn0 if not np.isnan(cn0) else 20, prn))
    sc = None
    for sysc in 'GEC':
        sel = [p for p in pts if p[3][0] == sysc]
        if not sel:
            continue
        a = np.radians([p[0] for p in sel]); r = [p[1] for p in sel]
        sc = ax.scatter(a, r, c=[p[2] for p in sel], vmin=15, vmax=50, s=22,
                        cmap='viridis', edgecolors='k', linewidths=0.3,
                        marker={'G': 'o', 'E': 's', 'C': '^', 'R': 'D'}[sysc],
                        label={'G': 'GPS', 'E': 'Galileo', 'C': 'BeiDou'}[sysc], zorder=3)
    ax.set_title('Tracked satellites, mid-epoch', pad=16, fontsize=8)
    ax.legend(loc='upper center', bbox_to_anchor=(0.42, 1.10), ncol=3,
              frameon=False, fontsize=6.5, handletextpad=0.2, columnspacing=0.8)
    cb = fig.colorbar(sc, ax=ax, pad=0.09, shrink=0.72)
    cb.set_label('C/N$_0$ (dB-Hz)', fontsize=7)
    cb.ax.tick_params(labelsize=6.5)
    fig.savefig(os.path.join(FIG, 'fig_sky.png'))
    plt.close(fig)


def fig_raw(epochs):
    tow = np.array([e['tow'] for e in epochs])
    tow = tow - tow[0]
    cnt = {s: [] for s in 'GEC'}
    for e in epochs:
        c = {s: 0 for s in 'GEC'}
        for prn, v in e['sat'].items():
            s = prn[0]
            if s in c and spp.get_code(v, s)[0] is not None:
                c[s] += 1
        for s in c:
            cnt[s].append(c[s])

    fig, axs = plt.subplots(1, 2, figsize=(6.9, 2.5))
    ax = axs[0]
    bottom = np.zeros(len(tow))
    for s, lab in [('C', 'BeiDou'), ('E', 'Galileo'), ('G', 'GPS')]:
        ax.fill_between(tow, bottom, bottom + np.array(cnt[s]), color=COL[s],
                        alpha=0.85, label=lab, linewidth=0)
        bottom += np.array(cnt[s])
    ax.set_xlabel('Time since 09:00:27 GPST (s)')
    ax.set_ylabel('Satellites with L1 code')
    ax.set_title('(a) Observations per constellation')
    ax.legend(loc='lower left', ncol=3, frameon=False, fontsize=7)
    ax.set_ylim(0, max(bottom) + 3)

    els, cn0s, syss = [], [], []
    # use the solution mean as the local origin
    ax = axs[1]
    mean = np.array(json.load(open('out/ref_own.json'))['mean_ecef'])
    lat0, lon0, _ = gnss.ecef2geo(mean)
    for e in epochs[::3]:
        t = e['week'] * 604800 + e['tow']
        for prn, v in e['sat'].items():
            snr = v.get(spp.SNR_OBS.get(prn[0], ''), np.nan)
            code, rho = spp.get_code(v, prn[0])
            if code is None or np.isnan(snr):
                continue
            ep = gnss.pick_eph(ephs_all, prn[0], prn, t)
            if ep is None:
                continue
            p, _ = gnss.sat_pos_clock(ep, t - rho / gnss.C_LIGHT)
            az, el = gnss.azel(p - mean, lat0, lon0)
            els.append(np.degrees(el)); cn0s.append(snr); syss.append(prn[0])
    for s, lab in [('G', 'GPS'), ('E', 'Galileo'), ('C', 'BeiDou')]:
        m = np.array(syss) == s
        ax.scatter(np.array(els)[m], np.array(cn0s)[m], s=3, alpha=0.35,
                   color=COL[s], label=lab, linewidths=0)
    ax.axhline(40, color='k', ls='--', lw=0.7)
    ax.axhline(30, color='k', ls=':', lw=0.7)
    ax.text(12, 40.8, '40 dB-Hz LOS', fontsize=6.5)
    ax.text(12, 30.8, '30 dB-Hz multipath / NLOS', fontsize=6.5)
    ax.set_xlabel('Elevation (deg)'); ax.set_ylabel('C/N$_0$ (dB-Hz)')
    ax.set_title('(b) C/N$_0$ versus elevation (every 3rd epoch)')
    ax.legend(loc='lower right', frameon=False)
    ax.set_ylim(0, 55)
    fig.savefig(os.path.join(FIG, 'fig_raw.png'))
    plt.close(fig)


def fig_enu(sols1, sols6):
    ok = [s for s in sols6 if s['ok']]
    mean = np.array([s['x'] for s in ok]).mean(axis=0)
    fig, axs = plt.subplots(3, 1, figsize=(6.5, 4.2), sharex=True)
    for lab, sols, c in [('GPS only (v1)', sols1, '#888888'),
                         ('GPS+Galileo+BeiDou, weighted (v6)', sols6, '#c0392b')]:
        ok = [s for s in sols if s['ok']]
        t = np.array([s['tow'] for s in ok]); t -= t[0]
        enu = np.array([gnss.enu_offset(s['x'], mean) for s in ok])
        for k, ax in enumerate(axs):
            ax.plot(t, enu[:, k], lw=0.6, color=c, label=lab if k == 0 else None)
            ax.set_ylabel(['East (m)', 'North (m)', 'Up (m)'][k])
    axs[0].legend(frameon=False, ncol=2, loc='lower right', fontsize=6.5)
    axs[2].set_xlabel('Time since 09:00:27 GPST (s)')
    for ax, lim in zip(axs, (110, 110, 130)):
        ax.axhline(0, color='k', lw=0.5)
        ax.set_ylim(-lim, lim)
    fig.suptitle('Static solution about its mean, Block X', fontsize=8.5, y=0.995)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'fig_enu.png'))
    plt.close(fig)


def fig_scatter(sols1, sols6):
    fig, axs = plt.subplots(1, 2, figsize=(6.3, 2.9), sharex=True, sharey=True)
    mean = np.array([s['x'] for s in sols6 if s['ok']]).mean(axis=0)
    for ax, sols, title in [(axs[0], sols1, '(a) GPS only, unweighted (v1)'),
                            (axs[1], sols6, '(b) multi-GNSS, weighted, RAIM (v6)')]:
        enu = np.array([gnss.enu_offset(s['x'], mean) for s in sols if s['ok']])
        ax.scatter(enu[:, 0], enu[:, 1], s=4, alpha=0.55, color='#2c3e50', linewidths=0)
        ax.plot(enu[:, 0].mean(), enu[:, 1].mean(), '+', color='#c0392b', ms=9)
        for r, ls in [(1, ':'), (2, '--')]:
            ax.add_patch(plt.Circle((enu[:, 0].mean(), enu[:, 1].mean()),
                                    r * enu[:, 0].std(), fill=False, ls=ls, lw=0.8,
                                    color='#c0392b'))
        ax.set_title(f'{title}\n1σ E = {enu[:,0].std():.1f} m, 1σ N = {enu[:,1].std():.1f} m')
        ax.set_xlabel('East (m)')
        ax.set_aspect('equal')
        ax.set_xlim(-90, 90); ax.set_ylim(-90, 90)
    axs[0].set_ylabel('North (m)')
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'fig_scatter.png'))
    plt.close(fig)


# ------------------------------------------------------------------- example --
def fig_example():
    ex = gnss.RinexObs('data/example/blockx_2025.obs')
    eph = gnss.read_rinex_nav('data/example/blockx_2025.nav')
    ref = np.array([[r[1], r[2], r[3]] for r in ref_receiver('data/example/NAV-HPPOSECEF.csv')])
    xr = ref.mean(axis=0)
    fig, axs = plt.subplots(1, 2, figsize=(6.6, 2.6))
    for tag, chg, c, lab in [
            ('v3', dict(systems=['G', 'E', 'C'], weight='none'), '#7f8c8d', 'GPS+GAL+BDS (v3)'),
            ('v6', dict(systems=['G', 'E', 'C'], weight='snr', reject=True), '#c0392b', 'v6 (final)')]:
        sols = spp.run(ex.epochs, eph, cfg(chg, ex.approx_pos))
        ok = [s for s in sols if s['ok']]
        t = np.array([s['tow'] for s in ok]); t -= t[0]
        enu = np.array([gnss.enu_offset(s['x'], xr) for s in ok])
        d2 = np.hypot(enu[:, 0], enu[:, 1])
        axs[0].plot(t, d2, lw=0.7, color=c, label=f'{lab}: 2D RMSE {np.sqrt((d2**2).mean()):.1f} m')
        axs[1].hist(d2, bins=np.arange(0, 60, 3), alpha=0.55, color=c, label=lab)
    axs[0].set_xlabel('Epoch time (s)'); axs[0].set_ylabel('2D error (m)')
    axs[0].set_title('(a) Example dataset: 2D error against the receiver solution')
    axs[0].legend(frameon=False)
    axs[1].set_xlabel('2D error (m)'); axs[1].set_ylabel('Epochs')
    axs[1].set_title('(b) Distribution of the 2D error')
    axs[1].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'fig_example.png'))
    plt.close(fig)


# ----------------------------------------------------------------- benchmark --
def fig_bench():
    bm = gnss.RinexObs('data/benchmark/urbannav_deep1.obs')
    eph = gnss.read_rinex_nav('data/benchmark/urbannav_deep1.nav')
    ion = gnss.read_iono_header('data/benchmark/urbannav_deep1.nav')
    x0 = gnss.geo2ecef(np.deg2rad(22.30), np.deg2rad(114.172), 20.0)
    kw = dict(ion_a=ion['GPSA'], ion_b=ion['GPSB']) if 'GPSA' in ion else {}
    s1 = spp.run(bm.epochs, eph, cfg(dict(systems=['G'], weight='none'), x0, **kw))
    s6 = spp.run(bm.epochs, eph, cfg(dict(systems=['G', 'E', 'C'], weight='snr', reject=True), x0, **kw))
    ok = [s for s in s6 if s['ok']]
    mean = np.array([s['x'] for s in ok]).mean(axis=0)
    lat0, lon0, _ = gnss.ecef2geo(mean)

    fig, axs = plt.subplots(1, 2, figsize=(6.9, 2.9))
    for sols, c, lab in [(s1, '#7f8c8d', 'GPS only (v1)'), (s6, '#c0392b', 'final (v6)')]:
        okk = [s for s in sols if s['ok']]
        enu = np.array([gnss.enu_offset(s['x'], mean) for s in okk])
        axs[0].plot(enu[:, 0], enu[:, 1], lw=0.6, color=c, label=lab, alpha=0.9)
        axs[1].scatter(enu[:, 0], enu[:, 1], s=2, color=c, alpha=0.5, label=lab, linewidths=0)
    axs[0].set_xlabel('East (m)'); axs[0].set_ylabel('North (m)')
    axs[0].set_title('(a) Estimated track, ENU about its mean')
    axs[0].legend(frameon=False); axs[0].set_aspect('equal')
    axs[1].set_xlabel('East (m)'); axs[1].set_title('(b) Sample-level scatter')
    axs[1].legend(frameon=False, markerscale=4); axs[1].set_aspect('equal')
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'fig_bench.png'))
    plt.close(fig)


def ref_receiver(path):
    out = []
    with open(path) as f:
        next(f)
        for line in f:
            p = line.strip().split(',')
            if len(p) < 6:
                continue
            out.append((float(p[2]) / 1000.0, float(p[3]) / 100.0,
                        float(p[4]) / 100.0, float(p[5]) / 100.0))
    return out


if __name__ == '__main__':
    os.makedirs(FIG, exist_ok=True)
    o, epochs, ephs_all, ubx = load_own()
    x0 = o.approx_pos
    ref = json.load(open('out/ref_own.json'))
    mean = np.array(ref['mean_ecef'])
    s1 = spp.run(epochs, ephs_all, cfg(dict(systems=['G'], weight='none'), x0))
    s6 = spp.run(epochs, ephs_all, cfg(dict(systems=['G', 'E', 'C'], weight='snr', reject=True), x0))

    fig_sky(epochs, ephs_all, mean)
    fig_raw(epochs)
    fig_enu(s1, s6)
    fig_scatter(s1, s6)
    fig_example()
    fig_bench()
    print('figures written to', FIG)
