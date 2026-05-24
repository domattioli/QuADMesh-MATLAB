function newTris = splitQuad(CM,ElemIDs)
%SPLITQUADS Split each quadrilateral into 2 triangles.
%   newTris = SPLITQUADS(CM,ElemIDs) for
%
%   Note: I coded this last minute and it probably only works for one quad
%   at a time. It'll likely be a valuable tool for us in the future,
%   assuming it is optimized for inputs of more than one quad.
%   
%   Example:
%
%   See also:
%==========================================================================

% Initialize output.
newTris = zeros(numel(ElemIDs)*2,3);

% Get quad connectivity.
quadConn	= CM.ConnectivityList(ElemIDs,:);

% Build newTris' connectivity.
newTris(1:2:end,:)  = quadConn(:,[1 2 4]);
newTris(2:2:end,:)  = quadConn(:,[2 3 4]);
end