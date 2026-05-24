function mainAxis = plotQuadProgress(mainAxis,Domain,subDomain,iLayer,removedEdgeIDs)
% Keep window size.
ax  = get(mainAxis,'XLim');
ay  = get(mainAxis,'YLim');

% Delete all patches (old mesh domain).
delete(findobj(mainAxis,'type','patch'));

% Delete all line plots except those for previous layers.
nLayersCompleted	= Domain.nLayers - iLayer;
delete(mainAxis.Children(1:(end-nLayersCompleted)));

% Plot triangles (as edges) of layers not-yet-reached.
Domain.plot([vertcat(Domain.Layers.OE{1:iLayer-1});...
    vertcat(Domain.Layers.IE{1:iLayer-1})],'elemcolor',[1 1 1]);

% Keep window.
set(gca,'XLim',ax,'YLim',ay);

% Plot "quads" by only plotting non-removed edges of iLayer (subDomain).
subDomainEdgeIDs    = (1:subDomain.nEdges)';
subDomain.plotEdge(setdiff(subDomainEdgeIDs,removedEdgeIDs(removedEdgeIDs > 0)),'color','k');
drawnow
end