from PySide6.QtCore import QObject, Signal
from core.models.serial_device_model import SerialDeviceModel
from util.logger import logger

class BacklightWorker(QObject):
    
    # Mapping of platform names to commands
    BRIGHTNESS_STRING = {
        "Athena": {0: "0%", 1: "10%", 2: "20%", 3: "30%", 4: "40%", 5: "50%", 6: "60%", 7: "70%", 8: "80%", 9: "90%", 10: "100%"},
        "other": {0: "0%", 1: "10%", 2: "20%", 3: "40%", 4: "60%", 5: "80%", 6: "90%", 7: "100%"}
    }
    
    # Signal to emit updated battery data
    backlight_updated = Signal(str)

    def __init__(self, device_model: SerialDeviceModel, platform_name: str = None):
        super().__init__()
        self._model = device_model
        self._platform_name = platform_name

    def set_backlight_brightness(self, brightness: int):
        """
        Set the Backlight brightness.
        """
        command = f"echo {brightness} > /sys/class/backlight/backlight/brightness"

        if not self._model.is_connected():
            logger.warning("Device not connected, cannot get battery info")
            return

        try:
            self._model.send_command_sync(command)
        except Exception as e:
            logger.error(f"Error setting Backlight brightness: {e}")
            return

    def get_backlight_brightness(self):
        """
        Get the Backlight brightness.
        """

        command = "cat /sys/class/backlight/backlight/brightness"
        
        try:
            response = self._model.send_command_sync(command)
            for line in response:
                if line.isdigit():
                    self.backlight_updated.emit(self.BRIGHTNESS_STRING.get(self._platform_name, self.BRIGHTNESS_STRING["other"]).get(int(line), "Unknown"))
        except Exception as e:
            logger.error(f"Error getting Backlight brightness: {e}")
            return
    
    def toggle_backlight(self, on_off: bool):
        """
        Toggle the Backlight.
        """
        value = 0 if on_off else 1
        command = f"echo {value} > /sys/class/backlight/backlight/bl_power"
        
        try:
            self._model.send_command_sync(command)
        except Exception as e:
            logger.error(f"Error toggling Backlight: {e}")
            return
    
    def get_backlight_status(self):
        """
        Get the Backlight status.
        """
        command = "cat /sys/class/backlight/backlight/bl_power"
        
        try:
            response = self._model.send_command_sync(command)
            for line in response:
                if line.isdigit():
                    self.backlight_updated.emit("On" if int(line) == 0 else "Off")
        except Exception as e:
            logger.error(f"Error getting Backlight status: {e}")
            return
