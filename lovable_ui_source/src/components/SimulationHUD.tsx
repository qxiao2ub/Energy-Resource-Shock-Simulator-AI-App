import { Activity, ArrowDownRight, ArrowUpRight, ChevronDown, CircleDollarSign } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { RESOURCES, RESOURCE_INFO, type FlowMode, type Resource, type SimulationState } from '@/lib/simulation';
const MODES:FlowMode[]=['All','Supply','Demand','Trade','Money','Events'];
export function SimulationHUD({ state, resource, onResource, mode, onMode, running }: {state:SimulationState;resource:Resource;onResource:(r:Resource)=>void;mode:FlowMode;onMode:(m:FlowMode)=>void;running:boolean}) {
 return <div className="flex w-full flex-col gap-2 border-b border-border bg-background px-3 py-3 sm:px-8">
   <div className="flex flex-wrap items-stretch gap-2">
     <div className="min-w-44 rounded-md border border-border/70 bg-card/95 p-3 shadow-lg backdrop-blur-sm">
       <label htmlFor="resource-select" className="mb-1 block text-[10px] font-semibold uppercase text-muted-foreground">Resource</label>
       <Select value={resource} onValueChange={v=>onResource(v as Resource)}><SelectTrigger id="resource-select" className="h-8 w-full border-border bg-background/60"><SelectValue /></SelectTrigger><SelectContent>{RESOURCES.map(r=><SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent></Select>
     </div>
     <div className="min-w-44 flex-1 rounded-md border border-border/70 bg-card/95 p-3 shadow-lg backdrop-blur-sm">
       <div className="flex items-center gap-1 text-[10px] font-semibold uppercase text-muted-foreground"><CircleDollarSign className="h-3 w-3"/> Simulated price</div>
       <div className="mt-1 flex items-baseline gap-2"><span className="text-xl font-semibold tabular-nums text-card-foreground transition-all duration-500">${state.price.toFixed(2)}</span><span className="text-xs text-muted-foreground">{RESOURCE_INFO[resource].unit}</span></div>
       <div className="flex items-center justify-between gap-2 text-xs"><span className="flex items-center text-primary">{state.pricePct>=0?<ArrowUpRight className="h-3 w-3"/>:<ArrowDownRight className="h-3 w-3"/>}{state.pricePct.toFixed(1)}%</span><span className="text-muted-foreground">30d scenario ${state.forecast.toFixed(2)}</span></div>
     </div>
     <div className="min-w-44 flex-1 rounded-md border border-border/70 bg-card/95 p-3 shadow-lg backdrop-blur-sm">
       <div className="flex items-center gap-1 text-[10px] font-semibold uppercase text-muted-foreground"><Activity className="h-3 w-3"/> Simulated global index</div>
       <div className="mt-2 grid grid-cols-3 gap-3 text-xs"><div><span className="text-muted-foreground">Supply</span><p className="font-semibold tabular-nums">{state.supply.toFixed(0)}%</p></div><div><span className="text-muted-foreground">Demand</span><p className="font-semibold tabular-nums">{state.demand.toFixed(0)}%</p></div><div><span className="text-muted-foreground">Balance</span><p className="font-semibold tabular-nums text-primary">{state.balance.toFixed(0)}%</p></div></div>
       <p className="mt-1 text-[10px] text-muted-foreground">{state.active.length} active shocks · risk {state.risk.toFixed(1)}/10</p>
     </div>
   </div>
   <div className="flex max-w-full items-center gap-1 self-start overflow-x-auto rounded-md border border-border/70 bg-card p-1 shadow-sm" role="group" aria-label="Map view">
     {MODES.map(m=><Button key={m} size="sm" variant={mode===m?'secondary':'ghost'} onClick={()=>onMode(m)} className="h-7 shrink-0 px-2.5 text-xs" aria-pressed={mode===m}>{m}</Button>)}
     <ChevronDown className="ml-1 hidden h-3 w-3 text-muted-foreground sm:block" aria-hidden="true"/>
   </div>
   <span className="self-start rounded bg-muted px-2 py-1 text-[10px] text-muted-foreground">Illustrative scenario · {running?'Playing':'Paused'} · not a market forecast</span>
 </div>;
}
