"""
Generate PyInstaller version info file (version_info.txt) from APP_VERSION.

Usage:
    python version_info.py

Reads APP_VERSION from main.py and writes version_info.txt for PyInstaller's
--version-file flag. This embeds File Version, Product Version, Company Name,
etc. into the exe's Windows properties.
"""

import re
import os

# Read version from main.py
script_dir = os.path.dirname(os.path.abspath(__file__))
main_py = os.path.join(script_dir, "main.py")

with open(main_py, "r") as f:
    content = f.read()

match = re.search(r'APP_VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content)
if not match:
    raise ValueError("Could not find APP_VERSION in main.py")

major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
version_str = f"{major}.{minor}.{patch}"
version_tuple = f"{major}, {minor}, {patch}, 0"

print(f"Version: {version_str} ({version_tuple})")

template = f"""# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version_tuple}),
    prodvers=({version_tuple}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'CompanyName', u'Highland Mortgage Services'),
            StringStruct(u'FileDescription', u'Nexus - Automated Vendor Account Provisioning'),
            StringStruct(u'FileVersion', u'{version_str}.0'),
            StringStruct(u'InternalName', u'Nexus'),
            StringStruct(u'LegalCopyright', u'Highland Mortgage Services'),
            StringStruct(u'OriginalFilename', u'Nexus.exe'),
            StringStruct(u'ProductName', u'Nexus'),
            StringStruct(u'ProductVersion', u'{version_str}.0'),
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""

output_path = os.path.join(script_dir, "version_info.txt")
with open(output_path, "w") as f:
    f.write(template)

print(f"Written: {output_path}")
