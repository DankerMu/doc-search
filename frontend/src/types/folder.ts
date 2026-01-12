export type FolderTreeNode = {
  id: number;
  name: string;
  parent_id: number | null;
  children: FolderTreeNode[];
};

export type FolderTreeSelectNode = {
  title: string;
  value: number;
  children?: FolderTreeSelectNode[];
};

export function foldersToTreeSelectData(nodes: FolderTreeNode[]): FolderTreeSelectNode[] {
  return nodes.map((node) => ({
    title: node.name,
    value: node.id,
    children: node.children?.length ? foldersToTreeSelectData(node.children) : undefined
  }));
}

