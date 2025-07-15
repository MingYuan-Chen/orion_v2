"""
HW/SW Configuration Manager
Manage the HW/SW configuration of the Hydra
"""
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QHBoxLayout, QWidget, QComboBox, QLabel, QVBoxLayout, QFileDialog, QMessageBox, QDialog
from PySide6.QtCore import QObject, Signal, Qt
from util.logger import logger
import json
import os
from datetime import datetime


class HWSWConfigManager(QObject):
    """HW/SW Configuration Manager"""
    
    # Configuration update signal
    config_updated = Signal(str, str, str)  # component_id, field_type, new_value
    
    def __init__(self):
        super().__init__()
        self.table_widget = None
        self.edit_dialog_class = None
        self.save_button = None
        self.load_button = None
        self.config_combo = None
        self.platform_name = None
        
        # 确保 hw_config 目录存在
        self.config_dir = "hw_config"
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            logger.info(f"Created directory: {self.config_dir}")
        
        # Default configuration data - 改为 "--"
        self.config_data = [
            {
                "id": "touch",
                "component": "Touch",
                "part_number": "--", 
                "serial_number": "--",
                "note": "--"
            },
            {
                "id": "display",
                "component": "Display",
                "part_number": "--",
                "serial_number": "--",
                "note": "--"
            },
            {
                "id": "main_board",
                "component": "Main Board",
                "part_number": "--",
                "serial_number": "--",
                "note": "--"
            },
            {
                "id": "edp_board",
                "component": "eDP Board", 
                "part_number": "--",
                "serial_number": "--",
                "note": "--"
            },
            {
                "id": "battery",
                "component": "Battery",
                "part_number": "--",
                "serial_number": "--",
                "note": "--"
            }
        ]
    
    def set_platform_name(self, platform_name: str):
        """set platform name"""
        self.platform_name = platform_name
        self._update_config_combo()
    
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
            self._add_config_buttons()
            self._populate_table()
    
    def _add_config_buttons(self):
        """add config buttons and dropdown menu"""
        # get the parent widget of the table widget (groupBox_hw_components)
        parent_widget = self.table_widget.parent()
        if not parent_widget:
            logger.error("Cannot find parent widget for table")
            return
        
        # get the existing layout
        layout = parent_widget.layout()
        if not layout:
            logger.error("Cannot find layout for parent widget")
            return
        
        # create button container
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(5, 5, 5, 5)
        
        # Save config button
        self.save_button = QPushButton("Save Config")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1C97EA;
            }
            QPushButton:pressed {
                background-color: #00559F;
            }
        """)
        self.save_button.clicked.connect(self._on_save_config)
        
        # Load config button
        self.load_button = QPushButton("Load Config")
        self.load_button.setStyleSheet("""
            QPushButton {
                background-color: #00A86B;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00C878;
            }
            QPushButton:pressed {
                background-color: #008754;
            }
        """)
        self.load_button.clicked.connect(self._on_load_config)
        
        # config file dropdown menu
        self.config_combo = QComboBox()
        self.config_combo.setStyleSheet("""
            QComboBox {
                background-color: #3E3E3E;
                color: white;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                min-width: 200px;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #555555;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: 3px solid transparent;
                border-top-color: white;
                top: 1px;
            }
            QComboBox QAbstractItemView {
                background-color: #3E3E3E;
                color: white;
                border: 1px solid #555555;
                selection-background-color: #0078D7;
            }
        """)
        
        # create Config label
        config_label = QLabel("Config:")
        config_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: transparent;
                padding: 8px;
                font-weight: bold;
            }
        """)
        
        # add to layout
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(config_label)
        button_layout.addWidget(self.config_combo)
        button_layout.addStretch()  # add stretch
        
        # insert button container before the table
        layout.insertWidget(0, button_container)
        
        # update config dropdown menu
        self._update_config_combo()
    
    def _setup_table(self):
        """Set table properties"""
        # Set table column widths
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Component column
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Part Number column
        header.setSectionResizeMode(2, QHeaderView.Stretch)          # Serial Number column
        header.setSectionResizeMode(3, QHeaderView.Stretch)          # Note column
        
        # Set table height to display all 5 components
        header_height = 35  # Header row height
        row_height = 50     # Row height
        total_rows = 5      # Total 5 components
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
            /* scroll bar style */
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

    def _create_editable_cell(self, value: str, component_id: str, field_type: str) -> QWidget:
        """
        Create editable cell with value and edit button
        
        Args:
            value: Cell value
            component_id: Component ID
            field_type: Field type
            
        Returns:
            QWidget with value and edit button
        """
        # Create container widget
        container = QWidget()
        container.component_id = component_id
        container.field_type = field_type
        
        # Create horizontal layout
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(5)
        
        # Create value label
        value_label = QLabel(value)
        value_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: transparent;
                padding: 4px;
                border: 1px solid transparent;
                border-radius: 3px;
            }
        """)
        
        # Create edit button
        edit_button = QPushButton("✎")
        edit_button.setProperty("class", "config-edit-button")
        edit_button.setToolTip("Edit value")
        edit_button.clicked.connect(
            lambda: self._on_edit_value(component_id, field_type, value_label)
        )
        
        # Add to layout
        layout.addWidget(value_label)
        layout.addStretch()
        layout.addWidget(edit_button)
        
        # Store reference to value label for updates
        container.value_label = value_label
        
        return container
    
    def _on_edit_value(self, component_id: str, field_type: str, value_label: QLabel):
        """
        Handle edit button click
        
        Args:
            component_id: Component ID
            field_type: Field type
            value_label: Value label widget
        """
        if not self.edit_dialog_class:
            logger.warning("Edit dialog class not set")
            return
            
        # Get current value
        current_value = value_label.text()
        
        # Create dialog
        dialog = self.edit_dialog_class(
            title="Edit Value",
            label_text=f"Edit {field_type.replace('_', ' ').title()}:",
            initial_text=current_value
        )
        
        # Show dialog
        if dialog.exec() == QDialog.Accepted:
            new_value = dialog.get_text()
            
            # Update value
            self._update_config_value(component_id, field_type, new_value)
            
            # Emit signal
            self.config_updated.emit(component_id, field_type, new_value)
    
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
    
    def _on_save_config(self):
        """handle save config button click"""
        if not self.platform_name:
            self._show_error_message("Error", "Cannot get platform name")
            return
        
        # pop up input dialog to let user input config name
        if not self.edit_dialog_class:
            self._show_error_message("Error", "Edit dialog class not set")
            return
        
        dialog = self.edit_dialog_class(
            title="Save Config",
            label_text="Please input config name:",
            initial_text=""
        )
        
        if dialog.exec() == QDialog.Accepted:
            config_name = dialog.get_text().strip()
            if not config_name:
                self._show_error_message("Error", "Config name cannot be empty")
                return
            
            # generate file name
            filename = f"{self.platform_name}_{config_name}.json"
            filepath = os.path.join(self.config_dir, filename)
            
            try:
                # create hw_config directory if it doesn't exist
                if not os.path.exists(self.config_dir):
                    os.makedirs(self.config_dir, exist_ok=True)
                    logger.info(f"Created config directory: {self.config_dir}")
                
                # create config data
                config_data = {
                    "platform_name": self.platform_name,
                    "config_name": config_name,
                    "created_date": datetime.now().isoformat(),
                    "components": self.config_data
                }
                
                # save to file
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Config saved to: {filepath}")
                self._show_info_message("Success", f"Config saved as: {filename}")
                
                # update dropdown menu
                self._update_config_combo()
                
            except Exception as e:
                error_msg = f"Save config failed: {str(e)}"
                logger.error(error_msg)
                self._show_error_message("Error", error_msg)
    
    def _on_load_config(self):
        """handle load config button click"""
        if not self.config_combo:
            return
        
        selected_config = self.config_combo.currentText()
        if not selected_config or selected_config == "No available config":
            self._show_error_message("Error", "Please select a config to load")
            return
        
        # generate file path
        filepath = os.path.join(self.config_dir, selected_config)
        
        try:
            # read config file
            with open(filepath, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # validate config data
            if 'components' not in config_data:
                self._show_error_message("Error", "Config file format is incorrect")
                return
            
            # update config data
            self.config_data = config_data['components']
            
            # repopulate table
            self._populate_table()
            
            logger.info(f"Config loaded from {filepath}")
            self._show_info_message("Success", f"Config loaded: {selected_config}")
            
        except Exception as e:
            error_msg = f"Load config failed: {str(e)}"
            logger.error(error_msg)
            self._show_error_message("Error", error_msg)
    
    def _update_config_combo(self):
        """update config dropdown menu"""
        if not self.config_combo or not self.platform_name:
            return
        
        # clear existing options
        self.config_combo.clear()
        
        try:
            # get all config files
            config_files = []
            if os.path.exists(self.config_dir):
                for filename in os.listdir(self.config_dir):
                    if filename.endswith('.json') and filename.startswith(f"{self.platform_name}_"):
                        config_files.append(filename)
            
            # sort file names
            config_files.sort()
            
            if config_files:
                self.config_combo.addItems(config_files)
                logger.info(f"Found {len(config_files)} {self.platform_name} config files")
            else:
                self.config_combo.addItem("No available config")
                logger.info(f"No {self.platform_name} config files found")
                
        except Exception as e:
            logger.error(f"Update config dropdown menu failed: {str(e)}")
            self.config_combo.addItem("No available config")
    
    def _show_error_message(self, title: str, message: str):
        """show error message"""
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setStyleSheet(self._get_dark_message_box_style())
        msg_box.exec()
    
    def _show_info_message(self, title: str, message: str):
        """show info message"""
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setStyleSheet(self._get_dark_message_box_style())
        msg_box.exec()
    
    def _get_dark_message_box_style(self):
        """get dark message box style"""
        return """
            QMessageBox {
                background-color: #2E2E2E;
                color: white;
            }
            QMessageBox QLabel {
                color: white;
                background-color: transparent;
            }
            QMessageBox QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 6px 15px;
                border-radius: 3px;
                min-width: 60px;
            }
            QMessageBox QPushButton:hover {
                background-color: #1C97EA;
            }
            QMessageBox QPushButton:pressed {
                background-color: #00559F;
            }
        """
    
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