"""
Helm Packaging MCP Server — generates production-ready Helm charts,
values files, templates, and validates chart structures.

Tools:
    helm_generate_chart             Generate a complete Helm chart structure
    helm_generate_values            Generate values.yaml for an application
    helm_generate_env_values        Generate environment-specific values overrides
    helm_generate_helpers           Generate _helpers.tpl template
    helm_generate_deployment        Generate deployment.yaml for a component
    helm_generate_service           Generate service.yaml for a component
    helm_generate_ingress           Generate ingress.yaml template
    helm_validate_chart             Validate chart structure against best practices
    helm_suggest_commands           Suggest Helm CLI commands
    helm_list_templates             List available chart template patterns
"""

import json
import re
from enum import Enum
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("helm_packaging_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_COMPONENTS = ("backend", "frontend", "worker", "scheduler")
VALID_SERVICE_TYPES = ("ClusterIP", "NodePort", "LoadBalancer")
VALID_ENVIRONMENTS = ("dev", "staging", "prod")


class TemplateKind(str, Enum):
    DEPLOYMENT = "deployment"
    SERVICE = "service"
    INGRESS = "ingress"
    CONFIGMAP = "configmap"
    SECRET = "secret"
    PVC = "pvc"
    HPA = "hpa"
    SERVICEACCOUNT = "serviceaccount"
    NETWORKPOLICY = "networkpolicy"
    PDB = "pdb"
    CRONJOB = "cronjob"
    JOB = "job"
    HELPERS = "helpers"
    NOTES = "notes"


TEMPLATE_CATALOG: list[dict] = [
    {
        "kind": "deployment",
        "description": "Deployment resource for pods",
        "required": True,
    },
    {
        "kind": "service",
        "description": "Service resource for networking",
        "required": True,
    },
    {
        "kind": "ingress",
        "description": "Ingress resource for HTTP routing",
        "required": False,
    },
    {
        "kind": "configmap",
        "description": "ConfigMap for non-sensitive config",
        "required": False,
    },
    {
        "kind": "secret",
        "description": "ExternalSecret/SealedSecret references",
        "required": False,
    },
    {
        "kind": "pvc",
        "description": "PersistentVolumeClaim for storage",
        "required": False,
    },
    {
        "kind": "hpa",
        "description": "HorizontalPodAutoscaler for scaling",
        "required": False,
    },
    {
        "kind": "serviceaccount",
        "description": "ServiceAccount and RBAC",
        "required": False,
    },
    {
        "kind": "networkpolicy",
        "description": "NetworkPolicy for traffic control",
        "required": False,
    },
    {
        "kind": "pdb",
        "description": "PodDisruptionBudget for availability",
        "required": False,
    },
    {
        "kind": "cronjob",
        "description": "CronJob for scheduled tasks",
        "required": False,
    },
    {
        "kind": "job",
        "description": "Job for one-time operations / hooks",
        "required": False,
    },
    {
        "kind": "helpers",
        "description": "_helpers.tpl naming and label helpers",
        "required": True,
    },
    {
        "kind": "notes",
        "description": "NOTES.txt post-install instructions",
        "required": True,
    },
]

RESOURCE_PRESETS: dict[str, dict[str, dict[str, str]]] = {
    "dev": {
        "requests": {"cpu": "50m", "memory": "64Mi"},
        "limits": {"cpu": "200m", "memory": "256Mi"},
    },
    "staging": {
        "requests": {"cpu": "250m", "memory": "256Mi"},
        "limits": {"cpu": "500m", "memory": "512Mi"},
    },
    "prod": {
        "requests": {"cpu": "500m", "memory": "512Mi"},
        "limits": {"cpu": "1000m", "memory": "1Gi"},
    },
}

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9\-]*$")


def _validate_chart_name(v: str) -> str:
    if not _NAME_PATTERN.match(v):
        raise ValueError(
            "Chart name must be lowercase, start with a letter, "
            "and contain only [a-z0-9-]"
        )
    if len(v) > 53:
        raise ValueError("Chart name must be 53 characters or fewer")
    return v


def _validate_semver(v: str) -> str:
    if not re.match(r"^\d+\.\d+\.\d+", v):
        raise ValueError(f"Version '{v}' is not valid SemVer (expected X.Y.Z)")
    return v


# ---------------------------------------------------------------------------
# Pydantic Input Models
# ---------------------------------------------------------------------------


