import type { ViewId } from "../api/types";

const VIEWS: { id: ViewId; label: string; short: string }[] = [
  { id: "launch", label: "Amendment Launch", short: "1 Launch" },
  { id: "redline", label: "Semantic Redline", short: "2 Redline" },
  { id: "impact", label: "Impact Graph", short: "3 Impact" },
  { id: "timeline", label: "215-Day Timeline", short: "4 Timeline" },
  { id: "findings", label: "Rehearsal Findings", short: "5 Findings" },
  { id: "actions", label: "Action Ledger", short: "6 Actions" },
  { id: "manifest", label: "Release Manifest", short: "7 Manifest" },
];

type Props = {
  active: ViewId;
  onChange: (id: ViewId) => void;
  unlocked: Set<ViewId>;
};

export function ViewNav({ active, onChange, unlocked }: Props) {
  return (
    <nav className="view-nav" aria-label="Judge views">
      {VIEWS.map((v) => {
        const enabled = unlocked.has(v.id);
        return (
          <button
            key={v.id}
            type="button"
            className="view-tab"
            data-active={active === v.id}
            disabled={!enabled}
            aria-current={active === v.id ? "page" : undefined}
            aria-label={v.label}
            title={enabled ? v.label : `${v.label} (waiting for backend)`}
            onClick={() => enabled && onChange(v.id)}
          >
            {v.short}
          </button>
        );
      })}
    </nav>
  );
}

export { VIEWS };
