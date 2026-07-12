import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Provider as ReduxProvider } from 'react-redux';
import { RouterProvider } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { store } from '@/store';
import { router } from '@/routes';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ReduxProvider store={store}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          cssVar: {},
          hashed: false,
          token: {
            colorPrimary: '#2563eb',
            borderRadius: 6,
          },
        }}
      >
        <RouterProvider router={router} />
      </ConfigProvider>
    </ReduxProvider>
  </StrictMode>,
);
