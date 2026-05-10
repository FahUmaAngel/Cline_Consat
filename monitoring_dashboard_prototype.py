"""
Monitoring Dashboard Prototype
===============================
Monitoring system for tracking routing, masking, and policy enforcement

Author: CONSAT PoC Team
Date: May 4, 2026
"""

import json
import time
from enum import Enum
from typing import Dict, List
from dataclasses import dataclass, asdict, field
from datetime import datetime
from collections import defaultdict


class MetricType(Enum):
    """Metric type"""
    REQUEST_COUNT = "request_count"
    LOCAL_ROUTING_COUNT = "local_routing_count"
    CLOUD_ROUTING_COUNT = "cloud_routing_count"
    MASKING_ITEMS = "masking_items"
    POLICY_VIOLATIONS = "policy_violations"
    PROCESSING_TIME = "processing_time"
    ERROR_COUNT = "error_count"


@dataclass
class Metric:
    """Metric record"""
    timestamp: str
    metric_type: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """Alert record"""
    timestamp: str
    severity: str  # info, warning, critical
    message: str
    metric_type: str
    value: float
    threshold: float


class MetricsCollector:
    """Collects metrics from various systems"""

    def __init__(self):
        self.metrics: List[Metric] = []
        self.alerts: List[Alert] = []

        # Thresholds for alert creation
        self.alert_thresholds = {
            'processing_time_ms': 5000,  # alert if > 5 seconds
            'error_rate_percent': 5,      # alert if error rate > 5%
            'policy_violation_rate': 10,  # alert if violation rate > 10%
        }

    def record_metric(self, metric_type: MetricType, value: float, tags: Dict = None):
        """Record a metric"""
        metric = Metric(
            timestamp=datetime.now().isoformat(),
            metric_type=metric_type.value,
            value=value,
            tags=tags or {},
        )
        self.metrics.append(metric)

        # Check thresholds
        self._check_thresholds(metric_type, value)

    def _check_thresholds(self, metric_type: MetricType, value: float):
        """Check whether an alert should be created"""
        if metric_type == MetricType.PROCESSING_TIME:
            if value > self.alert_thresholds['processing_time_ms']:
                self._create_alert(
                    severity='warning',
                    message=f'Processing time {value}ms exceeds threshold',
                    metric_type=metric_type.value,
                    value=value,
                    threshold=self.alert_thresholds['processing_time_ms'],
                )
        elif metric_type == MetricType.POLICY_VIOLATIONS:
            if value > 0:
                self._create_alert(
                    severity='critical',
                    message=f'Policy violation detected: {int(value)} critical violation(s)',
                    metric_type=metric_type.value,
                    value=value,
                    threshold=0,
                )

    def _create_alert(self, severity: str, message: str, metric_type: str,
                      value: float, threshold: float):
        """Create an alert"""
        alert = Alert(
            timestamp=datetime.now().isoformat(),
            severity=severity,
            message=message,
            metric_type=metric_type,
            value=value,
            threshold=threshold,
        )
        self.alerts.append(alert)

    def get_all_metrics(self) -> List[Dict]:
        """Retrieve all metrics"""
        return [asdict(m) for m in self.metrics]

    def get_all_alerts(self) -> List[Dict]:
        """Retrieve all alerts"""
        return [asdict(a) for a in self.alerts]


