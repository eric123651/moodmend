## MoodMend 后端服务

### 功能介绍
- 用户认证系统（注册、登录）
- 情绪分析与记录
- 个性化建议生成
- NFT徽章生成
- 统计数据分析
- 阿里云服务集成

### 技术栈
- Python Flask
- SQLite数据库
- 阿里云智能语音交互服务 (语音识别)
- 阿里云自然语言处理服务 (情感分析)
- 阿里云通义千问 (建议生成)

### 安装与运行
1. 安装依赖：`pip install -r requirements.txt`
2. 配置阿里云凭证（在aliyun_config.py中设置或通过环境变量）
3. 运行服务：`python moodmend_backend.py`

### 环境变量配置

项目现在使用`.env`文件管理敏感配置信息，避免硬编码凭证。配置步骤：

1. 打开 `/Users/zhengbowei/MoodMend/moodmend/src/backend/.env` 文件
2. 替换示例值为您的实际凭证：
   - `ALIYUN_ACCESS_KEY_ID`: 您的阿里云访问密钥ID
   - `ALIYUN_ACCESS_KEY_SECRET`: 您的阿里云访问密钥Secret
   - `DASHSCOPE_API_KEY`: 您的通义千问API Key
   - `NLS_APP_KEY`: 您的智能语音交互服务AppKey

**重要安全提示**：
- 请确保将`.env`文件添加到`.gitignore`中，避免将敏感凭证提交到版本控制系统
- 不要在代码中硬编码任何API密钥或访问凭证

### 最近更新
- 将Google Cloud服务替换为阿里云服务
- 实现了阿里云NLP情感分析
- 实现了通义千问AI建议生成
- 实现了阿里云语音识别服务