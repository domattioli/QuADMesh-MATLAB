function EdgeIDs	= CCWEdgesAroundVertsFun(CM,VertIDs)
%CCWEDGESAROUNDVERTSFUN Sorts edges (and verts) around a vert in CCW order.
%   Domain	= orderEdgesAroundVert(Domain,VertIDs) returns...
%   
%   See also:
%==========================================================================

%% Use Polar Coordinates.
%%% Alternative; set each vert as a local (0,0) then convert all its
%%% adjacent verts to polar coordinates, then sort them by their degree.
if nargin == 1
    VertIDs     = (1:CM.nVerts)';
end
EdgeIDs = CM.vert2Edge('VertIDs',VertIDs);
for idx = 1:length(VertIDs)
    % Get vertices of edges connected to idx.
    vert2Edges	= EdgeIDs{idx};
    vert2Edge2VertIDs	= CM.edge2Vert(vert2Edges);
    polyVertIDs	= zeros(size(vert2Edge2VertIDs,1),1);
    for jdx = 1:length(polyVertIDs)
        polyVertIDs(jdx)= vert2Edge2VertIDs(jdx,...
            ~ismember(vert2Edge2VertIDs(jdx,:),VertIDs(idx)));
    end
    
    % Get X-Y coordinates of vertices defining polygon.
    X   = CM.Points(polyVertIDs,1);
    Y   = CM.Points(polyVertIDs,2);
    
    % Shift X-Y such that idx is the reference point (datum [0,0]).
    idxXY   = CM.Points(VertIDs(idx),1:2);
    X   = X - idxXY(1);
    Y   = Y - idxXY(2);
    
    % Convert X-Y to polar coordinates, sort to CCW order.
    theta   = cart2pol(X,Y);
    [~,itheta]	= sort(theta,'ascend');             % Ensures CCW orientation.
    
    % Reorder EdgeIDs.
    EdgeIDs{idx}	= vert2Edges(itheta);
end

%% Use Convex hull.
% %%% Note: I don't think this will always catch all verts via convhull?
% tic
% EdgeIDs = Domain.vert2Edge('VertIDs',1:Domain.nVerts);
% for idx = 1:Domain.nVerts
%     % Get vertices of edges connected to idx.
%     vert2Edges	= EdgeIDs{idx};
%     polyVertIDs	= Domain.edge2Vert(vert2Edges);
%     VertIDs     = zeros(size(polyVertIDs,1),1);
%     
%     if length(VertIDs) == 2
%         iVertIDs	= [VertIDs; idx];
%         
%     else
%         for jdx = 1:length(VertIDs)
%             VertIDs(jdx)    = polyVertIDs(jdx,~ismember(polyVertIDs(jdx,:),idx));
%         end
%         % Get X-Y coordinates of vertices defining polygon.
%         X   = Domain.Points(VertIDs,1);
%         Y   = Domain.Points(VertIDs,2);
%         
%         % Compute convex hull of X-Y points.
%         iVertIDs	= convhull(X,Y);
%     end
%     
%     % Reorder edge2Vert and vert2Edge.
% %     Domain.Adjacencies.Edge2Vert(vert2Edges)  = polyVertIDs(iVertIDs(1:end-1),:);
% %     Domain.Adjacencies.Cert2Edge{idx}   = vert2Edges(iVertIDs(1:end-1));
% end
% toc
