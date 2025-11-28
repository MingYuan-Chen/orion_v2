import os
import sys
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from core.models.serial_device_model import SerialDeviceModel
from core.view_models.device_view_model import DeviceViewModel
from core.views.main_view import MainView


def main():
    """
    The main entry point of the application.
    """
    # 1. Create the application instance
    app = QApplication(sys.argv)

    # --- Load and apply stylesheet ---
    style_file = Path(__file__).parent / "resources" / "themes" / "dark_theme.qss"
    if style_file.exists():
        with open(style_file, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    # ---

    # Set application name
    app.setApplicationName("Orion")
    app.setApplicationDisplayName("Serial Tool v2.1.0 20251128")
    app.setOrganizationName("Orion")
    app.setOrganizationDomain("orion.com")
    app.setApplicationVersion("2.1.0.0")

    # Set application icon
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        icon_path = os.path.join(sys._MEIPASS, 'resources', 'icons', 'header.ico')
    else:
        # Normal development environment
        icon_path = os.path.join(os.getcwd(), "resources", "icons", "header.ico")
    app.setWindowIcon(QIcon(icon_path))

    # 2. Create the Model, ViewModel, and View instances (MVVM setup)
    serial_model = SerialDeviceModel()
    device_view_model = DeviceViewModel(model=serial_model)
    main_view = MainView(view_model=device_view_model)

    # 3. Show the main window
    main_view.show()

    # 4. Start the Qt event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
