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


def _logical_lines(text, describe):
    """Yield (first_physical_lineno, logical_line) with POSIX backslash-newline
    continuations joined.

    A trailing run of backslashes continues the line iff its length is odd (an
    even run is escaped backslashes, not a continuation). A comment line cannot
    start a continuation: to the shell its trailing backslash is comment text.
    The D56 submit script is the first committed Slurm job to use continuations;
    line-by-line shlex previously died on them with an opaque collection error
    ("No escaped character"), so this reader exists to keep the guard covering
    continued invocations instead of crashing on them.
    """
    pending_first = None
    pending_text = None
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if pending_text is None and raw.lstrip().startswith("#"):
            yield lineno, raw
            continue
        first = lineno if pending_first is None else pending_first
        accumulated = raw if pending_text is None else pending_text + raw
        trailing = len(raw) - len(raw.rstrip("\\"))
        if trailing % 2 == 1:
            pending_first, pending_text = first, accumulated[:-1]
            continue
        pending_first = pending_text = None
        yield first, accumulated
    if pending_text is not None:
        raise ValueError(
            f"{describe}:{pending_first}: dangling backslash continuation at "
            "end of file")


def _file_invocations(slurm_path):
    """Return every direct Python-script invocation in one Slurm file."""
    invocations = []
    for lineno, line in _logical_lines(slurm_path.read_text(), slurm_path.name):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                tokens = shlex.split(stripped, comments=True)
            except ValueError as error:
                raise ValueError(
                    f"{slurm_path.name}:{lineno}: {error}") from error
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


def _slurm_invocations():
    """Return every direct Python-script invocation in every Slurm file."""
    invocations = []
    for slurm_path in sorted(EXPERIMENTS_DIR.glob("*.slurm")):
        invocations.extend(_file_invocations(slurm_path))
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


def _write_synthetic_slurm(tmp_path, text):
    path = tmp_path / "job_synthetic.slurm"
    path.write_text(text)
    return path


def test_continued_invocation_is_one_invocation_with_all_flags(tmp_path):
    """Flags on backslash-continuation lines belong to the same invocation."""
    path = _write_synthetic_slurm(
        tmp_path,
        "python experiments/foo.py \\\n"
        "    --alpha 1 \\\n"
        "    --beta 2\n",
    )
    invocations = _file_invocations(path)
    assert len(invocations) == 1
    _, lineno, _, script_token, arguments = invocations[0].values
    assert lineno == 1
    assert script_token == "experiments/foo.py"
    assert [token for token in arguments if token.startswith("--")] == [
        "--alpha", "--beta"]


def test_one_line_invocations_are_unchanged(tmp_path):
    path = _write_synthetic_slurm(
        tmp_path, "echo start\npython experiments/foo.py --gamma 3\n")
    invocations = _file_invocations(path)
    assert len(invocations) == 1
    _, lineno, _, script_token, arguments = invocations[0].values
    assert lineno == 2
    assert script_token == "experiments/foo.py"
    assert arguments == ["--gamma", "3"]


def test_dangling_continuation_reports_file_and_line(tmp_path):
    """A dangling continuation must not surface as an opaque shlex error."""
    path = _write_synthetic_slurm(
        tmp_path, "echo ok\npython experiments/foo.py \\\n")
    with pytest.raises(ValueError, match=(
            r"job_synthetic\.slurm:2: dangling backslash continuation")):
        _file_invocations(path)


def test_comment_lines_do_not_start_continuations(tmp_path):
    """To the shell a trailing backslash on a comment line is comment text."""
    path = _write_synthetic_slurm(
        tmp_path,
        "# a comment that ends with a backslash \\\n"
        "python experiments/foo.py --delta 4\n",
    )
    invocations = _file_invocations(path)
    assert len(invocations) == 1
    assert invocations[0].values[1] == 2


def test_d56_submit_script_invocation_flags_are_exact():
    """The D56 continued invocation is discovered with exactly its three flags,
    so the argparse cross-check genuinely covers it (it previously either
    crashed collection or, with a naive fix, would have seen no flags at all).
    """
    params = [
        param for param in _slurm_invocations()
        if param.values[0].name == "submit_d19_a7_bench.slurm"
    ]
    assert len(params) == 1
    _, _, _, script_token, arguments = params[0].values
    assert script_token == "experiments/d19_bench.py"
    passed_options = {
        token.split("=", maxsplit=1)[0]
        for token in arguments
        if token.startswith("--")
    }
    assert passed_options == {"--scale", "--threads", "--budget-s"}
