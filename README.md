# ⚾ Dream Order TCG 卡片查詢與翻譯系統

Dream Order 是一款以日本職棒 NPB 為主題的交換卡片遊戲（TCG）。本專案提供卡片資訊查詢與即時日文翻譯功能，協助玩家快速了解卡片能力。

## 🎯 主要功能

- **📊 完整卡片資料庫**：收錄 4000+ 張官方卡片資訊
- **🔍 智能搜尋**：支援卡片編號、球員名字、球隊等多重條件查詢
- **🌐 即時翻譯**：日文能力描述自動翻譯成繁體中文
- **📋 結構化資料**：自動解析 AP/DP 加成、守備位置、稀有度等屬性
- **⚡ 本地快取**：快速載入，無需每次重新抓取
- **🎨 雙語對照**：提供日文原文與中文翻譯切換檢視

## 📦 安裝需求

### 系統需求
- Python 3.8 或更高版本
- 網路連線（用於 Google Translate API）

### 安裝套件

```bash
pip install streamlit requests beautifulsoup4 googletrans==3.1.0a0
```

## 🚀 使用方式

### 1. 啟動應用程式

```bash
streamlit run main.py
```

應用程式將在瀏覽器中自動開啟，預設網址為 `http://localhost:8501`

### 2. 搜尋卡片

在搜尋框輸入以下任一條件：
- **卡片編號**：例如 `BP01-G01`、`PBP02-B03`
- **球員名字**：支援日文或中文（例如：`山崎`、`大谷`）
- **球隊名稱**：支援日文或中文（例如：`巨人`、`讀賣`）
- **關鍵字**：能力描述中的關鍵字

### 3. 查看卡片資訊

搜尋結果將顯示：
- 官方卡面圖片
- 球隊、守備位置、稀有度
- AP/DP 基本加成值
- 特殊能力說明（日文原文 / 中文翻譯）
- 能力標記說明

### 4. 更新卡片資料庫

點擊「重新抓取並更新本地快取」按鈕，系統將從官網重新抓取最新卡片資料。

**注意**：完整更新約需 2-3 分鐘，請耐心等待。

## 🔧 進階功能

### 離線重建快取

如需完整重建本地快取，可執行：

```bash
python fetch_all_cards.py
```

此腳本會從官網抓取所有卡片並儲存至 `local_cache/card_data.json`。

### 自訂設定

在 `main.py` 頂部可調整版本號：

```python
VERSION_MAJOR = 1  # 主版本號（重大功能更新）
VERSION_MINOR = 0  # 次版本號（小功能更新或修正）
```

## 📂 專案結構

```
DreamOrder_Search/
├── main.py                 # 主應用程式
├── fetch_all_cards.py      # 離線資料抓取腳本
├── local_cache/            # 本地快取目錄
│   └── card_data.json      # 卡片資料快取檔案
└── README.md               # 專案說明文件
```

## 📝 版本資訊

### Version 1.0 (2026-06-28)

**Initial Release** 🎉

#### ✨ 新功能
- 卡片資訊查詢與搜尋系統
- 日文→繁體中文即時翻譯
- 本地快取機制（17ms 快速載入）
- 完整結構化資料解析（AP/DP/位置/稀有度）
- 雙語對照顯示（日文原文 / 中文翻譯）
- 支援 4000+ 張官方卡片

#### 🔧 技術特性
- Streamlit Web UI 框架
- BeautifulSoup4 網頁解析
- Google Translate API 整合
- 智能去重（相同編號平行卡）
- 延遲翻譯優化（避免 API rate limit）

#### 🐛 已知限制
- Google Translate 免費版有請求頻率限制
- 部分特殊符號可能翻譯不精確
- 需網路連線才能使用翻譯功能

## 🤝 貢獻指南

歡迎提交 Issue 或 Pull Request！

### 回報問題
- 請詳細描述問題發生的情境
- 附上錯誤訊息或截圖
- 說明使用的作業系統和 Python 版本

### 建議新功能
- 描述功能需求與使用場景
- 說明預期效果

## 📄 授權聲明

本專案僅供學習與個人使用。卡片圖片及資料版權屬於 Dream Order 官方。

## 🔗 相關連結

- [Dream Order 官方網站](https://dreamorder.com/)
- [Dream Order 卡表](https://dreamorder.com/cardlist/)

## 💡 常見問題

### Q: 為什麼翻譯速度較慢？
A: 系統使用 Google Translate API，每句翻譯都需要網路請求。為避免 API 限制，設有延遲機制。

### Q: 如何更新到最新卡片？
A: 點擊應用程式中的「重新抓取並更新本地快取」按鈕，或執行 `python fetch_all_cards.py`。

### Q: 快取檔案在哪裡？
A: 儲存在 `local_cache/card_data.json`，可直接編輯或刪除重建。

### Q: 支援哪些卡池？
A: 支援所有官方卡池，包括 BP、CBP、PB、PBP、CSD、PSD 等系列。

---

**Made with ⚾ for Dream Order TCG players**
