// The glass box: the headline decomposed to every matched pair, on a TanStack
// Table v8 engine under the app's own markup, with the rendered window
// virtualized (@tanstack/react-virtual). Faceted BATCH filters (Apply model, no
// per-keystroke re-run, no scroll-to-top), removable filter chips, pagination
// (persisted page size), a comfortable/compact density toggle, value-suppressed
// styling on shaky figures, a persistent "Showing $Y of $X · N of M" line, and
// Saved Views. Clicking a row opens the trace drawer with prev/next over the
// current sorted+filtered set.

import { useEffect, useMemo, useRef, useState } from "react";
import {
  type ColumnDef,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import * as Popover from "@radix-ui/react-popover";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import type { Confidence, Estimate, MatchedPair } from "../types";
import { int, money0, money2, moneyAbbrev, moneyCoarse, provisionShort } from "../format";
import { useStored } from "../storage";
import { pairId } from "../pair";
import { ConfidenceBadge, MoneyTip, Tip } from "./ui";
import TraceDrawer from "./TraceDrawer";

interface Props {
  est: Estimate;
}

interface Filters {
  years: number[];
  hts: string[];
  programs: string[];
  confidence: Confidence[];
  headlineOnly: boolean;
}
const EMPTY_FILTERS: Filters = {
  years: [],
  hts: [],
  programs: [],
  confidence: [],
  headlineOnly: false,
};

interface SavedView {
  name: string;
  filters: Filters;
  sorting: SortingState;
  density: Density;
  pageSize: number;
}
type Density = "comfortable" | "compact";
const PAGE_SIZES = [25, 50, 100];

export default function GlassBox({ est }: Props) {
  const pairs = est.matched_pairs;

  // ── view state ────────────────────────────────────────────────────────────
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [sorting, setSorting] = useState<SortingState>([{ id: "recovery", desc: true }]);
  const [density, setDensity] = useStored<Density>("drawback-density", "comfortable");
  const [pageSize, setPageSize] = useStored<number>("drawback-pagesize", 50);
  const [pageIndex, setPageIndex] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [views, setViews] = useStored<SavedView[]>("drawback-views", []);

  // facet option lists (with counts) computed once per dataset
  const facets = useMemo(() => buildFacets(pairs), [pairs]);

  // ── filtering (batch — only recomputes when `filters` changes) ────────────
  const filtered = useMemo(() => applyFilters(pairs, filters), [pairs, filters]);

  // headline total (X) is fixed; filtered recovery (Y) reconciles against it
  const filteredRecovery = useMemo(
    () => filtered.reduce((a, p) => a + p.recovery, 0),
    [filtered],
  );
  const headlineTotal = est.headline_point;

  const columns = useMemo<ColumnDef<MatchedPair>[]>(() => makeColumns(), []);

  const table = useReactTable({
    data: filtered,
    columns,
    state: { sorting },
    onSortingChange: (u) => {
      setSorting(u);
      setPageIndex(0); // re-sort resets to first page, but never scrolls table
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const sortedRows = table.getRowModel().rows;
  const pageCount = Math.max(1, Math.ceil(sortedRows.length / pageSize));
  const clampedPage = Math.min(pageIndex, pageCount - 1);
  const pageRows = sortedRows.slice(clampedPage * pageSize, clampedPage * pageSize + pageSize);

  // ordered list of pairs on the current page (for drawer prev/next)
  const pageOrder = useMemo(() => pageRows.map((r) => r.original), [pageRows]);
  const selectedIdx = selectedId ? pageOrder.findIndex((p) => pairId(p) === selectedId) : -1;
  const selectedPair = selectedIdx >= 0 ? pageOrder[selectedIdx] : null;

  // ── virtualization of the page's rows ─────────────────────────────────────
  const scrollRef = useRef<HTMLDivElement>(null);
  const rowH = density === "compact" ? 31 : 39;
  const virtualizer = useVirtualizer({
    count: pageRows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => rowH,
    overscan: 12,
  });
  const vItems = virtualizer.getVirtualItems();
  const padTop = vItems.length ? vItems[0].start : 0;
  const padBottom = vItems.length
    ? virtualizer.getTotalSize() - vItems[vItems.length - 1].end
    : 0;

  // density change resizes every row → re-measure the virtual window
  useEffect(() => {
    virtualizer.measure();
  }, [rowH, virtualizer]);

  // turning the page should show the new page from the top (paging, not
  // filtering — filters keep position per the research's "don't scroll-to-top")
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [clampedPage]);

  // ── filter helpers ────────────────────────────────────────────────────────
  function applyAndReset(next: Filters) {
    setFilters(next);
    setPageIndex(0); // new filter → page 1, but the table body does NOT scroll
  }
  const activeChips = describeFilters(filters, applyAndReset);
  const headerCount = countActive(filters);

  function applyView(v: SavedView) {
    setFilters(v.filters);
    setSorting(v.sorting);
    setDensity(v.density);
    setPageSize(v.pageSize);
    setPageIndex(0);
  }
  function saveView(name: string) {
    const v: SavedView = { name, filters, sorting, density, pageSize };
    setViews((prev) => [...prev.filter((x) => x.name !== name), v]);
  }

  return (
    <div className="grid" style={{ gap: 18 }}>
      <Reconciliation est={est} />

      <section className="panel flush">
        {/* toolbar */}
        <div className="tabletools">
          <FilterMenu facets={facets} value={filters} onApply={applyAndReset} count={headerCount} />

          <DensityMenu density={density} setDensity={setDensity} />

          <SavedViewsMenu
            views={views}
            onApply={applyView}
            onSave={saveView}
            onDelete={(name) => setViews((prev) => prev.filter((x) => x.name !== name))}
          />

          <div className="toolspacer" />
          <PageSizeMenu pageSize={pageSize} setPageSize={(n) => { setPageSize(n); setPageIndex(0); }} />
        </div>

        {/* active filter chips */}
        {activeChips.length > 0 && (
          <div className="filterchips">
            <span className="lab">Filters</span>
            {activeChips.map((c) => (
              <span className="fchip" key={c.key}>
                {c.label}
                <button onClick={c.remove} aria-label={`Remove filter ${c.label}`}>
                  ×
                </button>
              </span>
            ))}
            <button className="fchip clearall" onClick={() => applyAndReset(EMPTY_FILTERS)}>
              Clear all
            </button>
          </div>
        )}

        {/* table */}
        <div className="grid-scroll" ref={scrollRef}>
          <table className={`pairs tg ${density === "compact" ? "compact" : ""}`}>
            <colgroup>
              <col style={{ width: "15%" }} />
              <col style={{ width: "10%" }} />
              <col style={{ width: "9%" }} />
              <col style={{ width: "7%" }} />
              <col style={{ width: "12%" }} />
              <col style={{ width: "10%" }} />
              <col style={{ width: "10%" }} />
              <col style={{ width: "11%" }} />
              <col style={{ width: "9%" }} />
              <col style={{ width: "10%" }} />
              <col style={{ width: "8%" }} />
            </colgroup>
            <thead>
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((h) => {
                    const canSort = h.column.getCanSort();
                    const dir = h.column.getIsSorted();
                    const meta = h.column.columnDef.meta as ColMeta | undefined;
                    return (
                      <th
                        key={h.id}
                        className={`${meta?.num ? "num" : ""} ${canSort ? "sortable" : ""}`}
                        onClick={canSort ? h.column.getToggleSortingHandler() : undefined}
                        aria-sort={
                          dir === "asc" ? "ascending" : dir === "desc" ? "descending" : "none"
                        }
                        scope="col"
                      >
                        {flexRender(h.column.columnDef.header, h.getContext())}
                        {canSort && dir && <span className="ar">{dir === "asc" ? "▲" : "▼"}</span>}
                        {meta?.unit && <span className="unit">{meta.unit}</span>}
                      </th>
                    );
                  })}
                </tr>
              ))}
            </thead>
            <tbody>
              {padTop > 0 && (
                <tr aria-hidden style={{ height: padTop }}>
                  <td colSpan={columns.length} style={{ padding: 0, border: 0 }} />
                </tr>
              )}
              {vItems.map((vi) => {
                const row = pageRows[vi.index];
                const p = row.original;
                const id = pairId(p);
                const suppressed = !p.in_headline || p.confidence === "low";
                return (
                  <tr
                    key={id}
                    style={{ height: rowH }}
                    className={`${selectedId === id ? "active" : ""} ${suppressed ? "suppressed" : ""}`}
                    onClick={() => setSelectedId(id)}
                    tabIndex={0}
                    role="button"
                    aria-label={`Open trace for ${p.import_entry} line ${p.import_line_no}`}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setSelectedId(id);
                      }
                    }}
                    title="Open trace"
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td
                        key={cell.id}
                        className={cellClass(cell.column.columnDef.meta as ColMeta | undefined)}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                );
              })}
              {padBottom > 0 && (
                <tr aria-hidden style={{ height: padBottom }}>
                  <td colSpan={columns.length} style={{ padding: 0, border: 0 }} />
                </tr>
              )}
              {!pageRows.length && (
                <tr>
                  <td colSpan={columns.length}>
                    <div className="empty">No pairs match these filters.</div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* reconciliation line — filtered subset vs headline total */}
        <div className="reconline">
          <span className="big">
            Showing <MoneyTip value={filteredRecovery} abbrev={moneyAbbrev(filteredRecovery)} />{" "}
            <span className="of">
              of <MoneyTip value={headlineTotal} abbrev={moneyAbbrev(headlineTotal)} /> recovery
            </span>
          </span>
          <span className="of mono" style={{ fontSize: 12 }}>
            · {int(filtered.length)} of {int(pairs.length)} pairs
            {countActive(filters) > 0 ? " (filtered)" : ""}
          </span>
        </div>

        {/* pagination */}
        <Pager
          page={clampedPage}
          pageCount={pageCount}
          total={sortedRows.length}
          pageSize={pageSize}
          onPage={setPageIndex}
        />
      </section>

      <p className="muted" style={{ fontSize: 12.5, margin: 0 }}>
        Click any row to open its full explainable trace — rule citations (live links), the numbered
        derivation, charge breakdown, window dates and evidence manifest. Low-confidence and
        not-in-headline rows are shown muted with a coarser figure so the number isn’t over-read.
      </p>

      {selectedPair && (
        <TraceDrawer
          pair={selectedPair}
          onClose={() => setSelectedId(null)}
          onPrev={() => setSelectedId(pairId(pageOrder[selectedIdx - 1]))}
          onNext={() => setSelectedId(pairId(pageOrder[selectedIdx + 1]))}
          hasPrev={selectedIdx > 0}
          hasNext={selectedIdx >= 0 && selectedIdx < pageOrder.length - 1}
        />
      )}
    </div>
  );
}

