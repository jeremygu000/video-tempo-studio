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

function parsePositiveInt(value: string | null, fallback: number) {
  if (value == null) return fallback;
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) return fallback;
  return parsed;
}

export async function GET(request: Request) {
  await ensureProgressColumns();
  const { searchParams } = new URL(request.url);
  const page = parsePositiveInt(searchParams.get("page"), 1);
  const pageSize = Math.min(parsePositiveInt(searchParams.get("pageSize"), 20), 100);

  const total = await prisma.runs.count();
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(page, totalPages);
  const skip = (safePage - 1) * pageSize;

  const runs = await prisma.runs.findMany({
    orderBy: { id: "desc" },
    skip,
    take: pageSize,
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
  return NextResponse.json({
    runs,
    pagination: {
      page: safePage,
      pageSize,
      total,
      totalPages,
    },
  });
}
