function [CM,removedVertIDs]	= CleanupBoundaryQuads(CM,removedVertIDs,canRemoveEdges,plotProgress)
%CLEANUPBOUNDARYQUADS Removes unsmoothable quads on mesh boundaries.
%   [CM,removedVertIDs] = TRUNCATEBOUNDARYQUADS(CM,Domain,canRemoveEdges,
%   plotProgress) returns...
%
%   These quads are identified as those on the boundary with interior
%   angles exceeding 134 degrees defined by two boundary edges. These
%   quads will have a quality of zero by our definition and cannot be
%   smoothed to a better quality since the angle defined by the
%   boundary edges is unsmoothable. Some additional work should include
%   a capability for removing or refining quads with 4 nodes on the
%   boundary.
%
%   See also: POSTPROCESSROUTINE.
%==========================================================================
idx = 0
% Keep track of vertices removed from mesh.
removedVertIDs  = [removedVertIDs; zeros(length(CM.Layers.OV{1}),1)];
iremovedVertIDs = find(removedVertIDs == 0,1,'first');

% Depending on user-input, remove degenerate quads or correct their geometry.
ineligibleElemIDs   = [];
if canRemoveEdges   % Collapse degenerate, unsmoothable quads along mesh boundary.
    exitCriterionMet = false;
    while ~exitCriterionMet
        idx = idx + 1
        % Identify all quads with 2 adjacent edges on the mesh boundary.
        bEdgeIDs    = CM.boundaryEdges;
        bVertIDs    = CM.boundaryVerts;
        bElemIDs    = CM.Layers.OE{1};
        bElem2EdgeIDs	= CM.elem2Edge(bElemIDs);
        [c,r]   = find(ismember(bElem2EdgeIDs,bEdgeIDs)')
        ibElem2EdgeIDs	= sum(,2);
        bElemIDs_with_2_bEdges	= ibElem2EdgeIDs == 2;
        
        % Deal with quads having only 2 edges on boundary.
        ElemIDs	= bElemIDs(bElemIDs_with_2_bEdges);
        ElemIDs(ismember(ElemIDs,ineligibleElemIDs))	= 0;
        if isempty(ElemIDs) || all(ElemIDs == 0)
            exitCriterionMet	= true;	% Part one of criteria met; move on to quads with 3, 4 edges on boundary.
            continue
        else
            % Get interior angles of ElemIDs' boundary vertices.
            theta   = CM.interiorAngles(ElemIDs);
            if all(theta(:) < 135)
                exitCriterionMet	= true;
                continue
            end
        end
        
        % Flag thetas corresponding to vertices not on boundary.
        Elem2VertIDs = CM.elem2Vert(ElemIDs);
        Elem2bVertIDs= ismember(Elem2VertIDs,bVertIDs);
        theta(Elem2bVertIDs == 0)	= 0;
        if all(theta(:) < 135)
            exitCriterionMet	= true;
            continue
        end
        
        % Flag angles that are not comprised by 2 boundary vertices.
        bEdges_of_ElemIDs   = bElem2EdgeIDs(bElemIDs_with_2_bEdges,:);
        bEdges_of_ElemIDs(~ismember(bEdges_of_ElemIDs,bEdgeIDs))	= 0;
        ibEdges_of_ElemIDs = bEdges_of_ElemIDs > 0;
        vert1   = ibEdges_of_ElemIDs(:,4) & ibEdges_of_ElemIDs(:,1);
        vert2   = ibEdges_of_ElemIDs(:,1) & ibEdges_of_ElemIDs(:,2);
        vert3   = ibEdges_of_ElemIDs(:,2) & ibEdges_of_ElemIDs(:,3);
        vert4   = ibEdges_of_ElemIDs(:,3) & ibEdges_of_ElemIDs(:,4);
        theta(vert1,2:4)	= 0;
        theta(vert2,[1 3:4])= 0;
        theta(vert3,[1:2 4])= 0;
        theta(vert4,1:3)	= 0;
        
        % Select eligibleQuad with boundary vertex exceeding 135 degrees, largest angle 1st.
        theta(theta < 135.00)	= 0;
        if all(theta(:) < 135)
            exitCriterionMet	= true;
            continue
        end
        [thetaSorted,itheta] = sort(theta,2,'descend');
        [~,iElemIDs]	= max(thetaSorted(:,1));
        eligibleElemID	= ElemIDs(iElemIDs);
        
        % Get relevant adjacency info for eligible quad.
        eligibleVertID  = Elem2VertIDs(iElemIDs,itheta(iElemIDs));
        eligiblebEdgeIDs	= bEdges_of_ElemIDs(iElemIDs,bEdges_of_ElemIDs(iElemIDs,:) > 0);
        eligiblebEdge2VertIDs	= CM.edge2Vert(eligiblebEdgeIDs);
        eligiblebEdge2VertIDs(eligiblebEdge2VertIDs == eligibleVertID)	= [];
        if length(eligiblebEdge2VertIDs) ~= 2       % Sides aren't adjacent.
            ineligibleElemIDs   = [ineligibleElemIDs; eligibleElemID]; %#ok<*AGROW>
            continue
        end
        eligibleQuadNeighbors   = CM.vert2Elem('vertids',eligiblebEdge2VertIDs);
        for ieligibleQuadNeighbors = 1:numel(eligibleQuadNeighbors)
            tmp	= eligibleQuadNeighbors{ieligibleQuadNeighbors};
            tmp(ismember(tmp,[0; eligibleElemID]))	= [];
            eligibleQuadNeighbors{ieligibleQuadNeighbors}	= tmp;
        end
        
        % Perform Boundary Quad Cleanup Operation.
        [CM,rv]	= CleanupBoundaryQuadsSubRoutine(CM,eligibleVertID,...
            eligiblebEdge2VertIDs,eligibleElemID,eligibleQuadNeighbors);
        removedVertIDs(iremovedVertIDs:iremovedVertIDs+1)	= rv;
        iremovedVertIDs	= iremovedVertIDs + 2;
    end
end

% Update Outputs.
removedVertIDs(removedVertIDs == 0)	= [];
CM  = CHILmesh(CM.ConnectivityList,CM.Points);
end

function [CM,removedVertIDs]	= CleanupBoundaryQuadsSubRoutine(CM,...
    eligibleVertID,eligiblebEdge2VertIDs,eligibleElemID,eligibleQuadNeighbors)
%CLEANUPBOUNDARYQUADSSUBROUTINE Removes quads with too-obtuse of angles.

%   See also: CLEANUPBOUNDARYQUADS.
%==========================================================================

% Get connectivity of each quad.
side1Conn   = CM.ConnectivityList(eligibleQuadNeighbors{1},:);
side2Conn   = CM.ConnectivityList(eligibleQuadNeighbors{2},:);

% Index to common vertices of each side of quad's neighbors.
[r1,c1] = find(ismember(side1Conn,eligiblebEdge2VertIDs(1)));
[r2,c2] = find(ismember(side2Conn,eligiblebEdge2VertIDs(2)));
iside1Conn  = sub2ind(size(side1Conn),r1,c1);
iside2Conn  = sub2ind(size(side2Conn),r2,c2);

% Replace too-obtuse-VertIDs with common vertices.
removedVertIDs  = unique([side1Conn(iside1Conn); side2Conn(iside2Conn)]);
side1Conn(iside1Conn)   = eligibleVertID;
side2Conn(iside2Conn)   = eligibleVertID;

% Update CHILmesh object.
CM.ConnectivityList(eligibleQuadNeighbors{1},:)	= side1Conn;
CM.ConnectivityList(eligibleQuadNeighbors{2},:)	= side2Conn;
CM.ConnectivityList(eligibleElemID,:)	= 0;
CM  = CHILmesh(CM.ConnectivityList(sum(CM.ConnectivityList,2) ~= 0,:),CM.Points);

% Future addition: Adjust vertices of quads that had a vertex shifted such
% that their previously-unaltered vertices shift slightly toward
% eligibleVertID.
end
