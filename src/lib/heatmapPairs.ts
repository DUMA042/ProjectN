/** Curated heatmap dimension pairings — nonsense pairs are impossible by
 * construction: employee dimensions can only be rows and only pair with time
 * buckets; attribute rows pair with time buckets or other attributes. */

export const TIME_DIMS = ["day", "week", "month", "quarter"];

const EMPLOYEE_DIMS = ["employee", "employee_id"];

export interface DimOpt {
  key: string;
  label: string;
}

export function buildHeatOptions(all: DimOpt[]) {
  const attrs = all.filter((d) => !TIME_DIMS.includes(d.key) && !EMPLOYEE_DIMS.includes(d.key));
  const employeeDims = all.filter((d) => EMPLOYEE_DIMS.includes(d.key));
  const timeDims = all.filter((d) => TIME_DIMS.includes(d.key));

  return {
    /** Row dimension choices: attributes + employee dims (rows only). */
    rowOptions: [...attrs, ...employeeDims],
    /** Column choices for a given row dimension. */
    colOptionsFor(rowDim: string): DimOpt[] {
      if (EMPLOYEE_DIMS.includes(rowDim)) return timeDims;
      return [...timeDims, ...attrs];
    },
    /** Validate a row change; returns the adjusted (row, col) pair. */
    guardRow(next: string, colDim: string): { row: string; col: string } {
      if (EMPLOYEE_DIMS.includes(next)) {
        return { row: next, col: TIME_DIMS.includes(colDim) ? colDim : "month" };
      }
      return { row: next, col: colDim };
    },
    /** Validate a column change; null = rejected. */
    guardCol(next: string, rowDim: string): string | null {
      if (EMPLOYEE_DIMS.includes(next)) return null;
      if (EMPLOYEE_DIMS.includes(rowDim) && !TIME_DIMS.includes(next)) return null;
      return next;
    },
  };
}
