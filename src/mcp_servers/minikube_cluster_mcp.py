"""
Minikube Cluster MCP Server — generates cluster configurations, validates
readiness, troubleshoots issues, and manages local Kubernetes lifecycle.

Tools:
    minikube_generate_config         Generate minikube start command
    minikube_suggest_addons          Suggest addons for a use case
    minikube_validate_readiness      Validate cluster/Helm readiness checklist
    minikube_diagnose_startup        Diagnose cluster startup issues
    minikube_diagnose_networking     Diagnose networking/access issues
    minikube_diagnose_storage        Diagnose storage/PVC issues
    minikube_suggest_lifecycle       Suggest lifecycle commands
    minikube_recommend_resources     Recommend resources for a workload
    minikube_generate_ci_config      Generate CI/CD minikube configs
    minikube_list_error_solutions    Look up error messages and solutions
"""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("minikube_cluster_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_PROFILES = ("minimal", "standard", "heavy")
VALID_DRIVERS = ("docker", "podman", "hyperv", "virtualbox", "kvm2")
VALID_RUNTIMES = ("containerd", "docker", "cri-o")
VALID_CNI = ("bridge", "calico", "cilium", "flannel")
VALID_PLATFORMS = ("linux", "macos", "windows")
VALID_CI_PLATFORMS = ("github-actions", "gitlab-ci", "jenkins")

RESOURCE_PROFILES: dict[str, dict] = {
    "minimal": {
        "cpus": 2,
        "memory": "2048",
        "disk_size": "10g",
        "description": "Learning basics, simple pods",
    },
    "standard": {
        "cpus": 4,
        "memory": "4096",
        "disk_size": "20g",
        "description": "Helm charts, multi-service apps",
    },
    "heavy": {
        "cpus": 6,
        "memory": "8192",
        "disk_size": "40g",
        "description": "Multi-node, complex workloads",
    },
}

ADDON_CATALOG: dict[str, dict] = {
    "ingress": {
        "purpose": "HTTP routing via Nginx ingress controller",
        "when": "External access to services needed",
        "use_cases": ["helm-testing", "development", "multi-service"],
    },
    "metrics-server": {
        "purpose": "Resource usage metrics (kubectl top, HPA)",
        "when": "Monitoring or autoscaling needed",
        "use_cases": ["helm-testing", "development", "production-like"],
    },
    "dashboard": {
        "purpose": "Web-based cluster management UI",
        "when": "Visual cluster management desired",
        "use_cases": ["learning", "development"],
    },
    "storage-provisioner": {
        "purpose": "Dynamic PersistentVolume provisioning",
        "when": "StatefulSets or PVCs used",
        "use_cases": ["helm-testing", "development", "production-like"],
    },
    "default-storageclass": {
        "purpose": "Default StorageClass for PVC claims",
        "when": "Helm charts with persistence enabled",
        "use_cases": ["helm-testing", "development", "production-like"],
    },
    "registry": {
        "purpose": "In-cluster container image registry",
        "when": "Building and testing images locally",
        "use_cases": ["development", "ci-cd"],
    },
}

USE_CASE_ADDONS: dict[str, list[str]] = {
    "learning": ["dashboard", "metrics-server"],
    "development": ["ingress", "dashboard", "metrics-server", "storage-provisioner"],
    "helm-testing": [
        "ingress",
        "storage-provisioner",
        "default-storageclass",
        "metrics-server",
    ],
    "production-like": [
        "ingress",
        "metrics-server",
        "storage-provisioner",
        "default-storageclass",
    ],
    "ci-cd": ["registry", "metrics-server"],
}

DRIVER_PLATFORMS: dict[str, list[str]] = {
    "docker": ["linux", "macos", "windows"],
    "podman": ["linux", "macos"],
    "hyperv": ["windows"],
    "virtualbox": ["linux", "macos", "windows"],
    "kvm2": ["linux"],
}

STARTUP_ISSUES: dict[str, dict] = {
    "wont_start": {
        "title": "Cluster Won't Start",
        "symptoms": "minikube start hangs or fails",
        "diagnostics": [
            "minikube status",
            "minikube logs --file=minikube-logs.txt",
            "docker ps  # if using docker driver",
        ],
        "causes": [
            {
                "cause": "Driver not running",
                "diagnosis": "docker ps fails",
                "solution": "Start Docker Desktop/daemon",
            },
            {
                "cause": "Insufficient resources",
                "diagnosis": "OOM or resource errors in logs",
                "solution": "Reduce --memory or --cpus",
            },
            {
                "cause": "Corrupted cluster",
                "diagnosis": "Previous failed start",
                "solution": "minikube delete && minikube start",
            },
            {
                "cause": "Network issues",
                "diagnosis": "Timeout pulling images",
                "solution": "Check proxy settings, internet connectivity",
            },
            {
                "cause": "Permission denied",
                "diagnosis": "Permission errors in logs",
                "solution": "Run as admin or fix docker group membership",
            },
        ],
    },
    "guest_provision": {
        "title": "GUEST_PROVISION Error",
        "symptoms": "Exiting due to GUEST_PROVISION",
        "diagnostics": [
            "minikube logs --problems",
        ],
        "causes": [
            {
                "cause": "Corrupted VM/container state",
                "diagnosis": "Error during provisioning",
                "solution": "minikube delete --purge && minikube start",
            },
            {
                "cause": "Driver mismatch",
                "diagnosis": "Wrong driver for platform",
                "solution": "Specify correct driver: --driver=docker",
            },
        ],
    },
    "api_server_down": {
        "title": "API Server Not Responding",
        "symptoms": "kubectl commands timeout, connection refused",
        "diagnostics": [
            "minikube status",
            "docker ps | grep minikube  # docker driver",
            'minikube ssh "curl -k https://localhost:8443/healthz"',
        ],
        "causes": [
            {
                "cause": "Cluster stopped",
                "diagnosis": "host: Stopped in status",
                "solution": "minikube start",
            },
            {
                "cause": "API server crash",
                "diagnosis": "apiserver: Stopped",
                "solution": "minikube stop && minikube start",
            },
            {
                "cause": "Kubeconfig stale",
                "diagnosis": "Context points to old cluster",
                "solution": "minikube update-context",
            },
        ],
    },
    "stuck_starting": {
        "title": "Cluster Stuck Starting",
        "symptoms": "Status shows Starting for extended period",
        "diagnostics": [
            "minikube logs --file=cluster-start.log",
            'minikube ssh "journalctl -u kubelet"',
        ],
        "causes": [
            {
                "cause": "Image pull timeout",
                "diagnosis": "Pulling image logs",
                "solution": "Check internet, use minikube cache add",
            },
            {
                "cause": "DNS issues",
                "diagnosis": "DNS resolution errors",
                "solution": "Check /etc/resolv.conf, proxy settings",
            },
            {
                "cause": "Resource exhaustion",
                "diagnosis": "Node OOM events",
                "solution": "Increase --memory allocation",
            },
        ],
    },
}

NETWORKING_ISSUES: dict[str, dict] = {
    "service_unreachable": {
        "title": "Services Not Accessible from Host",
        "symptoms": "Cannot reach services from host machine",
        "diagnostics": [
            "kubectl get svc",
            "kubectl get endpoints",
            "minikube service list",
            "minikube ip",
        ],
        "solutions_by_type": {
            "ClusterIP": "kubectl port-forward svc/<name> 8080:80",
            "NodePort": "minikube service <name> --url",
            "LoadBalancer": "minikube tunnel  # must run continuously",
            "Ingress": "minikube addons enable ingress && add to /etc/hosts",
        },
    },
    "ingress_broken": {
        "title": "Ingress Not Working",
        "symptoms": "Ingress returns 404 or times out",
        "diagnostics": [
            "minikube addons list | grep ingress",
            "kubectl get pods -n ingress-nginx",
            "kubectl get ingress",
            "kubectl get ingress -o wide",
        ],
        "causes": [
            {
                "cause": "Addon not enabled",
                "solution": "minikube addons enable ingress",
            },
            {
                "cause": "Controller not ready",
                "solution": "Wait and check: kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx",
            },
            {
                "cause": "Wrong host header",
                "solution": "Add to /etc/hosts: $(minikube ip) myapp.local",
            },
            {
                "cause": "Missing ingressClassName",
                "solution": "Add ingressClassName: nginx to Ingress spec",
            },
        ],
    },
    "dns_failure": {
        "title": "DNS Resolution Fails in Cluster",
        "symptoms": "Pods cannot resolve service names",
        "diagnostics": [
            "kubectl get pods -n kube-system -l k8s-app=kube-dns",
            "kubectl logs -n kube-system -l k8s-app=kube-dns",
            "kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup kubernetes.default",
        ],
        "causes": [
            {
                "cause": "CoreDNS pods not running",
                "solution": "Check kube-system pods, restart minikube",
            },
            {
                "cause": "Network policy blocking DNS",
                "solution": "Allow UDP 53 egress to kube-system",
            },
        ],
    },
    "loadbalancer_pending": {
        "title": "LoadBalancer Stuck on Pending",
        "symptoms": "EXTERNAL-IP shows <pending>",
        "diagnostics": [
            "kubectl get svc",
        ],
        "causes": [
            {
                "cause": "No tunnel running",
                "solution": "Run 'minikube tunnel' in a separate terminal",
            },
        ],
    },
}

STORAGE_ISSUES: dict[str, dict] = {
    "pvc_pending": {
        "title": "PVC Stuck in Pending",
        "symptoms": "PersistentVolumeClaim remains in Pending state",
        "diagnostics": [
            "kubectl get pvc",
            "kubectl describe pvc <pvc-name>",
            "kubectl get sc",
            "kubectl describe sc standard",
        ],
        "causes": [
            {
                "cause": "Storage provisioner not enabled",
                "solution": "minikube addons enable storage-provisioner && minikube addons enable default-storageclass",
            },
            {
                "cause": "StorageClass missing",
                "solution": "Verify: kubectl get sc  # should show 'standard'",
            },
            {
                "cause": "Incompatible accessMode",
                "solution": "Use ReadWriteOnce for hostPath storage",
            },
        ],
    },
    "permission_denied": {
        "title": "Volume Permission Denied",
        "symptoms": "Container cannot write to mounted volume",
        "diagnostics": [
            "kubectl describe pod <pod-name>",
            "kubectl logs <pod-name>",
        ],
        "causes": [
            {
                "cause": "Missing fsGroup",
                "solution": "Add securityContext.fsGroup: 1000 to pod spec",
            },
            {
                "cause": "Wrong runAsUser",
                "solution": "Set securityContext.runAsUser to match volume owner",
            },
            {
                "cause": "ReadOnly volume",
                "solution": "Check volumeMount readOnly setting",
            },
        ],
    },
}

ERROR_LOOKUP: dict[str, dict[str, str]] = {
    "machine does not exist": {
        "cause": "Deleted or corrupted cluster",
        "fix": "minikube delete && minikube start",
    },
    "kubeconfig not found": {
        "cause": "Context not set",
        "fix": "minikube update-context",
    },
    "connection refused": {
        "cause": "API server down",
        "fix": "minikube stop && minikube start",
    },
    "unable to upgrade connection": {
        "cause": "kubectl version mismatch",
        "fix": "Update kubectl to match cluster version",
    },
    "no space left on device": {
        "cause": "Disk full",
        "fix": "Increase --disk-size, prune images: docker system prune",
    },
    "unable to resolve host": {
        "cause": "DNS issues",
        "fix": "Check network connectivity and proxy settings",
    },
    "ImagePullBackOff": {
        "cause": "Cannot pull container image",
        "fix": "Check image name/tag, registry access, or use eval $(minikube docker-env)",
    },
    "CrashLoopBackOff": {
        "cause": "Container keeps crashing",
        "fix": "Check kubectl logs <pod-name> --previous",
    },
    "Pending": {
        "cause": "Resources or config issue",
        "fix": "kubectl describe <resource> for details",
    },
    "OOMKilled": {
        "cause": "Out of memory",
        "fix": "Increase container memory limits or minikube --memory",
    },
    "ErrImagePull": {
        "cause": "Image not found in registry",
        "fix": "Verify image exists: docker pull <image>",
    },
    "Insufficient cpu": {
        "cause": "Not enough CPU on node",
        "fix": "Restart minikube with higher --cpus",
    },
    "Insufficient memory": {
        "cause": "Not enough memory on node",
        "fix": "Restart minikube with higher --memory",
    },
    "no persistent volumes available": {
        "cause": "No PV matches PVC",
        "fix": "Enable: minikube addons enable storage-provisioner",
    },
    "Hyper-V is not available": {
        "cause": "Hyper-V feature disabled",
        "fix": "Enable Hyper-V in Windows Features, use Pro/Enterprise edition",
    },
    "Cannot connect to the Docker daemon": {
        "cause": "Docker not running",
        "fix": "Start Docker Desktop or: sudo systemctl start docker",
    },
    "VT-x is not available": {
        "cause": "Virtualization disabled in BIOS",
        "fix": "Enable VT-x/AMD-V in BIOS/UEFI settings",
    },
}

# ---------------------------------------------------------------------------
# Pydantic Input Models
# ---------------------------------------------------------------------------


class ConfigGenerateInput(BaseModel):
    """Input for minikube_generate_config."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    profile_name: str = Field(
        "standard", description="Resource profile: minimal, standard, heavy"
    )
    kubernetes_version: str = Field("v1.29.0", description="Kubernetes version")
    driver: str = Field("docker", description="Virtualization driver")
    addons: list[str] = Field(default_factory=list, description="Addons to enable")
    nodes: int = Field(1, ge=1, le=10, description="Number of cluster nodes")
    cpus: int | None = Field(None, ge=1, le=32, description="Override CPU count")
    memory: str | None = Field(None, description="Override memory (e.g. '4096')")
    disk_size: str | None = Field(None, description="Override disk size (e.g. '20g')")
    container_runtime: str = Field("containerd", description="Container runtime")
    cni: str | None = Field(None, description="CNI plugin")
    extra_config: list[str] = Field(
        default_factory=list, description="Extra config flags"
    )

    @field_validator("profile_name")
    @classmethod
    def validate_profile(cls, v: str) -> str:
        if v not in VALID_PROFILES:
            raise ValueError(f"profile_name must be one of {VALID_PROFILES}")
        return v

    @field_validator("driver")
    @classmethod
    def validate_driver(cls, v: str) -> str:
        if v not in VALID_DRIVERS:
            raise ValueError(f"driver must be one of {VALID_DRIVERS}")
        return v

    @field_validator("container_runtime")
    @classmethod
    def validate_runtime(cls, v: str) -> str:
        if v not in VALID_RUNTIMES:
            raise ValueError(f"container_runtime must be one of {VALID_RUNTIMES}")
        return v


class AddonSuggestInput(BaseModel):
    """Input for minikube_suggest_addons."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    use_case: str = Field(
        ...,
        description="Use case: learning, development, helm-testing, production-like, ci-cd",
    )

    @field_validator("use_case")
    @classmethod
    def validate_use_case(cls, v: str) -> str:
        if v not in USE_CASE_ADDONS:
            raise ValueError(f"use_case must be one of {list(USE_CASE_ADDONS.keys())}")
        return v


