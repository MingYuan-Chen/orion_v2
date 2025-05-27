"""
HW/SW Configuration Manager
管理硬件和軟件配置信息的顯示和編輯
"""
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QHBoxLayout, QWidget
from PySide6.QtCore import QObject, Signal, Qt
from util.logger import logger


class HWSWConfigManager(QObject):
    """HW/SW Configuration 管理器"""
    
    # 配置更新信號
    config_updated = Signal(str, str, str)  # component_id, field_type, new_value
    
    def __init__(self):
        super().__init__()
        self.table_widget = None
        self.edit_dialog_class = None
        
        # 預設配置數據
        self.config_data = [
            {
                "id": "touch",
                "component": "Touch",
                "part_number": "81B156YF3A3F-VR", 
                "serial_number": "TP78422397",
                "note": "PSC Customized"
            },
            {
                "id": "display",
                "component": "Display",
                "part_number": "931156VD16F-00",
                "serial_number": "YD8374192",
                "note": "TIANMA TM156VDSG16-00"
            },
            {
                "id": "main_board",
                "component": "Main Board",
                "part_number": "99EMHYDRA00A3",
                "serial_number": "HYFHD24160599",
                "note": ""
            },
            {
                "id": "power_board", 
                "component": "Power Board",
                "part_number": "PWR-X1C-90W",
                "serial_number": "PB7384723",
                "note": ""
            },
            {
                "id": "edp_board",
                "component": "eDP Board", 
                "part_number": "99GLCNB000F",
                "serial_number": "CM98437652",
                "note": ""
            },
            {
                "id": "battery",
                "component": "Battery",
                "part_number": "32LBN20130F",
                "serial_number": "240500734",
                "note": "Li-ion Battery 2S1P 3350mAh"
            }
        ]
    
    def set_ui_components(self, table_widget: QTableWidget, edit_dialog_class=None):
        """
        設置 UI 組件
        
        Args:
            table_widget: 配置表格組件
            edit_dialog_class: 編輯對話框類別
        """
        self.table_widget = table_widget
        self.edit_dialog_class = edit_dialog_class
        
        if self.table_widget:
            self._setup_table()
            self._populate_table()
    
    def _setup_table(self):
        """設置表格屬性"""
        # 設置表格列寬
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Component 列
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Part Number 列
        header.setSectionResizeMode(2, QHeaderView.Stretch)          # Serial Number 列
        header.setSectionResizeMode(3, QHeaderView.Stretch)          # Note 列
        
        # 設置表格高度以顯示所有 6 個組件
        header_height = 35  # 標題行高度
        row_height = 50     # 每行的高度
        total_rows = 6      # 總共 6 個組件
        table_height = header_height + (total_rows * row_height) + 10  # 額外的邊距
        
        # 設置表格的固定高度以顯示所有組件
        self.table_widget.setFixedHeight(table_height)
        
        # 禁用表格內部滾動條
        self.table_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 設置表格樣式
        self.table_widget.setStyleSheet("""
            QTableWidget {
                background-color: #252526;
                color: white;
                gridline-color: #3F3F46;
                border: 1px solid #3F3F46;
            }
            QTableWidget::item {
                background-color: #252526;
                padding: 8px;
            }
            QTableWidget::item:alternate {
                background-color: #2D2D30;
            }
            QTableWidget::item:selected {
                background-color: #0078D7;
            }
            QHeaderView::section {
                background-color: #333337;
                color: white;
                padding: 8px;
                border: 1px solid #3F3F46;
                font-weight: bold;
            }
            QPushButton.config-edit-button {
                background-color: #444444;
                color: white;
                border: none;
                padding: 4px;
                border-radius: 3px;
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
                font-size: 12px;
            }
            QPushButton.config-edit-button:hover {
                background-color: #555555;
            }
            QPushButton.config-edit-button:pressed {
                background-color: #666666;
            }
            /* 滾動條樣式 */
            QScrollBar:vertical {
                background: #333333;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                border-radius: 6px;
                min-height: 20px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666666;
            }
            QScrollBar::handle:vertical:pressed {
                background: #777777;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
            QScrollBar:horizontal {
                background: #333333;
                height: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background: #555555;
                border-radius: 6px;
                min-width: 20px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #666666;
            }
            QScrollBar::handle:horizontal:pressed {
                background: #777777;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background: none;
            }
        """)
    
    def _populate_table(self):
        """填充表格數據"""
        self.table_widget.setRowCount(len(self.config_data))
        
        for row, config in enumerate(self.config_data):
            # Component 列 - 只顯示文字
            component_item = QTableWidgetItem(config["component"])
            self.table_widget.setItem(row, 0, component_item)
            
            # Part Number 列 - 包含文字和編輯按鈕
            part_number_widget = self._create_editable_cell(
                config["part_number"], 
                config["id"], 
                "part_number"
            )
            self.table_widget.setCellWidget(row, 1, part_number_widget)
            
            # Serial Number 列 - 包含文字和編輯按鈕
            serial_number_widget = self._create_editable_cell(
                config["serial_number"],
                config["id"], 
                "serial_number"
            )
            self.table_widget.setCellWidget(row, 2, serial_number_widget)
            
            # Note 列 - 包含文字和編輯按鈕
            note_widget = self._create_editable_cell(
                config["note"],
                config["id"], 
                "note"
            )
            self.table_widget.setCellWidget(row, 3, note_widget)
        
        # 設置行高
        for row in range(self.table_widget.rowCount()):
            self.table_widget.setRowHeight(row, 50)
    
    def _create_editable_cell(self, value: str, component_id: str, field_type: str):
        """
        創建可編輯的單元格組件
        
        Args:
            value: 顯示值
            component_id: 組件ID
            field_type: 字段類型 (part_number 或 serial_number)
            
        Returns:
            包含文字和編輯按鈕的 QWidget
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        
        # 值標籤
        value_item = QTableWidgetItem(value)
        value_item.setData(1000, value)  # 存儲原始值
        
        # 編輯按鈕
        edit_button = QPushButton("✎")
        edit_button.setProperty("class", "config-edit-button")
        edit_button.setMaximumSize(24, 24)
        edit_button.setMinimumSize(24, 24)
        edit_button.clicked.connect(
            lambda: self._on_edit_clicked(component_id, field_type, value)
        )
        
        # 將原始值顯示為文字
        from PySide6.QtWidgets import QLabel
        value_label = QLabel(value)
        value_label.setStyleSheet("color: #4FC3F7; font-weight: bold;")
        
        layout.addWidget(value_label)
        layout.addStretch()
        layout.addWidget(edit_button)
        
        # 保存引用以便後續更新
        widget.value_label = value_label
        widget.component_id = component_id
        widget.field_type = field_type
        
        return widget
    
    def _on_edit_clicked(self, component_id: str, field_type: str, current_value: str):
        """
        處理編輯按鈕點擊事件
        
        Args:
            component_id: 組件ID
            field_type: 字段類型
            current_value: 當前值
        """
        if not self.edit_dialog_class:
            logger.warning("Edit dialog class not set")
            return
        
        # 確定對話框標題和標籤
        if field_type == "part_number":
            title = "Edit Part Number"
            label = "Enter new part number:"
        elif field_type == "serial_number":
            title = "Edit Serial Number" 
            label = "Enter new serial number:"
        else:  # note
            title = "Edit Note"
            label = "Enter note:"
        
        # 顯示編輯對話框
        dialog = self.edit_dialog_class(
            title=title,
            label_text=label,
            initial_text=current_value
        )
        
        if dialog.exec():
            new_value = dialog.get_text().strip()
            if new_value and new_value != current_value:
                self._update_config_value(component_id, field_type, new_value)
                # 發送更新信號
                self.config_updated.emit(component_id, field_type, new_value)
                logger.info(f"Updated {component_id} {field_type}: {current_value} -> {new_value}")
    
    def _update_config_value(self, component_id: str, field_type: str, new_value: str):
        """
        更新配置值並刷新 UI
        
        Args:
            component_id: 組件ID
            field_type: 字段類型
            new_value: 新值
        """
        # 更新內部數據
        for config in self.config_data:
            if config["id"] == component_id:
                config[field_type] = new_value
                break
        
        # 更新表格顯示
        self._refresh_table_display(component_id, field_type, new_value)
    
    def _refresh_table_display(self, component_id: str, field_type: str, new_value: str):
        """
        刷新表格顯示
        
        Args:
            component_id: 組件ID
            field_type: 字段類型
            new_value: 新值
        """
        # 確定列索引
        if field_type == "part_number":
            col_index = 1
        elif field_type == "serial_number":
            col_index = 2
        else:  # note
            col_index = 3
        
        # 找到對應的行
        for row in range(self.table_widget.rowCount()):
            widget = self.table_widget.cellWidget(row, col_index)
            if widget and hasattr(widget, 'component_id') and widget.component_id == component_id:
                if hasattr(widget, 'value_label'):
                    widget.value_label.setText(new_value)
                break
    
    def get_config_data(self):
        """獲取當前配置數據"""
        return self.config_data.copy()
    
    def set_config_data(self, new_data: list):
        """
        設置新的配置數據
        
        Args:
            new_data: 新的配置數據列表
        """
        self.config_data = new_data.copy()
        if self.table_widget:
            self._populate_table()
    
    def export_config(self):
        """導出配置數據"""
        return {
            "hw_sw_configuration": self.config_data
        } 