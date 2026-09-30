import { useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { formatDate } from '@/lib/event-status';
import type { SimulationState } from '@/lib/simulation';
const DAY=86400000;
export function ScenarioTimeline({state,events,now,onSetDate,onPlay}:{state:SimulationState;events:{name:string;startDate:string;endDate:string}[];now:number;onSetDate:(n:number)=>void;onPlay:()=>void}){
 const bounds=useMemo(()=>{
   const starts=events.map(e=>Date.parse(`${e.startDate}T00:00:00Z`)).filter(Number.isFinite);
   if(!starts.length)return null;
   const ends=events.map(e=>Date.parse(`${e.endDate||e.startDate}T00:00:00Z`)).filter(Number.isFinite);
   return {min:Math.min(...starts)-7*DAY,max:Math.max(...ends)+30*DAY};
 },[events]);
 if(!bounds)return null;
 const clamped=Math.max(bounds.min,Math.min(bounds.max,now));
 const entries=state.effects.flatMap(e=>[
   e.age>=0&&e.age<3?`${e.event.name} begins near ${e.nearest.name}`:null,
   e.age>=3&&e.age<7?`Production responds at ${e.nearest.name}`:null,
   e.age>=7&&e.age<13?`Export routes from ${e.nearest.name} adjust`:null,
   e.age>=13&&e.age<24?`Importers and model price respond`:null,
   e.age>=e.duration?`Recovery begins near ${e.nearest.name}`:null,
 ]).filter((s):s is string=>Boolean(s));
 return <section className="border-b border-border bg-card/40 px-6 py-4 sm:px-8"><div className="mx-auto max-w-4xl">
   <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><div><h2 className="text-sm font-semibold text-foreground">Scenario timeline</h2><p className="text-xs text-muted-foreground">{formatDate(new Date(clamped).toISOString().slice(0,10))} · {state.resource} · simulated progression</p></div><Button size="sm" variant="outline" onClick={onPlay}>Play from first event</Button></div>
   <Slider aria-label="Scenario date" min={bounds.min} max={bounds.max} step={DAY} value={[clamped]} onValueChange={v=>onSetDate(v[0]??bounds.min)}/>
   <div className="mt-2 flex justify-between text-[11px] text-muted-foreground"><span>{formatDate(new Date(bounds.min).toISOString().slice(0,10))}</span><span>{formatDate(new Date(bounds.max).toISOString().slice(0,10))}</span></div>
   <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted-foreground"><span>Risk {state.risk.toFixed(1)}/10</span><span>Supply {state.supply.toFixed(0)}%</span><span>Estimated disrupted routes {state.routes.filter(r=>r.disruption>.15).length}</span>{entries.slice(0,2).map((entry,i)=><span key={`${i}-${entry}`} className="text-primary">↗ {entry}</span>)}</div>
 </div></section>;
}
