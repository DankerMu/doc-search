import { Button, Descriptions, Drawer, Space, Spin, Typography } from 'antd';

import { getDocumentDownloadUrl, useDocumentDetail } from '../../hooks/useDocuments';
import { formatFileSize } from '../../types/document';

export type DocumentPreviewProps = {
  open: boolean;
  documentId: number | null;
  query: string;
  onClose: () => void;
};

function escapeRegExp(input: string): string {
  return input.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function highlightText(text: string, query: string) {
  const trimmed = query.trim();
  if (!trimmed) return text;

  const terms = Array.from(new Set(trimmed.split(/\s+/).filter(Boolean))).slice(0, 8);
  if (!terms.length) return text;

  const regex = new RegExp(`(${terms.map(escapeRegExp).join('|')})`, 'gi');
  const nodes: Array<string | JSX.Element> = [];
  let lastIndex = 0;

  for (const match of text.matchAll(regex)) {
    if (typeof match.index !== 'number') continue;
    const start = match.index;
    const matched = match[0] ?? '';
    if (!matched) continue;

    nodes.push(text.slice(lastIndex, start));
    nodes.push(<mark key={`${start}-${matched}`}>{matched}</mark>);
    lastIndex = start + matched.length;
  }

  nodes.push(text.slice(lastIndex));
  return <>{nodes}</>;
}

export default function DocumentPreview(props: DocumentPreviewProps) {
  const detailQuery = useDocumentDetail(props.documentId, props.open);
  const document = detailQuery.data;

  return (
    <Drawer
      open={props.open}
      width={720}
      title={document?.original_name ?? '文档预览'}
      onClose={props.onClose}
      extra={
        document ? (
          <Space>
            <Button
              type="primary"
              href={getDocumentDownloadUrl(document.id)}
              target="_blank"
              rel="noreferrer"
            >
              下载原文件
            </Button>
          </Space>
        ) : null
      }
    >
      {detailQuery.isLoading ? (
        <Spin />
      ) : document ? (
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Descriptions size="small" column={1} bordered>
            <Descriptions.Item label="类型">{document.file_type}</Descriptions.Item>
            <Descriptions.Item label="大小">{formatFileSize(document.file_size)}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{new Date(document.created_at).toLocaleString()}</Descriptions.Item>
          </Descriptions>
          <Typography.Paragraph style={{ marginBottom: 0 }}>全文</Typography.Paragraph>
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
            {highlightText(document.content_text ?? '', props.query) || (
              <Typography.Text type="secondary">暂无内容</Typography.Text>
            )}
          </div>
        </Space>
      ) : (
        <Typography.Text type="secondary">未选择文档</Typography.Text>
      )}
    </Drawer>
  );
}

