"""Shared, preregistered infrastructure for the M2bR run drivers.

Importing this module never starts a sampler.  Every sampling boundary accepts
an injected ``sampler_fn``; the production default is ``fit_hmc_e1`` and the
dry-run/test default is the deterministic mock defined below.
"""

from __future__ import annotations

import hashlib
import json
import math
import multiprocessing as mp
import os
import platform
import socket
import struct
import subprocess
import time
from dataclasses import dataclass
from queue import Empty
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import torch

# The historical experiment is a script rather than a package module.  Put its
# directory on sys.path so STUDY_CONFIGS is imported from the authoritative
# implementation, rather than copied into a third configuration registry.
import sys

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))

from prior_sensitivity_study import (  # noqa: E402
    NOISE_SPLIT_HI,
    NOISE_SPLIT_LO,
    STUDY_CONFIGS,
)
from fit_method_metric_comparison import (  # noqa: E402
    METRICS,
    SEED,
    TAUS,
    crude_ess,
)

from bistar_gp import build_model, generate_toy_data  # noqa: E402
from bistar_gp.bms_star import extract_gp_predictives, run_bms_star  # noqa: E402
from bistar_gp.candidates import build_toy_candidates  # noqa: E402
from bistar_gp.config import (  # noqa: E402
    build_kernels_from_config,
    build_likelihood_from_config,
)
from bistar_gp.e1_potential import fit_hmc_e1  # noqa: E402
from bistar_gp.sampler_diagnostics import SamplerDiagnostics  # noqa: E402

torch.set_default_dtype(torch.float64)

SITE_NAMES = (
    "covar_module.kernels.0.base_kernel.lengthscale_prior",
    "covar_module.kernels.0.outputscale_prior",
    "covar_module.kernels.1.variance_prior",
    "likelihood.noise_covar.noise_prior",
)
NOISE_SITE = "likelihood.noise_covar.noise_prior"
PROJECTIONS = {7: 865.0, 10: 1362.0}
FREEZE_PATH = REPO_ROOT / "docs" / "m2br_freeze" / "start_freeze_v1.14.json"
EXPECTED_MANIFEST_SHA256 = (
    "b1abfa3c244a03f3ce3b5a69782157aad087e01de8b15a9a332de6ab2643d891"
)
# Backward-compatible name used by the emitted run-plan schema.
FREEZE_SHA256 = EXPECTED_MANIFEST_SHA256


def build_cell_model(config: str, x=None, y=None):
    """Build a fresh toy model exactly as ``run_one_method`` lines 128-130."""
    if config not in STUDY_CONFIGS:
        raise KeyError(f"unknown M2bR config {config!r}")
    if x is None or y is None:
        if x is not None or y is not None:
            raise ValueError("x and y must either both be supplied or both omitted")
        x, y, _ = generate_toy_data()
    prior_config = STUDY_CONFIGS[config]
    kernels, names = build_kernels_from_config(prior_config)
    likelihood = build_likelihood_from_config(prior_config)
    model, likelihood = build_model(x, y, kernels, names, likelihood)
    model._m2br_prior_config = prior_config
    model._m2br_config_object = prior_config
    return model, likelihood, x, y


@lru_cache(maxsize=1)
def toy_scoring_context():
    """Generate the frozen toy data and fit each toy candidate exactly once."""
    x, y, info = generate_toy_data()
    x_np, y_np = x.numpy(), y.numpy()
    x_eval = np.linspace(x_np.min() - 1, x_np.max() + 1, 60)
    x_eval_torch = torch.tensor(x_eval).double()
    candidate_results = []
    for candidate in build_toy_candidates():
        candidate.fit(x_np, y_np)
        candidate_results.append(candidate.predict(x_eval))
    return x, y, info, x_eval_torch, candidate_results


def _site_summaries(samples: Mapping[str, np.ndarray]) -> dict[str, dict]:
    summaries = {}
    for site, values in samples.items():
        draws = np.asarray(values, dtype=float).reshape(-1)
        if not len(draws):
            raise ValueError(f"sample site {site!r} has no draws")
        q05, q50, q95 = np.quantile(draws, [0.05, 0.5, 0.95])
        summaries[site] = {
            "n": int(len(draws)),
            "mean": float(draws.mean()),
            "sd": float(draws.std()),
            "q05": float(q05),
            "q50": float(q50),
            "q95": float(q95),
            "crude_ess": float(crude_ess(draws)),
        }
    return summaries


