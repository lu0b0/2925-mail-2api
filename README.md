# 2925Api 无限邮件Api服务

FastAPI 服务，用于获取 2925.com 临时邮箱的邮件内容。

## 功能

- 根据邮箱地址、时间范围、邮件主题获取邮件内容
- 自动管理 token 认证和过期刷新
- 返回纯文本内容（自动清理 HTML 标签）

## 快速开始

### 1. 准备 Cookie

从浏览器获取 2925.com 的 Cookie，保存到 `cookie.txt` 文件：

```bash
echo "your_cookie_string" > cookie.txt
```

### 2. Docker 部署

#### 构建镜像

```bash
docker build -t 2925-mail-service .
```

#### 运行容器

```bash
docker run -d \
  --name 2925-mail \
  -p 8000:8000 \
  -v $(pwd)/cookie.txt:/app/cookie.txt \
  2925-mail-service
```

**Windows PowerShell:**
```powershell
docker run -d `
  --name 2925-mail `
  -p 8000:8000 `
  -v ${PWD}/cookie.txt:/app/cookie.txt `
  2925-mail-service
```

#### 查看日志

```bash
docker logs -f 2925-mail
```

#### 停止/删除容器

```bash
docker stop 2925-mail
docker rm 2925-mail
```

### 3. 本地运行（无 Docker）

```bash
pip install -r requirements.txt
python server.py
```

## API 接口

### POST /mails

获取符合条件的邮件内容。

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `email` | string | 是 | - | 接收邮件的邮箱地址 |
| `time` | int | 否 | 30 | 搜索最近 N 秒内的邮件 |
| `subject` | string | 是 | - | 邮件主题（精确匹配） |

**响应：**

```json
{
  "code": 200,
  "email": "邮件正文内容"
}
```

- `code`: 200 表示成功，0 表示未找到匹配邮件
- `email`: 邮件正文（已清理 HTML 标签）

### 示例

```bash
curl -X POST http://localhost:8000/mails \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "time": 60,
    "subject": "邮件标题"
  }'
```

**响应示例：**

```json
{
  "code": 200,
  "email": "您的验证码是：123456"
}
```

## 文件说明

```
.
├── Dockerfile           # Docker 镜像定义
├── requirements.txt     # Python 依赖
├── server.py           # FastAPI 服务代码
├── cookie.txt          # Cookie 文件（需自行创建）
└── README.md           # 本文档
```

## 注意事项

1. **Cookie 安全**：
   - `cookie.txt` 包含敏感信息，不要提交到 Git
   - Cookie 过期后需要重新获取并重启容器

2. **Token 管理**：
   - Token 过期会自动使用 Cookie 刷新
   - Cookie 过期时接口返回 401 错误
   - 容器启动时会立即验证 Cookie 有效性

3. **并发安全**：
   - 单个容器实例线程安全
   - 多容器部署需要独立的 Cookie 文件

## 故障排查

### 401 错误：cookie 过期

```bash
# 重新获取 Cookie 并替换 cookie.txt
echo "new_cookie_string" > cookie.txt

# 重启容器
docker restart 2925-mail
```

### 查看容器内部 Token

```bash
docker exec 2925-mail python -c "from server import mail_session; print(mail_session.token)"
```

### 未找到邮件（code: 0）

检查：
- 邮箱地址是否正确
- 时间范围是否足够（默认 30 秒）
- 邮件主题是否完全匹配

## 许可

本项目仅供学习和个人使用。
