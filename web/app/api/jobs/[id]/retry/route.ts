import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

type RouteParams = { params: Promise<{ id: string }> };

export async function POST(_request: Request, { params }: RouteParams) {
  const { id } = await params;
  const jobId = Number(id);
  if (!Number.isInteger(jobId)) {
    return NextResponse.json({ error: "invalid job id" }, { status: 400 });
  }

  const result = await prisma.jobs.updateMany({
    where: {
      id: jobId,
      status: { in: ["failed", "skipped"] },
    },
    data: {
      status: "pending",
      started_at: null,
      finished_at: null,
    },
  });

  if (result.count === 0) {
    return NextResponse.json(
      { ok: false, error: "job is not failed/skipped or does not exist" },
      { status: 409 },
    );
  }

  return NextResponse.json({ ok: true, requeued: result.count });
}