class ReadinessInput(BaseModel):
    """Input for minikube_validate_readiness."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    check_helm: bool = Field(True, description="Include Helm readiness checks")
    check_ingress: bool = Field(False, description="Include ingress readiness checks")
    check_storage: bool = Field(False, description="Include storage readiness checks")
    check_metrics: bool = Field(False, description="Include metrics readiness checks")


class StartupDiagnoseInput(BaseModel):
    """Input for minikube_diagnose_startup."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    issue_type: str = Field(
        ...,
        description="Issue: wont_start, guest_provision, api_server_down, stuck_starting",
    )

    @field_validator("issue_type")
    @classmethod
    def validate_issue(cls, v: str) -> str:
        valid = tuple(STARTUP_ISSUES.keys())
        if v not in valid:
            raise ValueError(f"issue_type must be one of {valid}")
        return v


class NetworkDiagnoseInput(BaseModel):
    """Input for minikube_diagnose_networking."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    issue_type: str = Field(
        ...,
        description="Issue: service_unreachable, ingress_broken, dns_failure, loadbalancer_pending",
    )

    @field_validator("issue_type")
    @classmethod
    def validate_issue(cls, v: str) -> str:
        valid = tuple(NETWORKING_ISSUES.keys())
        if v not in valid:
            raise ValueError(f"issue_type must be one of {valid}")
        return v


class StorageDiagnoseInput(BaseModel):
    """Input for minikube_diagnose_storage."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    issue_type: str = Field(..., description="Issue: pvc_pending, permission_denied")

    @field_validator("issue_type")
    @classmethod
    def validate_issue(cls, v: str) -> str:
        valid = tuple(STORAGE_ISSUES.keys())
        if v not in valid:
            raise ValueError(f"issue_type must be one of {valid}")
        return v


