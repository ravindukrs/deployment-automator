import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime
import deployment_config.deployment_properties as props

import os
import torch
import numpy as np
# import plotly

from botorch.models import SingleTaskGP, ModelListGP
from gpytorch.mlls.exact_marginal_log_likelihood import ExactMarginalLogLikelihood

from botorch import fit_gpytorch_model

from botorch.acquisition.monte_carlo import qExpectedImprovement
from botorch.optim import optimize_acqf


def get_front_end_ip():
    front_end_ip = subprocess.check_output(
        "cd deployment_config &&  kubectl get services --namespace=" + props.VAR_NAMESPACE + " |  awk '/front-end/ {print $4}'",
        shell=True)
    external_ip = front_end_ip.decode('utf-8')
    print("Current External IP: ", external_ip)
    if external_ip.__contains__(".") and external_ip.__len__() > 6:
        print("Returning final External IP: ", external_ip)
        time.sleep(2)
        external_ip = external_ip.strip()
        return external_ip
    else:
        print("No IP detected. Retrying in 5 seconds...")
        time.sleep(5)
        get_front_end_ip()
    return external_ip


def modify_xml(ip):
    mytree = ET.parse('deployment-performance/jmeter-script.jmx')
    myroot = mytree.getroot()
    for item in myroot.iter('stringProp'):
        if (item.attrib['name'] == 'HTTPSampler.domain'):
            item.text = ip

    mytree.write('./deployment-performance/jmeter-script.jmx')
    print("Updated JMX")


def run_jmeter():
    shellcommand = "./apache-jmeter-5.4.1/bin/jmeter -n -t ./deployment-performance/jmeter-script.jmx -l ./deployment-performance/perf-results/jtl/testresults" + str(
        datetime.now().strftime("%d-%m-%Y-%H:%M:%S")) + ".jtl | awk '/summary =/ {print $3,$16}'"

    shell_output = subprocess.check_output(
        shellcommand,
        shell=True)

    shell_results_array = shell_output.decode('utf-8').splitlines()

    last_result = shell_results_array[-1]
    result = last_result.split()
    average_latency = result[0]
    error_percentage = result[1]

    return average_latency, error_percentage


def write_results(value):
    with open('./deployment-performance/latency-records.csv', 'a+') as file:
        file.write(value + '\n')
        print("Latency added to records")

def get_configuration_string(configuration):
    config_string = '{} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {}'.format(
        props.VAR_NAMESPACE,
        configuration[0], configuration[1],
        configuration[2], configuration[3],
        configuration[4], configuration[5],
        configuration[6], configuration[7],
        configuration[8], configuration[9],
        configuration[10], configuration[11],
        configuration[12], configuration[13],
        configuration[14], configuration[15],

    )
    return config_string


def target_function(configurations):
    result = []
    for configuration in configurations:
        # Modify the Deployment Template & Deploy new Configuration
        config_string = get_configuration_string(configuration)
        subprocess.call("chmod +x ./deployment_config/template-deployment.sh", shell=True)
        subprocess.call("cd deployment_config && ./template-deployment.sh " + config_string, shell=True)

        external_ip = "<pending>"
        # Get Public IP of Front End
        while (not(external_ip.__contains__(".") and external_ip.__len__() > 6)):
            print("Getting Public IP of Front End Service")
            external_ip = get_front_end_ip()
            print("External IP ", external_ip)

        # Update Jmeter Configuration
        modify_xml(external_ip)

        # Run Jmeter Test and Collect Metrics
        average_latency, error_percentage = run_jmeter()

        print("Average Latency of Deployment:", average_latency)

        # Write Jmeter Latency result to CSV
        result_string = '{} {} {}'.format(
            average_latency,
            error_percentage,
            config_string
        )
        write_results(result_string)
        print("Latency as a Float: ", float(average_latency))
        print("Latency Inverted: ", float(average_latency) * -1)
        result.append(float(average_latency) * -1)

        # Delete Namespace and Deployment
        subprocess.call("chmod +x ./deployment_config/delete-deployment.sh", shell=True)
        subprocess.call("cd deployment_config && ./delete-deployment.sh " + props.VAR_NAMESPACE, shell=True)

    print("From Target Function result: ", result)
    return torch.tensor(result)


def generate_initial_data():
    resource = props.RESOURCES[0]
    train_x = torch.tensor([[
        resource["CARTS_CPU"], resource["CARTS_MEMORY"],
        resource["CATALOGUE_CPU"], resource["CATALOGUE_MEMORY"],
        resource["FRONT_END_CPU"], resource["FRONT_END_MEMORY"],
        resource["ORDERS_CPU"], resource["ORDERS_MEMORY"],
        resource["PAYMENT_CPU"], resource["PAYMENT_MEMORY"],
        resource["QUEUE_MASTER_CPU"], resource["QUEUE_MASTER_MEMORY"],
        resource["SHIPPING_CPU"], resource["SHIPPING_MEMORY"],
        resource["USER_CPU"], resource["USER_MEMORY"],

    ]])
    print("Initial Configuration: ", train_x)
    exact_obj = target_function(train_x).unsqueeze(-1)
    best_observed_value = exact_obj.max().item()
    return train_x, exact_obj, best_observed_value


def get_next_points(init_x, init_y, best_init_y, bounds, n_points=1):
    single_model = SingleTaskGP(init_x, init_y)
    mll = ExactMarginalLogLikelihood(single_model.likelihood, single_model)
    fit_gpytorch_model(mll)

    EI = qExpectedImprovement(model=single_model, best_f=best_init_y)

    cpu_equality_constraints = (torch.tensor([0, 2, 4, 6, 8, 10, 12, 14]), torch.tensor([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]), 800.0)
    memory_equality_constraints = (torch.tensor([1, 3, 5, 7, 9, 11, 13, 15]), torch.tensor([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]), 1700.0)

    equality_constraints = [cpu_equality_constraints, memory_equality_constraints]

    candidates, _ = optimize_acqf(
        acq_function=EI,
        bounds=bounds,
        q=n_points,
        equality_constraints=equality_constraints,
        num_restarts=200,
        raw_samples=512,
        options={"batch_limit": 5, "maxiter": 200}
    )

    return candidates


if __name__ == '__main__':
    # Create AKS Cluster
    subprocess.call("chmod +x ./deployment_config/deployment-automater.sh", shell=True)
    subprocess.call("cd deployment_config && ./deployment-automater.sh ", shell=True)

    n_runs = 100

    init_x, init_y, best_init_y = generate_initial_data()
    print("Init X: ", init_x)
    print("Init Y: ", init_y)
    print("best_init_y : ", best_init_y)

    bounds = torch.tensor([
        [10., 20., 10., 25., 25., 50., 25., 50., 25., 25., 25., 50., 25., 50., 25., 25.],
        [800., 1700., 800., 1700., 800., 1700., 800., 1700., 800., 1700., 800., 1700., 8000., 1700., 800., 1700.]
    ])

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

    subprocess.call("chmod +x ./deployment_config/delete-resources.sh", shell=True)
    subprocess.call("cd deployment_config && ./delete-resources.sh", shell=True)
