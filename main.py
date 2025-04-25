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


def main():
    """Main entry function"""
    try:
        # Create application
        app = QApplication(sys.argv)
        
        # 設置更完整的應用程序標識
        app.setApplicationName("VT Hydra")
        app.setApplicationDisplayName("VT Hydra Device Manager")
        app.setOrganizationName("Orion")
        app.setOrganizationDomain("orion.com")
        app.setApplicationVersion("1.0.0.0")
        
        # 確保 Qt 知道所有窗口屬於同一應用程序實例
        app.setAttribute(Qt.AA_UseHighDpiPixmaps)  # 使用高 DPI 圖像
        
        app.setStyle("Fusion")  # Use Fusion style for a modern look
        
        # Set application icon
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            icon_path = os.path.join(sys._MEIPASS, 'resources', 'icons', 'header.ico')
        else:
            # Normal development environment
            current_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(current_dir, "resources", "icons", "header.ico")
            
        if os.path.exists(icon_path):
            from PySide6.QtGui import QIcon
            app_icon = QIcon(icon_path)
            app.setWindowIcon(app_icon)
            logger.info("Application icon set successfully")
        else:
            logger.warning(f"Icon file not found: {icon_path}")
        
        # 設置進程 ID，用於任務管理器顯示
        if sys.platform == 'win32':
            import ctypes
            app_id = 'Orion.VTHydra.DeviceManager.2504'  # 格式: 組織.產品.應用.版本
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
                logger.debug(f"Set Windows Application User Model ID: {app_id}")
            except Exception as e:
                logger.warning(f"Failed to set Application User Model ID: {e}")
        
        # Start with login screen
        login_dialog = LoginDialog()
        login_result = login_dialog.exec()
        
        # If login successful, show device manager
        if login_result == LoginDialog.Accepted and login_dialog.login_successful:
            logger.info("Login successful. Starting device manager...")
            
            # Create and show device manager
            device_manager = DeviceManagerWidget()
            device_manager.show()
            
            # Run main event loop
            return app.exec()
        else:
            logger.info("Login cancelled or failed. Exiting application.")
            return 0
            
    except Exception as e:
        logger.error(f"Application failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())