class LifecycleInput(BaseModel):
    """Input for minikube_suggest_lifecycle."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    action: str = Field(
        ...,
        description="Action: start, stop, pause, unpause, delete, status, ssh, tunnel",
    )
    profile: str | None = Field(None, description="Profile name")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        valid = (
            "start",
            "stop",
            "pause",
            "unpause",
            "delete",
            "status",
            "ssh",
            "tunnel",
        )
        if v not in valid:
            raise ValueError(f"action must be one of {valid}")
        return v


class ResourceRecommendInput(BaseModel):
    """Input for minikube_recommend_resources."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    workload_type: str = Field(
        ..., description="Workload: single-pod, multi-service, helm-chart, multi-node"
    )
    estimated_pods: int = Field(5, ge=1, le=100, description="Estimated number of pods")
    needs_persistence: bool = Field(False, description="Whether PVCs are needed")
    needs_ingress: bool = Field(False, description="Whether ingress is needed")


class CIConfigInput(BaseModel):
    """Input for minikube_generate_ci_config."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    ci_platform: str = Field(
        ..., description="CI platform: github-actions, gitlab-ci, jenkins"
    )
    kubernetes_version: str = Field("v1.29.0", description="Kubernetes version")
    chart_path: str | None = Field(None, description="Helm chart path for testing")

    @field_validator("ci_platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        if v not in VALID_CI_PLATFORMS:
            raise ValueError(f"ci_platform must be one of {VALID_CI_PLATFORMS}")
        return v


class ErrorLookupInput(BaseModel):
    """Input for minikube_list_error_solutions."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    error_message: str | None = Field(
        None, description="Specific error message to look up"
    )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def minikube_generate_config(
    profile_name: str = "standard",
    kubernetes_version: str = "v1.29.0",
    driver: str = "docker",
    addons: list[str] | None = None,
    nodes: int = 1,
    cpus: int | None = None,
    memory: str | None = None,
    disk_size: str | None = None,
    container_runtime: str = "containerd",
    cni: str | None = None,
    extra_config: list[str] | None = None,
) -> str:
    """Generate a minikube start command with recommended configuration.

    Returns JSON: {command, profile_details, post_start_checks, notes}
    This is a SUGGESTION — not executed. Configurations target local development.
    """
    parsed = ConfigGenerateInput(
        profile_name=profile_name,
        kubernetes_version=kubernetes_version,
        driver=driver,
        addons=addons or [],
        nodes=nodes,
        cpus=cpus,
        memory=memory,
        disk_size=disk_size,
        container_runtime=container_runtime,
        cni=cni,
        extra_config=extra_config or [],
    )

    profile = RESOURCE_PROFILES[parsed.profile_name]
    use_cpus = parsed.cpus or profile["cpus"]
    use_memory = parsed.memory or profile["memory"]
    use_disk = parsed.disk_size or profile["disk_size"]

    parts = ["minikube start"]
    parts.append(f"    --driver={parsed.driver}")
    parts.append(f"    --kubernetes-version={parsed.kubernetes_version}")
    parts.append(f"    --cpus={use_cpus}")
    parts.append(f"    --memory={use_memory}")
    parts.append(f"    --disk-size={use_disk}")

    if parsed.container_runtime != "containerd":
        parts.append(f"    --container-runtime={parsed.container_runtime}")

    if parsed.cni:
        parts.append(f"    --cni={parsed.cni}")

    if parsed.nodes > 1:
        parts.append(f"    --nodes={parsed.nodes}")

    if parsed.addons:
        parts.append(f"    --addons={','.join(parsed.addons)}")

    for ec in parsed.extra_config:
        parts.append(f"    --extra-config={ec}")

    command = " \\\n".join(parts)

    total_cpus = use_cpus * parsed.nodes if isinstance(use_cpus, int) else use_cpus
    total_mem = int(use_memory) * parsed.nodes if use_memory.isdigit() else use_memory

    post_checks = [
        "minikube status  # Expect: host=Running, kubelet=Running, apiserver=Running",
        "kubectl cluster-info  # Verify API server accessible",
        "kubectl get nodes  # Verify node(s) Ready",
    ]

    if "ingress" in parsed.addons:
        post_checks.append(
            "kubectl get pods -n ingress-nginx  # Verify ingress controller running"
        )

    if (
        "storage-provisioner" in parsed.addons
        or "default-storageclass" in parsed.addons
    ):
        post_checks.append("kubectl get sc  # Verify default storage class exists")

    if "metrics-server" in parsed.addons:
        post_checks.append(
            "kubectl top nodes  # Verify metrics available (may take 1-2 min)"
        )

    return json.dumps(
        {
            "status": "success",
            "command": command,
            "profile_details": {
                "profile": parsed.profile_name,
                "cpus_per_node": use_cpus,
                "memory_per_node_mb": use_memory,
                "disk_size": use_disk,
                "total_nodes": parsed.nodes,
                "total_cpus": total_cpus,
                "total_memory_mb": total_mem,
            },
            "post_start_checks": post_checks,
            "notes": [
                "SUGGESTION ONLY — not executed",
                f"Profile: {parsed.profile_name} ({profile['description']})",
                f"Driver: {parsed.driver}",
                f"Resources per node: {use_cpus} CPUs, {use_memory}MB RAM, {use_disk} disk",
            ],
        },
        indent=2,
    )


