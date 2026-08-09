import { useState, useRef, useCallback } from "react";
import { Upload, FileSpreadsheet, X } from "lucide-react";

interface QueuedFile {
  name: string;
  size: number;
  file: File;
}

interface FileDropZoneProps {
  files: QueuedFile[];
  onFilesAdded: (files: File[]) => void;
  onRemoveFile: (index: number) => void;
  onClearAll: () => void;
  uploading?: boolean;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FileDropZone({
  files,
  onFilesAdded,
  onRemoveFile,
  onClearAll,
  uploading,
}: FileDropZoneProps) {
  const [dragover, setDragover] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragover(false);
      const dropped = Array.from(e.dataTransfer.files).filter((f) =>
        f.name.toLowerCase().endsWith(".xlsx")
      );
      if (dropped.length) onFilesAdded(dropped);
    },
    [onFilesAdded]
  );

  const handleBrowse = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      onFilesAdded(Array.from(e.target.files).filter((f) =>
        f.name.toLowerCase().endsWith(".xlsx")
      ));
      e.target.value = "";
    }
  };

  return (
    <div className="space-y-3">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
        onDragLeave={() => setDragover(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-card p-10 text-center cursor-pointer transition-all duration-200 ${
          dragover
            ? "border-accent bg-nav-hover scale-[1.01]"
            : "border-border hover:border-text-muted"
        } ${uploading ? "pointer-events-none opacity-60" : ""}`}
      >
        <Upload
          size={40}
          className={`mx-auto mb-3 transition-colors ${
            dragover ? "text-accent" : "text-text-muted"
          }`}
          strokeWidth={1.5}
        />
        <p className="text-sm font-medium text-text-primary">
          {dragover ? "Drop files here" : "Drag & drop .xlsx files here"}
        </p>
        <p className="text-xs text-text-secondary mt-1">or click to browse</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".xlsx"
          className="hidden"
          onChange={handleBrowse}
        />
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="card-container p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
              Queued Files ({files.length})
            </span>
            {!uploading && (
              <button
                onClick={onClearAll}
                className="text-xs text-text-muted hover:text-danger transition-colors"
              >
                Clear all
              </button>
            )}
          </div>
          <div className="space-y-1">
            {files.map((f, i) => (
              <div
                key={`${f.name}-${i}`}
                className="flex items-center gap-3 px-3 py-2 rounded-btn hover:bg-nav-hover transition-colors group"
              >
                <FileSpreadsheet size={16} className="text-success flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary truncate">{f.name}</p>
                  <p className="text-xs text-text-muted">{formatSize(f.size)}</p>
                </div>
                {!uploading && (
                  <button
                    onClick={() => onRemoveFile(i)}
                    className="text-text-muted hover:text-danger transition-colors opacity-0 group-hover:opacity-100"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
