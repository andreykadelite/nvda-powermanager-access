"""Load pure submodules without importing NVDA's runtime entry point."""

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
package = types.ModuleType("powermanager")
package.__path__ = [str(ROOT / "addon/appModules/powermanager")]
sys.modules["powermanager"] = package
