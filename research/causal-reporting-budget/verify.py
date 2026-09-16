"""Recompute the finite premises of the causal-reporting budget note.

Python 3.10+, standard library only. No network, file writes or model calls.
The analytic proof in README.md handles infinite trees and adaptive histories.
Prepared by Zero (ChatGPT) for Youngseok Oh, 2026-09-16.
"""
from __future__ import annotations
import json
from fractions import Fraction as F
from functools import lru_cache
from itertools import permutations, product
from typing import Callable

LOW = (0, 1, 2, 4)
HIGH = (3, 5, 6, 7)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def raw_law(k: int) -> tuple[int, ...]:
    """Integer masses with denominator 120: all ordered 6P3 samples."""
    if k not in (0, 1, 5, 6):
        raise ValueError('source count outside the specified hypotheses')
    labels = [1] * k + [0] * (6 - k)
    mass = [0] * 8
    for i, j, h in permutations(range(6), 3):
        mass[4 * labels[i] + 2 * labels[j] + labels[h]] += 1
    return tuple(mass)


@lru_cache(None)
def subplans(prefix: str) -> tuple[tuple[str, ...], ...]:
    """Before any flip: flip now, or wait and select the future subtrees."""
    if len(prefix) == 3:
        return ((), (prefix,))
    return ((prefix,),) + tuple(a + b for a in subplans(prefix + '0')
                               for b in subplans(prefix + '1'))


def push(triggers: tuple[str, ...], raw: tuple[int, ...]) -> tuple[int, ...]:
    mass = [0] * 8
    for word, weight in enumerate(raw):
        target = word
        text = f'{word:03b}'
        for depth in (1, 2, 3):
            if text[:depth] in triggers:
                target ^= 1 << (3 - depth)
                break
        mass[target] += weight
    return tuple(mass)


def model():
    raw = {k: raw_law(k) for k in (0, 1, 5, 6)}
    policies = tuple(a + b for a in subplans('0') for b in subplans('1'))
    sides = tuple(tuple(sorted({push(t, raw[k]) for t in policies for k in ks}))
                  for ks in ((0, 1), (5, 6)))
    p, q = sides
    check(len(policies) == 676 and len(p) == len(q) == 67, 'model size')
    check(q == tuple(sorted(r[::-1] for r in p)), 'reflection')
    for side, coords in ((p, LOW), (q, HIGH)):
        for i in coords:
            check(tuple(120 if j == i else 0 for j in range(8)) in side,
                  'missing extreme point mass')
    check(all(r[7] == 0 for r in p) and all(r[0] == 0 for r in q),
          'exclusive support coordinates')
    return raw, p, q


def dot(row, score):
    return sum(a * b for a, b in zip(row, score))


def backward(raw, score, maximize: bool):
    """A second expression: no policy list, recurse on true/output prefixes."""
    choose = max if maximize else min

    @lru_cache(None)
    def visit(truth: str, observed: str, spent: bool):
        if len(truth) == 3:
            return raw[int(truth, 2)] * score[int(observed, 2)]
        value = 0
        for bit in (0, 1):
            child = truth + str(bit)
            honest = visit(child, observed + str(bit), spent)
            value += honest if spent else choose(
                honest, visit(child, observed + str(1 - bit), True))
        return value
    return F(visit('', '', False), 120)


def bounds(p, q, numerator, denominator: int):
    return (F(min(dot(r, numerator) for r in p), 120 * denominator),
            F(max(dot(r, numerator) for r in q), 120 * denominator))


def mean_cost(p: F) -> F:
    """Classical exact Bernoulli cost; analytic justification is in the note."""
    if not isinstance(p, F) or not 0 <= p <= 1:
        raise ValueError('Fraction in [0,1] required')
    if p in (0, 1):
        return F(0)
    den = p.denominator
    return 2 - F(2, den) if den & (den - 1) == 0 else F(2)


def sample(p: F, next_bit: Callable[[], int]) -> tuple[int, int]:
    if not isinstance(p, F) or not 0 <= p <= 1:
        raise ValueError('Fraction in [0,1] required')
    num, den, used = p.numerator, p.denominator, 0
    while num not in (0, den):
        threshold, num = divmod(2 * num, den)
        bit = next_bit()
        if type(bit) is not int or bit not in (0, 1):
            raise ValueError('bit must be integer 0 or 1')
        used += 1
        if bit < threshold:
            return 1, used
        if bit > threshold:
            return 0, used
    return int(num == den), used