def serialize_bms_results(results: Mapping[str, Mapping[float, Any]]) -> dict:
    """Convert BMSStarResult objects to strict-JSON-compatible structures."""
    out = {}
    for metric in METRICS:
        by_tau = results[metric]
        first = by_tau[TAUS[0]]
        g_matrix = np.asarray(first.G_matrix, dtype=float)
        winners = np.argmin(g_matrix, axis=1)
        out[metric] = {
            "instance_posteriors": {
                str(tau): np.asarray(by_tau[tau].instance_posteriors, dtype=float).tolist()
                for tau in TAUS
            },
            "G_matrix": g_matrix.tolist(),
            "hard_win_fractions": [
                float(np.mean(winners == j)) for j in range(g_matrix.shape[1])
            ],
        }
    return out


def score_samples(samples, model, likelihood, x, y, x_eval_torch,
                  candidate_results, n_predictives=200,
                  expected_predictives=200):
    """Run the frozen D12/D18 predictive extraction and BMS* scoring path."""
    prior_config = getattr(model, "_m2br_prior_config", None)
    if prior_config is None:
        # Drivers stamp the key; for direct callers infer the matching object.
        matches = [pc for pc in STUDY_CONFIGS.values()
                   if pc is getattr(model, "_m2br_config_object", None)]
        if matches:
            prior_config = matches[0]
        else:
            raise ValueError("model lacks its M2bR prior configuration stamp")

    np.random.seed(SEED)
    gp_samples = extract_gp_predictives(
        model, likelihood, x, y, x_eval_torch, samples,
        kernel_builder=lambda: build_kernels_from_config(prior_config),
        likelihood_builder=lambda: build_likelihood_from_config(prior_config),
        n_posterior_samples=n_predictives,
        jitter=1e-4,
    )
    if not gp_samples:
        raise RuntimeError("no valid GP predictives extracted")
    if len(gp_samples) != int(expected_predictives):
        raise ValueError(
            "predictive cardinality mismatch: "
            f"expected {expected_predictives}, extracted {len(gp_samples)}")
    bms = run_bms_star(gp_samples, candidate_results, METRICS, np.array(TAUS))
    return {
        "gp_samples": gp_samples,
        "n_predictives": len(gp_samples),
        "metrics": serialize_bms_results(bms),
        "site_summaries": _site_summaries(samples),
    }


def stamp_model_config(model, config: str):
    """Attach the exact STUDY_CONFIGS object needed by predictive builders."""
    model._m2br_prior_config = STUDY_CONFIGS[config]
    model._m2br_config_object = STUDY_CONFIGS[config]
    return model


def basin_occupancy(noise_draws) -> dict[str, float | int]:
    noise = np.asarray(noise_draws, dtype=float).reshape(-1)
    return {
        "P_lo": float(np.mean(noise < NOISE_SPLIT_LO)),
        "P_mid": float(np.mean((noise >= NOISE_SPLIT_LO) &
                               (noise <= NOISE_SPLIT_HI))),
        "P_hi": float(np.mean(noise > NOISE_SPLIT_HI)),
        "n": int(noise.size),
    }


def diagnostics_payload(diag: SamplerDiagnostics) -> dict:
    payload = diag.to_dict()
    payload.update({
        "n_divergences": (list(diag.n_divergences)
                          if diag.n_divergences is not None else None),
        "divergence_rate": diag.divergence_rate,
        "tree_depths": ([list(c) for c in diag.tree_depths]
                        if diag.tree_depths is not None else None),
        "depth_saturation_rate": diag.depth_saturation_rate,
        "notpsd_post_warmup_total": diag.notpsd_post_warmup_total,
        "notpsd_post_warmup_rate": diag.notpsd_post_warmup_rate,
    })
    return payload


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def semantic_array_bytes(name: str, values) -> bytes:
    arr = np.asarray(values, dtype="<f8", order="C")
    dims = np.asarray(arr.shape, dtype="<i8").tobytes(order="C")
    return (name.encode("utf-8") + b"\x00" + struct.pack("<I", arr.ndim)
            + dims + arr.tobytes(order="C"))


