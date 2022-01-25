echo "Initiating VM Configuration..."
echo "Installing Azure CLI"
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
echo "Logging in with Azure CLI"
az login --use-device-code
echo "Installing Java"
sudo apt update
sudo apt install default-jre -y
java -version
sudo apt -y upgrade
echo "Verify Python Version"
python3 -V
echo "Installing PIP3"
sudo apt install -y python3-pip
echo "Change Directory to Automator"
cd deployment-automator/
echo "Download Jmeter"
wget http://www.gtlib.gatech.edu/pub/apache/jmeter/binaries/apache-jmeter-5.4.1.tgz
echo "Extract Jmeter"
tar xf apache-jmeter-5.4.1.tgz
echo "Installing Project Requirements"
pip install -r requirements.txt
echo "Install kubectl"
sudo az aks install-cli
echo "Running main2.py"
python3 main-pso.py