import { Card, Typography } from 'antd';

import useDocumentTitle from '../hooks/useDocumentTitle';

export default function Home() {
  useDocumentTitle('Doc Search - 首页');

  return (
    <Card>
      <Typography.Title level={3} style={{ marginTop: 0 }}>
        欢迎使用 Doc Search
      </Typography.Title>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
        请从左侧导航开始。
      </Typography.Paragraph>
    </Card>
  );
}

