import { NextResponse } from "next/server";
import { triggerWorkerForTarget } from "@/lib/worker";

type RouteParams = { params: Promise<{ id: string }> };

export async function POST(_request: Request, { params }: RouteParams) {
  const { id } = await params;
  const jobId = Number(id);
  if (!Number.isInteger(jobId)) {
    return NextResponse.json({ error: "invalid job id" }, { status: 400 });
  }

  try {
    const result = await triggerWorkerForTarget(jobId);
    return NextResponse.json({ ok: true, stdout: result.stdout, stderr: result.stderr });
  } catch (error) {
    return NextResponse.json(
      { ok: false, error: error instanceof Error ? error.message : "worker failed" },
      { status: 500 },
    );
  }
}
