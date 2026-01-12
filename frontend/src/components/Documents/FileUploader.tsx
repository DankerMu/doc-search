import { InboxOutlined } from '@ant-design/icons';
import { Upload, Typography } from 'antd';
import type { UploadRequestOption as RcUploadRequestOption } from 'rc-upload/lib/interface';

import { useUploadDocument } from '../../hooks/useDocuments';

export type FileUploaderProps = {
  folderId?: number | null;
  onUploaded?: () => void;
};

export default function FileUploader(props: FileUploaderProps) {
  const uploadMutation = useUploadDocument();

  return (
    <Upload.Dragger
      aria-label="file-uploader"
      name="file"
      multiple={false}
      showUploadList
      customRequest={async (options: RcUploadRequestOption) => {
        const file = options.file instanceof File ? options.file : null;
        if (!file) {
          options.onError?.(new Error('Invalid file'));
          return;
        }

        try {
          await uploadMutation.mutateAsync({
            file,
            folderId: props.folderId,
            onProgress: (percent) => options.onProgress?.({ percent })
          });
          options.onSuccess?.({}, file);
          props.onUploaded?.();
        } catch (err) {
          options.onError?.(err as Error);
        }
      }}
    >
      <p className="ant-upload-drag-icon">
        <InboxOutlined />
      </p>
      <Typography.Paragraph style={{ marginBottom: 0 }}>拖拽文件到此处，或点击上传</Typography.Paragraph>
      <Typography.Text type="secondary">支持 PDF / DOC(X) / MD / XLS(X)</Typography.Text>
    </Upload.Dragger>
  );
}
