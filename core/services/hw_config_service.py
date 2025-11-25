import json
import os
import sys
from typing import List, Dict, Optional
from util.logger import logger

class HWConfigService:
    """
    Service to handle loading and saving of hardware configuration JSON files.
    """
    def __init__(self):
        # Determine base path handling frozen state (PyInstaller)
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.getcwd()

        self.config_dir = os.path.join(base_path, "resources", "hw_config")
        
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir)
            except OSError as e:
                logger.error(f"Failed to create config directory: {e}")
        
        self._ensure_default_configs()

    def _ensure_default_configs(self):
        """
        Ensures that the specific 7 default config files exist.
        If not, creates them with the hardcoded content.
        """
        default_files = {
            "argo_VN240014_20251113.json": {
                "platform_name": "argo",
                "platform_model": "VN240014",
                "platform_serial": "24622000013",
                "config_name": "2025-1111",
                "created_date": "2025-11-11T15:41:11.065498",
                "components": [
                    {"id": "touch", "component": "Touch", "part_number": "156YF4A0", "serial_number": "A6J0019", "note": "Touch Sensor Model: XH8678A01B"},
                    {"id": "display", "component": "Display", "part_number": "N/A", "serial_number": "S156VDUARRSA1SA142N0022", "note": "Model: TM156VDSG16 TIANMA"},
                    {"id": "main_board", "component": "Main Board", "part_number": "98PMHYDRA00F-020", "serial_number": "ARFHD24360007", "note": "--"},
                    {"id": "edp_board", "component": "eDP Board", "part_number": "99GLCNB000F V1.00", "serial_number": "2422192100", "note": "Model : GL108_518234192 REV:D"},
                    {"id": "battery", "component": "Battery", "part_number": "MD-BAT02 ", "serial_number": "243300004", "note": "Model: BN2013250-001LML-01"}
                ]
            },
            "argo_VN240018_20251112.json": {
                "platform_name": "argo",
                "platform_model": "VN240018",
                "platform_serial": "24622000013",
                "config_name": "VN240018_20251112",
                "created_date": "2025-11-12T17:47:19.688473",
                "components": [
                    {"id": "touch", "component": "Touch", "part_number": "156YF4A0", "serial_number": "A710017", "note": "Touch Sensor Model : XH8678A01B"},
                    {"id": "display", "component": "Display", "part_number": "Can NOT be verified", "serial_number": "S156VDUARRSA1SA142N0063", "note": "Model : TIANMA TM156VDSG16"},
                    {"id": "main_board", "component": "Main Board", "part_number": "98PMHYDRA00F-020", "serial_number": "ARFHD24360014 ", "note": "--"},
                    {"id": "edp_board", "component": "eDP Board", "part_number": "99GLCNB000F V1.00", "serial_number": "2422192102", "note": "Model : GL108_518234192 REV:D"},
                    {"id": "battery", "component": "Battery", "part_number": "BN2013250-001LML-01", "serial_number": "243300004", "note": "Model : MD-BAT02"}
                ]
            },
            "athena_Small_24622000013_20251117.json": {
                "platform_name": "athena",
                "platform_model": "Small",
                "platform_serial": "24622000013",
                "config_name": "Small_24622000013_20251117",
                "created_date": "2025-11-17T11:02:11.975218",
                "components": [
                    {"id": "touch", "component": "Touch", "part_number": "133YF0A0", "serial_number": "98FCNYANA1350F-010", "note": "--"},
                    {"id": "display", "component": "Display", "part_number": "--", "serial_number": "13A2500472013", "note": "--"},
                    {"id": "main_board", "component": "Main Board", "part_number": "98PMATHENA000-030", "serial_number": "ATNA025240008", "note": "--"},
                    {"id": "edp_board", "component": "eDP Board", "part_number": "--", "serial_number": "--", "note": "Test"},
                    {"id": "battery", "component": "Battery", "part_number": "--", "serial_number": "2503030", "note": "--"}
                ]
            },
            "gemini_10FHD210010_20251113.json": {
                "platform_name": "gemini",
                "platform_model": "10FHD210010",
                "platform_serial": "24622000013",
                "config_name": "10FHD210010",
                "created_date": "2025-11-13T10:45:20.762553",
                "components": [
                    {"id": "touch", "component": "Touch", "part_number": "101YF6A1", "serial_number": "4460182", "note": "Model: XH8712C01A"},
                    {"id": "display", "component": "Display", "part_number": "Can't not be verify", "serial_number": "24706020061", "note": "Model: TM10JDHG30"},
                    {"id": "main_board", "component": "Main Board", "part_number": "98PMHYDRA00F-020", "serial_number": "HYFHD22180021", "note": "Model: Can't not be verify"},
                    {"id": "edp_board", "component": "eDP Board", "part_number": "N/A", "serial_number": "N/A", "note": "N/A"},
                    {"id": "battery", "component": "Battery", "part_number": "Can't not be verify", "serial_number": "240500734", "note": "Model: MD-BAT"}
                ]
            },
            "gemini_fhd_CP240765_20251113.json": {
                "platform_name": "hydra_fhd",
                "platform_model": "CP240765",
                "platform_serial": "24622000013",
                "config_name": "2025-1111_FHD 10.1 Gemini",
                "created_date": "2025-11-11T14:01:51.657140",
                "components": [
                    {"id": "touch", "component": "Touch", "part_number": "156YF3A3", "serial_number": "101YF6A5", "note": "Model: XH8712C01A"},
                    {"id": "display", "component": "Display", "part_number": "Can't not be verify", "serial_number": "2X2BBJU2EYZZ-PS0100", "note": "Model: AUO G101UAN01.0"},
                    {"id": "main_board", "component": "Main Board", "part_number": "98PMHYDRA00F-020", "serial_number": "GEFHD24480373", "note": "Model: Can't not be verify"},
                    {"id": "edp_board", "component": "eDP Board", "part_number": "99GLCNB002F V.203", "serial_number": "224600114", "note": "Model : GL108_518234192 REV:D"},
                    {"id": "battery", "component": "Battery", "part_number": "MD-BAT", "serial_number": "243400017", "note": "Model: Can't not be verify"}
                ]
            },
            "hydra_fhd_CQ241891_20251112.json": {
                "platform_name": "hydra_fhd",
                "platform_model": "CQ241891",
                "platform_serial": "24622000013",
                "config_name": "hw_config",
                "created_date": "2025-11-12T11:51:41.906666",
                "components": [
                    {"id": "touch", "component": "Touch", "part_number": "156YF3A3", "serial_number": "9AK0685", "note": "Touch Sensor Model: XH8678S01B"},
                    {"id": "display", "component": "Display", "part_number": "Can NOT be Verified", "serial_number": "S156VDUARRSA1SA13CT00F7", "note": "Model : TIANMA TM156VDSG16"},
                    {"id": "main_board", "component": "Main Board", "part_number": "98PMHYDRA00F-020", "serial_number": "HYFHD24160599", "note": "--"},
                    {"id": "edp_board", "component": "eDP Board", "part_number": "99GLCNB000F V1.00", "serial_number": "2418192588", "note": "Model : GL108_518234192 REV:D"},
                    {"id": "battery", "component": "Battery", "part_number": "Can NOT be Verified", "serial_number": "243400017", "note": "Model : MD-BAT"}
                ]
            },
            "hydra_hd_CN190024_20251113.json": {
                "platform_name": "hydra_hd",
                "platform_model": "CN190024",
                "platform_serial": "24622000013",
                "config_name": "hw_config",
                "created_date": "2025-11-13T11:51:41.906666",
                "components": [
                    {"id": "touch", "component": "Touch", "part_number": "101YF6A5", "serial_number": "9A50218", "note": "Touch Sensor Model: XH8678A01.FAC.A"},
                    {"id": "display", "component": "Display", "part_number": "Can NOT be Verified", "serial_number": "4B83BD03URZZ-ZS0100", "note": "Model : AUO G156XTN01.0"},
                    {"id": "main_board", "component": "Main Board", "part_number": "98PMHYDRA00F-020", "serial_number": "HYMB2240002", "note": "--"},
                    {"id": "edp_board", "component": "eDP Board", "part_number": "N/A", "serial_number": "N/A", "note": "--"},
                    {"id": "battery", "component": "Battery", "part_number": "Can NOT be Verified", "serial_number": "191801036", "note": "Model : MD-BAT"}
                ]
            },
            "odin_default.json": {
                "platform_name": "odin",
                "platform_model": "Default",
                "platform_serial": "0000",
                "config_name": "hw_config",
                "created_date": "2025-11-13T11:51:41.906666",
                "components": [
                    {"id": "touch", "component": "Touch", "part_number": "--", "serial_number": "--", "note": "--"},
                    {"id": "display", "component": "Display", "part_number": "--", "serial_number": "--", "note": "--"},
                    {"id": "main_board", "component": "Main Board", "part_number": "--", "serial_number": "--", "note": "--"},
                    {"id": "edp_board", "component": "eDP Board", "part_number": "N/A", "serial_number": "N/A", "note": "--"},
                    {"id": "battery", "component": "Battery", "part_number": "--", "serial_number": "--", "note": "--"}
                ]
            }
        }

        for filename, data in default_files.items():
            filepath = os.path.join(self.config_dir, filename)
            if not os.path.exists(filepath):
                self.save_config(filename, data)
                logger.info(f"Restored missing default config file: {filename}")

    def get_config_files(self, platform_name: str) -> List[str]:
        """
        Returns a list of config filenames that match the given platform name.
        Matches if the filename starts with the platform name (case-insensitive).
        """
        if not platform_name or platform_name == "Unknown":
            return []
            
        matched_files = []
        try:
            if os.path.exists(self.config_dir):
                for filename in os.listdir(self.config_dir):
                    if filename.endswith(".json"):
                        # Check if filename starts with platform_name (case-insensitive)
                        # e.g. "athena" matches "athena_Small_..."
                        if filename.lower().startswith(platform_name.lower()):
                            matched_files.append(filename)
        except Exception as e:
            logger.error(f"Error listing config files: {e}")
            
        return sorted(matched_files)

    def load_config(self, filename: str) -> Dict:
        """
        Loads the content of a specific config file.
        """
        filepath = os.path.join(self.config_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config file {filename}: {e}")
            return {}

    def save_config(self, filename: str, data: Dict) -> bool:
        """
        Saves the data to a config file.
        """
        filepath = os.path.join(self.config_dir, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving config file {filename}: {e}")
            return False
