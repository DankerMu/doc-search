import { Layout, Menu } from 'antd';
import type { MenuProps } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';

import { ROUTES } from '../../types/routes';

const menuKeys = [ROUTES.home, ROUTES.search, ROUTES.documents];
const items: MenuProps['items'] = [
  { key: ROUTES.home, label: '首页' },
  { key: ROUTES.search, label: '搜索' },
  { key: ROUTES.documents, label: '文档' }
];

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const selectedKeys = menuKeys.includes(location.pathname) ? [location.pathname] : [];

  return (
    <Layout.Sider breakpoint="lg" collapsedWidth="0">
      <div style={{ height: 32, margin: 16, color: 'rgba(255, 255, 255, 0.85)' }}>Doc Search</div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={selectedKeys}
        items={items}
        onClick={({ key }) => navigate(key)}
      />
    </Layout.Sider>
  );
}
