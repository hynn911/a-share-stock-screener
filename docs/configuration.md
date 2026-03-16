# 配置指南

## 快速开始

### 1. 复制环境变量模板

```bash
# Windows (PowerShell)
cp .env.example .env

# Linux/macOS
cp .env.example .env
```

### 2. 编辑 `.env` 文件

根据你的需求修改 `.env` 文件中的配置项。

## 配置项说明

### 数据库配置

```ini
DATABASE_URL=sqlite:///./data/stock.db
```

- **默认**: SQLite（开发环境）
- **生产环境**: 建议使用 PostgreSQL
  ```ini
  DATABASE_URL=postgresql://user:password@localhost:5432/stock_db
  ```

### Tushare Token（可选）

```ini
# TUSHARE_TOKEN=your_token_here
```

**为什么要配置 Tushare？**
- AkShare 依赖的免费数据源不稳定，经常连接超时
- Tushare 数据更稳定可靠
- 免费版有积分限制，但基础数据够用

**获取 Token 步骤：**
1. 访问 https://tushare.pro/
2. 注册账号
3. 登录后进入「个人中心」→「接口 Token」
4. 复制 Token 到 `.env` 文件

**注意：** 不要将 `.env` 文件提交到 Git！

### 离线模式

```ini
STOCK_APP_OFFLINE_MODE=0
```

- `0` - 在线模式（默认）
- `1` - 离线模式（优先使用本地缓存）

### 日志级别

```ini
LOG_LEVEL=INFO
```

可选值：`DEBUG`, `INFO`, `WARNING`, `ERROR`

## 安全提示

### 不要提交敏感信息

`.env` 文件已添加到 `.gitignore`，但请务必：
1. 不要手动将 `.env` 添加到 Git
2. 不要将 `.env` 上传到公开仓库
3. 不要将包含真实 token 的截图发布到公开场合

### 使用 `.env.example` 分享配置模板

`.env.example` 文件是安全的配置模板，不包含真实敏感信息：
- 可以安全提交到 Git
- 团队成员可以复制为 `.env` 使用

## 环境变量优先级

系统按以下顺序读取配置（后面的覆盖前面的）：

1. `.env.example`（模板，仅供参考）
2. `.env`（本地配置）
3. 系统环境变量

## 验证配置

```bash
# 测试数据源连接
python tests/test_data_sources.py

# 检查环境变量是否生效
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('TUSHARE_TOKEN:', os.getenv('TUSHARE_TOKEN', '未设置'))"
```

## 故障排查

### 问题：修改 `.env` 后配置未生效

**解决：**
1. 重启 Python/Streamlit 进程
2. 清理 Python 缓存：
   ```bash
   find . -type d -name '__pycache__' -exec rm -rf {} +
   find . -name '*.pyc' -delete
   ```
3. 确认 `.env` 文件格式正确（无多余空格、引号）

### 问题：Tushare token 无效

**检查：**
1. Token 是否正确复制（无多余空格）
2. Tushare 账号积分是否足够
3. 访问 https://tushare.pro/ 验证账号状态

## 示例配置

### 开发环境（SQLite + 缓存）

```ini
DATABASE_URL=sqlite:///./data/stock.db
TUSHARE_TOKEN=
STOCK_APP_OFFLINE_MODE=0
LOG_LEVEL=DEBUG
```

### 生产环境（PostgreSQL + Tushare）

```ini
DATABASE_URL=postgresql://user:password@localhost:5432/stock_db
TUSHARE_TOKEN=your_real_token_here
STOCK_APP_OFFLINE_MODE=0
LOG_LEVEL=INFO
```

### 离线/演示环境

```ini
DATABASE_URL=sqlite:///./data/stock.db
TUSHARE_TOKEN=
STOCK_APP_OFFLINE_MODE=1
LOG_LEVEL=INFO
```
