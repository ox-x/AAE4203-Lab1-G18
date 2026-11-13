"""
spp.py -- weighted least-squares single point positioning for AAE4203 Lab 1.

The state vector is [x, y, z, b_G, b_C, b_E] where each b is one receiver
clock bias per constellation (metres).  Only the constellations actually
present contribute their clock column.
"""

import numpy as np

import gnss
from gnss import C_LIGHT

# default mid-latitude Klobuchar coefficients (broadcast values are not
# carried in the RTKCONV-generated navigation header)
IONO_ALPHA = [1.1176e-08, 1.4901e-08, -5.9605e-08, -1.1921e-07]
IONO_BETA = [8.8064e+04, 1.3107e+05, -1.6384e+05, -6.5536e+05]

CODE_OBS = {
    'G': ['C1C', 'C1W', 'C1X', 'C2W'],
    'E': ['C1X', 'C1C', 'C5Q'],
    'C': ['C2I', 'C1I', 'C7I'],
    'R': ['C1C', 'C1P'],
}
SNR_OBS = {'G': 'S1C', 'E': 'S1X', 'C': 'S2I', 'R': 'S1C'}
SYS_INDEX = {'G': 0, 'C': 1, 'E': 2}
# column of each constellation in the state vector follows the order of
# cfg['systems'], so that a subset of constellations stays contiguous
def sys_col(sysc, systems):
    return systems.index(sysc)


def get_code(obs_vals, sysc):
    for t in CODE_OBS.get(sysc, []):
        if t in obs_vals and obs_vals[t] > 1e6:
            return t, obs_vals[t]
    return None, None


def prepare(obs, ephs, x0, cfg):
    """Build per-satellite records for one epoch (geometry, corrections)."""
    t_rx = obs['week'] * 604800.0 + obs['tow']
    lat0, lon0, h0 = gnss.ecef2geo(x0[:3])
    rows = []

    for prn, vals in obs['sat'].items():
        sysc = prn[0]
        if sysc not in cfg['systems']:
            continue
        code, rho = get_code(vals, sysc)
        if code is None:
            continue
        eph = gnss.pick_eph(ephs, sysc, prn, t_rx)
        if eph is None:
            continue

        # signal transmission time: two iterations are enough at mm level
        tau = rho / C_LIGHT
        for _ in range(3):
            pos, dts = gnss.sat_pos_clock(eph, t_rx - tau)
            rng = np.linalg.norm(pos - x0[:3])
            tau = rng / C_LIGHT

        # earth rotation (Sagnac) during propagation
        th = gnss.OMEGA_E * tau
        R = np.array([[np.cos(th), np.sin(th), 0.0],
                      [-np.sin(th), np.cos(th), 0.0],
                      [0.0, 0.0, 1.0]])
        pos = R @ pos

        dxyz = pos - x0[:3]
        rng = np.linalg.norm(dxyz)
        az, el = gnss.azel(dxyz, lat0, lon0)

        iono = gnss.klobuchar(cfg.get('ion_a', IONO_ALPHA), cfg.get('ion_b', IONO_BETA),
                              lat0, lon0, az, el, obs['tow'])
        trop = gnss.tropo_saastamoinen(el, max(h0, 0.0))
        cn0 = vals.get(SNR_OBS.get(sysc, ''), np.nan)

        if el < np.deg2rad(cfg['elev_mask']):
            continue
        if cfg['cn0_mask'] is not None and not np.isnan(cn0) and cn0 < cfg['cn0_mask']:
            continue

        # corrected pseudorange (satellite clock + atmosphere removed)
        pr_corr = rho + C_LIGHT * dts - iono - trop

        rows.append(dict(prn=prn, sys=sysc, sat=pos, el=el, az=az, cn0=cn0,
                         rho=pr_corr, iono=iono, trop=trop, dts=dts, pr=rho))
    return rows, t_rx


def design(rows, x, systems):
    """Design matrix / misclosure for state x = [X,Y,Z,b...]."""
    n = len(rows)
    nsys = len(systems)
    H = np.zeros((n, 3 + nsys))
    y = np.zeros(n)
    for i, r in enumerate(rows):
        d = r['sat'] - x[:3]
        rng = np.linalg.norm(d)
        e = d / rng                      # receiver -> satellite unit vector
        H[i, 0:3] = -e
        H[i, 3 + systems.index(r['sys'])] = 1.0
        y[i] = r['rho'] - rng - x[3 + systems.index(r['sys'])]
    return H, y


