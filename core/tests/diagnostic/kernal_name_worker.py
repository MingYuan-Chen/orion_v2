"""
Diagnostic kernal name test worker module
Implement diagnostic kernal name test for device
"""
from typing import List, Tuple
from core.tests.base_test_worker import BaseTestWorker, TestStep
from util.logger import logger


class KernalNameWorker(BaseTestWorker):
    """Diagnostic kernal name worker, implement diagnostic kernal name test for device"""
    
    def __init__(self, device_worker, continue_on_failure=True, platform_name="hydra"):
        super().__init__(device_worker, continue_on_failure=continue_on_failure, platform_name=platform_name)
    
    def _validate_kernal_name(self, response: str) -> Tuple[bool, str]:
        """
        验证内核名称是否为Linux gemini
        
        Args:
            response: 命令执行结果
            
        Returns:
            (success, message): 验证结果
        """
        # 记录完整的响应以便调试和导出报告
        logger.info(f"Kernal name full response: {response}")
        
        # 检查响应中是否包含"Linux gemini"
        if "Linux gemini" in response:
            return True, f"Kernal name check passed. Full info: {response}"
        else:
            return False, f"Kernal name check failed. Full info: {response}"
    
    def prepare_test_steps(self) -> List[TestStep]:
        """
        Prepare diagnostic kernal name test steps
        
        Returns:
            diagnostic kernal name test steps list
        """
        return [
            TestStep(
                command="uname -a", 
                validation_func=self._validate_kernal_name,  # 使用自定义验证函数
                timeout=5, 
                description="Check kernal name",
                max_retries=1,
                retry_delay=500
            )
        ]

