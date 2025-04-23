# VT Hydra Device Management System

![Version](https://img.shields.io/badge/version-2.5.0.4-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-green)
![Qt](https://img.shields.io/badge/Qt-PySide6-orange)

A comprehensive monitoring and testing system for Hydra series hardware devices, providing real-time system information, diagnostic tools, and hardware testing capabilities.

## Features

- **Real-time Device Monitoring**
  - System information dashboard (CPU, memory, storage)
  - Battery status monitoring (charge level, voltage, current, temperature)
  - Customizable information display with editable fields

- **Hardware Testing Suite**
  - USB ports testing
  - eMMC storage testing
  - EEPROM testing
  - Step-by-step test progress tracking

- **System Logs**
  - Real-time log viewing and filtering
  - Command execution interface
  - Log level and time range filtering

- **User-Friendly Interface**
  - Modern dark theme UI
  - Multi-device support
  - Responsive layout

## System Requirements

- Python 3.8 or higher
- Operating Systems:
  - Windows 10 or later
  - Linux (Ubuntu 20.04 or later recommended)
  - macOS 10.14 or later
- Minimum 4GB RAM
- 200MB free disk space

## Installation

### Dependencies

```bash
# Install required packages
pip install -r requirements.txt
```

### Configuration

1. Connect your Hydra device to your computer via USB
2. Ensure the serial port is accessible
3. Set up appropriate permissions if needed (especially on Linux)

## Usage

### Starting the Application

```bash
# Start the application
python main.py
```

### Connecting to a Device

1. In the main window, click "Connect"
2. Select the appropriate serial port
3. Click "Connect" to establish communication with the device

### System Monitoring

- The "Dashboard" tab displays real-time system information
- Click "Refresh" to update the information
- Use the edit buttons to modify device information fields

### Running Hardware Tests

1. Navigate to the "Functionality Test" tab
2. Select the desired test (USB, eMMC, or EEPROM)
3. Click "Start Test" to begin the testing process
4. View real-time test results and progress

### Viewing System Logs

1. Navigate to the "System Logs" tab
2. Use the filtering options to focus on specific log levels or time periods
3. Use the command input to send commands directly to the device

## Project Structure

```
VT_Hydra_2504_v2/
├── core/
│   ├── models/         # Data models
│   ├── services/       # Business logic services
│   ├── workers/        # Background workers
│   └── tests/          # Hardware test workers
├── gui/
│   ├── ui/             # UI definition files
│   ├── views/          # View controllers
│   └── view_models/    # View models (MVVM pattern)
├── resources/
│   └── icons/          # Application icons
├── util/
│   └── logger.py       # Logging utilities
├── main.py             # Application entry point
└── requirements.txt    # Python dependencies
```

## Troubleshooting

### Common Issues

1. **Device not detected**
   - Ensure device is properly connected
   - Check if the correct driver is installed
   - Verify that the device is powered on

2. **Tests failing**
   - Check physical connections
   - Ensure device firmware is up to date
   - Refer to device documentation for specific test requirements

3. **UI not responding**
   - Check system resources (CPU/memory usage)
   - Restart the application
   - Verify Python and PySide6 installation

## Development

### Building from Source

```bash
# Clone the repository
git clone https://192.168.26.172:8080/VT_Hydra_2504.git
cd VT_Hydra_2504

# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest
```

### Creating Executable

```bash
# Using PyInstaller
pyinstaller main.spec
```

## License

Copyright © 2025. All rights reserved.

---

*For technical support, please contact frank_chen@promate.com* 