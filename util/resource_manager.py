
import sys
import os
import shutil
from util.logger import logger

def get_app_path():
    """取得應用程式的根目錄，無論是從原始碼執行還是作為打包後的 .exe 執行"""
    if getattr(sys, 'frozen', False):
        # 如果是打包後的 .exe
        return os.path.dirname(sys.executable)
    else:
        # 如果是從 .py 原始碼執行
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_resource_path(relative_path):
    """取得資源檔案的路徑，支援打包後的環境"""
    if getattr(sys, 'frozen', False):
        # 在打包後的環境中，資源通常位於 _MEIPASS 暫存資料夾
        base_path = sys._MEIPASS
    else:
        # 在開發環境中，資源位於專案根目錄
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    return os.path.join(base_path, relative_path)

def ensure_default_hw_configs():
    """
    確保預設的硬體設定檔存在於執行檔同層目錄。
    如果 hw_config 資料夾或其中的 JSON 檔案不存在，則會自動建立。
    """
    app_path = get_app_path()
    target_config_dir = os.path.join(app_path, 'hw_config')

    # 預設的設定檔清單
    default_configs = [
        "argo_VN240014_20251113.json",
        "argo_VN240018_20251112.json",
        "athena_Small_24622000013_20251117.json",
        "gemini_10FHD210010_20251113.json",
        "gemini_fhd_CP240765_20251113.json",
        "hydra_fhd_CQ241891_20251112.json",
        "hydra_hd_CN190024_20251113.json"
    ]

    # 1. 確保目標 hw_config 資料夾存在
    if not os.path.exists(target_config_dir):
        logger.debug(f"Creating directory: {target_config_dir}")
        os.makedirs(target_config_dir)

    # 2. 檢查並複製預設設定檔
    for config_file in default_configs:
        target_file_path = os.path.join(target_config_dir, config_file)
        
        if not os.path.exists(target_file_path):
            logger.debug(f"'{config_file}' not found. Creating it from source...")
            try:
                # 取得原始設定檔的路徑
                source_file_path = get_resource_path(os.path.join('hw_config', config_file))
                
                if os.path.exists(source_file_path):
                    # 複製檔案
                    shutil.copy2(source_file_path, target_file_path)
                    logger.debug(f"Successfully created '{config_file}'.")
                else:
                    logger.debug(f"Error: Source file not found at '{source_file_path}'. Cannot create '{config_file}'.")
            except Exception as e:
                logger.debug(f"Error creating '{config_file}': {e}")

if __name__ == '__main__':
    # 用於測試
    logger.debug(f"Application Path: {get_app_path()}")
    ensure_default_hw_configs()
    logger.debug("Default hardware configuration check complete.")
