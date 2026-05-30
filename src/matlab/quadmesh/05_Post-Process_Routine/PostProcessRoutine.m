function [CM,Domain]	= PostProcessRoutine(CM,Domain,canRemoveEdges,plotProgress,nSmoothIterations)
%POSTPROCESSROUTINE Improves quality of elements in the mesh.
%   [CM,Domain] = POSTPROCESSROUTINE(CM,Domain,canRemoveEdges) returns...
%
%   Operations include:
%   1)  Doublet Collapse    - 2 quads sharing 3 vertices => 1 quad.
%   2)  Quad Vertex Merge   - 1 quad w/ node2 having only 3 vertex
%                             attachments each, i.e. 5 quads in local
%                             mesh => 4 quads.
%   3)  BoundaryQuadCleanup - Shifts vertices of obtuse interior angles OR
%                           - Truncates low-quality quads from mesh.
%   4)  Unnamed func        - When 1 quad-edge has 2 valence-3 nodes.
%   5)  ControlVA           - Vertex valence 6 or more.
%   6)  RemoveUnusedVertices- Cleans-up unused verts in mesh for smoothing.
%   7)  Smoothing           - FEM smoothing that forces equil. tris, rects.

%   See also: MAIN, CREATEQUADDOMAIN, TRI2QUADROUTINE.
%==========================================================================

%% 0) Prepare For Iterative Quality Improvement Operators.
% Prepare for plotting.
if plotProgress
    mainAxis	= gca;
end

% Loop is necessary because the operations enable each other.
quadsStillBeingRemoved  = true(2,1);
numElems	= CM.nElems;
while quadsStillBeingRemoved(1)
    removedVertIDs  = [];
    quadsStillBeingRemoved(2) = true;
    while quadsStillBeingRemoved(2)
        %% 1) Remove Concave Quadrilaterals.
        [CM,removedVertIDs]	= DoubletCollapse(CM,removedVertIDs);toc
        mainAxis	= plotQualityProgress(mainAxis,CM,plotProgress);
        
        %% 2) Remove Quads w/ Valence-3 Diagonals.
        [CM,removedVertIDs]	= QuadVertexMerge_v2(CM,removedVertIDs,plotProgress);toc
        mainAxis	= plotQualityProgress(mainAxis,CM,plotProgress);
        
        % Check if another iteration is needed.
        if CM.nElems < numElems
            numElems	= CM.nElems;
        else
            quadsStillBeingRemoved(2)	= false;
        end
    end
    
    %% 3) Remove Unsmoothable Low-Quality Boundary Quads.
    if ~strcmp(CM.Type,'Mixed-Element')          	% Not used in mixed-element meshes.
       [CM,removedVertIDs]	= CleanupBoundaryQuads_v2(CM,removedVertIDs,canRemoveEdges,plotProgress);toc
    end
    mainAxis	= plotQualityProgress(mainAxis,CM,plotProgress);
    
    % Check if another iteration is needed.
    if CM.nElems < numElems
        numElems	= CM.nElems;
    else
        quadsStillBeingRemoved(1)	= false;
    end
    
    %% 4) Remove Unused Vertices in Mesh.
    CM	= RemoveUnusedVertices(CM,removedVertIDs);toc
end

%% 5) Smooth Mesh.
try
    CM	= FEMSmooth(CM);toc
    if plotProgress
        cla;	CM.plot;
    end
    CM	= MCSmooth(CM,plotProgress,nSmoothIterations);toc
catch
    fprintf('\nFEMSmooth failed; Likely due to size of mesh\n\n');
    CM	= MCSmooth(CM,plotProgress,nSmoothIterations);toc
end

%% 99) Reorganize Quads Adjacent To Edge With 2 Valence-3 Nodes.
% CM  = unnamedfunc(CM,removedVertIDs);toc
% if plotProgress
%     cla;	CM.plot;
% end

%% 99) Reorganize Edges for Vertices >= Valence-6.
% CM  = valenceControl(CM,removedVertIDs);toc
% if plotProgress
%     cla;	CM.plot;
% end


% usedVertIDs = unique(CM.elem2Vert);
% unusedVertIDs   = setdiff(1:CM.nVerts,usedVertIDs);
% CM	= RemoveUnusedVertices(CM,unusedVertIDs);

% mainAxis	= plotQualityProgress(mainAxis,CM,plotProgress);
% CM	= twoPartSmoother(CM,plotProgress);         % Hybrid the two smoothers.