def sample_arrays_sha256(samples: Mapping[str, np.ndarray]) -> str:
    return sha256_bytes(b"".join(
        semantic_array_bytes(site, samples[site]) for site in sorted(samples)))


def sample_array_hashes(samples: Mapping[str, np.ndarray]) -> dict[str, str]:
    return {site: sha256_bytes(semantic_array_bytes(site, values))
            for site, values in sorted(samples.items())}


def canonical_start_sha256(values: Mapping[str, Any]) -> str:
    return sample_arrays_sha256(values)


def env_provenance() -> dict:
    def version(name):
        try:
            module = __import__(name)
            return getattr(module, "__version__", None)
        except Exception:
            return None

    try:
        git_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
            text=True, capture_output=True, check=True).stdout.strip()
    except Exception:
        git_sha = None
    return {
        "git_sha": git_sha,
        "versions": {name: version(name)
                     for name in ("torch", "gpytorch", "pyro", "arviz", "numpy")},
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "torch_thread_count": int(torch.get_num_threads()),
        "cpu_count": os.cpu_count(),
    }


def pin_execution_environment(threads=None):
    """Pin and record the compute environment before a real --execute run.

    The frozen leapfrog projections (865 s td7 / 1362 s td10) were calibrated on
    this 14-core Mac at 10 PyTorch intra-op threads; pinning keeps them valid and
    makes the run reproducible. ``threads`` defaults to 10 (or the
    ``M2BR_TORCH_THREADS`` env override). intra-op threads are pinned; inter-op is
    best effort (settable only before parallel work starts). Returns a record for
    the run report; also captures the BLAS thread-count environment variables."""
    requested = int(os.environ.get(
        "M2BR_TORCH_THREADS", threads if threads is not None else 10))
    try:
        torch.set_num_threads(requested)
    except Exception:
        pass
    interop_pinned = True
    try:
        torch.set_num_interop_threads(requested)
    except Exception:
        interop_pinned = False
    blas_keys = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                 "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")
    return {
        "requested_torch_threads": requested,
        "torch_num_threads": int(torch.get_num_threads()),
        "torch_num_interop_threads": int(torch.get_num_interop_threads()),
        "interop_pinned": interop_pinned,
        "blas_env": {key: os.environ.get(key) for key in blas_keys},
        "cpu_count": os.cpu_count(),
        "benchmark_reference": {"torch_threads": 10, "cpu_count": 14},
    }


def require_absent(path) -> Path:
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite completed artifact: {path}")
    return path


