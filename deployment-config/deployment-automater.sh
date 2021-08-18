#!/bin/bash
echo "\033[1;34m Creating Resource Group... \033[0m"
az group create --name fypResourceGroup --location eastus &&
echo "\033[1;32m Created Resource Group \033[0m"
echo "\033[1;34m Retriving Addon Info... \033[0m"
az provider show -n Microsoft.OperationsManagement -o table &&
az provider show -n Microsoft.OperationalInsights -o table &&
echo "\033[1;34m Registering Addons \033[0m"
az provider register --namespace Microsoft.OperationsManagement 
az provider register --namespace Microsoft.OperationalInsights
echo "\033[1;32m Done registering addons \033[0m"
echo "\033[1;34m Creating Cluster with single node... \033[0m"
az aks create --resource-group fypResourceGroup --name fypAKSCluster --node-count 1 --enable-addons monitoring --generate-ssh-keys --yes
echo "\033[1;32m Cluster Created\033[0m"
echo "\033[1;34m Retriving Credentials... \033[0m"
az aks get-credentials --resource-group fypResourceGroup --name fypAKSCluster --overwrite-existing
echo "\033[1;32m Configuration Saved\033[0m"
echo "\033[1;34m Retriving Nodes... \033[0m"
kubectl get nodes
echo "\033[1;34m Creating Deployment... \033[0m"
kubectl apply -f complete-demo2.yaml
echo "\033[1;32m Deployment Created\033[0m"
echo "\033[1;34m Sleeping for 2 minutes... \033[0m"
sleep 2m
echo "\033[1;32m Done sleeping\033[0m"
echo "\033[1;34m Retriving Services... \033[0m"
kubectl get services --namespace=sock-shop
echo "\033[1;32m Microservice Deployment is complete!\033[0m"