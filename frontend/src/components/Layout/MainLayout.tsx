import { Layout } from 'antd';
import { Outlet } from 'react-router-dom';

import Header from './Header';
import Sidebar from './Sidebar';

const { Content } = Layout;

export default function MainLayout() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sidebar />
      <Layout>
        <Header />
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}

