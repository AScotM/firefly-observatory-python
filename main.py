#!/usr/bin/env python3
import argparse
import collections
import datetime
import json
import math
import os
import random
import shutil
import signal
import sys
import time

VERSION = '1.0.0'
PALETTES = {
    'aurora': ((40,190,190),(70,255,160),(80,125,255),(255,195,110)),
    'ember': ((255,110,45),(255,195,60),(255,80,100),(255,235,160)),
    'moon': ((80,140,225),(150,195,255),(190,165,255),(215,235,255)),
    'forest': ((40,145,80),(100,220,100),(180,245,100),(255,215,100)),
    'ocean': ((25,120,195),(45,220,230),(120,175,255),(170,250,245)),
    'violet': ((130,65,225),(205,105,245),(255,145,220),(115,175,255)),
    'mono': ((120,120,120),(170,170,170),(215,215,215),(255,255,255))
}
MODES = ('flock','drift','orbit','breathe','swarm','rain')
FIELDS = ('x','y','vx','vy','phase','frequency','energy','size','family','age')
STOP = False

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def torus(a,b,size):
    d=b-a
    if d > size/2: d-=size
    if d < -size/2: d+=size
    return d

def stop_handler(signum, frame):
    global STOP
    STOP = True

class World:
    def __init__(self, cfg):
        self.c=cfg
        self.rng=random.Random(cfg.seed)
        self.agents=[]
        self.t=0.0
        self.frame=0
        self.order=0.0
        self.mean_energy=0.0
        self.telemetry={'cpu':0.0,'memory':0.0,'io':0.0}
        for _ in range(cfg.agents):
            r=self.rng
            self.agents.append([r.random()*cfg.width,r.random()*cfg.height,(r.random()-.5)*2,(r.random()-.5)*2,r.random()*2*math.pi,.65+r.random()*1.3,.5+r.random()*.5,.6+r.random()*.8,r.randrange(4),0.0])

    def step(self,dt):
        c=self.c
        radius=max(1,c.radius)
        cols=max(1,math.ceil(c.width/radius))
        rows=max(1,math.ceil(c.height/radius))
        grid=collections.defaultdict(list)
        for i,a in enumerate(self.agents):
            grid[(min(cols-1,int(a[0]/radius)),min(rows-1,int(a[1]/radius)))].append(i)
        updated=[]
        sx=sy=energy=0.0
        cx=c.width/2
        cy=c.height/2
        for i,a in enumerate(self.agents):
            x,y,vx,vy,phase,freq,en,size,family,age=a
            count=0
            sine=alignx=aligny=repelx=repely=0.0
            gx=min(cols-1,int(x/radius)); gy=min(rows-1,int(y/radius))
            cells={( (gx+dx)%cols,(gy+dy)%rows) for dx in (-1,0,1) for dy in (-1,0,1)}
            for cell in cells:
                for j in grid[cell]:
                    if i==j: continue
                    b=self.agents[j]
                    dx=torus(x,b[0],c.width); dy=torus(y,b[1],c.height)
                    d2=dx*dx+dy*dy
                    if d2>=c.radius*c.radius: continue
                    sine+=math.sin(b[4]-phase)
                    alignx+=b[2]; aligny+=b[3]
                    if d2>.000001:
                        f=1/(d2+.2)
                        repelx-=dx*f; repely-=dy*f
                    count+=1
            coupling=c.coupling*(1+.35*self.telemetry['cpu'] if c.telemetry else 1)
            phase=(phase+dt*(freq+coupling*sine/max(1,count)))%(2*math.pi)
            nx=self.rng.gauss(0,1)*c.noise
            ny=self.rng.gauss(0,1)*c.noise
            if c.mode=='flock' and count:
                nx+=.3*(alignx/count-vx)+.12*repelx
                ny+=.3*(aligny/count-vy)+.12*repely
            elif c.mode=='orbit':
                dx=torus(x,cx,c.width); dy=torus(y,cy,c.height)
                r=max(1,math.hypot(dx,dy))
                nx+=-dy/r*.7+dx/r*.08
                ny+=dx/r*.7+dy/r*.08
            elif c.mode=='breathe':
                nx+=math.sin(self.t*.7+phase)*.3
                ny+=math.cos(self.t*.7+phase)*.3
            elif c.mode=='swarm':
                nx+=repelx*.35+math.sin(self.t*.17+family)*.3
                ny+=repely*.35+math.cos(self.t*.13+family)*.3
            elif c.mode=='rain':
                ny+=.6
                nx+=math.sin(self.t+y*.05)*.15
            elif c.mode=='drift':
                nx+=math.sin(self.t*.2+y*.03)*.08
                ny+=math.cos(self.t*.2+x*.03)*.08
            if c.mode!='rain':
                nx+=torus(x,cx,c.width)/max(1,c.width)*c.gravity
                ny+=torus(y,cy,c.height)/max(1,c.height)*c.gravity
            nx+=c.wind*.3
            vx=clamp(vx*.985+nx*dt,-2.8,2.8)
            vy=clamp(vy*.985+ny*dt,-2.8,2.8)
            x=(x+vx*dt*2.2)%c.width
            y=(y+vy*dt*1.1)%c.height
            en=clamp(.55+.45*math.sin(phase),0,1)
            updated.append([x,y,vx,vy,phase,freq,en,size,family,age+dt])
            sx+=math.cos(phase); sy+=math.sin(phase); energy+=en
        self.agents=updated
        self.t+=dt
        self.frame+=1
        self.order=math.hypot(sx,sy)/len(updated)
        self.mean_energy=energy/len(updated)