def _atomic_replace(path: Path, writer: Callable[[Any], None], mode: str):
    require_absent(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + f".tmp-{os.getpid()}")
    if tmp.exists():
        raise FileExistsError(f"stale atomic temporary exists: {tmp}")
    try:
        with open(tmp, mode) as handle:
            writer(handle)
            handle.flush()
            os.fsync(handle.fileno())
        # Recheck immediately before replace so even a racing completed file
        # is never overwritten.
        require_absent(path)
        os.replace(tmp, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
    except BaseException:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise
    return path


def atomic_write_json(path, obj):
    return _atomic_replace(
        Path(path),
        lambda handle: json.dump(obj, handle, indent=2, sort_keys=True,
                                 allow_nan=False),
        "w",
    )


def atomic_save_npz(path, **arrays):
    return _atomic_replace(
        Path(path), lambda handle: np.savez(handle, **arrays), "wb")


def _stage_artifact(path: Path, writer: Callable[[Any], None], mode: str):
    """Write and fsync one transaction member without making it consumable."""
    require_absent(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + f".tmp-{os.getpid()}")
    if tmp.exists():
        raise FileExistsError(f"stale atomic temporary exists: {tmp}")
    try:
        with open(tmp, mode) as handle:
            writer(handle)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise
    return tmp


def transactional_persist(*, json_artifacts=None, npz_artifacts=None,
                          samples_path):
    """Stage a run's artifacts, committing its sample cache strictly last.

    This is the transaction boundary used by both M2bR drivers.  Sidecars may
    become visible if a later rename fails, but a consumable sample cache can
    only appear after every other member has been successfully staged and
    renamed.
    """
    json_artifacts = list((json_artifacts or {}).items())
    npz_artifacts = list((npz_artifacts or {}).items())
    samples_path = Path(samples_path)
    all_paths = [Path(path) for path, _ in json_artifacts + npz_artifacts]
    if samples_path not in all_paths:
        raise ValueError("samples_path must name one staged NPZ artifact")
    if len(set(all_paths)) != len(all_paths):
        raise ValueError("transaction artifact paths must be unique")

    staged = {}
    try:
        for path, obj in json_artifacts:
            path = Path(path)
            staged[path] = _stage_artifact(
                path,
                lambda handle, value=obj: json.dump(
                    value, handle, indent=2, sort_keys=True, allow_nan=False),
                "w",
            )
        for path, arrays in npz_artifacts:
            path = Path(path)
            staged[path] = _stage_artifact(
                path,
                lambda handle, value=arrays: np.savez(handle, **value),
                "wb",
            )

        commit_order = [path for path in all_paths if path != samples_path]
        commit_order.append(samples_path)
        for path in commit_order:
            require_absent(path)
            os.replace(staged[path], path)
            staged.pop(path)
        try:
            directory_fd = os.open(samples_path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
    finally:
        for tmp in staged.values():
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass
    return all_paths


def _timestamp_or_none():
    try:
        return datetime.now(timezone.utc).isoformat()
    except Exception:
        return None


def persist_failure(path, run_id, exc, diagnostics=None):
    diag = diagnostics if diagnostics is not None else getattr(exc, "diagnostics", None)
    payload = {
        "status": "failed",
        "run_id": run_id,
        "exception": {"type": type(exc).__name__, "message": str(exc)},
        "timestamp": _timestamp_or_none(),
        "diagnostics": diagnostics_payload(diag) if diag is not None else None,
    }
    atomic_write_json(path, payload)
    return payload


@dataclass
class Deadline:
    ceiling_seconds: float
    reserve_seconds: float = 600.0
    clock: Callable[[], float] = time.monotonic
    t0: float | None = None

    def start(self):
        if self.t0 is not None:
            raise RuntimeError("deadline already started")
        self.t0 = float(self.clock())
        return self.t0

    def _require_started(self):
        if self.t0 is None:
            raise RuntimeError("deadline has not started")

    def remaining(self):
        self._require_started()
        return max(0.0, self.t0 + self.ceiling_seconds - float(self.clock()))

    def sampling_cutoff(self):
        self._require_started()
        return self.t0 + self.ceiling_seconds - self.reserve_seconds

    def may_start(self, run, projection_seconds):
        del run  # carried for readable callers and audit logs
        self._require_started()
        to_cutoff = self.sampling_cutoff() - float(self.clock())
        return to_cutoff >= float(projection_seconds)

    def run_isolated(self, fn, projection, hard_cutoff, **kwargs):
        return run_isolated(fn, projection, hard_cutoff,
                            clock=self.clock, **kwargs)


def _isolated_target(fn, queue):
    try:
        queue.put(("completed", fn()))
    except BaseException as exc:  # preserve technical failure data if picklable
        diag = getattr(exc, "diagnostics", None)
        queue.put(("failed", {
            "type": type(exc).__name__,
            "message": str(exc),
            "diagnostics": diagnostics_payload(diag) if diag is not None else None,
        }))


def _close_queue(queue):
    try:
        queue.close()
        queue.join_thread()
    except Exception:
        pass


def _terminate(process, termination_grace):
    process.terminate()
    process.join(max(0.0, float(termination_grace)))
    if process.is_alive():
        process.kill()
        process.join(max(0.0, float(termination_grace)))


# Module-level self-test targets (picklable under 'spawn') used only by the
# hermetic isolation tests -- never by any run path.
def _selftest_return(payload):
    return payload


def _selftest_raise(message):
    raise RuntimeError(message)


def _selftest_sleep(seconds):
    time.sleep(seconds)
    return {"slept": seconds}


def _selftest_ignore_sigterm(seconds):
    import signal
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    time.sleep(seconds)
    return {"slept": seconds}


def _selftest_pin_and_report_threads():
    # Confirms the in-child pin governs a spawned process (fix 5).
    pin_execution_environment()
    return torch.get_num_threads()


def run_isolated(fn, projection, hard_cutoff, *, clock=time.monotonic,
                 failure_path=None, run_id=None, termination_grace=1.0):
    """Execute ``fn`` in a child process and enforce the common absolute cutoff.

    Uses the 'spawn' start method -- forking a multi-threaded PyTorch parent is
    unsafe on macOS -- and waits for the child's result with a bounded
    ``queue.get(timeout=...)`` whose timeout IS the remaining time to the
    absolute cutoff. ``Queue.empty()`` is documented unreliable and is not used.
    ``fn`` and its arguments must be picklable (module-level callables); the
    audit run closure and the mock sampler both are."""
    del projection  # projection gates starts; the absolute cutoff gates runtime
    context = mp.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=_isolated_target, args=(fn, queue))
    try:
        # spawn pickles the target here; an unpicklable target raises now.
        process.start()
    except BaseException:
        _close_queue(queue)
        raise
    remaining = max(0.0, float(hard_cutoff) - float(clock()))
    try:
        status, value = queue.get(timeout=remaining)
    except Empty:
        # Absolute cutoff reached with no result: terminate, then kill.
        _terminate(process, termination_grace)
        _close_queue(queue)
        if failure_path is not None:
            atomic_write_json(failure_path, {
                "status": "timed_out",
                "run_id": run_id,
                "reason": "absolute_cutoff",
                "exception": {
                    "type": "TimeoutError",
                    "message": f"absolute M2bR cutoff reached for {run_id}",
                },
                "timestamp": _timestamp_or_none(),
            })
        return {"status": "timed_out", "run_id": run_id}
    # Result received; let the child exit cleanly, then release queue resources.
    process.join(max(0.0, float(termination_grace)))
    if process.is_alive():
        _terminate(process, termination_grace)
    _close_queue(queue)
    if status == "completed":
        return {"status": status, "run_id": run_id, "value": value}
    result = {"status": "failed", "run_id": run_id, "error": value}
    if failure_path is not None:
        error = RuntimeError(value["message"])
        if value.get("diagnostics") is not None:
            error.diagnostics = SamplerDiagnostics.from_dict(value["diagnostics"])
        persist_failure(failure_path, run_id, error)
    return result


def deterministic_mock_sampler(model, likelihood, x, y, **kwargs):
    """Hermetic four-site sampler substitute used only by dry-runs/tests."""
    del model, likelihood, x, y
    n = int(kwargs.get("n_samples", 2000))
    seed = int(kwargs.get("seed", 0) or 0)
    rng = np.random.default_rng(seed)
    centers = (2.0, 1.0, 0.08, 0.22)
    samples = {
        site: np.maximum(1e-6, center + rng.normal(0.0, center * 0.02, n))
        for site, center in zip(SITE_NAMES, centers)
    }
    depth = int(kwargs.get("max_tree_depth", 7))
    diagnostics = SamplerDiagnostics(
        sampler="m2br_mock",
        n_chains=1,
        n_draws=n,
        n_warmup=int(kwargs.get("n_warmup", 1000)),
        site_names=SITE_NAMES,
        max_tree_depth=depth,
        step_size=0.1,
        divergence_draws=((),),
        acceptance_rate=(0.9,),
        leapfrog_counts=(tuple([3] * n),),
        notpsd_rejections=0,
        notpsd_rejections_warmup=0,
        notpsd_rejections_per_draw=(tuple([0] * n),),
        unavailable=(),
    )
    return (samples, diagnostics) if kwargs.get("return_diagnostics") else samples


# --- Fail-closed sampler capability gate (D35) --------------------------------
# The historical gate keyed on ``sampler_fn is fit_hmc_e1`` -- fail-OPEN: any
# callable that was not that exact object (e.g. ``partial(fit_hmc_e1)``) ran
# without authorization. This inverts it to fail-CLOSED: ONLY samplers explicitly
# registered as safe mocks may run without ``authorized=True``; the real sampler
# and every unrecognized callable are gated. Behaviour for the two intended
# entrypoints is unchanged: real HMC still requires authorization, and the
# registered ``deterministic_mock_sampler`` (dry-run) still runs ungated.
#
# The "registration" is a marker attribute ON THE FUNCTION OBJECT, not a
# module-level set: the drivers import this module bare (``m2br_run_common``)
# while tests import it as ``experiments.m2br_run_common``, so a module-level
# registry would be duplicated and never agree. A per-object attribute travels
# with the callable regardless of which module copy inspects it.
#
# SPAWN NOTE: a mock that must survive an isolated (``spawn``) run has to be
# registered at IMPORT time -- like ``deterministic_mock_sampler`` below -- so the
# re-imported child object carries the marker. Functions pickle by module/name,
# so a marker added at RUNTIME is not present in the child; a runtime-registered
# mock is therefore only valid for in-process (``isolate=False``) use. In practice
# the only samplers that traverse spawn are ``fit_hmc_e1`` (gated) and the
# import-registered dry-run mock, so this is a documented constraint, not a hole.
_UNGATED_ATTR = "_m2br_ungated_mock"


def register_mock_sampler(fn):
    """Mark a deterministic mock sampler as safe to run without authorization."""
    setattr(fn, _UNGATED_ATTR, True)
    return fn


def unregister_mock_sampler(fn) -> None:
    """Remove a mock marker (used by test fixtures for cleanup)."""
    try:
        delattr(fn, _UNGATED_ATTR)
    except AttributeError:
        pass


def is_ungated_sampler(fn) -> bool:
    """True only for explicitly registered mock samplers."""
    return getattr(fn, _UNGATED_ATTR, False) is True


def require_sampler_authorization(sampler_fn, authorized) -> None:
    """Fail-closed gate: raise unless ``sampler_fn`` is a registered mock or
    ``authorized is True``. Real HMC AND any unrecognized callable (including a
    wrapper such as ``partial(fit_hmc_e1)``) are gated."""
    if is_ungated_sampler(sampler_fn):
        return
    if authorized is not True:
        raise PermissionError(
            "sampler requires authorized=True (CLI: --execute); only registered "
            "mock samplers run without authorization")


register_mock_sampler(deterministic_mock_sampler)


def json_sha256(obj) -> str:
    encoded = json.dumps(obj, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    return sha256_bytes(encoded)


def run_plan_payload() -> dict:
    """Machine-readable combined plan shared by both no-execute CLIs."""
    from m2br_audit_run import AUDIT_RUNS
    from m2br_validation_run import VALIDATION_CELLS, load_frozen_starts

    starts = load_frozen_starts(FREEZE_PATH)
    audit_output = "runs/m2br_corrected_impact"
    validation_output = "runs/m2br_validation"
    return {
        "protocol": "M2bR AUDIT and VALIDATION run plan",
        "manifest": {"path": str(FREEZE_PATH.relative_to(REPO_ROOT)),
                     "sha256": FREEZE_SHA256},
        "provenance": env_provenance(),
        "audit": {
            "ceiling_seconds": 7200,
            "reserve_seconds": 600,
            "runs": [{
                **run,
                "seed": 42,
                "n_samples": 2000,
                "n_warmup": 1000,
                "projection_seconds": PROJECTIONS[run["td"]],
                "output_paths": {
                    "samples": f"{audit_output}/samples_{run['run_id']}_e1.npz",
                    "diagnostics": f"{audit_output}/diagnostics_{run['run_id']}.json",
                    "results": f"{audit_output}/results_{run['run_id']}.json",
                },
            } for run in AUDIT_RUNS],
        },
        "validation": {
            "ceiling_seconds": 21600,
            "reserve_seconds": 600,
            "cells": [{
                **cell,
                "seeds": [0, 1, 2, 3],
                "n_samples": 2000,
                "n_warmup": 1000,
                "projection_seconds_per_chain": PROJECTIONS[cell["td"]],
                "start_semantic_sha256": [
                    record["semantic_sha256"]
                    for record in starts[cell["config"]]["records"]
                ],
                "output_path": f"{validation_output}/{cell['cell']}",
            } for cell in VALIDATION_CELLS],
        },
    }


def emit_run_plan(path=REPO_ROOT / "docs" / "m2br_freeze" / "run_plan.json"):
    payload = run_plan_payload()
    path = Path(path)
    if path.exists():
        with open(path) as handle:
            if json.load(handle) == payload:
                return payload
        raise FileExistsError(f"existing run plan differs; refusing overwrite: {path}")
    atomic_write_json(path, payload)
    return payload