// ── columns ───────────────────────────────────────────────────────────────
interface ColMeta {
  num?: boolean;
  unit?: string;
  mono?: boolean;
}
function cellClass(meta?: ColMeta): string {
  const c: string[] = [];
  if (meta?.num) c.push("num");
  if (meta?.mono) c.push("mono");
  return c.join(" ");
}

function makeColumns(): ColumnDef<MatchedPair>[] {
  return [
    {
      id: "import",
      header: "Import entry / line",
      accessorFn: (p) => `${p.import_entry}/${p.import_line_no}`,
      enableSorting: true,
      meta: { mono: true },
      cell: (c) => {
        const p = c.row.original;
        return (
          <>
            {p.import_entry}
            <span className="faint"> /{p.import_line_no}</span>
          </>
        );
      },
    },
    {
      id: "export",
      header: "Export ref",
      accessorFn: (p) => p.export_reference,
      meta: { mono: true },
      cell: (c) => c.row.original.export_reference,
    },
    {
      id: "hts8",
      header: "HTS8",
      accessorFn: (p) => p.hts8,
      meta: { mono: true },
      cell: (c) => c.row.original.hts8,
    },
    {
      id: "quantity",
      header: "Qty",
      accessorFn: (p) => p.quantity,
      meta: { num: true, unit: "units" },
      cell: (c) => int(c.row.original.quantity),
    },
    {
      id: "provision",
      header: "Provision",
      accessorFn: (p) => p.provision,
      enableSorting: false,
      meta: { mono: true },
      cell: (c) => (
        <span style={{ color: "var(--ink-2)" }}>{provisionShort(c.row.original.provision)}</span>
      ),
    },
    {
      id: "desig",
      header: "Desig. duty",
      accessorFn: (p) => p.per_unit_designated_duty,
      meta: { num: true, unit: "$/unit" },
      cell: (c) => money2(c.row.original.per_unit_designated_duty),
    },
    {
      id: "comparator",
      header: "Comparator",
      accessorFn: (p) => p.per_unit_comparator_duty ?? -1,
      meta: { num: true, unit: "$/unit" },
      cell: (c) => {
        const v = c.row.original.per_unit_comparator_duty;
        return v == null ? <span className="faint">—</span> : money2(v);
      },
    },
    {
      id: "recovery",
      header: "Recovery",
      accessorFn: (p) => p.recovery,
      meta: { num: true, unit: "$" },
      cell: (c) => {
        const p = c.row.original;
        const suppressed = !p.in_headline || p.confidence === "low";
        // full precision for firm headline rows; coarse for shaky ones
        return suppressed ? (
          <span className="coarse">{moneyCoarse(p.recovery)}</span>
        ) : (
          <span className="pos">{money2(p.recovery)}</span>
        );
      },
    },
    {
      id: "recovery_low",
      header: "Range low",
      accessorFn: (p) => p.recovery_low,
      meta: { num: true, unit: "$" },
      cell: (c) => <span className="faint">{money2(c.row.original.recovery_low)}</span>,
    },
    {
      id: "confidence",
      header: "Confidence",
      accessorFn: (p) => ({ high: 3, medium: 2, low: 1 })[p.confidence],
      cell: (c) => <ConfidenceBadge c={c.row.original.confidence} />,
    },
    {
      id: "in_headline",
      header: "In headline",
      accessorFn: (p) => (p.in_headline ? 1 : 0),
      cell: (c) =>
        c.row.original.in_headline ? (
          <span className="dotcheck" role="img" aria-label="In headline">
            ✓
          </span>
        ) : (
          <span className="dotno" role="img" aria-label="Not in headline">
            —
          </span>
        ),
    },
  ];
}