class Field:
    def __init__(self,w,h):
        self.w=w;self.h=h
        self.data=[0.0]*(w*h*3)
    def fade(self,k):
        self.data=[v*k for v in self.data]
    def glow(self,x,y,r,color,strength):
        r=max(.3,r)
        span=math.ceil(r*2.7)
        for py in range(max(0,int(y)-span),min(self.h,int(y)+span+1)):
            yy=(py-y)*1.7
            for px in range(max(0,int(x)-span),min(self.w,int(x)+span+1)):
                d2=(px-x)**2+yy*yy
                v=strength*math.exp(-d2/(2*r*r))
                if v<.0001: continue
                k=(py*self.w+px)*3
                self.data[k]=min(255,self.data[k]+color[0]*v)
                self.data[k+1]=min(255,self.data[k+1]+color[1]*v)
                self.data[k+2]=min(255,self.data[k+2]+color[2]*v)
    def paint(self,world):
        c=world.c
        self.fade(c.trails)
        colors=PALETTES[c.palette]
        for a in world.agents:
            pulse=a[6]**3
            self.glow(a[0],a[1],(.65+a[7]*.4)*c.bloom,colors[a[8]%len(colors)],(.06+pulse*.8)*c.density)
            if pulse>.72:
                self.glow(a[0],a[1],.45,(255,255,235),(pulse-.7)*1.5)
    def ansi(self,c,world):
        chars=' .,:;irsXA253hMHGS#9B&@'
        out=['\x1b[H']
        for y in range(self.h):
            last=None
            for x in range(self.w):
                k=(y*self.w+x)*3
                r,g,b=(int(clamp(v,0,255)) for v in self.data[k:k+3])
                lum=clamp((r*.2126+g*.7152+b*.0722)/255,0,1)
                if c.ascii:
                    out.append(chars[int(lum*(len(chars)-1))])
                    continue
                glyph='✶' if lum>.76 else '✦' if lum>.43 else '•' if lum>.15 else '·' if lum>.045 else ' '
                rgb=(r,g,b)
                if rgb!=last:
                    out.append(f'\x1b[38;2;{r};{g};{b}m')
                    last=rgb
                out.append(glyph)
            out.append('\x1b[0m\x1b[K')
            if y<self.h-1: out.append('\n')
        if c.stats:
            out.append(f'\n\x1b[2m firefly observatory python | {c.mode} | {len(world.agents)} agents | t {world.t:.1f}s | coherence {world.order:.3f} | glow {world.mean_energy:.3f} | seed {c.seed}\x1b[0m\x1b[K')
            if c.telemetry:
                v=world.telemetry
                out.append(f"\n\x1b[2m CPU {v['cpu']*100:.1f}% | memory {v['memory']*100:.1f}% | disk {v['io']:.1f} MB/s\x1b[0m\x1b[K")
        return ''.join(out)
    def ppm(self,path):
        with open(path,'wb') as f:
            f.write(f'P6\n{self.w} {self.h}\n255\n'.encode())
            f.write(bytes(int(clamp(v,0,255)) for v in self.data))
    def text(self,path):
        chars=' .,:;irsXA253hMHGS#9B&@'
        with open(path,'w',encoding='utf-8') as f:
            for y in range(self.h):
                f.write(''.join(chars[int(clamp(sum(self.data[(y*self.w+x)*3:(y*self.w+x)*3+3])/765,0,1)*(len(chars)-1))] for x in range(self.w))+'\n')

