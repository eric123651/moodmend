# MoodMend - AI情绪调节平台

## 项目介绍
MoodMend是一个基于AI技术的情绪调节平台，帮助用户通过语音输入分析情绪状态并提供相应的建议。平台集成了语音识别、自然语言处理和情绪分析功能，为用户提供全方位的情绪管理体验。

## 核心功能
- **语音情绪分析**：通过语音输入识别用户情绪状态
- **情绪日志记录**：自动记录用户的情绪变化历程
- **数据可视化**：通过图表直观展示情绪变化趋势
- **用户认证**：安全的登录注册系统

## 技术栈
- **前端**：HTML, CSS, JavaScript
- **后端**：Python Flask
- **数据库**：SQLite
- **AI服务**：阿里云NLP, 语音识别, 通义千问

## 快速开始

### 环境要求
- Python 3.7+
- 依赖库见 requirements.txt

### 安装步骤
1. 克隆项目
   ```
   git clone https://github.com/username/moodmend.git
   cd moodmend
   ```

2. 安装依赖
   ```
   pip install -r requirements.txt
   ```

3. 配置阿里云服务
   在 `backend/aliyun_config.py` 中配置你的阿里云API密钥

4. 启动服务
   ```
   python backend/app.py
   ```

5. 访问应用
   打开浏览器访问 http://localhost:3000

## 测试账号
- 用户名: test
- 密码: password123

## 项目结构
```
moodmend/
├── backend/         # 后端代码
├── frontend/        # 前端代码
├── docs/            # 文档
├── tests/           # 测试代码
└── deploy/          # 部署配置
```

## API文档
详细API文档请查看 `docs/API_Docs.md`

## 贡献指南
欢迎提交Issue和Pull Request来帮助改进项目。

## 许可证
MIT License