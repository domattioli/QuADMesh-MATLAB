function [Domain,subDomain,removedEdgeIDs,ElemIDs,VertIDs,bVertIDs]...
    = identifyEdgesFunction(Domain,iLayer)
%IDENTIFYEDGESFUNCTION Creates a quadrangular or mixed-element mesh.
%   [Domain,subDomain] = IDENTIFYEDGESFUNCTION
%
%   See also: TRI2QUADROUTINE.
%==========================================================================

% Get elems of layer; create sub-domain CHILmesh object.
ElemIDs	= [Domain.Layers.OE{iLayer}; Domain.Layers.IE{iLayer}];
subDomain	= CHILmesh(Domain.ConnectivityList(ElemIDs,:),Domain.Points);
VertIDs	= Domain.Layers.OV{iLayer};                 % Verts of outer boundary.

% Get verts that define the outer boundary(ies) of the subDomain.
bEdgeIDs	= subDomain.boundaryEdges;              % Boundary edges.
bVertIDs	= subDomain.edge2Vert(bEdgeIDs);        % Vertices of ^.

% Ignore bEdgeIDs defined by inner boundary(ies), i.e. inner verts.
IV_bEdges	= sum(ismember(bVertIDs,VertIDs),2) == 0;
bEdgeIDs(IV_bEdges)	= [];                           % Remove IV_bEdges from
bVertIDs(IV_bEdges,:)   = [];                       % future consideration.

% Re-index bVertIDs with respect to VertIDs.
[ubVertIDs,~,iunique]   = unique(bVertIDs);         % Index unique bVertIDs.
bVertIDs	= reshape(iunique,size(bVertIDs));      % 1st unique value to last.

% Get adjacency lists for reference, flag these throughout routine.
vert2Edges	= subDomain.vert2Edge('VertIDs',ubVertIDs,'store','m');
edge2Elems	= subDomain.edge2Elem;                  % Wrt to sub-domain.

% Compute unique paths along outer vertices of subDomain/iLayer.
Path	= PathsOnOV(iLayer,Domain);                 % Verts indexed wrt Point List.

%%% For real-time plotting.
subDomain.plot;

% Initialize variable for edges to be removed (assume all edges).
removedEdgeIDs	= zeros(size(edge2Elems,1),1);
i_removedEdgeIDs= 1;                                % Index first entry.

% Advance along verts in iPath, identifying every-other edge.
for iPath	= 1:size(Path,2)
    % Wrap path w/ destination, source verts.
    pathVertIDs	= [Path{iPath}(end); Path{iPath}; Path{iPath}(1)];
    
    % Identify edge at which path begins.
    downEdgeID  = bEdgeIDs(sum(ismember(...
        bVertIDs,pathVertIDs(1:2)),2) == 2);
    if isempty(downEdgeID)
        downEdgeID = bEdgeIDs(sum(ismember(bVertIDs,pathVertIDs(1:2)),2) == 1);
        if numel(downEdgeID) > 1
            downEdgeID = downEdgeID(1);
        end
    end
    
    % Advance along each vertex in iPath.
    for iPathVertID = 2:length(pathVertIDs)-1
        % Get edges incident to iPathVertID and their attached elems.
        ivert2Edges	= find(ubVertIDs == VertIDs(pathVertIDs(iPathVertID)));
        iPathVertID_EdgeIDs	= vert2Edges(ivert2Edges,...
            vert2Edges(ivert2Edges,:) > 0);
        num_Edges	= length(iPathVertID_EdgeIDs);
        
        % Identify uppath, downpath edges along subDomain boundary.
        adjEdgeIDs	= iPathVertID_EdgeIDs(ismember(...
            iPathVertID_EdgeIDs,bEdgeIDs));
        adjEdgeVertIDs  = subDomain.edge2Vert(adjEdgeIDs);
        upEdgeID    = downEdgeID;                   % Advance downpath.
        downEdgeID  = adjEdgeIDs(sum(ismember(adjEdgeVertIDs,...
            VertIDs(pathVertIDs(iPathVertID+1))),2) > 0);
%         downEdgeID  = adjEdgeIDs(adjEdgeIDs ~= upEdgeID)
        
        %%% For real-time plotting:
