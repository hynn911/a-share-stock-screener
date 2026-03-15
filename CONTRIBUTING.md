# 贡献指南

感谢您对本项目的关注！本文档提供了一些指导方针，帮助您为项目做出贡献。

## 🤝 如何贡献

### 1. 报告问题

如果您发现了 bug 或有功能建议，请创建 Issue 并包含：

- 清晰的问题描述
- 复现步骤
- 预期行为与实际行为
- 环境信息（Python 版本、操作系统等）
- 相关日志或截图

### 2. 提交代码

#### 准备工作

```bash
# Fork 项目
git fork <repository-url>

# 克隆到本地
git clone <your-fork-url>
cd stock

# 创建分支
git checkout -b feature/your-feature-name
```

#### 开发规范

1. **代码风格**：遵循 PEP 8 规范
2. **类型注解**：使用 Python type hints
3. **文档字符串**：为函数和类添加 docstring
4. **测试**：为新功能添加测试用例

#### 提交代码

```bash
# 提交更改
git add .
git commit -m "feat: 添加新功能描述"

# 推送分支
git push origin feature/your-feature-name
```

#### 创建 Pull Request

在 GitHub 上创建 Pull Request，并包含：

- 清晰的标题
- 详细的描述（说明变更内容、原因、测试方法）
- 关联的 Issue 编号

### 3. Commit 信息格式

遵循 Conventional Commits 规范：

```
<type>: <description>

[optional body]
```

**Type 类型**：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具链相关

## 📋 开发环境设置

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# 安装开发依赖
pip install -r requirements.txt
pip install pytest pytest-cov black flake8 mypy

# 运行测试
pytest tests/ --cov=core

# 代码格式化
black core/ ui/ tasks/
flake8 core/ ui/ tasks/
```

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_specific.py

# 生成覆盖率报告
pytest --cov=core --cov-report=html
```

## 📝 文档

如需更新文档，请编辑：

- `README.md` - 项目主文档
- `docs/` - 详细文档目录

## 💬 讨论

欢迎在 Discussions 中参与讨论：

- 功能想法
- 技术问题
- 使用分享

## ⚖️ 行为准则

请保持友好、专业的交流氛围，尊重每一位贡献者。

## 📧 联系方式

如有疑问，请通过 Issue 或 Pull Request 联系。

---

感谢您的贡献！🎉