@mcp.tool()
async def minikube_suggest_addons(
    use_case: str,
) -> str:
    """Suggest minikube addons based on your use case.

    Returns JSON: {use_case, recommended_addons, addon_details}
    Use cases: learning, development, helm-testing, production-like, ci-cd
    """
    parsed = AddonSuggestInput(use_case=use_case)

    recommended = USE_CASE_ADDONS[parsed.use_case]
    details = []
    for addon_name in recommended:
        addon = ADDON_CATALOG.get(addon_name, {})
        details.append(
            {
                "name": addon_name,
                "purpose": addon.get("purpose", ""),
                "when": addon.get("when", ""),
            }
        )

    enable_cmd = (
        f"minikube addons enable {' '.join(recommended)}"
        if len(recommended) == 1
        else None
    )
    if not enable_cmd:
        enable_cmd = " && ".join(f"minikube addons enable {a}" for a in recommended)

    return json.dumps(
        {
            "status": "success",
            "use_case": parsed.use_case,
            "recommended_addons": recommended,
            "addon_details": details,
            "enable_command": enable_cmd,
            "notes": [
                "SUGGESTION ONLY — not executed",
                "Addons can also be enabled at start: --addons="
                + ",".join(recommended),
            ],
        }
    )


@mcp.tool()
async def minikube_validate_readiness(
    check_helm: bool = True,
    check_ingress: bool = False,
    check_storage: bool = False,
    check_metrics: bool = False,
) -> str:
    """Generate a validation checklist for cluster and Helm readiness.

    Returns JSON: {checklist}
    Each check includes the command to run and expected output.
    """
    parsed = ReadinessInput(
        check_helm=check_helm,
        check_ingress=check_ingress,
        check_storage=check_storage,
        check_metrics=check_metrics,
    )

    checklist: list[dict] = []

    # Core cluster checks (always)
    checklist.extend(
        [
            {
                "category": "cluster",
                "check": "Cluster status",
                "command": "minikube status",
                "expected": "host: Running, kubelet: Running, apiserver: Running",
            },
            {
                "category": "cluster",
                "check": "API server responding",
                "command": "kubectl cluster-info",
                "expected": "Kubernetes control plane is running",
            },
            {
                "category": "cluster",
                "check": "Node ready",
                "command": "kubectl get nodes",
                "expected": "STATUS: Ready",
            },
            {
                "category": "cluster",
                "check": "System pods healthy",
                "command": "kubectl get pods -n kube-system",
                "expected": "All pods Running",
            },
        ]
    )

    if parsed.check_helm:
        checklist.extend(
            [
                {
                    "category": "helm",
                    "check": "Helm installed",
                    "command": "helm version",
                    "expected": 'version.BuildInfo{Version:"v3.x.x"...}',
                },
                {
                    "category": "helm",
                    "check": "Helm repos accessible",
                    "command": "helm repo list",
                    "expected": "No error",
                },
                {
                    "category": "helm",
                    "check": "Can template charts",
                    "command": "helm template test ./chart",
                    "expected": "Rendered YAML output",
                },
            ]
        )

    if parsed.check_ingress:
        checklist.extend(
            [
                {
                    "category": "ingress",
                    "check": "Ingress addon enabled",
                    "command": "minikube addons list | grep ingress",
                    "expected": "ingress: enabled",
                },
                {
                    "category": "ingress",
                    "check": "Ingress controller running",
                    "command": "kubectl get pods -n ingress-nginx",
                    "expected": "STATUS: Running",
                },
                {
                    "category": "ingress",
                    "check": "Ingress class available",
                    "command": "kubectl get ingressclass",
                    "expected": "nginx class listed",
                },
            ]
        )

    if parsed.check_storage:
        checklist.extend(
            [
                {
                    "category": "storage",
                    "check": "Default StorageClass",
                    "command": "kubectl get sc",
                    "expected": "standard (default) with provisioner",
                },
                {
                    "category": "storage",
                    "check": "PVC can bind",
                    "command": "kubectl get pvc",
                    "expected": "STATUS: Bound (if PVCs exist)",
                },
            ]
        )

    if parsed.check_metrics:
        checklist.extend(
            [
                {
                    "category": "metrics",
                    "check": "Metrics server running",
                    "command": "kubectl get pods -n kube-system -l k8s-app=metrics-server",
                    "expected": "STATUS: Running",
                },
                {
                    "category": "metrics",
                    "check": "Metrics available",
                    "command": "kubectl top nodes",
                    "expected": "CPU/memory values shown",
                },
            ]
        )

    return json.dumps(
        {
            "status": "success",
            "checklist": checklist,
            "total_checks": len(checklist),
            "notes": [
                "Run each command and verify against expected output",
                "All commands are read-only and safe to execute",
            ],
        },
        indent=2,
    )


