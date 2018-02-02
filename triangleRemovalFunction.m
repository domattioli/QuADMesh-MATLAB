function [Domain,newMesh] = triangleRemovalFunction(Domain,newMesh,...
    remainingElemIDs,iLayer,VertIDs,bVertIDs)
%TRIANGLEREMOVALFUNCTION Summary of this function goes here
%   Detailed explanation goes here
%   
%   See also: EDGEINSERTION, EDGEREMOVAL, EDGEBISECTION, TRI2QUADROUTINE.
%==========================================================================

% Similar, but different functions used for mesh boundary.
if iLayer == 1 && 1 % Add conditional to determine whether we are on boundary.
    % Edge Insertion ------------------------------------------------------
    %%% 1. When only one point of tri is on mesh boundary.
    %%% 2. Or when two edges of a tri are on mesh boundary (don't want to
    %%% truncate tri).
    
    % Edge Removal --------------------------------------------------------
    %%% 1. When one edge of tri is on mesh boundary.
    
    % Edge Bisection ------------------------------------------------------
    %%% 1. When one edge of tri is on mesh boundary and the user does not
    %%% want to remove an edge so we can project a new point from the
    %%% boundary to convert this tri into a quad.
    
else                                                % Not on mesh boundary.
    for idx	= 1:length(remainingElemIDs)
        % Get triangle.
        triElemID	= remainingElemIDs(idx);     	% Indexed wrt Domain.
        triEdgeIDs  = Domain.elem2Edge(triElemID)';
        triEdge2Vert	= Domain.edge2Vert(triEdgeIDs);
        triElem2Vert    = Domain.ConnectivityList(triElemID,:);
        triElem2Elem    = Domain.edge2Elem(triEdgeIDs);
        
        % Accomodation is based on number of triangle's edges on boundary.
        i_tribVertIDs   = ismember(triEdge2Vert,VertIDs(bVertIDs));
        i_tribEdgeIDs   = find(sum(i_tribVertIDs,2) == 2);
        nbEdges	= numel(i_tribEdgeIDs);
        switch nbEdges
            case 0              % Edge Insertion --------------------------
                
                % Select the one (or one of) vert on the boundary.
                insertionVertID = triEdge2Vert(itriEdgeID,c);
                
                
            otherwise % {1 2 3}	% Edge Bisection --------------------------
                % Get VertIDs of itriEdgeID.
                edgeVerts   = triEdge2Vert(i_tribEdgeIDs(1),:);
                
                % Identify triElem2Elem across from itriEdgeIDs.
                opp_triElemID	= triElem2Elem(i_tribEdgeIDs(1),...
                    ~ismember(triElem2Elem(i_tribEdgeIDs(1),:),triElemID));
                opp_triElem2Vert= Domain.ConnectivityList(opp_triElemID,:);
                
                % Compute midpoint coordinate of idx_triEdge.
                [x,y] = Domain.edgeMidpoint(triEdgeIDs(i_tribEdgeIDs(1)));
                
                % Bisect itriEdgeID by inserting node at [x,y].
                NP	= size(Domain.Points,1) + 1;  	% Index new point.
                Domain.Points   = [Domain.Points; [x y 0]];
                idx_triElem2Vert	= find(ismember(triElem2Vert,edgeVerts));
                newMesh.ConnectivityList	= [newMesh.ConnectivityList;...
                    [triElem2Vert(1:idx_triElem2Vert(1)), NP,...
                    triElem2Vert(idx_triElem2Vert(2):end)]];
                opptri_newVerts     = [opp_triElem2Vert, NP];
                dt  = delaunayTriangulation(Domain.Points(opptri_newVerts,1:2));
                switch size(dt.ConnectivityList,1)	% Check for errors.
                    case 2                          % good to go.
                    case 3
                        idt = sum(ismember(...      % No degenerate tris.
                            opptri_newVerts(dt.ConnectivityList),[edgeVerts,NP]),2) == 3;
                        if any(idt)             	% Remove degenerate tris.
                            P   = Domain.Points(opptri_newVerts,1:2);
                            C   = dt.ConnectivityList(~idt,:);
                            dt  = triangulation(C,P);
                        end
                    otherwise
                        error('somehow got 1,4, or more triangles from delaunay');
                end
                
                % Update Domain information.
                NE  = size(Domain.ConnectivityList,1) + 1;
                Domain.ConnectivityList(opp_triElemID,:) =...
                    opptri_newVerts(dt.ConnectivityList(1,:));
                Domain.ConnectivityList	= [Domain.ConnectivityList;...
                    opptri_newVerts(dt.ConnectivityList(2,:))];
                Domain.Layers.IE{iLayer-1} = [Domain.Layers.IE{iLayer-1}; NE];
                Domain.Layers.IV{iLayer-1} = [Domain.Layers.IV{iLayer-1}; NE];
                
                %%% For real-team plotting:
                Domain.plot;   subDomain.plot(1:subDomain.nElems,'elemcolor','c');
                hold on;    triplot(dt);
        end
    end
end



