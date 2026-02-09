"""
Kubectl-AI MCP Server — generates kubectl-ai prompts, diagnostic workflows,
safety classifications, and Helm-aware resolution suggestions.

Tools:
    kubectl_generate_prompt         Generate kubectl-ai natural language prompt
    kubectl_diagnose_pod            Diagnostic workflow for pod issues
    kubectl_diagnose_service        Diagnostic workflow for service issues
    kubectl_diagnose_deployment     Diagnostic workflow for deployment issues
    kubectl_classify_safety         Classify safety level of a kubectl operation
    kubectl_suggest_workflow        Suggest diagnostic workflow for a symptom
    kubectl_check_helm_safety       Check Helm management and suggest safe changes
    kubectl_generate_triage         Generate emergency triage command sequence
    kubectl_list_prompt_patterns    List available prompt patterns by category
    kubectl_suggest_resolution      Suggest Helm-based resolution for common issues
"""

import json
from enum import Enum
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("kubectl_ai_mcp")

# ---------------------------------------------------------------------------
# Constants — Safety classifications
# ---------------------------------------------------------------------------


class SafetyLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


SAFE_OPERATIONS: dict[str, dict] = {
    "get": {
        "level": "green",
        "description": "List/get resources",
        "confirmation": False,
    },
    "describe": {
        "level": "green",
        "description": "Detailed resource info",
        "confirmation": False,
    },
    "logs": {
        "level": "green",
        "description": "View container logs",
        "confirmation": False,
    },
    "events": {
        "level": "green",
        "description": "View cluster events",
        "confirmation": False,
    },
    "top": {
        "level": "green",
        "description": "Resource usage metrics",
        "confirmation": False,
    },
    "explain": {
        "level": "green",
        "description": "API resource docs",
        "confirmation": False,
    },
}

CAUTION_OPERATIONS: dict[str, dict] = {
    "scale": {
        "level": "yellow",
        "description": "Change replica count",
        "confirmation": True,
    },
    "restart": {
        "level": "yellow",
        "description": "Rolling restart of pods",
        "confirmation": True,
    },
    "port-forward": {
        "level": "yellow",
        "description": "Network tunnel to pod",
        "confirmation": True,
    },
    "exec": {
        "level": "yellow",
        "description": "Shell access to container",
        "confirmation": True,
    },
    "cp": {
        "level": "yellow",
        "description": "Copy files to/from pod",
        "confirmation": True,
    },
    "cordon": {
        "level": "yellow",
        "description": "Mark node unschedulable",
        "confirmation": True,
    },
}

DANGEROUS_OPERATIONS: dict[str, dict] = {
    "delete": {
        "level": "red",
        "description": "Permanently remove resource",
        "confirmation": True,
    },
    "drain": {
        "level": "red",
        "description": "Evict all pods from node",
        "confirmation": True,
    },
    "patch": {
        "level": "red",
        "description": "Modify resource spec",
        "confirmation": True,
    },
    "edit": {
        "level": "red",
        "description": "Inline resource modification",
        "confirmation": True,
    },
    "replace": {
        "level": "red",
        "description": "Replace entire resource",
        "confirmation": True,
    },
    "taint": {
        "level": "red",
        "description": "Add/remove node taints",
        "confirmation": True,
    },
}

ALL_OPERATIONS = {**SAFE_OPERATIONS, **CAUTION_OPERATIONS, **DANGEROUS_OPERATIONS}

# ---------------------------------------------------------------------------
# Constants — Prompt pattern categories
# ---------------------------------------------------------------------------

