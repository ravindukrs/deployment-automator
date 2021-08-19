#!/bin/bash

# read the yml template from a file and substitute the string
# {{MYVARNAME}} with the value of the MYVARVALUE variable
echo "\033[1;34m Substituting for Deployment from Template... \033[0m"
template=`cat "deployment-template.yaml" | sed "s/{{VAR_NAMESPACE}}/$1/g; s/{{CARTS_CPU}}/$2/g; s/{{CARTS_MEMORY}}/$3/g; s/{{CATALOGUE_CPU}}/$4/g; s/{{CATALOGUE_MEMORY}}/$5/g; s/{{FRONT_END_CPU}}/$6/g; s/{{FRONT_END_MEMORY}}/$7/g; s/{{ORDERS_CPU}}/$8/g; s/{{ORDERS_MEMORY}}/$9/g; s/{{PAYMENT_CPU}}/${10}/g; s/{{PAYMENT_MEMORY}}/${11}/g; s/{{QUEUE_MASTER_CPU}}/${12}/g; s/{{QUEUE_MASTER_MEMORY}}/${13}/g; s/{{SHIPPING_CPU}}/${14}/g; s/{{SHIPPING_MEMORY}}/${15}/g; s/{{USER_CPU}}/${16}/g; s/{{USER_MEMORY}}/${17}/g"`
echo "\033[1;34m Creating Deployment... \033[0m"
# apply the yml with the substituted value
echo "$template" | kubectl apply -f -
echo "\033[1;32m Successfully Deployed\033[0m"
echo "\033[1;34m Sleeping for 10 seconds... \033[0m"
sleep 10
echo "\033[1;32m Done sleeping\033[0m"
echo "\033[1;34m Retriving Services... \033[0m"
kubectl get services --namespace=$1
echo "\033[1;32m Microservice Deployment is complete!\033[0m"
