"""
Kagent Analysis MCP Server — generates analysis prompts, assesses cluster health,
recommends resource optimizations, and provides educational Kubernetes insights.

Tools:
    kagent_generate_prompt           Generate kagent/k8sgpt analysis prompts
    kagent_assess_health             Assess cluster/namespace health status
    kagent_analyze_resources         Analyze resource utilization efficiency
    kagent_recommend_sizing          Generate right-sizing recommendations
    kagent_detect_antipatterns       Detect common resource anti-patterns
    kagent_generate_workflow         Generate complete analysis workflow
    kagent_validate_predeployment    Pre-deployment validation checklist
    kagent_analyze_performance       Analyze performance indicators
    kagent_audit_security            Generate security audit checklist
    kagent_explain_concept           Explain Kubernetes optimization concepts
"""

import json
import math
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("kagent_analysis_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_SCOPES = ("cluster", "namespace", "workload")
VALID_ANALYSIS_TYPES = (
    "health",
    "performance",
    "resources",
    "security",
    "cost",
    "best-practices",
    "scaling",
    "network",
    "storage",
)
VALID_OPTIMIZATION_LEVELS = ("conservative", "moderate", "aggressive")
VALID_TIME_RANGES = ("1h", "6h", "24h", "7d", "30d")
VALID_RESOURCE_TYPES = ("cpu", "memory", "storage")
VALID_WORKFLOW_TYPES = (
    "cluster-assessment",
    "namespace-health",
    "pre-deployment",
    "performance-investigation",
    "right-sizing",
    "security-audit",
    "cost-analysis",
    "anomaly-investigation",
)
VALID_CONCEPTS = (
    "requests-vs-limits",
    "hpa-vs-vpa",
    "qos-classes",
    "resource-quotas",
    "pod-disruption-budgets",
    "priority-classes",
    "cpu-throttling",
    "oom-killed",
    "probe-types",
    "image-optimization",
)

# ---------------------------------------------------------------------------
# Health thresholds
# ---------------------------------------------------------------------------

HEALTH_THRESHOLDS: dict[str, dict] = {
    "api_server_latency_ms": {"healthy": 100, "warning": 500},
    "cpu_utilization_pct": {"low": 20, "healthy_max": 70, "attention": 85},
    "memory_utilization_pct": {"low": 30, "healthy_max": 75, "attention": 90},
    "pod_restart_24h": {"healthy": 0, "warning": 3},
    "pod_startup_seconds": {"good": 30, "slow": 60},
    "image_pull_seconds": {"good": 30, "slow": 60},
    "dns_resolution_ms": {"good": 5, "slow": 50},
    "service_latency_p95_ms": {"good": 100, "slow": 500},
}

# ---------------------------------------------------------------------------
# Optimization level configs
# ---------------------------------------------------------------------------

OPTIMIZATION_CONFIGS: dict[str, dict] = {
    "conservative": {
        "percentile": "p95",
        "buffer_pct": 30,
        "limit_multiplier": 2.0,
        "change_increment_pct": "10-20",
        "hpa_threshold": 80,
        "description": "Minimize risk, generous buffers. Recommended for learning.",
    },
    "moderate": {
        "percentile": "p90",
        "buffer_pct": 20,
        "limit_multiplier": 1.5,
        "change_increment_pct": "20-30",
        "hpa_threshold": 70,
        "description": "Balance efficiency and stability.",
    },
    "aggressive": {
        "percentile": "p75",
        "buffer_pct": 10,
        "limit_multiplier": 1.2,
        "change_increment_pct": "30-50",
        "hpa_threshold": 60,
        "description": "Maximum efficiency. High risk of instability.",
    },
}

# ---------------------------------------------------------------------------
# Anti-pattern definitions
# ---------------------------------------------------------------------------

ANTIPATTERNS: dict[str, dict] = {
    "over-provisioning": {
        "description": "Resources set far above actual usage",
        "detection": "CPU or memory requests > 3x observed p95 usage",
        "impact": "Wastes cluster capacity, fewer pods schedulable, higher cloud cost",
        "fix": "Right-size based on actual usage with appropriate buffer",
    },
    "request-equals-limit": {
        "description": "CPU/memory request set equal to limit",
        "detection": "requests.cpu == limits.cpu or requests.memory == limits.memory",
        "impact": "No burst capacity; any spike causes throttling",
        "fix": "Set limits to 1.5-2x requests for burst headroom",
    },
    "no-limits": {
        "description": "Resource limits not set",
        "detection": "Missing limits.cpu or limits.memory",
        "impact": "Pod can consume unlimited resources, starving neighbors",
        "fix": "Always set limits; use 2x requests as starting point",
    },
    "latest-tag": {
        "description": "Using :latest image tag",
        "detection": "image.tag == 'latest' or no tag specified",
        "impact": "Non-deterministic deployments, difficult rollback, cache issues",
        "fix": "Use specific semver tags (e.g., 1.2.3)",
    },
    "no-probes": {
        "description": "Missing liveness or readiness probes",
        "detection": "No livenessProbe or readinessProbe configured",
        "impact": "K8s cannot detect unhealthy pods or readiness state",
        "fix": "Add HTTP/TCP probes with appropriate thresholds",
    },
    "no-security-context": {
        "description": "Missing pod/container security context",
        "detection": "No securityContext defined",
        "impact": "Containers may run as root with full capabilities",
        "fix": "Add runAsNonRoot, drop capabilities, readOnlyRootFilesystem",
    },
    "no-resource-requests": {
        "description": "Missing resource requests",
        "detection": "No requests.cpu or requests.memory",
        "impact": "Scheduler cannot properly place pods; BestEffort QoS",
        "fix": "Set requests based on observed p90-p95 usage",
    },
}

# ---------------------------------------------------------------------------
# Analysis prompt categories
# ---------------------------------------------------------------------------

PROMPT_CATEGORIES: dict[str, list[str]] = {
    "cluster-health": [
        "kagent analyze cluster --health",
        "kagent analyze cluster --summary",
        "kagent analyze cluster --components --detailed",
        "kagent analyze nodes --all",
        "kagent analyze nodes --pressure",
    ],
    "resource-utilization": [
        "kagent analyze utilization --namespace {namespace}",
        "kagent analyze waste --namespace {namespace} --threshold {threshold}",
        "kagent analyze efficiency --below 30",
        "kagent analyze sizing-candidates --namespace {namespace}",
    ],
    "performance": [
        "kagent analyze performance --namespace {namespace}",
        "kagent analyze bottlenecks --namespace {namespace} --top 5",
        "kagent analyze latency --service {workload} --namespace {namespace}",
        "kagent analyze throughput --service {workload}",
    ],
    "security": [
        "kagent analyze security --namespace {namespace}",
        "kagent analyze rbac --namespace {namespace}",
        "kagent analyze pod-security --namespace {namespace}",
        "kagent analyze network-security --namespace {namespace}",
        "kagent analyze secrets --namespace {namespace} --hygiene",
    ],
    "best-practices": [
        "kagent analyze best-practices --namespace {namespace}",
        "kagent analyze best-practices --category security",
        "kagent analyze best-practices --category reliability",
        "kagent analyze best-practices --category efficiency",
    ],
    "scaling": [
        "kagent analyze hpa --namespace {namespace}",
        "kagent analyze scaling-events --namespace {namespace} --period {time_range}",
        "kagent recommend scaling --deployment {workload}",
        "kagent analyze vpa-candidates --namespace {namespace}",
    ],
    "network": [
        "kagent analyze services --namespace {namespace} --connectivity",
        "kagent analyze dns --namespace {namespace}",
        "kagent analyze network-policies --namespace {namespace}",
        "kagent analyze traffic-flows --namespace {namespace}",
    ],
    "storage": [
        "kagent analyze pvc --namespace {namespace} --utilization",
        "kagent analyze pvc --growth --period 30d",
        "kagent analyze pvc --unused --namespace {namespace}",
        "kagent analyze storage-provisioner",
    ],
    "cost": [
        "kagent analyze cost --namespace {namespace} --educational",
        "kagent analyze cost-optimization --namespace {namespace}",
        "kagent analyze efficiency-score --namespace {namespace}",
    ],
}

# ---------------------------------------------------------------------------
# Workflow definitions
# ---------------------------------------------------------------------------

WORKFLOW_DEFINITIONS: dict[str, dict] = {
    "cluster-assessment": {
        "title": "Comprehensive Cluster Assessment",
        "purpose": "Full cluster health and efficiency review",
        "steps": [
            {
                "step": 1,
                "name": "Cluster Overview",
                "cmd": "kagent analyze cluster --summary",
            },
            {
                "step": 2,
                "name": "Component Health",
                "cmd": "kagent analyze components --all",
            },
            {
                "step": 3,
                "name": "Resource Utilization",
                "cmd": "kagent analyze resources --cluster-wide",
            },
            {
                "step": 4,
                "name": "Best Practices",
                "cmd": "kagent analyze best-practices --all-namespaces",
            },
            {
                "step": 5,
                "name": "Optimization Opportunities",
                "cmd": "kagent recommend --type all --conservative",
            },
        ],
    },
    "namespace-health": {
        "title": "Namespace Health Check",
        "purpose": "Focused analysis of specific namespace",
        "steps": [
            {
                "step": 1,
                "name": "Workload Status",
                "cmd": "kagent analyze workloads --namespace {namespace}",
            },
            {
                "step": 2,
                "name": "Resource Efficiency",
                "cmd": "kagent analyze resources --namespace {namespace} --detailed",
            },
            {
                "step": 3,
                "name": "Configuration Audit",
                "cmd": "kagent analyze config --namespace {namespace}",
            },
            {
                "step": 4,
                "name": "Network Analysis",
                "cmd": "kagent analyze network --namespace {namespace}",
            },
            {
                "step": 5,
                "name": "Recommendations",
                "cmd": "kagent recommend --namespace {namespace}",
            },
        ],
    },
    "pre-deployment": {
        "title": "Pre-Deployment Validation",
        "purpose": "Validate configuration before deployment",
        "steps": [
            {
                "step": 1,
                "name": "Resource Availability",
                "cmd": "kagent analyze capacity --for-deployment ./values.yaml",
            },
            {
                "step": 2,
                "name": "Configuration Check",
                "cmd": "kagent validate chart ./{chart} --values values.yaml",
            },
            {
                "step": 3,
                "name": "Best Practices",
                "cmd": "kagent lint deployment --strict",
            },
            {
                "step": 4,
                "name": "Risk Assessment",
                "cmd": "kagent assess risk --deployment {chart}",
            },
        ],
    },
    "performance-investigation": {
        "title": "Performance Investigation",
        "purpose": "Diagnose performance issues",
        "steps": [
            {
                "step": 1,
                "name": "Current Metrics",
                "cmd": "kagent analyze performance --namespace {namespace}",
            },
            {
                "step": 2,
                "name": "Bottleneck Detection",
                "cmd": "kagent analyze bottlenecks --namespace {namespace} --top 5",
            },
            {
                "step": 3,
                "name": "Resource Pressure",
                "cmd": "kagent analyze pressure --namespace {namespace}",
            },
            {
                "step": 4,
                "name": "Historical Comparison",
                "cmd": "kagent analyze trends --namespace {namespace} --period {time_range}",
            },
        ],
    },
    "right-sizing": {
        "title": "Resource Right-Sizing",
        "purpose": "Optimize resource allocation",
        "steps": [
            {
                "step": 1,
                "name": "Current Usage Analysis",
                "cmd": "kagent analyze sizing --namespace {namespace} --period 7d",
            },
            {
                "step": 2,
                "name": "Identify Over-Provisioned",
                "cmd": "kagent analyze waste --namespace {namespace} --threshold 40",
            },
            {
                "step": 3,
                "name": "Generate Recommendations",
                "cmd": "kagent recommend sizing --namespace {namespace} --{optimization_level}",
            },
            {
                "step": 4,
                "name": "Implementation Plan",
                "cmd": "# Review Helm upgrade commands from recommendations",
            },
        ],
    },
    "security-audit": {
        "title": "Security Audit",
        "purpose": "Review security configuration",
        "steps": [
            {
                "step": 1,
                "name": "Security Posture",
                "cmd": "kagent analyze security --namespace {namespace}",
            },
            {
                "step": 2,
                "name": "RBAC Analysis",
                "cmd": "kagent analyze rbac --namespace {namespace}",
            },
            {
                "step": 3,
                "name": "Pod Security Standards",
                "cmd": "kagent analyze pod-security --namespace {namespace}",
            },
            {
                "step": 4,
                "name": "Network Policy Coverage",
                "cmd": "kagent analyze network-security --namespace {namespace}",
            },
        ],
    },
    "cost-analysis": {
        "title": "Cost Analysis (Educational)",
        "purpose": "Understand resource costs for learning",
        "steps": [
            {
                "step": 1,
                "name": "Resource Cost Estimation",
                "cmd": "kagent analyze cost --namespace {namespace} --educational",
            },
            {
                "step": 2,
                "name": "Cost Optimization",
                "cmd": "kagent analyze cost-optimization --namespace {namespace}",
            },
            {
                "step": 3,
                "name": "Efficiency Score",
                "cmd": "kagent analyze efficiency-score --namespace {namespace}",
            },
        ],
    },
    "anomaly-investigation": {
        "title": "Anomaly Investigation",
        "purpose": "Investigate detected anomalies",
        "steps": [
            {
                "step": 1,
                "name": "Identify Anomalies",
                "cmd": "kagent analyze anomalies --namespace {namespace}",
            },
            {
                "step": 2,
                "name": "Gather Details",
                "cmd": "kagent analyze anomaly --id <anomaly-id> --detailed",
            },
            {
                "step": 3,
                "name": "Root Cause Analysis",
                "cmd": "kagent explain anomaly --id <anomaly-id>",
            },
            {
                "step": 4,
                "name": "Remediation Options",
                "cmd": "kagent recommend --for-anomaly <anomaly-id>",
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# Performance indicators
# ---------------------------------------------------------------------------

PERFORMANCE_INDICATORS: dict[str, dict] = {
    "pod_startup": {
        "metric": "Pod Startup Time",
        "good": "< 30s",
        "needs_attention": "> 60s",
        "prompts": [
            "kagent analyze pods --lifecycle --namespace {namespace}",
            "kagent analyze images --namespace {namespace} --size",
        ],
    },
    "container_restarts": {
        "metric": "Container Restart Count",
        "good": "0 in 24h",
        "needs_attention": "> 3 in 24h",
        "prompts": [
            "kagent analyze pods --restarts --namespace {namespace}",
            "kagent analyze pods --age --older-than 7d",
        ],
    },
    "image_pull": {
        "metric": "Image Pull Time",
        "good": "< 30s",
        "needs_attention": "> 60s",
        "prompts": [
            "kagent analyze images --namespace {namespace} --size",
        ],
    },
    "service_latency": {
        "metric": "Service Latency (p95)",
        "good": "< 100ms",
        "needs_attention": "> 500ms",
        "prompts": [
            "kagent analyze latency --percentiles --service {workload}",
            "kagent analyze latency --trend --period {time_range}",
        ],
    },
    "dns_resolution": {
        "metric": "DNS Resolution Time",
        "good": "< 5ms",
        "needs_attention": "> 50ms",
        "prompts": [
            "kagent analyze dns --namespace {namespace}",
            "kagent analyze dns --errors --period 1h",
        ],
    },
}

# ---------------------------------------------------------------------------
# Anomaly types
# ---------------------------------------------------------------------------

ANOMALY_TYPES: dict[str, dict] = {
    "high-restarts": {
        "detection": "> 3 restarts/hour",
        "potential_causes": [
            "OOMKilled",
            "Application crash",
            "Liveness probe failure",
        ],
        "investigation_prompts": [
            "kagent analyze pods --restarts --namespace {namespace}",
            "kagent explain anomaly --type restarts",
        ],
    },
    "pending-pods": {
        "detection": "Pod pending > 5min",
        "potential_causes": [
            "Insufficient resources",
            "Scheduling constraints",
            "PVC pending",
        ],
        "investigation_prompts": [
            "kagent analyze pods --pending --namespace {namespace}",
            "kagent analyze capacity --namespace {namespace}",
        ],
    },
    "evictions": {
        "detection": "Any pod eviction",
        "potential_causes": ["Node memory pressure", "Disk pressure", "PID pressure"],
        "investigation_prompts": [
            "kagent analyze nodes --pressure",
            "kagent analyze evictions --namespace {namespace}",
        ],
    },
    "failed-probes": {
        "detection": "Continuous probe failures",
        "potential_causes": [
            "Application issue",
            "Misconfigured probe",
            "Resource starvation",
        ],
        "investigation_prompts": [
            "kagent analyze probes --namespace {namespace}",
            "kagent analyze performance --namespace {namespace}",
        ],
    },
    "image-pull-failures": {
        "detection": "ImagePullBackOff",
        "potential_causes": [
            "Registry unreachable",
            "Wrong image name/tag",
            "Auth failure",
        ],
        "investigation_prompts": [
            "kagent analyze images --namespace {namespace} --errors",
        ],
    },
    "pvc-pending": {
        "detection": "PVC pending > 1min",
        "potential_causes": [
            "Storage class unavailable",
            "Quota exceeded",
            "Provisioner issue",
        ],
        "investigation_prompts": [
            "kagent analyze pvc --namespace {namespace} --status",
            "kagent analyze storage-provisioner",
        ],
    },
}

# ---------------------------------------------------------------------------
# Concept explanations
# ---------------------------------------------------------------------------

CONCEPT_EXPLANATIONS: dict[str, dict] = {
    "requests-vs-limits": {
        "title": "Resource Requests vs Limits",
        "summary": "Requests guarantee resources for scheduling; Limits cap maximum usage.",
        "details": (
            "REQUESTS: Guaranteed minimum resources. The scheduler uses requests to place pods on nodes.\n"
            "LIMITS: Maximum allowed resources. Exceeding CPU limits causes throttling; exceeding memory limits causes OOMKill.\n\n"
            "Best Practices:\n"
            "- Set requests based on typical usage (p90-p95)\n"
            "- Set limits 1.5-2x requests for burst capacity\n"
            "- Never set limits = requests (no burst room)\n"
            "- Never omit limits (unbounded consumption)"
        ),
        "related_prompts": [
            "kagent explain resources --concept requests-vs-limits",
            "kagent analyze sizing --namespace {namespace}",
        ],
    },
    "hpa-vs-vpa": {
        "title": "Horizontal vs Vertical Pod Autoscaler",
        "summary": "HPA adds/removes pod replicas; VPA adjusts per-pod resource requests/limits.",
        "details": (
            "HPA (Horizontal): Scales the number of pod replicas based on CPU/memory/custom metrics.\n"
            "VPA (Vertical): Adjusts resource requests and limits per pod based on observed usage.\n\n"
            "When to use:\n"
            "- HPA: Stateless services that handle concurrent load\n"
            "- VPA: Stateful workloads or when replica count should stay fixed\n"
            "- Both: Not recommended together for the same metric"
        ),
        "related_prompts": [
            "kagent explain scaling --concept hpa-vs-vpa",
            "kagent analyze hpa --namespace {namespace}",
            "kagent analyze vpa-candidates --namespace {namespace}",
        ],
    },
    "qos-classes": {
        "title": "Quality of Service (QoS) Classes",
        "summary": "K8s assigns QoS classes based on resource configuration to determine eviction priority.",
        "details": (
            "Guaranteed: requests == limits for all containers. Last to be evicted.\n"
            "Burstable: requests < limits for at least one container. Medium priority.\n"
            "BestEffort: No requests or limits set. First to be evicted.\n\n"
            "Recommendation: Use Burstable (requests < limits) for most workloads."
        ),
        "related_prompts": [
            "kagent explain resources --concept qos-classes",
            "kagent analyze pods --qos --namespace {namespace}",
        ],
    },
    "resource-quotas": {
        "title": "Resource Quotas",
        "summary": "Namespace-level caps on aggregate resource consumption.",
        "details": (
            "Resource quotas limit total CPU, memory, pod count, and other resources per namespace.\n"
            "Useful for multi-tenant clusters to prevent one team from consuming all resources.\n\n"
            "Common quotas: requests.cpu, requests.memory, limits.cpu, limits.memory, pods, services"
        ),
        "related_prompts": [
            "kagent analyze quotas --namespace {namespace}",
            "kagent analyze quota-usage --namespace {namespace} --warn-threshold 80",
        ],
    },
    "pod-disruption-budgets": {
        "title": "Pod Disruption Budgets (PDB)",
        "summary": "Limits how many pods can be voluntarily disrupted at once.",
        "details": (
            "PDBs protect availability during voluntary disruptions (node drain, upgrades).\n"
            "Configure with minAvailable or maxUnavailable.\n\n"
            "Development: Usually not needed (single replica).\n"
            "Production: Set minAvailable to ensure quorum."
        ),
        "related_prompts": [
            "kagent explain reliability --concept pdb",
        ],
    },
    "priority-classes": {
        "title": "Pod Priority and Preemption",
        "summary": "Assigns scheduling priority; higher-priority pods can preempt lower ones.",
        "details": (
            "Priority classes assign integer priorities to pods.\n"
            "When resources are scarce, the scheduler can evict low-priority pods to schedule high-priority ones.\n\n"
            "Use cases: Critical system pods > application pods > batch jobs"
        ),
        "related_prompts": [
            "kagent explain scheduling --concept priority-classes",
        ],
    },
    "cpu-throttling": {
        "title": "CPU Throttling",
        "summary": "CPU throttling occurs when a container hits its CPU limit.",
        "details": (
            "Signs: High container_cpu_cfs_throttled_periods_total, latency spikes under load.\n\n"
            "Solutions:\n"
            "1. Increase CPU limits (allow burst)\n"
            "2. Increase CPU requests (guarantee more)\n"
            "3. Optimize application code\n"
            "4. Scale horizontally (more replicas)"
        ),
        "related_prompts": [
            "kagent analyze bottlenecks --type cpu",
            "kagent analyze performance --deployment {workload}",
        ],
    },
    "oom-killed": {
        "title": "OOMKilled (Out of Memory)",
        "summary": "Container killed because it exceeded its memory limit.",
        "details": (
            "Signs: OOMKilled in pod events, container_memory_working_set_bytes near limit.\n\n"
            "Solutions:\n"
            "1. Increase memory limits\n"
            "2. Investigate memory leaks\n"
            "3. Tune GC settings (Java heap, Go GC%)\n"
            "4. Add memory-based HPA"
        ),
        "related_prompts": [
            "kagent analyze pods --restarts --namespace {namespace}",
            "kagent analyze bottlenecks --type memory",
        ],
    },
    "probe-types": {
        "title": "Kubernetes Probe Types",
        "summary": "Startup, liveness, and readiness probes manage pod lifecycle.",
        "details": (
            "Startup Probe: Delays liveness/readiness until app starts. Use for slow-starting apps.\n"
            "Liveness Probe: Detects deadlocked/hung containers. Failure triggers restart.\n"
            "Readiness Probe: Determines if pod can receive traffic. Failure removes from service.\n\n"
            "Order: startup → liveness + readiness (concurrent)"
        ),
        "related_prompts": [
            "kagent analyze probes --namespace {namespace}",
            "kagent explain reliability --concept probes",
        ],
    },
    "image-optimization": {
        "title": "Container Image Optimization",
        "summary": "Smaller images = faster pulls, less storage, smaller attack surface.",
        "details": (
            "Size hierarchy (smallest to largest):\n"
            "1. Distroless (~5-20MB) — most secure, no shell\n"
            "2. Alpine (~50MB) — small, shell available\n"
            "3. Slim variants (~150MB) — debian-slim, etc.\n"
            "4. Full images (~1GB) — largest, most compatible\n\n"
            "Best practices: Use multi-stage builds, specific tags, minimal base images."
        ),
        "related_prompts": [
            "kagent analyze images --namespace {namespace} --size",
            "kagent analyze containers --security --namespace {namespace}",
        ],
    },
}

# ---------------------------------------------------------------------------
# Security checklist items
# ---------------------------------------------------------------------------

SECURITY_CHECKLIST: list[dict] = [
    {
        "category": "Container Security",
        "item": "Non-root containers",
        "cmd": "kagent analyze containers --security --namespace {namespace}",
    },
    {
        "category": "Container Security",
        "item": "Read-only root filesystem",
        "cmd": "kagent analyze containers --filesystem --namespace {namespace}",
    },
    {
        "category": "Container Security",
        "item": "Capabilities dropped",
        "cmd": "kagent analyze containers --capabilities --namespace {namespace}",
    },
    {
        "category": "Resources",
        "item": "Resource limits set for all containers",
        "cmd": "kagent analyze config --validate-limits --namespace {namespace}",
    },
    {
        "category": "Resources",
        "item": "Resource requests set for all containers",
        "cmd": "kagent analyze config --validate-requests --namespace {namespace}",
    },
    {
        "category": "Network",
        "item": "Network policies defined",
        "cmd": "kagent analyze network-policies --namespace {namespace}",
    },
    {
        "category": "RBAC",
        "item": "Service accounts restricted",
        "cmd": "kagent analyze rbac --namespace {namespace}",
    },
    {
        "category": "Secrets",
        "item": "Secrets properly managed",
        "cmd": "kagent analyze secrets --namespace {namespace} --hygiene",
    },
    {
        "category": "Images",
        "item": "Specific image tags (not :latest)",
        "cmd": "kagent analyze images --namespace {namespace} --tags",
    },
    {
        "category": "Images",
        "item": "Trusted image registries",
        "cmd": "kagent analyze images --namespace {namespace} --registries",
    },
]

# ---------------------------------------------------------------------------
# Pydantic input models
# ---------------------------------------------------------------------------

_CFG = ConfigDict(str_strip_whitespace=True, extra="forbid")


class KagentGeneratePromptInput(BaseModel):
    model_config = _CFG
    analysis_type: str = Field(
        ...,
        description="Type of analysis: health, performance, resources, security, cost, best-practices, scaling, network, storage",
    )
    scope: str = Field(
        default="namespace", description="Scope: cluster, namespace, or workload"
    )
    namespace: str = Field(default="default", description="Target namespace")
    workload: Optional[str] = Field(
        default=None, description="Specific workload name (deployment, service, etc.)"
    )
    time_range: str = Field(
        default="24h", description="Time range: 1h, 6h, 24h, 7d, 30d"
    )

    @field_validator("analysis_type")
    @classmethod
    def _check_analysis_type(cls, v: str) -> str:
        if v not in VALID_ANALYSIS_TYPES:
            raise ValueError(f"analysis_type must be one of {VALID_ANALYSIS_TYPES}")
        return v

    @field_validator("scope")
    @classmethod
    def _check_scope(cls, v: str) -> str:
        if v not in VALID_SCOPES:
            raise ValueError(f"scope must be one of {VALID_SCOPES}")
        return v

    @field_validator("time_range")
    @classmethod
    def _check_time_range(cls, v: str) -> str:
        if v not in VALID_TIME_RANGES:
            raise ValueError(f"time_range must be one of {VALID_TIME_RANGES}")
        return v

    @field_validator("namespace")
    @classmethod
    def _check_namespace(cls, v: str) -> str:
        if ".." in v or "/" in v:
            raise ValueError("namespace must not contain path traversal characters")
        return v


class KagentAssessHealthInput(BaseModel):
    model_config = _CFG
    scope: str = Field(
        default="cluster", description="Scope: cluster, namespace, or workload"
    )
    namespace: str = Field(default="default", description="Target namespace")
    workload: Optional[str] = Field(default=None, description="Specific workload")
    include_thresholds: bool = Field(
        default=True, description="Include health threshold reference"
    )

    @field_validator("scope")
    @classmethod
    def _check_scope(cls, v: str) -> str:
        if v not in VALID_SCOPES:
            raise ValueError(f"scope must be one of {VALID_SCOPES}")
        return v

    @field_validator("namespace")
    @classmethod
    def _check_namespace(cls, v: str) -> str:
        if ".." in v or "/" in v:
            raise ValueError("namespace must not contain path traversal characters")
        return v


class KagentAnalyzeResourcesInput(BaseModel):
    model_config = _CFG
    namespace: str = Field(default="default", description="Target namespace")
    resource_type: Optional[str] = Field(
        default=None, description="Specific resource type: cpu, memory, storage"
    )
    waste_threshold_pct: int = Field(
        default=50, ge=10, le=90, description="Waste detection threshold percentage"
    )

    @field_validator("resource_type")
    @classmethod
    def _check_resource_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_RESOURCE_TYPES:
            raise ValueError(f"resource_type must be one of {VALID_RESOURCE_TYPES}")
        return v

    @field_validator("namespace")
    @classmethod
    def _check_namespace(cls, v: str) -> str:
        if ".." in v or "/" in v:
            raise ValueError("namespace must not contain path traversal characters")
        return v


class KagentRecommendSizingInput(BaseModel):
    model_config = _CFG
    namespace: str = Field(default="default", description="Target namespace")
    workload: Optional[str] = Field(
        default=None, description="Specific workload (deployment name)"
    )
    optimization_level: str = Field(
        default="conservative", description="Level: conservative, moderate, aggressive"
    )
    current_cpu_request: Optional[str] = Field(
        default=None, description="Current CPU request (e.g., '500m')"
    )
    current_memory_request: Optional[str] = Field(
        default=None, description="Current memory request (e.g., '512Mi')"
    )
    observed_cpu_p95: Optional[str] = Field(
        default=None, description="Observed p95 CPU usage (e.g., '150m')"
    )
    observed_memory_p95: Optional[str] = Field(
        default=None, description="Observed p95 memory usage (e.g., '280Mi')"
    )

    @field_validator("optimization_level")
    @classmethod
    def _check_level(cls, v: str) -> str:
        if v not in VALID_OPTIMIZATION_LEVELS:
            raise ValueError(
                f"optimization_level must be one of {VALID_OPTIMIZATION_LEVELS}"
            )
        return v

    @field_validator("namespace")
    @classmethod
    def _check_namespace(cls, v: str) -> str:
        if ".." in v or "/" in v:
            raise ValueError("namespace must not contain path traversal characters")
        return v


class KagentDetectAntipatternsInput(BaseModel):
    model_config = _CFG
    namespace: str = Field(default="default", description="Target namespace")
    include_fixes: bool = Field(default=True, description="Include fix recommendations")

    @field_validator("namespace")
    @classmethod
    def _check_namespace(cls, v: str) -> str:
        if ".." in v or "/" in v:
            raise ValueError("namespace must not contain path traversal characters")
        return v


class KagentGenerateWorkflowInput(BaseModel):
    model_config = _CFG
    workflow_type: str = Field(
        ...,
        description="Workflow type: cluster-assessment, namespace-health, pre-deployment, performance-investigation, right-sizing, security-audit, cost-analysis, anomaly-investigation",
    )
    namespace: str = Field(default="default", description="Target namespace")
    optimization_level: str = Field(
        default="conservative", description="Level: conservative, moderate, aggressive"
    )
    chart_name: Optional[str] = Field(
        default=None, description="Helm chart name (for pre-deployment)"
    )
    time_range: str = Field(
        default="24h", description="Time range for historical analysis"
    )

    @field_validator("workflow_type")
    @classmethod
    def _check_workflow(cls, v: str) -> str:
        if v not in VALID_WORKFLOW_TYPES:
            raise ValueError(f"workflow_type must be one of {VALID_WORKFLOW_TYPES}")
        return v

    @field_validator("optimization_level")
    @classmethod
    def _check_level(cls, v: str) -> str:
        if v not in VALID_OPTIMIZATION_LEVELS:
            raise ValueError(
                f"optimization_level must be one of {VALID_OPTIMIZATION_LEVELS}"
            )
        return v

    @field_validator("namespace")
    @classmethod
    def _check_namespace(cls, v: str) -> str:
        if ".." in v or "/" in v:
            raise ValueError("namespace must not contain path traversal characters")
        return v


class KagentValidatePredeploymentInput(BaseModel):
    model_config = _CFG
    namespace: str = Field(default="default", description="Target namespace")
    chart_name: Optional[str] = Field(default=None, description="Helm chart name")
    values_file: str = Field(
        default="values.yaml", description="Values file to validate"
    )

    @field_validator("namespace")
    @classmethod
    def _check_namespace(cls, v: str) -> str:
        if ".." in v or "/" in v:
            raise ValueError("namespace must not contain path traversal characters")
        return v


class KagentAnalyzePerformanceInput(BaseModel):
    model_config = _CFG
    namespace: str = Field(default="default", description="Target namespace")
    workload: Optional[str] = Field(default=None, description="Specific workload name")
    time_range: str = Field(
        default="24h", description="Time range: 1h, 6h, 24h, 7d, 30d"
    )
    observed_anomalies: Optional[list[str]] = Field(
        default=None, description="Observed issues (e.g., ['High latency', 'Timeouts'])"
    )

    @field_validator("time_range")
    @classmethod
    def _check_time_range(cls, v: str) -> str:
        if v not in VALID_TIME_RANGES:
            raise ValueError(f"time_range must be one of {VALID_TIME_RANGES}")
        return v

    @field_validator("namespace")
    @classmethod
    def _check_namespace(cls, v: str) -> str:
        if ".." in v or "/" in v:
            raise ValueError("namespace must not contain path traversal characters")
        return v


class KagentAuditSecurityInput(BaseModel):
    model_config = _CFG
    namespace: str = Field(default="default", description="Target namespace")
    include_prompts: bool = Field(
        default=True, description="Include kagent prompts for each check"
    )

    @field_validator("namespace")
    @classmethod
    def _check_namespace(cls, v: str) -> str:
        if ".." in v or "/" in v:
            raise ValueError("namespace must not contain path traversal characters")
        return v


class KagentExplainConceptInput(BaseModel):
    model_config = _CFG
    concept: str = Field(
        ...,
        description="Concept to explain: requests-vs-limits, hpa-vs-vpa, qos-classes, resource-quotas, pod-disruption-budgets, priority-classes, cpu-throttling, oom-killed, probe-types, image-optimization",
    )
    namespace: Optional[str] = Field(
        default="default", description="Namespace for contextualized prompts"
    )

    @field_validator("concept")
    @classmethod
    def _check_concept(cls, v: str) -> str:
        if v not in VALID_CONCEPTS:
            raise ValueError(f"concept must be one of {VALID_CONCEPTS}")
        return v


# ---------------------------------------------------------------------------
# Pure generator / helper functions
# ---------------------------------------------------------------------------


def _format_prompts(
    prompts: list[str],
    namespace: str,
    workload: Optional[str] = None,
    time_range: str = "24h",
    threshold: int = 50,
) -> list[str]:
    """Interpolate namespace/workload/time_range into prompt templates."""
    result = []
    for p in prompts:
        formatted = p.format(
            namespace=namespace,
            workload=workload or "<workload>",
            time_range=time_range,
            threshold=threshold,
        )
        result.append(formatted)
    return result


def _gen_health_assessment(
    scope: str, namespace: str, workload: Optional[str], include_thresholds: bool
) -> dict:
    """Generate health assessment report structure."""
    prompts: list[str] = []
    if scope == "cluster":
        prompts = [
            "kagent analyze cluster --health",
            "kagent analyze cluster --summary",
            "kagent analyze components --all",
            "kagent analyze nodes --all",
            "kagent analyze nodes --pressure",
        ]
    elif scope == "namespace":
        prompts = _format_prompts(
            [
                "kagent analyze workloads --namespace {namespace}",
                "kagent analyze resources --namespace {namespace} --detailed",
                "kagent analyze best-practices --namespace {namespace}",
                "kagent analyze config --namespace {namespace}",
            ],
            namespace,
        )
    elif scope == "workload":
        if workload:
            prompts = _format_prompts(
                [
                    "kagent analyze deployment {workload} --namespace {namespace}",
                    "kagent analyze deployment {workload} --replicas --utilization",
                    "kagent analyze pod {workload} --resources",
                ],
                namespace,
                workload,
            )
        else:
            prompts = _format_prompts(
                [
                    "kagent analyze workloads --namespace {namespace}",
                ],
                namespace,
            )

    result: dict = {
        "scope": scope,
        "namespace": namespace,
        "analysis_prompts": prompts,
        "health_categories": {
            "components": {"check": "API Server, etcd, scheduler, controller-manager"},
            "nodes": {"check": "Ready status, resource pressure, conditions"},
            "workloads": {"check": "Running pods, pending, CrashLoopBackOff"},
        },
    }

    if workload:
        result["workload"] = workload

    if include_thresholds:
        result["health_thresholds"] = HEALTH_THRESHOLDS

    return result


def _gen_resource_analysis(
    namespace: str, resource_type: Optional[str], waste_threshold: int
) -> dict:
    """Generate resource utilization analysis prompts and guidance."""
    prompts = _format_prompts(
        [
            "kagent analyze utilization --namespace {namespace}",
            "kagent analyze waste --namespace {namespace} --threshold {threshold}",
            "kagent analyze sizing-candidates --namespace {namespace}",
            "kagent analyze efficiency --below 30",
        ],
        namespace,
        threshold=waste_threshold,
    )

    if resource_type:
        prompts.append(
            f"kagent analyze utilization --type {resource_type} --namespace {namespace}"
        )

    return {
        "namespace": namespace,
        "resource_type": resource_type or "all",
        "waste_threshold_pct": waste_threshold,
        "analysis_prompts": prompts,
        "efficiency_bands": {
            "over_provisioned": f"Usage < {waste_threshold}% of request",
            "well_sized": f"Usage {waste_threshold}-80% of request",
            "under_provisioned": "Usage > 80% of request",
        },
        "utilization_thresholds": {
            "cpu": HEALTH_THRESHOLDS["cpu_utilization_pct"],
            "memory": HEALTH_THRESHOLDS["memory_utilization_pct"],
        },
    }


def _parse_resource_value(value: str) -> float:
    """Parse Kubernetes resource string to numeric millicores or MiB."""
    v = value.strip().lower()
    if v.endswith("mi"):
        return float(v[:-2])
    if v.endswith("gi"):
        return float(v[:-2]) * 1024
    if v.endswith("m"):
        return float(v[:-1])
    return float(v) * 1000  # assume cores → millicores


def _gen_sizing_recommendation(
    namespace: str,
    workload: Optional[str],
    level: str,
    current_cpu: Optional[str],
    current_mem: Optional[str],
    observed_cpu: Optional[str],
    observed_mem: Optional[str],
) -> dict:
    """Generate right-sizing recommendation."""
    config = OPTIMIZATION_CONFIGS[level]
    result: dict = {
        "namespace": namespace,
        "optimization_level": level,
        "level_config": config,
        "analysis_prompts": _format_prompts(
            [
                "kagent analyze sizing --namespace {namespace} --period 7d",
                "kagent recommend sizing --namespace {namespace} --{optimization_level}",
            ],
            namespace,
        ).copy(),
        "safety_reminder": "APPROVAL REQUIRED: All changes require explicit user confirmation.",
    }

    # Replace placeholder in second prompt
    result["analysis_prompts"][1] = result["analysis_prompts"][1].replace(
        "{optimization_level}", level
    )

    if workload:
        result["workload"] = workload
        result["analysis_prompts"].append(
            f"kagent recommend sizing --deployment {workload} --namespace {namespace}"
        )

    if observed_cpu and current_cpu:
        obs = _parse_resource_value(observed_cpu)
        cur = _parse_resource_value(current_cpu)
        recommended_request = math.ceil(obs * (1 + config["buffer_pct"] / 100))
        recommended_limit = math.ceil(recommended_request * config["limit_multiplier"])
        result["cpu_recommendation"] = {
            "current_request": current_cpu,
            "observed_p95": observed_cpu,
            "utilization_pct": round(obs / cur * 100, 1) if cur > 0 else 0,
            "recommended_request": f"{recommended_request}m",
            "recommended_limit": f"{recommended_limit}m",
            "rationale": f"{config['percentile']} ({observed_cpu}) + {config['buffer_pct']}% buffer",
        }

    if observed_mem and current_mem:
        obs = _parse_resource_value(observed_mem)
        cur = _parse_resource_value(current_mem)
        recommended_request = math.ceil(obs * (1 + config["buffer_pct"] / 100))
        recommended_limit = math.ceil(recommended_request * config["limit_multiplier"])
        result["memory_recommendation"] = {
            "current_request": current_mem,
            "observed_p95": observed_mem,
            "utilization_pct": round(obs / cur * 100, 1) if cur > 0 else 0,
            "recommended_request": f"{recommended_request}Mi",
            "recommended_limit": f"{recommended_limit}Mi",
            "rationale": f"{config['percentile']} ({observed_mem}) + {config['buffer_pct']}% buffer",
        }

    # Generate helm upgrade command if we have a workload and any recommendation
    if workload and (
        "cpu_recommendation" in result or "memory_recommendation" in result
    ):
        set_args = []
        if "cpu_recommendation" in result:
            set_args.append(
                f"--set {workload}.resources.requests.cpu={result['cpu_recommendation']['recommended_request']}"
            )
            set_args.append(
                f"--set {workload}.resources.limits.cpu={result['cpu_recommendation']['recommended_limit']}"
            )
        if "memory_recommendation" in result:
            set_args.append(
                f"--set {workload}.resources.requests.memory={result['memory_recommendation']['recommended_request']}"
            )
            set_args.append(
                f"--set {workload}.resources.limits.memory={result['memory_recommendation']['recommended_limit']}"
            )
        result["helm_upgrade_command"] = (
            f"helm upgrade <release> ./<chart> {' '.join(set_args)}"
        )

    return result


def _gen_workflow(
    workflow_type: str,
    namespace: str,
    level: str,
    chart_name: Optional[str],
    time_range: str,
) -> dict:
    """Generate a complete analysis workflow."""
    defn = WORKFLOW_DEFINITIONS[workflow_type]
    steps = []
    for s in defn["steps"]:
        cmd = s["cmd"].format(
            namespace=namespace,
            optimization_level=level,
            chart=chart_name or "<chart>",
            time_range=time_range,
        )
        steps.append({"step": s["step"], "name": s["name"], "command": cmd})

    return {
        "workflow_type": workflow_type,
        "title": defn["title"],
        "purpose": defn["purpose"],
        "namespace": namespace,
        "optimization_level": level,
        "steps": steps,
        "advisory_notice": "All outputs are recommendations only. User must explicitly approve any changes.",
    }


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def kagent_generate_prompt(
    analysis_type: str,
    scope: str = "namespace",
    namespace: str = "default",
    workload: str | None = None,
    time_range: str = "24h",
) -> str:
    """Generate kagent/k8sgpt analysis prompts for a given analysis type and scope.

    Returns JSON with ready-to-use kagent CLI prompts tailored to the analysis type,
    scope, namespace, and optional workload target.
    """
    inp = KagentGeneratePromptInput(
        analysis_type=analysis_type,
        scope=scope,
        namespace=namespace,
        workload=workload,
        time_range=time_range,
    )

    category_key = inp.analysis_type
    if category_key == "health":
        category_key = "cluster-health"
    elif category_key == "resources":
        category_key = "resource-utilization"

    raw_prompts = PROMPT_CATEGORIES.get(category_key, [])
    prompts = _format_prompts(raw_prompts, inp.namespace, inp.workload, inp.time_range)

    return json.dumps(
        {
            "analysis_type": inp.analysis_type,
            "scope": inp.scope,
            "namespace": inp.namespace,
            "workload": inp.workload,
            "time_range": inp.time_range,
            "prompts": prompts,
            "output_formats": ["--output json", "--output yaml", "--output table"],
        },
        indent=2,
    )


@mcp.tool()
async def kagent_assess_health(
    scope: str = "cluster",
    namespace: str = "default",
    workload: str | None = None,
    include_thresholds: bool = True,
) -> str:
    """Assess cluster, namespace, or workload health with diagnostic prompts and thresholds.

    Returns JSON with kagent prompts for health assessment, health categories to check,
    and optional threshold reference values for interpreting results.
    """
    inp = KagentAssessHealthInput(
        scope=scope,
        namespace=namespace,
        workload=workload,
        include_thresholds=include_thresholds,
    )
    result = _gen_health_assessment(
        inp.scope, inp.namespace, inp.workload, inp.include_thresholds
    )
    return json.dumps(result, indent=2)


@mcp.tool()
async def kagent_analyze_resources(
    namespace: str = "default",
    resource_type: str | None = None,
    waste_threshold_pct: int = 50,
) -> str:
    """Analyze resource utilization and detect waste in a namespace.

    Returns JSON with analysis prompts, efficiency bands, and utilization thresholds
    for identifying over-provisioned and under-provisioned workloads.
    """
    inp = KagentAnalyzeResourcesInput(
        namespace=namespace,
        resource_type=resource_type,
        waste_threshold_pct=waste_threshold_pct,
    )
    result = _gen_resource_analysis(
        inp.namespace, inp.resource_type, inp.waste_threshold_pct
    )
    return json.dumps(result, indent=2)


@mcp.tool()
async def kagent_recommend_sizing(
    namespace: str = "default",
    workload: str | None = None,
    optimization_level: str = "conservative",
    current_cpu_request: str | None = None,
    current_memory_request: str | None = None,
    observed_cpu_p95: str | None = None,
    observed_memory_p95: str | None = None,
) -> str:
    """Generate resource right-sizing recommendations with Helm upgrade commands.

    Provide current and observed values for concrete recommendations. Without observed
    values, returns analysis prompts to gather the data first.
    Returns JSON with sizing recommendations, rationale, and helm upgrade commands.
    """
    inp = KagentRecommendSizingInput(
        namespace=namespace,
        workload=workload,
        optimization_level=optimization_level,
        current_cpu_request=current_cpu_request,
        current_memory_request=current_memory_request,
        observed_cpu_p95=observed_cpu_p95,
        observed_memory_p95=observed_memory_p95,
    )
    result = _gen_sizing_recommendation(
        inp.namespace,
        inp.workload,
        inp.optimization_level,
        inp.current_cpu_request,
        inp.current_memory_request,
        inp.observed_cpu_p95,
        inp.observed_memory_p95,
    )
    return json.dumps(result, indent=2)


@mcp.tool()
async def kagent_detect_antipatterns(
    namespace: str = "default",
    include_fixes: bool = True,
) -> str:
    """Detect common Kubernetes resource anti-patterns and suggest fixes.

    Returns JSON with all known anti-patterns, their detection criteria, impact,
    and fix recommendations along with kagent prompts to check for each.
    """
    inp = KagentDetectAntipatternsInput(
        namespace=namespace,
        include_fixes=include_fixes,
    )
    patterns = []
    for name, info in ANTIPATTERNS.items():
        entry: dict = {
            "pattern": name,
            "description": info["description"],
            "detection": info["detection"],
            "impact": info["impact"],
        }
        if inp.include_fixes:
            entry["fix"] = info["fix"]
        patterns.append(entry)

    return json.dumps(
        {
            "namespace": inp.namespace,
            "antipatterns": patterns,
            "detection_prompts": _format_prompts(
                [
                    "kagent analyze best-practices --namespace {namespace}",
                    "kagent analyze config --validate-limits --namespace {namespace}",
                    "kagent analyze containers --security --namespace {namespace}",
                    "kagent analyze images --namespace {namespace} --tags",
                ],
                inp.namespace,
            ),
        },
        indent=2,
    )


@mcp.tool()
async def kagent_generate_workflow(
    workflow_type: str,
    namespace: str = "default",
    optimization_level: str = "conservative",
    chart_name: str | None = None,
    time_range: str = "24h",
) -> str:
    """Generate a complete multi-step analysis workflow with ordered kagent commands.

    Returns JSON with numbered workflow steps, each containing the kagent command
    to run. Workflow types: cluster-assessment, namespace-health, pre-deployment,
    performance-investigation, right-sizing, security-audit, cost-analysis,
    anomaly-investigation.
    """
    inp = KagentGenerateWorkflowInput(
        workflow_type=workflow_type,
        namespace=namespace,
        optimization_level=optimization_level,
        chart_name=chart_name,
        time_range=time_range,
    )
    result = _gen_workflow(
        inp.workflow_type,
        inp.namespace,
        inp.optimization_level,
        inp.chart_name,
        inp.time_range,
    )
    return json.dumps(result, indent=2)


@mcp.tool()
async def kagent_validate_predeployment(
    namespace: str = "default",
    chart_name: str | None = None,
    values_file: str = "values.yaml",
) -> str:
    """Generate pre-deployment validation checklist with kagent prompts.

    Returns JSON with validation categories (resources, configuration, security,
    images) and corresponding kagent commands to verify each item before deploying.
    """
    inp = KagentValidatePredeploymentInput(
        namespace=namespace,
        chart_name=chart_name,
        values_file=values_file,
    )
    chart = inp.chart_name or "<chart>"

    checklist = [
        {
            "category": "Resources",
            "item": "Sufficient cluster resources",
            "cmd": f"kagent analyze capacity --for-deployment ./{inp.values_file}",
        },
        {
            "category": "Configuration",
            "item": "Chart linting passes",
            "cmd": f"kagent validate chart ./{chart} --values {inp.values_file}",
        },
        {
            "category": "Configuration",
            "item": "Best practices met",
            "cmd": "kagent lint deployment --strict",
        },
        {
            "category": "Configuration",
            "item": "Resource limits defined",
            "cmd": f"kagent analyze config --validate-limits --namespace {inp.namespace}",
        },
        {
            "category": "Configuration",
            "item": "Probes configured",
            "cmd": f"kagent analyze probes --namespace {inp.namespace}",
        },
        {
            "category": "Security",
            "item": "Security context set",
            "cmd": f"kagent analyze containers --security --namespace {inp.namespace}",
        },
        {
            "category": "Images",
            "item": "Image tags specific (not :latest)",
            "cmd": f"kagent analyze images --namespace {inp.namespace} --tags",
        },
        {
            "category": "Risk",
            "item": "Risk assessment",
            "cmd": f"kagent assess risk --deployment {chart}",
        },
    ]

    return json.dumps(
        {
            "namespace": inp.namespace,
            "chart_name": chart,
            "values_file": inp.values_file,
            "checklist": checklist,
            "advisory_notice": "Complete all checks before running helm install/upgrade.",
        },
        indent=2,
    )


@mcp.tool()
async def kagent_analyze_performance(
    namespace: str = "default",
    workload: str | None = None,
    time_range: str = "24h",
    observed_anomalies: list[str] | None = None,
) -> str:
    """Analyze performance indicators and generate diagnostic prompts.

    Returns JSON with performance indicators, thresholds, analysis prompts,
    and a diagnostic checklist when anomalies are reported.
    """
    inp = KagentAnalyzePerformanceInput(
        namespace=namespace,
        workload=workload,
        time_range=time_range,
        observed_anomalies=observed_anomalies,
    )

    indicators = {}
    for key, info in PERFORMANCE_INDICATORS.items():
        indicators[key] = {
            "metric": info["metric"],
            "good": info["good"],
            "needs_attention": info["needs_attention"],
            "prompts": _format_prompts(
                info["prompts"], inp.namespace, inp.workload, inp.time_range
            ),
        }

    result: dict = {
        "namespace": inp.namespace,
        "time_range": inp.time_range,
        "performance_indicators": indicators,
        "general_prompts": _format_prompts(
            [
                "kagent analyze performance --namespace {namespace}",
                "kagent analyze bottlenecks --namespace {namespace} --top 5",
                "kagent analyze trends --namespace {namespace} --period {time_range}",
            ],
            inp.namespace,
            inp.workload,
            inp.time_range,
        ),
    }

    if inp.workload:
        result["workload"] = inp.workload
        result["workload_prompts"] = _format_prompts(
            [
                "kagent analyze performance --deployment {workload} -n {namespace}",
                "kagent analyze bottlenecks --deployment {workload} -n {namespace}",
                "kagent analyze resources --deployment {workload} --pressure",
            ],
            inp.namespace,
            inp.workload,
            inp.time_range,
        )

    if inp.observed_anomalies:
        result["observed_anomalies"] = inp.observed_anomalies
        diagnostic_checklist = [
            "CPU throttling (limits too low?)",
            "Memory pressure (approaching limits?)",
            "Network latency (DNS, service mesh?)",
            "Resource contention (noisy neighbors?)",
            "Disk I/O bottleneck (storage class?)",
        ]
        # Match anomalies to known types
        matched_anomalies = []
        for anomaly_text in inp.observed_anomalies:
            lower = anomaly_text.lower()
            for atype, ainfo in ANOMALY_TYPES.items():
                causes_match = any(
                    c.lower() in lower for c in ainfo["potential_causes"]
                )
                type_match = atype.replace("-", " ") in lower
                keyword_match = any(
                    kw in lower
                    for kw in [
                        "restart",
                        "pending",
                        "evict",
                        "probe",
                        "image",
                        "pvc",
                        "latency",
                        "timeout",
                        "crash",
                        "oom",
                    ]
                )
                if causes_match or type_match or keyword_match:
                    matched_anomalies.append(
                        {
                            "observed": anomaly_text,
                            "likely_type": atype,
                            "potential_causes": ainfo["potential_causes"],
                            "investigation_prompts": _format_prompts(
                                ainfo["investigation_prompts"],
                                inp.namespace,
                                inp.workload,
                                inp.time_range,
                            ),
                        }
                    )
                    break
        if matched_anomalies:
            result["matched_anomalies"] = matched_anomalies
        result["diagnostic_checklist"] = diagnostic_checklist

    return json.dumps(result, indent=2)


@mcp.tool()
async def kagent_audit_security(
    namespace: str = "default",
    include_prompts: bool = True,
) -> str:
    """Generate a security audit checklist with kagent prompts for each check.

    Returns JSON with categorized security checks (container security, resources,
    network, RBAC, secrets, images) and corresponding analysis commands.
    """
    inp = KagentAuditSecurityInput(
        namespace=namespace,
        include_prompts=include_prompts,
    )

    items = []
    for check in SECURITY_CHECKLIST:
        entry: dict = {
            "category": check["category"],
            "item": check["item"],
        }
        if inp.include_prompts:
            entry["command"] = check["cmd"].format(namespace=inp.namespace)
        items.append(entry)

    return json.dumps(
        {
            "namespace": inp.namespace,
            "audit_checklist": items,
            "workflow_prompts": _format_prompts(
                [
                    "kagent analyze security --namespace {namespace}",
                    "kagent analyze rbac --namespace {namespace}",
                    "kagent analyze pod-security --namespace {namespace}",
                    "kagent analyze network-security --namespace {namespace}",
                ],
                inp.namespace,
            ),
            "advisory_notice": "Security findings are recommendations only. Review and apply through Helm values.",
        },
        indent=2,
    )


@mcp.tool()
async def kagent_explain_concept(
    concept: str,
    namespace: str = "default",
) -> str:
    """Explain a Kubernetes optimization concept with educational context and related prompts.

    Returns JSON with concept title, summary, detailed explanation, and kagent prompts
    for hands-on exploration.
    """
    inp = KagentExplainConceptInput(
        concept=concept,
        namespace=namespace,
    )
    info = CONCEPT_EXPLANATIONS[inp.concept]

    return json.dumps(
        {
            "concept": inp.concept,
            "title": info["title"],
            "summary": info["summary"],
            "details": info["details"],
            "related_prompts": _format_prompts(
                info["related_prompts"], inp.namespace or "default"
            ),
            "all_concepts": list(VALID_CONCEPTS),
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
