# VT Hydra 裝置管理系統

![版本](https://img.shields.io/badge/version-1.0.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-green)
![Qt](https://img.shields.io/badge/Qt-PySide6-orange)

一套全方位的 Hydra 系列硬體裝置監控與測試系統，提供即時系統資訊、診斷工具及硬體測試功能。

## 功能特色

- **即時裝置監控**
  - 系統資訊儀表板（CPU、記憶體、儲存空間）
  - 電池狀態監控（電量、電壓、電流、溫度）
  - 可自訂資訊顯示與可編輯欄位

- **硬體測試套件**
  - USB 連接埠測試
  - eMMC 儲存測試
  - EEPROM 測試
  - 逐步測試進度追蹤

- **系統日誌**
  - 即時日誌檢視與篩選
  - 命令執行介面
  - 日誌等級與時間範圍篩選

- **友善使用者介面**
  - 現代化深色主題 UI
  - 多裝置支援
  - 響應式版面配置

## 系統需求

- Python 3.8 或更高版本
- 作業系統：
  - Windows 10 或更新版本
  - Linux（建議 Ubuntu 20.04 或更新版本）
  - macOS 10.14 或更新版本
- 至少 4GB 記憶體
- 200MB 可用磁碟空間

## 安裝方式

### 相依套件

```bash
# 安裝所需套件
pip install -r requirements.txt
```

### 設定

1. 透過 USB 將 Hydra 裝置連接至電腦
2. 確保序列埠可以存取
3. 必要時設定適當的權限（特別是在 Linux 上）

## 使用方式

### 啟動應用程式

```bash
# 啟動應用程式
python main.py
```

### 連接裝置

1. 在主視窗中，點擊「連接」
2. 選擇適當的序列埠
3. 點擊「連接」以建立與裝置的通訊

### 系統監控

- 「儀表板」分頁顯示即時系統資訊
- 點擊「重新整理」更新資訊
- 使用編輯按鈕修改裝置資訊欄位

### 執行硬體測試

1. 導航至「功能測試」分頁
2. 選擇所需的測試（USB、eMMC 或 EEPROM）
3. 點擊「開始測試」以啟動測試程序
4. 檢視即時測試結果和進度

### 檢視系統日誌

1. 導航至「系統日誌」分頁
2. 使用篩選選項專注於特定日誌等級或時間期間
3. 使用命令輸入欄直接傳送命令至裝置

## 專案結構

```
VT_Hydra_2504_v2/
├── core/
│   ├── models/         # 資料模型
│   ├── services/       # 業務邏輯服務
│   ├── workers/        # 背景工作執行緒
│   └── tests/          # 硬體測試工作執行緒
├── gui/
│   ├── ui/             # UI 定義檔案
│   ├── views/          # 視圖控制器
│   └── view_models/    # 視圖模型（MVVM 模式）
├── resources/
│   └── icons/          # 應用程式圖示
├── util/
│   └── logger.py       # 日誌工具
├── main.py             # 應用程式進入點
└── requirements.txt    # Python 相依套件
```

## 疑難排解

### 常見問題

1. **無法偵測裝置**
   - 確保裝置正確連接
   - 檢查是否安裝正確的驅動程式
   - 確認裝置已開機

2. **測試失敗**
   - 檢查實體連接
   - 確保裝置韌體為最新版本
   - 參考裝置說明文件了解特定測試需求

3. **使用者介面沒有回應**
   - 檢查系統資源（CPU/記憶體使用情況）
   - 重新啟動應用程式
   - 確認 Python 和 PySide6 安裝正確

## 開發

### 從原始碼建置

```bash
# 複製儲存庫
git clone https://192.168.26.172:8080/VT_Hydra_2504.git
cd VT_Hydra_2504

# 安裝開發相依套件
pip install -r requirements.txt

# 執行測試
pytest
```

### 建立可執行檔

```bash
# 使用 PyInstaller
pyinstaller main.spec
```

## 授權

版權所有 © 2025。保留所有權利。

---

*如需技術支援，請聯絡 frank_chen@promate.com* 