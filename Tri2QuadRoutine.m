function [Domain,time] = Tri2QuadRoutine(Domain,time)
%TRI2QUADROUTINE Creates a quadrangular or mixed-element mesh.
%   [Domain,time] = Tri2QuadRoutine(Domain,plotProgress,time)
%
%   See also: MAIN, CREATEQUADDOMAIN, POSTPROCESSROUTINE.
%==========================================================================

% Initialize output mesh.
clf;    clc;    tic
newMesh     = struct('Points',Domain.Points,'ConnectivityList',[]);

% For each layer in mesh, identify edges for removal to create quads.
for iLayer	= Domain.nLayers:-1:1                   % Work outward.
    %% 1. Identify every other edge along each path in iLayer.
    [Domain,subDomain,removedEdgeIDs,ElemIDs,VertIDs,bVertIDs]	=...
        identifyEdgesFunction(Domain,iLayer);
    
    %% 2. Remove All Indexed Edges (Merge Triangles) To Create Quads.
    % Get elements neighboring each EdgeID.
    pairElemIDs	= subDomain.edge2Elem(removedEdgeIDs(removedEdgeIDs > 0));
    
    % Merge triangles indexed by pairElemIDs across the shared edge(s).
    newMesh.ConnectivityList	 = [newMesh.ConnectivityList;...
        mergeTrianglesFunction(subDomain,pairElemIDs)];
    
    %% 3. Add/Remove Edges to Create Quads/Remove Remaining Tris.
    % Identify remaining triangles in path.
    remainingElemIDs    = ElemIDs(~ismember(ElemIDs,ElemIDs(pairElemIDs)));
    
    % Convert remaining triangles to quads or remove them from mesh.
    [Domain,newMesh] = triangleRemovalFunction(Domain,newMesh,...
        remainingElemIDs,iLayer,VertIDs,bVertIDs);
end

%%  4. Build Global Quad CHILmesh Object for Post-Processing.