PROMPT_CATEGORIES: dict[str, list[dict[str, str]]] = {
    "pods": [
        {
            "intent": "List pods",
            "prompt": 'kubectl ai "list all pods in {namespace} namespace"',
        },
        {
            "intent": "Pod details",
            "prompt": 'kubectl ai "describe pod {name} in {namespace}"',
        },
        {
            "intent": "Pod YAML",
            "prompt": 'kubectl ai "get pod {name} in {namespace} as yaml"',
        },
        {
            "intent": "Non-running pods",
            "prompt": 'kubectl ai "show pods in {namespace} that are not in Running state"',
        },
        {
            "intent": "Pods by restarts",
            "prompt": 'kubectl ai "list pods in {namespace} sorted by restart count descending"',
        },
        {
            "intent": "Pod labels",
            "prompt": 'kubectl ai "show pods with label app={component} in {namespace}"',
        },
    ],
    "deployments": [
        {
            "intent": "List deployments",
            "prompt": 'kubectl ai "list all deployments in {namespace} namespace"',
        },
        {
            "intent": "Rollout status",
            "prompt": 'kubectl ai "show rollout status for {name} deployment in {namespace}"',
        },
        {
            "intent": "Rollout history",
            "prompt": 'kubectl ai "show revision history for {name} deployment in {namespace}"',
        },
        {
            "intent": "Replica status",
            "prompt": 'kubectl ai "show desired vs ready replicas for deployments in {namespace}"',
        },
        {
            "intent": "Deployment conditions",
            "prompt": 'kubectl ai "show conditions for {name} deployment in {namespace}"',
        },
    ],
    "services": [
        {
            "intent": "List services",
            "prompt": 'kubectl ai "list all services in {namespace} namespace"',
        },
        {
            "intent": "Service endpoints",
            "prompt": 'kubectl ai "show endpoints for {name} service in {namespace}"',
        },
        {
            "intent": "Selector check",
            "prompt": 'kubectl ai "show selector for {name} and matching pods in {namespace}"',
        },
        {
            "intent": "External access",
            "prompt": 'kubectl ai "show services with NodePort or LoadBalancer in {namespace}"',
        },
    ],
    "logs": [
        {
            "intent": "Recent logs",
            "prompt": 'kubectl ai "show last 100 lines of logs from {name} pod in {namespace}"',
        },
        {
            "intent": "Follow logs",
            "prompt": 'kubectl ai "follow logs from {name} deployment in {namespace}"',
        },
        {
            "intent": "Timestamped logs",
            "prompt": 'kubectl ai "show logs with timestamps from {name} in {namespace}"',
        },
        {
            "intent": "Error logs",
            "prompt": 'kubectl ai "show logs containing ERROR from {name} in {namespace}"',
        },
        {
            "intent": "Previous container",
            "prompt": 'kubectl ai "show logs from previous container instance of {name} pod"',
        },
    ],
    "events": [
        {
            "intent": "Recent events",
            "prompt": 'kubectl ai "show events in {namespace} namespace sorted by time"',
        },
        {
            "intent": "Warning events",
            "prompt": 'kubectl ai "show warning events in {namespace} namespace"',
        },
        {
            "intent": "Resource events",
            "prompt": 'kubectl ai "show events related to {resource_type} {name} in {namespace}"',
        },
        {
            "intent": "Count by reason",
            "prompt": 'kubectl ai "count events by reason in {namespace} namespace"',
        },
    ],
    "metrics": [
        {
            "intent": "Pod metrics",
            "prompt": 'kubectl ai "show cpu and memory usage for pods in {namespace}"',
        },
        {
            "intent": "Top pods CPU",
            "prompt": 'kubectl ai "show top 10 pods by cpu usage in {namespace}"',
        },
        {
            "intent": "Top pods memory",
            "prompt": 'kubectl ai "show top 10 pods by memory usage in {namespace}"',
        },
        {
            "intent": "Usage vs limits",
            "prompt": 'kubectl ai "compare resource usage to limits for pods in {namespace}"',
        },
    ],
    "ingress": [
        {
            "intent": "List ingress",
            "prompt": 'kubectl ai "list all ingress in {namespace} namespace"',
        },
        {
            "intent": "Ingress rules",
            "prompt": 'kubectl ai "show routing rules for ingress in {namespace}"',
        },
        {
            "intent": "Ingress controller",
            "prompt": 'kubectl ai "show ingress controller pods and their status"',
        },
    ],
    "storage": [
        {
            "intent": "PVC status",
            "prompt": 'kubectl ai "list PVCs in {namespace} with status and storage class"',
        },
        {
            "intent": "PVC binding",
            "prompt": 'kubectl ai "show which PV is bound to pvc {name} in {namespace}"',
        },
        {
            "intent": "Storage capacity",
            "prompt": 'kubectl ai "show storage capacity for all PVCs in {namespace}"',
        },
    ],
    "helm": [
        {
            "intent": "Helm resources",
            "prompt": 'kubectl ai "list resources with label app.kubernetes.io/managed-by=Helm in {namespace}"',
        },
        {
            "intent": "Release info",
            "prompt": 'kubectl ai "show annotations with helm release info for {resource_type} {name}"',
        },
        {
            "intent": "Release resources",
            "prompt": 'kubectl ai "show all resources belonging to helm release {release}"',
        },
    ],
    "network": [
        {
            "intent": "Network policies",
            "prompt": 'kubectl ai "list network policies in {namespace} namespace"',
        },
        {
            "intent": "DNS check",
            "prompt": 'kubectl ai "show coredns pods and their status"',
        },
        {
            "intent": "Service discovery",
            "prompt": 'kubectl ai "show how to test dns resolution for {name}.{namespace}.svc.cluster.local"',
        },
    ],
}

# ---------------------------------------------------------------------------
# Constants — Diagnostic workflows
# ---------------------------------------------------------------------------

