
import sys
import time
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

    # --- Load and apply stylesheet and icon ---
    if hasattr(sys, '_MEIPASS'):
        style_file = Path(sys._MEIPASS) / "resources" / "themes" / "dark_theme.qss"
        icon_path = Path(sys._MEIPASS) / "resources" / "icons" / "header.ico"
    else:
        style_file = Path(__file__).parent / "resources" / "themes" / "dark_theme.qss"
        icon_path = Path(__file__).parent / "resources" / "icons" / "header.ico"
    if style_file.exists():
        with open(style_file, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    # ---

    # Set application name
    app.setApplicationName("Orion")
    app.setApplicationDisplayName(f'Serial Tool v2.1.0_{time.strftime("%Y%m%d")}')
    app.setOrganizationName("Orion")
    app.setOrganizationDomain("orion.com")
    app.setApplicationVersion("2.1.0.0")

    # Set application icon
    app.setWindowIcon(QIcon(str(icon_path)))

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
