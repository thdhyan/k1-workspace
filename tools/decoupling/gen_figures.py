import sys
PAPER="#2d3142"; INK="#f5f5f5"; MUTED="#bfc0c0"; SOFT="#949eb2"; ACC="#f08a59"; ACCT="rgba(240,138,89,0.10)"; LINK="#739fdf"
MONO="'Geist Mono', monospace"; SANS="'Geist', sans-serif"
SER={"s1":"#9caf8f","s2":"#82a0c0","s3":"#d3ad7a","s4":"#b88670"}

def defs():
    m=lambda i,c:f'<marker id="{i}" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{c}"/></marker>'
    return "<defs>"+m("arrow",MUTED)+m("arrow-accent",ACC)+m("arrow-link",LINK)+"</defs>"

def node(x,y,tag,fanin,name,sub,kind="int"):
    w,h=160,56
    if kind=="int": fill,stroke,sw="rgba(245,245,245,0.04)",INK,1
    elif kind=="leaf": fill,stroke,sw="rgba(245,245,245,0.05)",MUTED,0.8
    elif kind=="ext": fill,stroke,sw="rgba(245,245,245,0.03)","rgba(245,245,245,0.30)",1
    elif kind=="focal": fill,stroke,sw=ACCT,ACC,1.2
    tw=max(28,len(tag)*6+10)
    s=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{PAPER}"/>'
    s+=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"' + (' stroke-dasharray="4,3"' if kind=="ext" else '') + '/>'
    s+=f'<rect x="{x+8}" y="{y+6}" width="{tw}" height="12" rx="2" fill="transparent" stroke="rgba(245,245,245,0.40)" stroke-width="0.8"/>'
    s+=f'<text x="{x+8+tw/2}" y="{y+15}" fill="{INK}" font-size="7" font-family="{MONO}" text-anchor="middle" letter-spacing="0.08em">{tag}</text>'
    if fanin is not None:
        s+=f'<rect x="{x+w-36}" y="{y+8}" width="28" height="12" rx="2" fill="transparent" stroke="rgba(245,245,245,0.40)" stroke-width="0.8"/>'
        s+=f'<text x="{x+w-22}" y="{y+17}" fill="{INK}" font-size="8" font-family="{MONO}" text-anchor="middle">{fanin} IN</text>'
    s+=f'<text x="{x+w/2}" y="{y+34}" fill="{INK}" font-size="12" font-weight="600" font-family="{SANS}" text-anchor="middle">{name}</text>'
    s+=f'<text x="{x+w/2}" y="{y+50}" fill="{SOFT}" font-size="9" font-family="{MONO}" text-anchor="middle">{sub}</text>'
    return s

