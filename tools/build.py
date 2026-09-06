"""Reproducible source-only NVDA add-on package; no runtime build dependencies."""

import ast
import hashlib
import json
import re
from pathlib import Path
import zipfile

from configobj import ConfigObj
import markdown

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "addon"
DIST = ROOT / "dist"
STAMP = (2026, 9, 6, 0, 0, 0)


def require(condition, message):
    if not condition:
        raise ValueError(message)


PUBLIC_ROOT_FILES = (
    "README.md",
    "README.ru.md",
    "CHANGELOG.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "requirements-dev.txt",
    "pyproject.toml",
    ".gitignore",
    ".gitattributes",
    "QA-REPORT.md",
)
PUBLIC_TOOLS = ("build.py", "bootstrap.ps1", "check_docs.py", "publish.ps1")


def render_document(text, language):
    def offline_link(match):
        target = match[1]
        if "://" in target or not target.endswith(".md"):
            return match[0]
        target = re.sub(r"user-guide\.md$", "readme.html", target)
        target = re.sub(r"\.md$", ".html", target)
        return f"]({target})"

    text = re.sub(r"\]\(([^)]+)\)", offline_link, text)
    html = f'<!doctype html><html lang="{language}"><head><meta charset="utf-8"><title>PowerManagerII Access</title>'
    html += "<style>body{max-width:65em;margin:2em auto;padding:0 1em;line-height:1.6;font-family:sans-serif}table{border-collapse:collapse}th,td{border:1px solid #777;padding:.5em;text-align:left}a{color:#034ea2}pre{white-space:pre-wrap}</style></head><body>"
    return html + markdown.markdown(text, extensions=["tables", "fenced_code"]) + "</body></html>"


def documentation():
    for language in ("ru", "en"):
        for stem in ("user-guide", "development", "testing"):
            text = (ROOT / "docs" / language / f"{stem}.md").read_text(encoding="utf-8")
            filename = "readme.html" if stem == "user-guide" else f"{stem}.html"
            path = ADDON / "doc" / language / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render_document(text, language), encoding="utf-8", newline="\n")
    (ADDON / "LICENSE.txt").write_bytes((ROOT / "LICENSE").read_bytes())


def public_source_files(addon_files):
    files = [("addon/" + name, path) for name, path in addon_files]
    files += [(name, ROOT / name) for name in PUBLIC_ROOT_FILES]
    for folder, suffixes in (("tests", {".py"}), ("docs", {".md"}), (".github", {".yml", ".md"})):
        files += [
            (p.relative_to(ROOT).as_posix(), p)
            for p in (ROOT / folder).rglob("*")
            if p.is_file() and p.suffix in suffixes and "__pycache__" not in p.parts
        ]
    files += [("tools/" + name, ROOT / "tools" / name) for name in PUBLIC_TOOLS]
    return files


def write_zip(path, files):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, source in sorted(files):
            info = zipfile.ZipInfo(name, STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def main():
    documentation()
    manifest = ConfigObj(str(ADDON / "manifest.ini"), encoding="utf-8")
    require(manifest["name"] == "powerManagerAccess", "Unexpected add-on name")
    require(re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"]), "Use a three-part release version")
    require(
        tuple(map(int, manifest["minimumNVDAVersion"].split(".")))
        <= tuple(map(int, manifest["lastTestedNVDAVersion"].split("."))),
        "Invalid NVDA version interval",
    )
    DIST.mkdir(exist_ok=True)
    files = []
    for source in ADDON.rglob("*"):
        if not source.is_file() or "__pycache__" in source.parts:
            continue
        relative = source.relative_to(ADDON).as_posix()
        require(source.suffix in {".py", ".json", ".ini", ".html", ".txt"}, f"Unexpected file: {relative}")
        require(not relative.startswith("globalPlugins/"), "Development plugins must not be shipped")
        if source.suffix == ".py":
            ast.parse(source.read_text(encoding="utf-8"), filename=relative, feature_version=(3, 11))
        files.append((relative, source))
    package_name = f"{manifest['name']}-{manifest['version']}"
    addon_file = DIST / f"{package_name}.nvda-addon"
    write_zip(addon_file, files)
    with zipfile.ZipFile(addon_file) as archive:
        require(archive.testzip() is None, "Corrupt ZIP")
        require("manifest.ini" in archive.namelist(), "Missing manifest")
        require("appModules/powermanager/__init__.py" in archive.namelist(), "Missing application module")
    source_zip = DIST / f"{package_name}-source.zip"
    write_zip(source_zip, public_source_files(files))
    checksums = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (addon_file, source_zip)}
    (DIST / "SHA256SUMS.txt").write_text(
        "".join(f"{value}  {name}\n" for name, value in checksums.items()), encoding="ascii", newline="\n"
    )
    print(json.dumps({"package": str(addon_file), "files": len(files), "sha256": checksums}, indent=2))


if __name__ == "__main__":
    main()
