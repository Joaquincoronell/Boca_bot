import { NextResponse } from "next/server";
export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  const base = process.env.BOCA_BACKEND_URL || "https://boca-bot-monitor.onrender.com";
  try {
    const res = await fetch(new URL("/health", base), {cache: "no-store", signal: AbortSignal.timeout(20000)});
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    if (data?.ok !== true) throw new Error("Respuesta de salud inválida");
    return NextResponse.json({online: true, message: "Servidor Render disponible; monitor no verificado."}, {headers: {"Cache-Control": "no-store"}});
  } catch {
    return NextResponse.json({online: false, message: "Render no responde; podría estar reiniciándose o suspendido."}, {status: 503, headers: {"Cache-Control": "no-store"}});
  }
}