POD_ISSUES: dict[str, dict] = {
    "pending": {
        "title": "Pod Stuck in Pending",
        "symptoms": "Pod remains in Pending state, never schedules",
        "steps": [
            {
                "prompt": 'kubectl ai "describe pod {name} in {namespace} and show events"',
                "purpose": "Get pod events",
            },
            {
                "prompt": 'kubectl ai "show nodes with allocatable cpu and memory"',
                "purpose": "Check node resources",
            },
            {
                "prompt": 'kubectl ai "show PVC status for PVCs used by pod {name}"',
                "purpose": "Check PVC status",
            },
            {
                "prompt": 'kubectl ai "show nodeSelector and affinity for pod {name}"',
                "purpose": "Check scheduling constraints",
            },
            {
                "prompt": 'kubectl ai "show taints on all nodes and tolerations for pod {name}"',
                "purpose": "Check taints/tolerations",
            },
        ],
        "common_causes": [
            {
                "event": "Insufficient cpu",
                "cause": "Node lacks CPU",
                "resolution": "Reduce resource requests via Helm values or add nodes",
            },
            {
                "event": "Insufficient memory",
                "cause": "Node lacks memory",
                "resolution": "Reduce resource requests via Helm values or add nodes",
            },
            {
                "event": "no persistent volumes available",
                "cause": "PVC not bound",
                "resolution": "Check storage class, create PV",
            },
            {
                "event": "node(s) didn't match node selector",
                "cause": "Label mismatch",
                "resolution": "Fix nodeSelector in Helm values or label nodes",
            },
        ],
    },
    "crashloop": {
        "title": "Pod in CrashLoopBackOff",
        "symptoms": "Container repeatedly crashes and restarts",
        "steps": [
            {
                "prompt": 'kubectl ai "show pod {name} restart count and last restart time"',
                "purpose": "Check restart pattern",
            },
            {
                "prompt": 'kubectl ai "show logs from pod {name} in {namespace}"',
                "purpose": "Get current container logs",
            },
            {
                "prompt": 'kubectl ai "show logs from previous container in pod {name}"',
                "purpose": "Get previous container logs",
            },
            {
                "prompt": 'kubectl ai "show container exit codes for pod {name}"',
                "purpose": "Check exit codes",
            },
            {
                "prompt": 'kubectl ai "show resource limits vs usage for pod {name}"',
                "purpose": "Check resource constraints",
            },
            {
                "prompt": 'kubectl ai "show liveness probe configuration for pod {name}"',
                "purpose": "Check probe config",
            },
        ],
        "common_causes": [
            {
                "event": "Exit code 1",
                "cause": "Application error",
                "resolution": "Check application logs for stack trace",
            },
            {
                "event": "Exit code 137 (OOMKilled)",
                "cause": "Memory limit exceeded",
                "resolution": "Increase memory limit via Helm: --set backend.resources.limits.memory=1Gi",
            },
            {
                "event": "Exit code 127",
                "cause": "Command not found",
                "resolution": "Verify image has required binaries",
            },
            {
                "event": "Liveness probe failed",
                "cause": "Health check failing",
                "resolution": "Adjust probe timing or fix health endpoint",
            },
        ],
    },
    "oomkilled": {
        "title": "Pod OOMKilled",
        "symptoms": "Container killed due to memory limit",
        "steps": [
            {
                "prompt": 'kubectl ai "show events mentioning OOMKilled for pod {name}"',
                "purpose": "Confirm OOMKill",
            },
            {
                "prompt": 'kubectl ai "show memory limit for containers in pod {name}"',
                "purpose": "Check memory limit",
            },
            {
                "prompt": 'kubectl ai "show memory usage metrics for pod {name}"',
                "purpose": "Check memory usage",
            },
            {
                "prompt": 'kubectl ai "compare memory request vs limit for pod {name}"',
                "purpose": "Compare request vs limit",
            },
        ],
        "common_causes": [
            {
                "event": "OOMKilled",
                "cause": "Memory limit too low",
                "resolution": "Increase memory limit: helm upgrade myapp ./myapp --set backend.resources.limits.memory=1Gi",
            },
            {
                "event": "OOMKilled (repeated)",
                "cause": "Memory leak in application",
                "resolution": "Profile application memory usage, fix leak",
            },
        ],
    },
    "container_creating": {
        "title": "Pod Stuck in ContainerCreating",
        "symptoms": "Pod stays in ContainerCreating state",
        "steps": [
            {
                "prompt": 'kubectl ai "show events for pod {name} in {namespace}"',
                "purpose": "Check pod events",
            },
            {
                "prompt": 'kubectl ai "describe pod {name} showing image pull events"',
                "purpose": "Check image pull status",
            },
            {
                "prompt": 'kubectl ai "show volume mount status for pod {name}"',
                "purpose": "Check volume mounts",
            },
            {
                "prompt": 'kubectl ai "verify secrets and configmaps referenced by pod {name} exist"',
                "purpose": "Check referenced resources",
            },
        ],
        "common_causes": [
            {
                "event": "ErrImagePull",
                "cause": "Image doesn't exist",
                "resolution": "Verify image name and tag in Helm values",
            },
            {
                "event": "ImagePullBackOff",
                "cause": "Auth or rate limit",
                "resolution": "Check imagePullSecrets in Helm values",
            },
            {
                "event": "MountVolume.SetUp failed",
                "cause": "Volume issue",
                "resolution": "Check PVC binding, CSI driver",
            },
            {
                "event": "secret not found",
                "cause": "Missing secret",
                "resolution": "Create secret or fix reference in Helm values",
            },
        ],
    },
    "evicted": {
        "title": "Pod Evicted",
        "symptoms": "Pod terminated with Evicted status",
        "steps": [
            {
                "prompt": 'kubectl ai "describe evicted pods in {namespace} and show reason"',
                "purpose": "Check eviction reason",
            },
            {
                "prompt": 'kubectl ai "show node conditions for node that evicted pod"',
                "purpose": "Check node conditions",
            },
            {
                "prompt": 'kubectl ai "show disk usage and pressure on nodes"',
                "purpose": "Check disk pressure",
            },
            {
                "prompt": 'kubectl ai "show resource usage summary for all nodes"',
                "purpose": "Check cluster resources",
            },
        ],
        "common_causes": [
            {
                "event": "DiskPressure",
                "cause": "Node disk full",
                "resolution": "Clean up images, increase disk",
            },
            {
                "event": "MemoryPressure",
                "cause": "Node memory exhausted",
                "resolution": "Add memory, reduce workloads",
            },
        ],
    },
}

SERVICE_ISSUES: dict[str, dict] = {
    "no_endpoints": {
        "title": "Service Has No Endpoints",
        "symptoms": "Service exists but has no endpoints",
        "steps": [
            {
                "prompt": 'kubectl ai "show endpoints for service {name} in {namespace}"',
                "purpose": "Check endpoints",
            },
            {
                "prompt": 'kubectl ai "show selector for service {name} in {namespace}"',
                "purpose": "Get service selector",
            },
            {
                "prompt": 'kubectl ai "list pods matching selector of service {name} in {namespace}"',
                "purpose": "Find matching pods",
            },
            {
                "prompt": 'kubectl ai "show labels on pods in {namespace} that should match service"',
                "purpose": "Verify pod labels",
            },
            {
                "prompt": 'kubectl ai "show ready status for pods selected by service {name}"',
                "purpose": "Check pod readiness",
            },
        ],
        "common_causes": [
            {
                "cause": "Selector mismatch",
                "resolution": "Fix labels in Helm values to match service selector",
            },
            {
                "cause": "No ready pods",
                "resolution": "Fix readiness probe or application health",
            },
            {
                "cause": "No pods running",
                "resolution": "Scale up or check deployment via Helm",
            },
        ],
    },
    "not_accessible": {
        "title": "Service Not Accessible",
        "symptoms": "Cannot reach service from inside or outside cluster",
        "steps": [
            {
                "prompt": 'kubectl ai "describe service {name} in {namespace}"',
                "purpose": "Verify service exists",
            },
            {
                "prompt": 'kubectl ai "show type and ports for service {name}"',
                "purpose": "Check service type",
            },
            {
                "prompt": 'kubectl ai "show endpoints for service {name}"',
                "purpose": "Verify endpoints exist",
            },
            {
                "prompt": 'kubectl ai "list network policies affecting namespace {namespace}"',
                "purpose": "Check network policies",
            },
            {
                "prompt": 'kubectl ai "show how to create debug pod to test service connectivity"',
                "purpose": "Test from within cluster",
            },
            {
                "prompt": 'kubectl ai "describe ingress routing to service {name}"',
                "purpose": "Check ingress (if external)",
            },
        ],
        "common_causes": [
            {
                "cause": "No endpoints",
                "resolution": "Check pod readiness and label matching",
            },
            {
                "cause": "Network policy blocking",
                "resolution": "Update network policy via Helm values",
            },
            {
                "cause": "Ingress misconfigured",
                "resolution": "Fix ingress paths/host in Helm values",
            },
        ],
    },
}

