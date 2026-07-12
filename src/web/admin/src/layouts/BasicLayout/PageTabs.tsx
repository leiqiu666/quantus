import { Tabs, Dropdown } from 'antd';
import type { TabsProps, MenuProps } from 'antd';
import { useTabs } from '@/hooks/useTabs';

/**
 * 多 Tab 标签页组件。
 *
 * 行为：
 *  - 点击 Tab → 切换 URL（useTabs.switchTo）
 *  - 点击关闭按钮 → 移除 Tab + 跳到相邻 Tab
 *  - 右键 Tab → 关闭其他 / 关闭全部
 */
export default function PageTabs() {
  const { tabs, activeKey, switchTo, close, closeOthers, closeAll } = useTabs();

  if (!tabs.length) return null;

  const items: TabsProps['items'] = tabs.map((t) => ({
    key: t.key,
    label: <TabLabel tabKey={t.key} label={t.label} />,
    closable: t.closable,
  }));

  const onEdit: TabsProps['onEdit'] = (targetKey, action) => {
    if (action === 'remove' && typeof targetKey === 'string') {
      close(targetKey);
    }
  };

  function TabLabel({ tabKey, label }: { tabKey: string; label: string }) {
    const menuItems: MenuProps['items'] = [
      { key: 'closeOthers', label: '关闭其他' },
      { key: 'closeAll', label: '关闭全部' },
    ];

    return (
      <Dropdown
        trigger={['contextMenu']}
        menu={{
          items: menuItems,
          onClick: ({ key }) => {
            if (key === 'closeOthers') closeOthers(tabKey);
            else if (key === 'closeAll') closeAll();
          },
        }}
      >
        <span>{label}</span>
      </Dropdown>
    );
  }

  return (
    <div className="bg-white px-2 pt-2 border-b border-gray-200">
      <Tabs
        type="editable-card"
        hideAdd
        size="small"
        activeKey={activeKey}
        items={items}
        onChange={switchTo}
        onEdit={onEdit}
        tabBarStyle={{ margin: 0 }}
      />
    </div>
  );
}
