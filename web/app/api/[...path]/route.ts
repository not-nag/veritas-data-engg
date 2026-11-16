import { NextRequest } from "next/server";
export const dynamic = "force-dynamic";
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  if (
    path.length !== 1 ||
    ![
      "session",
      "mappings",
      "cloud",
      "dashboard",
      "record",
      "process",
      "review",
      "export",
      "operations",
      "dead-letter",
    ].includes(path[0])
  )
    return Response.json({ error: "Not found" }, { status: 404 });
  if (request.method === "POST") {
    const origin = request.headers.get("origin");
    if (origin && new URL(origin).host !== request.headers.get("host"))
      return Response.json({ error: "Origin rejected" }, { status: 403 });
  }
  try {
    const body = request.method === "POST" ? await request.text() : undefined;
    if (body && Buffer.byteLength(body) > 10_000_000)
      return Response.json({ error: "Upload limit is 10 MB" }, { status: 413 });
    const response = await fetch(
      `http://127.0.0.1:8000/api/${path[0]}${request.nextUrl.search}`,
      {
        method: request.method,
        headers: {
          "Content-Type": "application/json",
          ...(request.headers.get("authorization")
            ? { Authorization: request.headers.get("authorization")! }
            : {}),
        },
        body,
        cache: "no-store",
        signal: AbortSignal.timeout(120000),
      },
    );
    return new Response(await response.text(), {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("Content-Type") || "application/json",
        ...(path[0] === "export"
          ? {
              "Content-Disposition":
                'attachment; filename="veritas-standardised.csv"',
            }
          : {}),
      },
    });
  } catch {
    return Response.json(
      {
        error:
          "The processing service is unavailable. Start the Python API on port 8000.",
      },
      { status: 503 },
    );
  }
}
export { proxy as GET, proxy as POST };
