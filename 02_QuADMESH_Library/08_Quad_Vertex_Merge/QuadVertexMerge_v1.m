function [CM,removedVertIDs]	= QuadVertexMerge_v1(CM)
%QUADVERTEXMERGE Removes quads w/ valence-3 diagonals nodes.
%   [CM,removedVertIDs] = QuadVertexMerge(CM) returns ...
%
%   At some point, change code to not have the stupid vertex
%   attachments part and so that the rest of the code operates
%   soley on information provided by Q (don't output T). Also,
%   make it so other topological operations are incorporated
%   into this, i.e. a "QuadRemoval" function that calls QVM and
%   other functions.
%   See also: POSTPROCESSROUTINE, DOUBLETCOLLAPSE, TRUNCATEBOUNDARYQUADS.
%==========================================================================

% Identify diagonals not extending from the mesh boundaries.
[VertIDs,ElemIDs]	= CM.diagonals('store','m');
ibVertIDs   = CM.edge2Vert(CM.boundaryEdges);       % Boundary diags.
VertIDs(ibVertIDs,:)	= [];                    	% Remove D that extend
ElemIDs(ibVertIDs)	= [];                           % from CM boundaries
idxTriElemIDs	= sum(VertIDs == 0,2) > 0;        	% Triangles.
VertIDs(idxTriElemIDs,:)= [];                     	% Remove D of tris.
ElemIDs(idxTriElemIDs)	= [];

% Get valence of VertIDs.
valenceVertIDs	= {CM.vert2Elem('vertids',VertIDs(:,1),'store','m'),...
    CM.vert2Elem('vertids',VertIDs(:,2),'store','m')};
maxValence	= max([size(valenceVertIDs{1},2),size(valenceVertIDs{2},2)]);

% Continue until all eligible quads are removed.
stoppingCriterionMet = false;
while ~stoppingCriterionMet
    % Index to eligible diagonals.
    idxEligibleD	= sum([sum(valenceVertIDs{1} > 0,2) == 3,...
        sum(valenceVertIDs{2} > 0,2) == 3],2) == 2;
    if sum(idxEligibleD) == 0
        stoppingCriterionMet    = true;
        continue
    end
    
    % Get quads of eligible diagonal.
    EligibleElemID	= ElemIDs(find(idxEligibleD,1,'first'));
end