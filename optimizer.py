import os
import torch
import numpy as np
# import plotly

from botorch.models import SingleTaskGP, ModelListGP
from gpytorch.mlls.exact_marginal_log_likelihood import ExactMarginalLogLikelihood

from botorch import fit_gpytorch_model

from botorch.acquisition.monte_carlo import qExpectedImprovement
from botorch.optim import optimize_acqf


def target_function(individuals):
    result = []
    for x in individuals:
        curr_result = (np.exp(-(x[0] - 2) ** 2) + np.exp(-(x[0] - 6) ** 2 / 10) + (1 / (x[0] ** 2 + 1)) - x[1])
        result.append(curr_result * -1)
    return torch.tensor(result)


def generate_initial_data(n=10):
    train_x = torch.rand(n, 2)
    exact_obj = target_function(train_x).unsqueeze(-1)
    best_observed_value = exact_obj.max().item()
    return train_x, exact_obj, best_observed_value


def get_next_points(init_x, init_y, best_init_y, bounds, n_points=1):
    single_model = SingleTaskGP(init_x, init_y)
    mll = ExactMarginalLogLikelihood(single_model.likelihood, single_model)
    fit_gpytorch_model(mll)

    EI = qExpectedImprovement(model=single_model, best_f=best_init_y)

    candidates, _ = optimize_acqf(
        acq_function=EI,
        bounds=bounds,
        q=n_points,
        num_restarts=200,
        raw_samples=512,
        options={"batch_limit": 5, "maxiter": 200}
    )

    return candidates


n_runs = 15

init_x, init_y, best_init_y = generate_initial_data(1)
bounds = torch.tensor([[0., 2.], [10., 5.]])

for i in range(n_runs):
    print(f"Nr. of Optimization run: {i}")

    new_candidate = get_next_points(init_x, init_y, best_init_y, bounds, n_points=1)
    new_results = target_function(new_candidate).unsqueeze(-1)

    print(f"New Candidate is: {new_candidate}")

    init_x = torch.cat([init_x, new_candidate])
    init_y = torch.cat([init_y, new_results])

    best_init_y = init_y.max().item()
    print(f"New Result is: {new_results}")
    print(f"Best point performs this way: {best_init_y}")
    print(f"Best Corresponding Index of Y value performs this way: {torch.argmax(init_y)}")
    print(f"Best Corresponding Y value performs this way: {init_x[torch.argmax(init_y)]}")
