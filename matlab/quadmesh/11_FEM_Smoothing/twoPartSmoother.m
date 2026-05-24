function CM = twoPartSmooth(CM,plotProgress);
%TWOPARTSMOOTH Uses iterative smoothing on 2nd layer vert, FEM elsewhere.
%   CM = twoPartSmoother(CM) returns...
%   
%   See also FEMSMOOTH, MCSMOOTH.
%==========================================================================

if ~strcmp(CM.Type,'Mixed-Element')          	% Not used in mixed-element meshes.
    % Get elements of boundary layer, layer 2, and layer 3 of domain.
    ElemIDs	= [CM.Layers.OE{1}; CM.Layers.IE{1}; CM.Layers.OE{2};...
        CM.Layers.IE{2}; CM.Layers.OE{3}; CM.Layers.IE{3}];
    iElemIDs	= 1:length([CM.Layers.OE{1}; CM.Layers.IE{1}]);
    
    % Create smoothed mesh along boundary via MCsmooth.
    boundaryMesh    = CHILmesh(CM.ConnectivityList(ElemIDs,:),CM.Points);
    boundaryMesh    = MCsmooth(boundaryMesh,plotProgress,3,CM.Layers.IV{1});
    
    % Create smoothed mesh from interior elements via FEMSmoother.
    interiorMesh    = CHILmesh(CM.ConnectivityList(setdiff(...
        1:CM.nElems,ElemIDs(iElemIDs)),:),CM.Points);
    interiorMesh    = RemoveUnusedVertices(interiorMesh,CM.Layers.OV{1});
    interiorMesh    = FEMSmoother(interiorMesh);
    
    %%% From here, you would combine the two, taking the MCsmooth-ed
    %%% boundary layer and the FEMsmoother-ed interior layers.?
else
    CM  = FEMSmoother(CM);
end
