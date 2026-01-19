from PySide6.QtCore import QThread, Signal

class StabilityTestWorker(QThread):
    """
    Worker thread for running stability tests (e.g., Ping Test).
    Merges the previous StabilityTestWorker and WorkerSignals.
    """
    result = Signal(str)

    def __init__(self, service, duration: int, ip: str, ssid: str = None, password: str = None):
        super().__init__()
        self.service = service
        self.duration = duration
        self.ip = ip
        self.ssid = ssid
        self.password = password
        
    def run(self):
        try:
            if self.ssid:
                # Needed to connect first
                success, msg = self.service.connect_network_sync(self.ssid, self.password)
                if not success:
                    self.result.emit(f"Connection Failed: {msg}")
                    return
                # Disconnect eth0 to ensure test is via WiFi
                self.service.disconnect_network("eth0")
            else:
                # Disconnect WiFi interface to ensure test is via Ethernet
                # Assuming wlp1s0 is the wifi interface name
                self.service.disconnect_network("wlp1s0")

            # Run Ping Test
            summary = self.service.run_ping_test(self.duration, self.ip)
            self.result.emit(summary)
            
        except Exception as e:
            self.result.emit(f"Error: {e}")
            
        finally:
            # Always try to reconnect eth0 after test
            self.service.connect_device("eth0")
