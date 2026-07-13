"""Functional M2c profile potential (P1, prereg v1.17 rev-5 section 2a).

The nuisance coordinates are logs of constrained hyperparameters. Kernel and
likelihood values are substituted with ``torch.func.functional_call`` so the
likelihood graph remains connected, while the fixed noise coordinate is kept
outside the profile state.
"""

import gpytorch
import torch

from .e1_potential import _JointModule, _site_parameter_map
from .fit import DEFAULT_JITTER
from .model import apply_hp_value


torch.set_default_dtype(torch.float64)


class ProfilePotential:
    """Differentiable ``log_joint(exp(u), noise) + sum(u)`` profile target."""

    def __init__(self, model, likelihood, train_x, train_y,
                 jitter=DEFAULT_JITTER):
        self._model = model
        self._likelihood = likelihood
        self._x = train_x.double()
        self._y = train_y.double()
        self._jitter = jitter

        self.sites = tuple(name for name, *_ in model.named_priors())
        self._site_map = _site_parameter_map(model, self.sites)
        noise_sites = tuple(
            site for site in self.sites if "noise_covar.noise" in site
        )
        if len(noise_sites) != 1:
            raise RuntimeError(
                "profile site-role ambiguity: expected exactly one "
                f"noise_covar.noise site, found {len(noise_sites)}: "
                f"{noise_sites}"
            )
        self.noise_site = noise_sites[0]
        self.nuisance_sites = tuple(
            site for site in self.sites if site != self.noise_site
        )
        self._joint = _JointModule(model)

    def _coordinate(self, value, connected):
        coordinate = torch.as_tensor(
            value, dtype=torch.float64, device=self._y.device
        )
        return coordinate if connected else coordinate.detach()

    def _fixed_noise(self, noise):
        value = float(torch.as_tensor(noise).detach())
        return torch.as_tensor(
            value, dtype=torch.float64, device=self._y.device
        )

    def g_value(self, u, noise, connected=True):
        """Return the scalar profile log density in constrained-log space."""
        self._model.train()
        self._likelihood.train()
        overrides = {}
        log_prior = self._y.new_zeros(())
        log_jacobian = self._y.new_zeros(())

        for site in self.nuisance_sites:
            coordinate = self._coordinate(u[site], connected)
            theta = torch.exp(coordinate)
            prior, fqname, constraint, raw_shape = self._site_map[site]
            log_prior = log_prior + prior.log_prob(theta).sum()
            log_jacobian = log_jacobian + coordinate.sum()
            raw = (
                constraint.inverse_transform(theta)
                if constraint is not None else theta
            )
            overrides["gp." + fqname] = raw.reshape(raw_shape)

        theta_noise = self._fixed_noise(noise)
        prior, fqname, constraint, raw_shape = self._site_map[self.noise_site]
        log_prior = log_prior + prior.log_prob(theta_noise).sum()
        raw_noise = (
            constraint.inverse_transform(theta_noise)
            if constraint is not None else theta_noise
        )
        overrides["gp." + fqname] = raw_noise.reshape(raw_shape)

        with gpytorch.settings.cholesky_jitter(self._jitter):
            log_marginal = torch.func.functional_call(
                self._joint, overrides, (self._x, self._y)
            )
        return log_marginal + log_prior + log_jacobian

    def g_grad_functional(self, u, noise):
        """Differentiate the functional profile value over nuisance sites."""
        u_required = {
            site: torch.as_tensor(u[site], dtype=torch.float64)
            .clone().detach().requires_grad_(True)
            for site in self.nuisance_sites
        }
        value = self.g_value(u_required, noise)
        gradients = torch.autograd.grad(
            value, [u_required[site] for site in self.nuisance_sites]
        )
        return dict(zip(self.nuisance_sites, gradients))

    def g_grad_naive_data(self, u, noise):
        """Return the D23-broken ``.data``-injection reference gradient.

        ``apply_hp_value`` writes constrained values into module parameters,
        severing the nuisance-to-likelihood graph. Explicit prior and log
        Jacobian terms remain connected, exposing the missing likelihood
        contribution used by the prereg v1.3/D23 sentinel.
        """
        u_required = {
            site: torch.as_tensor(u[site], dtype=torch.float64)
            .clone().detach().requires_grad_(True)
            for site in self.nuisance_sites
        }
        saved_parameters = {
            name: parameter.detach().clone()
            for name, parameter in self._model.named_parameters()
        }

        try:
            self._model.train()
            self._likelihood.train()
            log_prior = self._y.new_zeros(())
            log_jacobian = self._y.new_zeros(())
            for site in self.nuisance_sites:
                theta = torch.exp(u_required[site])
                if not apply_hp_value(
                        self._model, self._likelihood, site, theta):
                    raise RuntimeError(
                        f"profile site could not be applied by name: {site}"
                    )
                prior = self._site_map[site][0]
                log_prior = log_prior + prior.log_prob(theta).sum()
                log_jacobian = log_jacobian + u_required[site].sum()

            theta_noise = self._fixed_noise(noise)
            if not apply_hp_value(
                    self._model, self._likelihood,
                    self.noise_site, theta_noise):
                raise RuntimeError(
                    "profile noise site could not be applied by name: "
                    f"{self.noise_site}"
                )
            noise_prior = self._site_map[self.noise_site][0]
            log_prior = log_prior + noise_prior.log_prob(theta_noise).sum()

            # Likelihood-only score through the SAME _JointModule as the
            # functional path, but reached after apply_hp_value's ``.data``
            # writes (which sever the kernel-site graph — the D23 defect).
            # Priors are added explicitly above (log_prior), mirroring
            # g_value's decomposition exactly, so this scalar does NOT
            # double-count priors (an ExactMarginalLogLikelihood would add
            # every registered prior a second time).
            with gpytorch.settings.cholesky_jitter(self._jitter):
                fresh_score = self._joint(self._x, self._y)
            naive_value = fresh_score + log_prior + log_jacobian
            gradients = torch.autograd.grad(
                naive_value,
                [u_required[site] for site in self.nuisance_sites],
                allow_unused=True,
            )
            return dict(zip(self.nuisance_sites, gradients))
        finally:
            with torch.no_grad():
                for name, parameter in self._model.named_parameters():
                    parameter.copy_(saved_parameters[name])
