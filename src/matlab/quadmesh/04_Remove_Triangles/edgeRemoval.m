function [Domain,newMesh]	= edgeRemoval(Domain,newMesh,tElemID,tEdgeIDs,...
    tEdge2VertIDs,itbEdgeIDs)
%EDGEREMOVAL Remove edge of triangle on layer boundary.
%
%
%   See also: EDGEBISECTION, EDGEINSERTION, REMOVETRIANGLESFUN.
%==========================================================================

% Compute midpoint coordinate of tElemID's boundary edge.
[x,y,z]	= Domain.edgeMidpoint(tEdgeIDs(itbEdgeIDs));

% Identify verts on boundary.
tbVertIDs   = tEdge2VertIDs(itbEdgeIDs,:);

% Identify quads in newMesh sharing tbVertIDs on "side 2" of tri.
adjQuadIDs2	= find(sum(ismember(newMesh.ConnectivityList,tbVertIDs(2)),2) > 0);

% Change coordinates of "side 1" tbVertID to [x,y,z].
Domain.Points(tbVertIDs(1),:)   = [x y z];

% Replace vert on "side 2" of tbVertID with "side 1" of tbVertID in quads.
% Quads on "side 2" of tbVertID now are adjacent to "side 1" tbVertID.
Domain.ConnectivityList(ismember(Domain.ConnectivityList,tbVertIDs(2))) = tbVertIDs(1);
oldQuadConn	= newMesh.ConnectivityList(adjQuadIDs2,:);
oldQuadConn(ismember(oldQuadConn,tbVertIDs(2))) = tbVertIDs(1);
newMesh.ConnectivityList(adjQuadIDs2,:)	= oldQuadConn;

% In Domain.Layers, remove tElemID from OE list for boundary layer..
Domain.Layers.OE{1}(ismember(Domain.Layers.OE{1},tElemID))	= [];

% Flag tElemID in Domain.ConnectivityList.
% Domain.ConnectivityList(tElemID,:)  = 0;

% Do a really inefficient update of the Domain adjacency lists.
Domain.nEdges   = Domain.nEdges - 1;                % Only removed 1 edge.
Domain.nElems   = size(Domain.ConnectivityList,1);
Domain.nVerts   = Domain.nVerts;
Domain  = Domain.buildAdjacencies;

% %%% For real-time plotting: show new conn of tris in iLayer-1.
% if plotProgress
%     Domain.plot(newElemIDs,'elemcolor','w');
% end