class LinuxTelemetry:
    def __init__(self):
        self.last=None
        self.last_time=None
    def read(self):
        try:
            with open('/proc/stat',encoding='ascii') as f: cpu=[int(x) for x in f.readline().split()[1:]]
            total=sum(cpu); idle=cpu[3]+(cpu[4] if len(cpu)>4 else 0)
            with open('/proc/meminfo',encoding='ascii') as f:
                mem={k:int(v.split()[0]) for k,v in (line.split(':',1) for line in f if ':' in line)}
            memory=1-mem.get('MemAvailable',0)/max(1,mem.get('MemTotal',1))
            with open('/proc/diskstats',encoding='ascii') as f:
                sectors=sum(int(v[5])+int(v[9]) for line in f if len(v:=line.split())>=10 and not v[2].startswith(('loop','ram')))
            now=time.monotonic()
            cpu_usage=io=0.0
            if self.last is not None:
                oldtotal,oldidle,oldsectors=self.last
                dt=now-self.last_time
                cpu_usage=clamp(1-(idle-oldidle)/max(1,total-oldtotal),0,1)
                io=max(0,sectors-oldsectors)*512/max(dt,1e-6)/1e6
            self.last=(total,idle,sectors);self.last_time=now
            return {'cpu':cpu_usage,'memory':clamp(memory,0,1),'io':io}
        except (OSError,ValueError,IndexError,ZeroDivisionError):
            return {'cpu':0.0,'memory':0.0,'io':0.0}

def parser():
    p=argparse.ArgumentParser(description='Faithful Python adaptation of Firefly Observatory Go')
    p.add_argument('command',nargs='?',default='run',choices=('run','render','inspect','palettes','modes','version'))
    specs={'agents':(int,420),'fps':(int,24),'width':(int,0),'height':(int,0),'seed':(int,0),'palette':(str,'aurora'),'mode':(str,'flock'),'coupling':(float,1.4),'radius':(float,6.5),'speed':(float,1.0),'noise':(float,.22),'trails':(float,.83),'duration':(float,0),'density':(float,1),'wind':(float,.08),'gravity':(float,.04),'bloom':(float,.85),'frames':(int,0),'output':(str,''),'record':(str,''),'snapshot':(str,''),'restore':(str,'')}
    for name,(kind,default) in specs.items(): p.add_argument('-'+name,'--'+name,type=kind,default=default)
    for name in ('telemetry','border','ascii','headless','quiet','eco'):
        p.add_argument('-'+name,'--'+name,action='store_true')
    p.add_argument('-stats','--stats',action=argparse.BooleanOptionalAction,default=True)
    return p

