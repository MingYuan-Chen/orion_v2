import sys
import serial
import serial.tools.list_ports
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QComboBox, QMessageBox
)
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QTextCursor


# ============================
# QThread：負責背景監聽 serial
# ============================
class SerialWorker(QThread):
    received = Signal(str)
    error = Signal(str)

    def __init__(self, ser):
        super().__init__()
        self.ser = ser
        self.running = True

    def run(self):
        try:
            while self.running and self.ser.is_open:
                if self.ser.in_waiting:
                    data = self.ser.readline().decode(errors='ignore').strip()
                    if data:
                        self.received.emit(data)
                self.msleep(20)
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


# ============================
# 主 UI
# ============================
class SerialTerminal(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 Mini Tera Term")
        self.resize(600, 450)

        # Serial object
        self.ser = None
        self.worker = None

        layout = QVBoxLayout(self)

        # ===== Connection panel =====
        conn_layout = QHBoxLayout()

        conn_layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.port_combo.addItems([p.device for p in serial.tools.list_ports.comports()])
        conn_layout.addWidget(self.port_combo)

        conn_layout.addWidget(QLabel("Baudrate:"))
        self.baud_edit = QLineEdit("115200")
        conn_layout.addWidget(self.baud_edit)

        conn_layout.addWidget(QLabel("Timeout(s):"))
        self.timeout_edit = QLineEdit("1")
        self.timeout_edit.setFixedWidth(40)
        conn_layout.addWidget(self.timeout_edit)

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clicked.connect(self.connect_serial)
        conn_layout.addWidget(self.btn_connect)

        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.clicked.connect(self.disconnect_serial)
        conn_layout.addWidget(self.btn_disconnect)

        layout.addLayout(conn_layout)

        # ===== Terminal Area =====
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        layout.addWidget(self.text_area)

        # ===== Command input =====
        cmd_layout = QHBoxLayout()
        cmd_layout.addWidget(QLabel("Command:"))
        self.cmd_edit = QLineEdit()
        cmd_layout.addWidget(self.cmd_edit)

        btn_send = QPushButton("Send")
        btn_send.clicked.connect(self.send_command)
        cmd_layout.addWidget(btn_send)

        layout.addLayout(cmd_layout)

    # ======================
    # Connect Serial
    # ======================
    def connect_serial(self):
        try:
            port = self.port_combo.currentText()
            baud = int(self.baud_edit.text())
            timeout = float(self.timeout_edit.text())

            self.ser = serial.Serial(port, baudrate=baud, timeout=timeout)

            # 啟動背景讀取 Thread
            self.worker = SerialWorker(self.ser)
            self.worker.received.connect(self.on_received)
            self.worker.error.connect(self.on_error)
            self.worker.start()

            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)

            self.write_text(f"[INFO] Connected to {port} @ {baud} bps\n")

        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))

    # ======================
    # Disconnect Serial
    # ======================
    def disconnect_serial(self):
        if self.worker:
            self.worker.stop()

        if self.ser and self.ser.is_open:
            self.ser.close()

        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)

        self.write_text("[INFO] Disconnected.\n")

    # ======================
    # Send Command
    # ======================
    def send_command(self):
        if self.ser and self.ser.is_open:
            cmd = self.cmd_edit.text().strip()
            if cmd:
                self.ser.write((cmd + "\r\n").encode())
                self.write_text(f"[TX] {cmd}\n")
                self.cmd_edit.clear()
        else:
            QMessageBox.warning(self, "Not Connected", "Please connect to a serial port first.")

    # ======================
    # UI update handlers
    # ======================
    def on_received(self, msg):
        self.write_text(f"[DEVICE] {msg}\n")

    def on_error(self, msg):
        self.write_text(f"[ERROR] {msg}\n")

    # ======================
    # Write text to terminal
    # ======================
    def write_text(self, msg):
        self.text_area.append(msg)
        self.text_area.moveCursor(QTextCursor.End)


# ============================
# Main Entry
# ============================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SerialTerminal()
    window.show()
    sys.exit(app.exec())
    
