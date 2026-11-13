# -*- coding: utf-8 -*-
"""Build the AAE4203 Lab 1 report (Group 18) as a .docx."""

import json

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = 'report/AAE4203_Lab1_GNSS_Report_G18.docx'
FIG = 'fig/'

st = json.load(open('out/stats.json'))
own, ex, bm, raw = st['own'], st['example'], st['benchmark'], st['raw']

BODY = 10.0
CAP = 8.5


def set_cell_bg(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hexcolor)
    tcPr.append(shd)


def setup(doc):
    s = doc.sections[0]
    s.page_height, s.page_width = Cm(29.7), Cm(21.0)
    s.top_margin, s.bottom_margin = Cm(2.0), Cm(2.0)
    s.left_margin, s.right_margin = Cm(2.0), Cm(2.0)
    n = doc.styles['Normal']
    n.font.name = 'Times New Roman'
    n.font.size = Pt(BODY)
    n._element.rPr.rFonts.set(qn('w:eastAsia'), 'SimSun')
    p = n.paragraph_format
    p.space_before, p.space_after = Pt(0), Pt(4)
    p.line_spacing = 1.06


def H(doc, text, level=1):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10 if level == 1 else 7)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(11.5 if level == 1 else 10)
    r.font.color.rgb = RGBColor(0x1F, 0x3B, 0x57)
    return p


def P(doc, text, align=None, size=BODY, italic=False, space_after=4, first_indent=0.0):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.alignment = align if align is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
    if first_indent:
        p.paragraph_format.first_line_indent = Cm(first_indent)
    parts = text.split('**')
    for i, seg in enumerate(parts):
        if not seg:
            continue
        r = p.add_run(seg)
        r.font.size = Pt(size)
        r.italic = italic
        r.bold = (i % 2 == 1)
    return p


def EQ(doc, text, num):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.font.name = 'Cambria Math'
    r.font.size = Pt(10.5)
    tabs = p.paragraph_format.tab_stops
    tabs.add_tab_stop(Cm(16.6), 2)
    p.add_run('\t(%s)' % num).font.size = Pt(10)
    return p


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(text)
    r.font.size = Pt(CAP)
    return p


def picture(doc, path, width, cap):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(0)
    p.add_run().add_picture(path, width=Cm(width))
    caption(doc, cap)


def table(doc, header, rows, widths, cap, fontsize=8.2, cap_above=True):
    if cap_above:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(cap)
        r.font.size = Pt(CAP)
    t = doc.add_table(rows=1, cols=len(header))
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, h in enumerate(header):
        hdr[i].text = ''
        pp = hdr[i].paragraphs[0]
        pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pp.paragraph_format.space_after = Pt(1)
        rr = pp.add_run(h)
        rr.bold = True
        rr.font.size = Pt(fontsize)
        set_cell_bg(hdr[i], 'EAF0F6')
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ''
            pp = cells[i].paragraphs[0]
            pp.alignment = WD_ALIGN_PARAGRAPH.CENTER if i else WD_ALIGN_PARAGRAPH.LEFT
            pp.paragraph_format.space_after = Pt(1)
            rr = pp.add_run(str(v))
            rr.font.size = Pt(fontsize)
    for r in t.rows:
        for i, w in enumerate(widths):
            r.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def listing(doc, lines, cap, fontsize=7.4):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(cap)
    r.font.size = Pt(CAP)
    t = doc.add_table(rows=1, cols=1)
    t.style = 'Table Grid'
    c = t.rows[0].cells[0]
    set_cell_bg(c, 'F7F7F4')
    c.text = ''
    for i, ln in enumerate(lines):
        pp = c.paragraphs[0] if i == 0 else c.add_paragraph()
        pp.paragraph_format.space_after = Pt(0)
        pp.paragraph_format.space_before = Pt(0)
        pp.paragraph_format.line_spacing = 1.0
        rr = pp.add_run(ln if ln else ' ')
        rr.font.name = 'Consolas'
        rr.font.size = Pt(fontsize)
        rpr = rr._element.get_or_add_rPr()
        rf = rpr.find(qn('w:rFonts'))
        if rf is None:
            rf = OxmlElement('w:rFonts')
            rpr.append(rf)
        for a in ('w:ascii', 'w:hAnsi', 'w:cs'):
            rf.set(qn(a), 'Consolas')
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def footer_page_numbers(doc):
    sec = doc.sections[0]
    p = sec.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    fld = OxmlElement('w:fldSimple')
    fld.set(qn('w:instr'), 'PAGE')
    run._r.addnext(fld)
    for r in p.runs:
        r.font.size = Pt(8)


# ============================================================== document ====
doc = Document()
setup(doc)
footer_page_numbers(doc)

