"""
Kubernetes Deployment MCP Server — generates validated Kubernetes Deployment,
Service, and ConfigMap manifests and validates manifest structure.

Tools:
    k8s_generate_deployment     Generate a Deployment manifest (apps/v1)
    k8s_generate_service        Generate a Service manifest (v1)
    k8s_generate_configmap      Generate a ConfigMap manifest (v1)
    k8s_generate_stack          Generate a full deployment stack
    k8s_validate_manifest       Validate a manifest YAML structurally
"""

import json
import re
from typing import Optional

import yaml
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("k8s_deployment_mcp")

# ---------------------------------------------------------------------------
# Constants & regex patterns
# ---------------------------------------------------------------------------

_DNS_1123_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
_CPU_RE = re.compile(r"^(\d+m|\d+(\.\d+)?)$")
_MEM_RE = re.compile(r"^\d+(Ki|Mi|Gi|Ti)?$")
_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

VALID_SERVICE_TYPES = ("ClusterIP", "NodePort", "LoadBalancer")


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_dns1123(label: str, v: str) -> str:
    if not _DNS_1123_RE.match(v):
        raise ValueError(
            f"{label} must be a DNS-1123 subdomain (lowercase, alphanumeric, hyphens)"
        )
    if len(v) > 63:
        raise ValueError(f"{label} must be 63 characters or fewer")
    return v


# ---------------------------------------------------------------------------
# Pydantic sub-models
# ---------------------------------------------------------------------------


class PortConfig(BaseModel):
    """Container port definition."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ..., min_length=1, max_length=15, description="Port name — DNS-1123 label"
    )
    container_port: int = Field(
        ..., ge=1, le=65535, description="Container port number"
    )
    protocol: str = Field("TCP", description="TCP or UDP")

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not _DNS_1123_RE.match(v):
            raise ValueError(
                "Port name must be DNS-1123: lowercase alphanumeric, hyphens, 1-15 chars"
            )
        return v

    @field_validator("protocol")
    @classmethod
    def _validate_protocol(cls, v: str) -> str:
        if v not in ("TCP", "UDP"):
            raise ValueError("protocol must be TCP or UDP")
        return v


class EnvVar(BaseModel):
    """Environment variable (name = value)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=128, description="Env var name")
    value: str = Field(..., max_length=1024, description="Env var value")

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not _ENV_NAME_RE.match(v):
            raise ValueError("Env var name must match [A-Za-z_][A-Za-z0-9_]*")
        return v


