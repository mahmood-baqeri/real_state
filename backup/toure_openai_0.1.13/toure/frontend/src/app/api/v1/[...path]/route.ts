import { NextRequest, NextResponse } from "next/server";

const FASTAPI_BASE = process.env.INTERNAL_FASTAPI_URL || "http://127.0.0.1:8020";

async function proxyToFastAPI(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> }
) {
  const { path = [] } = await context.params;
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
  const bodyBuffer = hasBody ? await request.arrayBuffer() : undefined;

  try {
    const upstream = await fetch(targetUrl, {
      method: request.method,
      headers: forwardHeaders,
      body: bodyBuffer && bodyBuffer.byteLength > 0 ? bodyBuffer : undefined,
      redirect: "manual",
    });

    const respBuffer = await upstream.arrayBuffer();
    const respHeaders = new Headers();
    respHeaders.set(
      "content-type",
      upstream.headers.get("content-type") || "application/json"
    );
    const contentDisposition = upstream.headers.get("content-disposition");
    if (contentDisposition) {
      respHeaders.set("content-disposition", contentDisposition);
    }
    const cacheControl = upstream.headers.get("cache-control");
    if (cacheControl) {
      respHeaders.set("cache-control", cacheControl);
    }

    return new NextResponse(respBuffer, {
      status: upstream.status,
      headers: respHeaders,
    });
  } catch {
    return NextResponse.json(
      {
        success: false,
        data: null,
        meta: {},
        errors: [
          {
            code: "UPSTREAM_UNAVAILABLE",
            detail: "سرویس FastAPI موقتاً در دسترس نیست. لطفاً چند لحظه دیگر تلاش کنید.",
          },
        ],
        detail: "سرویس FastAPI موقتاً در دسترس نیست. لطفاً چند لحظه دیگر تلاش کنید.",
      },
      { status: 503 }
    );
  }
}

export const GET = proxyToFastAPI;
export const POST = proxyToFastAPI;
export const PUT = proxyToFastAPI;
export const PATCH = proxyToFastAPI;
export const DELETE = proxyToFastAPI;
