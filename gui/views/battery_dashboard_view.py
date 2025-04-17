#!/usr/bin/env python
"""
battery dashboard view

handle the display of battery dashboard ui and the connection with BatteryMonitorService
"""

import os
import sys
import numpy as np
from collections import deque
from datetime import datetime
from PySide6.QtWidgets import QWidget, QMessageBox, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Slot, QFile, QIODevice, QTimer, Qt
from PySide6.QtUiTools import QUiLoader
from core.services.battery_monitor_service import BatteryMonitorService
from util.logger import logger

# Import matplotlib for charts
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


class BatteryChartCanvas(FigureCanvas):
    """Custom canvas for battery data visualization"""
    
    def __init__(self, parent=None, width=5, height=3, dpi=80):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        
        # set initial axis limits to prevent empty chart issues
        self.axes.set_xlim(0, 10)
        self.axes.set_ylim(0, 100)
        
        self.axes.set_title('Battery Percentage Trend', fontsize=10)
        self.axes.set_xlabel('Time (minutes)', fontsize=8)
        self.axes.set_ylabel('Percentage (%)', fontsize=8)
        self.axes.grid(True)
        
        # adjust layout, reduce margins
        self.fig.tight_layout(pad=1.0)
        
        super(BatteryChartCanvas, self).__init__(self.fig)
        self.setParent(parent)
        
        self.x_data = []
        self.y_data = []
        self.line = None
        
        # set auto scaling policy
        FigureCanvas.setSizePolicy(self,
                                  QSizePolicy.Expanding,
                                  QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
    
    def update_figure(self, new_data):
        if not new_data:
            return
        
        # get battery percentage data
        battery_percent = new_data.get("relative_state")
        if battery_percent is None:
            return  # if no percentage data, do not update chart
        
        # update data
        self.x_data.append(len(self.x_data))
        self.y_data.append(float(battery_percent))
        
        # keep only last 30 data points
        if len(self.x_data) > 30:
            self.x_data = self.x_data[-30:]
            self.y_data = self.y_data[-30:]
        
        # clear current chart
        self.axes.clear()
        
        # draw new data
        self.line, = self.axes.plot(self.x_data, self.y_data, 'b-o')
        
        # set y-axis range, ensure always positive and have reasonable range
        min_y = max(0, min(self.y_data) - 5) if self.y_data else 0
        max_y = min(100, max(self.y_data) + 5) if self.y_data else 100
        self.axes.set_ylim(min_y, max_y)
        
        # set x-axis range
        if self.x_data:
            self.axes.set_xlim(max(0, min(self.x_data)), max(self.x_data) + 1)
        
        # add title and labels again
        self.axes.set_title('Battery Percentage Trend', fontsize=10)
        self.axes.set_xlabel('Time (minutes)', fontsize=8)
        self.axes.set_ylabel('Percentage (%)', fontsize=8)
        self.axes.grid(True)
        
        # if there are enough data points, add legend
        if len(self.x_data) > 0:
            self.axes.legend(['Percentage (%)'], loc='upper right', fontsize=8)
        
        # adjust layout, ensure all elements are visible
        self.fig.tight_layout(pad=1.0)
        
        self.draw()


class BatteryDashboardView(QWidget):
    """battery dashboard view class"""
    
    def __init__(self, parent=None, auto_start=True):
        """initialize battery dashboard view
        
        Args:
            parent: parent window
            auto_start: whether to start the monitoring service automatically
        """
        super().__init__(parent)
        
        # LED status and color mapping dictionary
        self.LED_STATUS_MAP = {
            1: ("Blue", "blue"), 9: ("Blue Blinking", "blue"),
            2: ("Green", "green"), 10: ("Green Blinking", "green"),
            3: ("Cyan", "cyan"), 11: ("Cyan Blinking", "cyan"),
            4: ("Red", "red"), 12: ("Red Blinking", "red"),
            5: ("Fuchsia", "fuchsia"), 13: ("Fuchsia Blinking", "fuchsia"),
            6: ("Orange", "orange"), 14: ("Orange Blinking", "orange"),
            7: ("White", "white"), 15: ("White Blinking", "white")
        }
        
        # load ui
        self.ui = self._load_ui()
        if not self.ui:
            raise RuntimeError("failed to load battery dashboard ui file")
        
        # adjust ui size and set parent
        self.ui.setParent(self)
        
        # Initialize chart
        self.init_chart()
        
        # set window title and properties
        self.setWindowTitle("Battery Dashboard")
        self.setWindowFlags(self.windowFlags())
        
        # Adjust size to fit the chart properly
        self.resize(720, 260)
        
        # create battery service
        self.battery_service = None
        
        # connect button click events
        self.ui.push_button_update_status.clicked.connect(self._on_update_button_clicked)
        self.ui.push_button_close_battery_dashboard.clicked.connect(self.close)
        
        # initialize service but not start monitoring immediately
        self._initialize_service()
        
        # if auto_start is True, show dashboard immediately
        if auto_start:
            logger.info("auto showing battery dashboard")
            self.show_dashboard()
    
    def init_chart(self):
        """Initialize chart for battery data visualization"""
        # Create chart widget
        self.chart_canvas = BatteryChartCanvas(self.ui.chart_frame)
        
        # Create layout for chart frame
        layout = QVBoxLayout(self.ui.chart_frame)
        layout.addWidget(self.chart_canvas)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Apply layout
        self.ui.chart_frame.setLayout(layout)
        
    def _load_ui(self):
        """load ui file
        
        Returns:
            loaded ui object, or None (if loading failed)
        """
        # find ui file path
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ui_file_path = os.path.join(current_dir, "ui", "battery_dashboard.ui")
        
        # load ui file
        ui_file = QFile(ui_file_path)
        if not ui_file.open(QIODevice.ReadOnly):
            logger.error(f"failed to open ui file {ui_file_path}: {ui_file.errorString()}")
            return None
        
        # load ui using QUiLoader
        loader = QUiLoader()
        ui = loader.load(ui_file)
        ui_file.close()
        
        if not ui:
            logger.error(f"failed to load ui file {ui_file_path}: {loader.errorString()}")
            return None
        
        return ui
    
    def _initialize_service(self):
        """initialize battery monitor service"""
        try:
            # show initializing message
            self.ui.update_time_value.setText("initializing...")
            self.ui.battery_progress_bar.setValue(0)
            self.ui.percent_value.setText(f"initializing...%")
            self.ui.capacity_value.setText(f"initializing... mWh")
            self.ui.charging_voltage_value.setText(f"initializing... V")
            self.ui.charging_current_value.setText(f"initializing... A")
            self.ui.temperature_value.setText(f"initializing... °C")
            self.ui.cycle_count_value.setText(f"initializing...")
            self.ui.led_status_value.setText(f"initializing...")
            self.ui.ac_value.setText(f"initializing...")
            
            
            # create service instance in main thread
            self.battery_service = BatteryMonitorService()
            
            # connect signals using Qt.QueuedConnection, ensure cross-thread safety
            self.battery_service.battery_data_updated.connect(
                self.update_battery_display,
                type=Qt.QueuedConnection
            )
            self.battery_service.error_occurred.connect(
                self.show_error,
                type=Qt.QueuedConnection
            )
            self.battery_service.update_status_changed.connect(
                self._handle_update_status,
                type=Qt.QueuedConnection
            )
            
            logger.info("battery monitor service initialized")
            
        except Exception as e:
            error_msg = f"failed to initialize battery monitor service: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(self, "initialization error", error_msg)
    
    def show_dashboard(self):
        """show dashboard and start monitoring"""
        # show window first
        self.show()
        logger.info("battery dashboard shown")
        
        # check if service is initialized
        if not self.battery_service:
            # reinitialize service
            self._initialize_service()
            
        if self.battery_service:
            # delay start monitoring, let ui show first
            QTimer.singleShot(100, self._delayed_start_monitoring)
        else:
            logger.error("failed to start monitoring: service not initialized")
            QMessageBox.critical(self, "error", "battery monitor service not initialized")
    
    def _delayed_start_monitoring(self):
        """delayed start of battery monitoring after UI is shown"""
        try:
            logger.info("starting battery monitoring...")
            self.battery_service.start_monitoring()
        except Exception as e:
            error_msg = f"failed to start monitoring: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(self, "error", error_msg)
    
    @Slot(dict)
    def update_battery_display(self, data):
        """update battery data display
        
        Args:
            data: dictionary containing battery data
        """
        logger.debug(f"received data update: {data}")
        # use QTimer.singleShot to ensure ui update in ui thread
        QTimer.singleShot(0, lambda: self._update_ui_with_data(data))
    
    def _update_ui_with_data(self, data):
        """update ui elements in ui thread
        
        Args:
            data: dictionary containing battery data
        """
        try:
            logger.debug("starting to update ui...")
            
            # Variables to store data for chart update
            voltage = None
            current = None
            temperature = None
            percent = None
            
            # update battery percentage
            relative_state = data.get("relative_state")
            if relative_state is not None:
                self.ui.battery_progress_bar.setValue(int(relative_state))
                self.ui.percent_value.setText(f"{relative_state:.1f}%")
                # adjust color based on battery percentage
                if relative_state < 10:
                    self.ui.percent_value.setStyleSheet("color: orange")
                elif relative_state <= 99:
                    self.ui.percent_value.setStyleSheet("color: blue")
                else:
                    self.ui.percent_value.setStyleSheet("color: green")
                # Store for chart
                percent = float(relative_state)
            
            # update capacity
            capacity = data.get("capacity")
            full_capacity = data.get("full_capacity")
            if capacity is not None:
                self.ui.capacity_value.setText(f"{capacity} of {full_capacity} mWh")
            
            # update charging voltage
            charging_voltage = data.get("charging_voltage")
            if charging_voltage is not None:
                self.ui.charging_voltage_value.setText(f"{charging_voltage:.1f}V")
                # Store for chart
                voltage = float(charging_voltage)
            
            # update charging current
            charging_current = data.get("charging_current")
            if charging_current is not None:
                self.ui.charging_current_value.setText(f"{abs(charging_current):.1f} A")
                # Store for chart
                current = float(abs(charging_current))
            
            # update temperature
            temperature_value = data.get("temperature")
            if temperature_value is not None:
                self.ui.temperature_value.setText(f"{temperature_value:.1f} °C")
                # Store for chart
                temperature = float(temperature_value)
            
            # update charging cycle count
            cycle_count = data.get("cycle_count")
            if cycle_count is not None:
                self.ui.cycle_count_value.setText(f"{cycle_count}")
            
            # update LED status
            led_status = data.get("led_status")
            if led_status is not None:
                status_info = self.LED_STATUS_MAP.get(led_status, ("Unknown", "gray"))
                self.ui.led_status_value.setText(status_info[0])
                self.ui.led_status_value.setStyleSheet(f"color: {status_info[1]}")

            # update AC connection status
            dc_status = data.get("dc_status")
            if dc_status is not None:
                if dc_status:
                    self.ui.ac_value.setText("Connected")
                    self.ui.ac_value.setStyleSheet("color: green")
                else:
                    self.ui.ac_value.setText("Disconnected")
                    self.ui.ac_value.setStyleSheet("color: orange")
            
            # update update time
            timestamp = data.get("timestamp")
            if timestamp is not None:
                self.ui.update_time_value.setText(timestamp)
            
            # Update chart with data
            self.chart_canvas.update_figure(data)
                
            logger.debug("ui updated")
            
        except Exception as e:
            logger.error(f"failed to update ui: {e}")
    
    @Slot(str)
    def show_error(self, error_msg):
        """show error message
        
        Args:
            error_msg: error message
        """
        logger.error(f"battery monitor error: {error_msg}")
        QMessageBox.warning(self, "error", error_msg)
    
    def closeEvent(self, event):
        """handle close event
        
        Args:
            event: close event
        """
        logger.info("battery dashboard closing...")
        
        try:
            # stop monitoring and release resources
            if self.battery_service:
                self.battery_service.cleanup()
                self.battery_service = None
                logger.info("battery monitor service resources cleaned")
        except Exception as e:
            logger.error(f"failed to clean resources: {e}")
        
        # accept close event
        event.accept()

    def _on_update_button_clicked(self):
        """handle update button click"""
        if not self.battery_service:
            logger.error("failed to update: service not initialized")
            QMessageBox.warning(self, "error", "battery monitor service not initialized")
            return
            
        try:
            logger.info("manually update battery status")
            self.battery_service.update_now()
        except Exception as e:
            error_msg = f"failed to update: {str(e)}"
            logger.error(error_msg)
            QMessageBox.warning(self, "error", error_msg)

    def _handle_update_status(self, is_complete):
        """handle update status change
        
        Args:
            is_complete: True if update is complete, False if update is in progress
        """
        self.ui.push_button_update_status.setEnabled(is_complete)
        if is_complete:
            self.ui.push_button_update_status.setText("Update Now")
        else:
            self.ui.push_button_update_status.setText("Updating...")
