function CM	= RemoveUnusedVertices(CM,removedVertIDs)
%REMOVEUNUSEDVERTICES Removes unused vertices in the mesh MESH.
%   CM = REMOVEUNUSEDVERTICES(CM,removedVertIDs) returns an updated points
%   list in CM where all vertices have valence-1 or greater.
%   
%   REMOVEUNUSEDVERTICES is required for smoothing the mesh.
%   
%   See also: FEMSMOOTHER, POSTPROCESSROUTINE.
%==========================================================================

% Add value of 1 to tally for all nodes in CM.Points after node v (chronologically).
removedVertIDs  = sort(removedVertIDs);
numUnused = length(removedVertIDs);
for idx	= 1:numUnused
    % Identify current unused vertex and next unused vertex.
    v	= removedVertIDs(idx);
    if idx < numUnused
        vNext   = removedVertIDs(idx+1);
    else
        vNext   = CM.nVerts;
    end
    
    % Identify all vertices between v and vNext in the mesh.
    iM  = ismember(CM.ConnectivityList,v+1:vNext);
    
    % Subtract idx from the index of all iM vertices.
    CM.ConnectivityList(iM)	= CM.ConnectivityList(iM) - idx;
end

% Update Mesh.
% CM.ConnectivityList(sum(CM.ConnectivityList == 0,2) > 0,:)	= [];
CM.Points(removedVertIDs,:)   = [];
CM  = CHILmesh(CM.ConnectivityList,CM.Points,CM.GridName);

