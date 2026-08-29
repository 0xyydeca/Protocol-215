import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LaunchView } from "../views/LaunchView";
import { getApiConfig } from "./config";
import { api } from "./client";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("LaunchView cloud reset", () => {
  it("sends confirm=true after modal confirm in cloud mode", async () => {
    const user = userEvent.setup();
    const demoReset = vi.spyOn(api, "demoReset").mockResolvedValue({
      ok: true,
      message: "cleared",
    });
    vi.spyOn(api, "listRuns").mockResolvedValue([]);

    render(
      <LaunchView
        recent={[]}
        recentError={null}
        onReloadRecent={() => undefined}
        onStarted={() => undefined}
        onReset={() => undefined}
        cloudMode
        apiConfigOk
        apiHealthy
      />,
    );

    await user.click(screen.getByRole("button", { name: /reset demo state/i }));
    expect(demoReset).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /confirm reset/i }));
    await waitFor(() => expect(demoReset).toHaveBeenCalledWith(true));
  });

  it("does not fabricate a successful stage without API data", () => {
    render(
      <LaunchView
        recent={null}
        recentError={null}
        onReloadRecent={() => undefined}
        onStarted={() => undefined}
        apiConfigOk
        apiHealthy={false}
      />,
    );
    expect(screen.queryByText(/COMPLETED/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /start amendment preflight/i })).toBeDisabled();
  });
});

describe("getApiConfig vercel missing base", () => {
  it("documents same-origin ok locally", () => {
    const cfg = getApiConfig();
    expect(cfg.ok).toBe(true);
    if (cfg.ok) expect(cfg.mode).toBe("same-origin");
  });
});
