import subprocess
import time
import xml.etree.ElementTree as ET


def get_front_end_ip():
    front_end_ip = subprocess.check_output(
        "cd deployment-config &&  kubectl get services --namespace=sock-shop |  awk '/front-end/ {print $4}'",
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
    mytree = ET.parse('./deployment-config/jmeter-script.jmx')
    myroot = mytree.getroot()
    for item in myroot.iter('stringProp'):
        if(item.attrib['name'] == 'HTTPSampler.domain'):
            item.text = ip

    mytree.write('./deployment-config/jmeter-script.jmx')
    print("Updated JMX")

def run_jmeter():
    average_latency = subprocess.check_output(
        "/Users/ravindu/Downloads/apache-jmeter-5.3/bin/jmeter -n -t ./deployment-config/jmeter-script.jmx -l ./deployment-config/testresults.jtl | awk '/summary =/ {print $3}'",
        shell=True)

    return average_latency.decode('utf-8')

if __name__ == '__main__':
    # Deploy Microservice on AKS
    subprocess.call("chmod +x ./deployment-config/deployment-automater.sh", shell=True)
    subprocess.call("cd deployment-config && ./deployment-automater.sh", shell=True)

    # Get Public IP of Front End
    print("Getting Public IP of Front End Service")
    external_ip = get_front_end_ip().strip()
    print("External IP ", external_ip)

    # Update Jmeter Configuration
    modify_xml(external_ip)

    # Run Jmeter Test and Collect Metrics
    average_latency = run_jmeter()
    print("Average Latency of Deployment:",average_latency)