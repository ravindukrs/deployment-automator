import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime
import deployment_config.deployment_properties as props

import torch
import re

from botorch.models import SingleTaskGP, ModelListGP
from gpytorch.mlls.exact_marginal_log_likelihood import ExactMarginalLogLikelihood

from botorch import fit_gpytorch_model

from botorch.acquisition.monte_carlo import qExpectedImprovement
from botorch.optim import optimize_acqf
import numpy as np



def target_function(configurations):
    result = []
    config = []
    for configuration in configurations:
        # Modify the Deployment Template & Deploy new Configuration
        outcome = -20.0 * np.exp(-0.2 * np.sqrt(0.5 * (configuration[0] ** 2 + configuration[1] ** 2))) - np.exp(0.5 * (np.cos(2 * np.pi * configuration[0]) + np.cos(2 * np.pi * configuration[1]))) + np.e + 20
        print("Outcome of Evaluation: ", outcome)
        print("Outcome of Evaluation Inverted: ", float(outcome) * -1)

        # For Latency
        result.append(float(outcome) * -1)

        outcome_string = '{} {} {}'.format(
            outcome,
            configuration[0],
            configuration[1]
        )

        with open('./deployment-performance/test-function.csv', 'a+') as file:
            file.write(outcome_string + '\n')
            print("Outcome added to records")

    print("From Target Function result: ", result)
    return torch.tensor(result, dtype=torch.double)


def generate_initial_data():
    train_x = torch.tensor([[
        np.random.uniform(-5.0, 5.0),
        np.random.uniform(-5.0, 5.0)
    ]], dtype=torch.double)

    print("Initial Configuration: ", train_x)
    exact_obj = target_function(train_x).unsqueeze(-1)
    best_observed_value = exact_obj.max().item()
    return train_x, exact_obj, best_observed_value


def get_next_points(init_x, init_y, best_init_y, bounds, n_points=1):
    single_model = SingleTaskGP(init_x, init_y)
    mll = ExactMarginalLogLikelihood(single_model.likelihood, single_model)
    fit_gpytorch_model(mll)

    EI = qExpectedImprovement(model=single_model, best_f=best_init_y)

    # REQUESTS
    # cpu_equality_constraints = (torch.tensor([0, 2, 4, 6, 8, 10, 12, 14]), torch.tensor([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]), 800.0)
    # memory_equality_constraints = (torch.tensor([1, 3, 5, 7, 9, 11, 13, 15]), torch.tensor([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]), 1700.0)

    # # LIMITS
    # cpu_equality_constraints = (torch.tensor([0, 2, 4, 6, 8, 10, 12, 14]), torch.tensor([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]), 2400.0)
    # memory_equality_constraints = (torch.tensor([1, 3, 5, 7, 9, 11, 13, 15]), torch.tensor([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]), 3600.0)

    # LIMITS
    # cpu_equality_constraints = (torch.tensor([0, 2]), torch.tensor([1.0, 1.0], dtype=torch.double), 500.0)
    # memory_equality_constraints = (torch.tensor([1, 3]), torch.tensor([1.0, 1.0], dtype=torch.double), 400.0)

    # equality_constraints = [cpu_equality_constraints, memory_equality_constraints]

    # candidates, _ = optimize_acqf(
    #     acq_function=EI,
    #     bounds=bounds,
    #     q=n_points,
    #     equality_constraints=equality_constraints,
    #     num_restarts=200,
    #     raw_samples=512,
    #     options={"batch_limit": 5, "maxiter": 200}
    # )

    # candidates, _ = optimize_acqf(
    #     acq_function=EI,
    #     bounds=bounds,
    #     q=n_points,
    #     # equality_constraints=equality_constraints,
    #     num_restarts=2,
    #     raw_samples=10,
    #     return_best_only = True
    #     # options={"batch_limit": 5, "maxiter": 200}
    # )

    candidates, _ = optimize_acqf(
        acq_function=EI,
        bounds=bounds,
        q=1,
        num_restarts=200,
        raw_samples=1024,
        options={"batch_limit": 5, "maxiter": 100}
    )

    return candidates


if __name__ == '__main__':

    n_runs = 100

    init_x, init_y, best_init_y = generate_initial_data()
    print("Init X: ", init_x)
    print("Init Y: ", init_y)
    print("best_init_y : ", best_init_y)

    bounds = torch.tensor([
        # REQUESTS
        # [10., 20., 10., 25., 25., 50., 25., 50., 25., 25., 25., 50., 25., 50., 25., 25.],
        # [800., 1700., 800., 1700., 800., 1700., 800., 1700., 800., 1700., 800., 1700., 800., 1700., 800., 1700.]

        # # LIMITS
        # [10., 20., 10., 25., 25., 50., 25., 50., 25., 25., 25., 50., 25., 50., 25., 25.],
        # [2400., 3600., 2400., 3600., 2400., 3600., 2400., 3600., 2400., 3600., 2400., 3600., 2400., 3600., 2400., 3600.]

        # LIMITS
        [-5.0, -5.0],
        [5.0, 5.0]

    ], dtype=torch.double)

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
