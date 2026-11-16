"""Procedural sound design for the 15 s showreel (synced to showreel.html cuts).

Run:  python3 audio.py   -> audio.wav (48 kHz, stereo, 16-bit)
Only numpy is needed.
"""
import wave
import numpy as np

SR = 48000
DUR = 15.0
N = int(SR * DUR)
L = np.zeros(N)
R = np.zeros(N)
rs = np.random.default_rng(3)


def add(sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N:
        return
    sig = sig[: N - max(i, 0)]
    if i < 0:
        sig = sig[-i:]
        i = 0
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    L[i:i + len(sig)] += sig * gain * l * 1.414
    R[i:i + len(sig)] += sig * gain * r * 1.414


def tt(d):
    return np.arange(int(d * SR)) / SR


def onepole_lp(x, cutoff):
    """Time-varying one-pole low-pass; cutoff may be an array (Hz)."""
    c = np.broadcast_to(np.asarray(cutoff, float), x.shape)
    a = 1 - np.exp(-2 * np.pi * c / SR)
    y = np.empty_like(x)
    s = 0.0
    for k in range(len(x)):
        s += a[k] * (x[k] - s)
        y[k] = s
    return y


def hp(x):
    return np.diff(x, prepend=0.0)


# ---------------------------------------------------------------- instruments
def kick(gain=1.0, dur=0.45):
    t = tt(dur)
    f = 45 + 140 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 7.5)
    s[:120] += rs.uniform(-1, 1, 120) * np.linspace(0.6, 0, 120)
    return np.tanh(s * 1.6) * gain


def sub(dur=1.4, f0=62, f1=32):
    t = tt(dur)
    f = f1 + (f0 - f1) * np.exp(-t * 3)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.6)


def clap(dur=0.25):
    t = tt(dur)
    n = hp(rs.uniform(-1, 1, len(t)))
    env = np.exp(-t * 22)
    for d in (0.0, 0.011, 0.022):
        env += 0.6 * np.exp(-np.clip(t - d, 0, None) * 120) * (t >= d)
    return n * env * 0.7 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.4


def hat(dur=0.06, open_=False):
    t = tt(0.35 if open_ else dur)
    n = hp(hp(rs.uniform(-1, 1, len(t))))
    return n * np.exp(-t * (9 if open_ else 70)) * 0.35


def crash(dur=1.6):
    t = tt(dur)
    n = hp(hp(rs.uniform(-1, 1, len(t))))
    return n * np.exp(-t * 2.6) * 0.3


def whoosh(dur, rise=True, f0=300, f1=7000, shape=2.0):
    t = tt(dur)
    p = t / dur
    curve = p ** shape if rise else np.sin(np.pi * p) ** 1.5
    cut = f0 + (f1 - f0) * (p if rise else np.sin(np.pi * p))
    n = rs.uniform(-1, 1, len(t))
    y = onepole_lp(onepole_lp(n, cut), cut)
    y /= np.max(np.abs(y)) + 1e-9
    return y * curve


def blip(f0, f1=None, dur=0.12):
    t = tt(dur)
    f = f0 if f1 is None else f0 + (f1 - f0) * (t / dur)
    return np.sin(2 * np.pi * np.cumsum(np.broadcast_to(f, t.shape)) / SR) * np.exp(-t * 30)


def tick(f=3200):
    t = tt(0.012)
    return np.sin(2 * np.pi * f * t) * np.exp(-t * 500) * 0.5


def pluck(f, dur=1.2, bright=1.0):
    t = tt(dur)
    s = sum((0.6 ** (h - 1)) * bright ** (h - 1) * np.sin(2 * np.pi * f * h * t) * np.exp(-t * (4 + 2.5 * h))
            for h in range(1, 6))
    return s * np.minimum(1, t * 400)


def bell(f, dur=2.5):
    t = tt(dur)
    parts = [(1, 1, 1.6), (2.76, 0.5, 2.6), (5.4, 0.25, 4.0), (8.93, 0.12, 6.0)]
    return sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * d) for m, a, d in parts) * np.minimum(1, t * 300)


