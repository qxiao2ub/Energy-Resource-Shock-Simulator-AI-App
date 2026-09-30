import { useEffect, useRef, useState } from 'react';
import type * as Leaflet from 'leaflet';
import countriesGeo from '@/data/countries.json';
import { type FlowMode, type SimulationState, type Resource, RESOURCE_ICON } from '@/lib/simulation';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { formatDate } from '@/lib/event-status';

type Selection={kind:'country'|'hub'|'route';id:string};
// Distinct hues so overlapping supply routes are easy to tell apart.
const ROUTE_COLORS=['#38bdf8','#f472b6','#a3e635','#fb923c','#c084fc','#2dd4bf','#facc15','#f87171'];
export function MapVisualization({map,L,state,mode,running,speed,resource,onAddAt}:{map:Leaflet.Map|null;L:typeof Leaflet|null;state:SimulationState;mode:FlowMode;running:boolean;speed:number;resource:Resource;onAddAt:(lat:number,lng:number)=>void}) {
 const layers=useRef<Leaflet.LayerGroup|null>(null);
 const [selection,setSelection]=useState<Selection|null>(null);
 // Close stale detail when switching resources.
 useEffect(()=>{setSelection(null)},[resource]);
 useEffect(()=>{
   if(!map||!L)return;
   const group=L.layerGroup().addTo(map);layers.current=group;
   return ()=>{group.remove();layers.current=null};
 },[map,L]);
 useEffect(()=>{
   if(!map||!L||!layers.current)return;
   const layer=layers.current;layer.clearLayers();
   const showCountries=mode==='All'||mode==='Supply'||mode==='Demand'||mode==='Trade';
   const countryData=new Map(state.countries.map(c=>[c.code,c]));
   if(showCountries){
     const geo=L.geoJSON(countriesGeo as GeoJSON.GeoJsonObject,{
       style:feature=>{
         const c=countryData.get(String(feature?.id??''));
         const value=mode==='Supply'?c?.production??0:mode==='Demand'?c?.demandNow??0:mode==='Trade'?c?.balance??0:c?.stress??0;
         return { color:'var(--sim-border)',weight:.8,fillColor:mode==='Trade'&&value>0?'var(--sim-positive)':'var(--sim-stress)',fillOpacity:c?Math.min(.4,.07+Math.abs(value)*(mode==='All'?.003:.018)):0,interactive:!!c };
       },
       onEachFeature:(feature,shape)=>{
         const c=countryData.get(String(feature.id??''));if(!c)return;
         shape.bindTooltip(`<strong>${c.name}</strong><br/>Simulated ${resource}<br/>Production ${c.production.toFixed(1)} · Demand ${c.demandNow.toFixed(1)}<br/>${c.balance>=0?'Surplus':'Deficit'} ${Math.abs(c.balance).toFixed(1)}`);
         shape.on('click',(e:Leaflet.LeafletMouseEvent)=>{L.DomEvent.stopPropagation(e);setSelection({kind:'country',id:c.code});onAddAt(Math.round(e.latlng.lat*10)/10,Math.round(e.latlng.lng*10)/10)});
       }
     }).addTo(layer);
     geo.bringToBack();
   }
   if(mode==='All'||mode==='Supply'||mode==='Trade'||mode==='Money'){
      state.routes.forEach((route,routeIndex)=>{
        const isMoney=mode==='Money';
        const endpoints:[[number,number],[number,number]] = isMoney?[[route.to.lat,route.to.lng],[route.from.lat,route.from.lng]]:[[route.from.lat,route.from.lng],[route.to.lat,route.to.lng]];
        const[from,to]=endpoints;
        // Quadratic curve; alternate the bend side so nearby routes separate visually.
        const side=routeIndex%2===0?1:-1;
        const mx=(from[0]+to[0])/2,my=(from[1]+to[1])/2;
        const dx=to[1]-from[1],dy=to[0]-from[0];
        const len=Math.hypot(dx,dy)||1;
        const bend=side*len*0.18;
        const cx=mx+(-dy/len)*bend,cy=my+(dx/len)*bend;
        const curvePoints:[number,number][]=[];
        for(let i=0;i<=32;i++){
          const t=i/32,u=1-t;
          curvePoints.push([u*u*from[0]+2*u*t*cx+t*t*to[0],u*u*from[1]+2*u*t*cy+t*t*to[1]]);
        }
        const pointAt=(t:number):[number,number]=>{const u=1-t;return [u*u*from[0]+2*u*t*cx+t*t*to[0],u*u*from[1]+2*u*t*cy+t*t*to[1]]};
         const color=isMoney?'var(--sim-money)':route.disruption>.25?'var(--sim-disrupted)':ROUTE_COLORS[routeIndex%ROUTE_COLORS.length];
         const amount=route.volume*(1-route.disruption);
         const line=L.polyline(curvePoints,{color,weight:Math.max(1.5,route.volume*.42)*(1-route.disruption*.65),opacity:.78}).addTo(layer);
        line.bindTooltip(`${isMoney?'Simulated trade value':'Estimated '+resource+' flow'}<br/>${isMoney?route.to.name+' → '+route.from.name:route.from.name+' → '+route.to.name}<br/>Relative volume ${amount.toFixed(1)}${route.disruption>.15?` · disruption ${(route.disruption*100).toFixed(0)}%`:''}`);
        line.on('click',(e:Leaflet.LeafletMouseEvent)=>{L.DomEvent.stopPropagation(e);setSelection({kind:'route',id:route.id})});
        // Moving shipment dots along the curve; positions derive from simulation time.
        const drift=((state.time/3600000)*(running?Math.max(.25,speed)/24:.05))%1;
        for(let i=0;i<3;i++){
          const t=(drift+i/3)%1;
          L.circleMarker(pointAt(t),{radius:2.6,color:'var(--sim-node-edge)',weight:1,fillColor:color,fillOpacity:.95,interactive:false}).addTo(layer);
        }
        // Always-on midpoint label: material + amount.
        const mid=pointAt(0.5);
        const label=L.marker(mid,{interactive:false,icon:L.divIcon({className:'',iconSize:[0,0],html:`<div class="sim-route-label sim-route-label-hidden${route.disruption>.25?' sim-route-label-disrupted':''}">${RESOURCE_ICON[resource]} ${resource} · ${amount.toFixed(1)}</div>`})}).addTo(layer);
        label.setZIndexOffset(500);
        const baseWeight=Math.max(1.5,route.volume*.42)*(1-route.disruption*.65);
        const showLabel=(e:Leaflet.LeafletMouseEvent)=>{
          label.setLatLng(e.latlng);
          label.getElement()?.querySelector('.sim-route-label')?.classList.remove('sim-route-label-hidden');
          line.setStyle({weight:baseWeight+2.5,opacity:1});
        };
        const hideLabel=()=>{
          label.getElement()?.querySelector('.sim-route-label')?.classList.add('sim-route-label-hidden');
          line.setStyle({weight:baseWeight,opacity:.72});
        };
        line.on('mouseover',showLabel);
        line.on('mousemove',(e:Leaflet.LeafletMouseEvent)=>label.setLatLng(e.latlng));
        line.on('mouseout',hideLabel);
       if(route.disruption>.15&&!isMoney){
         const alternate=state.hubs.find(h=>h.id!==route.from.id&&h.kind!=='Chokepoint');
         if(alternate){
           const detour=L.polyline([[alternate.lat,alternate.lng],[route.to.lat,route.to.lng]],{color:'var(--sim-positive)',weight:2,opacity:Math.min(.8,route.disruption),dashArray:'3 10',className:running?'sim-route-moving':''}).addTo(layer);
           detour.bindTooltip(`Illustrative alternative supply route<br/>${alternate.name} → ${route.to.name}`);
         }
       }
     });
   }
   if(mode==='All'||mode==='Supply'||mode==='Events'){
     state.hubs.forEach(hub=>{
       const impact=Math.min(.85,state.effects.reduce((max,e)=>Math.max(max,e.impact*Math.exp(-Math.max(0,Math.hypot(hub.lat-e.event.lat,hub.lng-e.event.lng)-4)/22)),0));
       const dot=L.circleMarker([hub.lat,hub.lng],{radius:hub.kind==='Chokepoint'?7:5,color:'var(--sim-node-edge)',weight:2,fillColor:impact>.15?'var(--sim-disrupted)':'var(--sim-node)',fillOpacity:.95}).addTo(layer);
       dot.bindTooltip(`<strong>${hub.name}</strong><br/>${hub.kind} · ${resource}<br/>Simulated capacity ${((1-impact)*100).toFixed(0)}%`);
       dot.on('click',(e:Leaflet.LeafletMouseEvent)=>{L.DomEvent.stopPropagation(e);setSelection({kind:'hub',id:hub.id})});
     });
   }
   if(mode==='All'||mode==='Events'){
     state.effects.forEach(e=>{
       const phase=Math.min(1,Math.max(0,e.age/3));
       L.circle([e.event.lat,e.event.lng],{radius:(60+Number(e.event.severity||0)*18)*1000*phase,color:'var(--sim-disrupted)',fillColor:'var(--sim-disrupted)',fillOpacity:Math.max(0,.12*(1-phase/2)*e.phase),opacity:.5*e.phase,weight:1,interactive:false}).addTo(layer);
       if(e.age>=0&&e.age<5){L.circle([e.event.lat,e.event.lng],{radius:Math.max(1,e.age/5)*500000,color:'var(--sim-disrupted)',weight:2,opacity:(1-e.age/5)*.8,fillOpacity:0,interactive:false}).addTo(layer)}
     });
   }
 },[map,L,state,mode,running,speed,resource]);
 const country=selection?.kind==='country'?state.countries.find(c=>c.code===selection.id):null;
 const hub=selection?.kind==='hub'?state.hubs.find(h=>h.id===selection.id):null;
 const route=selection?.kind==='route'?state.routes.find(r=>r.id===selection.id):null;
 return <>
   <div className="pointer-events-none absolute bottom-14 right-3 z-20 rounded-md border border-border/60 bg-card/95 px-3 py-2 text-[11px] text-card-foreground shadow-md sm:bottom-4 sm:right-16">
     <span className="font-semibold">{mode==='Money'?'Simulated trade value':mode==='Trade'?'Trade balance':mode==='Demand'?'Demand':mode==='Supply'?'Production':mode==='Events'?'Event impact':'Supply stress'}</span>
     <div className="mt-1 flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-[var(--sim-positive)]"/>Surplus <span className="h-2 w-2 rounded-full bg-[var(--sim-stress)]"/>Stress <span className="h-2 w-2 rounded-full bg-[var(--sim-disrupted)]"/>Disrupted</div>
   </div>
   <Sheet open={selection!==null} onOpenChange={open=>{if(!open)setSelection(null)}}><SheetContent side="right" className="z-[1100] overflow-y-auto"><SheetHeader><SheetTitle>{country?.name??hub?.name??(route?`${route.from.name} → ${route.to.name}`:'Details')}</SheetTitle><SheetDescription>Illustrative {resource} scenario · normalized units, not official statistics</SheetDescription></SheetHeader>
     {country&&<dl className="mt-8 space-y-4 text-sm"><Detail label="Production" value={country.production.toFixed(1)}/><Detail label="Demand" value={country.demandNow.toFixed(1)}/><Detail label={country.balance>=0?'Surplus':'Import need'} value={Math.abs(country.balance).toFixed(1)}/><Detail label="Supply stress" value={`${country.stress.toFixed(0)} / 100`}/><Detail label="Price exposure" value={`${(country.exposure*10).toFixed(1)}%`}/></dl>}
     {hub&&<dl className="mt-8 space-y-4 text-sm"><Detail label="Type" value={hub.kind}/><Detail label="Country" value={state.countries.find(c=>c.code===hub.country)?.name??hub.country}/><Detail label="Operational capacity" value={`${(100*(1-Math.min(.85,state.effects.reduce((max,e)=>Math.max(max,e.impact*Math.exp(-Math.hypot(hub.lat-e.event.lat,hub.lng-e.event.lng)/22)),0)))).toFixed(0)}%`}/><Detail label="Connected routes" value={String(state.routes.filter(r=>r.from.id===hub.id).length)}/></dl>}
     {route&&<dl className="mt-8 space-y-4 text-sm"><Detail label="Resource" value={resource}/><Detail label="Estimated flow" value={`${(route.volume*(1-route.disruption)).toFixed(1)} relative units`}/><Detail label="Disruption" value={`${(route.disruption*100).toFixed(0)}%`}/><Detail label="Simulated trade value" value={`$${(route.volume*(1-route.disruption)*state.price).toFixed(0)} index units`}/></dl>}
     <div className="mt-8 border-t border-border pt-4 text-xs text-muted-foreground">{formatDate(new Date(state.time).toISOString().slice(0,10))} · Educational visualization, not a real-time market or logistics feed.</div>
     {(country||hub)&&<Button className="mt-6" onClick={()=>{const point=country??hub;if(point){onAddAt(point.lat,point.lng);setSelection(null)}}}>Add event here</Button>}
     <Button variant="outline" className="mt-6" onClick={()=>setSelection(null)}>Close</Button>
   </SheetContent></Sheet>
 </>;
}
function Detail({label,value}:{label:string;value:string}){return <div className="flex justify-between gap-4 border-b border-border pb-3"><dt className="text-muted-foreground">{label}</dt><dd className="font-medium tabular-nums text-foreground">{value}</dd></div>}
