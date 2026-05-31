function [Domain,newMesh] = edgeInsertion(CASE,Domain,newMesh,iLayer,...
    tElemID,tConn,bVertIDs,plotProgress)
%EDGEINSERTION Insert edge by splitting the lone vert into two verts.
%   [Domain,newMesh] = EDGEINSERTION(Case,...) returns CHILmesh object
%   Domain updated for all layers iLayer-1:-1:1 and data for defining the
%   new quadrilateral mesh object newMesh, which is comprised of a points
%   list and quadrilateral elements' connectivity.
%
%   When CASE is equal to 1:
%       There is only one point of the triangle on the mesh boundary. An
%       edge is inserted at this point to split the triangle into a quad.
%
%   When CASE is equal to 2:
%       There is only one point of the triangle on the layer boundary. An
%       edge is inserted at this point to split the triangle into a quad.
%
%   When CASE is equal to 3:
%       There are 2 or 3 edges of the tri on the mesh boundary and instead
%       of truncating this triangle, an edge is inserted to form a
%       decently-shaped quad. If there are 3 edges, the first available
%       point is chosen for an edge insertion, otherwise, the point common
%       to both edges is chosen.
%
%   See also: EDGEREMOVAL, EDGEBISECTION, REMOVETRIANGLESFUN.
%==========================================================================

% Identify vert(s) on boundary.
itbVertID	= ismember(tConn,bVertIDs);
tbVertID	= tConn(itbVertID);

