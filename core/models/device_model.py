from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

class DeviceModel(ABC):
    """Base class for device models"""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.is_connected = False
        self.last_connection_time: Optional[datetime] = None
        self.last_command_time: Optional[datetime] = None
        
    @abstractmethod
    def connect(self) -> bool:
        """Connect to device"""
        pass
        
    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from device"""
        pass
        
    @abstractmethod
    def send_command(self, command: str) -> str:
        """Send command to device"""
        pass
        
    def update_connection_status(self, connected: bool):
        """Update connection status"""
        self.is_connected = connected
        if connected:
            self.last_connection_time = datetime.now()
            
    def update_command_time(self):
        """Update last command time"""
        self.last_command_time = datetime.now()
        
    def get_connection_duration(self) -> Optional[float]:
        """Get connection duration in seconds"""
        if self.is_connected and self.last_connection_time:
            return (datetime.now() - self.last_connection_time).total_seconds()
        return None 