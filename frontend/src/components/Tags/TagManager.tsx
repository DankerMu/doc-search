import { Button, Card, Form, Input, Modal, Popconfirm, Space, Table, Tag as AntTag, Typography } from 'antd';
import { useMemo, useState } from 'react';

import { useCreateTag, useDeleteTag, useTags, useUpdateTag } from '../../hooks/useTags';
import type { Tag, TagCreateInput } from '../../types/tag';

type EditorState =
  | { open: false }
  | { open: true; mode: 'create'; initial: TagCreateInput }
  | { open: true; mode: 'edit'; tagId: number; initial: TagCreateInput };

export default function TagManager() {
  const tagsQuery = useTags();
  const createTag = useCreateTag();
  const updateTag = useUpdateTag();
  const deleteTag = useDeleteTag();

  const [form] = Form.useForm<TagCreateInput>();
  const [editor, setEditor] = useState<EditorState>({ open: false });

  const openCreate = () => {
    const initial: TagCreateInput = { name: '', color: '#3B82F6' };
    form.setFieldsValue(initial);
    setEditor({ open: true, mode: 'create', initial });
  };

  const openEdit = (tag: Tag) => {
    const initial: TagCreateInput = { name: tag.name, color: tag.color };
    form.setFieldsValue(initial);
    setEditor({ open: true, mode: 'edit', tagId: tag.id, initial });
  };

  const columns = useMemo(
    () => [
      {
        title: '名称',
        dataIndex: 'name',
        key: 'name',
        render: (_: unknown, tag: Tag) => <AntTag color={tag.color}>{tag.name}</AntTag>
      },
      { title: '文档数', dataIndex: 'document_count', key: 'document_count' },
      {
        title: '操作',
        key: 'actions',
        render: (_: unknown, tag: Tag) => (
          <Space>
            <Button aria-label={`tag-edit-${tag.id}`} type="link" onClick={() => openEdit(tag)}>
              编辑
            </Button>
            <Popconfirm
              title="确定删除该标签？"
              okText="删除"
              cancelText="取消"
              onConfirm={() => deleteTag.mutate(tag.id)}
            >
              <Button aria-label={`tag-delete-${tag.id}`} type="link" danger>
                删除
              </Button>
            </Popconfirm>
          </Space>
        )
      }
    ],
    [deleteTag, form],
  );

  return (
    <Card
      title="标签管理"
      extra={
        <Button type="primary" onClick={openCreate} aria-label="tag-create">
          新建标签
        </Button>
      }
    >
      {tagsQuery.isError ? (
        <Typography.Text type="danger">标签加载失败</Typography.Text>
      ) : (
        <Table
          aria-label="tag-table"
          rowKey="id"
          loading={tagsQuery.isLoading}
          columns={columns}
          dataSource={tagsQuery.data ?? []}
          pagination={false}
        />
      )}

      <Modal
        open={editor.open}
        title={editor.open && editor.mode === 'edit' ? '编辑标签' : '新建标签'}
        okText="保存"
        cancelText="取消"
        confirmLoading={createTag.isPending || updateTag.isPending}
        onCancel={() => setEditor({ open: false })}
        onOk={async () => {
          const values = await form.validateFields();
          if (editor.open && editor.mode === 'edit') {
            await updateTag.mutateAsync({ id: editor.tagId, patch: values });
          } else {
            await createTag.mutateAsync(values);
          }
          setEditor({ open: false });
        }}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入名称' }]}
          >
            <Input aria-label="tag-name" placeholder="例如：合同" />
          </Form.Item>
          <Form.Item
            name="color"
            label="颜色"
            rules={[
              { required: true, message: '请输入颜色' },
              { pattern: /^#[0-9A-Fa-f]{6}$/, message: '格式应为 #RRGGBB' }
            ]}
          >
            <Input aria-label="tag-color" placeholder="#3B82F6" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}

