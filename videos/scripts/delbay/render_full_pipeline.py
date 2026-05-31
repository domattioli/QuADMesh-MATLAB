import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPLPolygon
from matplotlib.collections import LineCollection
import pathlib
from PIL import Image

d = np.load("delbay_stages.npz")
frames = d["frames"]; simplices = d["simplices"]; ring = d["ring"]
n_relax = int(d["n_relax_frames"]); n_smooth = int(d["n_smooth_frames"])

e = np.load("edge_removal_data.npz")
qpts = e["pts"]; quads = e["quads"]; removed = e["removed"]; kept = e["kept"]
Np = len(qpts)
removed = removed[(removed[:,0]<Np)&(removed[:,1]<Np)]
kept = kept[(kept[:,0]<Np)&(kept[:,1]<Np)]

C_POOR=np.array([224,64,251])/255; C_MID=np.array([124,77,255])/255
C_GOOD=np.array([0,229,255])/255; C_COAST=np.array([74,163,223])/255
C_BG=np.array([14,17,23])/255

def qcol(q):
    return C_POOR+(C_MID-C_POOR)*(q/0.5) if q<0.5 else C_MID+(C_GOOD-C_MID)*((q-0.5)/0.5)

def triq(pts,s):
    a,b,c=pts[s[:,0]],pts[s[:,1]],pts[s[:,2]]
    ab=np.linalg.norm(b-a,axis=1);bc=np.linalg.norm(c-b,axis=1);ca=np.linalg.norm(a-c,axis=1)
    ar=0.5*np.abs((b[:,0]-a[:,0])*(c[:,1]-a[:,1])-(c[:,0]-a[:,0])*(b[:,1]-a[:,1]))
    ss=(ab+bc+ca)/2
    rin=np.divide(ar,ss,out=np.zeros_like(ar),where=ss>0)
    rout=np.divide(ab*bc*ca,4*ar,out=np.ones_like(ar),where=ar>0)
    return np.clip(np.divide(2*rin,rout,out=np.zeros_like(ar),where=rout>0),0,1)

def quadq_one(p):
    worst=0.0
    for i in range(4):
        a=p[(i-1)%4]-p[i];b=p[(i+1)%4]-p[i]
        na,nb=np.hypot(*a),np.hypot(*b)
        if na<1e-12 or nb<1e-12: return 0.0
        cos=np.clip(np.dot(a,b)/(na*nb),-1,1)
        worst=max(worst,abs(np.degrees(np.arccos(cos))-90))
    return max(0.0,1-worst/90)

allxy=frames.reshape(-1,2);lo=allxy.min(0);hi=allxy.max(0)
scale=6.4/(hi-lo)[1];center=(lo+hi)/2;offset=np.array([-1.7,-0.15])
def scn(p2):
    xy=(np.atleast_2d(p2)-center)*scale;o=np.zeros((len(xy),2));o[:,0]=xy[:,0]+offset[0];o[:,1]=xy[:,1]+offset[1];return o
sring=scn(ring)

outdir=pathlib.Path("frames_pipe");outdir.mkdir(exist_ok=True)
imgs=[]; fc=0
durs=[]

def save(fig,ax,dur):
    global fc
    ax.plot(sring[:,0],sring[:,1],color=C_COAST,linewidth=2)
    ax.set_xlim(-4,4);ax.set_ylim(-4,4);ax.axis('off')
    p=outdir/f"f_{fc:03d}.png";plt.savefig(p,dpi=80,bbox_inches='tight',facecolor=C_BG);plt.close()
    imgs.append(Image.open(p));durs.append(dur);fc+=1

# STAGE 1-3: tri evolution (sample every 2)
print("tri stages...")
for i in range(0,len(frames),2):
    fig,ax=plt.subplots(figsize=(10,8),facecolor=C_BG);ax.set_facecolor(C_BG);ax.set_aspect('equal')
    pts=frames[i];q=triq(pts,simplices);sp=scn(pts)
    for tri,qi in zip(simplices,q):
        ax.add_patch(MPLPolygon(sp[tri],closed=True,facecolor=qcol(float(qi)),edgecolor=C_BG,linewidth=0.4))
    lbl="1 · Initialized" if i<n_relax else ("3 · Smoothed" if i>=n_relax+n_smooth else "2 · Truss solver")
    ax.text(0.05,0.95,lbl,transform=ax.transAxes,color='white',fontsize=14,weight='bold')
    save(fig,ax,350)

# STAGE 4: edge removal on FIXED nodes (start from final smoothed tri)
print("edge removal...")
sp=scn(qpts)
quad_q=np.array([quadq_one(qpts[qd]) for qd in quads])
kept_lines=[(sp[a],sp[b]) for a,b in kept]
removed_lines=[(sp[a],sp[b]) for a,b in removed]
NER=16
for fi in range(NER):
    t=fi/(NER-1)
    fig,ax=plt.subplots(figsize=(10,8),facecolor=C_BG);ax.set_facecolor(C_BG);ax.set_aspect('equal')
    fill_op=0.35+0.43*t
    for qd,qi in zip(quads,quad_q):
        ax.add_patch(MPLPolygon(sp[qd],closed=True,facecolor=qcol(float(qi)),edgecolor='none',alpha=fill_op))
    ax.add_collection(LineCollection(kept_lines,colors=(*C_GOOD,0.3+0.5*t),linewidths=0.6))
    ra=max(0,1-t*1.2)
    if ra>0.02:
        ax.add_collection(LineCollection(removed_lines,colors=(*C_POOR,ra*0.8),linewidths=0.5))
    lbl=f"4 · Tri2Quad  ({t*100:.0f}%)" if 0.1<t<0.9 else ("3 · Smoothed" if t<=0.1 else "4 · Quads")
    ax.text(0.05,0.95,lbl,transform=ax.transAxes,color='white',fontsize=14,weight='bold')
    ax.text(0.05,0.90,"magenta = diagonal removed",transform=ax.transAxes,color=C_POOR,fontsize=9)
    save(fig,ax,300)

# Hold final
print("hold...")
for _ in range(4):
    fig,ax=plt.subplots(figsize=(10,8),facecolor=C_BG);ax.set_facecolor(C_BG);ax.set_aspect('equal')
    for qd,qi in zip(quads,quad_q):
        ax.add_patch(MPLPolygon(sp[qd],closed=True,facecolor=qcol(float(qi)),edgecolor=C_BG,linewidth=0.3))
    ax.text(0.05,0.95,"4 · Quads",transform=ax.transAxes,color='white',fontsize=14,weight='bold')
    save(fig,ax,650)

imgs[0].save("delbay_hero.gif",save_all=True,append_images=imgs[1:],duration=durs,loop=0)
import os
print(f"GIF {os.path.getsize('delbay_hero.gif')/1024:.0f}KB {len(imgs)}f")

import imageio.v2 as imageio
fl=sorted(outdir.glob("f_*.png"))
w=imageio.get_writer("delbay_hero.mp4",fps=5,codec='libx264',quality=8,macro_block_size=16)
for f in fl: w.append_data(imageio.imread(f))
w.close()
print(f"MP4 {os.path.getsize('delbay_hero.mp4')/1024:.0f}KB")
