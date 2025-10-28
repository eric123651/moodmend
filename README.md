# MoodMend 应用使用指南

## 项目结构

- `moodmend_ui_demo.html` - 前端界面文件
- `moodmend_backend.py` - 后端API服务
- `moodmend_demo.html` - 日志显示演示页面
- `moodmend.db` - SQLite数据库文件
- `init_test_data.py` - 测试数据初始化脚本
- `requirements.txt` - 项目依赖

## 使用说明

### 1. 启动后端服务

后端服务已成功启动在 http://127.0.0.1:5000，它只提供API接口，不包含用户界面。

### 2. 访问前端界面

**不要在浏览器中直接访问 http://127.0.0.1:5000，因为这只是API服务！**

要访问互动界面，请按照以下步骤操作：

1. 在文件资源管理器中找到 `moodmend_ui_demo.html` 文件
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

### 演示页面使用

我们提供了一个专门的演示页面 `moodmend_demo.html`，展示如何正确实现"我的療癒紀錄"功能：

1. 确保后端服务正在运行
2. 打开 `moodmend_demo.html` 文件
3. 使用测试账号登录
4. 查看日志列表和统计数据

这个演示页面包含完整的功能：
- 用户登录验证
- 日志列表展示
- 时间和情绪筛选
- 分页功能
- 统计数据可视化
