"""
Firmware & OS Information Manager
Manage the display and editing of firmware and OS information
"""
from PySide6.QtWidgets import QLabel, QPushButton
from PySide6.QtCore import QObject, Signal
from util.logger import logger


class FirmwareOSManager(QObject):
    """Firmware & OS Information Manager"""
    
    # Information update signal
    info_updated = Signal(str, str)  # field_name, new_value
    
    def __init__(self):
        super().__init__()
        self.ui_components = {}
        self.edit_dialog_class = None
        
        # Default information data
        self.firmware_os_data = {
            "uboot_version": "...",
            "pic_firmware": "...", 
            "os_version": "...",
            "kernel_version": "..."
        }
        
        # Field label mapping
        self.field_labels = {
            "uboot_version": "U-Boot Version",
            "pic_firmware": "PIC Firmware",
            "os_version": "OS Version", 
            "kernel_version": "Kernel"
        }
    
    def set_ui_components(self, window, edit_dialog_class=None):
        """
        Set UI components
        
        Args:
            window: Main window object
            edit_dialog_class: Edit dialog class
        """
        self.edit_dialog_class = edit_dialog_class
        
        # Set UI components reference
        self.ui_components = {
            "uboot_version": {
                "value_label": window.value_uboot_version,
                "edit_button": window.button_edit_uboot_version
            },
            "pic_firmware": {
                "value_label": window.value_pic_firmware,
                "edit_button": window.button_edit_pic_firmware
            },
            "os_version": {
                "value_label": window.value_os_version,
                "edit_button": window.button_edit_os_version
            },
            "kernel_version": {
                "value_label": window.value_kernel,
                "edit_button": window.button_edit_kernel
            }
        }
        
        # Connect edit button signal
        self._connect_edit_buttons()
        
        # Initialize display
        self._update_display()
    
    def _connect_edit_buttons(self):
        """Connect edit button click signal"""
        for field_name, components in self.ui_components.items():
            edit_button = components["edit_button"]
            edit_button.clicked.connect(
                lambda checked, field=field_name: self._on_edit_clicked(field)
            )
    
    def _on_edit_clicked(self, field_name: str):
        """
        Handle edit button click event
        
        Args:
            field_name: Field name
        """
        if not self.edit_dialog_class:
            logger.warning("Edit dialog class not set")
            return
        
        current_value = self.firmware_os_data.get(field_name, "")
        field_label = self.field_labels.get(field_name, field_name)
        
        # Display edit dialog
        dialog = self.edit_dialog_class(
            title=f"Edit {field_label}",
            label_text=f"Enter new {field_label.lower()}:",
            initial_text=current_value
        )
        
        if dialog.exec():
            new_value = dialog.get_text().strip()
            if new_value and new_value != current_value:
                self._update_field_value(field_name, new_value)
                # Send update signal
                self.info_updated.emit(field_name, new_value)
                logger.info(f"Updated {field_label}: {current_value} -> {new_value}")
    
    def _update_field_value(self, field_name: str, new_value: str):
        """
        Update field value and refresh UI
        
        Args:
            field_name: Field name
            new_value: New value
        """
        # Update internal data
        self.firmware_os_data[field_name] = new_value
        
        # Update display
        if field_name in self.ui_components:
            value_label = self.ui_components[field_name]["value_label"]
            value_label.setText(new_value)
    
    def _update_display(self):
        """Update all field display"""
        for field_name, value in self.firmware_os_data.items():
            if field_name in self.ui_components:
                value_label = self.ui_components[field_name]["value_label"]
                value_label.setText(value)
    
    def get_firmware_os_data(self):
        """Get current firmware and OS information"""
        return self.firmware_os_data.copy()
    
    def set_firmware_os_data(self, new_data: dict):
        """
        Set new firmware and OS information
        
        Args:
            new_data: New information data dictionary
        """
        self.firmware_os_data.update(new_data)
        self._update_display()
    
    def export_data(self):
        """Export firmware and OS information"""
        return {
            "firmware_os_information": self.firmware_os_data
        } 