# ---------------------------------------------------------------- cover -----
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(40)
r = p.add_run('AAE4203 — Guidance and Navigation')
r.font.size = Pt(13)
r.font.color.rgb = RGBColor(0x44, 0x44, 0x44)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(26)
r = p.add_run('GNSS Lab Report')
r.bold = True
r.font.size = Pt(26)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('Lab 1: GNSS Positioning')
r.font.size = Pt(15)
r.font.color.rgb = RGBColor(0x1F, 0x3B, 0x57)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(10)
r = p.add_run('Single point positioning from u-blox raw measurements near Block X,\n'
              'validated against independent solutions and benchmarked on UrbanNav')
r.font.size = Pt(10.5)
r.italic = True


def cover_row(label, value, bold=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(1)
    r = p.add_run(label)
    r.font.size = Pt(10.5)
    r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    r2 = p.add_run(value)
    r2.font.size = Pt(10.5)
    r2.bold = bold


p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(34)

cover_row('Group:  ', 'Group 18 (receiver kit K08)', True)
cover_row('Members:  ', 'CHIU Sung Lim (23078005D); RAMOS CRUZ Axel Daniel (26009386X);')
cover_row('', 'YU Mengzhi (24102853D); ZHANG Borui (24102982D)')
cover_row('Instructor:  ', 'Prof. Weisong WEN')
cover_row('Department:  ', 'Department of Aeronautical and Aviation Engineering')
cover_row('School:  ', 'The Hong Kong Polytechnic University')
cover_row('Field session:  ', '30 October 2026, 17:00–17:10 HKT, next to Block X')
cover_row('Date:  ', '12 November 2026')

H(doc, 'Abstract')
P(doc, 'On 30 October 2026 our group logged 580 epochs (9 min 56 s at 1 Hz) of raw u-blox ZED-F9P '
       'measurements next to Block X, a semi-open site surrounded by 30–60 m buildings. The logs were '
       'converted with RTKCONV and processed with a single point positioning (SPP) solver written from '
       'scratch in Python: broadcast-ephemeris orbits, Klobuchar and Saastamoinen corrections, weighted '
       'least squares with one receiver clock per constellation and residual-based fault exclusion. On our '
       'own data the GPS-only baseline scatters 42.9 m (2D RMS about its mean); adding Galileo, BeiDou, '
       'elevation and C/N\u2080 weighting and outlier rejection reduces the scatter to 20.8 m and the 2D '
       'difference from the receiver solution from 41.5 m to 7.0 m. The same chain solves all 186 epochs of '
       'the example dataset with a 2D RMSE of about 16 m (23.5 m in 3D), against 25.6 m for the GPS-only '
       'variant on the 113 epochs it can solve — the same order as the 37.9 m reported for the reference '
       'implementation. On the UrbanNav benchmark the final '
       'version solves 1531 of 1534 epochs (99.8 %) with 15.6 satellites and a mean HDOP of 1.25, against '
       '96.1 % and 5.7 satellites for the GPS-only baseline; the official RMSE and rank are assigned on the '
       'leaderboard, which is why the ablation is quantified here by availability and internal consistency.')

p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(6)
r = p.add_run('Keywords: ')
r.bold = True
r.font.size = Pt(9.5)
r = p.add_run('GNSS; single point positioning; weighted least squares; urban positioning; u-blox ZED-F9P; '
              'UrbanNav')
r.font.size = Pt(9.5)

doc.add_page_break()

# ------------------------------------------------------- 1 data collection --
H(doc, '1  Data Collection')
P(doc, 'The field session took place on Friday 30 October 2026 in the semi-open area between Block X and the '
       'Jockey Club Innovation Tower on the PolyU campus (22.30560° N, 114.18005° E, ellipsoidal height '
       '≈ 19 m). The site is a paved courtyard opening to the north-west; the road viaduct and the '
       '30–60 m buildings of Block X and the Innovation Tower close the horizon to the north, east and '
       'south, which is the urban canyon the laboratory is designed around.')
P(doc, 'Each group used a u-blox ZED-F9P receiver with a multi-band ANN-MB antenna mounted on a ground '
       'plane, connected to a laptop, and u-center for configuration and logging. The ZED-F9P tracks GPS, '
       'GLONASS, Galileo and BeiDou on two frequencies; UBX-RXM-RAWX was enabled so that pseudorange, '
       'carrier phase, Doppler and C/N\u2080 were recorded for every tracked signal, together with the '
       'navigation messages and the receiver’s own solution (UBX-NAV-HPPOSECEF, retrieved afterwards with '
       'pyubx2). The antenna was placed on a stable surface at the marked location, away from the operator '
       'and the laptop, and was not touched during the recording.')
P(doc, 'The receiver clock was set to GPS time, so the logs run from 09:00:27 to 09:10:23 GPST '
       '(17:00:27–17:10:23 HKT). Recording was stopped and restarted once after 6 min 36 s, which produces '
       'an 18 s gap between 09:07:03 and 09:07:21 GPST. The mean positions of the two sub-solutions differ '
       'by 11.7 m East and 2.9 m North, but that is the slow multipath drift of Section 4 rather than a '
       'change of antenna position: over the same interval the solution wanders by the same amount '
       '(Fig. 4). The two logs contain 397 and 183 epochs, '
       '580 in total, at 1 Hz. Sky conditions were dry; no rain fade is visible in the C/N\u2080 record of '
       'Section 2. Table 1 summarises the set-up and Fig. 1 places the estimated positions on the site.')

table(doc,
      ['Field', 'Value'],
      [['Location', 'Block X, PolyU, Hong Kong (22.30560° N, 114.18005° E)'],
       ['Date and time', '30 Oct 2026, 09:00:27–09:10:23 GPST (17:00–17:10 HKT)'],
       ['Duration', '596 s, 580 epochs at 1 Hz, two logs (397 + 183)'],
       ['Receiver / antenna', 'u-blox ZED-F9P, ANN-MB multi-band, kit K08'],
       ['Software', 'u-center (logging), RTKCONV, Python 3.13 + NumPy'],
       ['Signals logged', 'GPS L1/L2, GLONASS L1/L2, Galileo E1/E7, BeiDou B1I/B2I'],
       ['Environment', 'Urban canyon: 30–60 m buildings S/E, viaduct N, trees W'],
       ['Weather', 'Dry, no precipitation, antenna static']],
      [3.6, 12.9],
      'Table 1. Data collection summary.')

picture(doc, FIG + 'fig_site.jpg', 15.0,
        'Figure 1. Estimated positions of the second log (yellow/red dots) plotted on the satellite image of '
        'the site; Block X and the Jockey Club Innovation Tower appear to the south of the antenna position.')

# -------------------------------------------------- 2 raw data analysis ----
H(doc, '2  Raw Data Analysis')
P(doc, 'The RINEX observation file contains 26.6 satellites with a usable L1/E1/B1I code measurement per '
       'epoch: 7.1 GPS, 7.6 Galileo, 6.8 BeiDou and 5.1 GLONASS on average, with peaks of 10, 10, 7 and 9 '
       '(Fig. 2a). It fluctuates between 15 and 26 satellites, and the two deepest dips, at about 150 s and '
       '540 s after the start, coincide with the largest position excursions in Fig. 4 — a loss of '
       'satellites that the geometry cannot absorb. GLONASS was logged but is not used in the solution: its FDMA '
       'signals need a per-satellite inter-frequency bias and a separate ephemeris evaluation, and the '
       'remaining three constellations already provide 19 satellites.')
P(doc, 'The C/N\u2080 record (Fig. 2b) is the clearest indicator of the environment. The median is '
       '33 dB-Hz for GPS and Galileo, 32 dB-Hz for GLONASS and 36 dB-Hz for BeiDou, and 31.5 % of all '
       'measurements fall below 30 dB-Hz — the threshold above which the tutorial expects direct '
       'line-of-sight reception. Many of these weak signals arrive at 30–60° elevation, i.e. from the '
       'direction of the buildings, which is the signature of diffraction, multipath and non-line-of-sight '
       '(NLOS) reception rather than of a poor antenna. Only the highest satellites consistently exceed '
       '40 dB-Hz.')

picture(doc, FIG + 'fig_raw.png', 16.4,
        'Figure 2. (a) Number of satellites with an L1 code measurement, per constellation, over the whole '
        'session. (b) C/N\u2080 against elevation for every third epoch; the dashed and dotted lines mark the '
        '40 dB-Hz (line of sight) and 30 dB-Hz (multipath/NLOS) thresholds used in the tutorial.')

P(doc, 'The sky plot of a mid-session epoch (Fig. 3) shows the consequence of the obstruction: the 20 '
       'tracked satellites are spread over most azimuths, but every satellite below 35° elevation lies '
       'between azimuth 120° and 200°, and the sector from 340° to 20° is sampled only above 40°. The '
       'horizon is therefore closed to the north and north-west and open to the east and south-east. '
       'Coverage is nevertheless adequate for a position fix: the mean HDOP is 2.47 with GPS only and falls to 0.82 when Galileo and '
       'BeiDou are added, which already anticipates the improvement measured in Section 4.')

picture(doc, FIG + 'fig_sky.png', 9.4,
        'Figure 3. Sky plot of the tracked satellites at 09:05:30 GPST; marker shape gives the constellation '
        'and colour the C/N\u2080. Radial rings are 30° and 60° elevation.')

table(doc,
      ['Constellation', 'Mean sats', 'Max', 'Median C/N\u2080 (dB-Hz)', 'Role in the solution'],
      [['GPS', '7.1', '10', '33', 'reference constellation, L1 C/A'],
       ['Galileo', '7.6', '10', '33', 'added in v2, E1'],
       ['BeiDou', '6.8', '7', '36', 'added in v3, B1I'],
       ['GLONASS', '5.1', '9', '32', 'logged, not processed (FDMA biases)']],
      [3.4, 2.4, 1.6, 4.0, 6.0],
      'Table 2. Constellation statistics over the 580 epochs.')

# --------------------------------------------------------- 3 SPP algorithm --
H(doc, '3  SPP Algorithm (Least Squares)')
P(doc, 'For satellite i the pseudorange is modelled as')
EQ(doc, 'ρᵢ = ‖pᵢ − p‖ + c δtᵣ − c δtⁱ + Iᵢ + Tᵢ + εᵢ', '1')
P(doc, 'where pᵢ is the satellite position at transmission time, p the receiver position, δtᵣ and δtⁱ the '
       'receiver and satellite clock offsets, Iᵢ and Tᵢ the ionospheric and tropospheric delays and εᵢ the '
       'multipath, NLOS and noise term. The satellite clock is removed with the broadcast polynomial '
       '(including the relativistic eccentricity term and the group delay TGD), the ionosphere with the '
       'Klobuchar model and the troposphere with the Saastamoinen model, giving the corrected pseudorange '
       'ρ̃ᵢ = ‖pᵢ − p‖ + b + εᵢ with b = c δtᵣ.')
P(doc, 'Linearising about the current estimate x₀ = [x, y, z, b]ᵀ with the line-of-sight unit vector '
       'eᵢ = (pᵢ − p₀)/rᵢ⁰ gives')
EQ(doc, 'yᵢ = ρ̃ᵢ − rᵢ⁰ − b₀ = −eᵢᵀ Δp + Δb + εᵢ ,      y = H Δx + ε', '2')
P(doc, 'and the weighted least-squares correction, iterated until ‖Δp‖ < 0.1 mm, is')
EQ(doc, 'Δx̂ = (HᵀWH)⁻¹ HᵀW y ,      W = diag(w₁ … wₙ)', '3')
P(doc, 'Three weighting schemes were implemented: W = I (unweighted, the tutorial baseline), '
       'wᵢ = sin²θᵢ, and a C/N\u2080-dependent variance σᵢ² = a² + (b/sin θᵢ)² with a = 0.3 m and '
       'b = 0.6·10^((45 − C/N\u2080ᵢ)/20) m, which combines the elevation and signal-strength information '
       'recommended in the tutorial. Because GPS, BeiDou and Galileo keep separate system times, the state '
       'vector carries one clock per constellation, x = [x, y, z, b_G, b_C, b_E]ᵀ, and a BeiDou satellite '
       'contributes the row [−eᵢᵀ 0 1 0]; at least 3 + m satellites are required for m systems.')
P(doc, 'Fault exclusion follows the residual test used in receiver autonomous integrity monitoring: after '
       'convergence the normalised residual |vᵢ|/σᵢ of every satellite is formed, the largest is removed if '
       'it exceeds 3.5 and the epoch is re-solved, up to three removals. The design matrix at the final '
       'iteration also gives the dilution of precision after rotating Q = (HᵀH)⁻¹ to East–North–Up.')

listing(doc, [
    'def solve_epoch(obs, ephs, x0, cfg):',
    '    rows, t_rx = prepare(obs, ephs, x0, cfg)      # orbits, clocks, iono, tropo, masks',
    '    systems = [s for s in "GCE" if s in cfg["systems"]]',
    '    x = np.r_[x0[:3], np.zeros(len(systems))]',
    '    for _ in range(cfg["max_iter"]):',
    '        H, y = design(rows, x, systems)           # H[i] = [-e_i, 1 in the system column]',
    '        W = np.diag(weights(rows, cfg))           # I, sin^2(el) or 1/sigma^2(C/N0)',
    '        dx = np.linalg.solve(H.T @ W @ H, H.T @ W @ y)',
    '        x += dx',
    '        if np.linalg.norm(dx[:3]) < 1e-4:',
    '            break',
    '    if cfg["reject"]:                             # RAIM-like exclusion',
    '        for _ in range(cfg["max_removal"]):',
    '            v = residuals(rows, x, systems)',
    '            k = int(np.argmax(np.abs(v) / sigma(rows, cfg)))',
    '            if abs(v[k]) / sigma(rows, cfg)[k] < cfg["reject_thres"]:',
    '                break',
    '            rows.pop(k)',
    '            x = solve_epoch_core(rows, x, systems, cfg)',
    '    return x, residuals(rows, x, systems)',
], 'Listing 1. Core of the solver (full, documented code in the repository).')

# --------------------------------------------------- 4 own-data validation --
H(doc, '4  Own-Data Validation')
P(doc, 'Our data have no ground truth, so the solution is validated in the three ways the tutorial '
       'prescribes: comparison with an independent solution, consistency of the static solution about its '
       'mean, and checks on the inputs. Table 3 reports the ablation on our own data — each row changes one '
       'thing only — and the last column gives the 2D difference from the receiver’s own solution '
       '(UBX-NAV-HPPOSECEF) over the 580 common epochs.')

rows = []
for tag in ['v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7']:
    o = own[tag]
    rows.append([tag, o['desc'].replace('+ ', ''),
                 '%.1f' % o['nsat'], '%.2f' % o['hdop'], '%.2f' % o['resid'],
                 '%.1f / %.1f / %.1f' % tuple(o['std']),
                 '%.1f' % o['rms2d'], '%.1f' % o['rec']['rms2d']])

table(doc, ['Version', 'Change tested', 'Sats', 'HDOP', 'Post-fit\nRMS (m)',
            'σ E / N / U (m)', '2D RMS about\nmean (m)', '2D diff. vs\nreceiver (m)'],
      rows, [1.5, 4.6, 1.2, 1.3, 1.9, 3.6, 2.4, 2.3],
      'Table 3. Ablation on our own data (580 epochs, static). The 2D RMS about the mean measures the '
      'repeatability of the static solution; the last column measures agreement with the receiver.', fontsize=8.0)

P(doc, 'The two strongest effects are geometric. Adding Galileo raises the average satellite count from 5.4 '
       'to 11.9 and cuts the repeatability from 42.9 m to 30.7 m; adding BeiDou brings it to 18.7 satellites, '
       'HDOP 0.82 and 24.1 m. This is the behaviour predicted by the error budget: with UERE ≈ 6 m and '
       'HDOP ≈ 2.5 the GPS-only solution cannot do better than about 15 m, and multipath multiplies that '
       'figure by a factor of two to three in a canyon. C/N\u2080 weighting (v5) is the single most '
       'effective correction after the constellations: the height scatter falls from 32.9 m to 13.8 m and '
       'the agreement with the receiver improves from 16.9 m to 7.7 m, because the vertical error is driven '
       'by the weak, low-elevation signals that the weighting suppresses. Residual rejection (v6) removes '
       'the remaining tail — the worst epoch of the GPS-only solution is 585 m away from the mean, against '
       '61 m for v6 — at the cost of one satellite per epoch. The C/N\u2080 mask of v7 lowers the post-fit '
       'residual to 6.4 m but rejects three epochs and slightly degrades the scatter, so the mask is too '
       'aggressive for this site and v6 is retained as the final version.')

P(doc, 'Table 4 summarises the comparison with the receiver solution for the final version. The agreement '
       'is 7.0 m in 2D, with a small horizontal bias (−2.0 m East, +0.1 m North) and a +7.1 m vertical '
       'offset. The offset is the expected single-frequency SPP height bias: the RTKCONV navigation header '
       'carries no broadcast ionospheric coefficients, so default mid-latitude Klobuchar values had to be '
       'used, and no antenna phase-centre or receiver group-delay calibration was applied.')

table(doc, ['Statistic', 'SPP − receiver', 'Receiver about its own mean'],
      [['Mean E / N / U (m)', '−2.03 / +0.14 / +7.07', '—'],
       ['Std E / N / U (m)', '5.49 / 3.75 / 14.63', '15.89 / 12.53 / 2.89'],
       ['2D RMS difference (m)', '6.95', '20.24'],
       ['Epochs compared', '580 of 580', '580'],
       ['Mean position', '22.305603° N, 114.180026° E, h = 25.9 m',
        '22.305602° N, 114.180046° E, h = 18.8 m']],
      [4.6, 6.6, 5.3],
      'Table 4. Differences between our SPP solution and the receiver solution for the final version (v6).')

P(doc, 'The last column of Table 4 is the key to reading the first one. The receiver itself wanders by '
       '15.9 m East and 12.5 m North about its own mean, i.e. as much as our solution does (17.1 m and '
       '11.8 m). The two solutions are therefore wrong in the same way at the same epochs: both see the '
       'same reflected signals, and the difference between them cancels the common-mode multipath. An '
       'agreement of 7 m is a statement about the processing chain, not about accuracy — which is exactly '
       'why the benchmark of Section 5 needs an independent reference.')

picture(doc, FIG + 'fig_enu.png', 15.6,
        'Figure 4. East, North and Up components of the static solution about its mean. Grey: GPS-only '
        'baseline (v1); red: final multi-GNSS weighted solution (v6). Three GPS-only epochs fall outside '
        'the plotted range (up to −0.9 km in height).')

picture(doc, FIG + 'fig_scatter.png', 15.4,
        'Figure 5. East–North scatter about the mean of the static solution: (a) GPS-only baseline, '
        '(b) final version. The dotted and dashed circles are the 1σ and 2σ East/North ellipses.')

P(doc, '**Input checks.** Two problems were found before any of these numbers could be trusted. First, the '
       'reference-station file downloaded from HK SatRef covers 17:00–17:59 GPST on 30 October, whereas the '
       'rover log runs at 09:00 GPST: the local time (17:00 HKT) had been entered in the request form where '
       'UTC was expected, so the base station and the rover do not overlap. RTKPOST therefore returned no '
       'differential solution at all — the .pos file contains its header and zero epochs — and the '
       'RTKPOST differential column of the validation table cannot be filled. A single-point run in RTKPOST '
       'on the second log does produce 182 epochs (quality flag 5) whose ground-track scatter, ±50–150 m, '
       'matches our GPS-only baseline. Second, the first version of our BeiDou processing was wrong by '
       '4 000 km in the pseudorange residuals because the BeiDou clock polynomial was evaluated with a '
       'time-of-clock offset of 1 356 weeks; the residual consistency test described in Section 6 caught '
       'it. Both cases illustrate why the tutorial insists on checking the inputs before interpreting a '
       'solution.')

# ------------------------------------------------------ 5 benchmark --------
H(doc, '5  Verification and Benchmark Results')
H(doc, '5.1  Regression test on the example dataset', level=2)
P(doc, 'Every version was run on the example dataset before the benchmark, as the tutorial requires. The '
       'example has 186 epochs, the receiver solution and the reference results of the tutorial, so it is '
       'the only dataset where our code can be checked against an answer we did not produce. Table 5 lists '
       'the error against the mean receiver position (UBX-NAV-HPPOSECEF).')

rows = []
for tag in ['v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7']:
    e = ex[tag]
    rows.append([tag, e['desc'].replace('+ ', ''),
                 '%.2f' % e['rms2d'], '%.2f' % e['rms3d'], '%.2f' % e['p95_2d'],
                 '%+.1f / %+.1f / %+.1f' % tuple(e['mean_enu']), str(e['n'])])
table(doc, ['Version', 'Change tested', '2D RMSE (m)', '3D RMSE (m)', 'P95 2D (m)',
            'Bias E / N / U (m)', 'Epochs'],
      rows, [1.5, 4.9, 2.1, 2.1, 1.9, 4.0, 1.6],
      'Table 5. Example dataset (Block X, 2025, 186 epochs): error of every version against the receiver '
      'reference solution.', fontsize=8.0)

P(doc, 'The example behaves as the tutorial describes. The GPS-only baseline is poor in both 2D and 3D — '
       '25.6 m and 80.7 m — and it only solves 113 of the 186 epochs, because the example navigation file '
       'contains five GPS ephemerides and 73 epochs therefore have fewer than four usable GPS satellites. '
       'Adding Galileo and BeiDou solves all 186 epochs and cuts the 2D error to 15.5 m; most of the '
       'remaining 3D error is the known vertical bias of single-frequency SPP (+20.7 m). The weighting and '
       'fault-exclusion steps barely change the 2D RMSE (15.3–16.1 m, the differences being within the '
       'noise) but they cut the height bias from +20.7 m to +16.2 m and the 95th percentile of the error '
       'from 28.0 m to 23.5 m, i.e. they act on the tail rather than on the bulk of the distribution. This '
       'is the same signature as on our own data, which is why the same final version was used on the '
       'benchmark.')

P(doc, 'Our GPS-only figure (25.6 m) is lower than the 37.9 m reported in Table 13 of the tutorial. The '
       'two numbers are not computed the same way: we compare with the mean receiver position over all '
       'epochs and apply a 10° elevation mask, whereas the reference compares with the per-epoch receiver '
       'solution and masks at 15°. The comparison that the tutorial does not provide — the full '
       'multi-constellation chain on all 186 epochs — is the one that shows the size of the gain: a factor '
       'of 2.5 in 2D and 3.4 in 3D relative to the GPS-only baseline.')

picture(doc, FIG + 'fig_example.png', 15.4,
        'Figure 6. Example dataset: (a) 2D error of every epoch against the receiver reference for the '
        'multi-constellation baseline (v3) and the final version (v6); (b) distribution of the 2D error.')

H(doc, '5.2  UrbanNav benchmark', level=2)
P(doc, 'The UrbanNav-HK-Deep-Urban-1 observation file contains 1534 epochs (week 2158, 455 346–456 879 s) '
       'and its navigation file carries the broadcast ionospheric coefficients, which are used here instead '
       'of the default values. The same seven versions were run in the same order. Table 6 reports the '
       'measurable metrics: availability (epochs with a solution), mean satellite count, mean HDOP, post-fit '
       'residual and two internal consistency indicators — the 2D deviation from the final v6 solution and '
       'the median epoch-to-epoch step, which for a 1 Hz vehicle trajectory is dominated by noise when the '
       'platform is nearly stationary.')

rows = []
for tag in ['v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7']:
    b = bm[tag]
    rows.append([tag, b['desc'].replace('+ ', ''),
                 '%.1f' % b['avail'], '%.1f' % b['nsat'], '%.2f' % b['hdop'], '%.2f' % b['resid'],
                 '%.1f' % b['dev_v6'], '%.2f' % b['jitter']])
table(doc, ['Version', 'Change tested', 'Avail. (%)', 'Sats', 'HDOP', 'Post-fit\nRMS (m)',
            '2D dev. from\nv6 (m)', 'Median step\n(m)'],
      rows, [1.5, 4.9, 1.9, 1.3, 1.3, 1.9, 2.4, 2.2],
      'Table 6. Ablation on the UrbanNav benchmark (1534 epochs). The reference trajectory used for scoring '
      'is withheld, so absolute RMSE cannot be computed offline; the table reports what can be measured '
      'without it.', fontsize=8.0)

P(doc, 'Availability is the metric that separates the versions most clearly, and it is also the one that '
       'decides whether a submission is ranked at all (the rule requires A ≥ 90 %). The GPS-only baseline '
       'loses 60 epochs (96.1 %) and averages 5.7 satellites with HDOP 2.79 — in the deep-urban segments '
       'there are simply not enough GPS satellites to solve. Galileo raises availability to 99.6 % and '
       'BeiDou to 99.8 %, with 15.9 satellites and HDOP 1.23, and the two additions together move the '
       'solution by 33.5 m (RMS, 2D) relative to the GPS-only track. Weighting and fault exclusion change '
       'the solution by a further 12.8 m and 4.7 m respectively, and reduce the epoch-to-epoch step from '
       '4.75 m to 4.05 m, i.e. they remove high-frequency noise rather than shifting the trajectory. The '
       'C/N\u2080 mask of v7 lowers the post-fit residual to 3.9 m but costs one percent of availability '
       'and pulls the solution back by 5.3 m, which suggests that it also removes healthy satellites in the '
       'open-sky segments; it is kept only as a diagnostic.')

picture(doc, FIG + 'fig_bench.png', 15.8,
        'Figure 7. Benchmark trajectory in the local East–North frame: (a) GPS-only baseline and final '
        'version drawn as a track, (b) every epoch plotted as a point. The circuit is about 800 m across.')

P(doc, 'These deviations are differences between solutions, not errors: a version that moves the trajectory '
       'by 30 m is not necessarily 30 m worse, and the only way to turn them into an accuracy statement is '
       'the reference trajectory held by the teaching team. What the table does establish is that the '
       'multi-constellation step is what makes the benchmark solvable at all, and that the weighting and '
       'fault-exclusion steps act on the noise rather than on the geometry. In the urban segments the '
       'remaining error is dominated by multipath and NLOS reception — the 31 % of measurements below '
       '30 dB-Hz measured at Block X is typical of this dataset too — and by the fact that a reflected '
       'signal biases the pseudorange by tens of metres while its geometry still looks healthy.')

P(doc, 'The submitted files are G18_benchmark.csv (1531 epochs, 99.8 % availability) and G18_owndata.csv '
       '(580 epochs), both in the five-column format of the tutorial with ECEF coordinates to three '
       'decimals. The final 2D/3D RMSE, the 95th-percentile error and the leaderboard rank are produced by '
       'the evaluation platform from the withheld reference and are therefore not quoted here.')

P(doc, 'The documented code (gnss.py, spp.py, run_all.py, plots.py), the two raw logs, the converted RINEX '
       'files and a README that reproduces both CSV files are in the group repository '
       'https://github.com/ox-x/AAE4203-Lab1-G18.')

H(doc, '6  AI-Use Statement')
P(doc, 'A generative AI assistant (WorkBuddy, running a DeepSeek-class model) was used for three purposes: '
       'to draft the RINEX readers and the least-squares solver from our specification, to explain the '
       'BeiDou time-system and GEO conventions documented in the ICD, and to debug the two failures '
       'described below. All output was checked against data whose answer we already knew, in the order the '
       'tutorial requires: the example dataset first, the benchmark last.')
P(doc, 'Three checks caught real errors. (i) On the example dataset the GPS-only solution initially gave '
       'no solution for 40 % of the epochs; the cause was a RINEX field-width assumption (the 14-character '
       'value field followed by the two loss-of-lock/strength characters) and it was found by comparing the '
       'satellite count per epoch with the reference plots of the tutorial. (ii) BeiDou residuals were '
       'consistent to 4 000 km for the first version: the satellite clock was evaluated with a '
       'time-of-clock offset of 1 356 weeks, which multiplied the af₁ term into a 12.8 ms error. The '
       'diagnostic was to compute, for every satellite, the quantity ρ + c·δt_s − I − T − r, which must be '
       'the same receiver clock bias for all satellites of one system; the spread exposed the bug '
       'immediately. (iii) The satellite elevations were first computed from the ECEF z component instead '
       'of the local vertical, which put half of the satellites below the horizon; the same consistency '
       'test showed the geometry to be impossible.')
P(doc, 'No data from other groups and no personal data were uploaded. The submitted trajectories are '
       'computed by our own code from the provided observations; no receiver solution, published UrbanNav '
       'ground truth or third-party position was used. The key prompts are listed in Appendix A.')

# ------------------------------------------------------------ references ---
H(doc, 'References')
for i, ref in enumerate([
    'W. Wen and the AAE4203 teaching team, “GNSS data collection, single point positioning and an accuracy '
    'challenge,” Laboratory Tutorial, Week 9, Semester 1, 2026/27, PolyU, v3.0.',
    'P. Misra and P. Enge, Global Positioning System: Signals, Measurements, and Performance, 2nd ed., '
    'Ganga-Jamuna Press, 2011.',
    'P. J. G. Teunissen and O. Montenbruck (Eds.), Springer Handbook of Global Navigation Satellite Systems, '
    'Springer, 2017.',
    'T. Takasu and A. Yasuda, “Development of the low-cost RTK-GPS receiver with an open source program '
    'package RTKLIB,” Proc. Int. Symp. GPS/GNSS, Jeju, 2009.',
    'L.-T. Hsu et al., “UrbanNav: an open-sourced multisensory dataset for benchmarking positioning '
    'algorithms designed for urban areas,” Proc. ION GNSS+ 2021, pp. 226–256.',
    'China Satellite Navigation Office, BeiDou Navigation Satellite System Signal In Space Interface '
    'Control Document, B1I, v3.0, 2019.',
], 1):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.first_line_indent = Cm(-0.8)
    r = p.add_run('[%d]  ' % i)
    r.font.size = Pt(8.8)
    r = p.add_run(ref)
    r.font.size = Pt(8.8)

# ------------------------------------------------------------- appendix ----
H(doc, 'Appendix A  Key AI Prompts')
prompts = [
    ('P1 — baseline solver (used, then rewritten by the group)',
     'I have RINEX 3 observation and navigation files from a u-blox ZED-F9P. Write a Python function that '
     'computes the satellite position and clock offset from the broadcast ephemeris (ICD-200), corrects the '
     'pseudorange for the satellite clock, Klobuchar ionosphere and Saastamoinen troposphere, and solves '
     'the weighted least-squares SPP epoch by epoch with Gauss–Newton iterations stopped at 0.1 mm. Use '
     'sin²(elevation) weights first. Explain every step and every constant.'),
    ('P2 — multi-constellation extension',
     'Extend the solver to GPS + Galileo + BeiDou with one receiver clock bias per system. BeiDou broadcasts '
     'in BDT; explain how the week and the 14 s offset enter the time of ephemeris and the clock polynomial, '
     'and why the satellite position algorithm differs for GEO satellites.'),
    ('P3 — verification',
     'Write a script that compares my trajectory with a reference CSV (epoch, ECEF) and prints the mean and '
     'standard deviation of the East/North/Up differences, the 2D and 3D RMSE, the 95th percentile and a '
     'scatter plot about the mean.'),
    ('P4 — debugging prompt that found the BeiDou bug',
     'For every satellite of every constellation print ρ + c·δt_s − I − T − ‖p_s − p_r‖ at one epoch. If '
     'the orbits and clocks are consistent this must equal the receiver clock bias, so it must be the same '
     'for all satellites of one system. My BeiDou values differ by 4 000 km — what could cause a '
     'constellation-wide offset of that size?'),
]
for head, body in prompts:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(1)
    r = p.add_run(head)
    r.bold = True
    r.font.size = Pt(8.8)
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_after = Pt(3)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run('“' + body + '”')
    r.font.size = Pt(8.6)
    r.italic = True

P(doc, 'Every prompt was answered with code that was then run on the example dataset before the benchmark; '
       'the numbers in Tables 3–6 come from our own runs of that code, not from the assistant.', space_after=2)

doc.save(OUT)
print('written', OUT)
