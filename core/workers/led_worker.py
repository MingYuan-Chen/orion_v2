from PySide6.QtCore import QObject, Signal
from core.models.serial_device_model import SerialDeviceModel
from util.logger import logger

class LedWorker(QObject):
    _mapper_platform_name = {
                "Athena": "athena",
                "Odin": "odin",
                "Gemini FHD": "gemini_fhd",
                "Gemini": "gemini",
                "Hydra FHD": "hydra_fhd",
                "Hydra": "hydra",
                "Argo": "argo"
            }
    
    SET_LED_STATUS = {
        "athena": {
            "blue": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x22 0x00 0x01 r2",
            "green": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x22 0x00 0x02 r2",
            "red": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x22 0x00 0x04 r2",
            "amber": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x22 0x00 0x08 r2",
            "blink_blue": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x22 0x00 0x11 r2",
            "blink_green": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x22 0x00 0x12 r2",
            "blink_red": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x22 0x00 0x14 r2",
            "blink_amber": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x22 0x00 0x18 r2",
            "default": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x22 0x00 0x20 r2"
        },
        "odin": {
            "blue": "i2ctransfer -f -y 2 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 2 w4@0x4c 0x03 0x22 0x00 0x01 r2",
            "green": "i2ctransfer -f -y 2 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 2 w4@0x4c 0x03 0x22 0x00 0x02 r2",
            "yellow": "i2ctransfer -f -y 2 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 2 w4@0x4c 0x03 0x22 0x00 0x06 r2",
            "blink_blue": "i2ctransfer -f -y 2 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 2 w4@0x4c 0x03 0x22 0x00 0x09 r2",
            "blink_green": "i2ctransfer -f -y 2 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 2 w4@0x4c 0x03 0x22 0x00 0x0a r2",
            "blink_yellow": "i2ctransfer -f -y 2 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 2 w4@0x4c 0x03 0x22 0x00 0x0e r2",
            "default": "i2ctransfer -f -y 2 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 2 w4@0x4c 0x03 0x22 0x00 0x10 r2"
        },
        "argo": {
            "blue": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x22 0x00 0x01 r2",
            "green": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x22 0x00 0x02 r2",
            "amber": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x22 0x00 0x04 r2",
            "blink_blue": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x22 0x00 0x09 r2",
            "blink_green": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x22 0x00 0x0a r2",
            "blink_amber": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x22 0x00 0x0c r2",
            "default": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x22 0x00 0x10 r2"
        },
        "other": {
            "blue": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x22 0x00 0x01 r2",
            "green": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x22 0x00 0x02 r2",
            "red": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x22 0x00 0x04 r2",
            "blink_blue": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x22 0x00 0x09 r2",
            "blink_green": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x22 0x00 0x0a r2",
            "blink_red": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x22 0x00 0x0c r2",
            "default": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x20 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x22 0x00 0x10 r2"
        }
    }

    GET_LED_STATUS = {
        "athena": "i2ctransfer -f -y 1 w4@0x4c 0x03 0x21 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 1 w4@0x4c 0x03 0x23 0x00 0x14 r2",
        "odin": "i2ctransfer -f -y 2 w4@0x4c 0x03 0x21 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 2 w4@0x4c 0x03 0x23 0x00 0x14 r2",
        "other": "i2ctransfer -f -y 0 w4@0x4c 0x03 0x21 0x00 0x14 r1; sleep 0.1; i2ctransfer -f -y 0 w4@0x4c 0x03 0x23 0x00 0x14 r2"
    }

    LED_STATUS_MAP = {
        "athena": {
            1: "Blue", 33: "Blue",
            2: "Green", 34: "Green",
            4: "Red", 36: "Red",
            8: "Amber", 40: "Amber",
            17: "Blue Blink", 49: "Blue Blink",
            18: "Green Blink", 50: "Green Blink",  
            20: "Red Blink", 52: "Red Blink",
            24: "Amber Blink", 56: "Amber Blink",
            0: "Off", 16: "Blink Off", 32: "Off"
        },
        "odin": {
            1: "Blue", 17: "Blue",
            2: "Green", 18: "Green",
            6: "Yellow", 22: "Yellow",
            9: "Blink Blue", 25: "Blink Blue",
            10: "Blink Green", 26: "Blink Green",
            14: "Blink Yellow", 30: "Blink Yellow",
            0: "Off", 16: "Off"
        },
        "argo": {
            1: "Blue", 17: "Blue",
            2: "Green", 18: "Green",
            4: "Amber", 20: "Amber",
            9: "Blink Blue", 25: "Blink Blue",
            10: "Blink Green", 26: "Blink Green",
            12: "Blink Amber", 28: "Blink Amber",
            0: "Off", 16: "Off"
        },
        "other": {
            1: "Blue", 17: "Blue",
            2: "Green", 18: "Green",
            4: "Red", 20: "Red",
            9: "Blink Blue", 25: "Blink Blue",
            10: "Blink Green", 26: "Blink Green",
            12: "Blink Red", 28: "Blink Red",
            0: "Off", 16: "Off"
        }
    }
    # Signal to emit updated battery data
    led_status_updated = Signal(str)

    def __init__(self, device_model: SerialDeviceModel, platform_name: str = None):
        super().__init__()
        self._model = device_model
        self._platform_name = self._mapper_platform_name.get(platform_name, "other")

    def set_led_status(self, status: str):
        """
        Set the LED status.
        """
        command = self.SET_LED_STATUS.get(self._platform_name, self.SET_LED_STATUS.get("other")).get(status, "")

        if not self._model.is_connected():
            logger.warning("Device not connected, cannot get battery info")
            return

        try:
            self._model.send_command_sync(command)
            if status != "default":
                self.led_status_updated.emit(f"{status}")
        except Exception as e:
            logger.error(f"Error setting LED status: {e}")
            return

    def get_led_status(self):
        """
        Get the LED status.
        """
        command = self.GET_LED_STATUS.get(self._platform_name, self.GET_LED_STATUS.get("other"))
        
        try:
            response = self._model.send_command_sync(command)
            for line in response:
                if len(line) > 4 and line.startswith('0x'):
                    line_hex = [x.replace('0x', '') for x in line.split() if x.startswith('0x')]
                    combined_hex = "0x" + line_hex[0] + line_hex[1]
                    hex_value = int(combined_hex, 16)
                    status = self.LED_STATUS_MAP.get(self._platform_name, self.LED_STATUS_MAP.get("other")).get(hex_value, "Unknown")
                    self.led_status_updated.emit(f"{status}")
        except Exception as e:
            logger.error(f"Error getting LED status: {e}")
            return
