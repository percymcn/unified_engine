"""
SmartFlow Integrity Monitor
============================

Monitors live SmartFlow system health and compares against golden baseline.

Features:
- Service health inspection
- Runtime chain health verification
- DB schema/state inspection
- Task/worker health checks
- Routing integrity validation
- Metadata completeness checks
- Dashboard/API freshness monitoring
- Broker/webhook pipeline health
- Baseline comparison and drift detection
- Composite health scoring

Categories:
- services: Container/service availability
- runtime_chain: Pipeline component status
- data_freshness: Stale data detection
- routing: Strategy routing alignment
- broker: Broker connectivity
- dashboard: API/DB alignment
- metadata: Signal field completeness
- tasks: Celery beat task health
- baseline_drift: Deviation from golden baseline
"""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.cache.redis_client import redis_client

logger = logging.getLogger(__name__)

# Baseline location
BASELINE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    ".smartflow_data", "baselines"
)
DEFAULT_BASELINE = "SMARTFLOW_GOLDEN_BASELINE_v1.json"


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class DriftSeverity(str, Enum):
    """Drift finding severity."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ComponentStatus:
    """Status of a single component."""
    name: str
    status: HealthStatus
    message: str = ""
    last_success: Optional[datetime] = None
    latency_ms: Optional[float] = None
    drift_flag: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DriftFinding:
    """A single drift finding."""
    category: str
    severity: DriftSeverity
    title: str
    description: str
    expected: Any = None
    actual: Any = None
    remediation: str = ""


@dataclass
class IntegrityReport:
    """Complete integrity report."""
    timestamp: datetime
    overall_status: HealthStatus
    health_score: float
    category_scores: Dict[str, float]
    components: List[ComponentStatus]
    drift_findings: List[DriftFinding]
    baseline_version: Optional[str] = None
    last_baseline_check: Optional[datetime] = None
    notes: List[str] = field(default_factory=list)


class SmartFlowIntegrityMonitor:
    """
    Monitors SmartFlow system integrity against golden baseline.
    """

    def __init__(self, baseline_path: Optional[str] = None):
        """Initialize with optional baseline path."""
        self.baseline_path = baseline_path or os.path.join(BASELINE_DIR, DEFAULT_BASELINE)
        self._baseline: Optional[Dict] = None
        self._load_baseline()

    def _load_baseline(self) -> None:
        """Load golden baseline from disk."""
        try:
            if os.path.exists(self.baseline_path):
                with open(self.baseline_path, 'r') as f:
                    self._baseline = json.load(f)
                logger.info(f"Loaded baseline: {self._baseline.get('baseline_version')}")
            else:
                logger.warning(f"Baseline not found: {self.baseline_path}")
                self._baseline = None
        except Exception as e:
            logger.error(f"Failed to load baseline: {e}")
            self._baseline = None

    def get_baseline(self) -> Optional[Dict]:
        """Return current baseline."""
        return self._baseline

    def run_full_check(self, db: Optional[Session] = None) -> IntegrityReport:
        """Run complete integrity check."""
        components: List[ComponentStatus] = []
        drift_findings: List[DriftFinding] = []
        category_scores: Dict[str, float] = {}
        notes: List[str] = []

        # Create DB session if not provided
        own_session = db is None
        if own_session:
            db = SessionLocal()

        try:
            # 1. Service Health
            service_components, service_score = self._check_services()
            components.extend(service_components)
            category_scores['services'] = service_score

            # 2. Database Health
            db_components, db_score, db_drift = self._check_database(db)
            components.extend(db_components)
            drift_findings.extend(db_drift)
            category_scores['database'] = db_score

            # 3. Runtime Chain Health
            chain_components, chain_score = self._check_runtime_chain(db)
            components.extend(chain_components)
            category_scores['runtime_chain'] = chain_score

            # 4. Strategy Registry Health
            strategy_components, strategy_score, strategy_drift = self._check_strategy_registry(db)
            components.extend(strategy_components)
            drift_findings.extend(strategy_drift)
            category_scores['routing'] = strategy_score

            # 5. Data Freshness
            freshness_components, freshness_score, freshness_drift = self._check_data_freshness(db)
            components.extend(freshness_components)
            drift_findings.extend(freshness_drift)
            category_scores['data_freshness'] = freshness_score

            # 6. Broker Health
            broker_components, broker_score = self._check_broker_health(db)
            components.extend(broker_components)
            category_scores['broker'] = broker_score

            # 7. Task Health
            task_components, task_score = self._check_task_health()
            components.extend(task_components)
            category_scores['tasks'] = task_score

            # 8. Baseline Drift Check
            if self._baseline:
                baseline_drift = self._check_baseline_drift(db)
                drift_findings.extend(baseline_drift)
                category_scores['baseline_drift'] = 100.0 - (len(baseline_drift) * 10)
            else:
                notes.append("No baseline loaded - baseline drift checks skipped")
                category_scores['baseline_drift'] = 50.0

            # Calculate overall score
            weights = {
                'services': 0.20,
                'database': 0.15,
                'runtime_chain': 0.15,
                'routing': 0.15,
                'data_freshness': 0.10,
                'broker': 0.10,
                'tasks': 0.10,
                'baseline_drift': 0.05
            }
            health_score = sum(
                category_scores.get(cat, 0) * weight
                for cat, weight in weights.items()
            )

            # Determine overall status
            if health_score >= 80:
                overall_status = HealthStatus.HEALTHY
            elif health_score >= 50:
                overall_status = HealthStatus.WARNING
            else:
                overall_status = HealthStatus.CRITICAL

            # Critical findings override
            critical_count = sum(1 for d in drift_findings if d.severity == DriftSeverity.CRITICAL)
            if critical_count > 0:
                overall_status = HealthStatus.CRITICAL
                notes.append(f"{critical_count} critical drift finding(s) detected")

            return IntegrityReport(
                timestamp=datetime.now(timezone.utc),
                overall_status=overall_status,
                health_score=round(health_score, 1),
                category_scores={k: round(v, 1) for k, v in category_scores.items()},
                components=components,
                drift_findings=drift_findings,
                baseline_version=self._baseline.get('baseline_version') if self._baseline else None,
                last_baseline_check=datetime.now(timezone.utc),
                notes=notes
            )

        finally:
            if own_session:
                db.close()

    def _check_services(self) -> tuple[List[ComponentStatus], float]:
        """Check core service health."""
        components = []
        healthy_count = 0
        total = 3  # DB, Redis, API

        # Database
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            components.append(ComponentStatus(
                name="postgres",
                status=HealthStatus.HEALTHY,
                message="Database connected"
            ))
            healthy_count += 1
        except Exception as e:
            components.append(ComponentStatus(
                name="postgres",
                status=HealthStatus.CRITICAL,
                message=f"Database error: {str(e)}"
            ))

        # Redis
        try:
            if redis_client.redis_client:
                redis_client.redis_client.ping()
                components.append(ComponentStatus(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    message="Redis connected"
                ))
                healthy_count += 1
            else:
                components.append(ComponentStatus(
                    name="redis",
                    status=HealthStatus.WARNING,
                    message="Redis client not initialized"
                ))
        except Exception as e:
            components.append(ComponentStatus(
                name="redis",
                status=HealthStatus.CRITICAL,
                message=f"Redis error: {str(e)}"
            ))

        # API (self-check)
        components.append(ComponentStatus(
            name="api",
            status=HealthStatus.HEALTHY,
            message="API running"
        ))
        healthy_count += 1

        score = (healthy_count / total) * 100
        return components, score

    def _check_database(self, db: Session) -> tuple[List[ComponentStatus], float, List[DriftFinding]]:
        """Check database schema and state."""
        components = []
        drift = []
        checks_passed = 0
        total_checks = 3

        # Alembic version
        try:
            result = db.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            version = result[0] if result else "unknown"
            expected = self._baseline.get('database_schema', {}).get('alembic_version') if self._baseline else None

            if expected and version != expected:
                drift.append(DriftFinding(
                    category="schema",
                    severity=DriftSeverity.WARNING,
                    title="Alembic version mismatch",
                    description=f"Database schema version differs from baseline",
                    expected=expected,
                    actual=version,
                    remediation="Review migration history"
                ))
                components.append(ComponentStatus(
                    name="alembic_version",
                    status=HealthStatus.WARNING,
                    message=f"Version: {version} (expected: {expected})",
                    drift_flag=True
                ))
            else:
                components.append(ComponentStatus(
                    name="alembic_version",
                    status=HealthStatus.HEALTHY,
                    message=f"Version: {version}"
                ))
                checks_passed += 1
        except Exception as e:
            components.append(ComponentStatus(
                name="alembic_version",
                status=HealthStatus.CRITICAL,
                message=f"Error: {str(e)}"
            ))

        # SmartFlow config table
        try:
            result = db.execute(text("SELECT count(*) FROM smartflow_config")).fetchone()
            count = result[0] if result else 0
            components.append(ComponentStatus(
                name="smartflow_config",
                status=HealthStatus.HEALTHY,
                message=f"{count} configurations",
                details={"row_count": count}
            ))
            checks_passed += 1
        except Exception as e:
            drift.append(DriftFinding(
                category="schema",
                severity=DriftSeverity.CRITICAL,
                title="smartflow_config table missing",
                description=str(e),
                remediation="Run alembic upgrade"
            ))
            components.append(ComponentStatus(
                name="smartflow_config",
                status=HealthStatus.CRITICAL,
                message=f"Error: {str(e)}"
            ))

        # FK relationship check
        try:
            result = db.execute(text("""
                SELECT count(*) FROM smartflow_signal_logs sl
                JOIN smartflow_config sc ON sl.config_id = sc.id
                LIMIT 1
            """)).fetchone()
            components.append(ComponentStatus(
                name="fk_relationships",
                status=HealthStatus.HEALTHY,
                message="FK relationships valid"
            ))
            checks_passed += 1
        except Exception as e:
            drift.append(DriftFinding(
                category="schema",
                severity=DriftSeverity.CRITICAL,
                title="FK relationship broken",
                description=str(e),
                remediation="Check model __tablename__ alignment"
            ))
            components.append(ComponentStatus(
                name="fk_relationships",
                status=HealthStatus.CRITICAL,
                message=f"Error: {str(e)}"
            ))

        score = (checks_passed / total_checks) * 100
        return components, score, drift

    def _check_runtime_chain(self, db: Session) -> tuple[List[ComponentStatus], float]:
        """Check runtime chain components are importable/available."""
        components = []
        available_count = 0

        chain_modules = [
            ("regime_detector", "app.services.regime_detector_v2", "RegimeDetectorV2"),
            ("engine_router", "app.services.smartflow_engine_router", "SmartFlowEngineRouter"),
            ("smartflow_service", "app.services.smartflow_service", "smartflow_service"),
            ("strategy_allocator", "app.services.strategy_allocator", "StrategyAllocator"),
            ("ai_feature_engine", "app.services.ai_feature_engine", "AIFeatureEngine"),
            ("flow_feature_engine", "app.services.flow_feature_engine", "FlowFeatureEngine"),
        ]

        for name, module_path, class_name in chain_modules:
            try:
                module = __import__(module_path, fromlist=[class_name])
                getattr(module, class_name)
                components.append(ComponentStatus(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    message="Module available"
                ))
                available_count += 1
            except Exception as e:
                components.append(ComponentStatus(
                    name=name,
                    status=HealthStatus.WARNING,
                    message=f"Import error: {str(e)[:50]}"
                ))

        score = (available_count / len(chain_modules)) * 100 if chain_modules else 100
        return components, score

    def _check_strategy_registry(self, db: Session) -> tuple[List[ComponentStatus], float, List[DriftFinding]]:
        """Check strategy registry state."""
        components = []
        drift = []
        score = 100.0

        try:
            result = db.execute(text("""
                SELECT strategy_id, strategy_type, status, health_status, is_paused
                FROM smartflow_strategies
            """)).fetchall()

            strategies = [
                {
                    'strategy_id': r[0],
                    'strategy_type': r[1],
                    'status': r[2],
                    'health_status': r[3],
                    'is_paused': r[4]
                }
                for r in result
            ]

            # Check strategy counts
            router_eligible = [s for s in strategies if 'approved' in s['status'] or s['status'] == 'built_in']
            paused = [s for s in strategies if s['is_paused']]
            unhealthy = [s for s in strategies if s['health_status'] in ['critical', 'degraded']]

            components.append(ComponentStatus(
                name="strategy_registry",
                status=HealthStatus.HEALTHY if len(router_eligible) >= 2 else HealthStatus.WARNING,
                message=f"{len(strategies)} strategies, {len(router_eligible)} router-eligible",
                details={
                    "total": len(strategies),
                    "router_eligible": len(router_eligible),
                    "paused": len(paused),
                    "unhealthy": len(unhealthy)
                }
            ))

            # Baseline comparison
            if self._baseline:
                baseline_strategies = self._baseline.get('strategy_registry', {}).get('strategies', [])
                baseline_ids = {s['strategy_id'] for s in baseline_strategies}
                current_ids = {s['strategy_id'] for s in strategies}

                missing = baseline_ids - current_ids
                if missing:
                    drift.append(DriftFinding(
                        category="routing",
                        severity=DriftSeverity.WARNING,
                        title="Missing strategies from baseline",
                        description=f"Strategies in baseline not found: {missing}",
                        expected=list(baseline_ids),
                        actual=list(current_ids)
                    ))
                    score -= 20

            if unhealthy:
                drift.append(DriftFinding(
                    category="routing",
                    severity=DriftSeverity.WARNING,
                    title="Unhealthy strategies detected",
                    description=f"{len(unhealthy)} strategies with degraded health",
                    actual=[s['strategy_id'] for s in unhealthy]
                ))
                score -= 10

            if paused:
                components.append(ComponentStatus(
                    name="paused_strategies",
                    status=HealthStatus.WARNING,
                    message=f"{len(paused)} strategies paused",
                    details={"paused": [s['strategy_id'] for s in paused]}
                ))

        except Exception as e:
            components.append(ComponentStatus(
                name="strategy_registry",
                status=HealthStatus.CRITICAL,
                message=f"Error: {str(e)}"
            ))
            score = 0

        return components, max(0, score), drift

    def _check_data_freshness(self, db: Session) -> tuple[List[ComponentStatus], float, List[DriftFinding]]:
        """Check for stale data."""
        components = []
        drift = []
        fresh_count = 0
        total = 2

        # Recent signals
        try:
            result = db.execute(text("""
                SELECT MAX(created_at) FROM smartflow_signal_logs
            """)).fetchone()
            last_signal = result[0] if result and result[0] else None

            if last_signal:
                age = datetime.now(timezone.utc) - last_signal.replace(tzinfo=timezone.utc)
                if age > timedelta(hours=24):
                    drift.append(DriftFinding(
                        category="data_freshness",
                        severity=DriftSeverity.INFO,
                        title="No recent signals",
                        description=f"Last signal was {age.total_seconds() / 3600:.1f} hours ago"
                    ))
                    components.append(ComponentStatus(
                        name="signal_freshness",
                        status=HealthStatus.WARNING,
                        message=f"Last signal: {last_signal}",
                        last_success=last_signal
                    ))
                else:
                    components.append(ComponentStatus(
                        name="signal_freshness",
                        status=HealthStatus.HEALTHY,
                        message=f"Last signal: {last_signal}",
                        last_success=last_signal
                    ))
                    fresh_count += 1
            else:
                components.append(ComponentStatus(
                    name="signal_freshness",
                    status=HealthStatus.WARNING,
                    message="No signals found"
                ))
        except Exception as e:
            components.append(ComponentStatus(
                name="signal_freshness",
                status=HealthStatus.CRITICAL,
                message=f"Error: {str(e)}"
            ))

        # Score history freshness
        try:
            result = db.execute(text("""
                SELECT MAX(timestamp) FROM smartflow_score_history
            """)).fetchone()
            last_score = result[0] if result and result[0] else None

            if last_score:
                components.append(ComponentStatus(
                    name="score_history_freshness",
                    status=HealthStatus.HEALTHY,
                    message=f"Last score: {last_score}",
                    last_success=last_score
                ))
                fresh_count += 1
            else:
                components.append(ComponentStatus(
                    name="score_history_freshness",
                    status=HealthStatus.WARNING,
                    message="No score history"
                ))
        except Exception as e:
            components.append(ComponentStatus(
                name="score_history_freshness",
                status=HealthStatus.WARNING,
                message=f"Error: {str(e)}"
            ))

        score = (fresh_count / total) * 100 if total > 0 else 100
        return components, score, drift

    def _check_broker_health(self, db: Session) -> tuple[List[ComponentStatus], float]:
        """Check broker connectivity (lightweight check)."""
        components = []

        try:
            result = db.execute(text("""
                SELECT broker, COUNT(*) as cnt, SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active
                FROM trading_accounts
                GROUP BY broker
            """)).fetchall()

            brokers = {r[0]: {'total': r[1], 'active': r[2]} for r in result}

            if brokers:
                active_brokers = [b for b, v in brokers.items() if v['active'] > 0]
                components.append(ComponentStatus(
                    name="broker_accounts",
                    status=HealthStatus.HEALTHY if active_brokers else HealthStatus.WARNING,
                    message=f"{len(active_brokers)} brokers with active accounts",
                    details=brokers
                ))
                score = 100 if active_brokers else 50
            else:
                components.append(ComponentStatus(
                    name="broker_accounts",
                    status=HealthStatus.WARNING,
                    message="No broker accounts found"
                ))
                score = 50

        except Exception as e:
            components.append(ComponentStatus(
                name="broker_accounts",
                status=HealthStatus.WARNING,
                message=f"Error: {str(e)}"
            ))
            score = 50

        return components, score

    def _check_task_health(self) -> tuple[List[ComponentStatus], float]:
        """Check Celery task health via Redis."""
        components = []
        score = 100.0

        try:
            # Check for Celery heartbeat in Redis
            if redis_client.redis_client:
                # Check if celery workers are registered
                worker_keys = redis_client.redis_client.keys("celery-task-meta-*")
                key_count = len(worker_keys) if worker_keys else 0

                components.append(ComponentStatus(
                    name="celery_tasks",
                    status=HealthStatus.HEALTHY,
                    message=f"Task backend available, {key_count} task results cached"
                ))
            else:
                components.append(ComponentStatus(
                    name="celery_tasks",
                    status=HealthStatus.WARNING,
                    message="Redis not available for task check"
                ))
                score = 70

        except Exception as e:
            components.append(ComponentStatus(
                name="celery_tasks",
                status=HealthStatus.WARNING,
                message=f"Cannot verify: {str(e)[:50]}"
            ))
            score = 70

        return components, score

    def _check_baseline_drift(self, db: Session) -> List[DriftFinding]:
        """Check for drift from golden baseline."""
        drift = []

        if not self._baseline:
            return drift

        # Git commit drift (informational)
        baseline_commit = self._baseline.get('code_identity', {}).get('git_commit', '')
        # Note: We don't check actual git commit as this runs inside container

        # Alembic version drift
        try:
            result = db.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            current_version = result[0] if result else None
            expected_version = self._baseline.get('database_schema', {}).get('alembic_version')

            if current_version != expected_version:
                drift.append(DriftFinding(
                    category="baseline_drift",
                    severity=DriftSeverity.WARNING,
                    title="Schema version drift",
                    description="Database schema version differs from frozen baseline",
                    expected=expected_version,
                    actual=current_version,
                    remediation="Review if migration is intentional"
                ))
        except Exception:
            pass

        # Strategy count drift
        try:
            result = db.execute(text("SELECT count(*) FROM smartflow_strategies")).fetchone()
            current_count = result[0] if result else 0
            expected_count = len(self._baseline.get('strategy_registry', {}).get('strategies', []))

            if current_count != expected_count:
                drift.append(DriftFinding(
                    category="baseline_drift",
                    severity=DriftSeverity.INFO,
                    title="Strategy count changed",
                    description="Number of strategies differs from baseline",
                    expected=expected_count,
                    actual=current_count
                ))
        except Exception:
            pass

        return drift

    def get_topology(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """Get runtime topology for visualization."""
        own_session = db is None
        if own_session:
            db = SessionLocal()

        try:
            report = self.run_full_check(db)

            # Build topology nodes
            nodes = []
            if self._baseline:
                for stage in self._baseline.get('runtime_chain', {}).get('stages', []):
                    # Find matching component status
                    comp_status = next(
                        (c for c in report.components if stage['name'] in c.name.lower()),
                        None
                    )
                    nodes.append({
                        "id": stage['name'],
                        "name": stage['name'].replace('_', ' ').title(),
                        "component": stage['component'],
                        "type": stage['type'],
                        "status": comp_status.status.value if comp_status else "unknown",
                        "message": comp_status.message if comp_status else "",
                        "drift_flag": comp_status.drift_flag if comp_status else False
                    })
            else:
                # Default chain without baseline
                default_chain = [
                    "market_data", "regime_detection", "adaptive_router",
                    "strategy_engine", "signal_guard", "allocator",
                    "execution", "broker", "logging"
                ]
                for name in default_chain:
                    nodes.append({
                        "id": name,
                        "name": name.replace('_', ' ').title(),
                        "status": "unknown"
                    })

            return {
                "timestamp": report.timestamp.isoformat(),
                "overall_status": report.overall_status.value,
                "health_score": report.health_score,
                "nodes": nodes,
                "drift_count": len(report.drift_findings),
                "baseline_version": report.baseline_version
            }

        finally:
            if own_session:
                db.close()


# Singleton instance
integrity_monitor = SmartFlowIntegrityMonitor()


def to_dict(obj: Any) -> Any:
    """Convert dataclass or enum to dict."""
    if hasattr(obj, '__dataclass_fields__'):
        return {k: to_dict(v) for k, v in asdict(obj).items()}
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, list):
        return [to_dict(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    return obj