if ismember(CASE,[1 2])
    % Select the one vert on the layer's boundary.
    if numel(tbVertID) > 1
        tbVertID	= tbVertID(1);
    end
    
    % Get adjacency info of tbVertID wrt Domain.
    EdgeIDs0	= cell2mat(CCWEdgesAroundVertsFun(Domain,tbVertID));
    EdgeIDs     = EdgeIDs0;
    Edge2VertIDs= Domain.edge2Vert(EdgeIDs);        % Verts of edges.
    Edge2ElemIDs = Domain.edge2Elem(EdgeIDs);
    
    % Identify EdgeIDs adjacent to tbVertID that are boundary edges of iLayer.
    iadjbEdgeIDs= sum(ismember(Edge2ElemIDs,Domain.Layers.OE{iLayer}),2) > 0 &...
        sum(ismember(Edge2ElemIDs,Domain.Layers.IE{iLayer}),2) == 0;
    if sum(iadjbEdgeIDs) > 2
        % Edges in interior layers will neighbor IE of iLayer-1.
        if iLayer > 1
            iadjbEdgeIDs	= iadjbEdgeIDs &...
                sum(ismember(Edge2ElemIDs,Domain.Layers.IE{iLayer-1}),2) > 0;
        else
            iadjbEdgeIDs = iadjbEdgeIDs & sum(Edge2ElemIDs == 0,2) > 0;
        end
    end
    adjbEdgeIDs	= EdgeIDs(iadjbEdgeIDs);
    
    % Identify vertices of adjbEdges that will remain unaltered.
    adjbEdge2VertIDs    = Edge2VertIDs(iadjbEdgeIDs,:);
    stationaryVertIDs   = [adjbEdge2VertIDs(1,~ismember(adjbEdge2VertIDs(1,:),tbVertID));...
        adjbEdge2VertIDs(2,~ismember(adjbEdge2VertIDs(2,:),tbVertID))];
    
    % Compute location of verts of new edge (along boundary edges adjacent to tbVertID).
    D   = Domain.edgeLength(adjbEdgeIDs);           % Dist to each vert.
    del = D./3;                                     % 1/3 of each ^.
    t   = del./D;                                   % Ratio of distances.
    npXYZ   = (1-t).*repmat(Domain.Points(tbVertID,1:3),2,1)...
        + Domain.Points(stationaryVertIDs,1:3).*t;
    
    % Get quads in newMesh that will be altered with newly-inserted edge.
    adjQuadIDs	= find(sum(ismember(...             % Indices wrt newMesh.
        newMesh.ConnectivityList,tbVertID),2) > 0);
    nadjQuadIDs = length(adjQuadIDs);
    adjQuadConn	= newMesh.ConnectivityList(adjQuadIDs,:);
    
    % Remove edges in iLayer-1 from Edge2VertIDs.
    if iLayer > 1
        iEdgeIDs	= sum(ismember(Edge2ElemIDs,Domain.Layers.IE{iLayer-1})...
            | ismember(Edge2ElemIDs,Domain.Layers.OE{iLayer-1}),2) == 2;
        EdgeIDs(iEdgeIDs)    = [];
        iadjbEdgeIDs(iEdgeIDs)	= [];
        Edge2VertIDs(iEdgeIDs,:)= [];
        Edge2ElemIDs(iEdgeIDs,:)= [];
    end
    
    % Rotate Edge2VertIDs such that the boundary edges are first, last.
    while sum(iadjbEdgeIDs([1,end])) ~= 2
        EdgeIDs	= EdgeIDs([2:end,1]);
        Edge2VertIDs    = Edge2VertIDs([2:end,1],:);
        Edge2ElemIDs    = Edge2ElemIDs([2:end,1],:);
        iadjbEdgeIDs    = iadjbEdgeIDs([2:end,1]);
    end
    
    % Ensure that the 1st boundary edge is listed 1st in Edge2VertIDs.
    if ~ismember(Edge2VertIDs(1,:),adjbEdge2VertIDs(1,:),'rows')
        EdgeIDs	= flipud(EdgeIDs);
        Edge2VertIDs	= flipud(Edge2VertIDs);
        Edge2ElemIDs    = flipud(Edge2ElemIDs);
    end
    
    % Determine which quad(s) are on each side of tri.
    [iEdge2ElemIDs,~]	= find(sum(ismember(Edge2ElemIDs,tElemID),2) > 0,1,'first');
    if nadjQuadIDs == 2
        % Edges on 1st side receive the new point, 2nd side does not.
        tris_of_newPTQuad   = Edge2ElemIDs(iEdge2ElemIDs,...
            ~ismember(Edge2ElemIDs(iEdge2ElemIDs,:),[0 tElemID]));
        newPTQuad   = find(sum(ismember(adjQuadConn,Edge2VertIDs(iEdge2ElemIDs,:)),2) == 2);
        
    else
        % Advance along EdgeIDs, identifying quads on each side of tElemID.
        try
            Edge2ElemIDs(ismember(Edge2ElemIDs,Domain.Layers.IE{iLayer-1}))	= 0;
        catch
            % Do nothing
        end
        itElemID    = find(sum(ismember(Edge2ElemIDs,tElemID),2) > 0);
        tris_of_newPTQuad   = unique(Edge2ElemIDs(1:itElemID(1),:));
        tris_of_newPTQuad(ismember(tris_of_newPTQuad,[0,tElemID]))	= [];
        newPTQuad   = find(sum(ismember(adjQuadConn,...
            Domain.ConnectivityList(tris_of_newPTQuad,:)),2) >= 3);
    end
    oldPTQuad   = setdiff(1:nadjQuadIDs,newPTQuad);
    
    % Replace tbVertID in newPTQuadsConn and adjacent edges with npID.
    npID	= size(Domain.Points,1)+1;              % New point VertID.
    newBoundaryVerts	= [stationaryVertIDs; npID; tbVertID];
    adjbEdge2VertIDs(1,ismember(adjbEdge2VertIDs(1,:),tbVertID))	= npID;
    newPTQuadConn   = adjQuadConn(newPTQuad,:);     % NewPTQuad(s)' new conn.
    newPTQuadConn(ismember(newPTQuadConn,tbVertID))	= npID;
    oldPTQuadConn   = adjQuadConn(oldPTQuad,:);     % Original/unchanged quad conn.
    
    % Update spatial location of verts comprising the new edge.
    Domain.Points   = [Domain.Points; npXYZ(1,1) npXYZ(1,2) npXYZ(1,3)];
    Domain.Points(tbVertID,:)   = [npXYZ(2,1) npXYZ(2,2)  npXYZ(2,3)];
    
    % Update quad(s) getting new point.
    newMesh.ConnectivityList(adjQuadIDs(newPTQuad),:)	= newPTQuadConn;
    
    % Construct new connectivity of tElemID, append (new quad) to newMesh.
    iV1V2   = ismember(tConn,oldPTQuadConn);
    V1V2= tConn(iV1V2);
    V1  = tbVertID;
    V2  = V1V2(~ismember(V1V2,V1));
    V3  = tConn(~iV1V2);
    V4  = npID;
    newMesh.ConnectivityList	= [newMesh.ConnectivityList; [V1 V2 V3 V4]];
    
    %%% Retriangulate all triangles in iLayer-1 using tbVertID.
    if CASE == 2
        % Identify tris adjacent to tbVertID that are OE, IE in iLayer-1.
        tbVertIDtris	= find(sum(ismember(...     % Tris adjacent to vert.
            Domain.ConnectivityList,tbVertID),2) > 0);
        iLm1OE	= tbVertIDtris(ismember(tbVertIDtris,Domain.Layers.OE{iLayer-1}));
        iLm1IE	= tbVertIDtris(ismember(tbVertIDtris,Domain.Layers.IE{iLayer-1}));
        iLm1Elem2VertIDs	= Domain.ConnectivityList([iLm1OE; iLm1IE],:);
        iLm1Edge2VertIDs	= unique(sort([iLm1Elem2VertIDs(:,1:2);...
            iLm1Elem2VertIDs(:,2:3); iLm1Elem2VertIDs(:,[3 1])],2),'rows');
        
        % Remove edges used by tbVertID from list.
        iLm1Edge2VertIDs(sum(ismember(iLm1Edge2VertIDs,tbVertID),2) > 0,:)	= [];
        
        % Identify vertices of new edge from which new tris are created.
        baseVertIDs	= [tbVertID, npID];
        rt_bVertIDs	= [iLm1Edge2VertIDs; adjbEdge2VertIDs; baseVertIDs];
        
        % Create an ordered sequence of vertices along boundary of local element set.
        nrt_bVertIDs	= size(rt_bVertIDs,1);      % # of local boundary verts.
        vertSeq	= zeros(nrt_bVertIDs,1);
        vertSeq([1 end])= [npID; tbVertID];
        rt_bVertIDs(sum(ismember(rt_bVertIDs,vertSeq([1 end])),2)==2,:)	= 0;
        for jdx = 2:nrt_bVertIDs-1                  % Connect "base verts".
            [r,~]	= find(rt_bVertIDs == vertSeq(jdx-1));
            vertSeq(jdx)	= rt_bVertIDs(r,~ismember(rt_bVertIDs(r,:),vertSeq(jdx-1)));
            rt_bVertIDs(r,:)= 0;                    % Flag used vertices.
        end
        
        % Create new tris by advancing along sequence, connecting half of
        % vertSeq(3:end) to the new point and half to tbVertID.
        newTris = cell(1,nrt_bVertIDs);
        inewTris= 1;
        switchVertID	= floor(nrt_bVertIDs/2);
        idxSeq	= {2:switchVertID; switchVertID+1:size(rt_bVertIDs,1)-2};
        for jdx	= idxSeq{1}(1):idxSeq{1}(end)
            % Create tris from 1st base vertex.
            newTris{inewTris}	= [vertSeq(1); vertSeq(jdx:jdx+1)];
            inewTris	= inewTris + 1;
        end
        for jdx	= idxSeq{2}(1):idxSeq{2}(end)
            % Create tris from 2nd/last base vertex.
            newTris{inewTris}	= [vertSeq(end); vertSeq(jdx:jdx+1)];
            inewTris	= inewTris + 1;
        end
        
        % Get connectivity of retriangulated (new) tris. Final tri is an IE.
        rtConn	= [cell2mat(newTris)'; [baseVertIDs, vertSeq(switchVertID+1)]];% Why plus 1??
        
        % Prepare to overwrite tris from iLayer-1 with retriangulated tris.
        irt	= 1:size(rtConn,1);                  	% Indices to all new tris.
        nrt	= irt(end);                          	% Num of ^.
        ioverwriteTriIDs	= [iLm1OE; iLm1IE];   	% Indices to old tris to overwrite.
        noverwriteTriIDs	= length(ioverwriteTriIDs);	% Num of ^.
        i_ioverwriteTriIDs	= irt(1:noverwriteTriIDs);	% Indices to overwrite old tris wrt rt.
        inewTriIDs	= irt(noverwriteTriIDs+1:nrt);	% Indices to new elemIDs.
        newTriIDs	= [ioverwriteTriIDs; size(Domain.ConnectivityList,1) + (1:numel(inewTriIDs))'];
        
        % Of new tris, whichever have only 1 vert from newBoundaryVerts are OV of iLayer-1.
        iOE	= sum(ismember(rtConn,newBoundaryVerts),2) == 1;
        
        % List new tris and npID from triangulation in correct Layers lists.
        Domain.Layers.OE{iLayer-1}(ismember(Domain.Layers.OE{iLayer-1},iLm1OE))	= [];
        Domain.Layers.OE{iLayer-1}	= [Domain.Layers.OE{iLayer-1}; newTriIDs(iOE)];
        Domain.Layers.IE{iLayer-1}(ismember(Domain.Layers.IE{iLayer-1},iLm1IE))	= [];
        Domain.Layers.IE{iLayer-1}	= [Domain.Layers.IE{iLayer-1}; newTriIDs(~iOE)];
        Domain.Layers.OV{iLayer}	= [Domain.Layers.OV{iLayer}; npID];
        Domain.Layers.IV{iLayer-1}  = [Domain.Layers.IV{iLayer-1}; npID];
        
        % Replace old tris with new some/all of the new tris in iLayer-1; append remaining tris.
        Domain.ConnectivityList(ioverwriteTriIDs(i_ioverwriteTriIDs),:)	= rtConn(i_ioverwriteTriIDs,:);
        Domain.ConnectivityList = [Domain.ConnectivityList; rtConn(inewTriIDs,:)];
    else
        newTriIDs   = [];
    end
    
    % Within Domain, split tElemID (new Quad) into 2 tris.
    replacementTris     = splitQuad(newMesh,size(newMesh.ConnectivityList,1));
    iOE = sum(ismember(replacementTris,newBoundaryVerts),2) > 1;
    Domain.ConnectivityList(tElemID,:)  = replacementTris(1,:);
    Domain.ConnectivityList	= [Domain.ConnectivityList; replacementTris(2,:)];
    itElemIDTris    = [tElemID; size(Domain.ConnectivityList,1)];
    if iOE(1)                                       % tElemID is still an OE.
    else
        Domain.Layers.OE{iLayer}(ismember(Domain.Layers.OE{iLayer},tElemID))	= [];
        Domain.Layers.OE{iLayer}= [Domain.Layers.IE{iLayer}; itElemIDTris(iOE)];
    end
    Domain.Layers.IE{iLayer}= [Domain.Layers.IE{iLayer}; itElemIDTris(~iOE)];
    newTriIDs	= [newTriIDs; tElemID; size(Domain.ConnectivityList,1)];
    
    % Update tris comprising newPTQuad.
    tris_of_newPTQuadConn   = Domain.ConnectivityList(tris_of_newPTQuad,:);
    tris_of_newPTQuadConn(ismember(tris_of_newPTQuadConn,tbVertID)) = npID;
    Domain.ConnectivityList(tris_of_newPTQuad,:)	= tris_of_newPTQuadConn;
    
    % Identify number of edges replacing original EdgeIDs.
    nEdges_tElemIDtris  = 1;                        % Edge created by splitting tElemID.
    if CASE == 2                                    % Num. edges defining retriangulation.
%         nEdges_iLm1tris	= size(iLm1Edge2VertIDs,1);
        Edges_rt    = unique(sort([rtConn(:,1:2);...
            rtConn(:,2:3); rtConn(:,[3 1])],2),'rows');
        nEdges_rt   = sum(sum(ismember(Edges_rt,[npID,tbVertID]),2) >= 1);

    else
%         nEdges_iLm1tris = 0;                        % Zero edges affected in iLayer-1.
        nEdges_rt	= 3;                         	% If no retri, include 3 layer boundary edges.
    end
    nEdges_newPTQuadtris    = iEdge2ElemIDs-1;      % Num. edges on each "side" of tElemID.
    nEdges_oldPTQuadtris    = length(EdgeIDs)- (iEdge2ElemIDs+1);
    
    % Do a really inefficient update of the Domain adjacency lists. 
%     Domain.nEdges   = Domain.nEdges - nEdges_iLm1tris + nEdges_rtris +...
%         nEdges_tElemIDtris + nEdges_newPTQuadtris;
    Domain.nEdges   = Domain.nEdges - length(EdgeIDs0) + nEdges_rt +...
        nEdges_tElemIDtris + nEdges_newPTQuadtris + nEdges_oldPTQuadtris;
    Domain.nElems   = size(Domain.ConnectivityList,1);
    Domain.nVerts   = npID;
    [~,Domain]	= Domain.isPolyCCW('index',newTriIDs);
    Domain  = Domain.buildAdjacencies;
    
else                                                % Split common/any point.
    % Compute average edge length of triangle, then try to make new edge as
    % close to this length as possible.
    %*** Not sure how to do this right now kind of a tricky problem); just
    %going to truncate off this triangle by not addint it to newMesh.
    
end
