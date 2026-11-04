"use client";
import {useState} from "react";
import {Server,RefreshCw,Play,Square} from "lucide-react";

type Event = {at:string;message:string};
type Status = {
  status:string;running:boolean;last_check:string|null;last_message:string;
  session_configured:boolean;mapped_sector_names:string[];
  allowed_mapped_sectors:string[];events:Event[];
};
export default function ServerControls({matchId,allowed,all}:{matchId:string;allowed:string[];all:boolean}) {
  const [password,setPassword]=useState("");
  const [server,setServer]=useState<Status|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  async function call(action:"status"|"config"|"start"|"stop") {
    setBusy(true);setError("");
    try {
      const res=await fetch("/api/bot",{
        method:action==="status"?"GET":"POST",
        headers:{"x-dashboard-password":password,...(action!=="status"?{"Content-Type":"application/json"}:{})},
        body:action==="status"?undefined:JSON.stringify({
          action,config:action==="config"?{
            match_id:matchId,
            interval_seconds:45,
            all_sectors:all,
            allowed_sectors:allowed,
          }:undefined,
        }),
        cache:"no-store",
      });
      const data=await res.json();
      if(!res.ok)throw new Error(data.detail||"Error de conexión");
      const st=await fetch("/api/bot",{headers:{"x-dashboard-password":password},cache:"no-store"});
      if(st.ok)setServer(await st.json());
      if(!st.ok && action==="status")setServer(null);
    }catch(e){setError(e instanceof Error?e.message:"Error de conexión")}
    finally{setBusy(false)}
  }
  return <section className="panel server-panel">
    <div className="paneltitle"><div><h2>Servidor de monitoreo</h2>
      <p>Conexión privada con el servicio de Playwright.</p></div><Server/></div>
    <label className="field">Contraseña de administración
      <input type="password" autoComplete="off" value={password}
        onChange={e=>setPassword(e.target.value)}
        placeholder="Contraseña configurada en Vercel"/></label>
    <div className="server-actions">
      <button className="secondary" onClick={()=>call("status")} disabled={busy||!password}><RefreshCw size={15}/> Conectar / actualizar</button>
      {server&&<>
        <button onClick={()=>call("config")} disabled={busy||server.running}>Guardar config. en servidor</button>
        <button onClick={()=>call(server.running?"stop":"start")} disabled={busy}>
          {server.running?<Square size={15}/>:<Play size={15}/>}
          {server.running?"Detener monitor":"Iniciar monitor"}
        </button>
      </>}
    </div>
    {error&&<p className="server-error">{error}</p>}
    {server&&<div className="server-status">
      <p><b>Estado:</b> {server.status} {server.running?"● Activo":"○ Inactivo"}</p>
      <p><b>Última revisión:</b> {server.last_check||"Nunca"}</p>
      <p><b>Sesión importada:</b> {server.session_configured?"Sí":"No"}</p>
      <p><b>Sectores mapeados:</b> {server.mapped_sector_names.length?server.mapped_sector_names.join(", "):"Pendientes de identificar en Boca Socios"}</p>
      <div className="server-logs">{server.events.slice(0,10).map((e,i)=><div key={i}>{new Date(e.at).toLocaleTimeString("es-AR")} · {e.message}</div>)}</div>
    </div>}
    <p className="note">La búsqueda solo comienza con una sesión autenticada y selectores reales de sectores. No supera colas ni controles de acceso.</p>
  </section>;
}
