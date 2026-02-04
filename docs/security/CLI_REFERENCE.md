# Security CLI Reference – `fte security`

All sub-commands are grouped under `fte security`.  Run `fte security --help` for a live list.

---

## Dashboard & Monitoring

### `fte security dashboard`

Real-time security posture overview.

```
Options:
  --watch              Live-refresh every 5 seconds (Ctrl-C to stop)
  --json               Output as JSON
```

Shows: credential count, verified MCP servers, rate-limit buckets, open circuits, recent alerts, isolated servers.

### `fte security health`

Single-line health status.

```
Options:
  --json               Output as JSON
  --verbose, -v        Detailed check results
```

Exit codes: 0 = HEALTHY, 1 = DEGRADED, 2 = UNHEALTHY.

### `fte security metrics`

Security event metrics over a time window.

```
Options:
  --since <window>     Time window: 1h, 24h, 7d (default: 24h)
  --json               Output as JSON
```

Shows: credential access count, verification failures, rate-limit hits, circuit trips, error rate, per-server breakdowns.

---

## Alerts & Scanning

### `fte security alerts`

View recent anomaly alerts.

```
Options:
  -n, --limit <N>      Number of alerts to show (default: 20)
  --json               Output as JSON
```

### `fte security scan`

Real-time anomaly scan.

```
Options:
  -s, --server <name>  Scan a specific server (default: all)
```

---

## Incident Response

### `fte security incident-report`

Generate investigation report from audit logs.

```
Options:
  --since <window>     Time window to analyse (default: 1h)
  --json               Output as JSON
```

### `fte security isolate <mcp>`

Emergency: quarantine an MCP server.

```
Options:
  -r, --reason <text>  Reason for isolation (required)
  -y, --confirm        Skip confirmation prompt
```

### `fte security restore <mcp>`

Re-enable a previously isolated server.

```
Options:
  -y, --confirm        Skip confirmation prompt
```

### `fte security isolated`

List all currently quarantined MCP servers.

### `fte security rotate-all`

Emergency mass credential rotation.

```
Options:
  -r, --reason <text>  Reason for rotation (required)
  -y, --confirm        Skip confirmation (CRITICAL action)
```

---

## Circuit Breakers

### `fte security circuit-status`

Current state of all circuit breakers.

```
Options:
  -s, --server <name>  Check a specific server
```

### `fte security reset-circuit <mcp>`

Manually close an open circuit breaker.

```
Options:
  -y, --confirm        Skip confirmation prompt
```

---

## Time-Window Syntax

Used by `--since` flags:

| Input | Meaning |
|-------|---------|
| `30m` | 30 minutes |
| `1h`  | 1 hour |
| `24h` | 24 hours |
| `7d`  | 7 days |

---

## Global Options

These apply to every `fte` command:

| Flag | Effect |
|------|--------|
| `--verbose, -v` | DEBUG-level logging |
| `--quiet, -q`   | ERROR-level only |
| `--no-color`    | Disable rich colours (CI-friendly) |
| `--version`     | Print version and exit |

---

**Version**: 1.0 | **Updated**: 2026-02-04