%         subDomain.plotEdge(upEdgeID,'color','r','LineWidth',2);         % Uppath edge
%         subDomain.plotPoint(VertIDs(PathVertIDs(iPathVertID-1)),'Color','r');	% Uppath vert.
        
        if num_Edges == 2                           % Only boundary edges remain.
            continue                                % Advance down-path.
        end
        
        %%% For real-time plotting:
%         subDomain.plotEdge(downEdgeID,'color','b','LineWidth',2);       % Downpath edge
%         subDomain.plotPoint(VertIDs(PathVertIDs(iPathVertID)),'Color','g');     % Downpath vert.
%         subDomain.plotPoint(VertIDs(PathVertIDs(iPathVertID+1)),'Color','b');   % Next vertex along path.
        
        % Sort iPathVert_EdgeIDs from up-path edge to down-path edge.
        %%% Note: this can be avoided if vert2edges are oriented CW/CCW.
        iPathVertID_ElemIDs	= subDomain.edge2Elem(iPathVertID_EdgeIDs);
        if any(sum(iPathVertID_ElemIDs == 0,1) == size(iPathVertID_ElemIDs,1))
            continue                                % No edges to remove.
        else
            s_iPathVertID_EdgeIDs	= [upEdgeID; zeros(num_Edges-2,1);...
                downEdgeID];                        % Upedge 1st; down last.
            downElemID	= 0;                        % Elem of downEdgeID.
            currentEdge	= find(iPathVertID_EdgeIDs == upEdgeID);
            for jdx	= 2:num_Edges-1
                % Identify elemID of upEdgeID.
                upElemID	= iPathVertID_ElemIDs(currentEdge,...
                    iPathVertID_ElemIDs(currentEdge,:) ~= downElemID);
                
                % Flag currentEdge as used.
                iPathVertID_ElemIDs(currentEdge,:)	= 0;
                
                % Find "currentEdge" and downElemID for next iteration.
                [currentEdge,~]	= find(iPathVertID_ElemIDs == upElemID);
                if isempty(currentEdge)             % Ensure currentEdge is chosen.
                    upElemID_neighbor   = subDomain.elem2Elem(upElemID);
                    upElemID_neighbor(upElemID_neighbor == 0)	= [];
                    upElemID_neighbor(~ismember(...
                        upElemID_neighbor,iPathVertID_ElemIDs))	= [];
                    [currentEdge,~] = find(ismember(iPathVertID_ElemIDs,...
                        upElemID_neighbor));
                end
                s_iPathVertID_EdgeIDs(jdx)	= iPathVertID_EdgeIDs(currentEdge);
                
                % If only one edge needs to be sorted, exit loop.
                remaining_edges_to_sort = s_iPathVertID_EdgeIDs == 0;
                if sum(remaining_edges_to_sort) == 1
                    s_iPathVertID_EdgeIDs(remaining_edges_to_sort) = ...
                        iPathVertID_EdgeIDs(~ismember(...
                        iPathVertID_EdgeIDs,s_iPathVertID_EdgeIDs));
                    break
                else                                % Advance along edges.
                    downElemID	= upElemID;
                end
            end
        end
        
        % Identify every other edge along path wrt the sorted edges.
        for jdx	= 2:num_Edges-1                     % Do not remove up/downEdges.
            % Check if edge jdx's ElemIDs have been flagged.
            ElemIDs_jdxEdge	= edge2Elems(s_iPathVertID_EdgeIDs(jdx),:);
            if any(ElemIDs_jdxEdge == 0)            % ElemID flagged.
                continue                            % Skip to next edge.
            else                                    % No ElemIDs flagged.
                % Store EdgeID for removal, update counter.
                removedEdgeIDs(i_removedEdgeIDs) = s_iPathVertID_EdgeIDs(jdx);
                vert2Edges(ismember(...             % Flag used edges.
                    vert2Edges,removedEdgeIDs(1:i_removedEdgeIDs)))	= 0;
                i_removedEdgeIDs	= i_removedEdgeIDs + 1;
                
                % Flag ElemIDs that are now used.
                edge2Elems(ismember(edge2Elems,ElemIDs_jdxEdge))	= 0;
            end
        end
    end
end




