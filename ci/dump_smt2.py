#!/usr/bin/env python3
"""Self-contained SMT-LIB exporter for the n=4, alpha=8/7 safe-region encoding.

Stdlib only; mirrors src/ffd_safe_region.py::decide(m) exactly (rank-count FFV).
Usage:
    python ci/dump_smt2.py --m 8 > m8.smt2

The generated SMT-LIB is semantically identical to what z3's to_smt2() produced
for logs/safe_region_m<M>.smt2; only the let-inlining / flat-sum formatting differs.
"""

import argparse


# tau = 8/7, item lower bound 2/7 (strict), item upper bound 3/7 (m=12) or 1 (m<12).
TAU = "(/ 8 7)"
LO = "(/ 2 7)"


def build(m):
    hi = "(/ 3 7)" if m == 12 else "1.0"
    lines = []
    nvars = 0
    nassert = 0

    def decl(s):
        nonlocal nvars
        lines.append(s)
        nvars += 1

    def ass(s):
        nonlocal nassert
        lines.append(f"(assert {s})")
        nassert += 1

    x = [f"x{i}" for i in range(m)]
    a = [[f"a{i}_{k}" for k in range(4)] for i in range(m)]
    u = [f"u{i}" for i in range(m)]
    t = [[f"t{i}_{g}" for g in range(4)] for i in range(m)]
    g = [[f"g{i}_{b}" for b in range(4)] for i in range(m)]
    s1 = [[f"s1_{i}_{k}" for k in range(4)] for i in range(m)]
    b2 = [[f"b2_{i}_{k}" for k in range(4)] for i in range(m)]
    b3 = [[f"b3_{i}_{k}" for k in range(4)] for i in range(m)]

    lines.append("(set-logic ALL)")
    lines.append("(set-info :status unknown)")

    for v in x:
        decl(f"(declare-fun {v} () Real)")
    for M in (a, t, g, s1, b2, b3):
        for row in M:
            for v in row:
                decl(f"(declare-fun {v} () Bool)")
    for v in u:
        decl(f"(declare-fun {v} () Bool)")

    def ite_r(cond, expr):
        return f"(ite {cond} {expr} 0.0)"

    def ite_i(cond):
        return f"(ite {cond} 1 0)"

    def plus(terms, zero):
        if not terms:
            return zero
        if len(terms) == 1:
            return terms[0]
        return "(+ " + " ".join(terms) + ")"

    # sort and range
    for i in range(m - 1):
        ass(f"(>= {x[i]} {x[i + 1]})")
    for i in range(m):
        ass(f"(> {x[i]} {LO})")
        ass(f"(<= {x[i]} {hi})")

    # FFD first-fit (faithful)
    def load(i, b):
        return plus([ite_r(g[j][b], x[j]) for j in range(i)], "0.0")

    def fits(i, b):
        return f"(<= {plus([load(i, b), x[i]], '0.0')} {TAU})"

    for i in range(m):
        for b in range(4):
            first = "(and " + " ".join([fits(i, b)] + [f"(not {fits(i, bp)})" for bp in range(b)]) + ")"
            ass(f"(= {g[i][b]} {first})")
        ass("(or " + " ".join(g[i]) + ")")

    # MMS <= 1
    for i in range(m):
        ass(f"(= {plus([ite_i(t[i][gg]) for gg in range(4)], '0')} 1)")
    for gg in range(4):
        ass(f"(<= {plus([ite_r(t[i][gg], x[i]) for i in range(m)], '0.0')} 1.0)")

    # witness assignment, U nonempty
    for i in range(m):
        ass(f"(= {plus([ite_i(a[i][k]) for k in range(4)] + [ite_i(u[i])], '0')} 1)")
    ass("(or " + " ".join(u) + ")")

    # FFV (rank-count)
    for k in range(4):
        def r(i):
            return "true" if k == 0 else "(not (or " + " ".join(a[i][:k]) + "))"

        X1 = plus([ite_r(s1[i][k], x[i]) for i in range(m)], "0.0")
        for i in range(m):
            ass(f"(= {s1[i][k]} (and {' '.join([r(i)] + [f'(not {r(j)})' for j in range(i)])}))")
            ass(f"(=> {s1[i][k]} {a[i][k]})")

        X2g = plus([ite_r(b2[i][k], x[i]) for i in range(m)], "0.0")
        for i in range(m):
            parts = [r(i), f"(not {s1[i][k]})", f"(<= {plus([X1, x[i]], '0.0')} {TAU})"]
            for j in range(i):
                parts.append(f"(not (and {r(j)} (not {s1[j][k]}) (<= {plus([X1, x[j]], '0.0')} {TAU})))")
            ass(f"(= {b2[i][k]} (and {' '.join(parts)}))")
            ass(f"(=> {b2[i][k]} (>= {plus([ite_i(a[j][k]) for j in range(i + 1)], '0')} 2))")

        for i in range(m):
            parts = [r(i), f"(not {s1[i][k]})", f"(not {b2[i][k]})", f"(<= {plus([X1, X2g, x[i]], '0.0')} {TAU})"]
            for j in range(i):
                parts.append(f"(not (and {r(j)} (not {s1[j][k]}) (not {b2[j][k]}) (<= {plus([X1, X2g, x[j]], '0.0')} {TAU})))")
            ass(f"(= {b3[i][k]} (and {' '.join(parts)}))")
            ass(f"(=> {b3[i][k]} (>= {plus([ite_i(a[j][k]) for j in range(i + 1)], '0')} 3))")

    lines.append("(check-sat)")
    return "\n".join(lines) + "\n", nvars, nassert


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, required=True)
    args = ap.parse_args()
    m = args.m
    assert 4 <= m <= 12, "m must be in [4,12]"
    out, nvars, nassert = build(m)
    print(out, end="")
    print(f"; variables={nvars} constraints={nassert}", file=__import__("sys").stderr)


if __name__ == "__main__":
    main()
