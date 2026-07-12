---
doc_id: 295
title: "中央结算系统持股汇总"
api_name: "ccass_hold"
url: "https://tushare.pro/document/2?doc_id=295"
---

## 中央结算系统持股汇总

---

接口：ccass_hold  
描述：获取中央结算系统持股汇总数据，覆盖全部历史数据，根据交易所披露时间，当日数据在下一交易日早上9点前完成入库  
限量：单次最大5000条数据，可循环或分页提供全部  
积分：用户120积分可以试用看数据，5000积分每分钟可以请求300次，8000积分以上可以请求500次每分钟，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | 股票代码 (e.g. 605009.SH) |
| hk_code | str | N | 港交所代码 （e.g. 95009） |
| trade_date | str | N | 交易日期(YYYYMMDD格式，下同) |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| trade_date | str | Y | 交易日期 |
| ts_code | str | Y | 股票代号 |
| name | str | Y | 股票名称 |
| shareholding | str | Y | 于中央结算系统的持股量(股)Shareholding in CCASS |
| hold_nums | str | Y | 参与者数目（个） |
| hold_ratio | str | Y | 占于上交所上市及交易的A股总数的百分比（%）% of the total number of A shares listed and traded on the SSE |

Note:
**接口用法**

### 数据样例
