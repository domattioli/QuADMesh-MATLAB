function [CM,removedVertIDs]	= QuadVertexMerge_v2(CM,removedVertIDs,plotProgress)
%QUADVERTEXMERGE Removes quads w/ valence-3 diagonals nodes.
%   [CM,removedVertIDs] = QuadVertexMerge(CM) returns ...
%
%   See also: POSTPROCESSROUTINE.
%==========================================================================

% Keep track of vertices removed from mesh.
removedVertIDs  = [removedVertIDs; zeros(length(CM.Layers.OV{1}),1)];
iremovedVertIDs = find(removedVertIDs == 0,1,'first');

% Perform Quad Vertex Merge on quads as eligible diagonals are discovered.
eligibleDiagonalsExist  = true;
while eligibleDiagonalsExist
    % Get all diagonals in mesh not composed of 2 boundary verts or triangles.
    bVertIDs    = CM.boundaryVerts;                	% VertIDs of boundary edges.
    [VertIDs,ElemIDs]   = CM.diagonals;
    iElemIDs	= sum(ismember(VertIDs,bVertIDs),2) > 0 | sum(VertIDs,2) == 0;
    VertIDs(iElemIDs,:)	= [];                      	% Remove ineligible diags.
    ElemIDs(iElemIDs)	= [];
    
    % Get valence of diagonals' verts.
    Vert2ElemIDs	= reshape(CM.vert2Elem('VertIDs',VertIDs),length(ElemIDs),2);
    valence = cellfun(@length,Vert2ElemIDs);
    
    % Identify all ElemIDs with diagonals comprised of 2 valence-3 verts.
    ivalence= sum(valence == 3,2) == 2;
    ElemIDs	= ElemIDs(ivalence);
    if isempty(ElemIDs)
        eligibleDiagonalsExist	= false;
        continue
    end
    VertIDs	= VertIDs(ivalence,:);
    
    % Get adjacent elems of ElemIDs.=
    valenceElemIDs    = [reshape(cell2mat(Vert2ElemIDs(ivalence,1)),3,sum(ivalence));...
        reshape(cell2mat(Vert2ElemIDs(ivalence,2)),3,sum(ivalence))]';
    
    % Assemble relevant adjacency lists of quads eligible for QVM operation.
    usedQuads   = false(CM.nElems,1);
    eligibleElemIDs	= zeros(length(ElemIDs),1);
    for idx = 1:length(ElemIDs)                     % Check for mutually-exclusive QVMs.
        % Select next available quad.
        currentQuad    = ElemIDs(idx);
        
        % Check if quad is already being used.
        if usedQuads(currentQuad)                   % Quad already used.
            continue
        end
        
        % Check if any of currentQuad's adjacent elems are being used.
        adjacentQuads   = valenceElemIDs(idx,:);
        if ~any(usedQuads(adjacentQuads))           % Quad is eligible for use.
            usedQuads([currentQuad adjacentQuads])	= true;
            eligibleElemIDs(idx)    = currentQuad;
        end
    end
    ieligibleElemIDs	= eligibleElemIDs ~= 0;
    eligibleElemIDs     = eligibleElemIDs(ieligibleElemIDs);
    eligibleVertIDs     = VertIDs(ieligibleElemIDs,:);
    eligibleElemIDsValence  = valenceElemIDs(ieligibleElemIDs,:);
    
    % Remove redundancy from eligibleElemIDsValence.
    ieligibleElemIDsValence	= eligibleElemIDsValence' - repmat(eligibleElemIDs',6,1) == 0;
    eligibleElemIDsValence  = eligibleElemIDsValence';
    eligibleElemIDsValence(ieligibleElemIDsValence)	= [];
    eligibleElemIDsValence  = reshape(eligibleElemIDsValence,4,[])';
    
    % Perform Quad Vertex Merge Subroutine.
    CM	= subroutineQuadVertexMerge(CM,eligibleElemIDs,...
        eligibleVertIDs,eligibleElemIDsValence);
    removedVertIDs(iremovedVertIDs:...
        iremovedVertIDs+length(eligibleElemIDs)-1)	= eligibleVertIDs(:,2);
    iremovedVertIDs	= iremovedVertIDs+length(eligibleElemIDs);
end

% Update Outputs.
removedVertIDs(removedVertIDs == 0)	= [];
end

function CM	= subroutineQuadVertexMerge(CM,eligibleElemIDs,...
        eligibleVertIDs,eligibleElemIDsValence)
%QUADVERTEXMERGESUBROUTINE Removes quads that are stuck between 4 other quads.
%   
%   See also: QUADVERTEXMERGE.
%==========================================================================

% Get connectivity of quads on side 2.
side2Quad1Conn  = CM.ConnectivityList(eligibleElemIDsValence(:,3),:)';
side2Quad2Conn  = CM.ConnectivityList(eligibleElemIDsValence(:,4),:)';

% On side 2, index to eligibleVertIDs(:,2).
iside2Quad1eligibleVertID	= ismember(side2Quad1Conn,eligibleVertIDs(:,2)');
iside2Quad2eligibleVertID	= ismember(side2Quad2Conn,eligibleVertIDs(:,2)');

% Replace indexed vertices with eligibleVertIDs(:,1) - side 1 vertices.
side2Quad1Conn(iside2Quad1eligibleVertID) = eligibleVertIDs(:,1);
side2Quad2Conn(iside2Quad2eligibleVertID) = eligibleVertIDs(:,1);

% Update CHILmesh object.
iQuads  = [eligibleElemIDsValence(:,3); eligibleElemIDsValence(:,4)];
CM.ConnectivityList(iQuads,:)	= [side2Quad1Conn'; side2Quad2Conn'];
[~,CM]  = CM.isPolyCCW('index',iQuads);
CM.ConnectivityList(eligibleElemIDs,:)	= 0;
CM  = CHILmesh(CM.ConnectivityList(sum(CM.ConnectivityList,2) ~= 0,:),CM.Points,CM.GridName);
end

