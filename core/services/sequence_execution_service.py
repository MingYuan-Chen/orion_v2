from PySide6.QtCore import QObject, Signal, QTimer, QEventLoop
from typing import List, Optional
from collections import deque
from core.models.serial_device_model import SerialDeviceModel

class SequenceExecutionService(QObject):
    """
    A service to execute a command and wait for a sequence of responses,
    ending with a specific marker.
    """
    command_completed = Signal(str)
    command_error = Signal(str)
    all_commands_completed = Signal()

    def __init__(self, device_model: SerialDeviceModel, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._device_model = device_model
        self._response_buffer = []
        self._end_markers = []
        self._event_loop = QEventLoop()
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)
        self._command_queue = deque()

        self._device_model.data_received.connect(self._on_data_received)
        self.command_completed.connect(self._on_command_completed)
        self.command_error.connect(self._on_command_error)

    def execute_sequence_commands(self, commands: List[str]):
        
        self._command_queue.extend(commands)
        self._execute_next_command()
    
    def _execute_next_command(self):
        if not self._command_queue:
            self.all_commands_completed.emit()
            return
        
        self._end_markers = ["#"]

        self._response_buffer.clear()
        current_command = self._command_queue.popleft()
        self._device_model.send_command(current_command)
        
        timeout = 10000 if "U-Boot" in current_command else 5000
        self._timer.start(timeout)
    
    def _on_data_received(self, data: str):
        """
        Slot to handle incoming data from the serial device.
        """
        
        # Check if any of the end markers are in the received data
        for marker in self._end_markers:
            if marker in data:
                self._timer.stop()
                self._finalize_command()
                return
            else:
                self._response_buffer.append(data)

    def _on_timeout(self):
        """
        Handles the case where the sequence times out.
        """
        self.command_error.emit("Sequence execution timed out.")

    def _finalize_command(self):
        """
        Finalizes the command by emitting the collected response.
        """
        full_response = "\n".join(self._response_buffer)
        self.command_completed.emit(full_response)
        self._response_buffer.clear()
    
    def _on_command_completed(self, response):
        if self._command_queue:
            self._execute_next_command()
    
    def _on_command_error(self, err_msg):
        self._timer.stop()
        self._command_queue.clear()
        self._end_markers = []