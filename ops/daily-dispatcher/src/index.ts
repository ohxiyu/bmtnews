import { runSchedule } from "./lib";

export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    if (request.method !== "GET" || url.pathname !== "/health") {
      return Response.json({ error: "Not found" }, { status: 404 });
    }
    return Response.json({
      service: "bmtnews-daily-dispatcher",
      status: "ok",
      primary_cron_utc: "30 0 * * *",
      final_cron_utc: "10 1 * * *",
    });
  },

  async scheduled(
    controller: ScheduledController,
    env: Env,
  ): Promise<void> {
    await runSchedule(controller.cron, controller.scheduledTime, env);
  },
} satisfies ExportedHandler<Env>;
