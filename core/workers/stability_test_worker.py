from PySide6.QtCore import QThread, Signal
import time

class StabilityTestWorker(QThread):
    """
    Worker thread for running stability tests (e.g., Ping Test).
    Merges the previous StabilityTestWorker and WorkerSignals.
    """
    result = Signal(str)
    ping_started = Signal()

    item_finished = Signal(str, str) # title, result
    
    def __init__(self, service, test_configs: list):
        super().__init__()
        self.service = service
        self.test_configs = test_configs
        
    def run(self):
        all_results = []
        
        try:
            for i, config in enumerate(self.test_configs):
                test_type = config.get("type", "ping")
                duration = config.get("duration", 3600)
                ip = config.get("ip", "")
                iface = config.get("interface_type", "ethernet")
                ssid = config.get("ssid")
                password = config.get("password")
                
                title = f"Test {i+1}: {test_type.upper()} ({iface})"
                self.result.emit(f"Starting {title}...")
                
                # Setup Environment
                if iface == "wifi":
                    if ssid:
                        # Ensure interface is up first since we might have disconnected it in previous test
                        self.service.connect_device("wlp1s0")
                        time.sleep(2)
                        
                        success, msg = self.service.connect_network_sync(ssid, password)
                        if not success:
                            self.result.emit(f"{title} Failed: Connection Error - {msg}")
                            continue # Skip to next
                        
                        self.result.emit(f"{title}: WiFi connected. Stabilizing...")
                        
                        time.sleep(5) # Wait for DHCP and routing
                        
                        # Disconnect eth0
                        self.service.disconnect_network("eth0")
                        time.sleep(2) # Wait for route update
                else:
                    # Ethernet: Disconnect WiFi
                    self.service.disconnect_network("wlp1s0")
                    # Ensure eth0 is up (though cleanup does it, good to double check)
                    self.service.connect_device("eth0")
                    time.sleep(3) # Stabilization
                
                # Run Test
                self.ping_started.emit()
                summary = self.service.run_ping_test(duration, ip, config)
                self.result.emit(f"{title} Finished.\n{summary}")
                self.item_finished.emit(title, summary)
                all_results.append(f"{title}: {summary}")
                
                # Teardown / Cleanup for next item
                self.service.connect_device("eth0")
                time.sleep(5) # Give time for Eth0 to fully come up and network stack to settle before next iteration
                
            self.result.emit("All tests completed.")
            
        except Exception as e:
            self.result.emit(f"Error during test execution: {e}")

    @staticmethod
    def save_config(file_path: str, configs: list) -> bool:
        """
        Saves the test configuration list to a JSON file.
        """
        import json
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(configs, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    @staticmethod
    def load_config(file_path: str) -> list:
        """
        Loads the test configuration list from a JSON file.
        """
        import json
        import os
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                configs = json.load(f)
            return configs if isinstance(configs, list) else []
        except Exception as e:
            print(f"Error loading config: {e}")
            return []
