# 行业/板块数据解决方案

## 问题现状

截至 2026-03-15，AkShare API 连接失败，无法获取行业/概念板块数据：
- 错误信息：`RemoteDisconnected: Remote end closed connection without response`
- 数据库状态：5820 只股票，0 只有行业数据（0.0%）
- 智能荐股页面无法显示行业和所属板块信息

## 原因分析

AkShare 是免费的开源 Python 库，数据来源于东方财富网。由于以下原因可能导致临时不可用：
1. 东方财富服务器临时限流
2. 网络波动
3. API 接口维护

**AkShare 完全免费，不需要注册或购买**

## 已实施的解决方案

### 1. UI 侧边栏刷新按钮

在"智能荐股"页面的侧边栏添加了：
- 数据状态显示（总数、行业覆盖率、概念覆盖率）
- "🔄 刷新行业/板块数据"按钮
- 详细的错误帮助信息

### 2. 自动重试机制

代码中实现了 3 次自动重试：
```python
for attempt in range(3):
    try:
        df = ak.stock_zh_a_spot_em()
        break
    except Exception:
        if attempt < 2:
            time.sleep(2 * (attempt + 1))
```

### 3. 数据库Fallback

当 API 失败时，自动从数据库获取行业数据：
- 如果数据库有数据：正常显示
- 如果数据库为空：显示警告提示用户刷新

## 手动更新方法

### 方法 1：使用 UI 按钮（推荐）

1. 打开 Streamlit 应用
2. 进入"智能荐股"页面
3. 在左侧边栏点击"🔄 刷新行业/板块数据"
4. 等待更新完成

### 方法 2：命令行脚本

```bash
# Windows PowerShell 或 CMD
cd stock
python tasks/update_stock_list.py
```

### 方法 3：诊断工具

```bash
cd stock
python tasks/diagnose_industry.py
```

诊断工具会：
1. 显示当前数据库状态
2. 测试多个 AkShare 数据源
3. 自动保存获取到的数据
4. 显示更新后的统计

## 验证数据更新

更新成功后，在"智能荐股"页面：
1. 查看侧边栏数据状态
2. 确认"有行业数据"和"有概念数据"的覆盖率接近 100%
3. 运行"开始智能选股"
4. 检查表格中的"行业"和"所属板块"列是否有数据

## 预期结果

成功更新后：
- 数据库：5820 只股票中 95%+ 有行业数据
- 智能荐股页面：显示每只股票的所属行业和概念板块
- 实时更新：API 恢复时自动获取最新数据

## 长期建议

1. **定时任务**：建议每天运行一次更新脚本
   ```bash
   # 添加到 Windows 任务计划程序
   python tasks/update_stock_list.py
   ```

2. **监控 API 状态**：在应用启动时检查行业数据覆盖率

3. **备用数据源**：考虑添加 Tushare 作为备用（需要注册获取 token）

## 相关文件

- 更新脚本：`tasks/update_stock_list.py`
- 诊断工具：`tasks/diagnose_industry.py`
- UI 代码：`ui/app.py` (第 1040-1083 行：侧边栏刷新功能)
- 数据获取：`core/data_fetcher.py` (`fetch_stock_list` 方法)
