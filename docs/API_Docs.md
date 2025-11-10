# MoodMend API 文档

## 接口概览

### 认证接口

#### POST /api/login
**描述**: 用户登录接口
**请求体**:
```json
{
  "username": "string",
  "password": "string"
}
```
**响应**:
- 成功: `{"token": "jwt_token", "user": {"id": 1, "username": "string"}}`
- 失败: `{"message": "登录失败原因"}`

### 语音识别接口

#### POST /api/speech-to-text
**描述**: 语音转文字接口
**请求体**:
```json
{
  "audio": "Blob对象或base64编码的音频数据"
}
```
**响应**:
```json
{
  "text": "识别出的文本内容"
}
```

### 情绪处理接口

#### POST /api/process-emotion
**描述**: 处理情绪分析
**请求头**:
- Authorization: Bearer {token}
**请求体**:
```json
{
  "text": "需要分析的文本内容"
}
```
**响应**:
```json
{
  "emotion": "happy|sad|angry|calm|neutral",
  "confidence": 0.85,
  "timestamp": "2023-07-15T14:30:00Z"
}
```

### 日志记录接口

#### GET /api/get-logs
**描述**: 获取用户情绪日志
**请求头**:
- Authorization: Bearer {token}
**查询参数**:
- limit: 限制返回记录数
- offset: 分页偏移
- start_date: 开始日期
- end_date: 结束日期
**响应**:
```json
{
  "logs": [
    {
      "id": 1,
      "emotion": "happy",
      "confidence": 0.85,
      "text": "今天很开心",
      "timestamp": "2023-07-15T14:30:00Z"
    },
    // 更多日志记录...
  ],
  "total": 100
}
```

## API 错误码

- 400: 请求参数错误
- 401: 未授权访问
- 403: 禁止访问
- 404: 资源不存在
- 500: 服务器内部错误

## API 使用示例

### 使用 Fetch API 调用登录接口
```javascript
fetch('/api/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ username: 'test', password: 'password123' })
})
.then(response => response.json())
.then(data => {
  if (data.token) {
    localStorage.setItem('token', data.token);
  }
});
```

### 使用 Bearer Token 调用受保护接口
```javascript
fetch('/api/get-logs', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  }
})
.then(response => response.json())
.then(data => {
  console.log(data.logs);
});
````