def grid_exclusion(p, q):
    count, maximum, checksum = 0, -10**9, 0
    # The proof reduces every potential positive D<=8 separator to these rows.
    for t in range(8):
        for high in product(range(t + 1), repeat=3):
            if max(high) != t:
                continue
            for low in product(range(t + 1, 9), repeat=3):
                z = (8, low[0], low[1], high[0], low[2], high[1], high[2], 0)
                gap = min(dot(r, z) for r in p) - max(dot(r, z) for r in q)
                check(gap <= 0, 'counterexample to D<=8 obstruction: ' + str(z))
                count += 1
                maximum = max(maximum, gap)
                checksum += gap
    check(count == 19188 and maximum == 0, 'grid coverage')
    return {'reduced_vectors': count, 'maximum_integer_gap': maximum,
            'integer_gap_sum': checksum, 'law_mass_denominator': 120}


def main():
    raw, p, q = model()
    # Exact legal witnesses for the analytic three-level argument.
    pb = push(('00', '010', '100'), raw[1])
    q1 = push(('1', '01'), raw[5])
    q2 = push(('01', '11', '101'), raw[5])
    expected = ((0, 0, 3, 2, 0, 1, 0, 0),
                (0, 2, 1, 3, 0, 0, 0, 0),
                (0, 1, 0, 0, 2, 3, 0, 0))
    check((pb, q1, q2) == tuple(tuple(20 * x for x in r) for r in expected),
          'three-level witness realization')
    difference = tuple(3 * a - 2 * b - c for a, b, c in zip(pb, q1, q2))
    check(all(difference[i] == 0 for i in HIGH)
          and sum(difference[i] for i in LOW) == 0, 'three-level identity')
    grid = grid_exclusion(p, q)
    maps = {
        'four_symbols': ((11, 11, 12, 0, 11, 0, 3, 0), 12, F(1,2), F(35,72)),
        'four_fair_bits': ((16, 12, 16, 1, 15, 0, 4, 0), 16, F(49,96), F(47,96)),
        'nine_uniform_tickets': ((9, 7, 9, 0, 8, 0, 2, 0), 9, F(13,27), F(25,54)),
        'central_map': ((21, 16, 21, 1, 20, 0, 5, 0), 21, F(65,126), F(61,126)),
    }
    results = {}
    for name, (z, den, wanted_c, wanted_s) in maps.items():
        c, s = bounds(p, q, z, den)
        check((c, s) == (wanted_c, wanted_s), 'attaining map: ' + name)
        scores = tuple(F(x, den) for x in z)
        check(c == min(backward(raw[k], scores, False) for k in (0, 1)),
              'safe backward comparison')
        check(s == max(backward(raw[k], scores, True) for k in (5, 6)),
              'unsafe backward comparison')
        results[name] = {'probabilities': list(map(str, scores)),
                         'C': str(c), 'S': str(s), 'margin': str(c - s)}
    g = tuple(F(x, 16) for x in maps['four_fair_bits'][0])
    executions = []
    for y, probability in enumerate(g):
        successes, total_cost, lengths = 0, 0, {}
        for tape in product((0, 1), repeat=4):
            bits = iter(tape)
            answer, used = sample(probability, lambda: next(bits))
            successes += answer
            total_cost += used
            lengths[used] = lengths.get(used, 0) + 1
        check(F(successes, 16) == probability, 'sampler probability')
        check(F(total_cost, 16) == mean_cost(probability), 'sampler mean')
        executions.append({'word': f'{y:03b}', 'probability': str(probability),
                           'mean_bits': str(F(total_cost, 16)),
                           'length_counts_out_of_16': lengths})
    check(max(mean_cost(v) for v in g) == F(15, 8), 'conditional mean threshold')
    # A valid sampler must reject invalid primitives and exhausted tapes.
    rejected = 0
    for value in (F(-1), F(2)):
        try:
            sample(value, lambda: 0)
        except ValueError:
            rejected += 1
    for value in (True, 2):
        try:
            sample(F(1,2), lambda: value)
        except ValueError:
            rejected += 1
    try:
        sample(F(1,16), lambda: next(iter(())))
    except StopIteration:
        rejected += 1
    check(rejected == 5, 'negative controls')
    print(json.dumps({
        'schema': 'causal-reporting-budget-finite-check-v1',
        'raw_laws_denominator_120': raw, 'causal_policies': 676,
        'distinct_safe_laws': len(p), 'distinct_unsafe_laws': len(q),
        'three_level_witnesses_denominator_6': expected,
        'grid_obstruction': grid, 'attaining_maps': results,
        'g16_finite_tape_executions': executions, 'rejected_inputs': rejected,
        'scope': 'Finite exact premises and sampler execution only. The note proves the all-history and infinite-tree claims. No empirical AI result or independent review.'
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
