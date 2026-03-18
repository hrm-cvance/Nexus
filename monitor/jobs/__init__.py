"""
Nexus Monitor Job Registry

Explicit registration — no filesystem discovery (PyInstaller bundles
don't have scannable directories).
"""

from monitor.jobs import partners_user_list

ALL_JOBS = [
    partners_user_list,
]
