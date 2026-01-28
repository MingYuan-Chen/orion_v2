from PySide6.QtCore import QObject, Signal, QTimer
from core.models.serial_device_model import SerialDeviceModel
from util.logger import logger
import re
import os
import time

class StressTestService(QObject):
    """
    Service for running stress tests on the device using 'lucifer'.
    """
    status_updated = Signal(dict)

    def __init__(self, device_model: SerialDeviceModel, platform_name: str = "Athena"):
        super().__init__()
        self._device_model = device_model
        self._platform_name = platform_name
        self._start_time = None
        
        # Timer for periodic status updates
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timeout)

    def start_stress_test(self, cpu_loading_percent: int, mem_loading_mb: int):
        """
        Starts the stress test with the specified CPU and Memory loading.

        :param cpu_loading_percent: CPU loading percentage (25, 50, 75, 100).
        :param mem_loading_mb: Memory loading in MB.
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_name = f"StressTest_{cpu_loading_percent}%_{mem_loading_mb}MB_{timestamp}.log"
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        self.log_file = os.path.join(log_dir, log_name)
        logger.info(f"Starting stress test. Log: {self.log_file}")

        commands = []

        # CPU Loading Logic
        # 4 cores total.
        # 25% = 1 core, 50% = 2 cores, 75% = 3 cores, 100% = 4 cores.
        num_cores = 0
        if cpu_loading_percent == 25:
            num_cores = 1
        elif cpu_loading_percent == 50:
            num_cores = 2
        elif cpu_loading_percent == 75:
            num_cores = 3
        elif cpu_loading_percent == 100:
            num_cores = 4
        else:
            logger.error(f"Invalid CPU loading percent: {cpu_loading_percent}. Must be 25, 50, 75, or 100.")
            return

        # Generate CPU commands
        for i in range(num_cores):
            # taskset -c <core> lucifer --cpuc 20000 --fpuc 20000 &
            cmd = f"taskset -c {i} lucifer --cpuc 20000 --fpuc 20000 --nodisplay &"
            commands.append(cmd)

        # MEM Loading Logic
        # Convert MB to Bytes
        mem_bytes = mem_loading_mb * 1024 * 1024
        # taskset -c 0 lucifer -m <bytes> --memc 1 &
        mem_cmd = f"taskset -c 0 lucifer -m {mem_bytes} --memc 1 --nodisplay &"
        commands.append(mem_cmd)

        # Combine all commands into a single line
        full_command = " ".join(commands)
        logger.info(f"Starting stress test with command: {full_command}")

        # Send command to device
        # Using send_command_sync assuming prompt returns quickly due to '&'
        self._device_model.send_command_sync(full_command)
        self._start_time = time.time()
        
        # Start timer (3 seconds)
        self._timer.start(3000)
    
    def stop_stress_test(self):
        """
        Stops the stress test by killing the 'lucifer' processes.
        """
        # Stop timer first
        self._timer.stop()

        # Kill all lucifer processes
        cmd = "killall lucifer"
        logger.info(f"Stopping stress test with command: {cmd}")
        self._device_model.send_command_sync(cmd)
        self._start_time = None

    def _on_timeout(self):
        """Called periodically by timer to update status."""
        status = self.get_status()
        if status:
            self.status_updated.emit(status)
            with open(self.log_file, "a") as f:
                f.write(f"{status['timestamp']}[{status['duration']}] - CPU: {status['cpu_usage']}%, "
                        f"Mem: {status['memory_usage']}%, "
                        f"Battery Temp: {status['battery_temperature']}C, "
                        f"CPU Temp: {status['cpu_temperature']}C\n")

    def get_status(self) -> dict:
        """
        Gets the current status from the device including:
        - CPU Usage (%)
        - Memory Usage (%)
        - Timestamp (current time)
        - Duration (since start_stress_test)
        - Battery Temperature (from I2C command)
        - CPU Temperature (from /sys/class/hwmon/hwmon0/temp1_input)
        
        Returns:
            dict: A dictionary containing the above 5 keys.
                  Returns None if parsing critically fails.
        """
        results = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "timestamp": "Unknown",
            "duration": "0s",
            "battery_temperature": "Unknown",
            "cpu_temperature": "Unknown"
        }

        # 1. Get Timestamp
        results["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        # 2. Get Duration
        if self._start_time:
            elapsed_seconds = int(time.time() - self._start_time)
            # Format as HH:MM:SS or just seconds if preferred, user asked for duration
            duration_days, remaining_seconds = divmod(elapsed_seconds, 86400)
            duration_hours, remaining_seconds = divmod(remaining_seconds, 3600)
            duration_minutes, duration_seconds = divmod(remaining_seconds, 60)
            
            if duration_days > 0:
                 results["duration"] = f"{duration_days}d {duration_hours:02d}:{duration_minutes:02d}:{duration_seconds:02d}"
            else:
                 results["duration"] = f"{duration_hours:02d}:{duration_minutes:02d}:{duration_seconds:02d}"
        else:
            results["duration"] = "0s"

        # 3. Get CPU & Memory Usage
        cmd_top = "top -b -n 1 | head -n 5"
        response_top = self._device_model.send_command_sync(cmd_top)
        
        try:
            for line in response_top:
                line = line.strip()
                if line.startswith("%Cpu(s):"):
                    # Extract idle percentage
                    match = re.search(r'(\d+\.\d+)\s+id', line)
                    if match:
                        idle_percent = float(match.group(1))
                        # Fix logic: user might have 97.1 id -> 2.9% usage
                        results["cpu_usage"] = round(100.0 - idle_percent, 1)

                elif line.startswith("MiB Mem"):
                    # Extract total and used
                    total_match = re.search(r'(\d+\.\d+)\s+total', line)
                    used_match = re.search(r'(\d+\.\d+)\s+used', line)
                    if total_match and used_match:
                        total_mem = float(total_match.group(1))
                        used_mem = float(used_match.group(1))
                        if total_mem > 0:
                            results["memory_usage"] = round((used_mem / total_mem) * 100.0, 1)
        except Exception as e:
            logger.error(f"Error parsing CPU/Mem usage: {e}")

        # 4. Get Battery Temperature
        if self._platform_name == "Odin":
            bus = 2
        elif self._platform_name == "Athena":
            bus = 1
        else:
            bus = 0
        cmd_temp = f"i2ctransfer -f -y {bus} w4@0x4c 0x03 0x51 0x00 0x08 r1; sleep 0.1; i2ctransfer -f -y {bus} w4@0x4c 0x03 0x53 0x00 0x08 r2"
        response_temp = self._device_model.send_command_sync(cmd_temp)
        
        try:
             for line in response_temp:
                line_hex = [x.replace('0x', '') for x in line.split() if x.startswith('0x')]
                
                if len(line_hex) == 2:
                    val = int("0x" + line_hex[0] + line_hex[1], 16)
                    temp_c = round((val / 10.0) - 273.2, 1) # Using standard Kelvin to Celsius
                    results["battery_temperature"] = f"{temp_c}"

        except Exception as e:
            logger.warning(f"Failed to parse temperature: {e}")
        
        # 5. Get CPU temperature
        cmd_cpu_temp = "cat /sys/class/hwmon/hwmon0/temp1_input 2>/dev/null || echo '0'"
        response_cpu_temp = self._device_model.send_command_sync(cmd_cpu_temp)
        
        try:
            for line in response_cpu_temp:
                if line.isdigit():
                    temp_celsius = round(float(line) / 1000.0, 1)
                    results["cpu_temperature"] = f"{temp_celsius}"

        except Exception as e:
            logger.warning(f"Failed to parse CPU temperature: {e}")

        return results

    def get_free_memory_mb(self) -> float:
        """
        Gets the free memory size in MB from /proc/meminfo.

        Returns:
            float: Free memory in MB. Returns 0.0 if parsing fails.
        """
        cmd = "cat /proc/meminfo | grep MemFree"
        response = self._device_model.send_command_sync(cmd)
        
        # Response should look like: "MemFree:        3285500 kB"
        # We might get multiple lines if grep matches more (unlikely for MemFree) or echo.
        # Just search for the pattern.
        
        try:
            for line in response:
                line = line.strip()
                if line.startswith("MemFree:"):
                    # Extract kB value
                    # Split by whitespace, take the second element (value)
                    parts = line.split()
                    if len(parts) >= 2:
                        kb_value = int(parts[1])
                        mb_value = round(kb_value / 1024.0, 1)
                        return mb_value
            
            logger.warning(f"Could not find MemFree in response: {response}")
            return 0.0
            
        except Exception as e:
            logger.error(f"Error parsing MemFree: {e}")
            return 0.0