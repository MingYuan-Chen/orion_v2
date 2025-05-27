"""
Firmware & OS Information Manager
管理韌體和作業系統資訊的顯示和編輯
"""
from PySide6.QtWidgets import QLabel, QPushButton
from PySide6.QtCore import QObject, Signal
from util.logger import logger


class FirmwareOSManager(QObject):
    """Firmware & OS Information 管理器"""
    
    # 資訊更新信號
    info_updated = Signal(str, str)  # field_name, new_value
    
    def __init__(self):
        super().__init__()
        self.ui_components = {}
        self.edit_dialog_class = None
        
        # 預設資訊數據
        self.firmware_os_data = {
            "uboot_version": "2025.03",
            "pic_firmware": "v2.4.8", 
            "os_version": "Linux gemini 4.1.15",
            "kernel": "6.2.0-36-generic"
        }
        
        # 欄位標籤映射
        self.field_labels = {
            "uboot_version": "U-Boot Version",
            "pic_firmware": "PIC Firmware",
            "os_version": "OS Version", 
            "kernel": "Kernel"
        }
    
    def set_ui_components(self, window, edit_dialog_class=None):
        """
        設置 UI 組件
        
        Args:
            window: 主窗口物件
            edit_dialog_class: 編輯對話框類別
        """
        self.edit_dialog_class = edit_dialog_class
        
        # 設置 UI 組件引用
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
            "kernel": {
                "value_label": window.value_kernel,
                "edit_button": window.button_edit_kernel
            }
        }
        
        # 連接編輯按鈕信號
        self._connect_edit_buttons()
        
        # 初始化顯示
        self._update_display()
    
    def _connect_edit_buttons(self):
        """連接編輯按鈕的點擊信號"""
        for field_name, components in self.ui_components.items():
            edit_button = components["edit_button"]
            edit_button.clicked.connect(
                lambda checked, field=field_name: self._on_edit_clicked(field)
            )
    
    def _on_edit_clicked(self, field_name: str):
        """
        處理編輯按鈕點擊事件
        
        Args:
            field_name: 欄位名稱
        """
        if not self.edit_dialog_class:
            logger.warning("Edit dialog class not set")
            return
        
        current_value = self.firmware_os_data.get(field_name, "")
        field_label = self.field_labels.get(field_name, field_name)
        
        # 顯示編輯對話框
        dialog = self.edit_dialog_class(
            title=f"Edit {field_label}",
            label_text=f"Enter new {field_label.lower()}:",
            initial_text=current_value
        )
        
        if dialog.exec():
            new_value = dialog.get_text().strip()
            if new_value and new_value != current_value:
                self._update_field_value(field_name, new_value)
                # 發送更新信號
                self.info_updated.emit(field_name, new_value)
                logger.info(f"Updated {field_label}: {current_value} -> {new_value}")
    
    def _update_field_value(self, field_name: str, new_value: str):
        """
        更新欄位值並刷新 UI
        
        Args:
            field_name: 欄位名稱
            new_value: 新值
        """
        # 更新內部數據
        self.firmware_os_data[field_name] = new_value
        
        # 更新顯示
        if field_name in self.ui_components:
            value_label = self.ui_components[field_name]["value_label"]
            value_label.setText(new_value)
    
    def _update_display(self):
        """更新所有欄位的顯示"""
        for field_name, value in self.firmware_os_data.items():
            if field_name in self.ui_components:
                value_label = self.ui_components[field_name]["value_label"]
                value_label.setText(value)
    
    def get_firmware_os_data(self):
        """獲取當前韌體和作業系統資訊"""
        return self.firmware_os_data.copy()
    
    def set_firmware_os_data(self, new_data: dict):
        """
        設置新的韌體和作業系統資訊
        
        Args:
            new_data: 新的資訊數據字典
        """
        self.firmware_os_data.update(new_data)
        self._update_display()
    
    def export_data(self):
        """導出韌體和作業系統資訊"""
        return {
            "firmware_os_information": self.firmware_os_data
        } 