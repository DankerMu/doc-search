import { Button, List, Space, Tag, Typography } from 'antd';

import type { SearchResultItem } from '../../types/search';

export type SearchResultsProps = {
  items: SearchResultItem[];
  loading?: boolean;
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number, pageSize: number) => void;
  onPreview: (documentId: number) => void;
};

type HighlightPart = { text: string; marked: boolean };

function splitMarkedText(input: string): HighlightPart[] {
  if (!input) return [];

  const parts: HighlightPart[] = [];
  let rest = input;
  while (true) {
    const start = rest.indexOf('<mark>');
    if (start === -1) {
      if (rest) parts.push({ text: rest, marked: false });
      break;
    }

    const before = rest.slice(0, start);
    if (before) parts.push({ text: before, marked: false });
    rest = rest.slice(start + '<mark>'.length);

    const end = rest.indexOf('</mark>');
    if (end === -1) {
      if (rest) parts.push({ text: rest, marked: true });
      break;
    }

    const markedText = rest.slice(0, end);
    if (markedText) parts.push({ text: markedText, marked: true });
    rest = rest.slice(end + '</mark>'.length);
  }

  return parts;
}

function HighlightSnippet({ html }: { html: string }) {
  const parts = splitMarkedText(html);
  if (!parts.length) return null;

  return (
    <Typography.Paragraph style={{ marginBottom: 0 }} type="secondary" ellipsis={{ rows: 2 }}>
      {parts.map((part, idx) =>
        part.marked ? (
          <mark key={idx}>{part.text}</mark>
        ) : (
          <span key={idx}>{part.text}</span>
        ),
      )}
    </Typography.Paragraph>
  );
}

export default function SearchResults(props: SearchResultsProps) {
  return (
    <List
      aria-label="search-results"
      loading={props.loading}
      dataSource={props.items}
      pagination={{
        current: props.page,
        pageSize: props.pageSize,
        total: props.total,
        onChange: props.onPageChange,
        showSizeChanger: true,
        showTotal: (total) => `共 ${total} 条`
      }}
      renderItem={(item) => (
        <List.Item
          actions={[
            <Button key="preview" type="link" onClick={() => props.onPreview(item.doc_id)}>
              预览
            </Button>
          ]}
        >
          <List.Item.Meta
            title={
              <Space size={12} wrap>
                <Typography.Text strong>{`文档 #${item.doc_id}`}</Typography.Text>
                <Tag>{item.file_type || 'unknown'}</Tag>
              </Space>
            }
            description={<HighlightSnippet html={item.highlight} />}
          />
        </List.Item>
      )}
    />
  );
}

