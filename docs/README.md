# MoodMend 应用使用指南

## 版本历史

### V1.0.3 - 品牌和UI更新

- 添加新的品牌Logo和图标资源，提升视觉识别度
- 更新登录页、注册页和欢迎页，添加居中显示的品牌Logo
- 统一HTML头部的图标引用，使用新的品牌Logo
- 调整界面主题颜色，优化品牌一致性
- 添加MoodMend_Logo_Option4.svg和icon-moodmend.svg资源文件

### V1.0.2 - 错误修复和稳定性提升

- 修复"ReferenceError: Cannot access 'currentUser' before initialization"登录错误
- 解决"后台同步注册失败: UnknownError: Background Sync is disabled"的兼容性问题
- 修复"未找到App容器元素!"的错误日志显示问题
- 增强Service Worker错误处理，提升离线功能的健壮性
- 改进前端变量作用域管理，确保应用在各种环境下稳定运行

### V1.0.1 - 功能修复和优化

- 修复数据库users表缺少user_name列的问题，解决注册功能500错误
- 修复get_logs函数中的数据库结果访问方式，确保正确返回日志数据
- 修复前端API调用中的email参数引用错误，避免参数传递问题
- 增强数据库兼容性，自动检测并添加缺失的表结构

## 项目结构

- `src/frontend/moodmend_ui_demo.html` - 前端界面文件
- `src/backend/moodmend_backend.py` - 后端API服务
- `icons/` - 应用图标和Logo资源
- `config/` - 配置文件目录
- `docs/` - 文档目录（包含本README）
- `requirements.txt` - 项目依赖
- `service-worker.js` - Service Worker实现
- `manifest.json` - Web应用清单

## 使用说明

### 1. 启动后端服务

后端服务已成功启动在 http://127.0.0.1:5000，它只提供API接口，不包含用户界面。

### 2. 访问前端界面

**不要在浏览器中直接访问 http://127.0.0.1:5000，因为这只是API服务！**

要访问互动界面，请按照以下步骤操作：

1. 确保已经启动了HTTP服务器（在项目根目录运行 `python -m http.server 8000`）
2. 在浏览器中访问 http://localhost:8000/src/frontend/moodmend_ui_demo.html

或者，你也可以直接打开文件：

1. 在文件资源管理器中找到 `src/frontend/moodmend_ui_demo.html` 文件
2. 双击该文件直接在浏览器中打开，或
3. 右键点击文件，选择「打开方式」→ 选择你的浏览器

### 3. 登录和使用

- 使用测试账号登录：
  - 邮箱: test@test.com
  - 密码: 123

## 功能说明

1. **情绪记录** - 输入你的情绪描述，获取个性化建议
2. **任务跟踪** - 完成每日任务并获得成就
3. **NFT徽章** - 根据情绪状态和进步获得徽章
4. **日志管理** - 查看历史记录和统计数据

## 注意事项

- 确保后端服务在使用过程中保持运行状态
- 前端页面会自动与后端API进行通信
- 数据会保存在本地的SQLite数据库文件中

如有问题，请检查浏览器控制台是否有错误信息。

## 日志显示功能实现指南

### SQL数据库连接流程

MoodMend使用SQLite作为数据库存储，通过Flask后端提供API接口供前端调用。以下是如何正确连接SQL到前端并显示"我的療癒紀錄"的详细说明：

#### 1. 后端数据库设计

数据库包含三个主要表：
- **users** - 存储用户账户信息
- **logs** - 存储情绪记录和任务完成情况
- **user_emotions** - 存储用户情绪历史

#### 2. 关键API接口

##### 2.1 获取日志API (`/api/get-logs`)

**功能**：查询用户的日志记录，支持分页和筛选

**参数**：
- `email` - 用户邮箱（必填）
- `page` - 页码（默认为1）
- `page_size` - 每页记录数（默认为10）
- `period` - 时间范围（all、week、month）
- `emotion` - 情绪类型过滤

**返回值**：
```json
{
  "success": true,
  "total": 29,
  "logs": [
    {
      "log_id": "uuid",
      "time": "2025-10-27T10:00:00",
      "emotion": "happy",
      "task": "計劃一個小慶祝活動。",
      "nft": "⭐ 星光徽章 - 喜悅守護",
      "completed": 1
    }
    // 更多日志...
  ]
}
```

##### 2.2 获取统计数据API (`/api/get-stats`)

**功能**：获取用户的情绪统计信息

**参数**：
- `email` - 用户邮箱（必填）
- `period` - 时间范围（all、week、month）

#### 3. 前端连接实现步骤

1. **初始化测试数据**
   - 运行 `python init_test_data.py` 添加测试数据
   - 这会创建测试用户和29条测试日志

2. **前端调用实现**

   ```javascript
   // 加载日志数据示例代码
   function loadLogs(page) {
       const email = currentUser.email;
       const period = document.getElementById('periodFilter').value;
       const emotion = document.getElementById('emotionFilter').value;
       
       // 构建查询URL
       let url = `http://localhost:5000/api/get-logs?email=${encodeURIComponent(email)}`;
       url += `&page=${page}&page_size=10`;
       if (period && period !== 'all') url += `&period=${period}`;
       if (emotion && emotion !== 'all') url += `&emotion=${emotion}`;
       
       // 发送请求并处理响应
       fetch(url)
       .then(response => response.json())
       .then(data => {
           if (data.success) {
               renderLogs(data.logs, data.total);
           }
       });
   }
   ```

3. **渲染日志列表**
   - 使用JavaScript动态创建日志卡片
   - 应用不同情绪的样式和图标
   - 实现分页控件

### 演示功能访问

日志显示功能已经集成到主应用中，你可以通过以下方式访问：

1. 确保后端服务正在运行（http://127.0.0.1:5000）
2. 启动HTTP服务器并访问 http://localhost:8000/src/frontend/moodmend_ui_demo.html
3. 使用测试账号登录
4. 在主界面中导航到日志记录部分

主应用包含完整的日志功能：
- 用户登录验证
- 日志列表展示
- 时间和情绪筛选
- 任务完成跟踪
- NFT徽章展示
