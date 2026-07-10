"""
Static regression guard for the D8 Mauna Loa fresh-HMC pattern.

The Mauna noise posterior concentrates near zero, so a fresh fit_hmc run
needs two sampler-efficiency knobs (DECISIONS D8): MAP-fit the SAME model
instance that is passed to fit_hmc (init_to_map reads the model's current
values, so fitting a different throwaway model is a silent no-op), and cap
the NUTS tree depth at 7 (uncapped depth-10 trees are intractable in the
stiff near-zero-noise region). bms_star_mauna_loa.py and mauna_loa.py were
fixed with D8; bistar_debias_mauna_loa.py kept the stale pattern until the
2026-07-08 cleanup chip. Executing these scripts is far too expensive for
CI, so the guard is source-level: parse each script and check both knobs.

Name matching alone is escapable (a fit_map in a mutually exclusive branch,
or a rebinding of the model name between fit_map and fit_hmc, reproduces
the historical fit-one-sample-another bug while satisfying a naive check),
so the guard requires the matching fit_map to be a SIBLING statement in the
same block as the fit_hmc call, with none of the four tracked names rebound
between them.
"""

import ast
from pathlib import Path

import pytest

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"

MAUNA_HMC_SCRIPTS = [
    "bistar_debias_mauna_loa.py",
    "bms_star_mauna_loa.py",
    "mauna_loa.py",
]


def _named_calls(root, func_name):
    """All Call nodes under `root` invoking a bare name `func_name`."""
    return [
        node
        for node in ast.walk(root)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == func_name
    ]


def _leading_arg_names(call, n=4):
    """Names of the first n positional args, or None if any is not a bare name."""
    if len(call.args) < n:
        return None
    names = []
    for arg in call.args[:n]:
        if not isinstance(arg, ast.Name):
            return None
        names.append(arg.id)
    return names


def _enclosing_block(tree, target):
    """(statement_list, index) of the innermost statement holding `target`.

    Among all statements that contain the target node, the innermost is the
    one with the fewest descendants (containing statements are nested).
    """
    best = None
    for node in ast.walk(tree):
        for _field, value in ast.iter_fields(node):
            if not isinstance(value, list):
                continue
            for i, stmt in enumerate(value):
                if not isinstance(stmt, ast.stmt):
                    continue
                if any(sub is target for sub in ast.walk(stmt)):
                    size = sum(1 for _ in ast.walk(stmt))
                    if best is None or size < best[2]:
                        best = (value, i, size)
    assert best is not None, "target node not found in any statement list"
    return best[0], best[1]


def _bound_names(stmt):
    """Every name (re)bound anywhere inside `stmt`."""
    names = set()
    for node in ast.walk(stmt):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            targets = [node.target]
        elif isinstance(node, ast.For):
            targets = [node.target]
        else:
            continue
        for target in targets:
            for sub in ast.walk(target):
                if isinstance(sub, ast.Name):
                    names.add(sub.id)
    return names


@pytest.mark.parametrize("script", MAUNA_HMC_SCRIPTS)
def test_fresh_hmc_follows_d8_pattern(script):
    source = (EXPERIMENTS_DIR / script).read_text()
    tree = ast.parse(source, filename=script)

    hmc_calls = _named_calls(tree, "fit_hmc")
    assert len(hmc_calls) == 1, (
        f"{script}: expected exactly one fit_hmc call, found {len(hmc_calls)}"
    )
    hmc = hmc_calls[0]

    # Knob 1: NUTS tree depth capped at 7.
    keywords = {kw.arg: kw.value for kw in hmc.keywords}
    assert "max_tree_depth" in keywords, (
        f"{script}:{hmc.lineno}: fit_hmc has no max_tree_depth — uncapped "
        f"depth-10 NUTS is intractable on Mauna Loa (D8)"
    )
    depth = keywords["max_tree_depth"]
    assert isinstance(depth, ast.Constant) and depth.value == 7, (
        f"{script}:{hmc.lineno}: max_tree_depth must be the literal 7 (D8)"
    )

    # Knob 2: the exact (model, likelihood, x, y) passed to fit_hmc is
    # MAP-fitted first, unconditionally, in the same block, with no rebinding
    # of any of the four names in between — so init_to_map reads the fitted
    # instance, not a fresh default one.
    hmc_args = _leading_arg_names(hmc)
    assert hmc_args is not None, (
        f"{script}:{hmc.lineno}: fit_hmc's first four args must be bare names "
        f"for this guard to track them"
    )
    block, hmc_index = _enclosing_block(tree, hmc)

    def _valid_map_fit(call):
        if _leading_arg_names(call) != hmc_args:
            return False
        map_block, map_index = _enclosing_block(tree, call)
        if map_block is not block or map_index >= hmc_index:
            return False
        rebound = set()
        for k in range(map_index + 1, hmc_index):
            rebound |= _bound_names(block[k])
        return not (rebound & set(hmc_args))

    assert any(_valid_map_fit(c) for c in _named_calls(tree, "fit_map")), (
        f"{script}:{hmc.lineno}: no unconditional sibling "
        f"fit_map({', '.join(hmc_args)}, ...) before fit_hmc without a "
        f"rebinding in between — init_to_map would start from default "
        f"hyperparameters (D8)"
    )
