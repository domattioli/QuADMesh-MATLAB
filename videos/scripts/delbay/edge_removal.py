import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPLPolygon
from matplotlib.collections import LineCollection
import pathlib
from PIL import Image
from quadmesh.tri2quad import tri2quad_routine
from chilmesh import CHILmesh

d = np.load("delbay_stages.npz")
frames = d["frames"]; simplices = d["simplices"]; ring = d["ring"]
final_tri = frames[-1]  # final smoothed positions

# Re-run tri2quad WITHOUT boundary removal → preserves original node indices
tri_mesh = CHILmesh(points=final_tri, connectivity=simplices)
quad_mesh = tri2quad_routine(tri_mesh, remove_boundary_tris=False, method="matching")
quad_conn = np.asarray(quad_mesh.connectivity_list, dtype=int)

# Separate quads (4 distinct) from padded tris
quads = []
leftover_tris = []
for row in quad_conn:
    u = list(dict.fromkeys(row.tolist()))  # unique preserving order
    if len(u) == 4:
        quads.append(u)
    elif len(u) == 3:
        leftover_tris.append(u)
quads = np.array(quads)
print(f"quads: {len(quads)}, leftover tris: {len(leftover_tris)}")
print(f"nodes preserved: {len(quad_mesh.points)} (tri had {len(final_tri)})")

# Original tri edges
def edge_key(a,b): return (min(a,b),max(a,b))
tri_edge_set = set()
for s in simplices:
    for u,v in ((s[0],s[1]),(s[1],s[2]),(s[2],s[0])):
        tri_edge_set.add(edge_key(u,v))

# Quad perimeter edges (kept)
quad_edge_set = set()
for q in quads:
    for u,v in ((q[0],q[1]),(q[1],q[2]),(q[2],q[3]),(q[3],q[0])):
        quad_edge_set.add(edge_key(u,v))
for t in leftover_tris:
    for u,v in ((t[0],t[1]),(t[1],t[2]),(t[2],t[0])):
        quad_edge_set.add(edge_key(u,v))

# REMOVED edges = tri edges not in quad set = the diagonals fused away
removed_edges = np.array([list(e) for e in (tri_edge_set - quad_edge_set)])
kept_edges = np.array([list(e) for e in quad_edge_set])
print(f"removed diagonal edges: {len(removed_edges)}, kept: {len(kept_edges)}")

np.savez("edge_removal_data.npz",
         pts=quad_mesh.points[:,:2], quads=quads,
         leftover=np.array(leftover_tris) if leftover_tris else np.empty((0,3),int),
         removed=removed_edges, kept=kept_edges, simplices=simplices)
print("saved edge_removal_data.npz")
