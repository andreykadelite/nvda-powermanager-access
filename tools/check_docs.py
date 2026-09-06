"""Check local documentation links, release filenames and accidental control characters."""

from pathlib import Path
import re

from configobj import ConfigObj

ROOT = Path(__file__).resolve().parents[1]
GITHUB_ROUTES = {"../../releases/latest", "../../issues/new/choose"}


def check():
    version = ConfigObj(str(ROOT / "addon/manifest.ini"), encoding="utf-8")["version"]
    paths = list(ROOT.glob("*.md")) + list((ROOT / "docs").rglob("*.md"))
    errors = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text):
            errors.append(f"{path.name}: unexpected control character")
        for found in re.findall(r"powerManagerAccess-(\d+\.\d+\.\d+)(?:\.nvda-addon|-source\.zip)", text):
            if found != version:
                errors.append(f"{path.name}: installer version {found} differs from {version}")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            if target.startswith(("https://", "http://", "#")) or target in GITHUB_ROUTES:
                continue
            local = (path.parent / target.split("#", 1)[0]).resolve()
            if not local.is_relative_to(ROOT) or not local.exists():
                errors.append(f"{path.relative_to(ROOT)}: missing local link {target}")
    return paths, errors


if __name__ == "__main__":
    documents, failures = check()
    for failure in failures:
        print(failure)
    if failures:
        raise SystemExit(1)
    print(f"Checked {len(documents)} documents: local links and release filenames match")
