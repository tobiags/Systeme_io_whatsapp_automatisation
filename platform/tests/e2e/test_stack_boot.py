from pathlib import Path


def test_stack_layout_exists():
    root = Path(__file__).resolve().parents[2]
    assert (root / "docker-compose.yml").exists()
    assert (root / "shared" / "config" / "settings.py").exists()
    assert (root / ".env.example").exists()
