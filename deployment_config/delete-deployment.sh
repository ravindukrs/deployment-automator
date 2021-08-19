 echo "Deleting Namespace"
 echo "$1"
 kubectl delete namespaces $1
 echo "Namespace Deleted"