// ── facets + filtering ──────────────────────────────────────────────────────
interface Facets {
  years: Array<{ value: number; count: number }>;
  hts: Array<{ value: string; count: number }>;
  programs: Array<{ value: string; count: number }>;
  confidence: Array<{ value: Confidence; count: number }>;
}
function buildFacets(pairs: MatchedPair[]): Facets {
  const yr = new Map<number, number>();
  const ht = new Map<string, number>();
  const pr = new Map<string, number>();
  const cf = new Map<Confidence, number>();
  for (const p of pairs) {
    yr.set(p.import_year, (yr.get(p.import_year) ?? 0) + 1);
    ht.set(p.hts8, (ht.get(p.hts8) ?? 0) + 1);
    pr.set(p.provision, (pr.get(p.provision) ?? 0) + 1);
    cf.set(p.confidence, (cf.get(p.confidence) ?? 0) + 1);
  }
  const order: Confidence[] = ["high", "medium", "low"];
  return {
    years: [...yr.entries()].sort((a, b) => b[0] - a[0]).map(([value, count]) => ({ value, count })),
    hts: [...ht.entries()].sort().map(([value, count]) => ({ value, count })),
    programs: [...pr.entries()].sort().map(([value, count]) => ({ value, count })),
    confidence: order
      .filter((c) => cf.has(c))
      .map((value) => ({ value, count: cf.get(value) ?? 0 })),
  };
}

