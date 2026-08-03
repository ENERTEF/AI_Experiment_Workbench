{{- if .Values.flower.superlink.enabled -}}
{{- if empty .Values.expose.hostname -}}
{{- fail "flower.superlink.enabled=true requires expose.hostname to be set" -}}
{{- end -}}
{{- if eq .Values.expose.type "gateway" -}}
{{- if empty .Values.expose.gateway.default_gateway.name -}}
{{- fail "flower.superlink.enabled=true with gateway requires expose.gateway.default_gateway.name" -}}
{{- end -}}
{{- if empty .Values.expose.gateway.default_gateway.https_passthrough_listener -}}
{{- fail "flower.superlink.enabled=true with gateway requires https_passthrough_listener" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "app.host" -}}
{{- printf "https://%s" .Values.expose.hostname -}}
{{- end -}}


{{- define "keycloak.client_secret" -}}
{{- if .Values.auth.external.enabled -}}
{{- .Values.auth.external.client_secret -}}
{{- else -}}
{{- randAlphaNum 32 -}}
{{- end -}}
{{- end -}}

{{- define "generate_client_secret" -}}
{{- $key := "client_secret" -}}
{{- if not (index .Release "client_secret") -}}
{{- $_ := set .Release $key (include "keycloak.client_secret" .) -}}
{{- end -}}
{{- end -}}

{{- define "keycloak.client_id" -}}
{{- if .Values.auth.external.enabled -}}
{{- .Values.auth.external.client_id -}}
{{- else -}}
jhub-mlfw
{{- end -}}
{{- end -}}

{{- define "keycloak.groups_key" -}}
{{- if .Values.auth.external.enabled -}}
{{ .Values.auth.external.groups_key -}}
{{- else -}}
{{- "oauth_user.roles" -}}
{{- end -}}
{{- end -}}

{{- define "keycloak.allowed_groups" -}}
{{- if .Values.auth.external.enabled -}}
{{- .Values.auth.external.allowed_groups | toJson -}}
{{- else -}}
{{- (list "mlflow-user") | toJson -}}
{{- end -}}
{{- end -}}

{{- define "keycloak.admin_groups" -}}
{{- if .Values.auth.external.enabled -}}
{{- .Values.auth.external.admin_groups | toJson -}}
{{- else -}}
{{- (list "mlflow-admin") | toJson -}}
{{- end -}}
{{- end -}}

{{- define "keycloak.realm_url" -}}
{{- if .Values.auth.external.enabled -}}
{{- .Values.auth.external.realm_url -}}
{{- else -}}
{{- printf "%s/auth/realms/mlflow-workbench" (include "app.host" .) -}}
{{- end -}}
{{- end -}}

{{- define "keycloak.authorize_url" -}}
{{- printf "%s/protocol/openid-connect/auth" (include "keycloak.realm_url" .) -}}
{{- end -}}

{{- define "keycloak.token_url" -}}
{{- printf "%s/protocol/openid-connect/token" (include "keycloak.realm_url" .) -}}
{{- end -}}

{{- define "keycloak.userinfo_url" -}}
{{- printf "%s/protocol/openid-connect/userinfo" (include "keycloak.realm_url" .) -}}
{{- end -}}

{{- define "flower.superlink_domain" -}}
{{- if .Values.flower.superlink.enabled -}}
{{- .Values.expose.hostname -}}
{{- else -}}
{{- .Values.flower.client.superlink_addr -}}
{{- end -}}
{{- end -}}

{{- define "flower.superlink_fleet" -}}
{{- printf "flwr-sv.%s:443" (include "flower.superlink_domain" .) -}}
{{- end -}}

{{- define "flower.superlink_control" -}}
{{- printf "flwr-ctrl.%s:443" (include "flower.superlink_domain" .) -}}
{{- end -}}

{{- define "flower.tls_secretname" -}}
{{ default "flower-superlink-tls" .Values.expose.tls.secretname }}
{{- end -}}

{{- define "flower.use_default_ca" -}}
{{- if or ( and .Values.flower.superlink.enabled ( not .Values.flower.superlink.use_default_ca ) ) ( not ( empty .Values.flower.client.superlink_cert ) ) -}}
false
{{- else -}}
true
{{- end -}}
{{- end -}}

{{- define "flower.ca_path" -}}
{{- if eq (include "flower.use_default_ca" .) "true" -}}
/etc/ssl/certs/ca-certificates.crt
{{- else -}}
/app/ca.crt
{{- end -}}
{{- end -}}

{{- define "flower.ca_secretname" -}}
{{- if .Values.flower.superlink.enabled -}}
{{- include "flower.tls_secretname" . -}}
{{- else if .Values.flower.client.superlink_cert -}}
flower-root-cert
{{- else -}}
{{- printf "" -}}
{{- end -}}
{{- end -}}

{{- define "flower.caps" -}}
{{- if and  .Values.flower.client.supernode.enabled (not (empty .Values.flower.client.supernode.caps_file)) -}}
true
{{- else -}}
false
{{- end -}}
{{- end -}}

{{- define "federated.workspace_name" -}}
  ws-federated
{{- end -}}
{{- define "federated.experiment_name" -}}
  exp-federated
{{- end -}}
{{- define "federated.experiment_id" -}}
  1
{{- end -}}