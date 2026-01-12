import { Card, Tree } from 'antd';
import type { DataNode } from 'antd/es/tree';
import { useMemo } from 'react';

import type { FolderTreeNode } from '../../types/folder';

export type FolderTreeProps = {
  folders: FolderTreeNode[];
  selectedId: number | null;
  onSelect: (folderId: number | null) => void;
};

function mapToTreeData(nodes: FolderTreeNode[]): DataNode[] {
  return nodes.map((node) => ({
    key: String(node.id),
    title: node.name,
    children: node.children?.length ? mapToTreeData(node.children) : undefined
  }));
}

function collectKeys(nodes: FolderTreeNode[]): string[] {
  const keys: string[] = [];
  for (const node of nodes) {
    keys.push(String(node.id));
    if (node.children?.length) keys.push(...collectKeys(node.children));
  }
  return keys;
}

export default function FolderTree(props: FolderTreeProps) {
  const treeData: DataNode[] = [
    { key: 'all', title: '全部文件夹', children: mapToTreeData(props.folders) }
  ];

  const selectedKeys = props.selectedId ? [String(props.selectedId)] : ['all'];
  const expandedKeys = useMemo(() => ['all', ...collectKeys(props.folders)], [props.folders]);

  return (
    <Card size="small" title="文件夹">
      <Tree
        aria-label="folder-tree"
        blockNode
        expandedKeys={expandedKeys}
        selectedKeys={selectedKeys}
        treeData={treeData}
        onSelect={(keys) => {
          const key = keys[0];
          if (!key || key === 'all') {
            props.onSelect(null);
            return;
          }
          const id = Number(key);
          props.onSelect(Number.isFinite(id) ? id : null);
        }}
      />
    </Card>
  );
}
