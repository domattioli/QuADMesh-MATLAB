function [CM,removedVertIDs]	= DoubletCollapse(CM,removedVertIDs)
%DOUBLETCOLLAPSE collapses all concave quads in mesh.
%	CM = DOUBLETCOLLAPSE(CM) returns updated CM without any concave quads.
%
%   See also: POSTPROCESSROUTINE.
%==========================================================================

% Identify interior valence-2 vertices.
iT	= CM.elemType;                                  % Get indices to tris, quads.
bEdgeIDs	= CM.boundaryEdges;                     % Get boundary edges.
bVertIDs    = CM.edge2Vert(bEdgeIDs);               % VertIDs of ^.
intVertIDs  = setdiff((1:CM.nVerts)',bVertIDs);
intVertIDs(ismember(intVertIDs,removedVertIDs))	= [];
valence_intVertIDs  = CM.vert2Elem('VertIDs',intVertIDs);
ivalence2VertID	= cellfun(@length,valence_intVertIDs) == 2;

% Get elems adjacent to valence-2 vertices.
vert2ElemID = horzcat(valence_intVertIDs{ivalence2VertID})';
valence2VertID    = intVertIDs(ivalence2VertID); 	% Index to CM.

% Filter out any verts made eligible by triangular elems.
vert2ElemID(ismember(vert2ElemID,iT))   = 0;

% Identify eligible verts and their adjacent elems.
eligibleVertIDs	= sum(vert2ElemID > 0,2) == 2;
vert2ElemID	= vert2ElemID(eligibleVertIDs,:);
valence2VertID	= valence2VertID(eligibleVertIDs);
if isempty(valence2VertID)
    return
end

% Keep track of vertices removed from mesh.
removedVertIDs  = [removedVertIDs; zeros(length(valence2VertID),1)];
iremovedVertIDs = find(removedVertIDs == 0,1,'first');
removedVertIDs(iremovedVertIDs:end)  = valence2VertID(eligibleVertIDs);

% Merge concave quad with convex quad neighbor for each removedVertID.
CM.ConnectivityList(vert2ElemID(:,1),:)	= DoubletCollapseSubRoutine(CM,valence2VertID,vert2ElemID);
CM.ConnectivityList(vert2ElemID(:,2),:)	= 0;

% Update output.
removedVertIDs(removedVertIDs == 0)	= [];
[~,CM,] = CM.isPolyCCW('index',vert2ElemID(:,1));
CM  = CHILmesh(CM.ConnectivityList(sum(CM.ConnectivityList,2) ~= 0,:),CM.Points,CM.GridName);
end

%% Actual Operation of Doublet Collapse Function.
function Elem2VertIDs	= DoubletCollapseSubRoutine(CM,VertIDs,Vert2ElemIDs)
%DOUBLETCOLLAPSESUBROUTINE Removes the 2 edges common to an adjacent concave-convex quad pair.
%   
%   See also: DOUBLETCOLLAPSE.
%==========================================================================

% Get connectivity of both quads in each eligible operation.
Elem2VertIDs1    = CM.ConnectivityList(Vert2ElemIDs(:,1),:);
Elem2VertIDs2    = CM.ConnectivityList(Vert2ElemIDs(:,2),:);

% Index to valence-2 vert(s) for each quad in 1st set.
iElem2VertIDs1	= Elem2VertIDs1 == repmat(uint32(VertIDs),1,4);

% Index to unique vert(s) of each quad in 2nd set.
iElem2VertIDs2  = zeros(size(iElem2VertIDs1));
for jdx = 1:4
    iElem2VertIDs2  = iElem2VertIDs2 + (Elem2VertIDs1(:,jdx) == Elem2VertIDs2);
end
iElem2VertIDs2	= iElem2VertIDs2 == 0;

% Replace VertIDs (valence-2 vert(s)) in 1st quad with the unique vert of 2nd.
Elem2VertIDs    = Elem2VertIDs1';
Elem2VertIDs2   = Elem2VertIDs2';
Elem2VertIDs(iElem2VertIDs1')	= Elem2VertIDs2(iElem2VertIDs2');
Elem2VertIDs    = Elem2VertIDs';
end


