import { Button, Result } from 'antd';
import { Link } from 'react-router-dom';

import useDocumentTitle from '../hooks/useDocumentTitle';
import { ROUTES } from '../types/routes';

export default function NotFound() {
  useDocumentTitle('Doc Search - 404');

  return (
    <Result
      status="404"
      title="页面不存在"
      extra={
        <Link to={ROUTES.home}>
          <Button type="primary">返回首页</Button>
        </Link>
      }
    />
  );
}
