"""Guard Slurm Python flags against the argparse interfaces they invoke.

Mauna Loa experiment execution requires remote Slurm resources and is too
expensive for CI. A stale flag set therefore would otherwise remain hidden
until submission and crash the job. This source-level M2a guard discovers the
Slurm jobs, parses their Python targets, and checks option compatibility as
recorded in plan-d19-mauna.md section 0.
"""

import ast
import shlex
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS_DIR = REPO_ROOT / "experiments"


def _is_python_interpreter(token):
    """Match python/python3/python3.x, bare or path-prefixed."""
    name = Path(token).name
    return name == "python" or name.startswith("python3")


def _slurm_invocations():
    """Return every direct Python-script invocation in every Slurm file."""
    invocations = []
    for slurm_path in sorted(EXPERIMENTS_DIR.glob("*.slurm")):
        for lineno, line in enumerate(slurm_path.read_text().splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            tokens = shlex.split(stripped, comments=True)
            for index, token in enumerate(tokens[:-1]):
                if not _is_python_interpreter(token):
                    continue
                # Skip interpreter options (python -u, -O, ...) between the
                # interpreter and the script token, so an option-carrying
                # invocation stays covered instead of silently dropping out.
                script_index = index + 1
                while (script_index < len(tokens)
                       and tokens[script_index].startswith("-")):
                    script_index += 1
                if script_index >= len(tokens):
                    continue
                if tokens[script_index].endswith(".py"):
                    invocations.append(
                        pytest.param(
                            slurm_path,
                            lineno,
                            stripped,
                            tokens[script_index],
                            tokens[script_index + 1:],
                            id=f"{slurm_path.name}:{lineno}-{tokens[script_index]}",
                        )
                    )
                    break
    return invocations


def _script_path(script_token):
    """Resolve bare and experiments-prefixed script paths from a Slurm job."""
    path = Path(script_token)
    if path.parts and path.parts[0] == "experiments":
        return REPO_ROOT / path
    return EXPERIMENTS_DIR / path


def _argparse_options(script_path):
    """Collect declared option strings from source without executing it."""
    tree = ast.parse(script_path.read_text(), filename=str(script_path))
    options = set()
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
        ):
            continue
        options.update(
            arg.value
            for arg in node.args
            if isinstance(arg, ast.Constant)
            and isinstance(arg.value, str)
            and arg.value.startswith("-")
        )
    return options


@pytest.mark.parametrize(
    "slurm_path,lineno,invocation,script_token,arguments", _slurm_invocations()
)
def test_slurm_flags_match_target_argparse(
    slurm_path, lineno, invocation, script_token, arguments
):
    script_path = _script_path(script_token)
    declared_options = _argparse_options(script_path)
    passed_options = {
        token.split("=", maxsplit=1)[0]
        for token in arguments
        if token.startswith("--")
    }
    stale_options = sorted(passed_options - declared_options)

    assert not stale_options, (
        f"{slurm_path.name}:{lineno}: {invocation!r} passes undeclared argparse "
        f"option(s) {stale_options} to {script_token}. A stale flag set crashes "
        "on submission; see the M2a refresh rationale in "
        "plan-d19-mauna.md section 0."
    )


def test_every_slurm_file_has_a_recognized_invocation():
    """Coverage guard for the guard: a job rewritten to an unrecognized
    launcher form would silently drop out of the parametrization above and
    its flags would go unchecked. Every Slurm file must contribute at least
    one recognized python invocation (M2a review round, finding 8)."""
    covered = {param.values[0] for param in _slurm_invocations()}
    all_slurm = set(EXPERIMENTS_DIR.glob("*.slurm"))
    assert all_slurm, "no Slurm files found under experiments/"
    uncovered = sorted(p.name for p in all_slurm - covered)
    assert not uncovered, (
        f"Slurm file(s) with no recognized python invocation: {uncovered}; "
        "extend _is_python_interpreter/_slurm_invocations rather than losing "
        "flag coverage")
