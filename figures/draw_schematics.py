"""Draw the five transfer schematics directly as embedded-font vector PDFs.

Matplotlib supplies the STIX font family. No TeX process or measured data is
used: these diagrams depict the manuscript's fixed definitions and example.
"""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

plt.rcParams.update({"font.family":"STIXGeneral","mathtext.fontset":"stix",
                     "font.size":9,"pdf.fonttype":42,"ps.fonttype":42})
META={"Creator":"Python vector renderer","Author":"","CreationDate":None,"ModDate":None}
def canvas(size,ylim):
    fig,ax=plt.subplots(figsize=size)
    fig.subplots_adjust(left=.025,right=.975,bottom=.035,top=.965)
    ax.set(xlim=(0,10),ylim=ylim);ax.set_axis_off()
    return fig,ax
def box(ax,x,y,w,h,text):
    ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle="round,pad=.025",
                  facecolor="white",edgecolor="black",linewidth=.7,zorder=3))
    ax.text(x,y,text,ha="center",va="center",zorder=4)
def arrow(ax,start,end,label=None,at=None,dash=False):
    ax.add_patch(FancyArrowPatch(start,end,arrowstyle="-|>",mutation_scale=9,
                  lw=.7,linestyle="--" if dash else "-",color="black"))
    if label:ax.text(*at,label,ha="center",va="center",
                    bbox=dict(facecolor="white",edgecolor="none",pad=1))
def save(fig,ax,out,name):
    fig.canvas.draw()
    for t in ax.texts:
        b=t.get_window_extent()
        if b.x0<fig.bbox.x0-1 or b.y0<fig.bbox.y0-1 or b.x1>fig.bbox.x1+1 or b.y1>fig.bbox.y1+1:
            raise ValueError("Label outside canvas: "+t.get_text())
    fig.savefig(out/(name+".pdf"),metadata=META);plt.close(fig)
def protocol(out):
    fig,ax=canvas((5.4,3.1),(-.3,6.2))
    box(ax,2.3,5.2,3.6,.95,"Running equality join\nRetained occurrences $L,R$")
    box(ax,7.2,5.2,3.6,.95,"Quiescent barrier\nFrontier $E$, sink $S$")
    box(ax,2.3,2.9,3.6,.95,"Fixed hierarchy $T$\nSparse exact optimizer")
    box(ax,7.2,2.9,3.6,.95,"Separate checker\nPacket and certificate")
    box(ax,4.9,.95,5.1,.9,"Sequential install, then resume\ninsertions and acknowledgments")
    arrow(ax,(4.15,5.2),(5.35,5.2),"stop",(4.75,5.65))
    ax.plot([7.2,7.2,2.3],[4.7,4.05,4.05],color="black",lw=.7)
    arrow(ax,(2.3,4.05),(2.3,3.43))
    ax.text(3.1,4.42,"Trusted snapshot",ha="center")
    arrow(ax,(4.15,2.9),(5.35,2.9),"candidate",(4.75,3.38))
    arrow(ax,(7.2,2.4),(6.3,1.43),"accept",(7.8,1.85))
    ax.plot([9.05,9.65,9.65],[2.9,2.9,5.2],color="black",lw=.7,ls="--")
    arrow(ax,(9.65,5.2),(9.05,5.2),dash=True)
    ax.text(9.55,3.95,"reject",rotation=90,ha="right",va="center")
    ax.text(2.2,1.9,"Rejection keeps source installed",ha="center",fontsize=8)
    ax.text(5,-.03,"Sink + pending = full join; each matching pair has one owner",ha="center",fontsize=8)
    save(fig,ax,out,"protocol")