class ResourceRequirements(BaseModel):
    """CPU/memory requests and limits."""

    model_config = ConfigDict(extra="forbid")

    requests_cpu: Optional[str] = Field(None, description="CPU request (e.g. '100m')")
    requests_memory: Optional[str] = Field(
        None, description="Memory request (e.g. '128Mi')"
    )
    limits_cpu: Optional[str] = Field(None, description="CPU limit (e.g. '200m')")
    limits_memory: Optional[str] = Field(
        None, description="Memory limit (e.g. '256Mi')"
    )

    @field_validator("requests_cpu", "limits_cpu")
    @classmethod
    def _validate_cpu(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _CPU_RE.match(v):
            raise ValueError(
                "CPU must be millicores (e.g. '100m') or decimal cores (e.g. '0.5')"
            )
        return v

    @field_validator("requests_memory", "limits_memory")
    @classmethod
    def _validate_memory(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _MEM_RE.match(v):
            raise ValueError("Memory must be numeric with unit (Ki|Mi|Gi|Ti)")
        return v


class ServicePort(BaseModel):
    """Service port mapping."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=15, description="Port name")
    port: int = Field(..., ge=1, le=65535, description="Service-facing port")
    target_port: int = Field(..., ge=1, le=65535, description="Container target port")
    protocol: str = Field("TCP", description="TCP or UDP")


# ---------------------------------------------------------------------------
# Tool input models (validated wrappers)
# ---------------------------------------------------------------------------


class DeploymentToolInput(BaseModel):
    """Validated top-level fields for k8s_generate_deployment / k8s_generate_stack."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    app_name: str = Field(..., min_length=1, max_length=63)
    image: str = Field(..., min_length=1)
    replicas: int = Field(1, ge=1, le=1000)
    namespace: str = Field("default", min_length=1, max_length=63)

    @field_validator("app_name")
    @classmethod
    def _validate_app(cls, v: str) -> str:
        return _validate_dns1123("app_name", v)

    @field_validator("namespace")
    @classmethod
    def _validate_ns(cls, v: str) -> str:
        return _validate_dns1123("namespace", v)


class ServiceToolInput(BaseModel):
    """Validated top-level fields for k8s_generate_service."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    app_name: str = Field(..., min_length=1, max_length=63)
    namespace: str = Field("default", min_length=1, max_length=63)
    service_type: str = Field("ClusterIP")

    @field_validator("app_name")
    @classmethod
    def _validate_app(cls, v: str) -> str:
        return _validate_dns1123("app_name", v)

    @field_validator("namespace")
    @classmethod
    def _validate_ns(cls, v: str) -> str:
        return _validate_dns1123("namespace", v)

    @field_validator("service_type")
    @classmethod
    def _validate_svc_type(cls, v: str) -> str:
        if v not in VALID_SERVICE_TYPES:
            raise ValueError(f"service_type must be one of {VALID_SERVICE_TYPES}")
        return v


class ConfigMapToolInput(BaseModel):
    """Validated top-level fields for k8s_generate_configmap."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    app_name: str = Field(..., min_length=1, max_length=63)
    namespace: str = Field("default", min_length=1, max_length=63)

    @field_validator("app_name")
    @classmethod
    def _validate_app(cls, v: str) -> str:
        return _validate_dns1123("app_name", v)

    @field_validator("namespace")
    @classmethod
    def _validate_ns(cls, v: str) -> str:
        return _validate_dns1123("namespace", v)


# ---------------------------------------------------------------------------
# Pure generation functions
# ---------------------------------------------------------------------------


def _base_labels(app_name: str, extra: Optional[dict] = None) -> dict:
    """Standard labels applied to every resource."""
    labels: dict = {
        "app": app_name,
        "app.kubernetes.io/name": app_name,
        "app.kubernetes.io/managed-by": "k8s-deployment-skill",
    }
    if extra:
        labels.update(extra)
    return labels


def _resource_block(resources: Optional[ResourceRequirements]) -> Optional[dict]:
    """Convert ResourceRequirements → K8s resources block. Returns None if empty."""
    if resources is None:
        return None
    block: dict = {}
    reqs: dict = {}
    if resources.requests_cpu:
        reqs["cpu"] = resources.requests_cpu
    if resources.requests_memory:
        reqs["memory"] = resources.requests_memory
    if reqs:
        block["requests"] = reqs
    lims: dict = {}
    if resources.limits_cpu:
        lims["cpu"] = resources.limits_cpu
    if resources.limits_memory:
        lims["memory"] = resources.limits_memory
    if lims:
        block["limits"] = lims
    return block if block else None


def _to_yaml(doc: dict) -> str:
    """Serialize manifest dict → YAML (no flow style, key order preserved)."""
    return yaml.dump(doc, default_flow_style=False, sort_keys=False)


def _gen_deployment(
    app_name: str,
    image: str,
    replicas: int,
    namespace: str,
    ports: list[PortConfig],
    env_vars: list[EnvVar],
    resources: Optional[ResourceRequirements],
    extra_labels: dict,
) -> str:
    labels = _base_labels(app_name, extra_labels or None)
    container: dict = {"name": app_name, "image": image}

    if ports:
        container["ports"] = [
            {"name": p.name, "containerPort": p.container_port, "protocol": p.protocol}
            for p in ports
        ]
    if env_vars:
        container["env"] = [{"name": e.name, "value": e.value} for e in env_vars]
    res = _resource_block(resources)
    if res:
        container["resources"] = res

    return _to_yaml(
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": app_name, "namespace": namespace, "labels": labels},
            "spec": {
                "replicas": replicas,
                "selector": {"matchLabels": {"app": app_name}},
                "template": {
                    "metadata": {"labels": labels},
                    "spec": {"containers": [container]},
                },
            },
        }
    )


def _gen_service(
    app_name: str, namespace: str, svc_type: str, ports: list[ServicePort]
) -> str:
    return _to_yaml(
        {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": f"{app_name}-svc",
                "namespace": namespace,
                "labels": _base_labels(app_name),
            },
            "spec": {
                "type": svc_type,
                "selector": {"app": app_name},
                "ports": [
                    {
                        "name": p.name,
                        "port": p.port,
                        "targetPort": p.target_port,
                        "protocol": p.protocol,
                    }
                    for p in ports
                ],
            },
        }
    )


