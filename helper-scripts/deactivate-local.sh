LOCAL_HOST="mlfw.hack"
SVC_ADDR="ingress-nginx-controller.ingress-nginx.svc.cluster.local"

COREFILE=$(kubectl get cm coredns -n kube-system -o jsonpath='{.data.Corefile}')
REWRITE_LINE="        rewrite name $LOCAL_HOST $SVC_ADDR"

if echo "$COREFILE" | grep -q "$LOCAL_HOST"; then
    NEW_COREFILE=$(echo "$COREFILE" | grep -v "$LOCAL_HOST" || true)
    PATCH_JSON=$(jq -n --arg conf "$NEW_COREFILE" '{"data": {"Corefile": $conf}}')
    kubectl patch cm coredns -n kube-system --type merge -p "$PATCH_JSON"
    echo "Success: Removed rewrite for $LOCAL_HOST"
    kubectl rollout restart deployment/coredns -n kube-system
    kubectl wait deployment -n kube-system coredns --for condition=Available=True --timeout=90s
else
    echo "Nothing to remove."
fi
