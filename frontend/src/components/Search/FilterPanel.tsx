import { Button, Card, Col, Input, Row, Select, Space, TreeSelect } from 'antd';

import type { FolderTreeNode } from '../../types/folder';
import { foldersToTreeSelectData } from '../../types/folder';
import type { Tag } from '../../types/tag';
import { tagToSelectOption } from '../../types/tag';
import type { SearchFilters } from '../../types/search';
import { FILE_TYPE_OPTIONS } from '../../types/document';

export type FilterPanelProps = {
  value: SearchFilters;
  onChange: (next: SearchFilters) => void;
  folders: FolderTreeNode[];
  tags: Tag[];
};

export default function FilterPanel(props: FilterPanelProps) {
  const treeData = foldersToTreeSelectData(props.folders);
  const tagOptions = props.tags.map(tagToSelectOption);
  const dateFrom = props.value.date_from ? props.value.date_from.slice(0, 10) : '';
  const dateTo = props.value.date_to ? props.value.date_to.slice(0, 10) : '';

  return (
    <Card
      size="small"
      title="高级过滤"
      extra={
        <Button onClick={() => props.onChange({})} aria-label="filters-reset">
          重置
        </Button>
      }
    >
      <Row gutter={[12, 12]}>
        <Col xs={24} sm={12} md={6}>
          <Select
            aria-label="filter-type"
            allowClear
            placeholder="类型"
            options={[...FILE_TYPE_OPTIONS]}
            value={props.value.type}
            onChange={(value) => props.onChange({ ...props.value, type: value })}
            style={{ width: '100%' }}
          />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <TreeSelect
            aria-label="filter-folder"
            allowClear
            placeholder="文件夹"
            treeData={treeData}
            value={props.value.folder_id ?? undefined}
            onChange={(value) =>
              props.onChange({ ...props.value, folder_id: typeof value === 'number' ? value : null })
            }
            style={{ width: '100%' }}
          />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Select
            aria-label="filter-tags"
            allowClear
            mode="multiple"
            placeholder="标签"
            options={tagOptions}
            value={props.value.tag_ids}
            onChange={(value) => props.onChange({ ...props.value, tag_ids: value })}
            style={{ width: '100%' }}
          />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Space.Compact style={{ width: '100%' }}>
            <Input
              aria-label="filter-date-from"
              type="date"
              value={dateFrom}
              onChange={(e) =>
                props.onChange({
                  ...props.value,
                  date_from: e.target.value
                    ? new Date(`${e.target.value}T00:00:00.000Z`).toISOString()
                    : null
                })
              }
            />
            <Input
              aria-label="filter-date-to"
              type="date"
              value={dateTo}
              onChange={(e) =>
                props.onChange({
                  ...props.value,
                  date_to: e.target.value
                    ? new Date(`${e.target.value}T23:59:59.999Z`).toISOString()
                    : null
                })
              }
            />
          </Space.Compact>
        </Col>
      </Row>
    </Card>
  );
}