def _gen_configmap(app_name: str, namespace: str, data: dict[str, str]) -> str:
    return _to_yaml(
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": f"{app_name}-config",
                "namespace": namespace,
                "labels": _base_labels(app_name),
            },
            "data": data,
        }
    )


# ---------------------------------------------------------------------------
# Structural validation logic
# ---------------------------------------------------------------------------


def _run_validation(yaml_str: str) -> dict:
    """Validate a manifest YAML structurally — no network calls."""
    errors: list[str] = []
    warnings: list[str] = []
    kind = "Unknown"
    name = ""

    try:
        doc = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        return {
            "valid": False,
            "kind": "Unknown",
            "name": "",
            "errors": [f"YAML parse error: {e}"],
            "warnings": [],
        }

    if not isinstance(doc, dict):
        return {
            "valid": False,
            "kind": "Unknown",
            "name": "",
            "errors": ["Manifest must be a YAML mapping"],
            "warnings": [],
        }

    for field in ("apiVersion", "kind", "metadata"):
        if field not in doc:
            errors.append(f"Missing required field: {field}")

    if "kind" in doc:
        kind = str(doc["kind"])
    if "metadata" in doc and isinstance(doc["metadata"], dict):
        name = doc["metadata"].get("name", "")
        if not name:
            errors.append("metadata.name is required and must be non-empty")

    if kind == "Deployment":
        _check_deployment(doc, errors, warnings)
    elif kind == "Service":
        _check_service(doc, errors, warnings)
    elif kind == "ConfigMap":
        _check_configmap(doc, errors, warnings)
    else:
        warnings.append(f"Unknown kind '{kind}' — kind-specific checks skipped")

    return {
        "valid": len(errors) == 0,
        "kind": kind,
        "name": name,
        "errors": errors,
        "warnings": warnings,
    }


def _check_deployment(doc: dict, errors: list[str], warnings: list[str]) -> None:
    if doc.get("apiVersion") != "apps/v1":
        errors.append(
            f"Deployment requires apiVersion 'apps/v1', got '{doc.get('apiVersion')}'"
        )
    spec = doc.get("spec", {})
    if not isinstance(spec, dict):
        errors.append("spec must be a mapping")
        return
    if "selector" not in spec:
        errors.append("spec.selector is required")
    if "template" not in spec:
        errors.append("spec.template is required")
    else:
        tmpl = spec["template"]
        containers = (tmpl.get("spec", {}) if isinstance(tmpl, dict) else {}).get(
            "containers", []
        )
        if not containers:
            errors.append(
                "spec.template.spec.containers must contain at least one container"
            )
        else:
            for i, c in enumerate(containers):
                if "name" not in c:
                    errors.append(f"containers[{i}].name is required")
                if "image" not in c:
                    errors.append(f"containers[{i}].image is required")
    replicas = spec.get("replicas", 1)
    if not isinstance(replicas, int) or replicas < 1:
        errors.append("spec.replicas must be a positive integer")
    # selector ⊆ template labels
    if "selector" in spec and "template" in spec:
        sel = spec.get("selector", {}).get("matchLabels", {})
        tmpl_labels = (
            spec.get("template", {}).get("metadata", {}).get("labels", {})
            if isinstance(spec.get("template"), dict)
            else {}
        )
        if sel and not all(tmpl_labels.get(k) == v for k, v in sel.items()):
            errors.append(
                "spec.selector.matchLabels must be a subset of spec.template.metadata.labels"
            )