DEPLOYMENT_ISSUES: dict[str, dict] = {
    "rollout_stuck": {
        "title": "Rollout Stuck",
        "symptoms": "Deployment rollout doesn't complete",
        "steps": [
            {
                "prompt": 'kubectl ai "show rollout status for deployment {name} in {namespace}"',
                "purpose": "Check rollout status",
            },
            {
                "prompt": 'kubectl ai "show replica sets for deployment {name} with ready count"',
                "purpose": "Check replica sets",
            },
            {
                "prompt": 'kubectl ai "show pods from new replica set for deployment {name}"',
                "purpose": "Check new pods",
            },
            {
                "prompt": 'kubectl ai "show events for pods in new replica set of {name}"',
                "purpose": "Check pod events",
            },
            {
                "prompt": 'kubectl ai "show pod disruption budgets affecting deployment {name}"',
                "purpose": "Check PDB",
            },
            {
                "prompt": 'kubectl ai "show resource quota usage in {namespace}"',
                "purpose": "Check resource quotas",
            },
        ],
        "common_causes": [
            {
                "cause": "New pods failing",
                "resolution": "Check pod diagnostics for the failing pods",
            },
            {
                "cause": "PDB blocking",
                "resolution": "Adjust PDB minAvailable in Helm values",
            },
            {
                "cause": "Resource quota exhausted",
                "resolution": "Increase quota or reduce requests",
            },
        ],
    },
    "not_scaling": {
        "title": "ReplicaSet Not Scaling",
        "symptoms": "Deployment shows desired replicas but not available",
        "steps": [
            {
                "prompt": 'kubectl ai "show replicas status for deployment {name}"',
                "purpose": "Check deployment status",
            },
            {
                "prompt": 'kubectl ai "describe newest replica set for deployment {name}"',
                "purpose": "Check ReplicaSet status",
            },
            {
                "prompt": 'kubectl ai "show pods being created by replica set"',
                "purpose": "Check pod creation",
            },
            {
                "prompt": 'kubectl ai "show available resources on nodes vs pod requests"',
                "purpose": "Check node capacity",
            },
            {
                "prompt": 'kubectl ai "show scheduling events for deployment {name} pods"',
                "purpose": "Check scheduler events",
            },
        ],
        "common_causes": [
            {
                "cause": "Insufficient node resources",
                "resolution": "Reduce resource requests in Helm values or add nodes",
            },
            {
                "cause": "Image pull errors",
                "resolution": "Check image repository and credentials in Helm values",
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# Constants — Common resolutions via Helm
# ---------------------------------------------------------------------------

HELM_RESOLUTIONS: dict[str, dict] = {
    "increase_memory": {
        "issue": "OOMKilled / memory pressure",
        "helm_command": "helm upgrade {release} ./{chart} --set {component}.resources.limits.memory={value}",
        "default_value": "1Gi",
        "values_path": "{component}.resources.limits.memory",
    },
    "increase_cpu": {
        "issue": "CPU throttling / slow response",
        "helm_command": "helm upgrade {release} ./{chart} --set {component}.resources.limits.cpu={value}",
        "default_value": "1000m",
        "values_path": "{component}.resources.limits.cpu",
    },
    "scale_replicas": {
        "issue": "High load / availability",
        "helm_command": "helm upgrade {release} ./{chart} --set {component}.replicaCount={value}",
        "default_value": "3",
        "values_path": "{component}.replicaCount",
    },
    "update_image": {
        "issue": "Deploy new version",
        "helm_command": "helm upgrade {release} ./{chart} --set {component}.image.tag={value}",
        "default_value": "latest",
        "values_path": "{component}.image.tag",
    },
    "enable_autoscaling": {
        "issue": "Variable load",
        "helm_command": "helm upgrade {release} ./{chart} --set autoscaling.enabled=true --set autoscaling.minReplicas=2 --set autoscaling.maxReplicas=10",
        "default_value": "true",
        "values_path": "autoscaling.enabled",
    },
    "fix_health_probe": {
        "issue": "Liveness/readiness probe failing",
        "helm_command": "helm upgrade {release} ./{chart} --set {component}.livenessProbe.initialDelaySeconds={value}",
        "default_value": "60",
        "values_path": "{component}.livenessProbe.initialDelaySeconds",
    },
    "enable_persistence": {
        "issue": "Data loss on restart",
        "helm_command": "helm upgrade {release} ./{chart} --set persistence.enabled=true --set persistence.size={value}",
        "default_value": "10Gi",
        "values_path": "persistence.enabled",
    },
    "fix_ingress": {
        "issue": "External access not working",
        "helm_command": "helm upgrade {release} ./{chart} --set ingress.enabled=true --set ingress.hosts[0].host={value}",
        "default_value": "myapp.local",
        "values_path": "ingress.enabled",
    },
}

# ---------------------------------------------------------------------------
# Pydantic Input Models
# ---------------------------------------------------------------------------


class PromptGenerateInput(BaseModel):
    """Input for kubectl_generate_prompt."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    intent: str = Field(
        ..., min_length=1, description="What you want to accomplish (natural language)"
    )
    resource_type: str = Field(
        "pod", description="Resource type: pod, deployment, service, ingress, etc."
    )
    name: Optional[str] = Field(None, description="Resource name")
    namespace: str = Field("default", min_length=1, description="Target namespace")
    output_format: Optional[str] = Field(
        None, description="Output format: yaml, json, wide, custom"
    )


class PodDiagnoseInput(BaseModel):
    """Input for kubectl_diagnose_pod."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    issue_type: str = Field(
        ...,
        description="Issue type: pending, crashloop, oomkilled, container_creating, evicted",
    )
    pod_name: Optional[str] = Field(
        None, description="Pod name (or use {name} placeholder)"
    )
    namespace: str = Field("default", description="Target namespace")
    helm_release: Optional[str] = Field(
        None, description="Associated Helm release name"
    )

    @field_validator("issue_type")
    @classmethod
    def validate_issue(cls, v: str) -> str:
        valid = tuple(POD_ISSUES.keys())
        if v not in valid:
            raise ValueError(f"issue_type must be one of {valid}")
        return v


class ServiceDiagnoseInput(BaseModel):
    """Input for kubectl_diagnose_service."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    issue_type: str = Field(..., description="Issue type: no_endpoints, not_accessible")
    service_name: Optional[str] = Field(None, description="Service name")
    namespace: str = Field("default", description="Target namespace")

    @field_validator("issue_type")
    @classmethod
    def validate_issue(cls, v: str) -> str:
        valid = tuple(SERVICE_ISSUES.keys())
        if v not in valid:
            raise ValueError(f"issue_type must be one of {valid}")
        return v


class DeploymentDiagnoseInput(BaseModel):
    """Input for kubectl_diagnose_deployment."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    issue_type: str = Field(..., description="Issue type: rollout_stuck, not_scaling")
    deployment_name: Optional[str] = Field(None, description="Deployment name")
    namespace: str = Field("default", description="Target namespace")

    @field_validator("issue_type")
    @classmethod
    def validate_issue(cls, v: str) -> str:
        valid = tuple(DEPLOYMENT_ISSUES.keys())
        if v not in valid:
            raise ValueError(f"issue_type must be one of {valid}")
        return v


class SafetyClassifyInput(BaseModel):
    """Input for kubectl_classify_safety."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    operation: str = Field(
        ...,
        min_length=1,
        description="kubectl operation verb (get, delete, scale, etc.)",
    )
    resource_type: Optional[str] = Field(
        None, description="Resource type being operated on"
    )
    is_helm_managed: bool = Field(
        False, description="Whether the target resource is Helm-managed"
    )


class WorkflowSuggestInput(BaseModel):
    """Input for kubectl_suggest_workflow."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    symptom: str = Field(
        ..., min_length=1, description="Observed symptom or error message"
    )
    namespace: str = Field("default", description="Target namespace")
    resource_name: Optional[str] = Field(None, description="Affected resource name")


class HelmSafetyInput(BaseModel):
    """Input for kubectl_check_helm_safety."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    resource_type: str = Field(
        ..., min_length=1, description="Resource type (deployment, service, etc.)"
    )
    resource_name: str = Field(..., min_length=1, description="Resource name")
    namespace: str = Field("default", description="Target namespace")
    intended_operation: str = Field(
        ..., description="What you want to change (scale, update image, etc.)"
    )
    helm_release: Optional[str] = Field(None, description="Helm release name")
    chart_path: str = Field(".", description="Path to Helm chart")


class TriageInput(BaseModel):
    """Input for kubectl_generate_triage."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    namespace: Optional[str] = Field(
        None, description="Target namespace (None for cluster-wide)"
    )
    scope: str = Field("namespace", description="Triage scope: namespace, cluster")

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        if v not in ("namespace", "cluster"):
            raise ValueError("scope must be 'namespace' or 'cluster'")
        return v


class ResolutionInput(BaseModel):
    """Input for kubectl_suggest_resolution."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    issue: str = Field(
        ...,
        min_length=1,
        description="Issue type (increase_memory, scale_replicas, update_image, etc.)",
    )
    release_name: str = Field(..., min_length=1, description="Helm release name")
    chart_name: str = Field(..., min_length=1, description="Chart name")
    component: str = Field("backend", description="Component name")
    value: Optional[str] = Field(None, description="Override value")

    @field_validator("issue")
    @classmethod
    def validate_issue(cls, v: str) -> str:
        valid = tuple(HELM_RESOLUTIONS.keys())
        if v not in valid:
            raise ValueError(f"issue must be one of {valid}")
        return v


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _fill_placeholders(text: str, **kwargs: str) -> str:
    """Replace {placeholders} in prompt text."""
    for key, val in kwargs.items():
        text = text.replace(f"{{{key}}}", val)
    return text


def _classify_operation(operation: str) -> dict:
    """Classify a kubectl operation by safety level."""
    op = operation.lower().strip()
    if op in SAFE_OPERATIONS:
        return {**SAFE_OPERATIONS[op], "operation": op}
    if op in CAUTION_OPERATIONS:
        return {**CAUTION_OPERATIONS[op], "operation": op}
    if op in DANGEROUS_OPERATIONS:
        return {**DANGEROUS_OPERATIONS[op], "operation": op}
    return {
        "level": "yellow",
        "description": "Unknown operation — treat with caution",
        "confirmation": True,
        "operation": op,
    }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def kubectl_generate_prompt(
    intent: str,
    resource_type: str = "pod",
    name: str | None = None,
    namespace: str = "default",
    output_format: str | None = None,
) -> str:
    """Generate a kubectl-ai natural language prompt from an intent description.

    Returns JSON: {status, prompt, safety_level, notes}
    Builds well-structured kubectl-ai prompts with namespace and format context.
    """
    parsed = PromptGenerateInput(
        intent=intent,
        resource_type=resource_type,
        name=name,
        namespace=namespace,
        output_format=output_format,
    )

    # Build the prompt
    parts = [parsed.intent]

    # Add resource context if not already in intent
    if parsed.name and parsed.name not in parsed.intent:
        parts.append(f"for {parsed.resource_type} {parsed.name}")

    if parsed.namespace not in parsed.intent:
        parts.append(f"in {parsed.namespace} namespace")

    if parsed.output_format and parsed.output_format not in parsed.intent:
        parts.append(f"as {parsed.output_format}")

    prompt_text = " ".join(parts)
    full_prompt = f'kubectl ai "{prompt_text}"'

    # Infer safety from intent keywords
    safety = "green"
    for keyword in ("delete", "drain", "patch", "edit", "replace"):
        if keyword in parsed.intent.lower():
            safety = "red"
            break
    if safety == "green":
        for keyword in ("scale", "restart", "exec", "forward"):
            if keyword in parsed.intent.lower():
                safety = "yellow"
                break

    notes = ["kubectl-ai translates natural language to kubectl commands"]
    if safety == "yellow":
        notes.append(
            "CAUTION: This intent may modify cluster state — confirm before executing"
        )
    elif safety == "red":
        notes.append(
            "DANGER: This intent involves a destructive operation — MANDATORY confirmation required"
        )

    return json.dumps(
        {
            "status": "success",
            "prompt": full_prompt,
            "safety_level": safety,
            "notes": notes,
        }
    )


@mcp.tool()
async def kubectl_diagnose_pod(
    issue_type: str,
    pod_name: str | None = None,
    namespace: str = "default",
    helm_release: str | None = None,
) -> str:
    """Generate a diagnostic workflow for pod issues.

    Returns JSON: {title, symptoms, diagnostic_steps, common_causes, helm_resolution}
    Issue types: pending, crashloop, oomkilled, container_creating, evicted
    """
    parsed = PodDiagnoseInput(
        issue_type=issue_type,
        pod_name=pod_name,
        namespace=namespace,
        helm_release=helm_release,
    )

    issue = POD_ISSUES[parsed.issue_type]
    name = parsed.pod_name or "{pod-name}"

    steps = []
    for step in issue["steps"]:
        prompt = _fill_placeholders(
            step["prompt"], name=name, namespace=parsed.namespace
        )
        steps.append({"prompt": prompt, "purpose": step["purpose"], "safety": "green"})

    result: dict = {
        "status": "success",
        "title": issue["title"],
        "symptoms": issue["symptoms"],
        "diagnostic_steps": steps,
        "common_causes": issue["common_causes"],
    }

    if parsed.helm_release:
        result["helm_note"] = (
            f"Resource is part of Helm release '{parsed.helm_release}'. "
            "All changes should go through: helm upgrade"
        )

    return json.dumps(result, indent=2)


@mcp.tool()
async def kubectl_diagnose_service(
    issue_type: str,
    service_name: str | None = None,
    namespace: str = "default",
) -> str:
    """Generate a diagnostic workflow for service issues.

    Returns JSON: {title, symptoms, diagnostic_steps, common_causes}
    Issue types: no_endpoints, not_accessible
    """
    parsed = ServiceDiagnoseInput(
        issue_type=issue_type,
        service_name=service_name,
        namespace=namespace,
    )

    issue = SERVICE_ISSUES[parsed.issue_type]
    name = parsed.service_name or "{service-name}"

    steps = []
    for step in issue["steps"]:
        prompt = _fill_placeholders(
            step["prompt"], name=name, namespace=parsed.namespace
        )
        steps.append({"prompt": prompt, "purpose": step["purpose"], "safety": "green"})

    return json.dumps(
        {
            "status": "success",
            "title": issue["title"],
            "symptoms": issue["symptoms"],
            "diagnostic_steps": steps,
            "common_causes": issue["common_causes"],
        },
        indent=2,
    )


@mcp.tool()
async def kubectl_diagnose_deployment(
    issue_type: str,
    deployment_name: str | None = None,
    namespace: str = "default",
) -> str:
    """Generate a diagnostic workflow for deployment issues.

    Returns JSON: {title, symptoms, diagnostic_steps, common_causes}
    Issue types: rollout_stuck, not_scaling
    """
    parsed = DeploymentDiagnoseInput(
        issue_type=issue_type,
        deployment_name=deployment_name,
        namespace=namespace,
    )

    issue = DEPLOYMENT_ISSUES[parsed.issue_type]
    name = parsed.deployment_name or "{deployment-name}"

    steps = []
    for step in issue["steps"]:
        prompt = _fill_placeholders(
            step["prompt"], name=name, namespace=parsed.namespace
        )
        steps.append({"prompt": prompt, "purpose": step["purpose"], "safety": "green"})

    return json.dumps(
        {
            "status": "success",
            "title": issue["title"],
            "symptoms": issue["symptoms"],
            "diagnostic_steps": steps,
            "common_causes": issue["common_causes"],
        },
        indent=2,
    )


@mcp.tool()
async def kubectl_classify_safety(
    operation: str,
    resource_type: str | None = None,
    is_helm_managed: bool = False,
) -> str:
    """Classify the safety level of a kubectl operation.

    Returns JSON: {level, description, confirmation_required, warning}
    Levels: green (safe), yellow (caution), red (dangerous)
    """
    parsed = SafetyClassifyInput(
        operation=operation,
        resource_type=resource_type,
        is_helm_managed=is_helm_managed,
    )

    classification = _classify_operation(parsed.operation)

    warning = None
    if classification["level"] == "red":
        warning = (
            f"DANGER: '{parsed.operation}' is a destructive operation. "
            f"{'Target resource is Helm-managed — use helm upgrade instead. ' if parsed.is_helm_managed else ''}"
            "MANDATORY confirmation required before execution."
        )
    elif classification["level"] == "yellow":
        warning = (
            f"CAUTION: '{parsed.operation}' modifies cluster state. "
            f"{'Target resource is Helm-managed — prefer helm upgrade. ' if parsed.is_helm_managed else ''}"
            "Confirm before executing."
        )
    elif parsed.is_helm_managed:
        warning = (
            "Note: Target resource is Helm-managed. "
            "Read operations are safe, but any changes should go through Helm."
        )

    return json.dumps(
        {
            "operation": parsed.operation,
            "level": classification["level"],
            "description": classification["description"],
            "confirmation_required": classification.get("confirmation", False),
            "is_helm_managed": parsed.is_helm_managed,
            "warning": warning,
        }
    )


@mcp.tool()
async def kubectl_suggest_workflow(
    symptom: str,
    namespace: str = "default",
    resource_name: str | None = None,
) -> str:
    """Suggest a complete diagnostic workflow based on observed symptoms.

    Returns JSON: {matched_issue, workflow_steps, notes}
    Matches symptoms to known issue patterns and provides step-by-step prompts.
    """
    parsed = WorkflowSuggestInput(
        symptom=symptom,
        namespace=namespace,
        resource_name=resource_name,
    )

    symptom_lower = parsed.symptom.lower()
    name = parsed.resource_name or "{resource-name}"

    # Match symptom to known issues
    matched = None
    source = None

    symptom_map = [
        (["pending", "stuck pending", "not scheduling"], "pending", POD_ISSUES),
        (
            ["crashloop", "crash loop", "crashloopbackoff", "keeps restarting"],
            "crashloop",
            POD_ISSUES,
        ),
        (["oomkill", "oom", "out of memory", "memory limit"], "oomkilled", POD_ISSUES),
        (
            ["containercreating", "container creating", "image pull"],
            "container_creating",
            POD_ISSUES,
        ),
        (["evicted", "eviction"], "evicted", POD_ISSUES),
        (
            ["no endpoint", "no endpoints", "empty endpoints"],
            "no_endpoints",
            SERVICE_ISSUES,
        ),
        (
            ["not accessible", "cannot reach", "connection refused", "timeout"],
            "not_accessible",
            SERVICE_ISSUES,
        ),
        (
            ["rollout stuck", "rollout not completing", "deployment stuck"],
            "rollout_stuck",
            DEPLOYMENT_ISSUES,
        ),
        (
            ["not scaling", "replicas not ready", "unavailable replicas"],
            "not_scaling",
            DEPLOYMENT_ISSUES,
        ),
    ]

    for keywords, issue_key, issue_source in symptom_map:
        if any(kw in symptom_lower for kw in keywords):
            matched = issue_source[issue_key]
            source = issue_key
            break

    if matched:
        steps = []
        for step in matched["steps"]:
            prompt = _fill_placeholders(
                step["prompt"], name=name, namespace=parsed.namespace
            )
            steps.append(
                {"prompt": prompt, "purpose": step["purpose"], "safety": "green"}
            )

        return json.dumps(
            {
                "status": "success",
                "matched_issue": matched["title"],
                "issue_key": source,
                "symptoms": matched["symptoms"],
                "workflow_steps": steps,
                "common_causes": matched.get("common_causes", []),
                "notes": [
                    "All diagnostic steps are read-only (green safety level)",
                    "Changes should be made via Helm upgrade, not kubectl",
                ],
            },
            indent=2,
        )

    # No match — provide generic health check workflow
    generic_steps = [
        {
            "prompt": f'kubectl ai "summarize resource health in {parsed.namespace}"',
            "purpose": "Namespace overview",
            "safety": "green",
        },
        {
            "prompt": f'kubectl ai "show pods not in Running/Completed state in {parsed.namespace}"',
            "purpose": "Find failing pods",
            "safety": "green",
        },
        {
            "prompt": f'kubectl ai "show warning events in last 30 minutes in {parsed.namespace}"',
            "purpose": "Recent warnings",
            "safety": "green",
        },
        {
            "prompt": f'kubectl ai "show pods near resource limits in {parsed.namespace}"',
            "purpose": "Resource pressure",
            "safety": "green",
        },
        {
            "prompt": f'kubectl ai "show pending pods and PVCs in {parsed.namespace}"',
            "purpose": "Pending resources",
            "safety": "green",
        },
    ]

    return json.dumps(
        {
            "status": "success",
            "matched_issue": "General Health Check",
            "issue_key": "general",
            "symptoms": parsed.symptom,
            "workflow_steps": generic_steps,
            "notes": [
                "No specific issue pattern matched — running general health check",
                "Refine the symptom description for more targeted diagnostics",
            ],
        },
        indent=2,
    )


@mcp.tool()
async def kubectl_check_helm_safety(
    resource_type: str,
    resource_name: str,
    namespace: str = "default",
    intended_operation: str = "scale",
    helm_release: str | None = None,
    chart_path: str = ".",
) -> str:
    """Check if a resource is Helm-managed and suggest safe change paths.

    Returns JSON: {check_prompts, helm_alternative, warning}
    Always recommends Helm upgrade over imperative kubectl for managed resources.
    """
    parsed = HelmSafetyInput(
        resource_type=resource_type,
        resource_name=resource_name,
        namespace=namespace,
        intended_operation=intended_operation,
        helm_release=helm_release,
        chart_path=chart_path,
    )

    release = parsed.helm_release or parsed.resource_name

    check_prompts = [
        {
            "prompt": f'kubectl ai "check if {parsed.resource_type} {parsed.resource_name} has helm managed-by label in {parsed.namespace}"',
            "purpose": "Verify Helm management",
        },
        {
            "prompt": f'kubectl ai "show annotations with helm release info for {parsed.resource_type} {parsed.resource_name}"',
            "purpose": "Get Helm release details",
        },
    ]

    # Build Helm alternative based on operation
    helm_alternatives: dict[str, str] = {
        "scale": f"helm upgrade {release} {parsed.chart_path} --set backend.replicaCount=3",
        "update_image": f"helm upgrade {release} {parsed.chart_path} --set backend.image.tag=v2",
        "update_env": f"helm upgrade {release} {parsed.chart_path} --set backend.env[0].name=KEY --set backend.env[0].value=val",
        "increase_memory": f"helm upgrade {release} {parsed.chart_path} --set backend.resources.limits.memory=1Gi",
        "increase_cpu": f"helm upgrade {release} {parsed.chart_path} --set backend.resources.limits.cpu=1000m",
        "enable_ingress": f"helm upgrade {release} {parsed.chart_path} --set ingress.enabled=true",
        "restart": f"helm upgrade {release} {parsed.chart_path} --set backend.podAnnotations.restartedAt=$(date +%s)",
    }

    alt = helm_alternatives.get(
        parsed.intended_operation,
        f"helm upgrade {release} {parsed.chart_path} --set <key>=<value>",
    )

    return json.dumps(
        {
            "status": "success",
            "check_prompts": check_prompts,
            "intended_operation": parsed.intended_operation,
            "helm_alternative": {
                "command": alt,
                "note": "RECOMMENDED: Use Helm to maintain state consistency",
            },
            "imperative_warning": (
                f"WARNING: Directly running 'kubectl {parsed.intended_operation}' on Helm-managed "
                f"resource '{parsed.resource_name}' will cause drift from Helm state. "
                "The next 'helm upgrade' will revert your changes."
            ),
        },
        indent=2,
    )


@mcp.tool()
async def kubectl_generate_triage(
    namespace: str | None = None,
    scope: str = "namespace",
) -> str:
    """Generate emergency triage command sequence for quick cluster assessment.

    Returns JSON: {scope, triage_steps}
    Provides ordered diagnostic prompts for rapid issue identification.
    """
    parsed = TriageInput(namespace=namespace, scope=scope)

    if parsed.scope == "cluster":
        steps = [
            {
                "prompt": 'kubectl ai "show any nodes with issues"',
                "purpose": "Node health",
                "priority": 1,
            },
            {
                "prompt": 'kubectl ai "show control plane component status"',
                "purpose": "Control plane health",
                "priority": 1,
            },
            {
                "prompt": 'kubectl ai "show warning events cluster-wide in last 10 minutes"',
                "purpose": "Recent cluster warnings",
                "priority": 2,
            },
            {
                "prompt": 'kubectl ai "show namespaces with failing pods"',
                "purpose": "Affected namespaces",
                "priority": 2,
            },
            {
                "prompt": 'kubectl ai "show nodes with resource pressure conditions"',
                "purpose": "Resource pressure",
                "priority": 3,
            },
            {
                "prompt": 'kubectl ai "show pods in kube-system that are not Running"',
                "purpose": "System pod health",
                "priority": 3,
            },
        ]
    else:
        ns = parsed.namespace or "default"
        steps = [
            {
                "prompt": f'kubectl ai "count pods by status in {ns}"',
                "purpose": "Pod status overview",
                "priority": 1,
            },
            {
                "prompt": f'kubectl ai "show pods not in Running/Completed state in {ns}"',
                "purpose": "Failing pods",
                "priority": 1,
            },
            {
                "prompt": f'kubectl ai "show warning events in last 30 minutes in {ns}"',
                "purpose": "Recent warnings",
                "priority": 2,
            },
            {
                "prompt": f'kubectl ai "show deployments with unavailable replicas in {ns}"',
                "purpose": "Deployment health",
                "priority": 2,
            },
            {
                "prompt": f'kubectl ai "show pods near resource limits in {ns}"',
                "purpose": "Resource pressure",
                "priority": 3,
            },
            {
                "prompt": f'kubectl ai "show pending pods and PVCs in {ns}"',
                "purpose": "Pending resources",
                "priority": 3,
            },
            {
                "prompt": f'kubectl ai "show services with no endpoints in {ns}"',
                "purpose": "Service health",
                "priority": 3,
            },
        ]

    return json.dumps(
        {
            "status": "success",
            "scope": parsed.scope,
            "namespace": parsed.namespace,
            "triage_steps": steps,
            "notes": [
                "All triage steps are read-only (green safety level)",
                "Execute in priority order: 1 (critical) -> 2 (important) -> 3 (supplementary)",
                "Follow up with specific diagnostic tools for identified issues",
            ],
        },
        indent=2,
    )


@mcp.tool()
async def kubectl_list_prompt_patterns(
    category: str | None = None,
) -> str:
    """List available kubectl-ai prompt patterns by category.

    Returns JSON: {categories, patterns}
    Categories: pods, deployments, services, logs, events, metrics, ingress, storage, helm, network
    """
    if category:
        cat = category.lower()
        if cat not in PROMPT_CATEGORIES:
            valid = list(PROMPT_CATEGORIES.keys())
            return json.dumps(
                {"status": "error", "error": f"category must be one of {valid}"}
            )
        return json.dumps(
            {
                "status": "success",
                "category": cat,
                "patterns": PROMPT_CATEGORIES[cat],
                "note": "Replace {namespace}, {name}, {component}, etc. with actual values",
            }
        )

    # Return all categories with counts
    summary = {cat: len(patterns) for cat, patterns in PROMPT_CATEGORIES.items()}
    return json.dumps(
        {
            "status": "success",
            "categories": summary,
            "total_patterns": sum(summary.values()),
            "note": "Pass a category name to get the full prompt list",
        }
    )


@mcp.tool()
async def kubectl_suggest_resolution(
    issue: str,
    release_name: str,
    chart_name: str,
    component: str = "backend",
    value: str | None = None,
) -> str:
    """Suggest Helm-based resolution for common Kubernetes issues.

    Returns JSON: {issue_description, helm_command, values_path, notes}
    Always resolves via Helm upgrade to maintain state consistency.
    """
    parsed = ResolutionInput(
        issue=issue,
        release_name=release_name,
        chart_name=chart_name,
        component=component,
        value=value,
    )

    resolution = HELM_RESOLUTIONS[parsed.issue]
    use_value = parsed.value or resolution["default_value"]

    command = _fill_placeholders(
        resolution["helm_command"],
        release=parsed.release_name,
        chart=parsed.chart_name,
        component=parsed.component,
        value=use_value,
    )

    values_path = _fill_placeholders(
        resolution["values_path"],
        component=parsed.component,
    )

    return json.dumps(
        {
            "status": "success",
            "issue_description": resolution["issue"],
            "helm_command": command,
            "values_path": values_path,
            "value": use_value,
            "notes": [
                "SUGGESTION ONLY — not executed",
                "Always use Helm upgrade instead of imperative kubectl commands",
                "Add --dry-run --debug to preview changes before applying",
                f"Alternatively, edit values.yaml at path: {values_path}",
            ],
        }
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