def pad(freqs, dur, att=1.0, rel=1.0):
    t = tt(dur)
    s = np.zeros(len(t))
    for f in freqs:
        for det in (-0.004, 0.0, 0.004):
            ff = f * (1 + det)
            s += np.sin(2 * np.pi * ff * t) + 0.25 * np.sin(2 * np.pi * 2 * ff * t)
    env = np.minimum(1, t / att) * np.minimum(1, (dur - t) / rel)
    return s / (len(freqs) * 3) * np.clip(env, 0, 1)


def bass(f, dur=0.22):
    t = tt(dur)
    s = sum(np.sin(2 * np.pi * f * h * t) / h for h in range(1, 6))
    return np.tanh(s * 1.4) * np.exp(-t * 9) * np.minimum(1, t * 600)


def hit(t0, g=1.0, big=False):
    add(kick(), t0, 0.9 * g)
    add(sub(1.6 if big else 0.9), t0, 0.55 * g)
    add(clap(), t0, 0.45 * g)
    if big:
        add(crash(), t0, 0.5 * g, 0.2)
        add(crash(), t0 + 0.01, 0.5 * g, -0.2)


A2, C3, E3, G3, A3 = 110.0, 130.81, 164.81, 196.0, 220.0
A4, C5, D5, E5, G5, A5, Cs5 = 440.0, 523.25, 587.33, 659.25, 783.99, 880.0, 554.37

# ================================================================ 01 UVOD
add(blip(520, 1040, 0.18), 0.08, 0.5)
add(whoosh(0.5, True, 200, 9000, 2.5), 0.5, 0.35, -0.5)
hit(1.05, 1.0, big=True)
add(pad([A2, E3, A3, C5], 3.2, att=0.05, rel=1.2), 1.05, 0.22)
for k in range(32):
    add(tick(2600 + (k % 3) * 300), 1.35 + k / 60, 0.25, rs.uniform(-.4, .4))
add(whoosh(0.4, True, 400, 12000, 3), 1.82, 0.3, 0.4)

