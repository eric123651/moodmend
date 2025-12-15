# MoodMend - 心情療癒追蹤應用

[![Version](https://img.shields.io/badge/version-1.2.1-blue.svg)](https://github.com/yourusername/moodmend)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-yellow.svg)](https://www.python.org/)

MoodMend 是一個現代化的心情追蹤與心理健康管理應用，幫助用戶記錄情緒、獲得個性化建議，並通過數據可視化了解自己的情緒模式。

## ✨ 主要功能

### 🎯 核心功能
- **情緒分析** - 智能檢測情緒類型（快樂、悲傷、憤怒、焦慮、平靜）
- **語音輸入** - 使用麥克風按鈕進行語音轉文字輸入
- **個性化建議** - 根據情緒提供呼吸練習、任務建議和資源鏈接
- **NFT徽章系統** - 完成任務獲得成就徽章，包括情緒轉變特殊徽章
- **心情日誌** - 完整的情緒記錄歷史，支持時間篩選
- **數據可視化** - 圓餅圖和折線圖展示情緒趨勢

### 📊 數據分析
- **時間區間選擇** - 1週、1月、3月、6月、1年、全部
- **圖表類型切換** - 圓餅圖 ↔ 折線圖
- **智能統計** - 任務完成率、情緒轉移成就
- **趨勢分析** - 情緒變化趨勢顏色標示

### 🎨 用戶體驗
- **現代化設計** - 漸變背景、玻璃擬態效果、流暢動畫
- **響應式佈局** - 適配各種屏幕尺寸
- **直觀導航** - 三頁式結構（首頁、日誌、情緒輸入）
- **即時反饋** - 成功提示、自動滾動、加載狀態

## 🚀 快速開始

### 前置要求
- Python 3.8 或更高版本
- pip (Python 包管理器)
- 現代瀏覽器（Chrome、Firefox、Safari）

### 安裝步驟

1. **克隆倉庫**
   ```bash
   git clone https://github.com/yourusername/moodmend.git
   cd moodmend
   ```

2. **安裝依賴**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置環境**
   ```bash
   cp .env.example .env
   # 編輯 .env 文件設置您的配置
   ```

4. **初始化數據庫**
   ```bash
   python init_test_data.py
   ```

5. **啟動後端服務**
   ```bash
   cd src/backend
   python moodmend_backend.py
   ```
   
   後端服務將在 `http://127.0.0.1:3000` 啟動

6. **打開前端界面**
   
   在瀏覽器中打開 `src/frontend/moodmend_ui_demo.html`

### 使用 Docker 部署

```bash
# 使用 Docker Compose 快速啟動
docker-compose up -d

# 或手動構建
docker build -t moodmend:latest .
docker run -d -p 3000:3000 -v $(pwd)/data:/app/data moodmend:latest
```

## 📖 使用指南

### 登錄
- **測試賬號**: `test@test.com`
- **密碼**: `123`

### 功能導航
1. **首頁（Page 1）** - 查看今日任務和NFT徽章
2. **心情日誌（Page 2）** - 瀏覽歷史記錄和統計圖表
3. **情緒分析（Page 3）** - 輸入情緒描述獲取建議

### 情緒分析流程
1. 在 Page 3 輸入您的情緒描述（支持語音輸入）
2. 點擊「開始調節」按鈕
3. 查看分析結果和個性化建議
4. 完成任務後點擊「生成徽章」保存記錄

## 🛠️ 項目結構

```
moodmend/
├── src/
│   ├── backend/
│   │   └── moodmend_backend.py    # Flask API 服務
│   └── frontend/
│       └── moodmend_ui_demo.html  # 前端界面
├── scripts/
│   ├── backup_database.py         # 數據庫備份腳本
│   └── restore_database.py        # 數據庫恢復腳本
├── docs/
│   ├── DEPLOYMENT.md              # 部署指南
│   ├── PRODUCTION_CHECKLIST.md   # 生產環境檢查清單
│   ├── PRIVACY_POLICY.md          # 隱私政策
│   └── TERMS_OF_SERVICE.md        # 服務條款
├── backups/                       # 數據庫備份目錄
├── .env.example                   # 環境變量模板
├── docker-compose.yml             # Docker Compose 配置
├── Dockerfile                     # Docker 鏡像配置
├── requirements.txt               # Python 依賴
└── init_test_data.py             # 測試數據初始化
```

## 🔧 配置說明

### 環境變量

在 `.env` 文件中配置以下變量：

```env
# 服務器配置
PORT=3000
HOST=0.0.0.0
DEBUG=False

# 數據庫配置
DATABASE_PATH=moodmend.db

# 安全配置
SECRET_KEY=your-secret-key-here

# 日誌配置
LOG_LEVEL=INFO
LOG_FILE=moodmend.log
```

## 📊 API 端點

### 用戶管理
- `POST /api/register` - 用戶註冊
- `POST /api/login` - 用戶登錄

### 情緒處理
- `POST /api/process-emotion` - 分析情緒並獲取建議
- `POST /api/add-log` - 保存情緒日誌
- `GET /api/get-logs` - 獲取日誌列表
- `GET /api/get-stats` - 獲取統計數據

### 監控
- `GET /health` - 健康檢查端點

## 🔒 安全性

- ✅ 密碼使用 bcrypt 加密存儲
- ✅ CORS 配置支持跨域請求
- ✅ 環境變量管理敏感信息
- ✅ SQL 注入防護
- ✅ 輸入驗證和清理

## 📦 數據管理

### 備份數據庫
```bash
python scripts/backup_database.py
```

### 恢復數據庫
```bash
python scripts/restore_database.py
```

### 自動備份
設置 cron 任務每天自動備份：
```bash
0 2 * * * cd /path/to/moodmend && python scripts/backup_database.py
```

## 🚀 部署

詳細部署指南請參閱 [DEPLOYMENT.md](docs/DEPLOYMENT.md)

### 生產環境部署選項
- Heroku
- DigitalOcean
- AWS EC2
- Docker Container

### 生產環境檢查清單
部署前請查看 [PRODUCTION_CHECKLIST.md](docs/PRODUCTION_CHECKLIST.md)

## 📈 版本歷史

### V1.2.1 - 語音輸入與UI優化 (當前版本)
- ✅ 語音輸入功能（Web Speech API）
- ✅ Page 3 UI 全面優化
- ✅ 現代化輸入框設計
- ✅ 背景浮動動畫
- ✅ 自動滾動和智能提示

### V1.2 - 增強心情日誌與圖表功能
- ✅ 圓餅圖與折線圖切換
- ✅ 時間區間選擇器
- ✅ 智能日期格式化
- ✅ 趨勢顏色標示

### V1.0.1 - 功能修復和優化
- ✅ 數據庫架構修復
- ✅ API 調用優化
- ✅ 兼容性增強

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 許可證

本項目採用 MIT 許可證 - 詳見 [LICENSE](LICENSE) 文件

## ⚠️ 免責聲明

**重要提示**: MoodMend 是一個心理健康工具，**不是**醫療設備或專業心理治療的替代品。

- 不用於診斷、治療或治愈任何疾病
- 不適合緊急心理健康情況
- 如有心理健康問題，請諮詢專業醫療人員

### 緊急情況
如果您正在經歷心理健康危機：
- 撥打緊急服務電話
- 聯繫危機熱線
- 立即尋求專業幫助

## 📞 支持

- **問題反饋**: [GitHub Issues](https://github.com/yourusername/moodmend/issues)
- **電子郵件**: support@moodmend.com
- **文檔**: [docs/](docs/)

## 🌟 致謝

感謝所有為 MoodMend 做出貢獻的開發者和用戶！

---

**MoodMend** - 用心記錄，用愛療癒 💙
