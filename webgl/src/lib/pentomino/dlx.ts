export type DlxRow = {
  // Stable caller-defined identifier for this exact-cover row.
  id: number;
  // Indices of columns satisfied by this row.
  columns: number[];
};

export type DlxResult = {
  // Chosen row ids in one exact-cover solution.
  rowIds: number[];
};

export type DlxTraceEvent = {
  // "place" when recursion picks a row, "remove" when it backtracks.
  type: 'place' | 'remove';
  // The row id placed/removed at this search step.
  rowId: number;
};

// Column header node in the toroidal linked structure.
//
// `size` tracks how many active row nodes remain in this column.
// `name` is the original column index (useful for diagnostics).
type Header = Node & { size: number; name: number };

// Core Dancing Links node (Knuth's Algorithm X with DLX pointers).
//
// Each node participates in:
// - a horizontal circular list for a row (`l`/`r`)
// - a vertical circular list for a column (`u`/`d`)
// - a pointer to its owning column header (`c`)
//
// `rowId` is copied onto every node in a row so we can emit solutions and
// trace events from any node in that row.
type Node = {
  l: Node;
  r: Node;
  u: Node;
  d: Node;
  c: Header;
  rowId: number;
};

// Choose the active column with the smallest branching factor.
//
// This is the classic DLX heuristic to reduce search fan-out.
function choose(root: Header): Header | null {
  let best: Header | null = null;
  for (let c = root.r as Header; c !== root; c = c.r as Header) {
    if (best === null || c.size < best.size) {
      best = c;
    }
  }
  return best;
}

// Remove a column from the header list and remove all conflicting rows.
//
// "Cover" means:
// 1) unlink the column header from the active header ring
// 2) for each row containing this column, unlink every other node in that row
//    from its column, shrinking those column sizes
function cover(c: Header): void {
  c.r.l = c.l;
  c.l.r = c.r;
  for (let i = c.d; i !== c; i = i.d) {
    for (let j = i.r; j !== i; j = j.r) {
      j.d.u = j.u;
      j.u.d = j.d;
      j.c.size -= 1;
    }
  }
}

// Inverse of `cover`, restoring links in exact reverse traversal order.
//
// Reverse order is required so pointer rewiring precisely undoes prior cover
// operations during backtracking.
function uncover(c: Header): void {
  for (let i = c.u; i !== c; i = i.u) {
    for (let j = i.l; j !== i; j = j.l) {
      j.c.size += 1;
      j.d.u = j;
      j.u.d = j;
    }
  }
  c.r.l = c;
  c.l.r = c;
}

export function solveDlx(
  columnCount: number,
  rows: DlxRow[],
  maxSolutions = 1,
): DlxResult[] {
  // Thin wrapper used when caller does not need decision trace events.
  return solveDlxWithTrace(columnCount, rows, maxSolutions).solutions;
}

export function solveDlxWithTrace(
  columnCount: number,
  rows: DlxRow[],
  maxSolutions = 1,
  maxTraceEvents = 20_000,
): { solutions: DlxResult[]; trace: DlxTraceEvent[] } {
  // Sentinel root for the circular list of active column headers.
  //
  // The root acts as both list anchor and termination marker while iterating.
  const root = {} as Header;
  root.l = root;
  root.r = root;
  root.u = root;
  root.d = root;
  root.c = root;
  root.size = 0;
  root.name = -1;
  root.rowId = -1;

  // Create one header node per exact-cover column and link all headers into
  // root's horizontal circular list.
  const cols: Header[] = [];
  for (let i = 0; i < columnCount; i += 1) {
    const h = {} as Header;
    h.l = root.l;
    h.r = root;
    h.l.r = h;
    h.r.l = h;
    h.u = h;
    h.d = h;
    h.c = h;
    h.size = 0;
    h.name = i;
    h.rowId = -1;
    cols.push(h);
  }

  // Materialize sparse rows as linked nodes:
  // - vertically inserted into each target column
  // - horizontally linked into that row's circular ring
  for (const row of rows) {
    let first: Node | null = null;
    let prev: Node | null = null;
    for (const idx of row.columns) {
      const c = cols[idx];
      const n = {} as Node;
      n.c = c;
      n.rowId = row.id;

      n.u = c.u;
      n.d = c;
      n.u.d = n;
      n.d.u = n;
      c.size += 1;

      if (first === null) {
        // First node starts a 1-node circular row ring.
        first = n;
        n.l = n;
        n.r = n;
      } else {
        // Append to row ring, keeping it circular through `first`.
        n.l = prev as Node;
        n.r = first;
        n.l.r = n;
        n.r.l = n;
      }
      prev = n;
    }
  }

  // Current partial solution as concrete row nodes.
  const partial: Node[] = [];
  // Accumulated exact-cover solutions.
  const out: DlxResult[] = [];
  // Optional bounded trace of place/remove decisions for visualization/debug.
  const trace: DlxTraceEvent[] = [];

  function pushTrace(event: DlxTraceEvent): void {
    // Keep trace memory bounded for large/unsat searches.
    if (trace.length < maxTraceEvents) {
      trace.push(event);
    }
  }

  function search(): void {
    // No columns left => all constraints satisfied by current partial rows.
    if (root.r === root) {
      out.push({ rowIds: partial.map((n) => n.rowId) });
      return;
    }
    // Early-stop once requested number of solutions is reached.
    if (out.length >= maxSolutions) {
      return;
    }

    const c = choose(root);
    // No viable column, or a required column with zero candidates.
    // Both cases are dead ends.
    if (!c || c.size === 0) {
      return;
    }

    // Branch on each row that can satisfy chosen column `c`.
    cover(c);
    for (let r = c.d; r !== c; r = r.d) {
      // Commit this row into the partial solution.
      partial.push(r);
      pushTrace({ type: 'place', rowId: r.rowId });
      // Cover all other columns touched by this row to enforce exclusivity.
      for (let j = r.r; j !== r; j = j.r) {
        cover(j.c);
      }

      // Recurse with tighter constraint set.
      search();

      // Undo row-implied covers before trying sibling rows.
      for (let j = r.l; j !== r; j = j.l) {
        uncover(j.c);
      }
      partial.pop();
      if (out.length >= maxSolutions) {
        break;
      }
      pushTrace({ type: 'remove', rowId: r.rowId });
    }
    // Restore chosen column before returning to caller.
    uncover(c);
  }

  search();
  return { solutions: out, trace };
}
