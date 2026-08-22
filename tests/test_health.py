from orbit.core.health import HealthCheck, HealthRegistry, HealthStatus


def test_health_registry_orders_checks_and_reports_overall_status() -> None:
    registry = HealthRegistry()
    registry.register("zeta", lambda: HealthCheck("zeta", HealthStatus.HEALTHY))
    registry.register("alpha", lambda: HealthCheck("alpha", HealthStatus.DEGRADED))

    results = registry.check()

    assert [item.name for item in results] == ["alpha", "zeta"]
    assert registry.overall() is HealthStatus.DEGRADED


def test_health_registry_turns_exceptions_into_unhealthy_checks() -> None:
    registry = HealthRegistry()

    def broken() -> HealthCheck:
        raise RuntimeError("database unavailable")

    registry.register("database", broken)

    result = registry.check()[0]

    assert result.status is HealthStatus.UNHEALTHY
    assert result.detail == "database unavailable"
    assert registry.overall() is HealthStatus.UNHEALTHY
