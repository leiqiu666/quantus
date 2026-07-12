---
doc_id: 151
title: "LPR贷款基础利率"
api_name: "shibor_lpr"
url: "https://tushare.pro/document/2?doc_id=151"
---

## LPR贷款基础利率

---

接口：shibor_lpr  
描述：LPR贷款基础利率  
限量：单次最大4000(相当于单次可提取18年历史)，总量不限制，可通过设置开始和结束日期分段获取  
积分：用户积累120积分可以调取，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)
**LPR介绍**

### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| date | str | N | 日期  (日期输入格式：YYYYMMDD，下同) |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| date | str | Y | 日期 |
| 1y | float | Y | 1年贷款利率 |
| 5y | float | Y | 5年贷款利率 |

**接口调用**

### 数据样例
