"""
CPU Stress Test Service

提供 CPU 壓力測試功能，可以控制 CPU 負載百分比和持續時間
通過時間片控制的方式達到指定的 CPU 負載水平
"""

from PySide6.QtCore import QObject, Signal, Slot, QTimer
from typing import Optional
from util.logger import logger

class CpuStressService(QObject):
    """
    CPU 壓力測試服務
    提供可控制的 CPU 負載測試功能
    """
    # 定義信號
    stress_started = Signal(str, int, int)    # device_id, loading_percent, duration_seconds
    stress_completed = Signal(str, str)       # device_id, message
    stress_error = Signal(str, str)           # device_id, error_message
    stress_progress = Signal(str, int, int)   # device_id, elapsed_seconds, total_seconds
    
    def __init__(self, serial_worker):
        """
        初始化 CPU 壓力測試服務
        
        Args:
            serial_worker: 串列設備工作器，用於命令執行
        """
        super().__init__()
        self.serial_worker = serial_worker
        
        # 服務狀態
        self.is_running = False
        self.current_device_id = None
        self.loading_percent = 0
        self.duration_seconds = 0
        self.elapsed_seconds = 0
        
        # 時間控制
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._on_progress_update)
        
        self.completion_timer = QTimer()
        self.completion_timer.setSingleShot(True)
        self.completion_timer.timeout.connect(self._on_stress_completed)
        
        # CPU 核心數（預設值，會在執行時偵測）
        self.cpu_cores = 4
        
        # 壓力測試進程 PID 列表
        self.stress_pids = []
        
        logger.info("CPU stress service initialized")
    
    def start_stress_test(self, device_id: str, loading_percent: int, duration_seconds: int) -> bool:
        """
        開始 CPU 壓力測試
        
        Args:
            device_id: 目標設備 ID
            loading_percent: CPU 負載百分比 (1-100)
            duration_seconds: 持續時間（秒）
            
        Returns:
            bool: 是否成功啟動測試
        """
        # 檢查是否已經在運行
        if self.is_running:
            logger.warning(f"CPU stress test already running for device: {self.current_device_id}")
            return False
        
        # 參數驗證
        if not (1 <= loading_percent <= 100):
            error_msg = f"Invalid loading percent: {loading_percent}. Must be between 1-100."
            logger.error(error_msg)
            self.stress_error.emit(device_id, error_msg)
            return False
        
        if duration_seconds < 0:
            error_msg = f"Invalid duration: {duration_seconds}. Must be 0 (unlimited) or greater than 0."
            logger.error(error_msg)
            self.stress_error.emit(device_id, error_msg)
            return False
        
        # 設定測試參數
        self.current_device_id = device_id
        self.loading_percent = loading_percent
        self.duration_seconds = duration_seconds
        self.elapsed_seconds = 0
        self.is_running = True
        
        logger.info(f"Starting CPU stress test: device={device_id}, loading={loading_percent}%, duration={duration_seconds}s")
        
        # 發出測試開始信號
        self.stress_started.emit(device_id, loading_percent, duration_seconds)
        
        # 第一步：偵測 CPU 核心數
        self._detect_cpu_cores()
        
        return True
    
    def stop_stress_test(self, device_id: str = None) -> bool:
        """
        停止 CPU 壓力測試
        
        Args:
            device_id: 設備 ID，如果為 None 則停止當前測試
            
        Returns:
            bool: 是否成功停止測試
        """
        if not self.is_running:
            logger.debug("No active CPU stress test to stop")
            return False
        
        if device_id and device_id != self.current_device_id:
            logger.debug(f"No active stress test for device {device_id}")
            return False
        
        logger.info(f"Stopping CPU stress test for device: {self.current_device_id}")
        
        # 停止計時器
        self.progress_timer.stop()
        self.completion_timer.stop()
        
        # 發送停止命令
        self._send_stop_commands()
        
        return True
    
    def _detect_cpu_cores(self):
        """偵測 CPU 核心數"""
        try:
            # 發送 nproc 命令偵測 CPU 核心數
            command = "nproc"
            logger.debug(f"Detecting CPU cores: {command}")
            self.serial_worker.send_command(self.current_device_id, command, 5)
            
            # 連接命令結果處理
            if not hasattr(self, '_command_connection') or not self._command_connection:
                self._command_connection = self.serial_worker.command_result.connect(self._on_command_result)
                
        except Exception as e:
            logger.error(f"Error detecting CPU cores: {e}")
            # 使用預設值繼續
            self.cpu_cores = 4
            self._start_stress_commands()
    
    def _start_stress_commands(self):
        """開始壓力測試命令"""
        try:
            # 計算時間片參數
            work_time_ms = int(self.loading_percent * 10)  # 每秒工作的毫秒數
            sleep_time_ms = 1000 - work_time_ms            # 每秒休息的毫秒數
            
            logger.info(f"Starting stress test with {self.cpu_cores} cores, "
                       f"work cycle: {work_time_ms}ms work, {sleep_time_ms}ms sleep")
            
            # 生成壓力測試腳本
            stress_script = self._generate_stress_script(work_time_ms, sleep_time_ms)
            
            # 發送壓力測試命令
            self.serial_worker.send_command(self.current_device_id, stress_script, 10)
            
            # 啟動進度計時器（每秒更新一次）
            self.progress_timer.start(1000)
            
            # 設定完成計時器（只有在有限時間時才啟動）
            if self.duration_seconds > 0:
                self.completion_timer.start(self.duration_seconds * 1000)
            # 如果 duration_seconds == 0，則無限執行直到手動停止
            
        except Exception as e:
            logger.error(f"Error starting stress commands: {e}")
            self._handle_error(f"Failed to start stress test: {e}")
    
    def _generate_stress_script(self, work_time_ms: int, sleep_time_ms: int) -> str:
        """
        生成壓力測試腳本
        
        Args:
            work_time_ms: 工作時間（毫秒）
            sleep_time_ms: 休息時間（毫秒）
            
        Returns:
            壓力測試命令字串
        """
        # 轉換為秒數
        work_time = work_time_ms / 1000.0
        sleep_time = sleep_time_ms / 1000.0
        
        # 生成多核心壓力測試腳本
        # 使用背景進程來控制每個核心的負載
        script_lines = []
        script_lines.append("# CPU Stress Test Script")
        script_lines.append(f"# Target: {self.loading_percent}% load for {self.duration_seconds}s")
        
        # 為每個 CPU 核心創建一個控制迴圈
        for core in range(self.cpu_cores):
            script_lines.append(f"(")
            if self.duration_seconds == 0:
                # 無限時間執行
                script_lines.append(f"  while true; do")
            else:
                # 有限時間執行
                script_lines.append(f"  end_time=$(($(date +%s) + {self.duration_seconds}))")
                script_lines.append(f"  while [ $(date +%s) -lt $end_time ]; do")
            script_lines.append(f"    timeout {work_time}s yes > /dev/null 2>&1")
            script_lines.append(f"    sleep {sleep_time}")
            script_lines.append(f"  done")
            script_lines.append(f") &")
        
        script_lines.append("echo 'CPU stress test started'")
        
        # 合併成單一命令
        script = " && ".join([line for line in script_lines if not line.startswith("#")])
        
        return script
    
    def _send_stop_commands(self):
        """發送停止命令"""
        try:
            # 殺死所有 yes 進程
            stop_command = "killall yes 2>/dev/null || echo 'stress processes stopped'"
            logger.debug(f"Sending stop command: {stop_command}")
            self.serial_worker.send_command(self.current_device_id, stop_command, 5)
            
        except Exception as e:
            logger.error(f"Error sending stop commands: {e}")
        finally:
            # 重置服務狀態
            self._reset_service_state()
    
    def _reset_service_state(self):
        """重置服務狀態"""
        self.is_running = False
        self.current_device_id = None
        self.loading_percent = 0
        self.duration_seconds = 0
        self.elapsed_seconds = 0
        self.stress_pids = []
        
        # 停止計時器
        self.progress_timer.stop()
        self.completion_timer.stop()
        
        # 斷開信號連接
        if hasattr(self, '_command_connection') and self._command_connection:
            try:
                self.serial_worker.command_result.disconnect(self._on_command_result)
                self._command_connection = None
            except Exception:
                pass
    
    def _handle_error(self, error_message: str):
        """處理錯誤"""
        logger.error(f"CPU stress test error: {error_message}")
        device_id = self.current_device_id
        
        # 嘗試清理
        self._send_stop_commands()
        
        # 發出錯誤信號
        self.stress_error.emit(device_id, error_message)
    
    @Slot()
    def _on_progress_update(self):
        """進度更新處理"""
        if not self.is_running:
            return
        
        self.elapsed_seconds += 1
        
        # 發出進度信號
        self.stress_progress.emit(
            self.current_device_id, 
            self.elapsed_seconds, 
            self.duration_seconds
        )
        
        logger.debug(f"CPU stress progress: {self.elapsed_seconds}/{self.duration_seconds}s")
    
    @Slot()
    def _on_stress_completed(self):
        """壓力測試完成處理"""
        if not self.is_running:
            return
        
        logger.info(f"CPU stress test completed for device: {self.current_device_id}")
        
        device_id = self.current_device_id
        if self.duration_seconds == 0:
            completion_message = f"CPU stress test completed successfully. " \
                               f"Loading: {self.loading_percent}%, Duration: unlimited ({self.elapsed_seconds}s elapsed)"
        else:
            completion_message = f"CPU stress test completed successfully. " \
                               f"Loading: {self.loading_percent}%, Duration: {self.duration_seconds}s"
        
        # 發送停止命令
        self._send_stop_commands()
        
        # 發出完成信號
        self.stress_completed.emit(device_id, completion_message)
    
    @Slot(str, str, str)
    def _on_command_result(self, device_id: str, command: str, response: str):
        """
        處理命令執行結果
        
        Args:
            device_id: 設備 ID
            command: 執行的命令
            response: 命令回應
        """
        # 確保是當前設備的回應
        if device_id != self.current_device_id or not self.is_running:
            return
        
        try:
            # 處理 nproc 命令的回應
            if "nproc" in command:
                self._handle_nproc_response(response)
            
            # 處理壓力測試開始確認
            elif "CPU stress test started" in response or "stress test started" in response:
                logger.info(f"CPU stress test confirmed started on device: {device_id}")
            
            # 處理停止命令回應
            elif "stress processes stopped" in response or "killall" in command:
                logger.info(f"CPU stress test processes stopped on device: {device_id}")
            
        except Exception as e:
            logger.error(f"Error processing command result: {e}")
    
    def _handle_nproc_response(self, response: str):
        """處理 nproc 命令回應"""
        try:
            # 解析 CPU 核心數
            lines = response.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.isdigit():
                    detected_cores = int(line)
                    if 1 <= detected_cores <= 32:  # 合理範圍
                        self.cpu_cores = detected_cores
                        logger.info(f"Detected {self.cpu_cores} CPU cores")
                        break
            
            # 開始壓力測試
            self._start_stress_commands()
            
        except Exception as e:
            logger.warning(f"Failed to parse CPU cores from response: {response}, error: {e}")
            # 使用預設值
            self.cpu_cores = 4
            self._start_stress_commands()
    
    def get_status(self) -> dict:
        """
        取得服務狀態
        
        Returns:
            dict: 服務狀態資訊
        """
        return {
            "is_running": self.is_running,
            "device_id": self.current_device_id,
            "loading_percent": self.loading_percent,
            "duration_seconds": self.duration_seconds,
            "elapsed_seconds": self.elapsed_seconds,
            "cpu_cores": self.cpu_cores,
            "progress_percent": round((self.elapsed_seconds / self.duration_seconds) * 100, 1) if self.duration_seconds > 0 else 0
        }
    
    def cleanup(self):
        """清理資源"""
        # 如果正在運行，先停止
        if self.is_running:
            self.stop_stress_test()
        
        # 清理狀態
        self._reset_service_state()
        
        logger.info("CPU stress service cleaned up")


