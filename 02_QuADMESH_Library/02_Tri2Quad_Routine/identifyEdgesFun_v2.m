function [Domain,subDomain,ElemIDs,VertIDs,bEdgeIDs,bVertIDs,removedEdgeIDs]...
    = identifyEdgesFun_v2(Domain,iLayer)
%IDENTIFYEDGESFUN Creates a quadrangular or mixed-element mesh.
%   [Domain,subDomain] = IDENTIFYEDGESFUNC
%
%   See also: PATHSONOV, TRI2QUADROUTINE.
%==========================================================================

% Get elems of layer; create sub-domain CHILmesh object.
ElemIDs	= [Domain.Layers.OE{iLayer}; Domain.Layers.IE{iLayer}];
subDomain	= CHILmesh(Domain.ConnectivityList(ElemIDs,:),Domain.Points);
VertIDs	= Domain.Layers.OV{iLayer};                 % Verts of outer boundary.

% Compute unique paths along outer vertices of subDomain/iLayer.
Path	= PathsOnOV(iLayer,Domain);                 % Verts indexed wrt Point List.
% Rearrange path to start with an outer "corner" element
for i = 1:size(Path,2)
    iStart = find(cellfun(@length,subDomain.vert2Elem('VertIDs',VertIDs(Path{i})))==1);
    if ~isempty(iStart)
        Path{i} = [Path{i}(iStart(1)+1:end);Path{i}(1:iStart(1))];
    end
end

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
vert2Edges	= MYcell2mat(CCWEdgesAroundVertsFun(subDomain,VertIDs),'zeros');
edge2Elems	= subDomain.edge2Elem;                  % Wrt to sub-domain.

% Advance along verts in iPath, identifying every-other edge.
removedEdgeIDs	= zeros(size(edge2Elems,1),1);      % Assume all edges are removed.
i_removedEdgeIDs	= 1;                        	% Index first entry.
for iPath	= 1:size(Path,2)
    % Wrap path w/ destination, source verts.
    pathVertIDs	= [Path{iPath}(end); Path{iPath}; Path{iPath}(1)];
    
    % Identify edge at which path begins.
    downEdgeID  = bEdgeIDs(sum(ismember(bVertIDs,pathVertIDs(1:2)),2) == 2);
    if isempty(downEdgeID)
        downEdgeID = bEdgeIDs(sum(ismember(bVertIDs,pathVertIDs(1:2)),2) == 1);
        if numel(downEdgeID) > 1
            downEdgeID = downEdgeID(1);
        end
    end
    
    % Advance along each vertex in iPath.
    for iPathVertID = 1:length(pathVertIDs)-1
        % Get edges incident to iPathVertID and their attached elems.
        iPathVertID_EdgeIDs	= vert2Edges(ubVertIDs == VertIDs(pathVertIDs(iPathVertID)),:);
        
        % Identify uppath and downpath edges along subDomain boundary.
        adjEdgeIDs	= iPathVertID_EdgeIDs(ismember(iPathVertID_EdgeIDs,bEdgeIDs));
        adjEdgeVertIDs  = subDomain.edge2Vert(adjEdgeIDs);
        upEdgeID    = downEdgeID;                   % Advance downpath.
        downEdgeID  = adjEdgeIDs(sum(ismember(adjEdgeVertIDs,...
            VertIDs(pathVertIDs(iPathVertID+1))),2) > 0);
        
        % Remove "padded" edges from vert2Edges.
        totalNumEdges   = cellfun(@length,...
            subDomain.vert2Edge('VertIDs',VertIDs(pathVertIDs(iPathVertID))));
        if totalNumEdges ~= length(iPathVertID_EdgeIDs)
            iPathVertID_EdgeIDs(totalNumEdges+1:end)	= [];
        end
        
        % Check if current vertex has any edges to remove.
        numUnusedEdges	= sum(iPathVertID_EdgeIDs > 0);
        if numUnusedEdges == 2                      % Only boundary edges remain.
            continue                                % Advance down-path.
        end
        
        % Sort iPathVert_EdgeIDs from up-path edge to down-path edge.
        iupEdgeID   = find(iPathVertID_EdgeIDs == upEdgeID);
        sortedEdgeIDs	= iPathVertID_EdgeIDs([iupEdgeID:end,1:iupEdgeID-1]);
        idownEdgeID	= find(sortedEdgeIDs == downEdgeID);
        if idownEdgeID == 2
            sortedEdgeIDs	= [sortedEdgeIDs(1), fliplr(sortedEdgeIDs(2:end))];
        end
        
        % Identify every other edge along path wrt the sorted edges.
        for iEdge	= 2:totalNumEdges-1          	% Do not remove up/downEdges.
            % Check if edge has been flagged.
            if sortedEdgeIDs(iEdge) == 0            % Edge flagged.
                continue                            % Skip to next edge.
            end
            
            % Check if edge jdx's ElemIDs have been flagged.
            iEdgeElemIDs	= edge2Elems(sortedEdgeIDs(iEdge),:);
            if any(iEdgeElemIDs == 0)               % ElemID flagged.
                continue                            % Skip to next edge.
            end
            
            % Store EdgeID for removal, update counter.
            removedEdgeIDs(i_removedEdgeIDs)	= sortedEdgeIDs(iEdge);
            vert2Edges(ismember(...             % Flag used edges.
                vert2Edges,removedEdgeIDs(1:i_removedEdgeIDs)))	= 0;
            i_removedEdgeIDs	= i_removedEdgeIDs + 1;

            % Flag ElemIDs that are now used.
            edge2Elems(ismember(edge2Elems,iEdgeElemIDs))	= 0;
        end        
    end
end

% Index bVertIDs to Domain.
bVertIDs    = VertIDs(bVertIDs);
