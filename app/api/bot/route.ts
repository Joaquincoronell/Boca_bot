import { NextRequest, NextResponse } from "next/server";
import { timingSafeEqual } from "node:crypto";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function sameSecret(a: string, b: string) {
  const aa = Buffer.from(a);
  const bb = Buffer.from(b);
  return aa.length === bb.length && timingSafeEqual(aa, bb);
}

async function forward(request: NextRequest, path: string, method: "GET" | "POST" | "PUT", body?: unknown) {
  const expected = process.env.DASHBOARD_PASSWORD || "";
  const provided = request.headers.get("x-dashboard-password") || "";
  if (!expected || !sameSecret(provided, expected)) {
    return NextResponse.json({detail: "Contraseña del panel incorrecta o no configurada."}, {status: 401});
  }
  const backend = process.env.BOCA_BACKEND_URL || "";
  const token = process.env.BOCA_BACKEND_TOKEN || "";
  if (!backend || !token) {
    return NextResponse.json({detail: "Falta configurar BOCA_BACKEND_URL o BOCA_BACKEND_TOKEN en Vercel."}, {status: 503});
  }
  try {
    const url = new URL("/api/" + path, backend);
    const response = await fetch(url.toString(), {
      method,
      headers: {Authorization: "Bearer " + token, ...(body ? {"Content-Type": "application/json"} : {})},
      body: body ? JSON.stringify(body) : undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(20000),
    });
    const text = await response.text();
    let payload: unknown;
    try { payload = JSON.parse(text); }
    catch { payload = {detail: "Respuesta inesperada del servidor."}; }
    return NextResponse.json(payload, {status: response.status, headers: {"Cache-Control": "no-store"}});
  } catch {
    return NextResponse.json({detail: "No se pudo contactar al servidor de Playwright."}, {status: 502});
  }
}

export async function GET(request: NextRequest) {
  return forward(request, "state", "GET");
}

export async function POST(request: NextRequest) {
  let data: {action?: string; config?: unknown};
  try { data = await request.json(); }
  catch { return NextResponse.json({detail: "JSON inválido."}, {status: 400}); }
  if (data.action === "start") return forward(request, "start", "POST");
  if (data.action === "stop") return forward(request, "stop", "POST");
  if (data.action === "config") return forward(request, "config", "PUT", data.config);
  return NextResponse.json({detail: "Acción desconocida."}, {status: 400});
}
