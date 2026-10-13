"""Static deploy gate: container, compose, Fly.io config and security policy exist and say the right things."""

import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SECURITY_SECTIONS = [
    "Threat model",
    "Data handling",
    "Secrets",
    "Auth",
    "Audit trail",
    "Uptime & backups",
    "Responsible disclosure",
]


def test_dockerfile_non_root_uv_and_healthcheck():
    text = (ROOT / "Dockerfile").read_text()
    users = re.findall(r"^\s*USER\s+(\S+)", text, re.M)
    assert users and users[-1] not in {"root", "0", "0:0"}, "final stage must run as a non-root user"
    assert re.search(r"\buv\b", text), "build with uv"
    assert re.search(r"uv sync[^\n]*--frozen", text), "install from the lockfile"
    hc = re.search(r"^\s*HEALTHCHECK\b.*$", text, re.M)
    assert hc and "/api/health" in text[hc.start():hc.start() + 400]
    copies = re.findall(r"^\s*COPY\s+(.+)$", text, re.M)
    assert not any(re.search(r"(^|\s)\.env(\s|$)", c) for c in copies), "never bake .env into the image"


def test_dockerignore_excludes_secrets_and_private_data():
    text = (ROOT / ".dockerignore").read_text()
    for pattern in (".env", "data/incoming", ".venv", "video"):
        assert pattern in text, pattern


def test_compose_app_with_optional_postgres_profile():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    services = compose["services"]
    assert "app" in services
    app = services["app"]
    assert "profiles" not in app, "app runs by default"
    assert "/api/health" in str(app.get("healthcheck", {}))
    pg = next((s for s in services.values() if "postgres" in str(s.get("image", ""))), None)
    assert pg is not None and pg.get("profiles"), "postgres must be opt-in via a profile"


def test_fly_toml_region_and_health_check():
    fly = tomllib.loads((ROOT / "fly.toml").read_text())
    assert fly["primary_region"] == "arn"
    checks = fly.get("http_service", {}).get("checks", [])
    assert any(c.get("path") == "/api/health" for c in checks), "http_service.checks needs /api/health"
    assert fly.get("mounts"), "SQLite needs a persistent volume"


def test_security_md_sections():
    text = (ROOT / "SECURITY.md").read_text()
    headings = [h.strip().lower() for h in re.findall(r"^#{2,3}\s+(.+)$", text, re.M)]
    for section in SECURITY_SECTIONS:
        assert any(h.startswith(section.lower()) for h in headings), f"SECURITY.md needs '## {section}'"


def test_env_example_documents_light_connector():
    text = (ROOT / ".env.example").read_text()
    for var in ("LIGHT_API_KEY", "LIGHT_API_URL"):
        assert re.search(rf"^\s*#?\s*{var}\s*=", text, re.M), var
