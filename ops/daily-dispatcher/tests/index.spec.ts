import { afterEach, describe, expect, it, vi } from "vitest";

import worker from "../src/index";
import { runSchedule, testing } from "../src/lib";

const ENV = {
  GITHUB_REPOSITORY: "ohxiyu/bmtnews",
  GITHUB_WORKFLOW: "daily-summary.yml",
  GITHUB_REF: "main",
  EDITION_TIMEZONE: "Asia/Shanghai",
  EDITION_CUTOFF_HOUR: "8",
  PUBLIC_SITE_URL: "https://ohxiyu.github.io/bmtnews",
  GITHUB_DISPATCH_TOKEN: "test-token",
} satisfies Env;

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("edition scheduling", () => {
  it("targets the Shanghai edition ending at 08:00", () => {
    const context = testing.editionContextFor(
      Date.parse("2026-07-31T00:30:00Z"),
      "Asia/Shanghai",
      8,
    );

    expect(context.date).toBe("2026-07-31");
    expect(context.cutoffUtc.toISOString()).toBe(
      "2026-07-31T00:00:00.000Z",
    );
  });

  it("builds raw and rendered URLs for both languages", () => {
    expect(testing.publicationUrls(ENV, "2026-07-31")).toEqual({
      raw: [
        "https://raw.githubusercontent.com/ohxiyu/bmtnews/gh-pages/_posts/2026-07-31-summary-zh.md",
        "https://raw.githubusercontent.com/ohxiyu/bmtnews/gh-pages/_posts/2026-07-31-summary-en.md",
      ],
      rendered: [
        "https://ohxiyu.github.io/bmtnews/2026/07/31/summary-zh.html",
        "https://ohxiyu.github.io/bmtnews/2026/07/31/summary-en.html",
      ],
    });
  });
});

describe("dispatcher behavior", () => {
  it("dispatches the explicit edition date when publication is missing", async () => {
    const requests: Request[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const request = new Request(input, init);
        requests.push(request);
        if (request.url.includes("/runs?")) {
          return Response.json({ workflow_runs: [] });
        }
        if (request.method === "POST") {
          return new Response(null, { status: 204 });
        }
        return new Response(null, { status: 404 });
      }),
    );

    await runSchedule(
      "30 0 * * *",
      Date.parse("2026-07-31T00:30:00Z"),
      ENV,
    );

    const dispatch = requests.find((request) => request.method === "POST");
    expect(dispatch).toBeDefined();
    await expect(dispatch?.json()).resolves.toEqual({
      ref: "main",
      inputs: {
        edition_date: "2026-07-31",
        trigger_source: "cloudflare-primary",
      },
    });
  });

  it("does not dispatch while an edition run is active", async () => {
    const requests: Request[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const request = new Request(input, init);
        requests.push(request);
        if (request.url.includes("/runs?")) {
          return Response.json({
            workflow_runs: [
              {
                status: "in_progress",
                conclusion: null,
                head_branch: "main",
                run_started_at: "2026-07-31T00:31:00Z",
                html_url: "https://github.com/example/run/1",
              },
            ],
          });
        }
        return new Response(null, { status: 404 });
      }),
    );

    await runSchedule(
      "40 0 * * *",
      Date.parse("2026-07-31T00:40:00Z"),
      ENV,
    );

    expect(requests.some((request) => request.method === "POST")).toBe(false);
  });

  it("does not rerun AI when gh-pages exists but rendering is delayed", async () => {
    const requests: Request[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const request = new Request(input, init);
        requests.push(request);
        if (request.url.includes("/runs?")) {
          return Response.json({
            workflow_runs: [
              {
                status: "completed",
                conclusion: "success",
                head_branch: "main",
                run_started_at: "2026-07-31T00:31:00Z",
                html_url: "https://github.com/example/run/2",
              },
            ],
          });
        }
        if (request.url.startsWith("https://raw.githubusercontent.com/")) {
          return new Response(null, { status: 200 });
        }
        return new Response(null, { status: 404 });
      }),
    );

    await runSchedule(
      "55 0 * * *",
      Date.parse("2026-07-31T00:55:00Z"),
      ENV,
    );

    expect(requests.some((request) => request.method === "POST")).toBe(false);
  });

  it("fails the final check after dispatching one last recovery", async () => {
    const requests: Request[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const request = new Request(input, init);
        requests.push(request);
        if (request.url.includes("/runs?")) {
          return Response.json({ workflow_runs: [] });
        }
        if (request.method === "POST") {
          return new Response(null, { status: 204 });
        }
        return new Response(null, { status: 404 });
      }),
    );

    await expect(
      runSchedule(
        "10 1 * * *",
        Date.parse("2026-07-31T01:10:00Z"),
        ENV,
      ),
    ).rejects.toThrow("final recovery dispatched");
    expect(requests.filter((request) => request.method === "POST")).toHaveLength(
      1,
    );
  });

  it("exposes only a read-only health endpoint", async () => {
    const health = await worker.fetch(
      new Request("https://dispatcher.example/health"),
    );
    const notFound = await worker.fetch(
      new Request("https://dispatcher.example/run", { method: "POST" }),
    );

    expect(health.status).toBe(200);
    await expect(health.json()).resolves.toMatchObject({
      service: "bmtnews-daily-dispatcher",
      status: "ok",
    });
    expect(notFound.status).toBe(404);
  });
});
