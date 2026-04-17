import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

async function ensureProgressColumns() {
  const columns = (await prisma.$queryRawUnsafe<Array<{ name: string }>>(
    "PRAGMA table_info(runs)"
  )) as Array<{ name: string }>;
  const names = new Set(columns.map((column) => column.name));

  if (!names.has("progress_pct")) {
    await prisma.$executeRawUnsafe("ALTER TABLE runs ADD COLUMN progress_pct INTEGER NOT NULL DEFAULT 0");
  }
  if (!names.has("progress_text")) {
    await prisma.$executeRawUnsafe("ALTER TABLE runs ADD COLUMN progress_text TEXT");
  }
  if (!names.has("progress_updated_at")) {
    await prisma.$executeRawUnsafe("ALTER TABLE runs ADD COLUMN progress_updated_at TEXT");
  }
}

export async function GET() {
  await ensureProgressColumns();
  const runs = await prisma.runs.findMany({
    orderBy: { id: "desc" },
    take: 200,
    select: {
      id: true,
      job_id: true,
      jobs: {
        select: {
          file_path: true,
          target_id: true,
        },
      },
      status: true,
      progress_pct: true,
      progress_text: true,
      progress_updated_at: true,
      duration_ms: true,
      error_message: true,
      log_file_path: true,
      created_at: true,
    },
  });
  return NextResponse.json({ runs });
}
