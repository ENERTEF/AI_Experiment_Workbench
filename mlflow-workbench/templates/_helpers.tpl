{{/*
Placu no Horderu
*/}}
{{- define "app.host" -}}
{{- if .Values.expose.enabled -}}
{{- printf "https://%s" .Values.expose.hostname -}}
{{- else -}}
{{- printf "https://localhost" -}}
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

{{- define "flower.server_url" -}}
{{- if .Values.flower.as_hub -}}
{{- .Values.expose.hostname -}}
{{- else -}}
{{- .Values.flower.hub_domain -}}
{{- end -}}
{{- end -}}

{{- define "flower.hub_superlink" -}}
{{- printf "flwr-sv.%s:443" (include "flower.server_url" .) -}}
{{- end -}}

{{- define "flower.hub_control" -}}
{{- printf "flwr-ctrl.%s:443" (include "flower.server_url" .) -}}
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