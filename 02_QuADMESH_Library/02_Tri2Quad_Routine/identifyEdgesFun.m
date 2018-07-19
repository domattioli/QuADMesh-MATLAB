function [Domain,subDomain,ElemIDs,VertIDs,bEdgeIDs,bVertIDs,removedEdgeIDs]...
    = identifyEdgesFun(Domain,iLayer)
%IDENTIFYEDGESFUN Creates a quadrangular or mixed-element mesh.
%   [Domain,subDomain] = IDENTIFYEDGESFUNC
%
%   See also: PATHSONOV, TRI2QUADROUTINE.
%==========================================================================

% Get elems of layer; create sub-domain CHILmesh object.
ElemIDs	= [Domain.Layers.OE{iLayer}; Domain.Layers.IE{iLayer}];
subDomain	= CHILmesh(Domain.ConnectivityList(ElemIDs,:),Domain.Points);
VertIDs	= Domain.Layers.OV{iLayer};                 % Verts of outer boundary.
hold on;subDomain.plot(1:subDomain.nElems,'elemcolor',[.9 .9 .9]);
subDomain.plotPoint(VertIDs);

% Compute unique paths along outer vertices of subDomain/iLayer.
Path	= PathsOnOV(iLayer,Domain);                 % Verts indexed wrt Point List.

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
% Domain.plotPoint(bVertIDs,'color','b');pause

% Get adjacency lists for reference, flag these throughout routine.
vert2Edges	= subDomain.vert2Edge('VertIDs',ubVertIDs,'store','m');
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
    for iPathVertID = 2:94%6%length(pathVertIDs)-1
subDomain.plotPoint(VertIDs(pathVertIDs(iPathVertID)),'color','g'); %   downEdgeID = 448;
        % Get edges incident to iPathVertID and their attached elems.
        ivert2Edges	= find(ubVertIDs == VertIDs(pathVertIDs(iPathVertID)));
        iPathVertID_EdgeIDs	= vert2Edges(ivert2Edges,vert2Edges(ivert2Edges,:) > 0);
        num_Edges	= length(iPathVertID_EdgeIDs);  % Unused edges of vert.
        
        % Identify uppath, downpath edges along subDomain boundary.
        adjEdgeIDs	= iPathVertID_EdgeIDs(ismember(iPathVertID_EdgeIDs,bEdgeIDs));
        adjEdgeVertIDs  = subDomain.edge2Vert(adjEdgeIDs);
        upEdgeID    = downEdgeID;                   % Advance downpath.
        downEdgeID  = adjEdgeIDs(sum(ismember(adjEdgeVertIDs,...
            VertIDs(pathVertIDs(iPathVertID+1))),2) > 0);
        if num_Edges == 2                           % Only boundary edges remain.
            continue                                % Advance down-path.
        end
        
        % Sort iPathVert_EdgeIDs from up-path edge to down-path edge.
        %***** Note: this can be avoided if vert2edges are oriented CW/CCW.
        iPathVertID_ElemIDs	= subDomain.edge2Elem(iPathVertID_EdgeIDs);
        if any(sum(iPathVertID_ElemIDs == 0,1) == size(iPathVertID_ElemIDs,1))
            continue                                % No edges to remove.
            
        else
            % Upedge 1st; down last.
            s_iPathVertID_EdgeIDs	= [upEdgeID; zeros(num_Edges-2,1); downEdgeID];                        
            downElemID	= 0;                        % Elem of downEdgeID.
            currentEdge	= find(iPathVertID_EdgeIDs == upEdgeID);
            for jdx	= 2:num_Edges-1 %       jdx = jdx + 1
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
                    [currentEdge,~]	= find(ismember(iPathVertID_ElemIDs,upElemID_neighbor));
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
subDomain.plotEdge(s_iPathVertID_EdgeIDs(jdx),'color','w');%pause
                % Flag ElemIDs that are now used.
                edge2Elems(ismember(edge2Elems,ElemIDs_jdxEdge))	= 0;
            end
        end
    end
end

% Index bVertIDs to Domain.
bVertIDs    = VertIDs(bVertIDs);
