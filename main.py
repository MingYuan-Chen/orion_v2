#!/usr/bin/env python
"""
Main entry point for the application
"""

import sys
from PySide6.QtWidgets import QApplication
from gui.views.login_dialog import LoginDialog
from gui.views.device_manager_widget import DeviceManagerWidget
from util.logger import logger
import os
from PySide6.QtCore import Qt
from util.resource_manager import ensure_default_hw_configs


def main():
    """Main entry function"""
    try:
        # Ensure default hardware configs are in place
        ensure_default_hw_configs()
        
        # Create application
        app = QApplication(sys.argv)
        
        # Set application name
        app.setApplicationName("Orion")
        app.setApplicationDisplayName("Orion Monitor v2.0.1 20251104")
        app.setOrganizationName("Orion")
        app.setOrganizationDomain("orion.com")
        app.setApplicationVersion("2.0.1.0")
        
        # use high DPI scaling
        app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        
        app.setStyle("Fusion")  # Use Fusion style for a modern look
        
        # Set application icon
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            icon_path = os.path.join(sys._MEIPASS, 'resources', 'icons', 'header.ico')
        else:
            # Normal development environment
            icon_path = os.path.join(os.getcwd(), "resources", "icons", "header.ico")
            
        if os.path.exists(icon_path):
            from PySide6.QtGui import QIcon
            app_icon = QIcon(icon_path)
            app.setWindowIcon(app_icon)
            logger.info("Application icon set successfully")
        else:
            logger.warning(f"Icon file not found: {icon_path}")
        
        # Set process ID, for task manager display
        if sys.platform == 'win32':
            import ctypes
            app_id = 'Promate.Orion.DeviceManager.1000'  # Format: Organization.Product.Application.Version
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
                logger.debug(f"Set Windows Application User Model ID: {app_id}")
            except Exception as e:
                logger.warning(f"Failed to set Application User Model ID: {e}")
        
        # Create and show device manager
        device_manager = DeviceManagerWidget()
        device_manager.show()
            
        # Run main event loop
        return app.exec()
            
    except Exception as e:
        logger.error(f"Application failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())