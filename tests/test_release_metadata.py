from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]

def test_release_version_is_stable_1_0_0():
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "1.0.0"
    assert client.get("/api/version").json()["version"] == "1.0.0"

def test_ui_release_label_is_stable():
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    assert "1.0 Stable" in html
    assert "RC1" not in html
