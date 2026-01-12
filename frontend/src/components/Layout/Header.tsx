import { Layout, Typography } from 'antd';

export default function Header() {
  return (
    <Layout.Header
      style={{
        background: '#fff',
        paddingInline: 24,
        display: 'flex',
        alignItems: 'center'
      }}
    >
      <Typography.Title level={4} style={{ margin: 0 }}>
        Doc Search
      </Typography.Title>
    </Layout.Header>
  );
}