function applyFilters(pairs: MatchedPair[], f: Filters): MatchedPair[] {
  return pairs.filter((p) => {
    if (f.years.length && !f.years.includes(p.import_year)) return false;
    if (f.hts.length && !f.hts.includes(p.hts8)) return false;
    if (f.programs.length && !f.programs.includes(p.provision)) return false;
    if (f.confidence.length && !f.confidence.includes(p.confidence)) return false;
    if (f.headlineOnly && !p.in_headline) return false;
    return true;
  });
}

function countActive(f: Filters): number {
  return (
    f.years.length +
    f.hts.length +
    f.programs.length +
    f.confidence.length +
    (f.headlineOnly ? 1 : 0)
  );
}

/** Build removable chip descriptors from the applied filters. `apply` lets each
 *  chip's × button re-apply a copy of the filters with that facet value removed. */
function describeFilters(
  f: Filters,
  apply: (next: Filters) => void,
): Array<{ key: string; label: string; remove: () => void }> {
  const chips: Array<{ key: string; label: string; remove: () => void }> = [];
  for (const y of f.years)
    chips.push({
      key: `y${y}`,
      label: `Year ${y}`,
      remove: () => apply({ ...f, years: f.years.filter((x) => x !== y) }),
    });
  for (const h of f.hts)
    chips.push({
      key: `h${h}`,
      label: `HTS ${h}`,
      remove: () => apply({ ...f, hts: f.hts.filter((x) => x !== h) }),
    });
  for (const p of f.programs)
    chips.push({
      key: `p${p}`,
      label: provisionShort(p),
      remove: () => apply({ ...f, programs: f.programs.filter((x) => x !== p) }),
    });
  for (const c of f.confidence)
    chips.push({
      key: `c${c}`,
      label: `${c} conf.`,
      remove: () => apply({ ...f, confidence: f.confidence.filter((x) => x !== c) }),
    });
  if (f.headlineOnly)
    chips.push({
      key: "headline",
      label: "In-headline only",
      remove: () => apply({ ...f, headlineOnly: false }),
    });
  return chips;
}

