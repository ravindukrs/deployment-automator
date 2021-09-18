import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime
import deployment_config.deployment_properties as props


def get_front_end_ip():
    front_end_ip = subprocess.check_output(
        "cd deployment_config &&  kubectl get services --namespace=" + props.VAR_NAMESPACE + " |  awk '/front-end/ {print $4}'",
        shell=True)
    external_ip = front_end_ip.decode('utf-8')
    print("Current External IP: ", external_ip)
    if external_ip.__contains__(".") and external_ip.__len__() > 6:
        print("Returning final External IP: ", external_ip)
        return external_ip
    else:
        print("No IP detected. Retrying in 5 seconds...")
        time.sleep(5)
        get_front_end_ip()


def modify_xml(ip):
    mytree = ET.parse('deployment-performance/jmeter-script.jmx')
    myroot = mytree.getroot()
    for item in myroot.iter('stringProp'):
        if (item.attrib['name'] == 'HTTPSampler.domain'):
            item.text = ip

    mytree.write('./deployment-performance/jmeter-script.jmx')
    print("Updated JMX")


def run_jmeter():
    shellcommand = "/Users/ravindu/Downloads/apache-jmeter-5.3/bin/jmeter -n -t ./deployment-performance/jmeter-script.jmx -l ./deployment-performance/perf-results/jtl/testresults" + str(
        datetime.now().strftime("%d-%m-%Y-%H:%M:%S")) + ".jtl | awk '/summary =/ {print $3}'"

    average_latency = subprocess.check_output(
        shellcommand,
        shell=True)

    return average_latency


def write_results(value):
    with open('./deployment-performance/latency-records.csv', 'a+') as file:
        file.write(value + '\n')
        print("Latency added to records")


def get_config_string(index):
    resource = props.RESOURCES[index]
    config_string = '{} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {}'.format(
        props.VAR_NAMESPACE,
        resource["CARTS_CPU"], resource["CARTS_MEMORY"],
        resource["CATALOGUE_CPU"], resource["CATALOGUE_MEMORY"],
        resource["FRONT_END_CPU"], resource["FRONT_END_MEMORY"],
        resource["ORDERS_CPU"], resource["ORDERS_MEMORY"],
        resource["PAYMENT_CPU"], resource["PAYMENT_MEMORY"],
        resource["QUEUE_MASTER_CPU"], resource["QUEUE_MASTER_CPU"],
        resource["SHIPPING_CPU"], resource["SHIPPING_MEMORY"],
        resource["USER_CPU"], resource["USER_MEMORY"],

    )
    return config_string


if __name__ == '__main__':
    # Create AKS Cluster
    subprocess.call("chmod +x ./deployment_config/deployment-automater.sh", shell=True)
    subprocess.call("cd deployment_config && ./deployment-automater.sh " + get_config_string(0), shell=True)

    for x in range(4):
        print("Entering Iteration ", x)
        # Create Deployment
        subprocess.call("chmod +x ./deployment_config/template-deployment.sh", shell=True)
        subprocess.call("cd deployment_config && ./template-deployment.sh " + get_config_string(0), shell=True)

        # Get Public IP of Front End
        print("Getting Public IP of Front End Service")
        external_ip = get_front_end_ip().strip()
        print("External IP ", external_ip)

        # Update Jmeter Configuration
        modify_xml(external_ip)

        # Run Jmeter Test and Collect Metrics
        average_latency = run_jmeter()
        latency_array = average_latency.decode('utf-8').splitlines()
        print("Average Latency of Deployment:", latency_array[-1])

        # Write Jmeter Latency result to CSV
        result_string = '{} {}'.format(
            latency_array[-1],
            get_config_string(0),
        )
        write_results(result_string)

        #Delete Namespace and Deployment
        subprocess.call("chmod +x ./deployment_config/delete-deployment.sh", shell=True)
        subprocess.call("cd deployment_config && ./delete-deployment.sh "+props.VAR_NAMESPACE, shell=True)

        if x == 4:
            subprocess.call("chmod +x ./deployment_config/delete-resources.sh", shell=True)
            subprocess.call("cd deployment_config && ./delete-resources.sh", shell=True)