def weights(rows, cfg):
    el = np.array([r['el'] for r in rows])
    if cfg['weight'] == 'none':
        return np.ones(len(rows))
    if cfg['weight'] == 'elev':
        return np.sin(el) ** 2
    if cfg['weight'] == 'snr':
        cn0 = np.array([r['cn0'] for r in rows])
        cn0 = np.where(np.isnan(cn0), 35.0, cn0)
        b = 0.6 * 10 ** ((45.0 - cn0) / 20.0)      # noise grows as C/N0 falls
        sig2 = 0.3 ** 2 + (b / np.sin(el)) ** 2
        return 1.0 / sig2
    raise ValueError(cfg['weight'])


def solve_epoch(obs, ephs, x0, cfg):
    systems = [s for s in 'GCE' if s in cfg['systems']]
    nsys = len(systems)
    rows, t_rx = prepare(obs, ephs, x0, cfg)
    res = dict(tow=obs['tow'], week=obs['week'], ok=False, n=0, nsat0=len(rows),
               removed=[], resid=np.array([]), pdop=np.nan, hdop=np.nan,
               vdop=np.nan, gdop=np.nan)
    if len(rows) < 3 + nsys:
        return None, res

    x = np.array([x0[0], x0[1], x0[2]] + [0.0] * nsys, dtype=float)
    for _ in range(cfg['max_iter']):
        H, y = design(rows, x, systems)
        w = weights(rows, cfg)
        W = np.diag(w)
        N = H.T @ W @ H
        if np.linalg.cond(N) > 1e12:
            return None, res
        dx = np.linalg.solve(N, H.T @ W @ y)
        x[:3] += dx[:3]
        x[3:] += dx[3:]
        if np.linalg.norm(dx[:3]) < 1e-4:
            break

    # ---- residual based outlier rejection (RAIM-like) --------------------
    if cfg['reject']:
        for _ in range(cfg['max_removal']):
            H, y = design(rows, x, systems)
            w = weights(rows, cfg)
            W = np.diag(w)
            v = y - H @ np.r_[np.zeros(3), np.zeros(nsys)]   # placeholder
            # recompute residuals at the converged state
            v = np.zeros(len(rows))
            for i, r in enumerate(rows):
                rng = np.linalg.norm(r['sat'] - x[:3])
                v[i] = r['rho'] - rng - x[3 + systems.index(r['sys'])]
            sigma = 1.0 / np.sqrt(np.maximum(w, 1e-12))
            if len(rows) <= 3 + nsys + 1:
                break
            norm = np.abs(v) / sigma
            k = int(np.argmax(norm))
            if norm[k] < cfg['reject_thres']:
                break
            res['removed'].append(rows[k]['prn'])
            rows.pop(k)
            # re-solve with the reduced set
            for _ in range(cfg['max_iter']):
                H, y = design(rows, x, systems)
                w = weights(rows, cfg)
                W = np.diag(w)
                N = H.T @ W @ H
                dx = np.linalg.solve(N, H.T @ W @ y)
                x[:3] += dx[:3]
                x[3:] += dx[3:]
                if np.linalg.norm(dx[:3]) < 1e-4:
                    break

    # ---- final residuals and DOP ----------------------------------------
    H, y = design(rows, x, systems)
    w = weights(rows, cfg)
    resid = []
    for i, r in enumerate(rows):
        rng = np.linalg.norm(r['sat'] - x[:3])
        resid.append(r['rho'] - rng - x[3 + systems.index(r['sys'])])
    resid = np.array(resid)

    Q = np.linalg.inv(H.T @ H)
    R = gnss.rot_ecef2enu(*gnss.ecef2geo(x[:3])[:2])
    Qenu = np.zeros((3, 3))
    Qenu = R @ Q[0:3, 0:3] @ R.T

    res.update(ok=True, x=x, n=len(rows), resid=resid,
               gdop=np.sqrt(np.trace(Q)), hdop=np.sqrt(Qenu[0, 0] + Qenu[1, 1]),
               vdop=np.sqrt(Qenu[2, 2]), rows_used=rows, ncyc=len(rows))
    return x, res


def run(obs_list, ephs, cfg):
    """Process a list of epochs; returns list of result dicts."""
    x0 = np.r_[cfg['x0'], np.zeros(3)]
    out = []
    last = None
    for obs in obs_list:
        if last is not None and np.all(np.isfinite(last)):
            x0 = np.r_[last[:3], np.zeros(3)]
        x, res = solve_epoch(obs, ephs, x0, cfg)
        if x is not None:
            last = x
            res['x'] = x[:3]
        out.append(res)
    return out
