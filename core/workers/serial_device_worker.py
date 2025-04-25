from PySide6.QtCore import QObject, Signal, Slot, QMutex, QThread
from typing import Dict, Optional, List, Any
import uuid
import time
from core.models.device_manager_model import DeviceManagerModel
from util.logger import logger
import sys

class SerialDeviceWorker(QObject):
    """
    Serial Device Worker Class
    
    Responsible for executing device operations in a separate thread, such as connecting, disconnecting, and sending commands.
    Each operation completes by emitting a signal to notify the result.
    Supports concurrent multi-device operations, and can be extended for various device services.
    """
    # Define external signals
    connection_result = Signal(str, bool, str)  # device_id, success, message
    disconnection_result = Signal(str, bool, str)  # device_id, success, message
    command_result = Signal(str, str, str)  # device_id, command, response
    
    # Define internal signals for passing commands between threads
    _connect_device_signal = Signal(str, str, int, int)  # device_id, port, baudrate, timeout
    _disconnect_device_signal = Signal(str)  # device_id
    _send_command_signal = Signal(str, str, int)  # device_id, command, timeout
    
    def __init__(self, device_manager: DeviceManagerModel):
        super().__init__()
        self.device_manager = device_manager
        self.command_mutex = QMutex()
        
        # 新增防重入標記
        self._is_cleaning = False
        
        # Create thread and move worker to thread
        self.thread = QThread()
        self.thread.setObjectName(f"SerialDeviceWorker_{uuid.uuid4().hex[:8]}")
        self.moveToThread(self.thread)
        
        # Connect thread signals
        self.thread.started.connect(self._on_thread_started)
        self.thread.finished.connect(self._on_thread_finished)
        
        # Connect internal signals to actual execution slots
        self._connect_device_signal.connect(self._execute_connect_device)
        self._disconnect_device_signal.connect(self._execute_disconnect_device)
        self._send_command_signal.connect(self._execute_send_command)
        
        # Start thread
        self.thread.start()
        
    def _on_thread_started(self):
        """Handle thread start"""
        logger.info(f"SerialDeviceWorker thread started: {self.thread.objectName()}")
        
    def _on_thread_finished(self):
        """Handle thread finish"""
        logger.info(f"SerialDeviceWorker thread finished: {self.thread.objectName()}")
        
    def cleanup(self):
        """Clean up resources, stop thread"""
        # Prevent duplicate cleanup
        if hasattr(self, '_is_cleaning') and self._is_cleaning:
            logger.warning("SerialDeviceWorker is already in the cleanup process, avoid duplicate calls")
            return
            
        # Set cleanup flag
        self._is_cleaning = True
            
        logger.info("SerialDeviceWorker starts cleaning up resources")
        
        try:
            # First disconnect all signal connections
            try:
                # Block sending new signals
                self.blockSignals(True)
                
                # Disconnect signal connections safely - PySide6's Signal does not have a receivers() method
                # Try to disconnect specific connections directly, using try-except to handle possible errors
                
                # Try to disconnect internal signal connections
                try:
                    self._connect_device_signal.disconnect(self._execute_connect_device)
                    logger.debug("Disconnected _connect_device_signal signal")
                except (TypeError, RuntimeError):
                    # Signal may not be connected or already disconnected
                    pass
                except Exception as e:
                    logger.warning(f"Error disconnecting _connect_device_signal: {e}")
                
                try:
                    self._disconnect_device_signal.disconnect(self._execute_disconnect_device)
                    logger.debug("Disconnected _disconnect_device_signal signal")
                except (TypeError, RuntimeError):
                    # Signal may not be connected or already disconnected
                    pass
                except Exception as e:
                    logger.warning(f"Error disconnecting _disconnect_device_signal: {e}")
                
                try:
                    self._send_command_signal.disconnect(self._execute_send_command)
                    logger.debug("Disconnected _send_command_signal signal")
                except (TypeError, RuntimeError):
                    # Signal may not be connected or already disconnected
                    pass
                except Exception as e:
                    logger.warning(f"Error disconnecting _send_command_signal: {e}")
                
                # Do not try to disconnect external signals, because we do not know who connected them
                # Just keep blockSignals(True)
                
                logger.debug("SerialDeviceWorker signal processing completed")
            except Exception as e:
                logger.warning(f"Error disconnecting signals: {e}")
            
            # Then stop the thread - Note: Keep a reference to the thread first
            thread_ref = None
            if hasattr(self, 'thread') and self.thread:
                thread_ref = self.thread  # Save reference
                
                if thread_ref.isRunning():
                    logger.debug(f"Stopping thread: {thread_ref.objectName()}")
                    # Disconnect the thread's signals first
                    try:
                        thread_ref.started.disconnect()
                    except Exception:
                        pass  # Ignore errors
                        
                    try:
                        thread_ref.finished.disconnect()
                    except Exception:
                        pass  # Ignore errors
                        
                    # Now try to stop the thread
                    thread_ref.quit()
                    if not thread_ref.wait(2000):  # Wait up to 2 seconds
                        logger.warning(f"Thread unresponsive, force termination: {thread_ref.objectName()}")
                        thread_ref.terminate()
                        thread_ref.wait(1000)  # Wait another second to ensure termination
                    logger.debug(f"Thread stopped: {thread_ref.objectName()}")
                
                # Clear object references, but keep local references for completion
                self.thread = None
                
            # Finally ensure the thread is completely cleaned up
            if thread_ref:
                try:
                    # Ensure thread memory is released
                    thread_ref.deleteLater()
                except Exception as e:
                    logger.warning(f"Error deleting thread object: {e}")
                    
            # Clear all other references
            self.device_manager = None
            
        except Exception as e:
            logger.error(f"Error cleaning up SerialDeviceWorker resources: {e}")
        finally:
            # Regardless of success or failure, reset the cleanup flag
            self._is_cleaning = False
            logger.info("SerialDeviceWorker resources cleaned up")
                
    def __del__(self):
        """Destructor, ensure resources are released"""
        try:
            logger.debug("SerialDeviceWorker is being destroyed")
            # Avoid calling cleanup in the destructor, which may cause problems
        except Exception:
            # Avoid throwing exceptions in the destructor
            pass
    
    # External interface methods - these methods are called from the main thread, only emit signals
        
    def connect_device(self, device_id: str, port: str, baudrate: int, timeout: int):
        """Connect serial device - execute in worker thread by emitting signals
        
        Args:
            device_id: device ID
            port: serial port name
            baudrate: baud rate
            timeout: timeout (seconds)
        """
        logger.info(f"Request to connect device {device_id} to port {port}")
        self._connect_device_signal.emit(device_id, port, baudrate, timeout)
            
    def disconnect_device(self, device_id: str):
        """Disconnect device - execute in worker thread by emitting signals
        
        Args:
            device_id: device ID
        """
        logger.info(f"Request to disconnect device {device_id}")
        self._disconnect_device_signal.emit(device_id)
            
    def send_command(self, device_id: str, command: str, timeout: int):
        """Send command to device - execute in worker thread by emitting signals
        
        Args:
            device_id: device ID
            command: command to send
            timeout: timeout (seconds)
        """
        logger.info(f"Request to send command to device {device_id}: {command}")
        self._send_command_signal.emit(device_id, command, timeout)
    
    # Actual execution methods - these slots are executed in the worker thread
    
    @Slot(str, str, int, int)
    def _execute_connect_device(self, device_id: str, port: str, baudrate: int, timeout: int):
        """Actual execute device connection operation (in worker thread)"""
        try:
            logger.info(f"Connecting device {device_id} to port {port}")
            
            # Create device and connect
            device = self.device_manager.create_serial_device(device_id, port, baudrate, timeout)
            if not device:
                self.connection_result.emit(device_id, False, f"Failed to create device {device_id}")
                return
                
            success = device.connect()
            if success:
                self.connection_result.emit(device_id, True, f"Successfully connected device {device_id} to port {port}")
            else:
                self.connection_result.emit(device_id, False, f"Failed to connect device {device_id} to port {port}")
        except Exception as e:
            logger.error(f"Error connecting device {device_id}: {str(e)}")
            self.connection_result.emit(device_id, False, f"Error connecting device: {str(e)}")
    
    @Slot(str)        
    def _execute_disconnect_device(self, device_id: str):
        """Actual execute device disconnection operation (in worker thread)"""
        try:
            logger.info(f"Disconnecting device {device_id}")
            
            success = self.device_manager.disconnect_device(device_id)
            if success:
                self.disconnection_result.emit(device_id, True, f"Successfully disconnected device {device_id}")
            else:
                self.disconnection_result.emit(device_id, False, f"Failed to disconnect device {device_id}")
        except Exception as e:
            logger.error(f"Error disconnecting device {device_id}: {str(e)}")
            self.disconnection_result.emit(device_id, False, f"Error disconnecting device: {str(e)}")
    
    @Slot(str, str, int)        
    def _execute_send_command(self, device_id: str, command: str, timeout: int):
        """Actual execute send command operation (in worker thread)"""
        try:
            logger.info(f"Sending command to device {device_id}: {command}")
            
            # Execute command
            response = self.device_manager.send_command(device_id, command, timeout)
            logger.info(f"Command completed: {device_id}, {command}")
            self.command_result.emit(device_id, command, response)
        except Exception as e:
            logger.error(f"Error sending command {command} to device {device_id}: {str(e)}")
            self.command_result.emit(device_id, command, f"Error: {str(e)}")