def save_snapshot(path,w):
    import dataclasses
    data={'version':1,'config':vars(w.c),'agents':[dict(zip(FIELDS,a)) for a in w.agents],'time':w.t,'frame':w.frame,'created':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    with open(path,'w',encoding='utf-8') as f:json.dump(data,f,indent=2)

def restore_snapshot(path,w):
    with open(path,encoding='utf-8') as f: data=json.load(f)
    if data.get('version')!=1: raise ValueError('unsupported snapshot version')
    old=data['config']
    if int(old['width'])!=w.c.width or int(old['height'])!=w.c.height:
        raise ValueError('snapshot dimensions must match')
    w.agents=[[a[k] for k in FIELDS] for a in data['agents']]
    w.t=float(data['time']);w.frame=int(data['frame'])

def main():
    global STOP
    c=parser().parse_args()
    if c.command=='version':print('Firefly Observatory Python '+VERSION);return 0
    if c.command=='palettes':print('\n'.join(PALETTES));return 0
    if c.command=='modes':print('\n'.join(MODES));return 0
    if c.palette not in PALETTES or c.mode not in MODES:raise ValueError('unknown palette or mode')
    if not 1<=c.agents<=30000 or not 1<=c.fps<=120 or c.radius<=0 or c.speed<=0 or c.coupling<0 or not 0<=c.trails<1 or c.density<=0 or c.bloom<0 or c.frames<0:raise ValueError('invalid configuration')
    if c.eco:
        c.fps=min(c.fps,12)
        if not c.restore:c.agents=min(c.agents,240)
    term=shutil.get_terminal_size((90,30))
    c.width=int(clamp(c.width or term.columns,12,500))
    c.height=int(clamp(c.height or term.lines-2-(1 if c.telemetry and c.stats else 0),6,200))
    if not c.seed:c.seed=time.time_ns()
    if c.command=='render' and not c.frames:c.frames=1
    w=World(c)
    if c.restore:restore_snapshot(c.restore,w)
    f=Field(c.width,c.height)
    telemetry=LinuxTelemetry() if c.telemetry else None
    interval=1/c.fps
    start=time.monotonic();deadline=start
    record=open(c.record,'a',encoding='utf-8') if c.record else None
    signal.signal(signal.SIGINT,stop_handler)
    signal.signal(signal.SIGTERM,stop_handler)
    interactive=not (c.headless or c.quiet or c.command=='inspect')
    if interactive:sys.stdout.write('\x1b[?25l\x1b[2J');sys.stdout.flush()
    try:
        while not STOP:
            if c.frames and w.frame>=c.frames:break
            if c.duration and time.monotonic()-start>=c.duration:break
            if telemetry and (w.frame%max(1,c.fps)==0):w.telemetry=telemetry.read()
            w.step(c.speed/c.fps)
            if interactive or c.output:
                f.paint(w)
            if interactive:
                sys.stdout.write(f.ansi(c,w));sys.stdout.flush()
            if record:
                record.write(json.dumps({'frame':w.frame,'time':w.t,'agents':len(w.agents),'coherence':w.order,'glow':w.mean_energy,'telemetry':w.telemetry})+'\n')
                if w.frame%60==0:record.flush()
            deadline+=interval
            wait=deadline-time.monotonic()
            if wait>0:time.sleep(wait)
            else:deadline=time.monotonic()
    finally:
        if interactive:sys.stdout.write('\x1b[0m\x1b[?25h\n');sys.stdout.flush()
        if record:record.close()
        if c.snapshot:save_snapshot(c.snapshot,w)
        if c.output:
            if c.output.lower().endswith('.ppm'):f.ppm(c.output)
            elif c.output.lower().endswith('.txt'):f.text(c.output)
            else:
                with open(c.output,'w',encoding='utf-8') as out:json.dump({'frame':w.frame,'time':w.t,'coherence':w.order,'glow':w.mean_energy,'agents':len(w.agents),'telemetry':w.telemetry},out,indent=2)
        if c.quiet or c.headless or c.command=='inspect':
            print(json.dumps({'frame':w.frame,'time':round(w.t,3),'coherence':round(w.order,5),'glow':round(w.mean_energy,5),'agents':len(w.agents)}))
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError) as exc:print(f'firefly: {exc}',file=sys.stderr);sys.exit(1)