def _check_service(doc: dict, errors: list[str], warnings: list[str]) -> None:
    if doc.get("apiVersion") != "v1":
        errors.append(
            f"Service requires apiVersion 'v1', got '{doc.get('apiVersion')}'"
        )
    spec = doc.get("spec", {})
    if not isinstance(spec, dict):
        errors.append("spec must be a mapping")
        return
    if "selector" not in spec:
        errors.append("spec.selector is required")
    if not spec.get("ports"):
        errors.append("spec.ports must contain at least one port")
    svc_type = spec.get("type", "ClusterIP")
    if svc_type not in {"ClusterIP", "NodePort", "LoadBalancer", "ExternalName"}:
        errors.append(f"Invalid Service type '{svc_type}'")


def _check_configmap(doc: dict, errors: list[str], warnings: list[str]) -> None:
    if doc.get("apiVersion") != "v1":
        errors.append(
            f"ConfigMap requires apiVersion 'v1', got '{doc.get('apiVersion')}'"
        )
    if "data" not in doc and "binaryData" not in doc:
        warnings.append("ConfigMap has no data or binaryData field")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def k8s_generate_deployment(
    app_name: str,
    image: str,
    replicas: int = 1,
    namespace: str = "default",
    ports: list[dict] | None = None,
    env_vars: list[dict] | None = None,
    resources: dict | None = None,
    labels: dict | None = None,
) -> str:
    """Generate a Kubernetes Deployment manifest (apps/v1).

    Returns JSON: {status, kind, name, namespace, manifest_yaml, notes}.
    Deterministic — identical input always produces identical YAML.
    All identifiers are DNS-1123 validated before generation.
    """
    parsed = DeploymentToolInput(
        app_name=app_name, image=image, replicas=replicas, namespace=namespace
    )
    parsed_ports = [PortConfig(**p) for p in (ports or [])]
    parsed_env = [EnvVar(**e) for e in (env_vars or [])]
    parsed_res = ResourceRequirements(**resources) if resources else None

    manifest_yaml = _gen_deployment(
        parsed.app_name,
        parsed.image,
        parsed.replicas,
        parsed.namespace,
        parsed_ports,
        parsed_env,
        parsed_res,
        labels or {},
    )

    return json.dumps(
        {
            "status": "success",
            "kind": "Deployment",
            "name": parsed.app_name,
            "namespace": parsed.namespace,
            "manifest_yaml": manifest_yaml,
            "notes": [
                "Deterministic: same input → same YAML",
                "Labels: app, app.kubernetes.io/name, app.kubernetes.io/managed-by applied",
                "Selector anchored on 'app' label",
            ],
        }
    )


@mcp.tool()
async def k8s_generate_service(
    app_name: str,
    ports: list[dict],
    namespace: str = "default",
    service_type: str = "ClusterIP",
) -> str:
    """Generate a Kubernetes Service manifest (v1).

    Returns JSON: {status, kind, name, namespace, manifest_yaml, notes}.
    Service name is auto-set to {app_name}-svc.
    Ports require: name, port, target_port. service_type: ClusterIP | NodePort | LoadBalancer.
    """
    if not ports:
        return json.dumps(
            {"status": "error", "error": "At least one port mapping is required"}
        )

    parsed = ServiceToolInput(
        app_name=app_name, namespace=namespace, service_type=service_type
    )
    parsed_ports = [ServicePort(**p) for p in ports]

    manifest_yaml = _gen_service(
        parsed.app_name, parsed.namespace, parsed.service_type, parsed_ports
    )

    return json.dumps(
        {
            "status": "success",
            "kind": "Service",
            "name": f"{parsed.app_name}-svc",
            "namespace": parsed.namespace,
            "manifest_yaml": manifest_yaml,
            "notes": [
                f"Selector targets Deployment with app={parsed.app_name}",
                f"Service type: {parsed.service_type}",
            ],
        }
    )


@mcp.tool()
async def k8s_generate_configmap(
    app_name: str,
    data: dict[str, str],
    namespace: str = "default",
) -> str:
    """Generate a Kubernetes ConfigMap manifest (v1).

    Returns JSON: {status, kind, name, namespace, manifest_yaml, notes}.
    ConfigMap name is auto-set to {app_name}-config.
    WARNING: Do NOT place secrets in data — use Kubernetes Secrets instead.
    """
    if not data:
        return json.dumps(
            {
                "status": "error",
                "error": "data must contain at least one key-value pair",
            }
        )

    parsed = ConfigMapToolInput(app_name=app_name, namespace=namespace)
    manifest_yaml = _gen_configmap(parsed.app_name, parsed.namespace, data)

    return json.dumps(
        {
            "status": "success",
            "kind": "ConfigMap",
            "name": f"{parsed.app_name}-config",
            "namespace": parsed.namespace,
            "manifest_yaml": manifest_yaml,
            "notes": ["Non-sensitive config only — never store secrets here"],
        }
    )


