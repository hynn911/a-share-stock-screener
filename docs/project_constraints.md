# 项目约束规范

## 核心约束

### 1. 股票信息展示规范（CRITICAL）

**所有展示股票的地方必须同时显示股票代码和股票名称**

格式：`{stock_code} - {stock_name}`

示例：
- ✅ 正确：`600519 - 贵州茅台`
- ❌ 错误：`600519`

#### 适用场景

1. **DataFrames 显示**
```python
# 必须添加股票名称列
df['股票'] = df['stock_code'] + " - " + df['stock_name']
```

2. **标题/标签**
```python
# 必须包含股票名称
st.markdown(f"#### {pos.stock_code} - {pos.stock_name}")
```

3. **指标卡片**
```python
# 标题中必须包含股票名称
st.subheader(f"{result['stock_code']} - {result['stock_name']}")
```

4. **下拉选项**
```python
# 选项必须包含股票名称
options = [f"{s.code} - {s.name}" for s in stocks]
```

#### 数据库查询规范

确保查询时获取股票名称：

```python
# 如果主表没有 name 字段，需要 JOIN stocks 表
from core.models import Stock

# 示例：获取股票名称
def get_stock_name(stock_code: str) -> str:
    stock = db.query(Stock).filter(Stock.code == stock_code).first()
    return stock.name if stock else ""

# 或在查询结果中添加名称
results.append({
    'stock_code': code,
    'stock_name': get_stock_name(code),  # 必须包含
    ...
})
```

---

### 2. 错误处理规范

所有外部 API 调用必须有错误处理：

```python
try:
    result = api_call()
    process(result)
except Exception as e:
    logger.error(f"API 调用失败：{e}")
    return fallback_value
```

---

### 3. 数据库操作规范

1. **必须关闭数据库连接**
```python
db = SessionLocal()
try:
    # 操作数据
finally:
    db.close()
```

2. **批量操作使用 commit**
```python
db.add_all(objects)
db.commit()  # 必须提交事务
```

---

### 4. API 请求规范

1. **添加延时避免限流**
```python
time.sleep(0.1)  # 至少 100ms 延时
```

2. **使用中文列名时用 iloc**
```python
# AkShare 数据使用列索引访问
value = row.iloc[2]  # 避免编码问题
```

---

### 5. UI 交互规范

1. **按钮操作后必须有反馈**
```python
st.success("操作成功")
st.warning("警告信息")
st.error("错误信息")
```

2. **数据为空时显示提示**
```python
if not data:
    st.warning("暂无数据")
```

---

### 6. 中文编码规范（CRITICAL）

**以 Web 显示为准，控制台编码问题可忽略**

1. **文件编码**
   - 所有 Python 文件必须使用 UTF-8 编码
   - 中文字符串直接使用中文，不使用转义字符

2. **控制台显示问题**
   - Windows 控制台可能无法正确显示 UTF-8 中文
   - 测试时以 Streamlit Web 界面显示为准
   - 不要在控制台编码问题上浪费时间调试

3. **Web 显示规范**
   - 确保 HTML/Streamlit 输出使用 UTF-8
   - 商品名称显示格式：`代码（中文名）` 或直接用中文名
   - 示例：`C (玉米)`, `CF (棉花)`, `AU (黄金)`

```python
# 示例：商品名称显示
display_name = f"{commodity_name} ({chinese_name})" if chinese_name != commodity_name else chinese_name
```

---

### 8. UI 颜色规范（CRITICAL）

**中国股市颜色：红涨绿跌**

#### Streamlit metric 颜色设置

```python
# 正收益/上涨用红色，负收益/下跌用绿色
# Streamlit: "normal"=正绿负红 (国际), "inverse"=正红负绿 (中国)
delta_color = "inverse" if value >= 0 else "normal"

st.metric("涨跌幅", f"{change_pct:+.1f}%", delta=delta, delta_color=delta_color)
```

#### 适用场景

- 持仓管理页面：盈亏比例、盈亏金额
- 智能荐股页面：涨跌幅、综合评分变化
- 选股器页面：涨跌幅、资金流入
- 大宗商品页面：价格涨跌幅

#### 颜色含义

- 🔴 红色 = 上涨/正收益（喜庆）
- 🟢 绿色 = 下跌/负收益

#### Streamlit delta_color 参数

- `"normal"`: 正数红色，负数绿色（符合中国股市）
- `"inverse"`: 正数绿色，负数红色（用于期货等国际市场）
- `"off"`: 不显示颜色

---

### 9. 测试验证规范（CRITICAL）

**每一次代码改动后必须完整测试相关功能**

#### 测试检查清单

每次修改后必须执行：

1. **语法检查**
```bash
python -m py_compile <filename>.py
```

2. **导入测试**
```bash
python -c "import <module>"
```

3. **功能测试**
- 启动 Streamlit: `streamlit run ui/app.py`
- 访问修改的页面
- 验证功能是否正常工作
- 检查是否有错误信息

4. **数据验证**
- 检查数据库连接
- 验证数据查询结果
- 确认数据显示格式

---

## 检查清单

提交前检查：
- [ ] 所有股票展示是否包含名称
- [ ] 数据库连接是否关闭
- [ ] API 调用是否有错误处理
- [ ] 空数据是否有友好提示
- [ ] 用户操作是否有反馈
- [ ] 已通过语法检查
- [ ] 已测试相关功能
