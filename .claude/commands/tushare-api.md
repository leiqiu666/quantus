# Tushare API 文档获取

通过 tushare SDK + API 获取接口字段定义，绕过 WebFetch 无法访问 SPA 页面的限制。

## 步骤

### 1. 用 SDK 获取输出字段

```python
uv run python -c "
import tushare as ts
pro = ts.pro_api()

# 用 _vip 接口按 period 拉取全市场数据，获取完整字段列表
api_name = '$ARGUMENTS'  # 如 fina_indicator_vip
method = getattr(pro, api_name, None)
if method is None:
    print(f'接口 {api_name} 不存在')
else:
    try:
        df = method(period='20240331')
    except TypeError:
        # 非财报类接口可能不支持 period，尝试 trade_date
        try:
            df = method(trade_date='20240331')
        except Exception as e2:
            print(f'调用失败: {e2}')
            df = None
    except Exception as e:
        print(f'调用失败: {e}')
        df = None

    if df is not None:
        print(f'接口: {api_name}')
        print(f'字段数: {len(df.columns)}')
        print(f'数据行数: {len(df)}')
        print()
        print('=== 字段列表 ===')
        for col in df.columns:
            dtype = str(df[col].dtype) if len(df) > 0 else 'unknown'
            sample = df[col].dropna().iloc[0] if len(df[col].dropna()) > 0 else None
            print(f'{col:40s} {dtype:15s} sample={sample}')
"
```

### 2. 用 API 获取字段描述

如果 SDK 返回的字段名不够直观，可调用 `api://` 接口获取字段描述：

```python
uv run python -c "
import tushare as ts
pro = ts.pro_api()

# 尝试通过 query 获取字段说明
from tushare.pro.client import DataApi
import json

# 获取接口的 field 描述
result = pro.query('get_field', api_name='$ARGUMENTS')
print(result)
"
```

### 3. 查看输入参数

通过 SDK 源码查看接口支持的参数：

```python
uv run python -c "
import tushare as ts
import inspect

pro = ts.pro_api()
method = getattr(pro, '$ARGUMENTS', None)
if method:
    sig = inspect.signature(method)
    print(f'方法签名: {sig}')
    # 打印 docstring
    if method.__doc__:
        print(f'Doc: {method.__doc__}')

# 查看 tushare pro client 源码中 query 方法的实现
client_src = inspect.getfile(ts.pro.client)
print(f'Client 源码: {client_src}')
"
```

## 注意事项

- `fina_indicator`（非 VIP）必须传 `ts_code`，不能按 period 全市场拉取
- `fina_indicator_vip` 需要 5000 积分，支持 `period` 参数拉取全市场
- 非财报类接口（如 `daily`、`adj_factor`）的参数可能是 `trade_date` 而非 `period`
- 如果 SDK 调用报错 "必填参数"，说明该接口不支持按 period/trade_date 拉取，需要指定 ts_code
- 字段列表中 `dtype` 为 `object` 通常是字符串，`float64` 是浮点数，`int64` 是整数
