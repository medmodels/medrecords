"""Download the Typst packages the report template imports.

Run from the repository root::

    uv run python scripts/fetch_typst_packages.py
"""

import re
import shutil
from pathlib import Path

import typst

TEMPLATE = Path(__file__).parent.parent / "medrecords" / "evaluation" / "template"

PACKAGES = TEMPLATE / "packages"

PREVIEW_IMPORT = re.compile(r'#import "(@preview/[a-z0-9-]+:[0-9.]+)"')

imports = sorted(
    {
        package
        for template in TEMPLATE.glob("*.typ")
        for package in PREVIEW_IMPORT.findall(template.read_text(encoding="utf-8"))
    }
)
importer = "\n".join(f'#import "{package}"' for package in imports)

shutil.rmtree(PACKAGES, ignore_errors=True)
typst.compile(importer.encode(), package_cache_path=PACKAGES)
