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

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QTimer, Signal, Slot

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
        self.max_data_points = 30000  # Keep last 30000 data points (about 3+ days at 10s intervals)
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
        
        # Data cache for handling invalid values (similar to CSV cache)
        self.data_cache = {
            "relative_state": 0,
            "voltage": 0,
            "current": 0,
            "temperature": 0
        }
        
        # Sampling configuration
        self.sampling_method = "multi_resolution"  # Options: "none", "uniform", "multi_resolution"
        
        # Setup chart
        self._setup_chart()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_chart)
        self.update_timer.start(1000)  # Update chart every second
        
        logger.info("Battery Chart Widget initialized")
    
    def _setup_chart(self):
        """Setup matplotlib chart"""
        # Set matplotlib style for dark theme
        plt.style.use('dark_background')
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create figure and canvas
        self.figure = Figure(figsize=(12, 6), dpi=100, facecolor='#252526')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #252526;")
        
        # Add canvas to layout
        layout.addWidget(self.canvas)
        
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
        
        # Temperature axis (offset right) - initial range, will be dynamically adjusted
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
        
        # Process data fields with caching for invalid values (similar to CSV logic)
        data_fields = {
            "relative_state": "battery_pct",
            "voltage": "voltage", 
            "current": "current",
            "temperature": "temp"
        }
        
        processed_data = {}
        
        for field, var_name in data_fields.items():
            current_value = battery_data.get(field, None)
            
            # Check if current value is valid (not None, not empty string, and not just whitespace)
            # Note: 0, 0.0, False are valid values, so we need to check specifically for None and empty strings
            if current_value is not None and str(current_value).strip() != "":
                try:
                    # Valid value: update cache and use current value
                    parsed_value = float(current_value)
                    self.data_cache[field] = parsed_value
                    processed_data[var_name] = parsed_value
                    logger.debug(f"Updated chart cache for {field}: {parsed_value}")
                except (ValueError, TypeError):
                    # Invalid float value: use cached value
                    processed_data[var_name] = self.data_cache[field]
                    logger.debug(f"Invalid value for {field}, using cached: {self.data_cache[field]}")
            else:
                # Empty or invalid value: use cached value
                processed_data[var_name] = self.data_cache[field]
                if self.data_cache[field] != 0:
                    logger.debug(f"Using cached value for {field}: {self.data_cache[field]}")
        
        # Add processed data to chart
        battery_pct = processed_data["battery_pct"]
        voltage = processed_data["voltage"]
        current = processed_data["current"]
        temp = processed_data["temp"]
        
        self.battery_percentage.append(battery_pct)
        self.voltage_data.append(voltage)
        self.current_data.append(current)
        self.temperature_data.append(temp)
        
        logger.debug(f"Added chart data point: Battery={battery_pct}%, V={voltage}V, I={current}A, T={temp}°C")
    
    def _get_optimized_data_for_plotting(self):
        """
        Get optimized data for plotting with dynamic sampling
        Returns sampled x_data and corresponding y_data for each metric
        """
        if len(self.timestamps) < 2:
            return None, None, None, None, None
        
        # Convert timestamps to relative seconds
        base_time = self.timestamps[0]
        full_x_data = [(t - base_time).total_seconds() for t in self.timestamps]
        full_battery = list(self.battery_percentage)
        full_voltage = list(self.voltage_data)
        full_current = list(self.current_data)
        full_temperature = list(self.temperature_data)
        
        total_points = len(full_x_data)
        
        # Apply sampling based on configuration
        if self.sampling_method == "none" or total_points <= 1000:
            # No sampling or small dataset
            return full_x_data, full_battery, full_voltage, full_current, full_temperature
        
        elif self.sampling_method == "uniform":
            # Uniform sampling (your original suggestion)
            return self._apply_uniform_sampling(
                full_x_data, full_battery, full_voltage, full_current, full_temperature
            )
        
        elif self.sampling_method == "multi_resolution":
            # Multi-resolution sampling (recommended)
            return self._apply_multi_resolution_sampling(
                full_x_data, full_battery, full_voltage, full_current, full_temperature
            )
        
        else:
            # Fallback to no sampling
            return full_x_data, full_battery, full_voltage, full_current, full_temperature
    
    def _apply_multi_resolution_sampling(self, x_data, battery, voltage, current, temperature):
        """
        Apply multi-resolution sampling:
        - Recent data (last 2 hours): full resolution
        - Medium data (last 12 hours): sample every 2 points
        - Old data (older than 12 hours): sample every 5 points
        """
        total_points = len(x_data)
        if total_points <= 1:
            return x_data, battery, voltage, current, temperature
        
        # Calculate time ranges (in seconds)
        max_time = x_data[-1]
        recent_threshold = max_time - 7200    # Last 2 hours (2 * 3600)
        medium_threshold = max_time - 43200   # Last 12 hours (12 * 3600)
        
        sampled_indices = []
        
        for i in range(total_points):
            current_time = x_data[i]
            
            if current_time >= recent_threshold:
                # Recent data: keep all points
                sampled_indices.append(i)
            elif current_time >= medium_threshold:
                # Medium data: sample every 2 points
                if i % 2 == 0:
                    sampled_indices.append(i)
            else:
                # Old data: sample every 5 points
                if i % 5 == 0:
                    sampled_indices.append(i)
        
        # Always include the last point
        if sampled_indices and sampled_indices[-1] != total_points - 1:
            sampled_indices.append(total_points - 1)
        
        # Extract sampled data
        sampled_x = [x_data[i] for i in sampled_indices]
        sampled_battery = [battery[i] for i in sampled_indices]
        sampled_voltage = [voltage[i] for i in sampled_indices]
        sampled_current = [current[i] for i in sampled_indices]
        sampled_temp = [temperature[i] for i in sampled_indices]
        
        logger.debug(f"Applied multi-resolution sampling: {total_points} -> {len(sampled_indices)} points")
        return sampled_x, sampled_battery, sampled_voltage, sampled_current, sampled_temp
    
    def _apply_uniform_sampling(self, x_data, battery, voltage, current, temperature):
        """
        Apply uniform sampling based on total data points (your original suggestion):
        - 1000+ points: sample every 2 points
        - 2000+ points: sample every 3 points
        - 3000+ points: sample every 4 points, etc.
        """
        total_points = len(x_data)
        if total_points <= 1000:
            return x_data, battery, voltage, current, temperature
        
        # Calculate sampling rate based on data size
        if total_points <= 2000:
            sample_rate = 2
        elif total_points <= 3000:
            sample_rate = 3
        elif total_points <= 5000:
            sample_rate = 4
        elif total_points <= 10000:
            sample_rate = 5
        else:
            # For very large datasets, sample more aggressively
            sample_rate = max(5, total_points // 2000)
        
        # Apply uniform sampling
        sampled_indices = []
        for i in range(0, total_points, sample_rate):
            sampled_indices.append(i)
        
        # Always include the last point
        if sampled_indices and sampled_indices[-1] != total_points - 1:
            sampled_indices.append(total_points - 1)
        
        # Extract sampled data
        sampled_x = [x_data[i] for i in sampled_indices]
        sampled_battery = [battery[i] for i in sampled_indices]
        sampled_voltage = [voltage[i] for i in sampled_indices]
        sampled_current = [current[i] for i in sampled_indices]
        sampled_temp = [temperature[i] for i in sampled_indices]
        
        logger.debug(f"Applied uniform sampling (rate={sample_rate}): {total_points} -> {len(sampled_indices)} points")
        return sampled_x, sampled_battery, sampled_voltage, sampled_current, sampled_temp
    
    def _update_chart(self):
        """Update chart display with optimized data sampling"""
        if len(self.timestamps) < 2:
            return
        
        try:
            # Get optimized data for plotting
            x_data, battery_data, voltage_data, current_data, temp_data = self._get_optimized_data_for_plotting()
            
            if x_data is None:
                return
            
            # Update line data and visibility based on settings
            if self.show_battery:
                self.line1.set_data(x_data, battery_data)
                self.line1.set_visible(True)
            else:
                self.line1.set_visible(False)
            
            if self.show_voltage:
                self.line2.set_data(x_data, voltage_data)
                self.line2.set_visible(True)
            else:
                self.line2.set_visible(False)
            
            if self.show_current:
                self.line3.set_data(x_data, current_data)
                self.line3.set_visible(True)
            else:
                self.line3.set_visible(False)
            
            if self.show_temperature:
                self.line4.set_data(x_data, temp_data)
                self.line4.set_visible(True)
            else:
                self.line4.set_visible(False)
            
            # Update x-axis limits
            if x_data:
                x_min, x_max = min(x_data), max(x_data)
                total_range = x_max - x_min
                
                # Always show complete data range with some padding
                if total_range > 0:
                    padding = max(10, total_range * 0.02)  # 2% padding or minimum 10 seconds
                    self.ax_main.set_xlim(x_min - padding, x_max + padding)
                    
                    # Format time display based on range
                    if total_range >= 3600:  # More than 1 hour
                        hours = int(total_range // 3600)
                        minutes = int((total_range % 3600) // 60)
                        self.ax_main.set_xlabel(f'Time (total {hours}h {minutes}m)', color='white', fontsize=10)
                    elif total_range >= 60:  # More than 1 minute
                        minutes = int(total_range // 60)
                        seconds = int(total_range % 60)
                        self.ax_main.set_xlabel(f'Time (total {minutes}m {seconds}s)', color='white', fontsize=10)
                    else:
                        self.ax_main.set_xlabel(f'Time (total {int(total_range)}s)', color='white', fontsize=10)
                else:
                    # Fallback for very short data
                    self.ax_main.set_xlim(-5, 5)
                    self.ax_main.set_xlabel('Time (seconds)', color='white', fontsize=10)
            
            # Update Y-axis limits dynamically based on sampled data
            self._update_y_axis_limits(battery_data, voltage_data, current_data, temp_data)
            
            # Update legend visibility
            self._update_legend()
            
            # Redraw canvas
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating battery chart: {str(e)}")
    
    def _update_y_axis_limits(self, battery_data, voltage_data, current_data, temp_data):
        """Update Y-axis limits dynamically based on sampled data"""
        if not battery_data and not voltage_data and not current_data and not temp_data:
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
            if self.show_battery and battery_data:
                data_min = min(battery_data)
                data_max = max(battery_data)
                default_min, default_max, margin = default_ranges['battery']
                
                y_min = min(default_min, data_min - margin)
                y_max = max(default_max, data_max + margin)
                self.ax_main.set_ylim(y_min, y_max)
            
            # Update Voltage axis
            if self.show_voltage and voltage_data:
                data_min = min(voltage_data)
                data_max = max(voltage_data)
                default_min, default_max, margin = default_ranges['voltage']
                
                y_min = min(default_min, data_min - margin)
                y_max = max(default_max, data_max + margin)
                self.ax_voltage.set_ylim(y_min, y_max)
            
            # Update Current axis
            if self.show_current and current_data:
                data_min = min(current_data)
                data_max = max(current_data)
                default_min, default_max, margin = default_ranges['current']
                
                y_min = min(default_min, data_min - margin)
                y_max = max(default_max, data_max + margin)
                self.ax_current.set_ylim(y_min, y_max)
            
            # Update Temperature axis
            if self.show_temperature and temp_data:
                data_min = min(temp_data)
                data_max = max(temp_data)
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
        
        # Clear data cache
        self.data_cache = {
            "relative_state": 0,
            "voltage": 0,
            "current": 0,
            "temperature": 0
        }
        
        # Clear lines
        for line in [self.line1, self.line2, self.line3, self.line4]:
            line.set_data([], [])
        
        self.canvas.draw()
        logger.info("Battery chart data cleared")
    
    def reload_data_from_history(self, history_data: List[Dict[str, Any]]):
        """
        Reload chart data from history data
        
        Args:
            history_data: List of historical battery data with timestamps
        """
        # Clear current data
        self.clear_data()
        
        # Add data points from history in chronological order
        for data_point in history_data:
            if "timestamp" in data_point:
                # Extract timestamp and battery data
                timestamp = data_point["timestamp"]
                battery_data = {k: v for k, v in data_point.items() if k != "timestamp"}
                
                # Add timestamp manually instead of using current time
                self.timestamps.append(timestamp)
                
                # Process data fields with caching
                data_fields = {
                    "relative_state": "battery_pct",
                    "voltage": "voltage", 
                    "current": "current",
                    "temperature": "temp"
                }
                
                processed_data = {}
                
                for field, var_name in data_fields.items():
                    current_value = battery_data.get(field, None)
                    
                    if current_value is not None and str(current_value).strip() != "":
                        try:
                            parsed_value = float(current_value)
                            self.data_cache[field] = parsed_value
                            processed_data[var_name] = parsed_value
                        except (ValueError, TypeError):
                            processed_data[var_name] = self.data_cache[field]
                    else:
                        processed_data[var_name] = self.data_cache[field]
                
                # Add processed data to chart
                self.battery_percentage.append(processed_data["battery_pct"])
                self.voltage_data.append(processed_data["voltage"])
                self.current_data.append(processed_data["current"])
                self.temperature_data.append(processed_data["temp"])
        
        # Update chart display
        self._update_chart()
        logger.info(f"Reloaded {len(history_data)} data points from history")
    
    def set_sampling_method(self, method: str):
        """
        Set the data sampling method for chart rendering
        
        Args:
            method: Sampling method - "none", "uniform", or "multi_resolution"
        """
        valid_methods = ["none", "uniform", "multi_resolution"]
        if method in valid_methods:
            self.sampling_method = method
            logger.info(f"Sampling method changed to: {method}")
            # Force chart refresh with new sampling
            self._update_chart()
        else:
            logger.warning(f"Invalid sampling method: {method}. Valid options: {valid_methods}")
    
    def get_sampling_info(self) -> dict:
        """
        Get information about current sampling configuration and data size
        
        Returns:
            Dictionary with sampling information
        """
        total_points = len(self.timestamps)
        
        if total_points < 2:
            return {
                "total_points": total_points,
                "sampling_method": self.sampling_method,
                "displayed_points": total_points,
                "sampling_ratio": 1.0
            }
        
        # Get sampled data to see actual display points
        x_data, _, _, _, _ = self._get_optimized_data_for_plotting()
        displayed_points = len(x_data) if x_data else 0
        sampling_ratio = displayed_points / total_points if total_points > 0 else 0
        
        return {
            "total_points": total_points,
            "sampling_method": self.sampling_method,
            "displayed_points": displayed_points,
            "sampling_ratio": round(sampling_ratio, 3)
        }
    
    def save_chart(self, file_path=None):
        """
        Save current chart as PNG file
        
        Args:
            file_path: Optional file path to save. If None, will use a default timestamp-based name
        
        Returns:
            str: The file path where the chart was saved, or None if save failed
        """
        try:
            from datetime import datetime
            import os
            from PySide6.QtWidgets import QFileDialog, QMessageBox
            
            # Generate default filename if not provided
            if not file_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = f"battery_chart_{timestamp}.png"
            
            # Ensure the chart is up to date
            self._update_chart()
            
            # Save the figure
            self.figure.savefig(
                file_path,
                dpi=300,  # High DPI for better quality
                bbox_inches='tight',  # Remove extra whitespace
                facecolor=self.figure.get_facecolor(),  # Maintain dark background
                edgecolor='none',
                format='png'
            )
            
            logger.info(f"Battery chart saved to: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save battery chart: {str(e)}")
            return None
    
    def save_chart_with_dialog(self):
        """Show file dialog and save chart"""
        try:
            from datetime import datetime
            from PySide6.QtWidgets import QFileDialog, QMessageBox
            
            # Generate default filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"battery_chart_{timestamp}.png"
            
            # Show save dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Battery Chart",
                default_filename,
                "PNG Files (*.png);;All Files (*)"
            )
            
            if file_path:
                # Save the chart
                saved_path = self.save_chart(file_path)
                
                if saved_path:
                    # Show success message
                    QMessageBox.information(
                        self,
                        "Save success",
                        f"Battery chart saved to:\n{saved_path}",
                        QMessageBox.Ok
                    )
                    return saved_path
                else:
                    # Show error message
                    QMessageBox.critical(
                        self,
                        "Save failed",
                        "Cannot save battery chart, please check the file path and permissions.",
                        QMessageBox.Ok
                    )
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error in save chart dialog: {str(e)}")
            # Show error message
            try:
                QMessageBox.critical(
                    self,
                    "Save failed",
                    f"Error saving battery chart:\n{str(e)}",
                    QMessageBox.Ok
                )
            except:
                pass
            return None
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
            logger.info("Battery Chart Widget timer stopped")
        
        self.clear_data()
        logger.info("Battery Chart Widget cleaned up")
    
    def resume_updates(self):
        """Resume chart updates (restart timer)"""
        if hasattr(self, 'update_timer'):
            self.update_timer.start(1000)  # Update chart every second
            logger.info("Battery Chart Widget timer resumed") 