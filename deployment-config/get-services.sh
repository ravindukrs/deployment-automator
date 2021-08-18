#!/bin/bash
echo "\033[1;34m Retriving Services... \033[0m"
kubectl get services --namespace=sock-shop
echo "\033[1;32m Microservice Deployment is complete!\033[0m"