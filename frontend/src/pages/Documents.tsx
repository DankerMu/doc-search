import { Alert, Button, Col, Row, Space, Table, Tabs, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useMemo, useState } from 'react';

import DocumentPreview from '../components/Documents/DocumentPreview';
import FileUploader from '../components/Documents/FileUploader';
import FolderTree from '../components/Folders/FolderTree';
import TagManager from '../components/Tags/TagManager';
import { getDocumentDownloadUrl, useDocuments } from '../hooks/useDocuments';
import { useFolders } from '../hooks/useFolders';
import useDocumentTitle from '../hooks/useDocumentTitle';
import type { Document } from '../types/document';
import { formatFileSize } from '../types/document';

export default function DocumentsPage() {
  useDocumentTitle('Doc Search - 文档');

  const [folderId, setFolderId] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [previewDocumentId, setPreviewDocumentId] = useState<number | null>(null);

  const foldersQuery = useFolders();
  const documentsQuery = useDocuments({ folderId, page, pageSize });

  const columns: ColumnsType<Document> = useMemo(
    () => [
      { title: '名称', dataIndex: 'original_name', key: 'original_name' },
      { title: '类型', dataIndex: 'file_type', key: 'file_type', width: 100 },
      {
        title: '大小',
        dataIndex: 'file_size',
        key: 'file_size',
        width: 120,
        render: (size: number) => formatFileSize(size)
      },
      {
        title: '创建时间',
        dataIndex: 'created_at',
        key: 'created_at',
        width: 180,
        render: (value: string) => new Date(value).toLocaleString()
      },
      {
        title: '操作',
        key: 'actions',
        width: 160,
        render: (_: unknown, doc: Document) => (
          <Space>
            <Button type="link" onClick={() => setPreviewDocumentId(doc.id)} aria-label={`doc-preview-${doc.id}`}>
              预览
            </Button>
            <Button type="link" href={getDocumentDownloadUrl(doc.id)} target="_blank" rel="noreferrer">
              下载
            </Button>
          </Space>
        )
      }
    ],
    [],
  );

  return (
    <Tabs
      items={[
        {
          key: 'documents',
          label: '文档',
          children: (
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <FileUploader folderId={folderId} />

              <Row gutter={[16, 16]}>
                <Col xs={24} lg={8}>
                  <FolderTree
                    folders={foldersQuery.data ?? []}
                    selectedId={folderId}
                    onSelect={(nextFolderId) => {
                      setFolderId(nextFolderId);
                      setPage(1);
                    }}
                  />
                </Col>
                <Col xs={24} lg={16}>
                  {documentsQuery.isError ? (
                    <Alert type="error" message="文档加载失败" showIcon />
                  ) : (
                    <Table
                      aria-label="documents-table"
                      rowKey="id"
                      loading={documentsQuery.isLoading}
                      columns={columns}
                      dataSource={documentsQuery.data?.items ?? []}
                      pagination={{
                        current: page,
                        pageSize,
                        total: documentsQuery.data?.total ?? 0,
                        onChange: (nextPage, nextSize) => {
                          setPage(nextPage);
                          setPageSize(nextSize);
                        }
                      }}
                    />
                  )}
                </Col>
              </Row>

              <Typography.Text type="secondary">
                选择文件夹后上传，将自动关联 folder_id。
              </Typography.Text>

              <DocumentPreview
                open={previewDocumentId !== null}
                documentId={previewDocumentId}
                query=""
                onClose={() => setPreviewDocumentId(null)}
              />
            </Space>
          )
        },
        { key: 'tags', label: '标签', children: <TagManager /> }
      ]}
    />
  );
}
