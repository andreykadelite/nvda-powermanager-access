"""Publication must preserve language and exclude local diagnostics."""

import importlib.util
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_builder", ROOT / "tools/build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def test_offline_documents_keep_language_and_resolve_guide_links():
    text = "# Help\n\n[Русский](../ru/user-guide.md) [Tests](testing.md) [NVDA](https://example.org/a.md)"
    rendered = build.render_document(text, "en")
    assert '<html lang="en">' in rendered
    assert 'href="../ru/readme.html"' in rendered
    assert 'href="testing.html"' in rendered
    assert 'href="https://example.org/a.md"' in rendered


def test_public_source_excludes_probe_tools_logs_and_vendor_files():
    files = dict(build.public_source_files([]))
    assert "tools/build.py" in files and "tools/publish.ps1" in files
    assert "docs/en/user-guide.md" in files and "docs/ru/user-guide.md" in files
    assert not any(name.startswith(("research/", ".venv/", "dist/")) for name in files)
    assert "tools/probe_nvda.py" not in files and "tools/install_probe.ps1" not in files
    assert not any(name.endswith((".exe", ".dll", ".log")) for name in files)


def test_archive_is_reproducible_and_contains_original_bytes(tmp_path):
    original = tmp_path / "source.py"
    original.write_bytes(b"# sample\nvalue = 1\n")
    first, second = tmp_path / "one.zip", tmp_path / "two.zip"
    build.write_zip(first, [("appModules/sample.py", original)])
    build.write_zip(second, [("appModules/sample.py", original)])
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert archive.testzip() is None
        assert archive.read("appModules/sample.py") == original.read_bytes()