if __name__ == "__main__":
    """測試 CPU 壓力測試服務"""
    from core.workers.serial_device_worker import SerialDeviceWorker
    from core.models.device_manager_model import DeviceManagerModel
    from PySide6.QtWidgets import QApplication
    import sys
    
    def main():
        # 創建應用程式
        app = QApplication(sys.argv)
        device_manager = DeviceManagerModel()
        serial_device_worker = SerialDeviceWorker(device_manager)
        
        # 連接設備（需要根據實際情況調整）
        # serial_device_worker.connect_device("device1", "COM4", 115200, 10)
        
        # 創建 CPU 壓力測試服務
        cpu_stress_service = CpuStressService(serial_device_worker)
        
        def on_stress_started(device_id, loading, duration):
            logger.info(f"Stress test started: {device_id}, {loading}%, {duration}s")
        
        def on_stress_completed(device_id, message):
            logger.info(f"Stress test completed: {device_id}, {message}")
        
        def on_stress_error(device_id, error):
            logger.error(f"Stress test error: {device_id}, {error}")
        
        def on_stress_progress(device_id, elapsed, total):
            logger.info(f"Stress test progress: {device_id}, {elapsed}/{total}s")
        
        # 連接信號
        cpu_stress_service.stress_started.connect(on_stress_started)
        cpu_stress_service.stress_completed.connect(on_stress_completed)
        cpu_stress_service.stress_error.connect(on_stress_error)
        cpu_stress_service.stress_progress.connect(on_stress_progress)
        
        # 測試 CPU 壓力測試服務
        # cpu_stress_service.start_stress_test("device1", 60, 30)  # 60% 負載，30 秒
        
        sys.exit(app.exec())
    
    if __name__ == "__main__":
        main()