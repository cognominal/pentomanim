export type DlxRow = {
  id: number;
  columns: number[];
};

export type DlxResult = {
  rowIds: number[];
};

export type DlxTraceEvent = {
  type: 'place' | 'remove';
  rowId: number;
};

type Header = Node & { size: number; name: number };

type Node = {
  l: Node;
  r: Node;
  u: Node;
  d: Node;
  c: Header;
  rowId: number;
};

function choose(root: Header): Header | null {
  let best: Header | null = null;
  for (let c = root.r as Header; c !== root; c = c.r as Header) {
    if (best === null || c.size < best.size) {
      best = c;
    }
  }
  return best;
}

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
  return solveDlxWithTrace(columnCount, rows, maxSolutions).solutions;
}

export function solveDlxWithTrace(
  columnCount: number,
  rows: DlxRow[],
  maxSolutions = 1,
  maxTraceEvents = 20_000,
): { solutions: DlxResult[]; trace: DlxTraceEvent[] } {
  const root = {} as Header;
  root.l = root;
  root.r = root;
  root.u = root;
  root.d = root;
  root.c = root;
  root.size = 0;
  root.name = -1;
  root.rowId = -1;

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
        first = n;
        n.l = n;
        n.r = n;
      } else {
        n.l = prev as Node;
        n.r = first;
        n.l.r = n;
        n.r.l = n;
      }
      prev = n;
    }
  }

  const partial: Node[] = [];
  const out: DlxResult[] = [];
  const trace: DlxTraceEvent[] = [];

  function pushTrace(event: DlxTraceEvent): void {
    if (trace.length < maxTraceEvents) {
      trace.push(event);
    }
  }

  function search(): void {
    if (root.r === root) {
      out.push({ rowIds: partial.map((n) => n.rowId) });
      return;
    }
    if (out.length >= maxSolutions) {
      return;
    }

    const c = choose(root);
    if (!c || c.size === 0) {
      return;
    }

    cover(c);
    for (let r = c.d; r !== c; r = r.d) {
      partial.push(r);
      pushTrace({ type: 'place', rowId: r.rowId });
      for (let j = r.r; j !== r; j = j.r) {
        cover(j.c);
      }
      search();
      for (let j = r.l; j !== r; j = j.l) {
        uncover(j.c);
      }
      partial.pop();
      if (out.length >= maxSolutions) {
        break;
      }
      pushTrace({ type: 'remove', rowId: r.rowId });
    }
    uncover(c);
  }

  search();
  return { solutions: out, trace };
}
