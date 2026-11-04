# t436: satellites per Starship vs packing pass (repo packer, layers arch). ESTIMATE. Measured points from box_gtc/results/t436/passes.jsonl
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
steps=["replica\nas-is","+ array leaf\n9 -> 4 mm","+ radiator pitch\n20 -> 10 mm","+ rack boxed,\nequip 800 kg/m3\n(adapter 0.15 m)","+ adapter\n0.10 m","+ adapter\n0.05 m"]
jun=[17,23,27,40,43,46]; aug=[12,16,17,27,28,30]
fig,ax=plt.subplots(figsize=(10,5.6)); x=range(len(steps))
ax.plot(x,jun,"o-",c="#d9822b",lw=2.2,label="June build (150 kW, 2.13 t)"); ax.plot(x,aug,"s-",c="#2b6fb5",lw=2.2,label="August build (250 kW, 3.27 t)")
ax.axhline(46,c="#d9822b",ls="--",lw=1); ax.axhline(30,c="#2b6fb5",ls="--",lw=1)
ax.text(0.02,46.8,"mass ceiling 46 (98 t / 2.13 t)",color="#d9822b",fontsize=9); ax.text(0.02,30.8,"mass ceiling 30 (98 t / 3.267 t)",color="#2b6fb5",fontsize=9)
for a,b in zip(x,jun): ax.annotate(b,(a,b),textcoords="offset points",xytext=(0,7),ha="center",fontsize=9)
for a,b in zip(x,aug): ax.annotate(b,(a,b),textcoords="offset points",xytext=(0,-14),ha="center",fontsize=9)
ax.plot([3.8],[45],"^",c="#555",ms=8); ax.annotate("alt. route: adapter 0.15 m,\nleaf 2 mm, rpitch 5 mm: 45 / 33",(3.8,45),xytext=(1.2,52),fontsize=8,arrowprops=dict(arrowstyle="->",lw=.6))
ax.set_xticks(list(x)); ax.set_xticklabels(steps,fontsize=8); ax.set_ylabel("satellites per Starship (repo packer)"); ax.set_ylim(0,58)
ax.set_title("Closing the packing gap: cumulative levers, each pass built on the last\nESTIMATE; 2020 Users Guide 8 m envelope, 17.24 m; 98 t mass limit; loads and deployment not yet sized",fontsize=10)
ax.legend(loc="lower right"); ax.grid(alpha=.25); fig.tight_layout(); fig.savefig("figures/fig_t436_sats_vs_pass.png",dpi=170); print("ok")
