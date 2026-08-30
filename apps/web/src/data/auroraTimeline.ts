/** Synthetic AURORA-101 215-day rollout geometry for the Timeline view. */

export type TimelineEventKind =
  | "global_release"
  | "local_approval"
  | "training"
  | "activation"
  | "visit"
  | "protocol_version"
  | "blocked";

/** Visual lane inside each site track (version band sits below process). */
export type TimelineLane = "process" | "version" | "visit" | "block";

export type TimelineEvent = {
  id: string;
  kind: TimelineEventKind;
  lane: TimelineLane;
  label: string;
  dayStart: number;
  dayEnd: number;
  detail?: string;
};

export type SiteTimeline = {
  siteId: string;
  city: string;
  name: string;
  /** Day the site flips from v1.0 → v2.0 (signature stagger). */
  v2ActivationDay: number;
  events: TimelineEvent[];
};

/** Day 0 = global amendment release; axis spans 215 days (study fragmentation window). */
export const ROLLOUT_DAYS = 215;

/**
 * Staggered site readiness for the demo narration:
 *   Phoenix → Day 30   (fast: approved + trained, then P002 courier block)
 *   Boston  → Day 95   (approved earlier; training lags)
 *   Seattle → Day 180  (approval + training both late)
 *
 * Protocol version bands switch at those days so a vertical slice of the chart
 * shows sites on different versions — the meaning of “215”.
 */
export const AURORA_TIMELINES: SiteTimeline[] = [
  {
    siteId: "SITE-001",
    city: "Phoenix",
    name: "Phoenix Synthetic Research Clinic",
    v2ActivationDay: 30,
    events: [
      {
        id: "phx-rel",
        kind: "global_release",
        lane: "process",
        label: "Release",
        dayStart: 0,
        dayEnd: 3,
        detail: "Global v2.0 amendment released to all sites.",
      },
      {
        id: "phx-appr",
        kind: "local_approval",
        lane: "process",
        label: "Approval",
        dayStart: 4,
        dayEnd: 14,
        detail: "Local ethics / IRB approval complete.",
      },
      {
        id: "phx-train",
        kind: "training",
        lane: "process",
        label: "Training",
        dayStart: 14,
        dayEnd: 28,
        detail: "Site staff amendment training complete.",
      },
      {
        id: "phx-act",
        kind: "activation",
        lane: "process",
        label: "Activation",
        dayStart: 30,
        dayEnd: 38,
        detail: "Site attempts v2.0 activation (~Day 30).",
      },
      {
        id: "phx-v1",
        kind: "protocol_version",
        lane: "version",
        label: "v1.0",
        dayStart: 0,
        dayEnd: 30,
        detail: "Operating under protocol v1.0 until Day 30.",
      },
      {
        id: "phx-v2",
        kind: "protocol_version",
        lane: "version",
        label: "v2.0",
        dayStart: 30,
        dayEnd: 215,
        detail: "Switches to v2.0 at Day 30 — earliest of the three sites.",
      },
      {
        id: "phx-p002",
        kind: "visit",
        lane: "visit",
        label: "P002 Day 1",
        dayStart: 40,
        dayEnd: 42,
        detail: "Dose 12:00 · PK 6h sample due 18:00.",
      },
      {
        id: "phx-block",
        kind: "blocked",
        lane: "block",
        label: "P002 courier / storage",
        dayStart: 40,
        dayEnd: 90,
        detail:
          "6h PK sample at 18:00 vs courier 17:30 and no overnight storage — activation blocked for this participant.",
      },
    ],
  },
  {
    siteId: "SITE-002",
    city: "Boston",
    name: "Boston Synthetic Clinical Unit",
    v2ActivationDay: 95,
    events: [
      {
        id: "bos-rel",
        kind: "global_release",
        lane: "process",
        label: "Release",
        dayStart: 0,
        dayEnd: 3,
        detail: "Same global v2.0 release day as Phoenix and Seattle.",
      },
      {
        id: "bos-appr",
        kind: "local_approval",
        lane: "process",
        label: "Approval",
        dayStart: 20,
        dayEnd: 48,
        detail: "Local approval completes mid-window — training still open.",
      },
      {
        id: "bos-train",
        kind: "training",
        lane: "process",
        label: "Training",
        dayStart: 48,
        dayEnd: 95,
        detail: "Training lags after approval; site cannot activate until complete.",
      },
      {
        id: "bos-act",
        kind: "activation",
        lane: "process",
        label: "Activation",
        dayStart: 95,
        dayEnd: 105,
        detail: "v2.0 activation around Day 95 once training closes.",
      },
      {
        id: "bos-v1",
        kind: "protocol_version",
        lane: "version",
        label: "v1.0",
        dayStart: 0,
        dayEnd: 95,
        detail: "Still on v1.0 while Phoenix has already moved to v2.0.",
      },
      {
        id: "bos-v2",
        kind: "protocol_version",
        lane: "version",
        label: "v2.0",
        dayStart: 95,
        dayEnd: 215,
        detail: "Flips to v2.0 at Day 95.",
      },
      {
        id: "bos-block",
        kind: "blocked",
        lane: "block",
        label: "Waiting on training",
        dayStart: 48,
        dayEnd: 95,
        detail: "Approved but not trained — activation gated until Day 95.",
      },
    ],
  },
  {
    siteId: "SITE-003",
    city: "Seattle",
    name: "Seattle Synthetic Trial Center",
    v2ActivationDay: 180,
    events: [
      {
        id: "sea-rel",
        kind: "global_release",
        lane: "process",
        label: "Release",
        dayStart: 0,
        dayEnd: 3,
        detail: "Same global v2.0 release; local gates are much later.",
      },
      {
        id: "sea-appr",
        kind: "local_approval",
        lane: "process",
        label: "Approval",
        dayStart: 120,
        dayEnd: 165,
        detail: "Local approval finishes late in the 215-day window.",
      },
      {
        id: "sea-train",
        kind: "training",
        lane: "process",
        label: "Training",
        dayStart: 165,
        dayEnd: 180,
        detail: "Training starts only after approval.",
      },
      {
        id: "sea-act",
        kind: "activation",
        lane: "process",
        label: "Activation",
        dayStart: 180,
        dayEnd: 190,
        detail: "Latest site to reach v2.0 (~Day 180).",
      },
      {
        id: "sea-v1",
        kind: "protocol_version",
        lane: "version",
        label: "v1.0",
        dayStart: 0,
        dayEnd: 180,
        detail: "Remains on v1.0 long after Phoenix and Boston switched.",
      },
      {
        id: "sea-v2",
        kind: "protocol_version",
        lane: "version",
        label: "v2.0",
        dayStart: 180,
        dayEnd: 215,
        detail: "Flips to v2.0 at Day 180 — ~150 days after Phoenix.",
      },
      {
        id: "sea-block",
        kind: "blocked",
        lane: "block",
        label: "Waiting on approval + training",
        dayStart: 15,
        dayEnd: 180,
        detail: "Neither approval nor training ready until late in the window.",
      },
    ],
  },
];
