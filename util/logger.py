import logging
import os
from datetime import datetime

class Logger:
    """Logger class with file and console handlers"""
    _instance = None  # Singleton instance
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, project_name='Orion', log_level=logging.DEBUG):
        """Initialize logger with project name and log level"""
        # Only initialize once
        if self._initialized:
            return
            
        self.project_name = project_name
        self.logger = logging.getLogger(project_name.lower())
        self.logger.setLevel(log_level)
        
        # Prevent log duplication
        self.logger.propagate = False
        
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        # Generate log filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = f'logs/{self.project_name}_{timestamp}.log'
        
        # Configure log format
        self.formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(filename)s][%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Clear existing handlers (in case of re-initialization)
        if self.logger.handlers:
            self.logger.handlers.clear()
            
        # Add handlers
        self._add_file_handler()
        self._add_console_handler()
        
        self._initialized = True
        
        # Log initialization
        self.logger.info(f"Logger initialized for project: {self.project_name}")
        
    def _add_file_handler(self):
        """Add file handler to logger"""
        file_handler = logging.FileHandler(self.log_filename, encoding='utf-8')
        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)
        
    def _add_console_handler(self):
        """Add console handler to logger"""
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)
        
    def set_level(self, level: int):
        """Set log level
        Args:
            level: Log level (e.g., logging.DEBUG(10), logging.INFO(20), logging.WARNING(30), logging.ERROR(40), logging.CRITICAL(50))
        """
        self.logger.setLevel(level)
        
    def debug(self, message: str, **kwargs):
        """Log debug message with optional parameters"""
        self.logger.debug(message, **kwargs)
        
    def info(self, message: str, **kwargs):
        """Log info message with optional parameters"""
        self.logger.info(message, **kwargs)
        
    def warning(self, message: str, **kwargs):
        """Log warning message with optional parameters"""
        self.logger.warning(message, **kwargs)
        
    def error(self, message: str, **kwargs):
        """Log error message with optional parameters"""
        self.logger.error(message, **kwargs)
        
    def critical(self, message: str, **kwargs):
        """Log critical message with optional parameters"""
        self.logger.critical(message, **kwargs)

# Create default logger instance
logger = Logger().logger 