class ComponentSpec(BaseModel):
    """Specification for a single application component."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        description="Component name (backend, frontend, worker, etc.)",
    )
    image_repository: str = Field(
        ..., min_length=1, description="Container image repository (e.g. myapp/backend)"
    )
    image_tag: str = Field(
        "", description="Image tag (empty defaults to Chart.appVersion)"
    )
    port: int = Field(8000, ge=1, le=65535, description="Container port")
    service_type: str = Field("ClusterIP", description="Kubernetes Service type")
    replicas: int = Field(1, ge=0, le=100, description="Number of replicas")
    health_path: str = Field("/health", description="Health check endpoint path")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not _NAME_PATTERN.match(v):
            raise ValueError(
                "Component name must be lowercase alphanumeric with hyphens"
            )
        return v

    @field_validator("service_type")
    @classmethod
    def validate_service_type(cls, v: str) -> str:
        if v not in VALID_SERVICE_TYPES:
            raise ValueError(f"service_type must be one of {VALID_SERVICE_TYPES}")
        return v


class ChartGenerateInput(BaseModel):
    """Input for helm_generate_chart."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    application_name: str = Field(
        ...,
        min_length=1,
        max_length=53,
        description="Chart/application name (lowercase, hyphenated)",
    )
    description: str = Field(
        "A Helm chart for Kubernetes", description="Chart description"
    )
    version: str = Field("0.1.0", description="Chart version (SemVer)")
    app_version: str = Field("1.0.0", description="Application version")
    components: list[ComponentSpec] = Field(
        ..., min_length=1, description="Application components"
    )
    ingress_enabled: bool = Field(False, description="Enable ingress resource")
    ingress_host: str = Field("myapp.local", description="Ingress hostname")
    persistence_enabled: bool = Field(False, description="Enable persistent storage")
    persistence_size: str = Field("1Gi", description="PVC size")

    @field_validator("application_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_chart_name(v)

    @field_validator("version", "app_version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        return _validate_semver(v)


class ValuesGenerateInput(BaseModel):
    """Input for helm_generate_values."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    application_name: str = Field(..., min_length=1, description="Application name")
    components: list[ComponentSpec] = Field(
        ..., min_length=1, description="Application components"
    )
    ingress_enabled: bool = Field(False, description="Enable ingress")
    ingress_host: str = Field("myapp.local", description="Ingress hostname")
    persistence_enabled: bool = Field(False, description="Enable persistence")
    persistence_size: str = Field("1Gi", description="PVC size")

    @field_validator("application_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_chart_name(v)


class EnvValuesInput(BaseModel):
    """Input for helm_generate_env_values."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    application_name: str = Field(..., min_length=1, description="Application name")
    environment: str = Field(..., description="Target environment: dev, staging, prod")
    components: list[str] = Field(..., min_length=1, description="Component names")
    ingress_host: Optional[str] = Field(None, description="Override ingress host")

    @field_validator("application_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_chart_name(v)

    @field_validator("environment")
    @classmethod
    def validate_env(cls, v: str) -> str:
        if v not in VALID_ENVIRONMENTS:
            raise ValueError(f"environment must be one of {VALID_ENVIRONMENTS}")
        return v


class HelpersInput(BaseModel):
    """Input for helm_generate_helpers."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    application_name: str = Field(
        ..., min_length=1, description="Application name for template helpers"
    )
    components: list[str] = Field(
        default_factory=lambda: ["backend"], description="Component names"
    )

    @field_validator("application_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_chart_name(v)


class DeploymentInput(BaseModel):
    """Input for helm_generate_deployment."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    application_name: str = Field(..., min_length=1, description="Application name")
    component: str = Field(
        ..., min_length=1, description="Component name (backend, frontend, etc.)"
    )

    @field_validator("application_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_chart_name(v)


class ServiceInput(BaseModel):
    """Input for helm_generate_service."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    application_name: str = Field(..., min_length=1, description="Application name")
    components: list[str] = Field(
        ..., min_length=1, description="Component names to create services for"
    )

    @field_validator("application_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_chart_name(v)


class IngressInput(BaseModel):
    """Input for helm_generate_ingress."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    application_name: str = Field(..., min_length=1, description="Application name")

    @field_validator("application_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_chart_name(v)


class ValidateChartInput(BaseModel):
    """Input for helm_validate_chart."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    chart_yaml: Optional[str] = Field(None, description="Content of Chart.yaml")
    values_yaml: Optional[str] = Field(None, description="Content of values.yaml")
    has_helpers: bool = Field(False, description="Whether _helpers.tpl exists")
    has_notes: bool = Field(False, description="Whether NOTES.txt exists")
    template_files: list[str] = Field(
        default_factory=list, description="List of template file names present"
    )


class CommandSuggestInput(BaseModel):
    """Input for helm_suggest_commands."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    chart_name: str = Field(..., min_length=1, description="Chart/release name")
    chart_path: str = Field(".", description="Path to chart directory")
    values_file: Optional[str] = Field(None, description="Values file to use")
    namespace: Optional[str] = Field(None, description="Kubernetes namespace")
    operation: str = Field(
        "install",
        description="Operation: install, upgrade, template, lint, package, uninstall, rollback, list",
    )

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, v: str) -> str:
        valid = (
            "install",
            "upgrade",
            "template",
            "lint",
            "package",
            "uninstall",
            "rollback",
            "list",
        )
        if v not in valid:
            raise ValueError(f"operation must be one of {valid}")
        return v


# ---------------------------------------------------------------------------
# Generator functions (pure, deterministic)
# ---------------------------------------------------------------------------


def _gen_chart_yaml(name: str, description: str, version: str, app_version: str) -> str:
    return f"""\
apiVersion: v2
name: {name}
description: {description}
type: application

# Chart version (increment for chart changes)
version: {version}

# Application version
appVersion: "{app_version}"

# Kubernetes version constraint
kubeVersion: ">=1.25.0-0"

# Maintainers
maintainers:
  - name: Platform Team

# Keywords
keywords:
  - {name}
  - kubernetes
  - helm

# Dependencies
dependencies: []
"""


def _gen_helmignore() -> str:
    return """\
# Patterns to ignore when building packages.
.git
.gitignore
.DS_Store
*.swp
*.bak
*.tmp
*.orig
*~
.vscode/
.idea/
*.md
!README.md
LICENSE
.env
.env.*
"""


def _gen_values_yaml(
    components: list[ComponentSpec],
    ingress_enabled: bool,
    ingress_host: str,
    persistence_enabled: bool,
    persistence_size: str,
) -> str:
    lines: list[str] = []
    lines.append("# Default values")
    lines.append("# This is a YAML-formatted file.")
    lines.append("")
    lines.append("# -- Global settings")
    lines.append("global:")
    lines.append("  # -- Image pull secrets for all containers")
    lines.append("  imagePullSecrets: []")
    lines.append("  # -- Storage class override")
    lines.append('  storageClass: ""')
    lines.append("")

    for comp in components:
        lines.append(f"# -- Component: {comp.name}")
        lines.append(f"{comp.name}:")
        lines.append(f"  # -- Enable/disable {comp.name} component")
        lines.append("  enabled: true")
        lines.append("")
        lines.append("  # -- Number of replicas")
        lines.append(f"  replicaCount: {comp.replicas}")
        lines.append("")
        lines.append("  # -- Image configuration")
        lines.append("  image:")
        lines.append(f"    repository: {comp.image_repository}")
        tag_val = (
            comp.image_tag if comp.image_tag else '""  # Defaults to Chart.appVersion'
        )
        lines.append(f"    tag: {tag_val}")
        lines.append("    pullPolicy: IfNotPresent")
        lines.append("")
        lines.append("  # -- Service configuration")
        lines.append("  service:")
        lines.append(f"    type: {comp.service_type}")
        lines.append(f"    port: {comp.port}")
        lines.append(f"    targetPort: {comp.port}")
        lines.append("")
        lines.append("  # -- Resource requests and limits")
        lines.append("  resources:")
        lines.append("    requests:")
        lines.append("      cpu: 100m")
        lines.append("      memory: 128Mi")
        lines.append("    limits:")
        lines.append("      cpu: 500m")
        lines.append("      memory: 512Mi")
        lines.append("")
        lines.append("  # -- Environment variables")
        lines.append("  env: []")
        lines.append("  # -- Environment variables from ConfigMap/Secret")
        lines.append("  envFrom: []")
        lines.append("")
        lines.append("  # -- Liveness probe configuration")
        lines.append("  livenessProbe:")
        lines.append("    httpGet:")
        lines.append(f"      path: {comp.health_path}")
        lines.append("      port: http")
        lines.append("    initialDelaySeconds: 30")
        lines.append("    periodSeconds: 10")
        lines.append("")
        lines.append("  # -- Readiness probe configuration")
        lines.append("  readinessProbe:")
        lines.append("    httpGet:")
        lines.append(f"      path: {comp.health_path}")
        lines.append("      port: http")
        lines.append("    initialDelaySeconds: 5")
        lines.append("    periodSeconds: 5")
        lines.append("")
        lines.append("  # -- Pod annotations")
        lines.append("  podAnnotations: {}")
        lines.append("")
        lines.append("  # -- Pod security context")
        lines.append("  podSecurityContext:")
        lines.append("    fsGroup: 1000")
        lines.append("")
        lines.append("  # -- Container security context")
        lines.append("  securityContext:")
        lines.append("    runAsNonRoot: true")
        lines.append("    runAsUser: 1000")
        lines.append("")
        lines.append("  # -- Node selector")
        lines.append("  nodeSelector: {}")
        lines.append("")
        lines.append("  # -- Tolerations")
        lines.append("  tolerations: []")
        lines.append("")
        lines.append("  # -- Affinity rules")
        lines.append("  affinity: {}")
        lines.append("")

    # Ingress
    lines.append("# -- Ingress configuration")
    lines.append("ingress:")
    lines.append(f"  enabled: {'true' if ingress_enabled else 'false'}")
    lines.append("  className: nginx")
    lines.append("  annotations: {}")
    lines.append("  hosts:")
    lines.append(f"    - host: {ingress_host}")
    lines.append("      paths:")

    # Build ingress paths from components
    has_backend = any(c.name == "backend" for c in components)
    has_frontend = any(c.name == "frontend" for c in components)
    if has_backend and has_frontend:
        lines.append("        - path: /api")
        lines.append("          pathType: Prefix")
        lines.append("          service: backend")
        lines.append("        - path: /")
        lines.append("          pathType: Prefix")
        lines.append("          service: frontend")
    elif has_backend:
        lines.append("        - path: /")
        lines.append("          pathType: Prefix")
        lines.append("          service: backend")
    else:
        for comp in components:
            lines.append(f"        - path: /")
            lines.append("          pathType: Prefix")
            lines.append(f"          service: {comp.name}")
            break  # default first component

    lines.append("  tls: []")
    lines.append("")

    # Persistence
    lines.append("# -- Persistence configuration")
    lines.append("persistence:")
    lines.append(f"  enabled: {'true' if persistence_enabled else 'false'}")
    lines.append('  storageClass: ""')
    lines.append("  accessMode: ReadWriteOnce")
    lines.append(f"  size: {persistence_size}")
    lines.append("")

    # ConfigMap
    lines.append("# -- ConfigMap data")
    lines.append("configMap:")
    lines.append("  enabled: false")
    lines.append("  data: {}")
    lines.append("")

    # External Secrets
    lines.append("# -- External secrets reference")
    lines.append("externalSecrets:")
    lines.append("  enabled: false")
    lines.append("  secretStoreRef: {}")
    lines.append("")

    # ServiceAccount
    lines.append("# -- Service account configuration")
    lines.append("serviceAccount:")
    lines.append("  create: true")
    lines.append("  annotations: {}")
    lines.append('  name: ""')
    lines.append("")

    # Autoscaling
    lines.append("# -- HorizontalPodAutoscaler configuration")
    lines.append("autoscaling:")
    lines.append("  enabled: false")
    lines.append("  minReplicas: 1")
    lines.append("  maxReplicas: 10")
    lines.append("  targetCPUUtilizationPercentage: 80")
    lines.append("  targetMemoryUtilizationPercentage: 80")

    return "\n".join(lines) + "\n"


def _gen_env_values(
    environment: str,
    components: list[str],
    ingress_host: str | None,
) -> str:
    presets = RESOURCE_PRESETS[environment]
    lines: list[str] = []

    env_labels = {
        "dev": "Development/Minikube",
        "staging": "Staging",
        "prod": "Production",
    }
    replicas = {"dev": 1, "staging": 2, "prod": 3}
    log_level = {"dev": "debug", "staging": "info", "prod": "info"}
    pvc_size = {"dev": "1Gi", "staging": "10Gi", "prod": "50Gi"}
    host_suffix = {
        "dev": ".local",
        "staging": ".staging.example.com",
        "prod": ".example.com",
    }

    lines.append(f"# {env_labels[environment]} environment overrides")
    lines.append(f"# Usage: helm install myapp ./myapp -f values-{environment}.yaml")
    lines.append("")
    lines.append("global:")
    lines.append(f"  environment: {environment}")
    lines.append(f"  development: {'true' if environment == 'dev' else 'false'}")
    lines.append("")

    for comp in components:
        lines.append(f"{comp}:")
        lines.append(f"  replicaCount: {replicas[environment]}")
        lines.append("  resources:")
        lines.append("    requests:")
        lines.append(f"      cpu: {presets['requests']['cpu']}")
        lines.append(f"      memory: {presets['requests']['memory']}")
        lines.append("    limits:")
        lines.append(f"      cpu: {presets['limits']['cpu']}")
        lines.append(f"      memory: {presets['limits']['memory']}")
        lines.append("  env:")
        lines.append("    - name: LOG_LEVEL")
        lines.append(f"      value: {log_level[environment]}")
        if environment == "dev":
            lines.append("    - name: DEBUG")
            lines.append('      value: "true"')
        lines.append("")

    # Ingress
    resolved_host = ingress_host
    if not resolved_host:
        base = components[0] if components else "myapp"
        resolved_host = f"{base}{host_suffix[environment]}"

    lines.append("ingress:")
    lines.append("  enabled: true")
    if environment != "dev":
        lines.append("  className: nginx")
    lines.append("  hosts:")
    lines.append(f"    - host: {resolved_host}")
    lines.append("      paths:")

    has_backend = "backend" in components
    has_frontend = "frontend" in components
    if has_backend and has_frontend:
        lines.append("        - path: /api")
        lines.append("          pathType: Prefix")
        lines.append("          service: backend")
        lines.append("        - path: /")
        lines.append("          pathType: Prefix")
        lines.append("          service: frontend")
    else:
        first = components[0] if components else "backend"
        lines.append("        - path: /")
        lines.append("          pathType: Prefix")
        lines.append(f"          service: {first}")

    if environment == "prod":
        lines.append("  annotations:")
        lines.append("    cert-manager.io/cluster-issuer: letsencrypt-prod")
        lines.append("  tls:")
        lines.append(
            f"    - secretName: {components[0] if components else 'myapp'}-tls"
        )
        lines.append("      hosts:")
        lines.append(f"        - {resolved_host}")

    lines.append("")

    # Autoscaling for staging/prod
    if environment in ("staging", "prod"):
        max_r = 5 if environment == "staging" else 10
        cpu_target = 75 if environment == "staging" else 70
        lines.append("autoscaling:")
        lines.append("  enabled: true")
        lines.append(f"  minReplicas: {replicas[environment]}")
        lines.append(f"  maxReplicas: {max_r}")
        lines.append(f"  targetCPUUtilizationPercentage: {cpu_target}")
        lines.append("")

    # Persistence
    lines.append("persistence:")
    lines.append("  enabled: true")
    if environment == "prod":
        lines.append("  storageClass: fast-ssd")
    lines.append(f"  size: {pvc_size[environment]}")

    return "\n".join(lines) + "\n"


def _gen_helpers_tpl(app_name: str, components: list[str]) -> str:
    lines: list[str] = []
    lines.append("{{/*")
    lines.append("Expand the name of the chart.")
    lines.append("*/}}")
    lines.append(f'{{{{- define "{app_name}.name" -}}}}')
    lines.append(
        f'{{{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}}}'
    )
    lines.append("{{- end }}")
    lines.append("")
    lines.append("{{/*")
    lines.append("Create a default fully qualified app name.")
    lines.append("*/}}")
    lines.append(f'{{{{- define "{app_name}.fullname" -}}}}')
    lines.append("{{- if .Values.fullnameOverride }}")
    lines.append('{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}')
    lines.append("{{- else }}")
    lines.append("{{- $name := default .Chart.Name .Values.nameOverride }}")
    lines.append("{{- if contains $name .Release.Name }}")
    lines.append('{{- .Release.Name | trunc 63 | trimSuffix "-" }}')
    lines.append("{{- else }}")
    lines.append(
        '{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}'
    )
    lines.append("{{- end }}")
    lines.append("{{- end }}")
    lines.append("{{- end }}")
    lines.append("")
    lines.append("{{/*")
    lines.append("Create chart name and version as used by the chart label.")
    lines.append("*/}}")
    lines.append(f'{{{{- define "{app_name}.chart" -}}}}')
    lines.append(
        '{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}'
    )
    lines.append("{{- end }}")
    lines.append("")
    lines.append("{{/*")
    lines.append("Common labels")
    lines.append("*/}}")
    lines.append(f'{{{{- define "{app_name}.labels" -}}}}')
    lines.append(f'helm.sh/chart: {{{{{{ include "{app_name}.chart" . }}}}}}')
    lines.append(f'{{{{{{ include "{app_name}.selectorLabels" . }}}}}}')
    lines.append("{{- if .Chart.AppVersion }}")
    lines.append("app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}")
    lines.append("{{- end }}")
    lines.append("app.kubernetes.io/managed-by: {{ .Release.Service }}")
    lines.append("{{- end }}")
    lines.append("")
    lines.append("{{/*")
    lines.append("Selector labels")
    lines.append("*/}}")
    lines.append(f'{{{{- define "{app_name}.selectorLabels" -}}}}')
    lines.append(f'app.kubernetes.io/name: {{{{{{ include "{app_name}.name" . }}}}}}')
    lines.append("app.kubernetes.io/instance: {{ .Release.Name }}")
    lines.append("{{- end }}")
    lines.append("")
    lines.append("{{/*")
    lines.append("Create the name of the service account to use")
    lines.append("*/}}")
    lines.append(f'{{{{- define "{app_name}.serviceAccountName" -}}}}')
    lines.append("{{- if .Values.serviceAccount.create }}")
    lines.append(
        f'{{{{- default (include "{app_name}.fullname" .) .Values.serviceAccount.name }}}}'
    )
    lines.append("{{- else }}")
    lines.append('{{- default "default" .Values.serviceAccount.name }}')
    lines.append("{{- end }}")
    lines.append("{{- end }}")

    # Component-specific fullname helpers
    for comp in components:
        lines.append("")
        lines.append("{{/*")
        lines.append(f"{comp.capitalize()} fullname")
        lines.append("*/}}")
        lines.append(f'{{{{- define "{app_name}.{comp}.fullname" -}}}}')
        lines.append(f'{{{{- printf "%s-{comp}" (include "{app_name}.fullname" .) }}}}')
        lines.append("{{- end }}")

    return "\n".join(lines) + "\n"


def _gen_deployment_yaml(app_name: str, component: str) -> str:
    return f"""\
{{{{- if .Values.{component}.enabled }}}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{{{{{ include "{app_name}.{component}.fullname" . }}}}}}
  labels:
    {{{{- include "{app_name}.labels" . | nindent 4 }}}}
    app.kubernetes.io/component: {component}
spec:
  replicas: {{{{{{ .Values.{component}.replicaCount }}}}}}
  selector:
    matchLabels:
      {{{{- include "{app_name}.selectorLabels" . | nindent 6 }}}}
      app.kubernetes.io/component: {component}
  template:
    metadata:
      {{{{- with .Values.{component}.podAnnotations }}}}
      annotations:
        {{{{- toYaml . | nindent 8 }}}}
      {{{{- end }}}}
      labels:
        {{{{- include "{app_name}.selectorLabels" . | nindent 8 }}}}
        app.kubernetes.io/component: {component}
    spec:
      {{{{- with .Values.global.imagePullSecrets }}}}
      imagePullSecrets:
        {{{{- toYaml . | nindent 8 }}}}
      {{{{- end }}}}
      serviceAccountName: {{{{{{ include "{app_name}.serviceAccountName" . }}}}}}
      securityContext:
        {{{{- toYaml .Values.{component}.podSecurityContext | nindent 8 }}}}
      containers:
        - name: {component}
          securityContext:
            {{{{- toYaml .Values.{component}.securityContext | nindent 12 }}}}
          image: "{{{{{{ .Values.{component}.image.repository }}}}}}:{{{{{{ .Values.{component}.image.tag | default .Chart.AppVersion }}}}}}"
          imagePullPolicy: {{{{{{ .Values.{component}.image.pullPolicy }}}}}}
          ports:
            - name: http
              containerPort: {{{{{{ .Values.{component}.service.targetPort }}}}}}
              protocol: TCP
          {{{{- with .Values.{component}.env }}}}
          env:
            {{{{- toYaml . | nindent 12 }}}}
          {{{{- end }}}}
          {{{{- with .Values.{component}.envFrom }}}}
          envFrom:
            {{{{- toYaml . | nindent 12 }}}}
          {{{{- end }}}}
          livenessProbe:
            {{{{- toYaml .Values.{component}.livenessProbe | nindent 12 }}}}
          readinessProbe:
            {{{{- toYaml .Values.{component}.readinessProbe | nindent 12 }}}}
          resources:
            {{{{- toYaml .Values.{component}.resources | nindent 12 }}}}
      {{{{- with .Values.{component}.nodeSelector }}}}
      nodeSelector:
        {{{{- toYaml . | nindent 8 }}}}
      {{{{- end }}}}
      {{{{- with .Values.{component}.affinity }}}}
      affinity:
        {{{{- toYaml . | nindent 8 }}}}
      {{{{- end }}}}
      {{{{- with .Values.{component}.tolerations }}}}
      tolerations:
        {{{{- toYaml . | nindent 8 }}}}
      {{{{- end }}}}
{{{{- end }}}}
"""


def _gen_service_yaml(app_name: str, components: list[str]) -> str:
    parts: list[str] = []
    for i, comp in enumerate(components):
        if i > 0:
            parts.append("---")
        parts.append(f"{{{{- if .Values.{comp}.enabled }}}}")
        parts.append("apiVersion: v1")
        parts.append("kind: Service")
        parts.append("metadata:")
        parts.append(f'  name: {{{{{{ include "{app_name}.{comp}.fullname" . }}}}}}')
        parts.append("  labels:")
        parts.append(f'    {{{{- include "{app_name}.labels" . | nindent 4 }}}}')
        parts.append(f"    app.kubernetes.io/component: {comp}")
        parts.append("spec:")
        parts.append(f"  type: {{{{{{ .Values.{comp}.service.type }}}}}}")
        parts.append("  ports:")
        parts.append(f"    - port: {{{{{{ .Values.{comp}.service.port }}}}}}")
        parts.append(
            f"      targetPort: {{{{{{ .Values.{comp}.service.targetPort }}}}}}"
        )
        parts.append("      protocol: TCP")
        parts.append("      name: http")
        parts.append("  selector:")
        parts.append(
            f'    {{{{- include "{app_name}.selectorLabels" . | nindent 4 }}}}'
        )
        parts.append(f"    app.kubernetes.io/component: {comp}")
        parts.append("{{- end }}")

    return "\n".join(parts) + "\n"


def _gen_ingress_yaml(app_name: str) -> str:
    return f"""\
{{{{- if .Values.ingress.enabled -}}}}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{{{{{ include "{app_name}.fullname" . }}}}}}
  labels:
    {{{{- include "{app_name}.labels" . | nindent 4 }}}}
  {{{{- with .Values.ingress.annotations }}}}
  annotations:
    {{{{- toYaml . | nindent 4 }}}}
  {{{{- end }}}}
spec:
  {{{{- if .Values.ingress.className }}}}
  ingressClassName: {{{{{{ .Values.ingress.className }}}}}}
  {{{{- end }}}}
  {{{{- if .Values.ingress.tls }}}}
  tls:
    {{{{- range .Values.ingress.tls }}}}
    - hosts:
        {{{{- range .hosts }}}}
        - {{{{{{ . | quote }}}}}}
        {{{{- end }}}}
      secretName: {{{{{{ .secretName }}}}}}
    {{{{- end }}}}
  {{{{- end }}}}
  rules:
    {{{{- range .Values.ingress.hosts }}}}
    - host: {{{{{{ .host | quote }}}}}}
      http:
        paths:
          {{{{- range .paths }}}}
          - path: {{{{{{ .path }}}}}}
            pathType: {{{{{{ .pathType }}}}}}
            backend:
              service:
                {{{{- if eq .service "backend" }}}}
                name: {{{{{{ include "{app_name}.backend.fullname" $ }}}}}}
                port:
                  number: {{{{{{ $.Values.backend.service.port }}}}}}
                {{{{- else if eq .service "frontend" }}}}
                name: {{{{{{ include "{app_name}.frontend.fullname" $ }}}}}}
                port:
                  number: {{{{{{ $.Values.frontend.service.port }}}}}}
                {{{{- end }}}}
          {{{{- end }}}}
    {{{{- end }}}}
{{{{- end }}}}
"""


def _gen_notes_txt(app_name: str, components: list[str]) -> str:
    parts: list[str] = []
    parts.append(f"Thank you for installing {{{{{{ .Chart.Name }}}}}}!")
    parts.append("")
    parts.append(f"Your release is named: {{{{{{ .Release.Name }}}}}}")
    parts.append(f"Chart version: {{{{{{ .Chart.Version }}}}}}")
    parts.append(f"App version: {{{{{{ .Chart.AppVersion }}}}}}")
    parts.append("")
    parts.append("{{- if .Values.ingress.enabled }}")
    parts.append("")
    parts.append("=== Ingress Access ===")
    parts.append("")
    parts.append("Your application is accessible via:")
    parts.append("{{- range .Values.ingress.hosts }}")
    parts.append("  http{{ if $.Values.ingress.tls }}s{{ end }}://{{ .host }}")
    parts.append("{{- end }}")
    parts.append("")
    parts.append("{{- else }}")
    parts.append("")
    parts.append("=== Service Access ===")

    for comp in components:
        parts.append("")
        parts.append(f"{{{{- if .Values.{comp}.enabled }}}}")
        parts.append(f"{comp.capitalize()}:")
        parts.append(
            f'  kubectl port-forward svc/{{{{{{ include "{app_name}.{comp}.fullname" . }}}}}} {{{{{{ .Values.{comp}.service.port }}}}}}:{{{{{{ .Values.{comp}.service.port }}}}}}'
        )
        parts.append(
            f"  Then visit: http://localhost:{{{{{{ .Values.{comp}.service.port }}}}}}"
        )
        parts.append("{{- end }}")

    parts.append("")
    parts.append("{{- end }}")
    parts.append("")
    parts.append("=== Useful Commands ===")
    parts.append("")
    parts.append("# View all deployed resources")
    parts.append("kubectl get all -l app.kubernetes.io/instance={{ .Release.Name }}")
    parts.append("")
    parts.append("# View logs")
    parts.append("kubectl logs -l app.kubernetes.io/instance={{ .Release.Name }} -f")
    parts.append("")
    parts.append("# Upgrade the release")
    parts.append("helm upgrade {{ .Release.Name }} ./{{ .Chart.Name }} -f values.yaml")
    parts.append("")
    parts.append("# Uninstall the release")
    parts.append("helm uninstall {{ .Release.Name }}")

    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def helm_generate_chart(
    application_name: str,
    description: str = "A Helm chart for Kubernetes",
    version: str = "0.1.0",
    app_version: str = "1.0.0",
    components: list[dict] = None,
    ingress_enabled: bool = False,
    ingress_host: str = "myapp.local",
    persistence_enabled: bool = False,
    persistence_size: str = "1Gi",
) -> str:
    """Generate a complete Helm chart structure with all required files.

    Returns JSON with Chart.yaml, values.yaml, _helpers.tpl, deployment.yaml,
    service.yaml, ingress.yaml, NOTES.txt, and .helmignore content.
    All templates follow Helm 3 best practices with security hardening.
    """
    # Validate and parse components
    if not components:
        return json.dumps(
            {"status": "error", "error": "At least one component is required"}
        )

    parsed = ChartGenerateInput(
        application_name=application_name,
        description=description,
        version=version,
        app_version=app_version,
        components=[ComponentSpec(**c) for c in components],
        ingress_enabled=ingress_enabled,
        ingress_host=ingress_host,
        persistence_enabled=persistence_enabled,
        persistence_size=persistence_size,
    )

    comp_names = [c.name for c in parsed.components]

    chart_yaml = _gen_chart_yaml(
        parsed.application_name, parsed.description, parsed.version, parsed.app_version
    )
    helmignore = _gen_helmignore()
    values_yaml = _gen_values_yaml(
        parsed.components,
        parsed.ingress_enabled,
        parsed.ingress_host,
        parsed.persistence_enabled,
        parsed.persistence_size,
    )
    helpers_tpl = _gen_helpers_tpl(parsed.application_name, comp_names)
    notes_txt = _gen_notes_txt(parsed.application_name, comp_names)

    deployments = {}
    for comp in comp_names:
        deployments[f"deployment-{comp}.yaml"] = _gen_deployment_yaml(
            parsed.application_name, comp
        )

    service_yaml = _gen_service_yaml(parsed.application_name, comp_names)
    ingress_yaml = _gen_ingress_yaml(parsed.application_name)

    directory_layout = [
        f"{parsed.application_name}/",
        f"  Chart.yaml",
        f"  values.yaml",
        f"  .helmignore",
        f"  templates/",
        f"    _helpers.tpl",
        f"    NOTES.txt",
    ]
    for dep_name in deployments:
        directory_layout.append(f"    {dep_name}")
    directory_layout.append("    service.yaml")
    directory_layout.append("    ingress.yaml")

    return json.dumps(
        {
            "status": "success",
            "directory_layout": "\n".join(directory_layout),
            "files": {
                "Chart.yaml": chart_yaml,
                "values.yaml": values_yaml,
                ".helmignore": helmignore,
                "templates/_helpers.tpl": helpers_tpl,
                "templates/NOTES.txt": notes_txt,
                "templates/service.yaml": service_yaml,
                "templates/ingress.yaml": ingress_yaml,
                **{f"templates/{k}": v for k, v in deployments.items()},
            },
            "notes": [
                "Chart API: v2 (Helm 3)",
                "Security: non-root containers, security contexts configured",
                "Health: liveness and readiness probes included",
                "Minikube: compatible with default resource limits",
                "WARNING: Review and adjust all templates before deploying",
            ],
        },
        indent=2,
    )


@mcp.tool()
async def helm_generate_values(
    application_name: str,
    components: list[dict] = None,
    ingress_enabled: bool = False,
    ingress_host: str = "myapp.local",
    persistence_enabled: bool = False,
    persistence_size: str = "1Gi",
) -> str:
    """Generate a values.yaml file for a Helm chart with documented defaults.

    Returns JSON: {status, content, notes}
    All values are parameterized with sensible development defaults.
    """
    if not components:
        return json.dumps(
            {"status": "error", "error": "At least one component is required"}
        )

    parsed = ValuesGenerateInput(
        application_name=application_name,
        components=[ComponentSpec(**c) for c in components],
        ingress_enabled=ingress_enabled,
        ingress_host=ingress_host,
        persistence_enabled=persistence_enabled,
        persistence_size=persistence_size,
    )

    content = _gen_values_yaml(
        parsed.components,
        parsed.ingress_enabled,
        parsed.ingress_host,
        parsed.persistence_enabled,
        parsed.persistence_size,
    )

    return json.dumps(
        {
            "status": "success",
            "content": content,
            "notes": [
                "All values documented with # -- comments",
                "Components toggleable via enabled: true/false",
                "No secrets in values.yaml (use externalSecrets)",
                "Resource defaults suitable for Minikube",
            ],
        }
    )


@mcp.tool()
async def helm_generate_env_values(
    application_name: str,
    environment: str,
    components: list[str] = None,
    ingress_host: str | None = None,
) -> str:
    """Generate environment-specific values override file (dev/staging/prod).

    Returns JSON: {status, filename, content, notes}
    Provides pre-configured resources, replicas, and settings per environment.
    """
    if not components:
        return json.dumps(
            {"status": "error", "error": "At least one component name is required"}
        )

    parsed = EnvValuesInput(
        application_name=application_name,
        environment=environment,
        components=components,
        ingress_host=ingress_host,
    )

    content = _gen_env_values(
        parsed.environment, parsed.components, parsed.ingress_host
    )
    filename = f"values-{parsed.environment}.yaml"

    return json.dumps(
        {
            "status": "success",
            "filename": filename,
            "content": content,
            "notes": [
                f"Environment: {parsed.environment}",
                f"Usage: helm install {parsed.application_name} ./{parsed.application_name} -f {filename}",
                "Override only what differs from base values.yaml",
            ],
        }
    )


@mcp.tool()
async def helm_generate_helpers(
    application_name: str,
    components: list[str] = None,
) -> str:
    """Generate _helpers.tpl with naming conventions, labels, and selector helpers.

    Returns JSON: {status, content, helpers_defined}
    Provides standard Helm naming, labeling, and service account helpers.
    """
    if not components:
        components = ["backend"]

    parsed = HelpersInput(
        application_name=application_name,
        components=components,
    )

    content = _gen_helpers_tpl(parsed.application_name, parsed.components)

    helpers_defined = [
        f"{parsed.application_name}.name",
        f"{parsed.application_name}.fullname",
        f"{parsed.application_name}.chart",
        f"{parsed.application_name}.labels",
        f"{parsed.application_name}.selectorLabels",
        f"{parsed.application_name}.serviceAccountName",
    ]
    for comp in parsed.components:
        helpers_defined.append(f"{parsed.application_name}.{comp}.fullname")

    return json.dumps(
        {
            "status": "success",
            "content": content,
            "helpers_defined": helpers_defined,
        }
    )


@mcp.tool()
async def helm_generate_deployment(
    application_name: str,
    component: str,
) -> str:
    """Generate a deployment.yaml template for a specific component.

    Returns JSON: {status, content, notes}
    Includes security context, probes, resource limits, and image configuration.
    """
    parsed = DeploymentInput(
        application_name=application_name,
        component=component,
    )

    content = _gen_deployment_yaml(parsed.application_name, parsed.component)

    return json.dumps(
        {
            "status": "success",
            "content": content,
            "notes": [
                f"Component: {parsed.component}",
                "Security: pod and container security contexts",
                "Probes: liveness and readiness configured",
                "Resources: configurable via values.yaml",
            ],
        }
    )


@mcp.tool()
async def helm_generate_service(
    application_name: str,
    components: list[str] = None,
) -> str:
    """Generate service.yaml templates for one or more components.

    Returns JSON: {status, content, notes}
    Creates Kubernetes Service resources with configurable type and ports.
    """
    if not components:
        components = ["backend"]

    parsed = ServiceInput(
        application_name=application_name,
        components=components,
    )

    content = _gen_service_yaml(parsed.application_name, parsed.components)

    return json.dumps(
        {
            "status": "success",
            "content": content,
            "notes": [
                f"Services: {', '.join(parsed.components)}",
                "Type configurable via values.yaml (ClusterIP, NodePort, LoadBalancer)",
                "Port mapping: service port -> target port",
            ],
        }
    )


@mcp.tool()
async def helm_generate_ingress(
    application_name: str,
) -> str:
    """Generate ingress.yaml template with multi-service routing.

    Returns JSON: {status, content, notes}
    Supports TLS, path-based routing, and ingress class configuration.
    """
    parsed = IngressInput(application_name=application_name)

    content = _gen_ingress_yaml(parsed.application_name)

    return json.dumps(
        {
            "status": "success",
            "content": content,
            "notes": [
                "Conditional creation via ingress.enabled",
                "Supports TLS termination",
                "Path-based routing to backend/frontend services",
                "IngressClassName configurable",
            ],
        }
    )


@mcp.tool()
async def helm_validate_chart(
    chart_yaml: str | None = None,
    values_yaml: str | None = None,
    has_helpers: bool = False,
    has_notes: bool = False,
    template_files: list[str] = None,
) -> str:
    """Validate a Helm chart structure against best practices.

    Returns JSON: {checks, warnings, score}
    Evaluates Chart.yaml, values.yaml, templates, and Minikube compatibility.
    """
    if template_files is None:
        template_files = []

    parsed = ValidateChartInput(
        chart_yaml=chart_yaml,
        values_yaml=values_yaml,
        has_helpers=has_helpers,
        has_notes=has_notes,
        template_files=template_files,
    )

    checks: dict[str, bool] = {}
    warnings: list[str] = []
    total = 0
    passed = 0

    # Chart.yaml checks
    if parsed.chart_yaml:
        total += 4
        has_api_v2 = "apiVersion: v2" in parsed.chart_yaml
        checks["chart_yaml_api_v2"] = has_api_v2
        passed += int(has_api_v2)
        if not has_api_v2:
            warnings.append("Chart.yaml should use apiVersion: v2 for Helm 3")

        has_name = "name:" in parsed.chart_yaml
        checks["chart_yaml_has_name"] = has_name
        passed += int(has_name)
        if not has_name:
            warnings.append("Chart.yaml is missing 'name' field")

        has_version = "version:" in parsed.chart_yaml
        checks["chart_yaml_has_version"] = has_version
        passed += int(has_version)
        if not has_version:
            warnings.append("Chart.yaml is missing 'version' field")

        has_app_version = "appVersion:" in parsed.chart_yaml
        checks["chart_yaml_has_app_version"] = has_app_version
        passed += int(has_app_version)
        if not has_app_version:
            warnings.append("Chart.yaml is missing 'appVersion' field")
    else:
        total += 1
        checks["chart_yaml_present"] = False
        warnings.append("Chart.yaml not provided for validation")

    # values.yaml checks
    if parsed.values_yaml:
        total += 4
        has_resources = "resources:" in parsed.values_yaml
        checks["values_has_resources"] = has_resources
        passed += int(has_resources)
        if not has_resources:
            warnings.append("values.yaml should define resource requests/limits")

        has_image = "image:" in parsed.values_yaml
        checks["values_has_image"] = has_image
        passed += int(has_image)
        if not has_image:
            warnings.append("values.yaml should define image configuration")

        has_enabled = "enabled:" in parsed.values_yaml
        checks["values_has_enabled_toggle"] = has_enabled
        passed += int(has_enabled)
        if not has_enabled:
            warnings.append("Components should be toggleable via enabled: true/false")

        # Check for hardcoded secrets
        secret_patterns = re.compile(
            r"(?:password|secret|token|api_key|credential)\s*:\s*['\"]?[^\s{][^'\"}\s]+",
            re.IGNORECASE,
        )
        has_secrets = bool(secret_patterns.search(parsed.values_yaml))
        checks["values_no_hardcoded_secrets"] = not has_secrets
        passed += int(not has_secrets)
        if has_secrets:
            warnings.append(
                "Possible hardcoded secret in values.yaml — use externalSecrets instead"
            )
    else:
        total += 1
        checks["values_yaml_present"] = False
        warnings.append("values.yaml not provided for validation")

    # Template checks
    total += 2
    checks["has_helpers_tpl"] = parsed.has_helpers
    passed += int(parsed.has_helpers)
    if not parsed.has_helpers:
        warnings.append("Missing _helpers.tpl — naming and labels will be inconsistent")

    checks["has_notes_txt"] = parsed.has_notes
    passed += int(parsed.has_notes)
    if not parsed.has_notes:
        warnings.append("Missing NOTES.txt — no post-install instructions for users")

    has_deployment = any("deployment" in f.lower() for f in parsed.template_files)
    has_service = any(
        "service" in f.lower() and "account" not in f.lower()
        for f in parsed.template_files
    )
    total += 2
    checks["has_deployment_template"] = has_deployment
    passed += int(has_deployment)
    if not has_deployment:
        warnings.append("No deployment template found")

    checks["has_service_template"] = has_service
    passed += int(has_service)
    if not has_service:
        warnings.append("No service template found")

    score = round((passed / total * 100) if total > 0 else 0, 1)

    return json.dumps(
        {
            "checks": checks,
            "warnings": warnings,
            "passed": passed,
            "total": total,
            "score": score,
            "rating": (
                "GOOD" if score >= 80 else "NEEDS WORK" if score >= 50 else "INCOMPLETE"
            ),
        }
    )


@mcp.tool()
async def helm_suggest_commands(
    chart_name: str,
    chart_path: str = ".",
    values_file: str | None = None,
    namespace: str | None = None,
    operation: str = "install",
) -> str:
    """Suggest Helm CLI commands for common operations.

    Returns JSON: {command, notes}
    Operations: install, upgrade, template, lint, package, uninstall, rollback, list.
    This is a SUGGESTION — not executed.
    """
    parsed = CommandSuggestInput(
        chart_name=chart_name,
        chart_path=chart_path,
        values_file=values_file,
        namespace=namespace,
        operation=operation,
    )

    parts: list[str] = []
    notes: list[str] = ["SUGGESTION ONLY — not executed"]

    match parsed.operation:
        case "install":
            parts.append(f"helm install {parsed.chart_name} {parsed.chart_path}")
            if parsed.values_file:
                parts.append(f"    -f {parsed.values_file}")
            if parsed.namespace:
                parts.append(f"    --namespace {parsed.namespace}")
                parts.append("    --create-namespace")
            notes.append("Add --dry-run --debug to preview before actual install")

        case "upgrade":
            parts.append(f"helm upgrade {parsed.chart_name} {parsed.chart_path}")
            if parsed.values_file:
                parts.append(f"    -f {parsed.values_file}")
            if parsed.namespace:
                parts.append(f"    --namespace {parsed.namespace}")
            notes.append("Add --install to create release if it doesn't exist")

        case "template":
            parts.append(f"helm template {parsed.chart_name} {parsed.chart_path}")
            if parsed.values_file:
                parts.append(f"    -f {parsed.values_file}")
            notes.append("Renders templates locally for review (no cluster needed)")

        case "lint":
            parts.append(f"helm lint {parsed.chart_path}")
            if parsed.values_file:
                parts.append(f"    -f {parsed.values_file}")
            notes.append("Checks chart for issues and best practices")

        case "package":
            parts.append(f"helm package {parsed.chart_path}")
            notes.append("Creates a .tgz archive for distribution")

        case "uninstall":
            parts.append(f"helm uninstall {parsed.chart_name}")
            if parsed.namespace:
                parts.append(f"    --namespace {parsed.namespace}")
            notes.append("Add --keep-history to preserve release history")

        case "rollback":
            parts.append(f"helm rollback {parsed.chart_name} 0")
            if parsed.namespace:
                parts.append(f"    --namespace {parsed.namespace}")
            notes.append("Replace '0' with the revision number to rollback to")
            notes.append("Use 'helm history' to see available revisions")

        case "list":
            parts.append("helm list")
            if parsed.namespace:
                parts.append(f"    --namespace {parsed.namespace}")
            else:
                parts.append("    --all-namespaces")
            notes.append("Shows all Helm releases")

    command = " \\\n".join(parts)

    return json.dumps(
        {
            "command": command,
            "notes": notes,
        }
    )


@mcp.tool()
async def helm_list_templates() -> str:
    """List all available Helm chart template patterns.

    Returns JSON: {status, templates, resource_presets}
    Each template describes a Kubernetes resource type and whether it's required.
    """
    return json.dumps(
        {
            "status": "success",
            "templates": TEMPLATE_CATALOG,
            "resource_presets": RESOURCE_PRESETS,
            "supported_environments": list(VALID_ENVIRONMENTS),
            "supported_service_types": list(VALID_SERVICE_TYPES),
        }
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