def path(d,accent=False,dash=False):
    c=ACC if accent else MUTED; mk="arrow-accent" if accent else "arrow"
    da=' stroke-dasharray="5,4"' if dash else ''
    return f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{1.2 if accent else 1}"{da} marker-end="url(#{mk})"/>'

def label(cx,cy,text,accent=False,anchor="middle"):
    w=len(text)*5.4+10
    x = cx-w/2 if anchor=="middle" else (cx-w if anchor=="end" else cx)
    tx = cx if anchor=="middle" else (cx-5 if anchor=="end" else cx+5)
    return (f'<rect x="{x:.0f}" y="{cy-6}" width="{w:.0f}" height="12" rx="2" fill="{PAPER}"/>'
            f'<text x="{tx}" y="{cy+3}" fill="{ACC if accent else MUTED}" font-size="8" font-family="{MONO}" text-anchor="{anchor}" letter-spacing="0.06em">{text}</text>')

def legend(y,items,tail=""):
    s=f'<line x1="40" y1="{y-20}" x2="960" y2="{y-20}" stroke="rgba(245,245,245,0.12)"/>'
    x=40
    for kind,txt in items:
        if kind in("int","leaf","ext","focal"):
            st={"int":(INK,"rgba(245,245,245,0.04)",""),"leaf":(MUTED,"rgba(245,245,245,0.05)",""),"ext":("rgba(245,245,245,0.30)","rgba(245,245,245,0.03)",' stroke-dasharray="4,3"'),"focal":(ACC,ACCT,"")}[kind]
            s+=f'<rect x="{x}" y="{y-6}" width="20" height="12" rx="2" fill="{st[1]}" stroke="{st[0]}"{st[2]}/>'
        elif kind=="arrow": s+=f'<line x1="{x}" y1="{y}" x2="{x+20}" y2="{y}" stroke="{MUTED}" marker-end="url(#arrow)"/>'
        elif kind=="cycle": s+=f'<line x1="{x}" y1="{y}" x2="{x+20}" y2="{y}" stroke="{ACC}" stroke-dasharray="5,4" stroke-width="1.2" marker-end="url(#arrow-accent)"/>'
        elif kind.startswith("s") or kind=="acc":
            c=ACC if kind=="acc" else SER[kind]
            s+=f'<rect x="{x}" y="{y-4}" width="16" height="8" fill="{c}" fill-opacity="0.22" stroke="{c}"/>'
        s+=f'<text x="{x+28}" y="{y+3}" fill="{MUTED}" font-size="9" font-family="{MONO}">{txt}</text>'
        x+=28+len(txt)*5.6+28
    if tail: s+=f'<text x="960" y="{y+4}" fill="{MUTED}" font-size="13" font-style="italic" font-family="\'Instrument Serif\', serif" text-anchor="end">{tail}</text>'
    return s

def svg(slug,title,desc,w,h,body):
    return (f'<div class="diagram-container"><svg viewBox="0 0 {w} {h}" style="min-width:{w}px" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{slug}-title {slug}-desc">'
            f'<title id="{slug}-title">{title}</title><desc id="{slug}-desc">{desc}</desc>{defs()}<rect width="100%" height="100%" fill="{PAPER}"/>{body}</svg></div>')

# ---------- Fig 1: current ----------
b=""
b+=path("M540,96 V120 Q540,128 548,128 H732 Q740,128 740,136 V160")          # ros->isaac
b+=path("M580,68 H740")                                                       # ros->teleop
b+=path("M820,96 V280")                                                       # teleop->models
b+=path("M180,96 V136 Q180,144 188,144 H672 Q680,144 680,152 V160")           # tests->isaac
b+=path("M380,180 H620")                                                      # scripts->isaac
b+=path("M620,200 H380",accent=True,dash=True)                                # isaac->scripts (cycle)
b+=path("M660,216 V240 Q660,248 652,248 H528 Q520,248 520,256 V280")          # isaac->mjlab
b+=path("M300,216 V248 Q300,256 308,256 H452 Q460,256 460,264 V280")          # scripts->mjlab
b+=path("M760,216 V280")                                                      # isaac->models
b+=path("M580,308 H672 a8,8 0 0,1 16,0 H740")                                 # mjlab->models (hop)
b+=path("M500,336 V360 Q500,368 508,368 H632 Q640,368 640,376 V400")          # mjlab->desc
b+=path("M680,216 V400")                                                      # isaac->desc
b+=label(500,166,"IMPORT · 49 SH")
b+=label(500,214,"CYCLE",accent=True)
b+=label(420,132,"23 TESTS")
b+=label(828,184,"PATH REFS",anchor="start")
b+=label(590,236,"USD + IK")
b+=node(100,40,"TEST",0,"tests/","28 py · 3 sys.path")
b+=node(420,40,"ROS",0,"src/k1_*","9 colcon pkgs")
b+=node(740,40,"APP",1,"k1_teleop/","own URDF copy")
b+=node(220,160,"OPS",1,"scripts/","113 sh · 18 py")
b+=node(620,160,"TRAIN",3,"isaac_tasks/","17 sys.path hacks")
b+=node(420,280,"TRAIN",2,"mjlab_k1/","59 files untracked")
b+=node(740,280,"DATA",3,"models/","1.3 GB · 53 untracked","leaf")
b+=node(600,400,"DATA",2,"k1_description","assets submodule","leaf")
b+=legend(510,[("int","package"),("leaf","data / leaf"),("arrow","depends on"),("cycle","back-edge")],"Fan-in counts drawn edges only.")
fig1=svg("current","booster_ws today: coupled dependency graph","Dependency graph of booster_ws today: isaac_tasks and scripts depend on each other in a cycle, and ROS packages, tests and scripts reach into training code.",1000,540,b)

# ---------- Fig 2: target ----------
b=""
b+=path("M180,96 V160")                                                       # ops->isaac
b+=path("M220,80 H392 Q400,80 400,88 V160")                                   # ops->mjlab
b+=path("M220,216 V280")                                                      # isaac->policies
b+=path("M420,216 V240 Q420,248 412,248 H288 Q280,248 280,256 V280")          # mjlab->policies
b+=path("M260,216 V224 Q260,232 268,232 H412 a8,8 0 0,1 16,0 H472 Q480,232 480,240 V280")  # isaac->core (hop)
b+=path("M500,216 V280")                                                      # mjlab->core
b+=path("M560,96 V280")                                                       # ros->core
b+=path("M740,68 H608 Q600,68 600,76 V280")                                   # teleop->core
b+=path("M820,216 V300 Q820,308 812,308 H620")                                # ext->core
b+=path("M540,336 V400")                                                      # core->desc
b+=label(310,68,"LAUNCH JOB")
b+=label(212,256,"EXPORT ONNX",anchor="end")
b+=label(552,120,"MANIFEST",anchor="end")
b+=label(720,320,"PIP PIN")
b+=node(60,40,"OPS",0,"k1_ops","hosts · jobs · docker")
b+=node(420,40,"ROS",0,"k1_ros","src/k1_* + deploy")
b+=node(740,40,"APP",0,"k1_teleop","VR / XR teleop")
b+=node(140,160,"TRAIN",1,"k1_train_isaac","isaac_tasks + compass")
b+=node(380,160,"TRAIN",1,"k1_train_mjlab","mjlab_k1 src + cli")
b+=node(740,160,"REPO",0,"split repos","k1_chat · k1m","ext")
b+=node(140,280,"DATA",2,"k1_policies","ONNX + manifest","leaf")
b+=node(460,280,"CORE",5,"k1_core","joints · gains · obs IO","focal")
b+=node(460,400,"DATA",1,"k1_description","URDF · MJCF · USD","leaf")
b+=legend(510,[("focal","shared contract"),("int","package"),("leaf","data"),("ext","own repo"),("arrow","depends on")],"No cycles. Only k1_core is shared.")
fig2=svg("target","booster_ws decoupled: hybrid target layout","Target layout: every package depends downward on k1_core and k1_description only; training writes exported policies, k1_chat and k1m live in their own repos and pin k1_core.",1000,540,b)

# ---------- Fig 3: radar ----------
import math
cx,cy,R=500,240,160
axes=["Fan-out","Joint copies","Path refs","sys.path","Untracked"]
def pt(i,v): a=-math.pi/2+2*math.pi*i/5; return (cx+v/10*R*math.cos(a), cy+v/10*R*math.sin(a))
def poly(vals): return " ".join(f"{x:.0f},{y:.0f}" for x,y in (pt(i,v) for i,v in enumerate(vals)))
b=""
for f in (0.2,0.4,0.6,0.8,1.0):
    op="0.20" if f==1.0 else "0.10"
    b+=f'<polygon points="{poly([f*10]*5)}" fill="none" stroke="rgba(245,245,245,{op})"/>'
for i in range(5):
    x,y=pt(i,10); b+=f'<line x1="{cx}" y1="{cy}" x2="{x:.0f}" y2="{y:.0f}" stroke="rgba(191,192,192,0.25)"/>'
for i,a in enumerate(axes):
    x,y=pt(i,11); anc="middle" if i==0 else ("start" if i in(1,2) else "end")
    yy = y-4 if i==0 else (y+10 if i in (2,3) else y+4)
    b+=f'<text x="{x:.0f}" y="{yy:.0f}" fill="{INK}" font-size="11" font-weight="600" font-family="{SANS}" text-anchor="{anc}">{a}</text>'
for v in (2,4,6,8,10):
    b+=f'<text x="{cx-6}" y="{cy-v*16+3}" fill="{MUTED}" font-size="8" font-family="{MONO}" text-anchor="end">{v}</text>'
series=[("s3","ROS src/",[5,10,1.7,1.2,0]),("s2","mjlab_k1/",[3.8,3.6,0.8,4.1,10]),("s1","isaac_tasks/",[6.3,6.4,3.6,10,1.0]),("s4","scripts/",[10,7.3,10,0.6,3.9])]
for k,n,v in series:
    c=SER[k]; b+=f'<polygon points="{poly(v)}" fill="{c}" fill-opacity="0.22" stroke="{c}" stroke-width="1.5"/>'
tgt=[2.5,0,0,0,0]
b+=f'<polygon points="{poly(tgt)}" fill="{ACC}" fill-opacity="0.22" stroke="{ACC}" stroke-width="1.8"/>'
for i,v in enumerate(tgt):
    x,y=pt(i,v); b+=f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3" fill="{ACC}"/>'
b+=legend(450,[("s1","isaac_tasks/"),("s2","mjlab_k1/"),("s3","ROS src/"),("s4","scripts/"),("acc","target pkg")],"Lower is better. Each axis scaled to its max.")
fig3=svg("coupling","Coupling profile per component","Radar of five coupling metrics for four current components versus the target package profile; scripts and isaac_tasks are the most coupled.",1000,480,b)

tpl=open(sys.argv[1]).read()
open(sys.argv[2],"w").write(tpl.replace("{{FIG1}}",fig1).replace("{{FIG2}}",fig2).replace("{{FIG3}}",fig3))