// ── toolbar widgets ─────────────────────────────────────────────────────────
function FilterMenu({
  facets,
  value,
  onApply,
  count,
}: {
  facets: Facets;
  value: Filters;
  onApply: (f: Filters) => void;
  count: number;
}) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Filters>(value);

  // when opening, seed the draft from the applied filters
  function onOpenChange(o: boolean) {
    if (o) setDraft(value);
    setOpen(o);
  }

  function toggle<T>(list: T[], v: T): T[] {
    return list.includes(v) ? list.filter((x) => x !== v) : [...list, v];
  }

  return (
    <Popover.Root open={open} onOpenChange={onOpenChange}>
      <Popover.Trigger asChild>
        <button className="btn ghost sm" aria-label="Filter pairs">
          <FilterIcon />
          Filter{count ? ` · ${count}` : ""}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content className="menu" align="start" sideOffset={6} style={{ minWidth: 280 }}>
          <div className="menu-h">Confidence</div>
          <div className="facet">
            {facets.confidence.map((o) => (
              <label key={o.value}>
                <input
                  type="checkbox"
                  checked={draft.confidence.includes(o.value)}
                  onChange={() => setDraft({ ...draft, confidence: toggle(draft.confidence, o.value) })}
                />
                <span style={{ textTransform: "capitalize" }}>{o.value}</span>
                <span className="cnt">{o.count}</span>
              </label>
            ))}
          </div>

          <div className="menu-h">Import year</div>
          <div className="facet">
            {facets.years.map((o) => (
              <label key={o.value}>
                <input
                  type="checkbox"
                  checked={draft.years.includes(o.value)}
                  onChange={() => setDraft({ ...draft, years: toggle(draft.years, o.value) })}
                />
                <span>{o.value}</span>
                <span className="cnt">{o.count}</span>
              </label>
            ))}
          </div>

          <div className="menu-h">Program</div>
          <div className="facet">
            {facets.programs.map((o) => (
              <label key={o.value}>
                <input
                  type="checkbox"
                  checked={draft.programs.includes(o.value)}
                  onChange={() => setDraft({ ...draft, programs: toggle(draft.programs, o.value) })}
                />
                <span>{provisionShort(o.value)}</span>
                <span className="cnt">{o.count}</span>
              </label>
            ))}
          </div>

          <div className="menu-h">HTS8</div>
          <div className="facet">
            {facets.hts.map((o) => (
              <label key={o.value}>
                <input
                  type="checkbox"
                  checked={draft.hts.includes(o.value)}
                  onChange={() => setDraft({ ...draft, hts: toggle(draft.hts, o.value) })}
                />
                <span className="mono">{o.value}</span>
                <span className="cnt">{o.count}</span>
              </label>
            ))}
          </div>

          <div className="menu-sep" />
          <label className="facet" style={{ padding: "0 8px" }}>
            <span style={{ display: "flex", alignItems: "center", gap: 9, padding: "6px 0" }}>
              <input
                type="checkbox"
                checked={draft.headlineOnly}
                onChange={(e) => setDraft({ ...draft, headlineOnly: e.target.checked })}
              />
              In-headline only
            </span>
          </label>

          <div className="menu-actions">
            <button
              className="btn ghost sm"
              onClick={() => setDraft(EMPTY_FILTERS)}
            >
              Reset
            </button>
            <button
              className="btn primary sm"
              style={{ marginLeft: "auto" }}
              onClick={() => {
                onApply(draft);
                setOpen(false);
              }}
            >
              Apply
            </button>
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

function DensityMenu({
  density,
  setDensity,
}: {
  density: Density;
  setDensity: (d: Density) => void;
}) {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button className="btn ghost sm" aria-label="Row density">
          <RowsIcon />
          {density === "compact" ? "Compact" : "Comfortable"}
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className="menu" align="start" sideOffset={6}>
          <DropdownMenu.Item className="menu-item" onSelect={() => setDensity("comfortable")}>
            <span className="ck">{density === "comfortable" ? "✓" : ""}</span> Comfortable
          </DropdownMenu.Item>
          <DropdownMenu.Item className="menu-item" onSelect={() => setDensity("compact")}>
            <span className="ck">{density === "compact" ? "✓" : ""}</span> Compact
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

function PageSizeMenu({
  pageSize,
  setPageSize,
}: {
  pageSize: number;
  setPageSize: (n: number) => void;
}) {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button className="btn ghost sm" aria-label="Rows per page">
          {pageSize} / page
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className="menu" align="end" sideOffset={6}>
          {PAGE_SIZES.map((n) => (
            <DropdownMenu.Item key={n} className="menu-item" onSelect={() => setPageSize(n)}>
              <span className="ck">{pageSize === n ? "✓" : ""}</span> {n} per page
            </DropdownMenu.Item>
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

function SavedViewsMenu({
  views,
  onApply,
  onSave,
  onDelete,
}: {
  views: SavedView[];
  onApply: (v: SavedView) => void;
  onSave: (name: string) => void;
  onDelete: (name: string) => void;
}) {
  const [name, setName] = useState("");
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button className="btn ghost sm" aria-label="Saved views">
          <BookmarkIcon />
          Views{views.length ? ` · ${views.length}` : ""}
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className="menu" align="start" sideOffset={6}>
          <div className="menu-h">Saved views</div>
          {views.length === 0 && (
            <div className="muted" style={{ padding: "4px 9px", fontSize: 12 }}>
              No saved views yet.
            </div>
          )}
          {views.map((v) => (
            <DropdownMenu.Item
              key={v.name}
              className="menu-item"
              onSelect={(e) => {
                e.preventDefault();
                onApply(v);
              }}
            >
              {v.name}
              <span
                className="del"
                role="button"
                aria-label={`Delete view ${v.name}`}
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(v.name);
                }}
              >
                ×
              </span>
            </DropdownMenu.Item>
          ))}
          <div className="menu-sep" />
          <div className="menu-field" onKeyDown={(e) => e.stopPropagation()}>
            <span className="fl">Save current view</span>
            <input
              className="input"
              placeholder="View name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <button
              className="btn primary sm"
              disabled={!name.trim()}
              onClick={() => {
                onSave(name.trim());
                setName("");
              }}
            >
              Save
            </button>
          </div>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

function Pager({
  page,
  pageCount,
  total,
  pageSize,
  onPage,
}: {
  page: number;
  pageCount: number;
  total: number;
  pageSize: number;
  onPage: (p: number) => void;
}) {
  if (total === 0) return null;
  const from = page * pageSize + 1;
  const to = Math.min(total, (page + 1) * pageSize);
  const nums = pageWindow(page, pageCount);
  return (
    <div className="pager">
      <span className="pginfo">
        {int(from)}–{int(to)} of {int(total)}
      </span>
      <div className="pgbtns">
        <button className="pgbtn" disabled={page === 0} onClick={() => onPage(page - 1)} aria-label="Previous page">
          ‹
        </button>
        {nums.map((n, i) =>
          n === -1 ? (
            <span key={`gap${i}`} className="pginfo" style={{ padding: "0 4px" }}>
              …
            </span>
          ) : (
            <button
              key={n}
              className={`pgbtn ${n === page ? "cur" : ""}`}
              onClick={() => onPage(n)}
              aria-label={`Page ${n + 1}`}
              aria-current={n === page ? "page" : undefined}
            >
              {n + 1}
            </button>
          ),
        )}
        <button
          className="pgbtn"
          disabled={page >= pageCount - 1}
          onClick={() => onPage(page + 1)}
          aria-label="Next page"
        >
          ›
        </button>
      </div>
    </div>
  );
}

function pageWindow(page: number, count: number): number[] {
  if (count <= 7) return Array.from({ length: count }, (_, i) => i);
  const out: number[] = [0];
  const lo = Math.max(1, page - 1);
  const hi = Math.min(count - 2, page + 1);
  if (lo > 1) out.push(-1);
  for (let i = lo; i <= hi; i++) out.push(i);
  if (hi < count - 2) out.push(-1);
  out.push(count - 1);
  return out;
}

function Reconciliation({ est }: { est: Estimate }) {
  const head = est.headline_point;
  const byProg = est.by_program.reduce((a, b) => a + b.recovery, 0);
  const byYear = est.by_year.reduce((a, b) => a + b.recovery, 0);
  const byPairs = est.matched_pairs
    .filter((p) => p.in_headline)
    .reduce((a, p) => a + p.recovery, 0);

  const eq = (a: number, b: number) => Math.abs(a - b) < 0.5;
  const ok = eq(head, byProg) && eq(head, byYear) && eq(head, byPairs);

  return (
    <div className="row wrap" style={{ gap: 12 }}>
      <span className={`recon ${ok ? "" : "bad"}`}>
        <span className="ck">{ok ? "✓" : "≠"}</span>
        Headline = Σ by-program = Σ by-year = Σ headline pairs {ok ? "" : "(mismatch)"}
      </span>
      <Tip label={`${money2(head)} = ${money2(byProg)} = ${money2(byYear)} = ${money2(byPairs)}`}>
        <span className="mono muted" style={{ fontSize: 12 }}>
          {money0(head)} reconciles four ways
        </span>
      </Tip>
    </div>
  );
}

/* icons */
function FilterIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
      <path d="M3 5h18l-7 8v6l-4-2v-4z" />
    </svg>
  );
}
function RowsIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden>
      <rect x="3" y="4" width="18" height="5" rx="1" />
      <rect x="3" y="13" width="18" height="5" rx="1" />
    </svg>
  );
}
function BookmarkIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden>
      <path d="M6 3h12v18l-6-4-6 4z" />
    </svg>
  );
}
