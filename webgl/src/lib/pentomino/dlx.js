function choose(root) {
    let best = null;
    for (let c = root.r; c !== root; c = c.r) {
        if (best === null || c.size < best.size) {
            best = c;
        }
    }
    return best;
}
function cover(c) {
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
function uncover(c) {
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
export function solveDlx(columnCount, rows, maxSolutions = 1) {
    return solveDlxWithTrace(columnCount, rows, maxSolutions).solutions;
}
export function solveDlxWithTrace(columnCount, rows, maxSolutions = 1, maxTraceEvents = 20000) {
    const root = {};
    root.l = root;
    root.r = root;
    root.u = root;
    root.d = root;
    root.c = root;
    root.size = 0;
    root.name = -1;
    root.rowId = -1;
    const cols = [];
    for (let i = 0; i < columnCount; i += 1) {
        const h = {};
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
        let first = null;
        let prev = null;
        for (const idx of row.columns) {
            const c = cols[idx];
            const n = {};
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
            }
            else {
                n.l = prev;
                n.r = first;
                n.l.r = n;
                n.r.l = n;
            }
            prev = n;
        }
    }
    const partial = [];
    const out = [];
    const trace = [];
    function pushTrace(event) {
        if (trace.length < maxTraceEvents) {
            trace.push(event);
        }
    }
    function search() {
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
//# sourceMappingURL=dlx.js.map