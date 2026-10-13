"""Public-repo quality gate: secrets, env documentation, README, lint, static JS. No network.

Failure messages name files and pattern labels only, never matched secret values.
"""

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "lovelight" / "static"
MAX_SCAN_BYTES = 5_000_000

ENV_READ_RE = re.compile(
    r"""os\.environ\.get\(\s*["'](\w+)["']"""
    r"""|os\.environ\[\s*["'](\w+)["']\s*\]"""
    r"""|os\.getenv\(\s*["'](\w+)["']"""
)
SECRET_PATTERNS = {
    "anthropic-api-key": re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"),
    "private-key-block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "gmail-app-password": re.compile(r"GMAIL\w*\s*[=:]\s*[\"']?(?:[a-z]{4}[ \-]?){3}[a-z]{4}\b"),
}


def _git(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


def _candidate_files() -> list[str]:
    """Files that would land in the public repo: tracked + untracked-but-not-ignored."""
    return sorted(set(_git("ls-files", "--cached")) | set(_git("ls-files", "--others", "--exclude-standard")))


def _env_vars_read_in_code() -> set[str]:
    names: set[str] = set()
    for path in [*(ROOT / "src").rglob("*.py"), *(ROOT / "scripts").rglob("*.py")]:
        for m in ENV_READ_RE.finditer(path.read_text()):
            names.update(g for g in m.groups() if g)
    return names


def test_dotenv_is_git_ignored():
    r = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT, check=False)
    assert r.returncode == 0, ".env must be matched by .gitignore"


def test_env_example_documents_every_env_var():
    example = ROOT / ".env.example"
    assert example.is_file(), ".env.example missing"
    declared = set(re.findall(r"^\s*#?\s*([A-Z][A-Z0-9_]+)\s*=", example.read_text(), re.MULTILINE))
    missing = _env_vars_read_in_code() - declared
    assert not missing, f".env.example lacks: {sorted(missing)}"


def test_env_example_is_tracked_candidate_and_has_no_real_values():
    assert ".env.example" in _candidate_files(), ".env.example must not be git-ignored"
    for line in (ROOT / ".env.example").read_text().splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = (s.strip() for s in line.split("=", 1))
        if key.endswith(("KEY", "PASSWORD", "SECRET", "TOKEN")):
            assert value == "" or value.startswith("<") or "your" in value.lower(), f"{key} looks like a real value"


def test_no_private_data_or_runtime_state_in_repo():
    bad = [
        f
        for f in _candidate_files()
        if f.startswith(("data/incoming/", "data/cache/"))
        or f.endswith((".db", ".sqlite", ".sqlite3"))
        or Path(f).name == ".env"
        or Path(f).name == ".DS_Store"
    ]
    assert not bad, f"private/runtime files would be published: {bad}"


def test_no_secrets_in_repo_files():
    hits = []
    for rel in _candidate_files():
        path = ROOT / rel
        if not path.is_file() or path.stat().st_size > MAX_SCAN_BYTES:
            continue
        text = path.read_bytes().decode("utf-8", errors="ignore")
        hits += [f"{rel}: {label}" for label, rx in SECRET_PATTERNS.items() if rx.search(text)]
    assert not hits, f"secret patterns found: {hits}"


def test_no_local_home_paths_in_repo_files():
    hits = []
    for rel in _candidate_files():
        path = ROOT / rel
        if not path.is_file() or path.stat().st_size > MAX_SCAN_BYTES:
            continue
        if re.search(rb"/Users/[a-z][\w.-]+/", path.read_bytes()):
            hits.append(rel)
    assert not hits, f"absolute home paths leak into: {hits}"


def test_secret_scanner_detects_planted_patterns():
    fake_key = "sk-ant-" + "api03-" + "x" * 20
    fake_pw = "GMAIL_APP_PASSWORD=" + "abcd efgh ijkl mnop"
    fake_pem = "-----BEGIN " + "PRIVATE KEY-----"
    for sample, label in [
        (fake_key, "anthropic-api-key"),
        (fake_pw, "gmail-app-password"),
        (fake_pem, "private-key-block"),
    ]:
        assert SECRET_PATTERNS[label].search(sample), label


def test_license_exists():
    lic = ROOT / "LICENSE"
    assert lic.is_file() and lic.read_text().strip(), "LICENSE missing or empty"


def test_pyproject_has_real_description():
    text = (ROOT / "pyproject.toml").read_text()
    m = re.search(r'^description\s*=\s*"([^"]*)"', text, re.MULTILINE)
    assert m and m.group(1) and "Add your description" not in m.group(1)


def _readme() -> str:
    readme = ROOT / "README.md"
    assert readme.is_file(), "README.md missing"
    return readme.read_text()


def test_readme_has_quickstart_commands():
    text = _readme()
    for cmd in ("uv sync", "uv run pytest", "uv run uvicorn lovelight.server:app"):
        assert cmd in text, f"README missing quickstart command: {cmd}"


def test_readme_has_architecture_and_trust_sections():
    headings = [h.lower() for h in re.findall(r"^#{1,4}\s+(.+)$", _readme(), re.MULTILINE)]
    assert any("architecture" in h for h in headings), "README needs an Architecture section"
    assert any("trust" in h or "security" in h for h in headings), "README needs a Trust/Security section"


def test_readme_referenced_paths_exist():
    text = _readme()
    refs = set(re.findall(r"\b((?:scripts|src|tests|docs|data/generated)/[\w./-]*\w)", text))
    refs |= {
        link.split("#")[0]
        for link in re.findall(r"\]\(([^)\s]+)\)", text)
        if not link.startswith(("http://", "https://", "#", "mailto:"))
    }
    missing = sorted(r for r in refs if r and not (ROOT / r).exists())
    assert not missing, f"README references missing paths: {missing}"


def test_quickstart_targets_exist():
    from lovelight import server

    assert server.app is not None
    assert (ROOT / "tests").is_dir()


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("js", sorted(p.name for p in STATIC.glob("*.js")))
def test_static_js_parses(js):
    r = subprocess.run(["node", "--check", str(STATIC / js)], capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr


def test_index_html_is_demo_ready():
    html = (STATIC / "index.html").read_text()
    assert re.search(r"<title>[^<]+</title>", html), "index.html needs a <title>"
    assert 'name="viewport"' in html, "index.html needs a viewport meta"


@pytest.mark.skipif(importlib.util.find_spec("ruff") is None, reason="ruff not installed (dev group)")
def test_ruff_clean():
    r = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
