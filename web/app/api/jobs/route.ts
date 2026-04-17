import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET() {
  const targets = await prisma.watch_targets.findMany({ orderBy: { id: "desc" } });
  const targetIds = targets.map((t) => t.id);

  const pendingJobs =
    targetIds.length === 0
      ? []
      : await prisma.jobs.findMany({
          where: {
            target_id: { in: targetIds },
            status: { in: ["pending", "running"] },
          },
          orderBy: { id: "desc" },
          select: {
            id: true,
            target_id: true,
            file_path: true,
            status: true,
            created_at: true,
          },
        });

  const pendingByTarget = new Map<number, typeof pendingJobs>();
  for (const pending of pendingJobs) {
    const current = pendingByTarget.get(pending.target_id) ?? [];
    current.push(pending);
    pendingByTarget.set(pending.target_id, current);
  }

  const jobs = targets.map((target) => {
    const targetPending = pendingByTarget.get(target.id) ?? [];
    return {
      ...target,
      pending_count: targetPending.length,
      pending_files: targetPending.slice(0, 20).map((job) => job.file_path),
    };
  });

  return NextResponse.json({ jobs });
}

export async function POST(request: Request) {
  const body = (await request.json()) as { directory?: string };
  const directory = (body.directory ?? "").trim();
  if (!directory) {
    return NextResponse.json({ error: "directory is required" }, { status: 400 });
  }

  const job = await prisma.watch_targets.create({
    data: { directory, enabled: 1 },
    select: { id: true },
  });
  return NextResponse.json({ id: job.id }, { status: 201 });
}
