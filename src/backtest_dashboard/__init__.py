"""可复用、完全离线的回测看板生成器。"""

from .builder import asset_path, package_source_files, render_dashboard, write_dashboard
from .schema import DashboardDataError, validate_dashboard_data

__all__ = [
    "DashboardDataError",
    "asset_path",
    "package_source_files",
    "render_dashboard",
    "validate_dashboard_data",
    "write_dashboard",
]
__version__ = "1.2.0"