if __name__ == "__main__":
    
    def main():
        from core.models.device_manager_model import DeviceManagerModel
        from util.logger import logger
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer

        # Create application
        app = QApplication(sys.argv)    
        device_manager = DeviceManagerModel()
        serial_device_worker = SerialDeviceWorker(device_manager)

        def on_connection_result(device_id, success, message):
            logger.info(f"Connection result: {device_id}, {success}, {message}")
            serial_device_worker.send_command("device1", "ls", 5)

        def on_disconnection_result(device_id, success, message):
            logger.info(f"Disconnection result: {device_id}, {success}, {message}")

        def on_command_result(device_id, command, response):
            logger.info(f"Command result: {device_id}, {command}, {response}")
            serial_device_worker.disconnect_device("device1")
        # Connect signals
        serial_device_worker.connection_result.connect(on_connection_result)
        serial_device_worker.disconnection_result.connect(on_disconnection_result)
        serial_device_worker.command_result.connect(on_command_result)

        # Test connection
        serial_device_worker.connect_device("device1", "COM4", 115200, 10)
        
        
        QTimer.singleShot(25000, lambda: serial_device_worker.cleanup())
        QTimer.singleShot(30000, lambda: QApplication.quit())
        sys.exit(app.exec())

    sys.exit(main())


