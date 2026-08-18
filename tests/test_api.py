"""End-to-end API workflow tests (role-aware)."""


def _create_employee(client, headers, code="API-001"):
    resp = client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "employee_code": code,
            "full_name": "API Test User",
            "department": "Security",
            "designation": "Analyst",
            "device_info": {"os": "Linux"},
            "access_privileges": ["vpn"],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _manager_headers(auth_headers, email="mgr@test.com"):
    return auth_headers(email=email, role="security_manager")


def test_employee_crud_workflow(client, auth_headers):
    mgr = _manager_headers(auth_headers)
    admin = auth_headers(email="root@test.com", role="administrator")
    emp = _create_employee(client, mgr)

    listing = client.get("/api/v1/employees", headers=mgr)
    assert listing.status_code == 200
    assert any(e["id"] == emp["id"] for e in listing.json())

    got = client.get(f"/api/v1/employees/{emp['id']}", headers=mgr)
    assert got.status_code == 200
    assert got.json()["full_name"] == "API Test User"

    upd = client.put(
        f"/api/v1/employees/{emp['id']}",
        headers=mgr,
        json={"department": "IT Security", "designation": "SOC Engineer"},
    )
    assert upd.status_code == 200
    assert upd.json()["department"] == "IT Security"

    dele = client.delete(f"/api/v1/employees/{emp['id']}", headers=admin)
    assert dele.status_code == 204
    assert client.get(f"/api/v1/employees/{emp['id']}", headers=mgr).status_code == 404


def test_analyst_cannot_create_employee(client, auth_headers):
    headers = auth_headers(email="viewer@test.com", role="security_analyst")
    resp = client.post(
        "/api/v1/employees",
        headers=headers,
        json={"employee_code": "NO-PERM", "full_name": "Blocked"},
    )
    assert resp.status_code == 403


def test_bulk_activity_log_ingestion(client, auth_headers):
    mgr = _manager_headers(auth_headers, email="mgr2@test.com")
    soc = auth_headers(email="soc@test.com", role="soc_engineer")
    emp = _create_employee(client, mgr, code="API-002")
    resp = client.post(
        "/api/v1/activity-logs/bulk",
        headers=soc,
        json={
            "logs": [
                {
                    "employee_id": emp["id"],
                    "activity_type": "login",
                    "source": "workstation",
                    "details": {"method": "mfa"},
                    "occurred_at": "2026-08-01T09:00:00",
                },
                {
                    "employee_id": emp["id"],
                    "activity_type": "usb_device",
                    "source": "workstation",
                    "details": {"device": "USB-1"},
                    "occurred_at": "2026-08-01T09:05:00",
                },
            ]
        },
    )
    assert resp.status_code == 201
    assert resp.json()["ingested"] == 2


def test_alert_escalation_creates_incident(client, auth_headers):
    mgr = _manager_headers(auth_headers, email="mgr3@test.com")
    soc = auth_headers(email="soc2@test.com", role="soc_engineer")
    emp = _create_employee(client, mgr, code="API-003")

    alert_resp = client.post(
        "/api/v1/alerts",
        headers=soc,
        json={
            "employee_id": emp["id"],
            "title": "Suspicious USB Activity",
            "description": "Unauthorized USB device connected",
            "severity": "high",
            "anomaly_type": "usb_device_spike",
        },
    )
    assert alert_resp.status_code == 201
    alert_id = alert_resp.json()["id"]

    inc = client.post(f"/api/v1/alerts/{alert_id}/escalate", headers=soc)
    assert inc.status_code == 201
    assert inc.json()["title"].startswith("Escalated:")
    assert alert_id in inc.json()["related_alert_ids"]


def test_analyst_cannot_create_alert(client, auth_headers):
    mgr = _manager_headers(auth_headers, email="mgr4@test.com")
    analyst = auth_headers(email="plain@test.com", role="security_analyst")
    emp = _create_employee(client, mgr, code="API-004")
    resp = client.post(
        "/api/v1/alerts",
        headers=analyst,
        json={
            "employee_id": emp["id"],
            "title": "Nope",
            "severity": "low",
        },
    )
    assert resp.status_code == 403


def test_dashboard_stats(client, auth_headers):
    headers = auth_headers()
    resp = client.get("/api/v1/dashboard/stats", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    for key in (
        "total_employees", "total_alerts", "open_alerts", "critical_alerts",
        "total_incidents", "active_incidents", "total_activity_logs",
        "high_risk_employees",
    ):
        assert key in data


def test_anomaly_detection_endpoints(client, auth_headers, monkeypatch, tmp_path):
    """Anomaly alert stats + cached latest detection endpoints."""
    from app.services import anomaly_detection as ad

    monkeypatch.setattr(ad, "DETECTION_CACHE", tmp_path / "detection.json")
    headers = auth_headers()

    stats = client.get("/api/v1/anomaly/alerts/stats", headers=headers)
    assert stats.status_code == 200
    assert "total_open" in stats.json()
    assert "by_severity" in stats.json()

    latest = client.get("/api/v1/anomaly/detect/latest", headers=headers)
    assert latest.status_code == 200
    assert latest.json() is None  # nothing cached yet in this isolated env

    # After a detection run, the cached result is served.
    client.post("/api/v1/anomaly/detect", headers=headers, json={"days": 30})
    latest2 = client.get("/api/v1/anomaly/detect/latest", headers=headers)
    assert latest2.status_code == 200
    assert latest2.json()["scanned_employees"] == 0
    assert latest2.json()["generated_at"]
