/** Shapes returned by GET /api/file-formats (the upload layout guide). */

export type ColumnUsage = "required" | "optional" | "ignored";

export interface FileFormatColumn {
  index: number | null;
  header: string;
  group?: string;
  usage: ColumnUsage;
  note?: string;
}

export interface FileFormatSpec {
  id: string;
  label: string;
  accepted: string;
  header_rows: number;
  data_starts_row: number;
  min_columns: number | null;
  positional: boolean;
  detection: string;
  filename_example: string;
  required_indexes: number[];
  required_headers?: string[];
  columns: FileFormatColumn[];
  warnings: string[];
}

export interface FileFormatsResponse {
  types: FileFormatSpec[];
  filename_pattern: string;
  note: string;
}
