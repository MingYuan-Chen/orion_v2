#!/usr/bin/env python
"""
Main entry point for the application
"""

import sys
from PySide6.QtWidgets import QApplication
from gui.views.login import LoginDialog
from gui.views.device_manager import DeviceManagerWidget
from util.logger import logger


def main():
    """Main entry function"""
    try:
        # Create application
        app = QApplication(sys.argv)
        
        # Set application name and style
        app.setApplicationName("VT Hydra")
        app.setStyle("Fusion")  # Use Fusion style for a modern look
        
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
            sys.exit(app.exec())
        else:
            logger.info("Login cancelled or failed. Exiting application.")
            return 0
            
    except Exception as e:
        logger.error(f"Application failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())