@mcp.tool()
async def minikube_diagnose_startup(
    issue_type: str,
) -> str:
    """Diagnose minikube cluster startup issues.

    Returns JSON: {title, symptoms, diagnostic_commands, causes_and_solutions}
    Issue types: wont_start, guest_provision, api_server_down, stuck_starting
    """
    parsed = StartupDiagnoseInput(issue_type=issue_type)
    issue = STARTUP_ISSUES[parsed.issue_type]

    return json.dumps(
        {
            "status": "success",
            "title": issue["title"],
            "symptoms": issue["symptoms"],
            "diagnostic_commands": issue["diagnostics"],
            "causes_and_solutions": issue["causes"],
            "recovery_fallback": "minikube delete --purge && minikube start --driver=docker",
            "notes": [
                "Diagnostic commands are read-only and safe",
                "Recovery fallback will destroy existing cluster data",
            ],
        },
        indent=2,
    )


@mcp.tool()
async def minikube_diagnose_networking(
    issue_type: str,
) -> str:
    """Diagnose minikube networking and service access issues.

    Returns JSON: {title, symptoms, diagnostic_commands, solutions}
    Issue types: service_unreachable, ingress_broken, dns_failure, loadbalancer_pending
    """
    parsed = NetworkDiagnoseInput(issue_type=issue_type)
    issue = NETWORKING_ISSUES[parsed.issue_type]

    result: dict = {
        "status": "success",
        "title": issue["title"],
        "symptoms": issue["symptoms"],
        "diagnostic_commands": issue["diagnostics"],
    }

    if "solutions_by_type" in issue:
        result["solutions_by_service_type"] = issue["solutions_by_type"]
    if "causes" in issue:
        result["causes_and_solutions"] = issue["causes"]

    result["notes"] = [
        "Diagnostic commands are read-only and safe",
        "For LoadBalancer services, 'minikube tunnel' must run continuously",
    ]

    return json.dumps(result, indent=2)


