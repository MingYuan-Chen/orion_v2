#!/usr/bin/env python
"""
Login View

Load login UI and handle user authentication
"""

import os
import sys
from PySide6.QtWidgets import QDialog, QMessageBox, QApplication, QLineEdit, QPushButton, QVBoxLayout
from PySide6.QtCore import Qt, QFile, QIODevice
from PySide6.QtUiTools import QUiLoader
from util.logger import logger


class LoginDialog(QDialog):
    """Login dialog class"""
    
    def __init__(self, parent=None):
        """Initialize login dialog
        
        Args:
            parent: parent window
        """
        super().__init__(parent)
        
        # Initialize login state
        self.login_successful = False
        
        # Load UI directly
        self._load_ui_direct()
        
        # Setup connections
        self._setup_connections()
        
    def _load_ui_direct(self):
        """Load UI with a more direct approach"""
        try:
            # Get UI file path - support PyInstaller
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
                ui_file_path = os.path.join(base_path, 'gui', 'ui', 'login_dialog.ui')
                icon_path = os.path.join(base_path, 'resources', 'icons', 'header.ico')
            else:
                # Normal development environment
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ui_file_path = os.path.join(current_dir, "ui", "login_dialog.ui")
                
                # Get icon path - go up two directories to find resources
                base_dir = os.path.dirname(os.path.dirname(current_dir))
                icon_path = os.path.join(base_dir, "resources", "icons", "header.ico")
                
            logger.debug(f"Loading UI from: {ui_file_path}")
            logger.debug(f"Icon path: {icon_path}")
            
            # Create main layout
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(main_layout)
            
            # Load UI file
            ui_file = QFile(ui_file_path)
            if not ui_file.open(QIODevice.ReadOnly):
                error_msg = f"Cannot open {ui_file_path}: {ui_file.errorString()}"
                logger.error(error_msg)
                QMessageBox.critical(self, "Error", error_msg)
                raise RuntimeError(error_msg)
            
            # Load UI using QUiLoader
            loader = QUiLoader()
            self.ui_widget = loader.load(ui_file)
            ui_file.close()
            
            if not self.ui_widget:
                error_msg = f"Failed to load UI file: {loader.errorString()}"
                logger.error(error_msg)
                QMessageBox.critical(self, "Error", error_msg)
                raise RuntimeError(error_msg)
            
            # Add widget to layout
            main_layout.addWidget(self.ui_widget)
            
            # Get UI controls
            self.line_edit_id = self.ui_widget.findChild(QLineEdit, "line_edit_id")
            self.line_edit_sn = self.ui_widget.findChild(QLineEdit, "line_edit_sn")
            self.push_button_login = self.ui_widget.findChild(QPushButton, "push_button_login")
            self.push_button_cancel = self.ui_widget.findChild(QPushButton, "push_button_cancel")
            
            if not all([self.line_edit_id, self.line_edit_sn, self.push_button_login, self.push_button_cancel]):
                error_msg = "Failed to find all required UI controls"
                logger.error(error_msg)
                QMessageBox.critical(self, "Error", error_msg)
                raise RuntimeError(error_msg)
            
            # Set UI properties
            self.setWindowTitle("Login")
            self.resize(self.ui_widget.size())
            
            # Set application icon
            if os.path.exists(icon_path):
                from PySide6.QtGui import QIcon
                self.setWindowIcon(QIcon(icon_path))
                logger.debug("Login dialog icon set successfully")
            else:
                logger.warning(f"Icon file not found: {icon_path}")
            
            # Set default values
            self.line_edit_id.setText("rdtest")
            self.line_edit_sn.setText("CQ112233")
            
            logger.debug("Login UI loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load UI: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load UI: {str(e)}")
            raise
    
    def _setup_connections(self):
        """Setup signal connections"""
        try:
            # Connect button events
            self.push_button_login.clicked.connect(self._on_login_clicked)
            self.push_button_cancel.clicked.connect(self.reject)
            
            # Connect text changed events for validation
            self.line_edit_id.textChanged.connect(self._validate_inputs)
            self.line_edit_sn.textChanged.connect(self._validate_inputs)
            
            # Initial validation
            self._validate_inputs()
            
            logger.debug("Login signals connected")
        except Exception as e:
            logger.error(f"Failed to connect login signals: {str(e)}", exc_info=True)
    
    def _validate_inputs(self):
        """Enable login button only when both fields have text"""
        has_id = bool(self.line_edit_id.text().strip())
        has_sn = bool(self.line_edit_sn.text().strip())
        self.push_button_login.setEnabled(has_id and has_sn)
    
    def _on_login_clicked(self):
        """Handle login button click"""
        # Get input values
        user_id = self.line_edit_id.text().strip()
        user_sn = self.line_edit_sn.text().strip()
        
        logger.info(f"Login attempt with ID: {user_id}, S/N: {user_sn}")
        
        # Show loading state
        self.push_button_login.setEnabled(False)
        self.push_button_login.setText("Logging in...")
        QApplication.processEvents()
        
        try:
            # Simple validation: consider login successful if both fields have content
            if user_id and user_sn:
                logger.info(f"User '{user_id}' logged in successfully")
                self.login_successful = True
                self.accept()
            else:
                logger.warning(f"Failed login attempt - empty fields")
                QMessageBox.warning(self, "Login Failed", "Please enter ID and S/N")
                self.push_button_login.setEnabled(True)
                self.push_button_login.setText("Login")
        except Exception as e:
            logger.error(f"Login processing error: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Login error: {str(e)}")
            self.push_button_login.setEnabled(True)
            self.push_button_login.setText("Login")
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        # Trigger login when Enter key is pressed
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.push_button_login.isEnabled():
                self._on_login_clicked()
        else:
            super().keyPressEvent(event)


# Test code
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = LoginDialog()
    result = dialog.exec()
    print(f"Dialog result: {result}, Login successful: {dialog.login_successful}")
    sys.exit(0) 