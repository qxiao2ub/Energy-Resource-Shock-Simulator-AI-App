/** Deterministic classroom scenario layer inspired by the uploaded Colab prototype.
 * The notebook's trained estimator is not deployed here: these are illustrative model values, not market forecasts. */
export type Resource = 'Oil' | 'Natural Gas' | 'Gasoline' | 'Heating Oil' | 'Copper' | 'Gold' | 'Silver';
export type FlowMode = 'All' | 'Supply' | 'Demand' | 'Trade' | 'Money' | 'Events';
export type ScenarioEvent = { id: string; name: string; type: string; severity: string; startDate: string; endDate: string; lat: number; lng: number };
export type Hub = { id: string; name: string; country: string; lat: number; lng: number; resources: Resource[]; importance: number; kind: 'Energy hub' | 'Mine' | 'Port' | 'Chokepoint' };
export type Country = { code: string; name: string; lat: number; lng: number; output: Partial<Record<Resource, number>>; demand: Partial<Record<Resource, number>> };
export type Route = { id: string; from: string; to: string; resource: Resource; volume: number };

export const RESOURCES: Resource[] = ['Oil', 'Natural Gas', 'Gasoline', 'Heating Oil', 'Copper', 'Gold', 'Silver'];
export const RESOURCE_ICON: Record<Resource, string> = { Oil: '🛢', 'Natural Gas': '🔥', Gasoline: '⛽', 'Heating Oil': '♨', Copper: '🔶', Gold: '🪙', Silver: '⚪' };
export const RESOURCE_INFO: Record<Resource, { base: number; unit: string; sensitivity: number }> = {
  Oil: { base: 75, unit: '/ bbl', sensitivity: 1 }, 'Natural Gas': { base: 3, unit: '/ MMBtu', sensitivity: .9 },
  Gasoline: { base: 2.4, unit: '/ gal', sensitivity: .85 }, 'Heating Oil': { base: 2.6, unit: '/ gal', sensitivity: .85 },
  Copper: { base: 4, unit: '/ lb', sensitivity: .7 }, Gold: { base: 1800, unit: '/ oz', sensitivity: .55 }, Silver: { base: 23, unit: '/ oz', sensitivity: .45 },
};
const energy: Resource[] = ['Oil', 'Natural Gas', 'Gasoline', 'Heating Oil'];
const metals: Resource[] = ['Copper', 'Gold', 'Silver'];
export const HUBS: Hub[] = [
  { id:'hormuz', name:'Strait of Hormuz', country:'ARE', lat:26.57, lng:56.25, resources:energy, importance:10, kind:'Chokepoint' },
  { id:'suez', name:'Suez Canal', country:'EGY', lat:30.59, lng:32.27, resources:energy, importance:8, kind:'Chokepoint' },
  { id:'panama', name:'Panama Canal', country:'PAN', lat:9.08, lng:-79.68, resources:[...energy, 'Copper', 'Gold'], importance:7, kind:'Chokepoint' },
  { id:'gulf', name:'US Gulf Coast', country:'USA', lat:29.76, lng:-95.37, resources:energy, importance:9, kind:'Energy hub' },
  { id:'north-sea', name:'North Sea', country:'NOR', lat:57, lng:2.5, resources:['Oil','Natural Gas'], importance:8, kind:'Energy hub' },
  { id:'siberia', name:'West Siberia', country:'RUS', lat:61, lng:75, resources:['Oil','Natural Gas'], importance:8, kind:'Energy hub' },
  { id:'chile', name:'Chile Copper Belt', country:'CHL', lat:-22.5, lng:-68.9, resources:metals, importance:9, kind:'Mine' },
  { id:'australia-mine', name:'Western Australia Mining', country:'AUS', lat:-23.7, lng:121, resources:metals, importance:6, kind:'Mine' },
  { id:'south-africa', name:'South Africa Gold Belt', country:'ZAF', lat:-26.2, lng:28, resources:['Gold'], importance:7, kind:'Mine' },
  { id:'indonesia', name:'Indonesia LNG / Mining', country:'IDN', lat:-2.5, lng:118, resources:['Natural Gas','Copper','Gold'], importance:7, kind:'Port' },
  { id:'australia-lng', name:'Australia LNG', country:'AUS', lat:-20, lng:116, resources:['Natural Gas'], importance:7, kind:'Energy hub' },
  { id:'norway', name:'Norway Energy Hub', country:'NOR', lat:60.4, lng:5.3, resources:['Oil','Natural Gas'], importance:7, kind:'Energy hub' },
];
// Normalized illustrative units, not reported national production statistics.
const C = (code:string,name:string,lat:number,lng:number,output:Partial<Record<Resource,number>>,demand:Partial<Record<Resource,number>>):Country => ({code,name,lat,lng,output,demand});
export const COUNTRIES: Country[] = [
 C('USA','United States',39,-98,{Oil:13,'Natural Gas':15,Gasoline:11,'Heating Oil':8,Copper:3,Gold:3,Silver:2},{Oil:20,'Natural Gas':13,Gasoline:12,'Heating Oil':9,Copper:6,Gold:5,Silver:5}),
 C('SAU','Saudi Arabia',24,45,{Oil:12,'Natural Gas':3,Gasoline:4,'Heating Oil':3},{Oil:4,'Natural Gas':2,Gasoline:2,'Heating Oil':2}),
 C('CHN','China',36,104,{Oil:4,'Natural Gas':5,Gasoline:4,'Heating Oil':3,Copper:6,Gold:4,Silver:5},{Oil:16,'Natural Gas':10,Gasoline:8,'Heating Oil':7,Copper:16,Gold:10,Silver:9}),
 C('IND','India',21,78,{Oil:2,'Natural Gas':2,Gasoline:2,'Heating Oil':2,Copper:2,Gold:1,Silver:1},{Oil:8,'Natural Gas':6,Gasoline:5,'Heating Oil':4,Copper:6,Gold:8,Silver:7}),
 C('RUS','Russia',61,96,{Oil:11,'Natural Gas':13,Gasoline:6,'Heating Oil':6,Gold:5,Copper:4},{Oil:4,'Natural Gas':5,Gasoline:3,'Heating Oil':3,Gold:2,Copper:2}),
 C('ARE','United Arab Emirates',24,54,{Oil:6,'Natural Gas':4,Gasoline:3},{Oil:2,'Natural Gas':2,Gasoline:2}),
 C('QAT','Qatar',25.3,51.2,{'Natural Gas':12,Oil:2},{'Natural Gas':1,Oil:1}),
 C('NOR','Norway',61,9,{Oil:6,'Natural Gas':8},{Oil:1,'Natural Gas':1}),
 C('AUS','Australia',-25,134,{'Natural Gas':10,Copper:7,Gold:8,Silver:5,Oil:2},{'Natural Gas':2,Copper:2,Gold:2,Silver:2,Oil:2}),
 C('CHL','Chile',-33,-71,{Copper:14,Gold:3,Silver:5},{Copper:2,Gold:1,Silver:1,Oil:2}),
 C('ZAF','South Africa',-29,24,{Gold:9,Silver:3,Copper:2},{Gold:2,Silver:1,Copper:1,Oil:2}),
 C('IDN','Indonesia',-2,118,{'Natural Gas':6,Copper:5,Gold:4,Oil:3},{'Natural Gas':2,Copper:2,Gold:2,Oil:4}),
 C('JPN','Japan',36,138,{Gold:1},{Oil:6,'Natural Gas':8,Gasoline:4,'Heating Oil':4,Copper:5,Gold:4,Silver:3}),
 C('KOR','South Korea',36,128,{},{Oil:5,'Natural Gas':5,Gasoline:4,Copper:5,Gold:3,Silver:3}),
 C('DEU','Germany',51,10,{Copper:1},{Oil:4,'Natural Gas':6,Gasoline:4,'Heating Oil':4,Copper:4,Gold:3,Silver:3}),
 C('GBR','United Kingdom',54,-2,{Oil:2,'Natural Gas':2},{Oil:4,'Natural Gas':4,Gold:3,Silver:2}),
 C('BRA','Brazil',-11,-52,{Oil:5,Copper:3,Gold:3},{Oil:5,Copper:3,Gold:2}),
 C('CAN','Canada',57,-106,{Oil:7,'Natural Gas':6,Copper:4,Gold:3,Silver:3},{Oil:3,'Natural Gas':3,Copper:2,Gold:2,Silver:2}),
 C('NGA','Nigeria',9,8,{Oil:5,'Natural Gas':3},{Oil:2,'Natural Gas':1}),
 C('PER','Peru',-10,-75,{Copper:8,Gold:3,Silver:8},{Copper:1,Gold:1,Silver:1}),
 C('EGY','Egypt',27,30,{Oil:2,'Natural Gas':3},{Oil:3,'Natural Gas':3}),
 C('PAN','Panama',9,-80,{},{Oil:1,'Natural Gas':1}),
];
export const ROUTES: Route[] = [
 {id:'gulf-china',from:'gulf',to:'CHN',resource:'Oil',volume:5}, {id:'hormuz-china',from:'hormuz',to:'CHN',resource:'Oil',volume:9}, {id:'hormuz-india',from:'hormuz',to:'IND',resource:'Oil',volume:7}, {id:'north-europe',from:'north-sea',to:'DEU',resource:'Oil',volume:4}, {id:'gulf-japan',from:'gulf',to:'JPN',resource:'Oil',volume:3},
 {id:'qatar-china',from:'hormuz',to:'CHN',resource:'Natural Gas',volume:7}, {id:'australia-japan',from:'australia-lng',to:'JPN',resource:'Natural Gas',volume:7}, {id:'australia-china',from:'australia-lng',to:'CHN',resource:'Natural Gas',volume:6}, {id:'norway-europe',from:'norway',to:'DEU',resource:'Natural Gas',volume:5},
 {id:'gulf-gasoline',from:'gulf',to:'BRA',resource:'Gasoline',volume:4}, {id:'hormuz-gasoline',from:'hormuz',to:'IND',resource:'Gasoline',volume:4}, {id:'north-heating',from:'north-sea',to:'GBR',resource:'Heating Oil',volume:4}, {id:'gulf-heating',from:'gulf',to:'DEU',resource:'Heating Oil',volume:3},
 {id:'chile-china',from:'chile',to:'CHN',resource:'Copper',volume:9}, {id:'australia-copper',from:'australia-mine',to:'IND',resource:'Copper',volume:5}, {id:'chile-us',from:'chile',to:'USA',resource:'Copper',volume:4},
 {id:'south-africa-india',from:'south-africa',to:'IND',resource:'Gold',volume:5}, {id:'australia-gold',from:'australia-mine',to:'CHN',resource:'Gold',volume:4}, {id:'chile-silver',from:'chile',to:'CHN',resource:'Silver',volume:4}, {id:'australia-silver',from:'australia-mine',to:'IND',resource:'Silver',volume:4},
];
const BASE_IMPACT:Record<string,number> = { war:1,earthquake:.65,hurricane:.7,port_closure:.75,pipeline_failure:.85,cyberattack:.55,labor_strike:.45,sanctions:.9,mine_accident:.6,drought:.4,shipping_chokepoint:.95,pandemic:.6 };
const DAY = 86400000;
export function distanceKm(a:{lat:number;lng:number},b:{lat:number;lng:number}) {
 const r=Math.PI/180,dLat=(b.lat-a.lat)*r,dLon=(b.lng-a.lng)*r;
 const x=Math.sin(dLat/2)**2+Math.cos(a.lat*r)*Math.cos(b.lat*r)*Math.sin(dLon/2)**2;
 return 12742*Math.asin(Math.min(1,Math.sqrt(x)));
}
export function simulate(events:ScenarioEvent[], resource:Resource, now:number) {
 const hubs=HUBS.filter(h=>h.resources.includes(resource));
 const effects=events.map(event=>{
   const start=Date.parse(`${event.startDate}T00:00:00Z`);
   if (!Number.isFinite(start)) return null;
   const end= event.endDate ? Date.parse(`${event.endDate}T00:00:00Z`)+DAY : start+21*DAY;
   const age=(now-start)/DAY;
   const duration=Math.max(1,(end-start)/DAY);
   if(age<0||age>duration+30) return null;
   const severity=Math.max(0,Math.min(10,Number(event.severity)||0));
   const nearest=[...hubs].sort((a,b)=>distanceKm(event,a)-distanceKm(event,b))[0];
   if(!nearest) return null;
   const distance=distanceKm(event,nearest);
   const safeHaven=(resource==='Gold'||resource==='Silver') && ['war','sanctions','pandemic','cyberattack'].includes(event.type);
   const proximity=Math.exp(-distance/1500);
   const strength=(BASE_IMPACT[event.type]??.5)*(severity/10)*RESOURCE_INFO[resource].sensitivity*(.55+nearest.importance/10)*(safeHaven?Math.max(.45,proximity):proximity);
   const onset=Math.min(1,Math.max(0,age/3));
   const recovery=age>duration?Math.exp(-(age-duration)/9):1;
   const phase=onset*recovery;
   return {event,nearest,age,duration,strength,phase, impact:strength*phase, safeHaven};
 }).filter((e):e is NonNullable<typeof e>=>e!==null);
 const active=effects.filter(e=>e.age<=e.duration);
  const risk=Math.min(10,effects.reduce((sum,e)=>sum+e.impact*7,0));
  // Transparent deterministic proxy; NOT the Colab model's price_delta_30d_pct.
  // Baseline market motion: slow seasonal wave + faster deterministic "noise", keyed to the
  // simulated clock so the price always drifts even with no events, and replays identically.
  const day=now/DAY;
  const seed=RESOURCES.indexOf(resource)*13.7;
  const seasonalPct=1.6*Math.sin(day/29+seed);
  const noisePct=.7*Math.sin(day*1.9+seed*2.3)+.45*Math.sin(day*5.3+seed);
  const basePct=seasonalPct+noisePct;
  const forecastPct=Math.min(35,basePct+effects.reduce((sum,e)=>sum+e.strength*(e.safeHaven?7:11),0));
  // Event shocks ramp in over ~15 days after a 4-day lag, on top of baseline motion.
  const shockPct=effects.reduce((sum,e)=>sum+e.impact*(e.safeHaven?7:11)*Math.min(1,Math.max(0,(e.age-4)/15)),0);
  const pricePct=Math.max(-25,Math.min(35,basePct+shockPct));
  const supply=Math.max(45,100-effects.reduce((sum,e)=>sum+e.impact*19*Math.min(1,Math.max(0,(e.age-1)/4)),0));
  const demand=Math.max(85,Math.min(110,100-shockPct*.16+basePct*.5));
 const routes=ROUTES.filter(r=>r.resource===resource).map(route=>{
   const from=hubs.find(h=>h.id===route.from);
   const to=COUNTRIES.find(c=>c.code===route.to);
   const disruption=from?Math.min(.85,effects.reduce((max,e)=>Math.max(max,e.impact*Math.exp(-distanceKm(from,e.nearest)/2500)*Math.min(1,Math.max(0,(e.age-3)/8))),0)):0;
   return {...route,from,to,disruption};
 }).filter((r):r is typeof r & {from:Hub;to:Country}=>Boolean(r.from&&r.to));
 const countries=COUNTRIES.map(country=>{
   const production=country.output[resource]??0, baselineDemand=country.demand[resource]??0;
   const exposure=effects.reduce((sum,e)=>sum+e.impact*Math.exp(-distanceKm(country,e.nearest)/5500)*Math.min(1,Math.max(0,(e.age-5)/7)),0);
   const productionNow=production*(1-Math.min(.8,exposure*.45));
   const demandNow=baselineDemand*(demand/100);
   return {...country,production:productionNow,demandNow,balance:productionNow-demandNow,stress:Math.min(100,Math.max(0,(demandNow-productionNow)*5+exposure*38)),exposure};
 });
 return {time:now,resource,price:RESOURCE_INFO[resource].base*(1+pricePct/100),pricePct,forecast:RESOURCE_INFO[resource].base*(1+forecastPct/100),forecastPct,supply,demand,balance:supply-demand,risk,effects,active,countries,routes,hubs};
}
export type SimulationState = ReturnType<typeof simulate>;
