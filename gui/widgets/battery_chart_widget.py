"""
Battery Chart Widget Module
Real-time battery monitoring charts similar to Windows Performance Monitor
"""
import sys
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Any, List
import matplotlib
matplotlib.use('Qt5Agg')  # Use Qt5Agg backend for PySide6 compatibility
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
import numpy as np

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel
from PySide6.QtCore import QTimer, Signal, Slot
from PySide6.QtGui import QFont

from util.logger import logger


class BatteryChartWidget(QWidget):
    """
    Battery Chart Widget for real-time monitoring
    Displays battery percentage, voltage, current, and temperature over time
    """
    
    def __init__(self, parent=None):
        """Initialize the battery chart widget"""
        super().__init__(parent)
        
        # Data storage (use deque for efficient append/pop operations)
        self.max_data_points = 100  # Keep last 100 data points (about 5 minutes at 3s intervals)
        self.timestamps = deque(maxlen=self.max_data_points)
        self.battery_percentage = deque(maxlen=self.max_data_points)
        self.voltage_data = deque(maxlen=self.max_data_points)
        self.current_data = deque(maxlen=self.max_data_points)
        self.temperature_data = deque(maxlen=self.max_data_points)
        
        # Chart visibility controls
        self.show_battery = True
        self.show_voltage = True
        self.show_current = True
        self.show_temperature = True
        
        # Setup UI
        self._setup_ui()
        self._setup_chart()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_chart)
        self.update_timer.start(1000)  # Update chart every second
        
        logger.info("Battery Chart Widget initialized")
    
    def _setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Controls layout
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)
        
        # Chart visibility checkboxes
        self.checkbox_battery = QCheckBox("Battery %")
        self.checkbox_battery.setChecked(True)
        self.checkbox_battery.setStyleSheet(self._get_checkbox_style("#4ECDC4"))
        self.checkbox_battery.toggled.connect(self._on_battery_toggled)
        
        self.checkbox_voltage = QCheckBox("Voltage (V)")
        self.checkbox_voltage.setChecked(True)
        self.checkbox_voltage.setStyleSheet(self._get_checkbox_style("#FF6B6B"))
        self.checkbox_voltage.toggled.connect(self._on_voltage_toggled)
        
        self.checkbox_current = QCheckBox("Current (A)")
        self.checkbox_current.setChecked(True)
        self.checkbox_current.setStyleSheet(self._get_checkbox_style("#4DABF7"))
        self.checkbox_current.toggled.connect(self._on_current_toggled)
        
        self.checkbox_temperature = QCheckBox("Temperature (°C)")
        self.checkbox_temperature.setChecked(True)
        self.checkbox_temperature.setStyleSheet(self._get_checkbox_style("#69DB7C"))
        self.checkbox_temperature.toggled.connect(self._on_temperature_toggled)
        
        controls_layout.addWidget(self.checkbox_battery)
        controls_layout.addWidget(self.checkbox_voltage)
        controls_layout.addWidget(self.checkbox_current)
        controls_layout.addWidget(self.checkbox_temperature)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Chart canvas will be added in _setup_chart
        
    def _get_checkbox_style(self, color: str) -> str:
        """Get checkbox style with custom color"""
        return f"""
            QCheckBox {{
                color: #FFFFFF;
                font-size: 11px;
                spacing: 5px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
            }}
            QCheckBox::indicator:unchecked {{
                border: 2px solid #555555;
                background-color: #2B2B2B;
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                border: 2px solid {color};
                background-color: {color};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked:hover {{
                background-color: {color};
                opacity: 0.8;
            }}
        """
    
    def _setup_chart(self):
        """Setup matplotlib chart"""
        # Set matplotlib style for dark theme
        plt.style.use('dark_background')
        
        # Create figure and canvas
        self.figure = Figure(figsize=(12, 6), dpi=100, facecolor='#252526')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #252526;")
        
        # Add canvas to layout
        self.layout().addWidget(self.canvas)
        
        # Create single subplot with multiple Y-axes
        self.ax_main = self.figure.add_subplot(1, 1, 1)
        
        # Create additional Y-axes for different scales
        self.ax_voltage = self.ax_main.twinx()
        self.ax_current = self.ax_main.twinx()
        self.ax_temperature = self.ax_main.twinx()
        
        # Position the additional axes with tighter spacing
        self.ax_current.spines['right'].set_position(('outward', 50))
        self.ax_temperature.spines['right'].set_position(('outward', 100))
        
        # Configure main axis (Battery %)
        self._configure_main_axis()
        
        # Configure additional axes
        self._configure_additional_axes()
        
        # Initialize empty lines with different axes
        self.line1, = self.ax_main.plot([], [], color='#4ECDC4', linewidth=2, label='Battery %')
        self.line2, = self.ax_voltage.plot([], [], color='#FF6B6B', linewidth=2, label='Voltage (V)')
        self.line3, = self.ax_current.plot([], [], color='#4DABF7', linewidth=2, label='Current (A)')
        self.line4, = self.ax_temperature.plot([], [], color='#69DB7C', linewidth=2, label='Temperature (°C)')
        
        # Create legend
        lines = [self.line1, self.line2, self.line3, self.line4]
        labels = [l.get_label() for l in lines]
        self.ax_main.legend(lines, labels, loc='upper left', frameon=True, 
                           facecolor='#1E1E1E', edgecolor='#444444', fontsize=9)
        
        # Adjust layout with custom margins to accommodate multiple Y-axes and X-axis label
        self.figure.subplots_adjust(left=0.08, right=0.75, top=0.95, bottom=0.20)
        
        # Initial draw
        self.canvas.draw()
    
    def _configure_main_axis(self):
        """Configure main axis (Battery %)"""
        self.ax_main.set_facecolor('#1E1E1E')
        self.ax_main.grid(True, alpha=0.3, color='#444444')
        # Set initial range, will be dynamically adjusted
        self.ax_main.set_ylim(0, 100)
        self.ax_main.tick_params(colors='white', labelsize=9)
        self.ax_main.set_xlabel('Time (seconds)', color='white', fontsize=10)
        self.ax_main.set_ylabel('Battery (%)', color='#4ECDC4', fontsize=10, fontweight='bold')
        self.ax_main.tick_params(axis='y', labelcolor='#4ECDC4')
        
        # Configure spines
        for spine in self.ax_main.spines.values():
            spine.set_color('#444444')
    
    def _configure_additional_axes(self):
        """Configure additional Y-axes"""
        # Voltage axis (right side) - initial range, will be dynamically adjusted
        self.ax_voltage.set_ylim(0, 12)
        self.ax_voltage.set_ylabel('Voltage (V)', color='#FF6B6B', fontsize=9, fontweight='bold')
        self.ax_voltage.tick_params(axis='y', labelcolor='#FF6B6B', labelsize=8)
        self.ax_voltage.spines['right'].set_color('#FF6B6B')
        
        # Current axis (offset right) - initial range, will be dynamically adjusted
        self.ax_current.set_ylim(-2, 3)
        self.ax_current.set_ylabel('Current (A)', color='#4DABF7', fontsize=9, fontweight='bold')
        self.ax_current.tick_params(axis='y', labelcolor='#4DABF7', labelsize=8)
        self.ax_current.spines['right'].set_color('#4DABF7')
        
        # Temperature axis (further offset right) - initial range, will be dynamically adjusted
        self.ax_temperature.set_ylim(0, 60)
        self.ax_temperature.set_ylabel('Temperature (°C)', color='#69DB7C', fontsize=9, fontweight='bold')
        self.ax_temperature.tick_params(axis='y', labelcolor='#69DB7C', labelsize=8)
        self.ax_temperature.spines['right'].set_color('#69DB7C')
        
        # Hide unnecessary spines for additional axes
        for ax in [self.ax_voltage, self.ax_current, self.ax_temperature]:
            ax.spines['top'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            ax.spines['left'].set_visible(False)
    
    def add_data_point(self, battery_data: Dict[str, Any]):
        """
        Add new data point to the charts
        
        Args:
            battery_data: Dictionary containing battery information
        """
        current_time = datetime.now()
        
        # Add timestamp
        self.timestamps.append(current_time)
        
        # Extract and add data points (with fallback to 0 if not available)
        try:
            battery_pct = float(battery_data.get('relative_state', 0))
            voltage = float(battery_data.get('voltage', 0))
            current = float(battery_data.get('current', 0))
            temp = float(battery_data.get('temperature', 0))
        except (ValueError, TypeError):
            # Use 0 as fallback for invalid data
            battery_pct = 0
            voltage = 0
            current = 0
            temp = 0
        
        self.battery_percentage.append(battery_pct)
        self.voltage_data.append(voltage)
        self.current_data.append(current)
        self.temperature_data.append(temp)
        
        logger.debug(f"Added chart data point: Battery={battery_pct}%, V={voltage}V, I={current}A, T={temp}°C")
    
    def _update_chart(self):
        """Update chart display"""
        if len(self.timestamps) < 2:
            return
        
        try:
            # Convert timestamps to relative seconds for better display
            base_time = self.timestamps[0]
            x_data = [(t - base_time).total_seconds() for t in self.timestamps]
            
            # Update line data and visibility based on settings
            if self.show_battery:
                self.line1.set_data(x_data, list(self.battery_percentage))
                self.line1.set_visible(True)
            else:
                self.line1.set_visible(False)
            
            if self.show_voltage:
                self.line2.set_data(x_data, list(self.voltage_data))
                self.line2.set_visible(True)
            else:
                self.line2.set_visible(False)
            
            if self.show_current:
                self.line3.set_data(x_data, list(self.current_data))
                self.line3.set_visible(True)
            else:
                self.line3.set_visible(False)
            
            if self.show_temperature:
                self.line4.set_data(x_data, list(self.temperature_data))
                self.line4.set_visible(True)
            else:
                self.line4.set_visible(False)
            
            # Update x-axis limits
            if x_data:
                x_min, x_max = min(x_data), max(x_data)
                x_range = max(60, x_max - x_min)  # Minimum 60 seconds range
                
                # Set x-axis limits for main axis (others will follow)
                self.ax_main.set_xlim(x_max - x_range, x_max + 5)
                
                # Update x-axis label
                self.ax_main.set_xlabel(f'Time (last {int(x_range)}s)', color='white', fontsize=10)
            
            # Update Y-axis limits dynamically based on data
            self._update_y_axis_limits()
            
            # Update legend visibility
            self._update_legend()
            
            # Redraw canvas
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating battery chart: {str(e)}")
    
    def _update_y_axis_limits(self):
        """Update Y-axis limits dynamically based on current data"""
        if not self.timestamps:
            return
        
        try:
            # Define default ranges and margins
            default_ranges = {
                'battery': (0, 100, 5),      # min, max, margin
                'voltage': (0, 12, 1),       # min, max, margin  
                'current': (-2, 3, 0.5),     # min, max, margin
                'temperature': (0, 60, 5)    # min, max, margin
            }
            
            # Update Battery % axis
            if self.show_battery and self.battery_percentage:
                data_min = min(self.battery_percentage)
                data_max = max(self.battery_percentage)
                default_min, default_max, margin = default_ranges['battery']
                
                y_min = min(default_min, data_min - margin)
                y_max = max(default_max, data_max + margin)
                self.ax_main.set_ylim(y_min, y_max)
            
            # Update Voltage axis
            if self.show_voltage and self.voltage_data:
                data_min = min(self.voltage_data)
                data_max = max(self.voltage_data)
                default_min, default_max, margin = default_ranges['voltage']
                
                y_min = min(default_min, data_min - margin)
                y_max = max(default_max, data_max + margin)
                self.ax_voltage.set_ylim(y_min, y_max)
            
            # Update Current axis
            if self.show_current and self.current_data:
                data_min = min(self.current_data)
                data_max = max(self.current_data)
                default_min, default_max, margin = default_ranges['current']
                
                y_min = min(default_min, data_min - margin)
                y_max = max(default_max, data_max + margin)
                self.ax_current.set_ylim(y_min, y_max)
            
            # Update Temperature axis
            if self.show_temperature and self.temperature_data:
                data_min = min(self.temperature_data)
                data_max = max(self.temperature_data)
                default_min, default_max, margin = default_ranges['temperature']
                
                y_min = min(default_min, data_min - margin)
                y_max = max(default_max, data_max + margin)
                self.ax_temperature.set_ylim(y_min, y_max)
                
        except Exception as e:
            logger.error(f"Error updating Y-axis limits: {str(e)}")
    
    def _update_legend(self):
        """Update legend to show only visible lines"""
        visible_lines = []
        visible_labels = []
        
        if self.show_battery:
            visible_lines.append(self.line1)
            visible_labels.append('Battery %')
        if self.show_voltage:
            visible_lines.append(self.line2)
            visible_labels.append('Voltage (V)')
        if self.show_current:
            visible_lines.append(self.line3)
            visible_labels.append('Current (A)')
        if self.show_temperature:
            visible_lines.append(self.line4)
            visible_labels.append('Temperature (°C)')
        
        # Clear existing legend
        if self.ax_main.legend_:
            self.ax_main.legend_.remove()
        
        # Create new legend with visible items only
        if visible_lines:
            self.ax_main.legend(visible_lines, visible_labels, loc='upper left', frameon=True,
                               facecolor='#1E1E1E', edgecolor='#444444', fontsize=9)
    
    @Slot(bool)
    def _on_battery_toggled(self, checked: bool):
        """Handle battery chart visibility toggle"""
        self.show_battery = checked
        self._update_chart()
    
    @Slot(bool)
    def _on_voltage_toggled(self, checked: bool):
        """Handle voltage chart visibility toggle"""
        self.show_voltage = checked
        self._update_chart()
    
    @Slot(bool)
    def _on_current_toggled(self, checked: bool):
        """Handle current chart visibility toggle"""
        self.show_current = checked
        self._update_chart()
    
    @Slot(bool)
    def _on_temperature_toggled(self, checked: bool):
        """Handle temperature chart visibility toggle"""
        self.show_temperature = checked
        self._update_chart()
    
    def clear_data(self):
        """Clear all chart data"""
        self.timestamps.clear()
        self.battery_percentage.clear()
        self.voltage_data.clear()
        self.current_data.clear()
        self.temperature_data.clear()
        
        # Clear lines
        for line in [self.line1, self.line2, self.line3, self.line4]:
            line.set_data([], [])
        
        self.canvas.draw()
        logger.info("Battery chart data cleared")
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        
        self.clear_data()
        logger.info("Battery Chart Widget cleaned up") 