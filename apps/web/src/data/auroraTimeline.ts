/** Synthetic AURORA-101 215-day rollout geometry for timeline view. */

export type TimelineEventKind =
  | "global_release"
  | "local_approval"
  | "training"
  | "activation"
  | "visit"
  | "protocol_version"
  | "blocked";

export type TimelineEvent = {
  id: string;
  kind: TimelineEventKind;
  label: string;
  dayStart: number;
  dayEnd: number;
  detail?: string;
};

export type SiteTimeline = {
  siteId: string;
  city: string;
  name: string;
  events: TimelineEvent[];
};

/** Day 0 = global amendment release; axis spans 215 days. */
export const ROLLOUT_DAYS = 215;

export const AURORA_TIMELINES: SiteTimeline[] = [
  {
    siteId: "SITE-001",
    city: "Phoenix",
    name: "Phoenix Synthetic Research Clinic",
    events: [
      { id: "phx-rel", kind: "global_release", label: "Global v2.0 release", dayStart: 0, dayEnd: 2 },
      {
        id: "phx-appr",
        kind: "local_approval",
        label: "Local approval complete",
        dayStart: 5,
        dayEnd: 12,
      },
      {
        id: "phx-train",
        kind: "training",
        label: "Amendment training complete",
        dayStart: 12,
        dayEnd: 28,
      },
      {
        id: "phx-act",
        kind: "activation",
        label: "Site activation window",
        dayStart: 30,
        dayEnd: 45,
      },
      {
        id: "phx-p001",
        kind: "visit",
        label: "P001 Day 1 (immutable / completed)",
        dayStart: -10,
        dayEnd: -9,
        detail: "Historical visit — cannot rewrite",
      },
      {
        id: "phx-p002",
        kind: "visit",
        label: "P002 Day 1 scheduled",
        dayStart: 40,
        dayEnd: 41,
        detail: "Dose 12:00 · PK 6h 18:00",
      },
      {
        id: "phx-block",
        kind: "blocked",
        label: "Activation blocked — P002 courier/storage",
        dayStart: 40,
        dayEnd: 90,
        detail: "Courier 17:30 · no overnight storage",
      },
      {
        id: "phx-v1",
        kind: "protocol_version",
        label: "Active protocol v1.0",
        dayStart: 0,
        dayEnd: 215,
      },
    ],
  },
  {
    siteId: "SITE-002",
    city: "Boston",
    name: "Boston Synthetic Clinical Unit",
    events: [
      { id: "bos-rel", kind: "global_release", label: "Global v2.0 release", dayStart: 0, dayEnd: 2 },
      {
        id: "bos-appr",
        kind: "local_approval",
        label: "Local approval complete",
        dayStart: 8,
        dayEnd: 20,
      },
      {
        id: "bos-train",
        kind: "training",
        label: "Training incomplete",
        dayStart: 20,
        dayEnd: 120,
        detail: "Blocks activation",
      },
      {
        id: "bos-block",
        kind: "blocked",
        label: "Blocked pending training",
        dayStart: 20,
        dayEnd: 150,
      },
      {
        id: "bos-v1",
        kind: "protocol_version",
        label: "Active protocol v1.0",
        dayStart: 0,
        dayEnd: 215,
      },
    ],
  },
  {
    siteId: "SITE-003",
    city: "Seattle",
    name: "Seattle Synthetic Trial Center",
    events: [
      { id: "sea-rel", kind: "global_release", label: "Global v2.0 release", dayStart: 0, dayEnd: 2 },
      {
        id: "sea-appr",
        kind: "local_approval",
        label: "Local approval pending",
        dayStart: 15,
        dayEnd: 180,
      },
      {
        id: "sea-train",
        kind: "training",
        label: "Training not started",
        dayStart: 15,
        dayEnd: 200,
      },
      {
        id: "sea-block",
        kind: "blocked",
        label: "Blocked pending approval + training",
        dayStart: 15,
        dayEnd: 215,
      },
      {
        id: "sea-v1",
        kind: "protocol_version",
        label: "Active protocol v1.0",
        dayStart: 0,
        dayEnd: 215,
      },
    ],
  },
];
