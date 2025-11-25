from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QLineEdit, QTableWidget, QTableWidgetItem, QPushButton, 
    QHeaderView, QMessageBox, QInputDialog
)
from PySide6.QtCore import Slot, Qt
from core.view_models.device_view_model import DeviceViewModel
from typing import Dict, List

class HWConfigView(QWidget):
    def __init__(self, view_model: DeviceViewModel, parent: QWidget = None):
        super().__init__(parent)
        self._vm = view_model
        self.setWindowTitle("Hardware Configuration")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("font-size: 16px;") # Increase overall font size
        
        self._setup_ui()
        self._setup_bindings()
        
        # Initial population if data exists
        self.on_hw_config_list_changed()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # --- Top Section: Config Selection ---
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Select Config:"))
        self.config_combo = QComboBox()
        # self.config_combo.currentIndexChanged.connect(self.on_config_selected) # Disable auto-load for now
        top_layout.addWidget(self.config_combo, 1)
        
        self.load_button = QPushButton("Load")
        self.load_button.clicked.connect(self.on_load_clicked)
        top_layout.addWidget(self.load_button)
        
        main_layout.addLayout(top_layout)

        # --- Middle Section: Platform Info ---
        info_layout = QHBoxLayout()
        
        self.model_input = self._create_labeled_input("Platform Model:", info_layout)
        self.serial_input = self._create_labeled_input("Platform Serial:", info_layout)
        # self.config_name_input = self._create_labeled_input("Config Name:", info_layout) # Removed as requested
        
        main_layout.addLayout(info_layout)

        # --- Bottom Section: Components Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Component", "Part Number", "Serial Number", "Note"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setColumnHidden(0, True) # Hide ID column as requested
        main_layout.addWidget(self.table)

        # --- Footer Section: Actions ---
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.on_save_clicked)
        footer_layout.addWidget(self.save_button)
        
        self.save_as_button = QPushButton("Save As...")
        self.save_as_button.clicked.connect(self.on_save_as_clicked)
        footer_layout.addWidget(self.save_as_button)
        
        main_layout.addLayout(footer_layout)

    def _create_labeled_input(self, label_text: str, layout: QHBoxLayout) -> QLineEdit:
        layout.addWidget(QLabel(label_text))
        line_edit = QLineEdit()
        layout.addWidget(line_edit)
        return line_edit

    def _setup_bindings(self):
        self._vm.hw_config_list_changed.connect(self.on_hw_config_list_changed)
        self._vm.current_hw_config_changed.connect(self.on_current_hw_config_changed)
        self._vm.hw_config_reset.connect(self.on_hw_config_reset)

    @Slot()
    def on_hw_config_list_changed(self):
        current_text = self.config_combo.currentText()
        self.config_combo.blockSignals(True)
        self.config_combo.clear()
        self.config_combo.addItems(self._vm.hw_config_list)
        
        # Restore selection if possible
        index = self.config_combo.findText(current_text)
        if index >= 0:
            self.config_combo.setCurrentIndex(index)
        
        self.config_combo.blockSignals(False)

    @Slot()
    def on_load_clicked(self):
        filename = self.config_combo.currentText()
        if filename:
            self._vm.load_hw_config(filename)

    # @Slot(int)
    # def on_config_selected(self, index: int):
    #     filename = self.config_combo.itemText(index)
    #     if filename:
    #         self._vm.load_hw_config(filename)

    @Slot()
    def on_current_hw_config_changed(self):
        config = self._vm.current_hw_config
        if not config:
            return

        self.model_input.setText(config.get("platform_model", ""))
        self.serial_input.setText(config.get("platform_serial", ""))
        # self.config_name_input.setText(config.get("config_name", ""))

        components = config.get("components", [])
        self.table.setRowCount(len(components))
        
        for row, comp in enumerate(components):
            self.table.setItem(row, 0, QTableWidgetItem(comp.get("id", "")))
            self.table.setItem(row, 1, QTableWidgetItem(comp.get("component", "")))
            self.table.setItem(row, 2, QTableWidgetItem(comp.get("part_number", "")))
            self.table.setItem(row, 3, QTableWidgetItem(comp.get("serial_number", "")))
            self.table.setItem(row, 4, QTableWidgetItem(comp.get("note", "")))

    def _collect_data(self) -> Dict:
        components = []
        for row in range(self.table.rowCount()):
            comp = {
                "id": self.table.item(row, 0).text(),
                "component": self.table.item(row, 1).text(),
                "part_number": self.table.item(row, 2).text(),
                "serial_number": self.table.item(row, 3).text(),
                "note": self.table.item(row, 4).text()
            }
            components.append(comp)

        return {
            "platform_name": self._vm.platform_name.lower(), # Assuming platform name doesn't change
            "platform_model": self.model_input.text(),
            "platform_serial": self.serial_input.text(),
            # "config_name": self.config_name_input.text(),
            "created_date": self._vm.current_hw_config.get("created_date", ""), # Preserve date
            "components": components
        }

    @Slot()
    def on_save_clicked(self):
        filename = self.config_combo.currentText()
        if not filename:
            QMessageBox.warning(self, "Warning", "No configuration selected.")
            return
            
        data = self._collect_data()
        self._vm.save_hw_config(filename, data)
        QMessageBox.information(self, "Success", f"Saved to {filename}")

    @Slot()
    def on_save_as_clicked(self):
        filename, ok = QInputDialog.getText(self, "Save As", "Enter new filename (e.g. argo_new.json):")
        if ok and filename:
            if not filename.endswith(".json"):
                filename += ".json"
            
            data = self._collect_data()
            self._vm.save_hw_config(filename, data)
            QMessageBox.information(self, "Success", f"Saved to {filename}")
            
            # Select the new file in combo box (list refresh happens via signal)
            # We might need to wait for list update, but usually it's fast.

    @Slot()
    def on_hw_config_reset(self):
        self.config_combo.clear()
        self.model_input.clear()
        self.serial_input.clear()
        self.table.setRowCount(0)

    def closeEvent(self, event):
        self.hide()
        event.ignore()
