# ETF Tracker Dashboard

## 簡介

ETF Tracker Dashboard 是一個基於 **Streamlit** 開發的視覺化應用，旨在讓使用者能夠方便地查詢、比較及管理台股 ETF 的歷史數據。此應用程式支援 **ETF 交易數據的查詢、更新、視覺化顯示**，並可透過 **表格與圖表** 呈現不同 ETF 的歷史表現。

---

## 功能特色

### 1. ETF 資料管理

✅ **初始化 (Init)**：抓取所有 ETF 的歷史數據並儲存。 ✅ **每日更新 (Update)**：自動取得當日 ETF 最新數據。 ✅ **排程更新 (Schedule)**：定期執行 ETF 數據更新 (適合長期運行)。

### 2. ETF 資料查詢與比較

✅ **查看各 ETF 最後資料更新時間** (表格格式顯示)。 ✅ **選擇單個或多個 ETF 進行歷史數據比較**。 ✅ **支援時間範圍篩選 (2 週、1 個月、3 個月、1 年、3 年)**。 ✅ **顯示歷史數據表格，支援排序與篩選**。 ✅ **圖表視覺化 ETF 走勢 (基於 Plotly)**。

---

## 環境安裝與執行

### 1. 安裝必要套件

請確保 Python 環境已安裝，然後安裝必要的 Python 套件：

```bash
pip install -r requirements.txt
```

### 2. 啟動應用程式

執行以下指令來啟動 **Streamlit Web 應用程式**：

```bash
streamlit run app.py
```

預設將在瀏覽器中開啟 `http://localhost:8501`，您可透過該頁面進行 ETF 追蹤與查詢。

### 3. 自訂 Port

若需自訂啟動埠，可使用：

```bash
streamlit run app.py --server.port=8888
```

---

## 主要 UI 功能與操作

### 📌 ETF 操作功能區

- **初始化資料 (Init)**：點擊後抓取所有 ETF 的歷史數據。
- **更新當日資料 (Update)**：抓取並更新最新 ETF 交易數據。
- **啟動排程 (Schedule)**：定期執行每日 ETF 更新。

### 📌 ETF 資料查詢

- **查看各 ETF 最後更新日期**：點擊按鈕後以表格顯示所有 ETF 的最後更新時間。
- **選擇 ETF 進行比較**：
  - 透過 **多選清單** 選擇要比較的 ETF。
  - 透過 **時間區間選擇** 過濾不同時期的表現。
  - 透過 **表格與圖表** 呈現 ETF 走勢與交易數據。

---

## 專案結構

```
ETF_Tracker/
├── config/                 # 設定檔與 ETF 清單
│   ├── config_loader.py
│   ├── settings.yaml
│   └── etf_list.yaml
├── modules/                # 主要模組 (抓取、儲存、處理、視覺化)
│   ├── data_fetcher.py
│   ├── storage.py
│   ├── data_processor.py
│   ├── reporter.py
│   ├── plotter.py
├── app.py                  # Streamlit 主程式 (UI 入口)
├── main.py                 # ETF 數據處理與排程
├── requirements.txt        # 依賴套件列表
├── README.md               # 本文件
```

---

## 進階調整

### 1. 修改 `settings.yaml` 設定檔

若要調整 ETF 來源、數據存放目錄、日誌設定等，可修改 `config/settings.yaml`。

### 2. 調整 ETF 清單

如需新增或移除 ETF，可修改 `config/etf_list.yaml`。

### 3. 部署建議

可透過 **Docker、雲端伺服器 (AWS/GCP)、或本地執行**，確保每日 ETF 交易數據自動更新。

---

## 版權與貢獻

📌 本專案為開源 ETF 追蹤應用，歡迎開發者貢獻改進與功能擴充！

📌 若有任何問題或建議，請透過 **GitHub Issue** 或 **Pull Request** 提出。

🚀 **Enjoy ETF Tracker!** 🚀

