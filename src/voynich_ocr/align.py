from collections import Counter

Column = list[int | None]

_DIAG, _SKIP, _INSERT, _WILD = 0, 1, 2, 3


def majority(readings: list) -> object:
    """Most frequent reading, a gap (None) included; ties go to the reading of the earliest source."""
    counts = Counter(readings)
    best = max(counts.values())
    return next(r for r in readings if counts[r] == best)


def _items(tokens: list[str], unknown: str) -> list[tuple[int, int]]:
    """(start, n) per alignment item; n > 0 is a single token, n < 0 a run of -n unknowns."""
    items = []
    i = 0
    while i < len(tokens):
        if tokens[i] != unknown:
            items.append((i, 1))
            i += 1
            continue
        j = i
        while j < len(tokens) and tokens[j] == unknown:
            j += 1
        items.append((i, -(j - i)))
        i = j
    return items


def _add(columns: list[Column], sequences: list[list[str]], s: int, unknown: str) -> None:
    tokens = sequences[s]
    items = _items(tokens, unknown)
    maj = [majority([sequences[t][c] if c is not None else None for t, c in enumerate(col[:s])]) for col in columns]
    skip_cost = [0 if m is None else 1 for m in maj]
    n_cols, n_items = len(columns), len(items)
    inf = float("inf")
    cost = [[inf] * (n_cols + 1) for _ in range(n_items + 1)]
    cost[0][0] = 0
    for j in range(1, n_cols + 1):
        cost[0][j] = cost[0][j - 1] + skip_cost[j - 1]
    for i in range(1, n_items + 1):
        start, n = items[i - 1]
        row, prev = cost[i], cost[i - 1]
        for j in range(n_cols + 1):
            best = row[j - 1] + skip_cost[j - 1] if j else inf
            if n > 0:
                if j:
                    best = min(best, prev[j - 1] + (tokens[start] != maj[j - 1]))
                best = min(best, prev[j] + 1)
            else:
                for k in range(min(-n, j) + 1):
                    best = min(best, prev[j - k])
            row[j] = best

    # Walk back from the end preferring a diagonal step, so gaps land leftmost; a wildcard prefers to cover
    # as many columns as it can.
    ops: list[tuple[int, int]] = []
    i, j = n_items, n_cols
    while i or j:
        start, n = items[i - 1] if i else (0, 0)
        here = cost[i][j]
        if i and n > 0 and j and here == cost[i - 1][j - 1] + (tokens[start] != maj[j - 1]):
            ops.append((_DIAG, 1))
            i, j = i - 1, j - 1
            continue
        if i and n < 0:
            k = next((k for k in range(min(-n, j), 0, -1) if here == cost[i - 1][j - k]), 0)
            if k:
                ops.append((_WILD, k))
                i, j = i - 1, j - k
                continue
        if j and here == cost[i][j - 1] + skip_cost[j - 1]:
            ops.append((_SKIP, 1))
            j -= 1
        elif i and n > 0 and here == cost[i - 1][j] + 1:
            ops.append((_INSERT, 1))
            i -= 1
        elif i and n < 0 and here == cost[i - 1][j]:
            ops.append((_WILD, 0))
            i -= 1
        else:
            raise AssertionError(f"no traceback step at ({i}, {j})")
    ops.reverse()

    out: list[Column] = []
    j = 0
    item = 0
    for op, k in ops:
        start, n = items[item] if item < n_items else (0, 0)
        if op == _DIAG:
            out.append(columns[j] + [start])
            j, item = j + 1, item + 1
        elif op == _SKIP:
            out.append(columns[j] + [None])
            j += 1
        elif op == _INSERT:
            out.append([None] * s + [start])
            item += 1
        else:
            out.extend(columns[j + d] + [start + d] for d in range(k))
            j, item = j + k, item + 1
    columns[:] = out


def align(sequences: list[list[str]], unknown: str) -> list[Column]:
    """Progressive alignment in the given source order: each sequence against the column majority of those
    before it, at unit cost. A run of n `unknown` tokens is one wildcard that covers 0..n columns at no cost;
    tokens of a run beyond the columns it covers are left out.

    Returns columns; `column[s]` is an index into `sequences[s]`, or None for a gap.
    """
    columns: list[Column] = [[i] for i in range(len(sequences[0]))] if sequences else []
    for s in range(1, len(sequences)):
        _add(columns, sequences, s, unknown)
    return columns
