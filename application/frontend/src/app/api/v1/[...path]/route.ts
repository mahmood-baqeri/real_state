import { NextRequest, NextResponse } from "next/server";

const FASTAPI_BASE = process.env.INTERNAL_FASTAPI_URL || "http://127.0.0.1:8020";

async function proxyToFastAPI(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const joined = path.join("/");
  const targetUrl = `${FASTAPI_BASE}/api/v1/${joined}${request.nextUrl.search}`;

  const forwardHeaders = new Headers();
  const auth = request.headers.get("authorization");
  if (auth) forwardHeaders.set("authorization", auth);
  const agencyId = request.headers.get("x-agency-id");
  if (agencyId) forwardHeaders.set("x-agency-id", agencyId);
  const contentType = request.headers.get("content-type");
  if (contentType) forwardHeaders.set("content-type", contentType);
  const idemp = request.headers.get("idempotency-key");
  if (idemp) forwardHeaders.set("idempotency-key", idemp);

  const hasBody = !["GET", "HEAD"].includes(request.method);
  const bodyText = hasBody ? await request.text() : undefined;

  const upstream = await fetch(targetUrl, {
    method: request.method,
    headers: forwardHeaders,
    body: bodyText,
    redirect: "manual",
  });

  const respBody = await upstream.text();
  return new NextResponse(respBody, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") || "application/json",
    },
  });
}

export const GET = proxyToFastAPI;
export const POST = proxyToFastAPI;
export const PUT = proxyToFastAPI;
export const PATCH = proxyToFastAPI;
export const DELETE = proxyToFastAPI;
