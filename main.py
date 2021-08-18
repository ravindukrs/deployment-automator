import subprocess
import time
def get_front_end_ip():
    front_end_ip = subprocess.check_output(
        "cd deployment-config &&  kubectl get services --namespace=sock-shop |  awk '/front-end/ {print $4}'",
        shell=True)
    external_ip = front_end_ip.decode('utf-8')
    if(external_ip.__contains__(".")):
        return external_ip
    else:
        print("No IP detected. Retrying in 5 seconds...")
        time.sleep(5)
        get_front_end_ip()



if __name__ == '__main__':
    subprocess.call("chmod +x ./deployment-config/deployment-automater.sh", shell=True)
    subprocess.call("cd deployment-config && ./deployment-automater.sh", shell=True)

    print("Getting Public IP of Front End Service")
    external_ip = get_front_end_ip()
    print(external_ip)