def running(out):
    fig,ax=canvas((5.4,2.9),(-1.3,4.2))
    for x,t in [(1.65,"Frontier"),(5.0,"Trusted hierarchy"),(8.4,"One exact packet")]:
        ax.text(x,3.8,t,ha="center",fontweight="bold")
    pending={(0,0),(0,1),(0,3),(1,0),(1,1),(2,0),(2,2),(2,3),(3,0),(3,2)}
    for j,c in enumerate("abcde"):ax.text(.58+.48*j,3.25,c,ha="center")
    for i in range(4):
        ax.text(.18,2.8-.58*i,f"$x_{i+1}$",ha="right",va="center")
        for j in range(5):
            ax.add_patch(Rectangle((.34+.48*j,2.51-.58*i),.48,.58,fill=False,edgecolor=".55",lw=.4))
            ax.text(.58+.48*j,2.8-.58*i,"•" if (i,j) in pending else "×",
                    color="black" if (i,j) in pending else ".55",ha="center",va="center")
    nodes={ "1234":(5,3.05),"12":(4.15,2.05),"34":(5.85,2.05),
            "1":(3.72,1.05),"2":(4.58,1.05),"3":(5.42,1.05),"4":(6.28,1.05)}
    for a,b in [("1234","12"),("1234","34"),("12","1"),("12","2"),("34","3"),("34","4")]:
        ax.plot([nodes[a][0],nodes[b][0]],[nodes[a][1],nodes[b][1]],color="black",lw=.7)
    for n,(x,y) in nodes.items():box(ax,x,y,.7 if len(n)>1 else .43,.4,n)
    box(ax,8.35,2.05,3.1,2.5,"{1,2,3,4} × {a}\n{1,2} × {b}\n{3,4} × {c}\n{1} × {d}\n{3} × {d}")
    ax.text(1.5,-.1,"• pending; × acknowledged\nColumn e is fully acknowledged",ha="center",va="center",fontsize=8)
    ax.text(5,-.1,"Each row factor is a node;\ncolumn factors are arbitrary subsets",ha="center",va="center",fontsize=8)
    ax.text(8.35,-.1,"Ten pending pairs,\neach represented once",ha="center",va="center",fontsize=8)
    save(fig,ax,out,"running-example")
def observers(out):
    fig,ax=canvas((5.4,1.6),(-.3,2.7))
    box(ax,5,2.1,3.2,.7,"Exact coefficients\nin $\\mathbb{N}[X,Y]$")
    for x,t in [(1.65,"Boolean support\nPair exists?"),(5,"Total count\nSum of coefficients"),(8.35,"Participating IDs\nVariable appears?")]:
        box(ax,x,.35,2.95,.7,t)
        arrow(ax,(5,1.72),(x,.75))
    save(fig,ax,out,"observer-controls")
def recurrence(out):
    fig,ax=canvas((5.4,2.5),(-.5,4.7))
    box(ax,5,3.95,4,1.2,"Node $v$ receives inherited set $K$\nWeight $k=\\sum_{j\\in K}b_j$")
    box(ax,5,2.6,2.3,.65,"Activate $v$?")
    arrow(ax,(5,3.30),(5,2.96))
    box(ax,2.5,1.2,4.3,.8,"Emit $(A_v,K)$\nChild $c$ receives $Q_c$")
    box(ax,7.5,1.2,4.3,.8,"Emit nothing at $v$\nChild $c$ receives $K\\cup Q_c$")
    arrow(ax,(4.2,2.24),(2.9,1.65),"yes: $k>0$",(2.65,2.3))
    arrow(ax,(5.8,2.24),(7.1,1.65),"no",(7.4,2.3))
    ax.text(2.5,.15,"$(\\alpha_v+k,1)+\\sum_cF_c(q_c)$",ha="center")
    ax.text(7.5,.15,"$\\sum_cF_c(k+q_c)$",ha="center")
    save(fig,ax,out,"recurrence")
def certificate(out):
    fig,ax=canvas((5.4,3),(-.6,5.6))
    box(ax,2.5,4.9,4,.8,"Trusted barrier context\n$A,B,E,T,a,b,h$")
    box(ax,7.5,4.9,4,.8,"Untrusted transfer\nBlocks, tree IDs, table, decisions")
    steps=[(3.5,"Validate source and tree; recompute Bad, $Q,q,\\alpha$"),
           (2.35,"Check exact reachable recurrence closure"),
           (1.2,"Reconstruct blocks; compare members, decisions and cost"),
           (.05,"Accept, then install by one sequential assignment")]
    for y,t in steps:box(ax,5,y,8.2,.68,t)
    arrow(ax,(2.5,4.47),(3.5,3.88));arrow(ax,(7.5,4.47),(6.5,3.88))
    for a,b in zip(steps,steps[1:]):arrow(ax,(5,a[0]-.37),(5,b[0]+.37))
    save(fig,ax,out,"certificate")
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--outdir",type=Path,required=True)
    a=ap.parse_args();a.outdir.mkdir(parents=True,exist_ok=True)
    for draw in [protocol,running,observers,recurrence,certificate]:draw(a.outdir)
    print("Five direct embedded-font vector schematics generated.")
if __name__=="__main__":main()
