"""
Views modules for the DQA test tool
"""

from .main_window import MainWindowController
from .device_manager_widget import DeviceManagerWidget
from .device_connection_dialog import DeviceConnectionDialog
from .login_dialog import LoginDialog
from .auto_diagnostic_view import AutoDiagnosticView
from .test_manager import TestManagerView
from .system_info_manager import SystemInfoManagerView
from .log_manager import LogManagerView
from .hw_sw_config_manager import HWSWConfigManager
from .firmware_os_manager import FirmwareOSManager
from .battery_monitor_manager import BatteryMonitorManager

__all__ = [
    'MainWindowController',
    'DeviceManagerWidget',
    'DeviceConnectionDialog',
    'LoginDialog',
    'AutoDiagnosticView',
    'TestManagerView',
    'SystemInfoManagerView',
    'LogManagerView',
    'HWSWConfigManager',
    'FirmwareOSManager',
    'BatteryMonitorManager'
] 