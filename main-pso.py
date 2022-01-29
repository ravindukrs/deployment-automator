import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime
import deployment_config.deployment_properties as props
from pyswarm import pso
import re

iteration = 0

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
    # For Latency
    shellcommand = "./apache-jmeter-5.4.1/bin/jmeter -n -t ./deployment-performance/jmeter-script.jmx -l ./deployment-performance/perf-results/jtl/testresults" + str(
        datetime.now().strftime("%d-%m-%Y-%H:%M:%S")) + ".jtl | awk '/summary =/ {print $9,$16}'"

    # # For TPS
    # shellcommand = "./apache-jmeter-5.4.1/bin/jmeter -n -t ./deployment-performance/jmeter-script.jmx -l ./deployment-performance/perf-results/jtl/testresults" + str(
    #     datetime.now().strftime("%d-%m-%Y-%H:%M:%S")) + ".jtl | awk '/summary =/ {print $7,$16}'"

    shell_output = subprocess.check_output(
        shellcommand,
        shell=True)

    shell_results_array = shell_output.decode('utf-8').splitlines()

    last_result = shell_results_array[-1]
    result = last_result.split()
    # For Latency
    average_latency = result[0]

    # # For TPS
    # average_latency = float(re.findall("\d+\.\d+", result[0])[0])

    error_percentage = result[1]

    return average_latency, error_percentage


def write_results(value):
    with open('./deployment-performance/latency-records.csv', 'a+') as file:
        file.write(value + '\n')
        print("Latency added to records")

def write_candidates(value, cpu, memory):
    with open('./deployment-performance/candidate-values.csv', 'a+') as file:
        file.write(' '.join(map(str, value)) + " " + str(cpu) + " " + str(memory) + '\n')

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


def target_function(configuration):
    global iteration
    print("Starting iteration: ", iteration)
    constraints_result = constraints(configuration)
    if (constraints_result[0] >= 0.0 and constraints_result[1] >= 0.0):
        result = []
        # Modify the Deployment Template & Deploy new Configuration
        config_string = get_configuration_string(configuration)
        print("Current config: ", config_string)
        subprocess.call("chmod +x ./deployment_config/template-deployment.sh", shell=True)
        subprocess.call("cd deployment_config && ./template-deployment.sh " + config_string, shell=True)

        external_ip = "<pending>"
        # Get Public IP of Front End
        while (not (external_ip.__contains__(".") and external_ip.__len__() > 6)):
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
        # For Latency
        errfloat = float(re.findall("\d+\.\d+", error_percentage)[0])
        if(errfloat > 10.0):
            result.append(240000.0)
        else:
            result.append(float(average_latency))

        # # For TPS
        # result.append(float(average_latency) * 1)

        # Delete Namespace and Deployment
        subprocess.call("chmod +x ./deployment_config/delete-deployment.sh", shell=True)
        subprocess.call("cd deployment_config && ./delete-deployment.sh " + props.VAR_NAMESPACE, shell=True)


        print("From Target Function result: ", result)
        iteration = iteration + 1
        return result[0]
    else:
        print("Ignoring Iteration")
        panelty  = panelty_function(constraints_result[0], constraints_result[1])
        return (panelty)

def panelty_function(cpu, memory):
    zcpu = (cpu * -1 ) + 2400.0
    zmemory = (memory * -1 ) + 3600.0
    panelty_from_resources = (zcpu + zmemory)*1000
    panelty = 240000 +  panelty_from_resources
    print("Panelty: ",  panelty)
    return panelty



def generate_initial_data():
    resource = props.RESOURCES[0]
    train_x = [
        resource["CARTS_CPU"], resource["CARTS_MEMORY"],
        resource["CATALOGUE_CPU"], resource["CATALOGUE_MEMORY"],
        resource["FRONT_END_CPU"], resource["FRONT_END_MEMORY"],
        resource["ORDERS_CPU"], resource["ORDERS_MEMORY"],
        resource["PAYMENT_CPU"], resource["PAYMENT_MEMORY"],
        resource["QUEUE_MASTER_CPU"], resource["QUEUE_MASTER_MEMORY"],
        resource["SHIPPING_CPU"], resource["SHIPPING_MEMORY"],
        resource["USER_CPU"], resource["USER_MEMORY"],

    ]
    print("Initial Configuration: ", train_x)
    exact_obj = target_function(train_x)
    # Run it a second time
    exact_obj = target_function(train_x)
    return train_x, exact_obj


def cpu_usage(x_train):
    return x_train[0] + x_train[2] + x_train[4] + x_train[6] + x_train[8] + x_train[10] + x_train[12] + x_train[14]

def memory_usage(x_train):
    return x_train[1] + x_train[3] + x_train[5] + x_train[7] + x_train[9] + x_train[11] + x_train[13] + x_train[15]

def constraints(x_train):
    cpu = cpu_usage(x_train)
    print("CPU Usage: ", cpu)
    memory = memory_usage(x_train)
    print("Memory Usage: ", memory)
    print(x_train)
    write_candidates(x_train, cpu, memory)
    return [2400.0 - cpu, 3600.0 - memory]



if __name__ == '__main__':
    # Create AKS Cluster
    subprocess.call("chmod +x ./deployment_config/deployment-automater.sh", shell=True)
    subprocess.call("cd deployment_config && ./deployment-automater.sh ", shell=True)

    init_x, init_y = generate_initial_data()
    print("Init X: ", init_x)
    print("Init Y: ", init_y)

    bounds = [
        # LIMITS
        [300., 500., 10., 25., 25., 50., 25., 50., 25., 25., 25., 50., 25., 50., 25., 25.],
        [2400., 3600., 2400., 3600., 2400., 3600., 2400., 3600., 2400., 3600., 2400., 3600., 2400., 3600., 2400., 3600.]

    ]
    print("Starting Optimization")
    xopt, fopt = pso(target_function, lb=bounds[0], ub=bounds[1], swarmsize=160, maxiter=1000 ,f_ieqcons=constraints)
    print("Optimization Complete")
    print("xopt: ",xopt)
    print("fopt: ",fopt)
    subprocess.call("chmod +x ./deployment_config/delete-resources.sh", shell=True)
    subprocess.call("cd deployment_config && ./delete-resources.sh", shell=True)
