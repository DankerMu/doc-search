import { Input } from 'antd';

export type SearchBarProps = {
  value: string;
  onChange: (next: string) => void;
  loading?: boolean;
};

export default function SearchBar({ value, onChange, loading }: SearchBarProps) {
  return (
    <Input
      aria-label="search-input"
      allowClear
      size="large"
      placeholder="输入关键词搜索…"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={loading}
    />
  );
}