# ================================================================ 02 FORMA
hit(2.2, 0.9)
for k, tb in enumerate(np.arange(2.2, 4.7, 0.25)):
    if k % 2 == 0:
        add(kick(0.7), tb, 0.55)
    else:
        add(hat(), tb, 0.6, 0.3)
    add(bass([A2 / 2, A2 / 2, C3 / 2, G3 / 4][(k // 2) % 4]), tb, 0.35)
for kt, f in ((2.85, C5), (3.40, E5), (3.95, G5)):
    add(whoosh(0.3, False, 600, 4000), kt - 0.3, 0.18, 0.3)
    add(pluck(f), kt, 0.32, -0.2)
    add(pluck(f * 2, 0.6, 0.6), kt, 0.1, 0.3)
add(blip(900, 300, 0.2), 4.12, 0.25)
add(whoosh(0.5, True, 200, 14000, 3.0), 4.22, 0.55)

# ================================================================ 03 TIPOGRAFIJA
for i, w in enumerate((4.72, 5.05, 5.40, 5.75)):
    hit(w, 1.0, big=(i == 0))
    add(bass([A2, C3, D5 / 4, E3][i], 0.32), w, 0.4)
    add(blip(1600 + 300 * i, 2400 + 300 * i, 0.08), w, 0.12, [-.5, .5, -.5, .5][i])
add(whoosh(0.5, True, 300, 9000, 2.0), 5.8, 0.25)
hit(6.3, 1.1, big=True)
for k, tb in enumerate(np.arange(6.3, 6.95, 0.125)):
    add(hat(open_=(k % 4 == 2)), tb, 0.5, 0.35 if k % 2 else -0.35)
    if k % 2 == 0:
        add(kick(0.8), tb, 0.6)
        add(bass(A2 / 2), tb, 0.35)

# slat wipe flutter
fl = whoosh(0.45, False, 800, 6000)
fl *= 0.55 + 0.45 * np.sign(np.sin(2 * np.pi * 26 * tt(0.45)))
add(fl, 6.92, 0.4, -0.3)

# ================================================================ 04 PROSTOR
add(sub(2.2, 70, 28), 7.2, 0.7)
add(kick(0.8, 0.6), 7.2, 0.7)
add(pad([A2 / 2, E3, A3, C5, E5], 2.7, att=0.4, rel=0.4), 7.15, 0.2)
for _ in range(70):  # sparkle as particles assemble
    t0 = 7.05 + rs.beta(1.4, 2.2) * 1.4
    add(blip(rs.uniform(2500, 7000), None, 0.08), t0, rs.uniform(0.03, 0.08), rs.uniform(-.9, .9))
for k, tb in enumerate(np.arange(7.7, 9.4, 0.5)):
    add(kick(0.5), tb, 0.35)
    add(hat(), tb + 0.25, 0.35, 0.4)
add(whoosh(0.9, False, 200, 2500), 8.5, 0.25, 0.3)  # morph swell
add(whoosh(0.42, True, 300, 16000, 3.5), 9.4, 0.6)

# ================================================================ 05 PODACI
hit(9.82, 1.15, big=True)
add(whoosh(0.3, False, 3000, 15000), 9.75, 0.3)
# counter ticks slowing down
tk, gap = 10.05, 0.018
while tk < 11.35:
    add(tick(3400), tk, 0.22, rs.uniform(-.5, .5))
    tk += gap
    gap *= 1.09
for i in range(9):  # bar pops, pentatonic up
    f = [A4, C5, D5, E5, G5, A5, C5 * 2, D5 * 2, E5 * 2][i]
    add(blip(f * 0.5, f, 0.1), 10.15 + i * 0.06, 0.16, -0.6 + i * 0.15)
t = tt(1.05)
glide = np.sin(2 * np.pi * np.cumsum(500 + 700 * (t / 1.05) ** 1.5) / SR) * np.sin(np.pi * t / 1.05) ** 2
add(glide, 10.55, 0.06, 0.5)
for k, tb in enumerate(np.arange(10.32, 12.1, 0.25)):
    if k % 2 == 0:
        add(kick(0.75), tb, 0.55)
        add(bass([A2 / 2, C3 / 2, E3 / 2, G3 / 4][(k // 2) % 4]), tb, 0.35)
    else:
        add(hat(), tb, 0.55, -0.3)

# ================================================================ 06 KRAJ
add(whoosh(0.4, True, 400, 15000, 2.0), 12.0, 0.5, -0.6)
hit(12.3, 1.1, big=True)
for i in range(3):
    add(whoosh(0.7, False, 500, 5000), 12.35 + i * 0.09, 0.12, [-.7, 0, .7][i])
for i, f in enumerate((A4, Cs5, E5)):  # resolve to A major on lock-up
    add(pluck(f, 2.0), 13.2 + i * 0.07, 0.3, [-.4, 0, .4][i])
add(kick(0.6), 13.2, 0.5)
add(bell(A5, 2.2), 13.0, 0.12, 0.2)
add(pad([A2, E3, A3, Cs5, E5], 2.2, att=0.25, rel=1.2), 12.8, 0.24)
for k in range(44):
    add(tick(2800 + (k % 4) * 200), 13.6 + k / 70, 0.16, rs.uniform(-.3, .3))

# ---------------------------------------------------------------- reverb + master
ir_t = tt(1.6)
ir = rs.uniform(-1, 1, len(ir_t)) * np.exp(-ir_t * 4.2)
ir[: int(0.012 * SR)] = 0
ir /= np.sqrt(np.sum(ir ** 2))


def conv(x):
    n = len(x) + len(ir)
    m = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[: len(x)]


wetL, wetR = conv(L), conv(R)
L = L + 0.22 * wetL
R = R + 0.22 * wetR

fade = np.ones(N)
fi = int(14.7 * SR)
fade[fi:] = np.linspace(1, 0, N - fi) ** 2
L *= fade
R *= fade

peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
L = np.tanh(L / peak * 1.25) / np.tanh(1.25) * 0.93
R = np.tanh(R / peak * 1.25) / np.tanh(1.25) * 0.93

data = (np.stack([L, R], 1) * 32767).astype('<i2')
with wave.open('audio.wav', 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(data.tobytes())
print('audio.wav written', data.shape)
