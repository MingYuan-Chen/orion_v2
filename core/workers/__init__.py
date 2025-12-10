"""
Workers modules for the DQA test tool
"""

from .serial_device_worker import SerialDeviceWorker
from .tcp_ip_device_worker import TcpIpDeviceWorker

__all__ = ['SerialDeviceWorker', 'TcpIpDeviceWorker']