export type Tag = {
  id: number;
  name: string;
  color: string;
  document_count: number;
  created_at: string;
};

export type TagCreateInput = {
  name: string;
  color: string;
};

export function tagToSelectOption(tag: Tag): { label: string; value: number } {
  return { label: tag.name, value: tag.id };
}

