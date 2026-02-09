"""
Anomaly Detector — detect unusual MCP usage patterns (spec 004 Platinum US11).

Monitors MCP action patterns and alerts on suspicious activity:
- Volume spikes (unusual number of calls)
- Timing anomalies (calls at unusual times)
- Sequence anomalies (unexpected action chains)

Uses statistical baseline (7-day rolling window, 2 std deviation threshold)
to distinguish normal variance from genuine anomalies.
"""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.security.models import RiskLevel


@dataclass
class AnomalyAlert:
    """An anomaly alert with context."""

    alert_id: str
    timestamp: datetime
    anomaly_type: str  # volume | timing | sequence
    severity: RiskLevel
    mcp_server: str
    description: str
    baseline_value: float
    observed_value: float
    details: dict = field(default_factory=dict)


@dataclass
class BaselineStats:
    """Statistical baseline for a metric."""

    mean: float
    std_dev: float
    sample_count: int
    window_start: datetime
    window_end: datetime


class AnomalyDetector:
    """
    Detect unusual MCP usage patterns using statistical baseline.

    Args:
        audit_log_path: Path to security audit log (JSON lines)
        alert_log_path: Path to write anomaly alerts
        baseline_window_days: Days of history for baseline (default: 7)
        std_dev_threshold: Standard deviations for anomaly (default: 2.0)
    """

    def __init__(
        self,
        audit_log_path: Path,
        alert_log_path: Path,
        baseline_window_days: int = 7,
        std_dev_threshold: float = 2.0,
    ):
        self._audit_log = audit_log_path
        self._alert_log = alert_log_path
        self._baseline_days = baseline_window_days
        self._std_threshold = std_dev_threshold
        self._alert_log.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public detection methods
    # ------------------------------------------------------------------

    def detect_unusual_volume(
        self,
        mcp_server: str,
        time_window_hours: int = 1,
    ) -> Optional[AnomalyAlert]:
        """
        Detect volume spikes (unusual number of calls in time window).

        Args:
            mcp_server: MCP server to check
            time_window_hours: Time window for volume check

        Returns:
            AnomalyAlert if spike detected, None otherwise
        """
        events = self._load_events()
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=time_window_hours)

        # Count calls in current window
        current_calls = [
            e
            for e in events
            if e.get("mcp_server") == mcp_server
            and e.get("event_type") == "mcp_action"
            and self._parse_timestamp(e["timestamp"]) >= window_start
        ]
        current_count = len(current_calls)

        # Calculate baseline from historical windows
        baseline = self._calculate_volume_baseline(
            events, mcp_server, time_window_hours
        )

        if baseline is None:
            return None  # Not enough data

        # Check if current volume exceeds threshold
        threshold = baseline.mean + (self._std_threshold * baseline.std_dev)
        if current_count > threshold:
            return self._create_alert(
                anomaly_type="volume",
                severity=RiskLevel.HIGH,
                mcp_server=mcp_server,
                description=f"Volume spike detected: {current_count} calls in {time_window_hours}h",
                baseline_value=baseline.mean,
                observed_value=float(current_count),
                details={
                    "time_window_hours": time_window_hours,
                    "threshold": threshold,
                    "std_dev": baseline.std_dev,
                },
            )

        return None

    def detect_unusual_timing(
        self,
        mcp_server: str,
    ) -> Optional[AnomalyAlert]:
        """
        Detect timing anomalies (calls at unusual times of day).

        Args:
            mcp_server: MCP server to check

        Returns:
            AnomalyAlert if timing anomaly detected, None otherwise
        """
        events = self._load_events()
        now = datetime.now(timezone.utc)
        recent_window = now - timedelta(hours=1)

        # Get recent calls for this server
        recent_calls = [
            e
            for e in events
            if e.get("mcp_server") == mcp_server
            and e.get("event_type") == "mcp_action"
            and self._parse_timestamp(e["timestamp"]) >= recent_window
        ]

        if not recent_calls:
            return None

        # Calculate baseline hour-of-day distribution
        baseline = self._calculate_timing_baseline(events, mcp_server)

        if baseline is None:
            return None

        # Check if current hour is anomalous
        current_hour = now.hour
        hour_baseline = baseline.get(current_hour, {})
        avg_calls = hour_baseline.get("mean", 0)
        std_dev = hour_baseline.get("std_dev", 0)

        recent_count = len(recent_calls)
        if std_dev > 0:
            threshold = avg_calls + (self._std_threshold * std_dev)
            if recent_count > threshold and avg_calls < 1.0:
                return self._create_alert(
                    anomaly_type="timing",
                    severity=RiskLevel.MEDIUM,
                    mcp_server=mcp_server,
                    description=f"Unusual timing: {recent_count} calls at hour {current_hour} (typically {avg_calls:.1f})",
                    baseline_value=avg_calls,
                    observed_value=float(recent_count),
                    details={
                        "hour_of_day": current_hour,
                        "threshold": threshold,
                    },
                )

        return None

    def detect_unusual_sequence(
        self,
        mcp_server: str,
        lookback_minutes: int = 30,
    ) -> Optional[AnomalyAlert]:
        """
        Detect sequence anomalies (unexpected action chains).

        Args:
            mcp_server: MCP server to check
            lookback_minutes: Minutes to look back for sequence

        Returns:
            AnomalyAlert if sequence anomaly detected, None otherwise
        """
        events = self._load_events()
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=lookback_minutes)

        # Get recent action sequence for this server
        recent_actions = [
            e.get("action")
            for e in events
            if e.get("mcp_server") == mcp_server
            and e.get("event_type") == "mcp_action"
            and self._parse_timestamp(e["timestamp"]) >= window_start
            and e.get("action") is not None
        ]

        if len(recent_actions) < 2:
            return None

        # Build action sequence
        sequence = " → ".join(recent_actions[-5:])  # Last 5 actions

        # Calculate baseline sequences
        baseline_sequences = self._calculate_sequence_baseline(events, mcp_server)

        # Check if this sequence is rare
        sequence_count = baseline_sequences.get(sequence, 0)
        if sequence_count == 0 and len(recent_actions) >= 3:
            # Never-before-seen sequence with 3+ actions
            return self._create_alert(
                anomaly_type="sequence",
                severity=RiskLevel.MEDIUM,
                mcp_server=mcp_server,
                description=f"Unusual action sequence: {sequence}",
                baseline_value=0.0,
                observed_value=1.0,
                details={
                    "sequence": sequence,
                    "action_count": len(recent_actions),
                },
            )

        return None

    def scan_all_servers(self) -> list[AnomalyAlert]:
        """
        Scan all MCP servers for anomalies.

        Returns:
            List of detected anomalies
        """
        alerts = []
        events = self._load_events()

        # Get unique servers from recent events
        servers = set(
            e.get("mcp_server")
            for e in events
            if e.get("event_type") == "mcp_action" and e.get("mcp_server")
        )

        for server in servers:
            # Check all anomaly types
            if alert := self.detect_unusual_volume(server):
                alerts.append(alert)

            if alert := self.detect_unusual_timing(server):
                alerts.append(alert)

            if alert := self.detect_unusual_sequence(server):
                alerts.append(alert)

        return alerts

    def get_recent_alerts(self, limit: int = 20) -> list[dict]:
        """
        Get recent anomaly alerts.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of alert dictionaries
        """
        if not self._alert_log.exists():
            return []

        lines = self._alert_log.read_text().strip().split("\n")
        alerts = [json.loads(line) for line in lines[-limit:] if line]
        return alerts

    # ------------------------------------------------------------------
    # Internal helper methods
    # ------------------------------------------------------------------

    def _load_events(self) -> list[dict]:
        """Load all events from audit log."""
        if not self._audit_log.exists():
            return []

        lines = self._audit_log.read_text().strip().split("\n")
        return [json.loads(line) for line in lines if line]

    def _parse_timestamp(self, ts_str: str) -> datetime:
        """Parse ISO timestamp string."""
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

    def _calculate_volume_baseline(
        self,
        events: list[dict],
        mcp_server: str,
        time_window_hours: int,
    ) -> Optional[BaselineStats]:
        """Calculate baseline volume statistics."""
        now = datetime.now(timezone.utc)
        baseline_start = now - timedelta(days=self._baseline_days)

        # Count calls per time window over baseline period
        window_counts = []
        current = baseline_start

        while current < now - timedelta(hours=time_window_hours):
            window_end = current + timedelta(hours=time_window_hours)
            count = len(
                [
                    e
                    for e in events
                    if e.get("mcp_server") == mcp_server
                    and e.get("event_type") == "mcp_action"
                    and baseline_start
                    <= self._parse_timestamp(e["timestamp"])
                    < window_end
                ]
            )
            window_counts.append(count)
            current = window_end

        if len(window_counts) < 3:
            return None  # Not enough data

        mean = sum(window_counts) / len(window_counts)
        variance = sum((x - mean) ** 2 for x in window_counts) / len(window_counts)
        std_dev = variance**0.5

        return BaselineStats(
            mean=mean,
            std_dev=std_dev,
            sample_count=len(window_counts),
            window_start=baseline_start,
            window_end=now,
        )

    def _calculate_timing_baseline(
        self,
        events: list[dict],
        mcp_server: str,
    ) -> Optional[dict[int, dict]]:
        """Calculate hour-of-day baseline distribution."""
        now = datetime.now(timezone.utc)
        baseline_start = now - timedelta(days=self._baseline_days)

        # Group calls by hour of day
        hour_counts = defaultdict(list)

        for event in events:
            if (
                event.get("mcp_server") == mcp_server
                and event.get("event_type") == "mcp_action"
            ):
                ts = self._parse_timestamp(event["timestamp"])
                if baseline_start <= ts < now:
                    hour_counts[ts.hour].append(ts.date())

        # Calculate stats per hour
        hour_stats = {}
        for hour, dates in hour_counts.items():
            date_counts = defaultdict(int)
            for date in dates:
                date_counts[date] += 1

            counts = list(date_counts.values())
            if counts:
                mean = sum(counts) / len(counts)
                variance = sum((x - mean) ** 2 for x in counts) / len(counts)
                hour_stats[hour] = {
                    "mean": mean,
                    "std_dev": variance**0.5,
                }

        return hour_stats if hour_stats else None

    def _calculate_sequence_baseline(
        self,
        events: list[dict],
        mcp_server: str,
    ) -> dict[str, int]:
        """Calculate baseline action sequence frequencies."""
        now = datetime.now(timezone.utc)
        baseline_start = now - timedelta(days=self._baseline_days)

        # Extract action sequences (5-action windows)
        actions = [
            e.get("action")
            for e in events
            if e.get("mcp_server") == mcp_server
            and e.get("event_type") == "mcp_action"
            and baseline_start <= self._parse_timestamp(e["timestamp"]) < now
            and e.get("action") is not None
        ]

        # Count 5-action sequences
        sequence_counts = defaultdict(int)
        for i in range(len(actions) - 4):
            sequence = " → ".join(actions[i : i + 5])
            sequence_counts[sequence] += 1

        return dict(sequence_counts)

    def _create_alert(
        self,
        anomaly_type: str,
        severity: RiskLevel,
        mcp_server: str,
        description: str,
        baseline_value: float,
        observed_value: float,
        details: dict,
    ) -> AnomalyAlert:
        """Create and log an anomaly alert."""
        alert = AnomalyAlert(
            alert_id=self._generate_alert_id(),
            timestamp=datetime.now(timezone.utc),
            anomaly_type=anomaly_type,
            severity=severity,
            mcp_server=mcp_server,
            description=description,
            baseline_value=baseline_value,
            observed_value=observed_value,
            details=details,
        )

        # Append to alert log
        record = {
            "alert_id": alert.alert_id,
            "timestamp": alert.timestamp.isoformat(),
            "anomaly_type": alert.anomaly_type,
            "severity": alert.severity.value,
            "mcp_server": alert.mcp_server,
            "description": alert.description,
            "baseline_value": alert.baseline_value,
            "observed_value": alert.observed_value,
            "details": alert.details,
        }

        with open(self._alert_log, "a") as fh:
            fh.write(json.dumps(record) + "\n")

        return alert

    def _generate_alert_id(self) -> str:
        """Generate unique alert ID."""
        import uuid

        return f"alert-{uuid.uuid4().hex[:12]}"
