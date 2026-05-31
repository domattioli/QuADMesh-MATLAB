function [Domain,newMesh] = removeTrianglesFun(CM,Domain,subDomain,newMesh,...
    canRemoveEdges,iLayer,remainingElemIDs,bEdgeIDs,bVertIDs,plotProgress)
%REMOVETRIANGLESFUN Removes triangles remaining in Domain's iLayer.
%   [Domain,newMesh]	= removeTrianglesFun(CM,Domain,subDomain,newMesh,...
%   canRemoveEdges,iLayer,remainingElemIDs,idx_remainingElemIDs,...
%   ElemIDs,VertIDs,bEdgeIDs,bVertIDs,plotProgress) returns _
%
%   See also: EDGEBISECTION, EDGEINSERTION, EDGEREMOVAL, TRI2QUADROUTINE.
%==========================================================================

% Functionality of triangle removal operation depends on layer of mesh.
if iLayer == 1 && CM.nLayers == Domain.nLayers
    onMeshBoundary	= true;
else
    onMeshBoundary	= false;
end
% and depends on whether the user will allow removal of mesh boundary edges.

% Loop through each remaining tri and determine the function neccessary for
% converting the tri into a quad or remove it from the mesh entirely.
ibEdgeIDs	= 1:3;                                  % Index to edges of tri.
for idx	= 1:length(remainingElemIDs)
    % Get triangle adjacencies, index them wrt to Domain.
    tElemID = remainingElemIDs(idx);                % Indexed wrt Domain.
    tConn	= Domain.ConnectivityList(tElemID,:);	% Connectivity of tri.
    tEdgeIDs= Domain.elem2Edge(tElemID)';           % Edges of tri.
    tEdge2VertIDs	= Domain.edge2Vert(tEdgeIDs);	% Verts of ^.
    tElem2ElemIDs	= Domain.edge2Elem(tEdgeIDs); 	% Neighbors of tri.
%         if any(CM.Points(tConn,1) < -91.14) &&...
%                 any(CM.Points(tConn,1) > -91.148) &&...
%                 any(CM.Points(tConn,2) < 29.21) &&...
%                 any(CM.Points(tConn,1) < 29.206)
%             idx
%             poo=1;
%         end
%         if any(CM.Points(tConn,1) < -90.8) &&...
%                 any(CM.Points(tConn,1) > -91) &&...
%                 any(CM.Points(tConn,2) > 29.15) &&...
%                 any(CM.Points(tConn,1) < 29.25)
%             Domain.plotElem(tElemID,'color','g');
%             idx
%             
%         end
    % Get number of boundary edges attached to tri.
    itbEdgeIDs	= ibEdgeIDs(sum(reshape(ismember(...
        [tEdge2VertIDs; fliplr(tEdge2VertIDs)],subDomain.edge2Vert(bEdgeIDs),...
        'rows'),3,2),2) > 0);
    n_edges	= numel(itbEdgeIDs);
    
    % Accomodation is based on number of triangle's edges on boundary.
    %%% Edge Bisection ----------------------------------------------------
    if onMeshBoundary && n_edges == 1 && ~canRemoveEdges
        % Project a new point from boundary to form a quad.
        [Domain,newMesh] = edgeBisection(1,Domain,newMesh,iLayer,...
            tElemID,tConn,tEdgeIDs,tEdge2VertIDs,tElem2ElemIDs,itbEdgeIDs);
        
    elseif ~onMeshBoundary && n_edges >= 1
        % Bisect one of the tris edges. None are on the mesh boundary.
        [Domain,newMesh] = edgeBisection(2,Domain,newMesh,iLayer,...
            tElemID,tConn,tEdgeIDs,tEdge2VertIDs,tElem2ElemIDs,itbEdgeIDs);
        
    %%% Edge Insertion ----------------------------------------------------
    elseif onMeshBoundary && n_edges == 0
        % Insert edge at lone point on mesh boundary to split tri into quad.
        [Domain,newMesh] = edgeInsertion(1,Domain,newMesh,iLayer,...
            tElemID,tConn,bVertIDs,plotProgress);
        
    elseif ~onMeshBoundary && n_edges == 0
        % Insert edge at lone point on mesh boundary to split tri into quad.
        [Domain,newMesh] = edgeInsertion(2,Domain,newMesh,iLayer,...
            tElemID,tConn,bVertIDs,plotProgress);
        
    elseif onMeshBoundary && ismember(n_edges,[2 3])
        % Insert edge at point common to both mesh boundary edges to split tri into quad.
        [Domain,newMesh] = edgeInsertion(3,Domain,newMesh,iLayer,...
            tElemID,tConn,bVertIDs,plotProgress);
        
    %%% Edge Removal ------------------------------------------------------
    elseif onMeshBoundary && n_edges == 1 && canRemoveEdges
        %%% Only one edge on the mesh boundary and the user will allow for
        %%% the removal of edgesl therefore this triangle is squeezed out.
        [Domain,newMesh] = edgeRemoval(Domain,newMesh,tElemID,tEdgeIDs,...
            tEdge2VertIDs,itbEdgeIDs);
    else
        errordlg('impossible criterion in removeTrianglesFun?');
    end
end
