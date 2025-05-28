"""
HW/SW Configuration Manager
Manage the HW/SW configuration of the Hydra
"""
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QHBoxLayout, QWidget
from PySide6.QtCore import QObject, Signal, Qt
from util.logger import logger


class HWSWConfigManager(QObject):
    """HW/SW Configuration Manager"""
    
    # Configuration update signal
    config_updated = Signal(str, str, str)  # component_id, field_type, new_value
    
    def __init__(self):
        super().__init__()
        self.table_widget = None
        self.edit_dialog_class = None
        
        # Default configuration data
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
        Set UI components
        
        Args:
            table_widget: Configuration table component
            edit_dialog_class: Edit dialog class
        """
        self.table_widget = table_widget
        self.edit_dialog_class = edit_dialog_class
        
        if self.table_widget:
            self._setup_table()
            self._populate_table()
    
    def _setup_table(self):
        """Set table properties"""
        # Set table column widths
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Component column
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Part Number column
        header.setSectionResizeMode(2, QHeaderView.Stretch)          # Serial Number column
        header.setSectionResizeMode(3, QHeaderView.Stretch)          # Note column
        
        # Set table height to display all 6 components
        header_height = 35  # Header row height
        row_height = 50     # Row height
        total_rows = 6      # Total 6 components
        table_height = header_height + (total_rows * row_height) + 10  # Additional margin
        
        # Set table fixed height to display all components
        self.table_widget.setFixedHeight(table_height)
        
        # Disable internal scroll bars
        self.table_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Set table style
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
        """Fill table data"""
        self.table_widget.setRowCount(len(self.config_data))
        
        for row, config in enumerate(self.config_data):
            # Component column - Display only text
            component_item = QTableWidgetItem(config["component"])
            self.table_widget.setItem(row, 0, component_item)
            
            # Part Number column - Contains text and edit button
            part_number_widget = self._create_editable_cell(
                config["part_number"], 
                config["id"], 
                "part_number"
            )
            self.table_widget.setCellWidget(row, 1, part_number_widget)
            
            # Serial Number column - Contains text and edit button
            serial_number_widget = self._create_editable_cell(
                config["serial_number"],
                config["id"], 
                "serial_number"
            )
            self.table_widget.setCellWidget(row, 2, serial_number_widget)
            
            # Note column - Contains text and edit button
            note_widget = self._create_editable_cell(
                config["note"],
                config["id"], 
                "note"
            )
            self.table_widget.setCellWidget(row, 3, note_widget)
        
        # Set row height
        for row in range(self.table_widget.rowCount()):
            self.table_widget.setRowHeight(row, 50)
    
    def _create_editable_cell(self, value: str, component_id: str, field_type: str):
        """
        Create editable cell component
        
        Args:
            value: Display value
            component_id: Component ID
            field_type: Field type (part_number or serial_number)
            
        Returns:
            QWidget with text and edit button
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        
        # Value label
        value_item = QTableWidgetItem(value)
        value_item.setData(1000, value)  # Store original value
        
        # Edit button
        edit_button = QPushButton("✎")
        edit_button.setProperty("class", "config-edit-button")
        edit_button.setMaximumSize(24, 24)
        edit_button.setMinimumSize(24, 24)
        edit_button.clicked.connect(
            lambda: self._on_edit_clicked(component_id, field_type, value)
        )
        
        # Display original value as text
        from PySide6.QtWidgets import QLabel
        value_label = QLabel(value)
        value_label.setStyleSheet("color: #4FC3F7; font-weight: bold;")
        
        layout.addWidget(value_label)
        layout.addStretch()
        layout.addWidget(edit_button)
        
        # Save reference for later updates
        widget.value_label = value_label
        widget.component_id = component_id
        widget.field_type = field_type
        
        return widget
    
    def _on_edit_clicked(self, component_id: str, field_type: str, current_value: str):
        """
        Handle edit button click event
        
        Args:
            component_id: Component ID
            field_type: Field type
            current_value: Current value
        """
        if not self.edit_dialog_class:
            logger.warning("Edit dialog class not set")
            return
        
        # Determine dialog title and label
        if field_type == "part_number":
            title = "Edit Part Number"
            label = "Enter new part number:"
        elif field_type == "serial_number":
            title = "Edit Serial Number" 
            label = "Enter new serial number:"
        else:  # note
            title = "Edit Note"
            label = "Enter note:"
        
        # Display edit dialog
        dialog = self.edit_dialog_class(
            title=title,
            label_text=label,
            initial_text=current_value
        )
        
        if dialog.exec():
            new_value = dialog.get_text().strip()
            if new_value and new_value != current_value:
                self._update_config_value(component_id, field_type, new_value)
                # Send update signal
                self.config_updated.emit(component_id, field_type, new_value)
                logger.info(f"Updated {component_id} {field_type}: {current_value} -> {new_value}")
    
    def _update_config_value(self, component_id: str, field_type: str, new_value: str):
        """
        Update config value and refresh UI
        
        Args:
            component_id: Component ID
            field_type: Field type
            new_value: New value
        """
        # Update internal data
        for config in self.config_data:
            if config["id"] == component_id:
                config[field_type] = new_value
                break
        
        # Update table display
        self._refresh_table_display(component_id, field_type, new_value)
    
    def _refresh_table_display(self, component_id: str, field_type: str, new_value: str):
        """
        Refresh table display
        
        Args:
            component_id: Component ID
            field_type: Field type
            new_value: New value
        """
        # Determine column index
        if field_type == "part_number":
            col_index = 1
        elif field_type == "serial_number":
            col_index = 2
        else:  # note
            col_index = 3
        
        # Find corresponding row
        for row in range(self.table_widget.rowCount()):
            widget = self.table_widget.cellWidget(row, col_index)
            if widget and hasattr(widget, 'component_id') and widget.component_id == component_id:
                if hasattr(widget, 'value_label'):
                    widget.value_label.setText(new_value)
                break
    
    def get_config_data(self):
        """Get current config data"""
        return self.config_data.copy()
    
    def set_config_data(self, new_data: list):
        """
        Set new config data
        
        Args:
            new_data: New config data list
        """
        self.config_data = new_data.copy()
        if self.table_widget:
            self._populate_table()
    
    def export_config(self):
        """Export config data"""
        return {
            "hw_sw_configuration": self.config_data
        } 