@mcp.tool()
async def minikube_diagnose_storage(
    issue_type: str,
) -> str:
    """Diagnose minikube storage and PVC issues.

    Returns JSON: {title, symptoms, diagnostic_commands, causes_and_solutions}
    Issue types: pvc_pending, permission_denied
    """
    parsed = StorageDiagnoseInput(issue_type=issue_type)
    issue = STORAGE_ISSUES[parsed.issue_type]

    return json.dumps(
        {
            "status": "success",
            "title": issue["title"],
            "symptoms": issue["symptoms"],
            "diagnostic_commands": issue["diagnostics"],
            "causes_and_solutions": issue["causes"],
            "notes": [
                "Minikube uses hostPath provisioner by default",
                "Enable storage-provisioner and default-storageclass addons for PVC support",
            ],
        },
        indent=2,
    )


@mcp.tool()
async def minikube_suggest_lifecycle(
    action: str,
    profile: str | None = None,
) -> str:
    """Suggest minikube lifecycle commands for cluster management.

    Returns JSON: {command, description, notes}
    Actions: start, stop, pause, unpause, delete, status, ssh, tunnel
    """
    parsed = LifecycleInput(action=action, profile=profile)
    p_flag = f" -p {parsed.profile}" if parsed.profile else ""

    commands: dict[str, dict] = {
        "start": {
            "command": f"minikube start{p_flag}",
            "description": "Start or resume the cluster (preserves existing data)",
            "notes": [
                "Add --driver=docker if first start",
                "Existing workloads will be restored",
            ],
        },
        "stop": {
            "command": f"minikube stop{p_flag}",
            "description": "Stop the cluster, preserving all data on disk",
            "notes": [
                "No resource consumption while stopped",
                "Use at end of work day",
            ],
        },
        "pause": {
            "command": f"minikube pause{p_flag}",
            "description": "Freeze cluster with minimal resource usage",
            "notes": ["Faster resume than stop/start", "Good for short breaks"],
        },
        "unpause": {
            "command": f"minikube unpause{p_flag}",
            "description": "Resume a paused cluster",
            "notes": ["Near-instant resume"],
        },
        "delete": {
            "command": f"minikube delete{p_flag}",
            "description": "Delete the cluster and all data",
            "notes": [
                "WARNING: This is destructive — all cluster data will be lost",
                "Add --purge to remove cache too",
            ],
        },
        "status": {
            "command": f"minikube status{p_flag}",
            "description": "Show cluster component status",
            "notes": ["Check host, kubelet, apiserver, kubeconfig status"],
        },
        "ssh": {
            "command": f"minikube ssh{p_flag}",
            "description": "SSH into the minikube node",
            "notes": [
                "For advanced debugging only",
                "Use: minikube ssh -- 'command' for one-off commands",
            ],
        },
        "tunnel": {
            "command": f"minikube tunnel{p_flag}",
            "description": "Create a network tunnel for LoadBalancer services",
            "notes": [
                "Must run continuously in a separate terminal",
                "May require sudo/admin",
            ],
        },
    }

    cmd = commands[parsed.action]
    return json.dumps(
        {
            "status": "success",
            "action": parsed.action,
            "command": cmd["command"],
            "description": cmd["description"],
            "notes": ["SUGGESTION ONLY — not executed"] + cmd["notes"],
        }
    )