class DashboardCalculator:
    """Calculates statistics for the dashboard"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector

    def calculate_stats(self) -> Dict:
        """Calculate various statistics"""
        metrics = self.metrics_collector.metrics

        if not metrics:
            return self._empty_stats()

        # Count by metric type
        metric_counts = defaultdict(int)
        metric_values = defaultdict(list)

        for metric in metrics:
            metric_counts[metric.metric_type] += 1
            metric_values[metric.metric_type].append(metric.value)

        # Calculate percentages
        total_requests = metric_counts.get('request_count', 0)
        local_routing = metric_counts.get('local_routing_count', 0)
        cloud_routing = metric_counts.get('cloud_routing_count', 0)

        local_percent = (local_routing / total_requests * 100) if total_requests > 0 else 0
        cloud_percent = (cloud_routing / total_requests * 100) if total_requests > 0 else 0

        # Calculate averages
        avg_processing_time = 0
        if metric_values.get('processing_time'):
            avg_processing_time = sum(metric_values['processing_time']) / len(metric_values['processing_time'])

        total_masking_items = sum(metric_values.get('masking_items', []))
        total_policy_violations = sum(metric_values.get('policy_violations', []))

        total_violations_all = sum(metric_values.get('policy_violations', []))
        quality_rate = ((total_requests - total_violations_all) / total_requests * 100) if total_requests > 0 else 100.0

        return {
            'timestamp': datetime.now().isoformat(),
            'total_requests': total_requests,
            'local_routing_count': local_routing,
            'cloud_routing_count': cloud_routing,
            'local_routing_percent': f"{local_percent:.1f}%",
            'cloud_routing_percent': f"{cloud_percent:.1f}%",
            'avg_processing_time_ms': f"{avg_processing_time:.2f}",
            'total_masking_items': total_masking_items,
            'total_policy_violations': total_policy_violations,
            'total_alerts': len(self.metrics_collector.alerts),
            'critical_alerts': len([a for a in self.metrics_collector.alerts if a.severity == 'critical']),
            # ISO14001: on-premise ratio reduces cloud compute / carbon footprint
            'on_premise_ratio': f"{local_percent:.1f}%",
            'cloud_offload_ratio': f"{cloud_percent:.1f}%",
            # ISO9001: output quality rate (requests without critical policy violations)
            'quality_pass_rate': f"{quality_rate:.1f}%",
        }

    def _empty_stats(self) -> Dict:
        return {
            'timestamp': datetime.now().isoformat(),
            'total_requests': 0,
            'local_routing_count': 0,
            'cloud_routing_count': 0,
            'local_routing_percent': '0%',
            'cloud_routing_percent': '0%',
            'avg_processing_time_ms': '0',
            'total_masking_items': 0,
            'total_policy_violations': 0,
            'total_alerts': 0,
            'critical_alerts': 0,
            'on_premise_ratio': '0%',
            'cloud_offload_ratio': '0%',
            'quality_pass_rate': '100.0%',
        }


class MonitoringDashboard:
    """Main monitoring dashboard"""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.calculator = DashboardCalculator(self.metrics_collector)

    def record_request(self, routing_decision: str, processing_time: float,
                       masked_items: int = 0, policy_violations: int = 0,
                       sensitivity_level: str = '', force_overridden: bool = False):
        """Record request processing"""
        self.metrics_collector.record_metric(
            MetricType.REQUEST_COUNT, 1
        )

        if routing_decision == 'local':
            self.metrics_collector.record_metric(
                MetricType.LOCAL_ROUTING_COUNT, 1,
                tags={'route': 'local'}
            )
        elif routing_decision == 'cloud':
            self.metrics_collector.record_metric(
                MetricType.CLOUD_ROUTING_COUNT, 1,
                tags={'route': 'cloud'}
            )

        if masked_items > 0:
            self.metrics_collector.record_metric(
                MetricType.MASKING_ITEMS, masked_items
            )

        if policy_violations > 0:
            self.metrics_collector.record_metric(
                MetricType.POLICY_VIOLATIONS, policy_violations
            )

        if routing_decision == 'local' and sensitivity_level == 'high' and not force_overridden:
            self.metrics_collector._create_alert(
                severity='critical',
                message='HIGH sensitivity data blocked — routed to Local LLM only',
                metric_type='sensitivity_block',
                value=1,
                threshold=0,
            )

        self.metrics_collector.record_metric(
            MetricType.PROCESSING_TIME, processing_time
        )

    def display_dashboard(self):
        """Display dashboard in text format"""
        stats = self.calculator.calculate_stats()

        print("\n" + "=" * 80)
        print("📊 MONITORING DASHBOARD")
        print("=" * 80)
        print(f"Timestamp: {stats['timestamp']}")
        print("-" * 80)

        print("\n📈 REQUEST STATISTICS")
        print(f"  Total Requests: {stats['total_requests']}")
        print(f"  Local Routing: {stats['local_routing_count']} ({stats['local_routing_percent']})")
        print(f"  Cloud Routing: {stats['cloud_routing_count']} ({stats['cloud_routing_percent']})")

        print("\n⚙️ PROCESSING")
        print(f"  Avg Processing Time: {stats['avg_processing_time_ms']} ms")
        print(f"  Total Masked Items: {stats['total_masking_items']}")

        print("\n🔐 SECURITY & COMPLIANCE (ISO27001)")
        print(f"  Total Policy Violations: {stats['total_policy_violations']}")
        print(f"  Total Alerts: {stats['total_alerts']}")
        print(f"  Critical Alerts: {stats['critical_alerts']}")

        print("\n🌱 ENVIRONMENTAL METRICS (ISO14001)")
        print(f"  On-Premise Processing: {stats['on_premise_ratio']}  ← less cloud = lower carbon")
        print(f"  Cloud Offload:         {stats['cloud_offload_ratio']}")

        print("\n✅ QUALITY METRICS (ISO9001)")
        print(f"  Output Quality Pass Rate: {stats['quality_pass_rate']}  ← requests without critical violations")

        # Display recent alerts
        if self.metrics_collector.alerts:
            print("\n⚠️ RECENT ALERTS")
            for alert in self.metrics_collector.alerts[-5:]:  # Show last 5
                severity_icon = "🔴" if alert.severity == "critical" else "🟡"
                print(f"  {severity_icon} [{alert.severity.upper()}] {alert.message}")

        print("\n" + "=" * 80 + "\n")

    def export_metrics_json(self, filepath: str):
        """Export metrics to a JSON file"""
        data = {
            'dashboard_stats': self.calculator.calculate_stats(),
            'all_metrics': self.metrics_collector.get_all_metrics(),
            'all_alerts': self.metrics_collector.get_all_alerts(),
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_health_status(self) -> Dict:
        """Get system health status"""
        stats = self.calculator.calculate_stats()

        # Determine health
        if stats['critical_alerts'] > 0:
            health = 'unhealthy'
        elif stats['total_alerts'] > 0:
            health = 'degraded'
        else:
            health = 'healthy'

        return {
            'health': health,
            'stats': stats,
        }


# ============== Test Cases ==============

if __name__ == "__main__":
    print("=" * 80)
    print("MONITORING DASHBOARD - PROTOTYPE TEST")
    print("=" * 80)

    dashboard = MonitoringDashboard()

    # Simulate some requests
    test_requests = [
        {'route': 'cloud', 'time': 500, 'masked': 2, 'violations': 0},
        {'route': 'cloud', 'time': 450, 'masked': 1, 'violations': 0},
        {'route': 'local', 'time': 2000, 'masked': 0, 'violations': 0},
        {'route': 'cloud', 'time': 600, 'masked': 3, 'violations': 1},
        {'route': 'cloud', 'time': 5500, 'masked': 2, 'violations': 0},  # Will trigger alert
        {'route': 'local', 'time': 1800, 'masked': 0, 'violations': 2},  # Will trigger alert
        {'route': 'cloud', 'time': 480, 'masked': 1, 'violations': 0},
    ]

    print("\nSimulating requests...")
    for i, req in enumerate(test_requests, 1):
        dashboard.record_request(
            routing_decision=req['route'],
            processing_time=req['time'],
            masked_items=req['masked'],
            policy_violations=req['violations'],
        )
        print(f"  Request {i}: {req['route'].upper()} | {req['time']}ms | Masked: {req['masked']} | Violations: {req['violations']}")

    # Display dashboard
    dashboard.display_dashboard()

    # Health status
    health = dashboard.get_health_status()
    print(f"System Health: {health['health'].upper()}")

    # Export metrics
    dashboard.export_metrics_json('monitoring_metrics.json')
    print("✅ Metrics exported to monitoring_metrics.json")
    print("\n✅ Monitoring dashboard prototype test complete!")
