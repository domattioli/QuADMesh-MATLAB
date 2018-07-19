% function [Path] = PathRewind(i)
% Retraces a path back to a specified node along that path, removing all
% nodes along the way.

% Delete the current path endnode and undo the corresponding changes to the
% attributed arrays.
if JuncFlg{NPaths}(i)
    if NPaths > 1
        LoneNodes(end+1) = CPN;
    end
    Path{NPaths}(i) = 0;
    CurPathYN{NPaths}(CPN) = false;
    NodeNPaths(CPN) = NodeNPaths(CPN) - 1;
    JuncFlg{NPaths}(i) = false;
    NJuncOnPath(NPaths) = NJuncOnPath(NPaths) - 1;
else
    if NPaths > 1
        LoneNodes(end+1) = CPN;
    end
    Path{NPaths}(i) = 0;
    CurPathYN{NPaths}(CPN) = false;
    NodeNPaths(CPN) = NodeNPaths(CPN) - 1;
end

% Determine the edge that was previously added to path, remove it, and undo
% changes to EdgeNPaths, and the list of unvisited edges.
if max(sum(BE2V == [Path{NPaths}(i-1),CPN],2)) > 1
    L = sum(BE2V == [Path{NPaths}(i-1),CPN],2);
    L = find(L == 2);
    EdgeNPaths(L) = EdgeNPaths(L) - 1;
    if NPaths > 1
        LoneBEdges(end+1) = L;
    end
elseif max(sum(BE2V == [CPN,Path{NPaths}(i-1)],2)) > 1
    L = sum(BE2V == [CPN,Path{NPaths}(i-1)],2);
    L = find(L == 2);
    EdgeNPaths(L) = EdgeNPaths(L) - 1;
    if NPaths > 1
        LoneBEdges(end+1) = L;
    end
end

i = i-1;
alltried = true;

% Check whether the next previous node is a junction, and whether all of
% its connections have already been tried. If it is a junction, but not all
% of its connections have been tried, then leave this script and continue
% along the "untried" branch.
if JuncFlg{NPaths}(i)
    TriedNodes{NPaths}(CPN) = true;
    CPN = Path{NPaths}(i);
    chkN = find(NodeCL(CPN,1:end) ~= 0);
    q = 1;
    while q < length(chkN)+1
        AdjN = NodeCL(CPN,chkN(q));
        % Filter out nodes already in current path and "tried" branches
        if CurPathYN{NPaths}(AdjN) || TriedNodes{NPaths}(AdjN)
            chkN(q) = [];
        else
            q = q + 1;
        end
    end
    % If the connected nodes have all been tried or are already members
    % of the path, then we also delete this junction node from the path
    % and continue backwards. Otherwise, do not enter the subsequent
    % loop.
    if isempty(chkN)
        % Preemptively undo changes to junction data arrays.
        JuncFlg{NPaths}(i) = false;
        NJuncOnPath(NPaths) = NJuncOnPath(NPaths) - 1;
    else
        alltried = false;
    end
end

% Repeat the above procedures for every node along the path, going
% backwards, until we reach a junction. If we have not already tried adding
% one of the junction connections to the path, then we leave this
% loop/script, add the "untried" node and continue adding nodes to the path,
% in order to see if we can get a "closed" path. However, we will come back
% here if that doesn't work. If all the connections to the found junction
% have already been tried, then we proceed even further back to the next
% previous junction until we find a junction with an "untried" branch.
while alltried && i > 1
    CPN = Path{NPaths}(i);
    
    if NPaths > 1
        LoneNodes(end+1) = CPN;
    end
    Path{NPaths}(i) = 0;
    CurPathYN{NPaths}(CPN) = false;
    NodeNPaths(CPN) = NodeNPaths(CPN) - 1;
    
    % Determine the edge that was previously added to path, remove it, and undo
    % changes to EdgeNPaths, and the list of unvisited edges.
    if max(sum(BE2V == [Path{NPaths}(i-1),CPN],2)) > 1
        L = sum(BE2V == [Path{NPaths}(i-1),CPN],2);
        L = find(L == 2);
        EdgeNPaths(L) = EdgeNPaths(L) - 1;
        if NPaths > 1
            LoneBEdges(end+1) = L;
        end
    elseif max(sum(BE2V == [CPN,Path{NPaths}(i-1)],2)) > 1
        L = sum(BE2V == [CPN,Path{NPaths}(i-1)],2);
        L = find(L == 2);
        EdgeNPaths(L) = EdgeNPaths(L) - 1;
        if NPaths > 1
            LoneBEdges(end+1) = L;
        end
    end
    
    i = i-1;
    % Check whether the next previous node is a junction, and whether all of
    % its connections have already been tried. If it is a junction, but not all
    % of its connections have been tried, then leave this script and continue
    % along the "untried" branch.
    if JuncFlg{NPaths}(i)
        TriedNodes{NPaths}(CPN) = true;
        CPN = Path{NPaths}(i);
        chkN = find(NodeCL(CPN,1:end) ~= 0);
        q = 1;
        % Filter out nodes already in current path and "tried" branches
        while q < length(chkN)+1
            AdjN = NodeCL(CPN,chkN(q));
            if CurPathYN{NPaths}(AdjN) || TriedNodes{NPaths}(AdjN)
                chkN(q) = [];
            else
                q = q + 1;
            end
        end
        % If the connected nodes have all been tried or are already members
        % of the path, then we also delete this junction node from the path
        % and continue backwards. Otherwise, leave the loop.
        if isempty(chkN)
            % Preemptively undo changes to junction data arrays.
            JuncFlg{NPaths}(i) = false;
            NJuncOnPath(NPaths) = NJuncOnPath(NPaths) - 1;
        else
            alltried = false;
        end
    end
    
end

% Once we leave the above loop, a junction has been reached that has a
% currently "untried" branch connected to it. We leave the script and 
% continue building a path along the first remaining branch, but if we have
% rewound back to the first node in the path, we need to update some
% variables first.

if i == 1
    TriedNodes{NPaths}(CPN) = true;
    CPN = Path{NPaths}(i);
    chkN = find(NodeCL(CPN,1:end) ~= 0);
    q = 1;
    % Filter out nodes already in "tried" branches
    while q < length(chkN)+1
        AdjN = NodeCL(CPN,chkN(q));
        if TriedNodes{NPaths}(AdjN)
            chkN(q) = [];
        else
            q = q + 1;
        end
    end
end