@mcp.tool()
async def minikube_recommend_resources(
    workload_type: str,
    estimated_pods: int = 5,
    needs_persistence: bool = False,
    needs_ingress: bool = False,
) -> str:
    """Recommend minikube resource allocation based on workload requirements.

    Returns JSON: {recommendation, start_command, addons}
    Calculates CPU, memory, disk, and addon requirements.
    """
    parsed = ResourceRecommendInput(
        workload_type=workload_type,
        estimated_pods=estimated_pods,
        needs_persistence=needs_persistence,
        needs_ingress=needs_ingress,
    )

    # Base resources for system pods (~500MB, 0.5 CPU)
    base_mem_mb = 512
    base_cpu = 0.5

    # Per-pod estimate (~128MB, 0.1 CPU average)
    pod_mem = parsed.estimated_pods * 128
    pod_cpu = parsed.estimated_pods * 0.1

    # Addon overhead
    addon_mem = 0
    addon_cpu = 0
    addons = []

    if parsed.needs_ingress:
        addon_mem += 256
        addon_cpu += 0.2
        addons.extend(["ingress"])

    if parsed.needs_persistence:
        addon_mem += 64
        addons.extend(["storage-provisioner", "default-storageclass"])

    # Always recommend metrics-server
    addon_mem += 128
    addon_cpu += 0.1
    addons.append("metrics-server")

    total_mem = int(base_mem_mb + pod_mem + addon_mem)
    total_cpu = base_cpu + pod_cpu + addon_cpu

    # Round up to practical values
    rec_mem = max(2048, ((total_mem + 511) // 512) * 512)  # Round up to 512MB
    rec_cpu = max(2, int(total_cpu + 0.9))  # Round up to integer

    # Disk based on workload
    rec_disk = "10g"
    if parsed.estimated_pods > 10 or parsed.needs_persistence:
        rec_disk = "20g"
    if parsed.estimated_pods > 20:
        rec_disk = "40g"

    # Determine profile
    if rec_cpu <= 2 and rec_mem <= 2048:
        profile = "minimal"
    elif rec_cpu <= 4 and rec_mem <= 4096:
        profile = "standard"
    else:
        profile = "heavy"

    # Build start command
    parts = [
        "minikube start",
        "    --driver=docker",
        f"    --cpus={rec_cpu}",
        f"    --memory={rec_mem}",
        f"    --disk-size={rec_disk}",
    ]
    if addons:
        parts.append(f"    --addons={','.join(addons)}")

    command = " \\\n".join(parts)

    return json.dumps(
        {
            "status": "success",
            "recommendation": {
                "profile": profile,
                "cpus": rec_cpu,
                "memory_mb": rec_mem,
                "disk_size": rec_disk,
                "addons": addons,
            },
            "calculation": {
                "system_overhead_mb": base_mem_mb,
                "pod_estimate_mb": pod_mem,
                "addon_overhead_mb": addon_mem,
                "total_estimated_mb": total_mem,
                "rounded_up_mb": rec_mem,
            },
            "start_command": command,
            "notes": [
                "SUGGESTION ONLY — not executed",
                f"Workload: {parsed.workload_type} with ~{parsed.estimated_pods} pods",
                f"Recommended profile: {profile}",
                "Ensure host machine has sufficient resources available",
            ],
        },
        indent=2,
    )


@mcp.tool()
async def minikube_generate_ci_config(
    ci_platform: str,
    kubernetes_version: str = "v1.29.0",
    chart_path: str | None = None,
) -> str:
    """Generate CI/CD configuration for minikube-based testing.

    Returns JSON: {platform, config_content, filename, notes}
    Platforms: github-actions, gitlab-ci, jenkins
    """
    parsed = CIConfigInput(
        ci_platform=ci_platform,
        kubernetes_version=kubernetes_version,
        chart_path=chart_path,
    )

    chart = parsed.chart_path or "./chart"

    configs: dict[str, dict] = {
        "github-actions": {
            "filename": ".github/workflows/helm-test.yml",
            "content": f"""\
name: Helm Chart Test
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Start Minikube
        uses: medyagh/setup-minikube@latest
        with:
          kubernetes-version: {parsed.kubernetes_version}
          driver: docker
          cpus: 2
          memory: 4096

      - name: Install Helm
        uses: azure/setup-helm@v3
        with:
          version: latest

      - name: Lint Chart
        run: helm lint {chart}

      - name: Template Chart
        run: helm template test {chart}

      - name: Install Chart
        run: |
          helm install test {chart} --wait --timeout=120s
          kubectl get all

      - name: Verify Pods Ready
        run: |
          kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=test --timeout=120s

      - name: Cleanup
        if: always()
        run: helm uninstall test || true
""",
        },
        "gitlab-ci": {
            "filename": ".gitlab-ci.yml",
            "content": f"""\
stages:
  - test

helm-test:
  stage: test
  image: docker:latest
  services:
    - docker:dind
  variables:
    DOCKER_TLS_CERTDIR: ""
  before_script:
    - apk add --no-cache curl bash
    - curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
    - install minikube-linux-amd64 /usr/local/bin/minikube
    - curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    - install kubectl /usr/local/bin/kubectl
    - curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
    - minikube start --driver=docker --kubernetes-version={parsed.kubernetes_version} --cpus=2 --memory=2048
  script:
    - helm lint {chart}
    - helm template test {chart}
    - helm install test {chart} --wait --timeout=120s
    - kubectl get all
    - kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=test --timeout=120s
  after_script:
    - helm uninstall test || true
    - minikube delete || true
""",
        },
        "jenkins": {
            "filename": "Jenkinsfile",
            "content": f"""\
pipeline {{
    agent any
    environment {{
        KUBECONFIG = "${{WORKSPACE}}/.kube/config"
    }}
    stages {{
        stage('Setup Minikube') {{
            steps {{
                sh '''
                    minikube start \\
                        --driver=docker \\
                        --kubernetes-version={parsed.kubernetes_version} \\
                        --cpus=2 \\
                        --memory=2048
                    kubectl cluster-info
                '''
            }}
        }}
        stage('Lint Chart') {{
            steps {{
                sh 'helm lint {chart}'
            }}
        }}
        stage('Install Chart') {{
            steps {{
                sh '''
                    helm install test {chart} --wait --timeout=120s
                    kubectl get all
                    kubectl wait --for=condition=ready pod \\
                        -l app.kubernetes.io/instance=test \\
                        --timeout=120s
                '''
            }}
        }}
    }}
    post {{
        always {{
            sh 'helm uninstall test || true'
            sh 'minikube delete || true'
        }}
    }}
}}
""",
        },
    }

    config = configs[parsed.ci_platform]

    return json.dumps(
        {
            "status": "success",
            "platform": parsed.ci_platform,
            "filename": config["filename"],
            "content": config["content"],
            "notes": [
                f"CI platform: {parsed.ci_platform}",
                f"Kubernetes version: {parsed.kubernetes_version}",
                f"Chart path: {chart}",
                "Review and adjust resource limits for your CI runner",
            ],
        },
        indent=2,
    )


@mcp.tool()
async def minikube_list_error_solutions(
    error_message: str | None = None,
) -> str:
    """Look up error messages and their solutions.

    Returns JSON: {matches} or {all_errors}
    Pass an error message to search, or omit to list all known errors.
    """
    parsed = ErrorLookupInput(error_message=error_message)

    if parsed.error_message:
        query = parsed.error_message.lower()
        matches = []
        for error_key, info in ERROR_LOOKUP.items():
            if query in error_key.lower() or error_key.lower() in query:
                matches.append(
                    {
                        "error": error_key,
                        "cause": info["cause"],
                        "fix": info["fix"],
                    }
                )

        if not matches:
            return json.dumps(
                {
                    "status": "success",
                    "matches": [],
                    "note": f"No exact match for '{parsed.error_message}'. Listing all known errors.",
                    "all_errors": [
                        {"error": k, "cause": v["cause"], "fix": v["fix"]}
                        for k, v in ERROR_LOOKUP.items()
                    ],
                }
            )

        return json.dumps(
            {
                "status": "success",
                "query": parsed.error_message,
                "matches": matches,
            }
        )

    return json.dumps(
        {
            "status": "success",
            "all_errors": [
                {"error": k, "cause": v["cause"], "fix": v["fix"]}
                for k, v in ERROR_LOOKUP.items()
            ],
            "total": len(ERROR_LOOKUP),
        }
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
