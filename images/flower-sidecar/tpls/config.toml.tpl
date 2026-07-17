[superlink]
default = "k8s"

[superlink.supergrid]
address = "supergrid.flower.ai"

[superlink.local]
address = ":local:"

[superlink.k8s]
address = "${SUPERLINK_CONTROL}"
root-certificates = "${ROOT_CERT_PATH}"