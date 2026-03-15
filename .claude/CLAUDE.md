# 项目约束 - A 股高价值股票发掘系统

## 缓存清理规程（重要！）

**每次修改代码后必须执行缓存清理，确保新代码生效！**

### 快速清理命令

**Windows (PowerShell 或 CMD)**:
```bash
# 使用一键脚本（推荐）
scripts\clean_and_restart.bat

# 或手动清理
cd stock
find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null
find . -name '*.pyc' -delete
streamlit run ui/app.py
```

**Linux / macOS**:
```bash
# 使用一键脚本（推荐）
bash scripts/clean_and_restart.sh

# 或手动清理
cd stock
find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null
find . -name '*.pyc' -delete
streamlit run ui/app.py
```

### 为什么需要清理缓存？

1. **Streamlit 模块缓存**：Streamlit 在启动时缓存所有导入的 Python 模块，修改代码后不会自动重新加载
2. **Python __pycache__**：Python 编译后的字节码文件可能包含旧版本代码
3. **浏览器缓存**：浏览器可能缓存旧的静态资源

### 验证代码生效方法

1. 在修改的文件中添加明显的日志输出：
   ```python
   print("=== 代码已更新：文件 xxx.py ===")
   ```

2. 重启 Streamlit 后检查控制台输出

3. 测试修改的功能是否按预期工作

4. 如果仍然报错：
   - 确认缓存是否彻底清理
   - 检查是否有多个 Python 环境
   - 确认 Streamlit 是否完全重启（不只是页面刷新）

### 常见错误及解决方案

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `AttributeError: 'X' object has no attribute 'Y'` | 模块缓存了旧版本 | 清理缓存并重启 Streamlit |
| `ModuleNotFoundError: No module named 'X'` | Python 路径问题 | 检查 sys.path 配置，清理缓存 |
| 修改后页面无变化 | 浏览器缓存或 Streamlit 缓存 | 强制刷新浏览器 (Ctrl+Shift+R) + 清理缓存 |

## 开发工作流

1. **修改代码** → 2. **清理缓存** → 3. **重启 Streamlit** → 4. **验证功能**

建议使用 `scripts/clean_and_restart.sh` 或 `scripts/clean_and_restart.bat` 一键完成清理和重启。

## 项目结构

```
stock/
├── core/           # 核心业务逻辑模块
│   ├── database.py    # 数据库连接和 Session 管理
│   ├── models.py      # SQLAlchemy 数据模型
│   ├── data_fetcher.py # 数据抓取
│   ├── indicator.py    # 技术指标计算
│   ├── capital.py      # 资金流分析
│   ├── hot_words.py    # 热词和板块分析
│   ├── position.py     # 持仓管理
│   ├── shareholder.py  # 股东户数分析
│   ├── stock_scorer.py # 股票综合评分
│   └── commodity.py    # 大宗商品监控
├── ui/             # Streamlit 前端界面
│   └── app.py         # 主界面入口
├── tasks/          # 定时任务和批处理脚本
├── tests/          # 测试用例
├── docs/           # 文档
├── scripts/        # 工具脚本
│   ├── clean_and_restart.sh   # Linux/Mac 清理重启脚本
│   └── clean_and_restart.bat  # Windows 清理重启脚本
└── data/           # 本地数据存储
```

## 技术栈

- **后端**: Python 3.10+, SQLAlchemy, AkShare
- **前端**: Streamlit
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **数据分析**: Pandas, NumPy
