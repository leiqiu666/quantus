import {
  HomeOutlined,
  AppstoreOutlined,
  DatabaseOutlined,
  StockOutlined,
  ClockCircleOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import { Navigate } from 'react-router-dom';
import type { RouteConfig } from '@/types/route';
import Home from '@/pages/Home';
import Demo1 from '@/pages/demo/Demo1';
import Demo2 from '@/pages/demo/Demo2';
import NotFound from '@/pages/NotFound';
import FeatureList from '@/pages/quant/FeatureList';
import FactorList from '@/pages/quant/FactorList';
import FactorComboPage from '@/pages/quant/FactorCombo';
import BacktestPage from '@/pages/quant/Backtest';
import FactorCsPage from '@/pages/research/FactorCs';
import StockKlinePage from '@/pages/research/StockKline';
import BacktestTradesPage from '@/pages/research/BacktestTrades';
import QuotePage from '@/pages/research/Quote';
import FinancialReportPeriodPage from '@/pages/dataSource/FinancialReportPeriodPage';
import OverviewPage from '@/pages/dataSource/OverviewPage';
import FinancialAnnDatePage from '@/pages/dataSource/FinancialAnnDatePage';
import KlineTradeDatePage from '@/pages/dataSource/KlineTradeDatePage';
import MarketTradeDatePage from '@/pages/dataSource/MarketTradeDatePage';
import IndexMonthPage from '@/pages/dataSource/IndexMonthPage';
import IndexTradeDatePage from '@/pages/dataSource/IndexTradeDatePage';
import StockBasicTradeDatePage from '@/pages/dataSource/StockBasicTradeDatePage';
import SchedulerOverviewPage from '@/pages/scheduler/Overview';
import SchedulerJobListPage from '@/pages/scheduler/JobList';
import SchedulerJobEditPage from '@/pages/scheduler/JobEdit';
import SchedulerRunListPage from '@/pages/scheduler/RunList';

export const routesConfig: RouteConfig[] = [
  {
    path: '/',
    name: '首页',
    icon: <HomeOutlined />,
    element: <Home />,
    closable: false,
  },
  {
    path: '/demo',
    name: 'Demo',
    icon: <AppstoreOutlined />,
    children: [
      {
        path: '/demo/page1',
        name: 'Demo页面1',
        element: <Demo1 />,
      },
      {
        path: '/demo/page2',
        name: 'Demo页面2',
        element: <Demo2 />,
      },
    ],
  },
  {
    path: '/data-source',
    name: '量化数据源',
    icon: <DatabaseOutlined />,
    children: [
      {
        path: '/data-source/overview',
        name: '数据总览',
        element: <OverviewPage />,
      },
      {
        path: '/data-source',
        name: '量化数据源首页重定向',
        element: <Navigate to="/data-source/overview" replace />,
        hideInMenu: true,
        closable: true,
      },
      {
        path: '/data-source/financial/period',
        name: '财务类/报告期',
        element: <FinancialReportPeriodPage />,
      },
      {
        path: '/data-source/financial/period-core',
        name: '财务类报告期重定向',
        element: <Navigate to="/data-source/financial/period" replace />,
        hideInMenu: true,
        closable: true,
      },
      {
        path: '/data-source/financial/period-extended',
        name: '财务类报告期扩展重定向',
        element: <Navigate to="/data-source/financial/period" replace />,
        hideInMenu: true,
        closable: true,
      },
      {
        path: '/data-source/financial/ann-date',
        name: '财务类/公告日',
        element: <FinancialAnnDatePage />,
      },
      {
        path: '/data-source/kline/trade-date',
        name: 'K线类/交易日',
        element: <KlineTradeDatePage />,
      },
      {
        path: '/data-source/market/trade-date',
        name: '市场类/交易日',
        element: <MarketTradeDatePage />,
      },
      {
        path: '/data-source/index/month',
        name: '指数类/月',
        element: <IndexMonthPage />,
      },
      {
        path: '/data-source/index/trade-date',
        name: '指数类/交易日',
        element: <IndexTradeDatePage />,
      },
      {
        path: '/data-source/stock/trade-date',
        name: '基础类/交易日',
        element: <StockBasicTradeDatePage />,
      },
    ],
  },
  {
    path: '/scheduler',
    name: '调度系统',
    icon: <ClockCircleOutlined />,
    children: [
      {
        path: '/scheduler/overview',
        name: '命令看板',
        element: <SchedulerOverviewPage />,
      },
      {
        path: '/scheduler/jobs',
        name: '任务管理',
        element: <SchedulerJobListPage />,
      },
      {
        path: '/scheduler/jobs/edit',
        name: '任务编辑',
        element: <SchedulerJobEditPage />,
        hideInMenu: true,
      },
      {
        path: '/scheduler/runs',
        name: '执行历史',
        element: <SchedulerRunListPage />,
      },
    ],
  },
  {
    path: '/quant',
    name: '因子管理',
    icon: <StockOutlined />,
    children: [
      {
        path: '/quant/feature-list',
        name: '特征管理',
        element: <FeatureList />,
      },
      {
        path: '/quant/factor-list',
        name: '因子列表',
        element: <FactorList />,
      },
      {
        path: '/quant/factor-combo',
        name: '因子组合',
        element: <FactorComboPage />,
      },
      {
        path: '/quant/backtest',
        name: '回测',
        element: <BacktestPage />,
      },
    ],
  },
  {
    path: '/research',
    name: '投研分析',
    icon: <LineChartOutlined />,
    children: [
      {
        path: '/research/factor-cs',
        name: '因子截面',
        element: <FactorCsPage />,
      },
      {
        path: '/research/stock-kline',
        name: '个股K线',
        element: <StockKlinePage />,
      },
      {
        path: '/research/backtest-trades',
        name: '回测明细',
        element: <BacktestTradesPage />,
      },
      {
        path: '/research/quote',
        name: '行情快照',
        element: <QuotePage />,
      },
    ],
  },
  {
    path: '/fundamental/report-period-list',
    name: '财报列表重定向',
    element: <Navigate to="/data-source/financial/period" replace />,
    hideInMenu: true,
    closable: true,
  },
  {
    path: '/fundamental/kline-daily-date-list',
    name: '日K列表重定向',
    element: <Navigate to="/data-source/kline/trade-date" replace />,
    hideInMenu: true,
    closable: true,
  },
  {
    path: '*',
    name: '未找到',
    element: <NotFound />,
    hideInMenu: true,
    closable: true,
  },
];

export const fallbackRedirect = {
  path: '/index',
  element: <Navigate to="/" replace />,
};