@mcp.tool()
async def k8s_generate_stack(
    app_name: str,
    image: str,
    replicas: int = 1,
    namespace: str = "default",
    ports: list[dict] | None = None,
    env_vars: list[dict] | None = None,
    resources: dict | None = None,
    labels: dict | None = None,
    service_type: str = "ClusterIP",
    configmap_data: dict[str, str] | None = None,
) -> str:
    """Generate a full deployment stack: Deployment + Service + ConfigMap.

    Auto-derivation rules:
    - Service: created from ports when ports are provided (defaults to ClusterIP).
    - ConfigMap: created from env_vars when provided; configmap_data overrides env_var-derived data.
    Returns JSON: {status, manifests: [{kind, name, manifest_yaml}], notes}.
    """
    parsed = DeploymentToolInput(
        app_name=app_name, image=image, replicas=replicas, namespace=namespace
    )
    if service_type not in VALID_SERVICE_TYPES:
        return json.dumps(
            {
                "status": "error",
                "error": f"service_type must be one of {VALID_SERVICE_TYPES}",
            }
        )

    parsed_ports = [PortConfig(**p) for p in (ports or [])]
    parsed_env = [EnvVar(**e) for e in (env_vars or [])]
    parsed_res = ResourceRequirements(**resources) if resources else None

    manifests: list[dict] = []

    # Deployment — always generated
    dep_yaml = _gen_deployment(
        parsed.app_name,
        parsed.image,
        parsed.replicas,
        parsed.namespace,
        parsed_ports,
        parsed_env,
        parsed_res,
        labels or {},
    )
    manifests.append(
        {"kind": "Deployment", "name": parsed.app_name, "manifest_yaml": dep_yaml}
    )

    # Service — auto-derived from ports
    if parsed_ports:
        svc_ports = [
            ServicePort(
                name=p.name,
                port=p.container_port,
                target_port=p.container_port,
                protocol=p.protocol,
            )
            for p in parsed_ports
        ]
        svc_yaml = _gen_service(
            parsed.app_name, parsed.namespace, service_type, svc_ports
        )
        manifests.append(
            {
                "kind": "Service",
                "name": f"{parsed.app_name}-svc",
                "manifest_yaml": svc_yaml,
            }
        )

    # ConfigMap — explicit data overrides env-derived
    cm_data = configmap_data
    if cm_data is None and parsed_env:
        cm_data = {e.name: e.value for e in parsed_env}
    if cm_data:
        cm_yaml = _gen_configmap(parsed.app_name, parsed.namespace, cm_data)
        manifests.append(
            {
                "kind": "ConfigMap",
                "name": f"{parsed.app_name}-config",
                "manifest_yaml": cm_yaml,
            }
        )

    return json.dumps(
        {
            "status": "success",
            "manifests": manifests,
            "notes": [
                f"Generated {len(manifests)} manifest(s): {', '.join(m['kind'] for m in manifests)}",
                (
                    "Service auto-derived from ports"
                    if parsed_ports
                    else "No Service — no ports provided"
                ),
                (
                    "ConfigMap from explicit configmap_data"
                    if configmap_data
                    else (
                        "ConfigMap auto-derived from env_vars"
                        if cm_data
                        else "No ConfigMap"
                    )
                ),
            ],
        }
    )


@mcp.tool()
async def k8s_validate_manifest(manifest_yaml: str) -> str:
    """Validate a Kubernetes manifest YAML structurally.

    Checks: YAML parsability, required top-level fields (apiVersion, kind, metadata.name),
    and kind-specific rules for Deployment (apps/v1), Service (v1), ConfigMap (v1).
    Returns JSON: {status, valid, kind, name, errors, warnings}.
    No network calls — purely structural validation.
    """
    result = _run_validation(manifest_yaml)
    return json.dumps({"status": "success", **result})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
