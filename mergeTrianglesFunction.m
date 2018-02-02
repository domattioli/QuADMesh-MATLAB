function elem2Vert	 = mergeTrianglesFunction(CM,ElemIDs)
%MERGETRIANGLESFUNCTION Merge set(s) of 2 adjacent tris to form 1 quad.
%   newQ = MERGETRIANGLESFUNCTION(CM,ElemIDs) returns the connectivity list
%   elem2Vert resulting from the removal of EdgeIDs from mesh CM.
%
%   See also: TRI2QUADROUTINE.
%==========================================================================

% Get vertices defining each ElemID in pair.
pairElem2Vert	= CM.elem2Vert(ElemIDs);
numOfEdges  = size(ElemIDs,1);
t1  = pairElem2Vert(1:numOfEdges,:);            % Tris to be merged.
t2  = pairElem2Vert(numOfEdges+1:end,:);

% Identify shared and unique vertices for pair of tris****There's a better way to do this****
t1_t2c123   = t1 == t2;
t1_t2c231   = t1 == t2(:,[2 3 1]);
t1_t2c312   = t1 == t2(:,[3 1 2]);
t1_common_t2    = t1_t2c123 + t1_t2c231 + t1_t2c312;
t2_t1c231   = t2 == t1(:,[2 3 1]);
t2_t1c312   = t2 == t1(:,[3 1 2]);
t2_common_t1    = t1_t2c123 + t2_t1c231 + t2_t1c312;

% Rotate t1,t2 unique vertices to column 3.
col_idx = [2 3 1;1 3 2];
for idx = 1:2
    t1_idxc	= ~t1_common_t2(:,idx);
    t2_idxc	= ~t2_common_t1(:,idx);
    t1(t1_idxc,:)	= t1(t1_idxc,col_idx(idx,:));
    t2(t2_idxc,:)   = t2(t2_idxc,col_idx(idx,:));
    t1_common_t2(t1_idxc,:)	= t1_common_t2(t1_idxc,col_idx(idx,:));
    t2_common_t1(t2_idxc,:) = t2_common_t1(t2_idxc,col_idx(idx,:));
end

% Build connectivity of new quads
elem2Vert	= [t1(:,[1 3 2]),t2(:,3)];
%%% Connectivity of new quads will be t1 with t2's unique inserted
%%% between cols 1 and 2 of t1.

