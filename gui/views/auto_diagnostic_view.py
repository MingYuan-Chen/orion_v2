"""
Auto diagnostic view module
Responsible for managing diagnostic test execution and UI updates
"""

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from typing import Dict, List, Any, Optional
import datetime

from core.services.hardware_test_manager import HardwareTestManagerService
from gui.widgets.diagnostic_container import DiagnosticContainer
from util.logger import logger

class AutoDiagnosticView(QObject):
    """
    Auto diagnostic view controller
    Manages diagnostic test execution and UI updates
    """
    
    # 定义信号
    all_diagnostics_completed = Signal()  # 所有诊断测试完成时发出
    export_report_requested = Signal()    # 请求导出报告时发出
    
    def __init__(self, device_id: str, hw_test_manager: HardwareTestManagerService):
        """
        初始化自动诊断视图
        
        Args:
            device_id: 设备ID
            hw_test_manager: 硬件测试管理器服务
        """
        super().__init__()
        
        # 保存设备ID和硬件测试管理器
        self.device_id = device_id
        self.hw_test_manager = hw_test_manager
        
        # UI组件引用
        self.main_widget = None
        self.diagnostic_container = None
        self.run_all_button = None
        self.export_button = None
        self.title_label = None
        
        # 测试状态跟踪
        self.diagnostic_results = {}
        self.current_diagnostics = []
        self.is_running = False
        
        # 连接信号
        self._connect_signals()
        
        logger.info("Auto diagnostic view initialized")
    
    def _connect_signals(self):
        """连接硬件测试管理器信号"""
        # 连接硬件测试管理器信号
        self.hw_test_manager.test_started.connect(self._on_test_started)
        self.hw_test_manager.test_completed.connect(self._on_test_completed)
        self.hw_test_manager.test_progress.connect(self._on_test_progress)
    
    def create_widget(self) -> QWidget:
        """
        创建并返回自动诊断主部件
        
        Returns:
            QWidget: 自动诊断主部件
        """
        # 创建主部件
        self.main_widget = QWidget()
        self.main_widget.setObjectName("diagnosticWidget")
        self.main_widget.setStyleSheet("""
            QWidget#diagnosticWidget {
                background-color: #1E1E1E;
                color: white;
                border-radius: 5px;
            }
            QLabel#titleLabel {
                font-weight: bold;
                font-size: 14px;
                color: #4FC3F7;
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1C97EA;
            }
        """)
        
        # 创建主布局
        main_layout = QVBoxLayout(self.main_widget)
        main_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.setSpacing(5)
        
        # 创建顶部布局（标题和按钮）
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题
        self.title_label = QLabel("Auto Diagnostic")
        self.title_label.setObjectName("titleLabel")
        top_layout.addWidget(self.title_label)
        
        # 添加弹性空间
        top_layout.addStretch()
        
        # 导出报告按钮
        self.export_button = QPushButton("Export Report")
        self.export_button.clicked.connect(self._on_export_report)
        top_layout.addWidget(self.export_button)
        
        # 间隔
        top_layout.addSpacing(10)
        
        # 运行所有测试按钮
        self.run_all_button = QPushButton("Run All Tests")
        self.run_all_button.clicked.connect(self._on_run_all_tests)
        top_layout.addWidget(self.run_all_button)
        
        # 添加顶部布局到主布局
        main_layout.addLayout(top_layout)
        
        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #333333;")
        line.setMaximumHeight(1)
        main_layout.addWidget(line)
        
        # 创建诊断容器
        self.diagnostic_container = DiagnosticContainer()
        
        # 计算项目高度和可见项目数
        item_height = 32  # 每个诊断项目高度
        visible_items = 5  # 可见项目数
        
        # 设置诊断容器高度
        scroll_height = item_height * visible_items + 15
        self.diagnostic_container.set_fixed_height(scroll_height)
        
        # 添加诊断容器到主布局
        main_layout.addWidget(self.diagnostic_container)
        
        # 设置主部件固定高度
        total_height = scroll_height + 60  # 标题区域约占60像素
        self.main_widget.setFixedHeight(total_height)
        
        return self.main_widget
    
    def setup_diagnostic_items(self, diagnostic_tests):
        """
        设置诊断测试项目
        
        Args:
            diagnostic_tests: 字典，键为测试ID，值为测试名称
        """
        # 清空现有项目
        if self.diagnostic_container:
            for test_id in self.diagnostic_container.get_all_test_ids():
                # 移除项目（暂不实现，因为DiagnosticContainer没有移除方法）
                pass
        
        # 添加诊断测试项目
        for test_id, test_name in diagnostic_tests.items():
            self.diagnostic_container.add_diagnostic_item(test_id, test_name)
            self.diagnostic_results[test_id] = {
                "status": "PENDING",
                "time": "--:--:--",
                "details": {}
            }
            
        # 记录所有诊断项目
        self.current_diagnostics = list(diagnostic_tests.keys())
    
    def _on_run_all_tests(self):
        """处理运行所有测试按钮点击"""
        if self.is_running:
            return
            
        self.is_running = True
        self.run_all_button.setText("Running...")
        self.run_all_button.setEnabled(False)
        
        # 重置所有诊断项目状态
        self.diagnostic_container.reset_all_items()
        
        # 开始运行测试序列
        self._run_diagnostic_sequence()
        
        logger.info("Starting auto diagnostic sequence")
    
    def _run_diagnostic_sequence(self):
        """运行诊断测试序列"""
        # 获取所有测试ID
        test_ids = self.diagnostic_container.get_all_test_ids()
        
        # 逐个执行测试
        for test_id in test_ids:
            # 开始测试
            self.hw_test_manager.start_test(self.device_id, test_id)
            
            # 记录开始时间
            start_time = datetime.datetime.now()
            self.diagnostic_results[test_id]["start_time"] = start_time
    
    def _on_export_report(self):
        """处理导出报告按钮点击"""
        # 发出导出报告请求信号
        self.export_report_requested.emit()
        
        logger.info("Export diagnostic report requested")
    
    @Slot(str)
    def _on_test_started(self, test_id: str):
        """
        处理测试开始事件
        
        Args:
            test_id: 测试ID
        """
        # 更新UI状态
        self.diagnostic_container.update_item_status(test_id, "PENDING")
        
        logger.info(f"Diagnostic test started: {test_id}")
    
    @Slot(str, bool, str)
    def _on_test_completed(self, test_id: str, success: bool, message: str):
        """
        处理测试完成事件
        
        Args:
            test_id: 测试ID
            success: 测试是否成功
            message: 结果消息
        """
        # 计算测试耗时
        if test_id in self.diagnostic_results and "start_time" in self.diagnostic_results[test_id]:
            start_time = self.diagnostic_results[test_id]["start_time"]
            end_time = datetime.datetime.now()
            duration = end_time - start_time
            time_str = f"{duration.seconds}.{duration.microseconds//1000:03d}s"
        else:
            time_str = "--:--:--"
        
        # 更新诊断结果
        status = "PASS" if success else "FAIL"
        self.diagnostic_results[test_id]["status"] = status
        self.diagnostic_results[test_id]["time"] = time_str
        self.diagnostic_results[test_id]["message"] = message
        
        # 更新UI状态
        self.diagnostic_container.update_item_status(test_id, status, time_str)
        
        # 检查是否所有测试都已完成
        all_completed = True
        for test_id in self.current_diagnostics:
            status = self.diagnostic_results[test_id]["status"]
            if status == "PENDING":
                all_completed = False
                break
        
        if all_completed:
            self._complete_all_diagnostics()
        
        # 记录测试完成
        if success:
            logger.info(f"Diagnostic test {test_id} completed: PASS ({time_str})")
        else:
            logger.error(f"Diagnostic test {test_id} failed: {message} ({time_str})")
    
    @Slot(str, int, int)
    def _on_test_progress(self, test_id: str, current_step: int, total_steps: int):
        """
        处理测试进度事件
        
        Args:
            test_id: 测试ID
            current_step: 当前步骤索引（从1开始）
            total_steps: 总步骤数
        """
        # 暂不更新UI进度，因为诊断项目没有进度条
        pass
    
    def _complete_all_diagnostics(self):
        """完成所有诊断测试"""
        self.is_running = False
        
        # 恢复按钮状态
        self.run_all_button.setText("Run All Tests")
        self.run_all_button.setEnabled(True)
        
        # 发出所有诊断测试完成信号
        self.all_diagnostics_completed.emit()
        
        logger.info("All diagnostic tests completed")
    
    def get_diagnostic_results(self) -> Dict[str, Dict[str, Any]]:
        """
        获取诊断结果
        
        Returns:
            包含诊断结果的字典
        """
        return self.diagnostic_results
    
    def cleanup(self):
        """清理资源"""
        try:
            logger.debug("Cleaning up AutoDiagnosticView resources")
            
            # 断开所有信号
            try:
                self.hw_test_manager.test_started.disconnect(self._on_test_started)
                self.hw_test_manager.test_completed.disconnect(self._on_test_completed)
                self.hw_test_manager.test_progress.disconnect(self._on_test_progress)
                
                if self.run_all_button:
                    self.run_all_button.clicked.disconnect(self._on_run_all_tests)
                
                if self.export_button:
                    self.export_button.clicked.disconnect(self._on_export_report)
            except Exception:
                # 信号可能已经断开，忽略错误
                pass
            
            # 清除引用
            self.diagnostic_container = None
            self.run_all_button = None
            self.export_button = None
            self.title_label = None
            self.main_widget = None
            
        except Exception as e:
            logger.error(f"Error during AutoDiagnosticView cleanup: {e}")
    
    def set_buttons_enabled(self, enabled=True):
        """
        启用或禁用所有按钮
        
        Args:
            enabled: 是否启用按钮
        """
        if self.run_all_button:
            self.run_all_button.setEnabled(enabled)
        
        if self.export_button:
            self.export_button.setEnabled(enabled) 