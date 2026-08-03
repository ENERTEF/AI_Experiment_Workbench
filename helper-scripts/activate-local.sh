LOCAL_HOST="mlfw.hack"
SVC_ADDR="ingress-nginx-controller.ingress-nginx.svc.cluster.local"

COREFILE=$(kubectl get cm coredns -n kube-system -o jsonpath='{.data.Corefile}')
REWRITE_LINE="    rewrite name $LOCAL_HOST $SVC_ADDR"

if echo "$COREFILE" | grep -q "$LOCAL_HOST"; then
    echo "Rewrite rule already exists in CoreDNS."
else
    # Insert rewrite line before the 'kubernetes' block
    NEW_COREFILE=$(echo "$COREFILE" | awk -v new_line="$REWRITE_LINE" '
        /kubernetes cluster.local/ { print new_line }
        { print $0 }
    ')
    PATCH_JSON=$(jq -n --arg conf "$NEW_COREFILE" '{"data": {"Corefile": $conf}}')
    kubectl patch cm coredns -n kube-system --type merge -p "$PATCH_JSON"
    echo "Success: Added rewrite for $LOCAL_HOST pointing to $SVC_ADDR"
    kubectl rollout restart deployment/coredns -n kube-system
    kubectl wait deployment -n kube-system coredns --for condition=Available=True --timeout=90s
fi
