import sys

import numpy as np

BINS, RESAMPLES, SIMS = 15, 400, 200
LINE_SD = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0


def ece_from(stats):
    n, sc, sk = stats[..., 0], stats[..., 1], stats[..., 2]
    return np.abs(sc - sk).sum(-1) / n.sum(-1)


def sim(rng, lines, per_line, conf_draw, delta):
    m = lines * per_line
    c = conf_draw(rng, m)
    shift = np.repeat(rng.normal(0, LINE_SD, lines), per_line)
    k = rng.random(m) < np.clip(c - delta + shift, 0, 1)
    b = np.clip(np.digitize(c, np.linspace(0, 1, BINS + 1)[1:-1], right=True), 0, BINS - 1)
    line = np.repeat(np.arange(lines), per_line)
    st = np.zeros((lines, BINS, 3))
    np.add.at(st, (line, b, 0), 1)
    np.add.at(st, (line, b, 1), c)
    np.add.at(st, (line, b, 2), k)
    w = rng.multinomial(lines, np.full(lines, 1 / lines), size=RESAMPLES)
    boot = np.einsum("rl,lbs->rbs", w, st)
    return ece_from(st.sum(0)), np.percentile(ece_from(boot), 97.5)


def main():
    lines, per_line = int(sys.argv[1]), int(sys.argv[2])
    dists = {
        "confident Beta(8,1)": lambda r, m: r.beta(8, 1, m),
        "spread U(0.2,1)": lambda r, m: r.uniform(0.2, 1.0, m),
    }
    rng = np.random.default_rng(20261027)
    for name, dist in dists.items():
        for delta in [0.0, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08]:
            res = np.array([sim(rng, lines, per_line, dist, delta) for _ in range(SIMS)])
            print(f"{name:20s} n={lines*per_line:6d} delta={delta:.2f} meanECE={res[:,0].mean():.3f} "
                  f"P(upper<=0.05)={np.mean(res[:,1] <= 0.05):.2f}")


main()
