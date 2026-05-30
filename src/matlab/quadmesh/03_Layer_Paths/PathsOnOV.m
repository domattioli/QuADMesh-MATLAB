function [Path] = PathsOnOV(iLayer,Domain)
% figure('units','normalized','outerposition',[0 0 1 1])
% plot(Domain)
% hold
Layers = Domain.Layers;
% Process the connectivity list of the outer elements in the layer
CL = Domain.ConnectivityList([Layers.OE{iLayer};Layers.IE{iLayer}],:);
CP = Domain.Points(1:max(max(CL)),:);
LocCM = CHILmesh(CL,CP);
% Get list of outer vertices and locally index their global node indices in
% decreasing order (i.e. the outer vertices in a layer are ordered smallest
% in global index to highest. This treatment sets up the order for the
% local indices, treating only the outer vertices as the local nodes)
NodeLoc2Gl = Layers.OV{iLayer};
NodeLoc2Gl = sort(NodeLoc2Gl);
NLocNodes = length(NodeLoc2Gl);

% Obtain local boundary edge list for outer vertices/elements
BE = LocCM.boundaryEdges;
% Obtain local edge to element list
Ed2E = LocCM.edge2Elem;
% Obtain local edge to vert list
BE2V = LocCM.edge2Vert;
% Obtain local boundary edge to vert list
BE2V = BE2V(BE,:);

% Obtain unique vertex IDs in local boundary edge to vert list and filter  
% out points not outer vertices.
RshBE = unique(BE2V);
for i = 1:length(RshBE)
    if ~(max(RshBE(i) == NodeLoc2Gl))
        BE2V(BE2V == RshBE(i)) = 0;
    end
end
% Delete any edges which contain a non-outer vertex (these are not actually
% boundary edges).
i = 1;
while i < size(BE2V,1) + 1
    if max(BE2V(i,:) == 0)
        BE2V(i,:) = [];
        BE(i) = [];
    else
        i = i + 1;
    end
end
% Convert global node numbers to local for edge to vert list.
L{1} = (1:size(BE2V,1));
L{2} = (1:size(BE2V,1));
for i = 1:NLocNodes
    for j = 1:2
        LL = BE2V(L{j},j) == NodeLoc2Gl(i);
        BE2V(L{j}(LL),j) = i;
        L{j}(LL) = [];
    end
end

% Obtain sizes, allocate, and populate arrays for local connectivity and
% points lists.
Dim = size(Domain.Points,2);
% Retreive the local points list for the outer vertices.
LocP = zeros(NLocNodes,Dim);
for i = 1:NLocNodes
    LocP(i,:) = Domain.Points(NodeLoc2Gl(i),:);
end
% plot3(LocP(:,1),LocP(:,2),LocP(:,3),'k*','MarkerSize',10,'LineWidth',2)
% Allocate and construct an adjacency matrix for the local nodes
OAdj = zeros(length(Layers.OV{iLayer}));
for i = 1:size(BE,1)
    p1 = BE2V(i,1);
    p2 = BE2V(i,2);
    
    OAdj(p1,p2) = 1;
    OAdj(p2,p1) = 1;
end
%------------------------------------------
% Build paths
%------------------------------------------
NPaths = 1; % Index to track number of current paths.
% Allocate path array (assume at first it contains all nodes, trim later)
Path{1} = zeros(NLocNodes,1);
% Allocate logical array for checking whether current path node is a junction
JuncFlg{1} = false(NLocNodes,1);
% Allocate array for storing number of path(s) each local node appears in.
NodeNPaths = zeros(NLocNodes,1);
% Allocate array for storing number of path(s) each local edge appears in.
EdgeNPaths = zeros(length(BE),1);
% Allocate logical array for checking whether current node exists in
% current path
CurPathYN{1} = false(NLocNodes,1);
% Evaluate number of connections for each local node
SumOAdj = sum(OAdj);
% Initialize counter for number of junction nodes on path.
NJuncOnPath(1) = 0;
% Initialize array for trial and error
TriedNodes{1} = false(NLocNodes,1);
% Build a nodal connectivity list
NodeCL = zeros(NLocNodes,max(SumOAdj));
for i = 1:NLocNodes
    tmp = find(OAdj(i,:));
    L = length(tmp);
    NodeCL(i,1:L) = tmp;
end
% Begin to build path at a junction (i.e. a node with greater than 2 
% connections) if found. Otherwise begin at first local node.
WhereJunc = find(SumOAdj > 2);
if isempty(WhereJunc)
    Path{1}(1) = 1;
    JuncFlg{1}(1) = false;
    CurPathYN{1}(1) = true;
    NodeNPaths(1) = NodeNPaths(1) + 1;
else
    wj = WhereJunc(1);
    Path{1}(1) = wj;
    JuncFlg{1}(1) = true;
    CurPathYN{1}(wj) = true;
    NodeNPaths(wj) = NodeNPaths(wj) + 1;
    NJuncOnPath(1) = 1; % Store number of junctions on path
end                     

CPN = Path{1}(1); % CPN = CURRENT PATH NODE
i = 1;
loopcounter = 0;
while true
    loopcounter = loopcounter + 1;
    if loopcounter > 1e5
        disp('Error: a path cannot be closed.')
        break;
    end
    CPNold = CPN;
    % If the first and current nodes are connected by an edge (and the 
    % current node is not the second node in the path), then the path has
    % successfully closed, so take no further action.
    if i > 2 && (max(sum(BE2V == [Path{1}(1),CPN],2)) > 1 || max(sum(BE2V == [CPN,Path{1}(1)],2)) > 1)
        chkN = [];
    else
        i = i + 1;
        % Load the list of adjacent nodes to consider
        chkN = find(NodeCL(CPN,1:end) ~= 0);
    end
    q = 1;
    % Filter out nodes that are already in the path.
    while q < length(chkN)+1
        AdjN = NodeCL(CPN,chkN(q));
        if CurPathYN{1}(AdjN)
            chkN(q) = [];
        else
            q = q + 1;
        end
    end
    j = 1;
    while j < length(chkN)+1
        AdjN = NodeCL(CPN,chkN(j));
        % Check whether or not nodes adjacent to current node are in 
        % current path and whether or not they are junction nodes. 
        if ~(CurPathYN{1}(AdjN))
            % If the node is neither, add the node to the path.
            if (SumOAdj(AdjN) < 3)
                Path{1}(i) = AdjN;
                CurPathYN{1}(AdjN) = true;
                JuncFlg{1}(i) = false;
                NodeNPaths(AdjN) = NodeNPaths(AdjN) + 1;
                CPN = AdjN;
                % Determine the edge that has been added to path and update
                % EdgeNPaths.
                if max(sum(BE2V == [Path{1}(i-1),CPN],2)) > 1
                    L = sum(BE2V == [Path{1}(i-1),CPN],2);
                    L = L == 2;
                    EdgeNPaths(L) = EdgeNPaths(L) + 1;
                elseif max(sum(BE2V == [CPN,Path{1}(i-1)],2)) > 1
                    L = sum(BE2V == [CPN,Path{1}(i-1)],2);
                    L = L == 2;
                    EdgeNPaths(L) = EdgeNPaths(L) + 1;                    
                end
                break;
            % If adjacent node is a junction, not in currently in the path, 
            % and all other adjacent nodes not currently in the path are 
            % junctions, then choose a remaining node to add to the path.
            elseif (min(SumOAdj(NodeCL(CPN,chkN(j:end))) > 2))
                 % Of all remaining connected nodes, choose to add a
                 % junction that results in a path edge on the same element
                 % as the previous path edge if possible. Otherwise choose
                 % any junction arbitrarily.
                jNodes = NodeCL(CPN,chkN(j:end));
                len = length(jNodes);
                if i > 2
                    A = [LocP(Path{1}(i-1),1)-LocP(Path{1}(i-2),1),LocP(Path{1}(i-1),2)-LocP(Path{1}(i-2),2)];
                end
                % If only one node remains, then add it to the
                % path, or if this is only the second node being
                % added to the list, just choose the first node
                % from the list of remaining potential nodes.
                if (len == 1 || i < 3)
                    ind = 1;
                % If there is more than one node remaining for
                % consideration, then choose the node which would
                % result in an edge on the same element as the previous
                % path edge (if such a node exists).
                else
                    jNodestemp = jNodes(1); % Store the first remaining node just in case none connected to the same element are found.
                    
                    % Determine edge ID, of the previous path edge.
                    if max(sum(BE2V == [Path{1}(i-2),Path{1}(i-1)],2)) > 1
                        L1 = sum(BE2V == [Path{1}(i-2),Path{1}(i-1)],2);
                    elseif max(sum(BE2V == [Path{1}(i-1),Path{1}(i-2)],2)) > 1
                        L1 = sum(BE2V == [Path{1}(i-1),Path{1}(i-2)],2);
                    end
                    L1 = L1 == 2;
                    % Determine elements connected to previous path
                    % edge.
                    L1 = Ed2E(BE(L1),:);
                    L1 = L1(L1 ~= 0);
                    q = 1;
                    % Determine the elements connected to the
                    % resulting path edges from adding each
                    % remaining junction node under consideration.
                    while q < length(jNodes) + 1
                        AdjN = jNodes(q);
                        if max(sum(BE2V == [Path{1}(i-1),AdjN],2)) > 1
                            L2 = sum(BE2V == [Path{1}(i-1),AdjN],2);
                        elseif max(sum(BE2V == [AdjN,Path{1}(i-1)],2)) > 1
                            L2 = sum(BE2V == [AdjN,Path{1}(i-1)],2);
                        end
                        L2 = L2 == 2;
                        L2 = Ed2E(BE(L2),:);
                        L2 = L2(L2 ~= 0);
                        % If none of the connected elements are in
                        % common with the previous path edge, then
                        % remove this node from the list of
                        % considered nodes. Otherwise, continue.
                        if ~max(L2 == L1)
                            jNodes(q) = [];
                        else
                            q = q + 1;
                        end
                    end
                    len = length(jNodes);
                    % If only one edge shares an element with the
                    % previous edge, pick the corresponding node.
                    if len == 1
                        ind = 1;
                    % If there is more than one node remaining for
                    % consideration, then choose the node which results in
                    % the smallest change of angle in the path.
                    elseif len > 1
                        ang = zeros(1,len);
                        for q = 1:len
                            AdjN = jNodes(q);
                            % Compute changes in angle in path due to
                            % adding each choice.
                            B = [LocP(AdjN,1)-LocP(Path{1}(i-1),1),LocP(AdjN,2)-LocP(Path{1}(i-1),2)];
                            ang(q) = dot(A,B);
                            ang(q) = ang(q)/(sqrt(A(1)^2 + A(2)^2)*sqrt(B(1)^2 + B(2)^2));
                            ang(q) = acos(ang(q));
                        end
                        disp(ang);
                        [~,ind] = min(ang);
                        % If the junction we first choose is already in the
                        % current path, then choose the node which changes
                        % the path direction next least
                        
                        while CurPathYN{1}(jNodes(ind)) && length(ang) > 1
                            ang(ind) = [];
                            jNodes(ind) = [];
                            [~,ind] = min(ang);
                        end
                    end
                end
                if ~isempty(jNodes)
                    AdjN = jNodes(ind);
                else
                    AdjN = jNodestemp;
                end
                if ~CurPathYN{1}(AdjN)
                    Path{1}(i) = AdjN;
                    JuncFlg{1}(i) = true;
                    CurPathYN{1}(AdjN) = true;
                    NodeNPaths(AdjN) = NodeNPaths(AdjN) + 1;
                    NJuncOnPath(1) = NJuncOnPath(1) + 1;
                    CPN = AdjN;
                    % Determine the ID of the edge that has been added to 
                    % path and update EdgeNPaths.
                    if max(sum(BE2V == [Path{1}(i-1),CPN],2)) > 1
                        L = sum(BE2V == [Path{1}(i-1),CPN],2);
                        L = L == 2;
                        EdgeNPaths(L) = EdgeNPaths(L) + 1;
                    elseif max(sum(BE2V == [CPN,Path{1}(i-1)],2)) > 1
                        L = sum(BE2V == [CPN,Path{1}(i-1)],2);
                        L = L == 2;
                        EdgeNPaths(L) = EdgeNPaths(L) + 1;
                    end
                    break;
                end
            end
        end
        j = j + 1;
    end
%     ii = i;
%     if i <= length(Path{NPaths})
%         if Path{NPaths}(i) == 0
%             ii = i-1;
%         end
%     end
%     if mod(NPaths,2) == 1
%         if ii <= length(Path{NPaths})
%             plot3(LocP(Path{NPaths}(1:ii),1),LocP(Path{NPaths}(1:ii),2),LocP(Path{NPaths}(1:ii),3),'-r*','MarkerSize',10,'LineWidth',2);
%         end
%     else
%         if ii <= length(Path{NPaths})
%             plot3(LocP(Path{NPaths}(1:ii),1),LocP(Path{NPaths}(1:ii),2),LocP(Path{NPaths}(1:ii),3),'-b*','MarkerSize',10,'LineWidth',2);
%         end
%     end
%     pause(.01)

    % If no adjacent node can be found that hasn't already been added to 
    % the path, then the path has ended.
    if CPNold == CPN
        % If the first and last nodes are connected by an edge, then the
        % path has successfully closed. Otherwise, there has been an error
        % and we must rewind.
        if max(sum(BE2V == [Path{1}(1),CPN],2)) > 1 || max(sum(BE2V == [CPN,Path{1}(1)],2)) > 1
            break;
        else
            i = i - 1;
            % Rewind along the path, removing each node until the nearest
            % junction is reached that has a currently "untried" branch.
            pathRewind
            % Add the first node of the "untried" branch to the path, and
            % continue business as usual from there.
            CPN = NodeCL(CPN,chkN(1));
            i = i + 1;
            Path{1}(i) = CPN;
            CurPathYN{1}(CPN) = true;
            NodeNPaths(CPN) = NodeNPaths(CPN) + 1;
            if SumOAdj(CPN) > 2
                JuncFlg{1}(i) = true;
                NJuncOnPath(1) = NJuncOnPath(1) + 1;
            else
                JuncFlg{1}(i) = false;
            end
           
            % Determine the ID of the edge that has been added to
            % path and update EdgeNPaths.
            if max(sum(BE2V == [Path{1}(i-1),CPN],2)) > 1
                L = sum(BE2V == [Path{1}(i-1),CPN],2);
                L = L == 2;
                EdgeNPaths(L) = EdgeNPaths(L) + 1;
            elseif max(sum(BE2V == [CPN,Path{1}(i-1)],2)) > 1
                L = sum(BE2V == [CPN,Path{1}(i-1)],2);
                L = L == 2;
                EdgeNPaths(L) = EdgeNPaths(L) + 1;
            end
        end
    end
end

% Delete all the zeros left in the path and trim junction flag array
JuncFlg{1}(Path{1} == 0) = [];
Path{1}(Path{1} == 0) = [];

% if mod(NPaths,2) == 1
%     plot3(LocP(Path{NPaths},1),LocP(Path{NPaths},2),LocP(Path{NPaths},3),'-r*','MarkerSize',10,'LineWidth',2)
% else
%     plot3(LocP(Path{NPaths},1),LocP(Path{NPaths},2),LocP(Path{NPaths},3),'-b*','MarkerSize',10,'LineWidth',2)
% end
% pause(.1)

% Next steps: identify outer vectors and edegs unvisited by any path. If they 
% exist, repeat the above procedure for those nodes (with slight modifications).
LoneBEdges = find(EdgeNPaths == 0);
% Count the path's "closed loop" edge as a visited boundary edge, even 
% though it does not actually appear in the path.
if max(sum(BE2V(LoneBEdges,:) == [Path{1}(end),Path{1}(1)],2)) > 1
    L = sum(BE2V(LoneBEdges,:) == [Path{1}(end),Path{1}(1)],2);
    L = L == 2;
    EdgeNPaths(LoneBEdges(L)) = EdgeNPaths(LoneBEdges(L)) + 1;
elseif max(sum(BE2V(LoneBEdges,:) == [Path{1}(1),Path{1}(end)],2)) > 1
    L = sum(BE2V(LoneBEdges,:) == [Path{1}(1),Path{1}(end)],2);
    L = L == 2;
    EdgeNPaths(LoneBEdges(L)) = EdgeNPaths(LoneBEdges(L)) + 1;
end
                            
LoneBEdges = find(EdgeNPaths == 0);
LoneNodes = find(NodeNPaths == 0);
while (LoneBEdges)
    NPaths = NPaths + 1;
    % Allocate new path array (assume at first that path contains all remaining nodes)
    L = 0;
    for i = 1:length(Path)
        L = L + length(Path{i});
    end
    Path{NPaths} = zeros(max(2,NLocNodes-L),1);
    % Allocate logical array for checking whether current path node is a junction
    JuncFlg{NPaths} = false(NLocNodes-L,1);
    % Allocate logical array for checking whether current node exists in
    % current path
    CurPathYN{NPaths} = false(NLocNodes,1);
    NJuncOnPath(NPaths) = 0;
    
    % Initialize array for trial and error
    TriedNodes{NPaths} = false(NLocNodes,1);

    % Check that previous path has at least one junction appearing in that
    % path. If so, then start at an unvisited node (prioritizing non-junctions)
    % connected to any junction from the previous path, but add that 
    % junction to the top of the path.
    if NJuncOnPath(NPaths-1) 
        wjtemp = 0;
        for i = 1:length(LoneNodes)
            Log = ismember(NodeCL(LoneNodes(i),:),Path{NPaths-1}(JuncFlg{NPaths-1}));
            if max(Log)
                 wj = NodeCL(LoneNodes(i),Log);
                 if SumOAdj(LoneNodes(i)) > 2 && i < length(LoneNodes)
                     wjtemp = wj(1);
                     itemp = i;
                 else
                     wj = wj(1);
                     Path{NPaths}(1) = wj;
                     JuncFlg{NPaths}(1) = true;
                     CurPathYN{NPaths}(wj) = true;
                     NodeNPaths(wj) = NodeNPaths(wj) + 1;
                     NJuncOnPath(NPaths) = 1;
                     
                     Path{NPaths}(2) = LoneNodes(i);
                     CurPathYN{NPaths}(LoneNodes(i)) = true;
                     NodeNPaths(LoneNodes(i)) = NodeNPaths(LoneNodes(i)) + 1;
                     LoneNodes(LoneNodes == wj) = [];
                     LoneNodes(LoneNodes == LoneNodes(i)) = [];
                     break;
                 end
            end
        end
        if wjtemp && i == length(LoneNodes) && Path{NPaths}(1) == 0
            wj = wjtemp;
            Path{NPaths}(1) = wj;
            JuncFlg{NPaths}(1) = true;
            CurPathYN{NPaths}(wj) = true;
            NodeNPaths(wj) = NodeNPaths(wj) + 1;
            NJuncOnPath(NPaths) = 1;
            
            Path{NPaths}(2) = LoneNodes(itemp);
            CurPathYN{NPaths}(LoneNodes(itemp)) = true;
            NodeNPaths(LoneNodes(itemp)) = NodeNPaths(LoneNodes(itemp)) + 1;
            LoneNodes(LoneNodes == wj) = [];
            LoneNodes(LoneNodes == LoneNodes(itemp)) = [];
        end
        % If there are no unvisited neighbors, then start at some unvisited
        % junction elsewhere.
        if (Path{NPaths}(1) == 0)
            if max(NodeNPaths(WhereJunc) == 0)
                wj = WhereJunc(NodeNPaths(WhereJunc) == 0);
                wj = wj(1);
                LoneNodes(LoneNodes == wj) = [];
                Path{NPaths}(1) = wj;
                JuncFlg{NPaths}(1) = true;
                CurPathYN{NPaths}(wj) = true;
                NodeNPaths(wj) = NodeNPaths(wj) + 1;
                NJuncOnPath(NPaths) = 1;
            % But if no unvisited junctions exist, and there are more
            % junctions in the layer aside from the ones in the previous
            % paths, then we need to find an unvisited node that is
            % connected to any junction (we prioritize adding non-junctions)
            elseif length(WhereJunc) ~= sum(NodeNPaths(WhereJunc) ~= 0)
                wjtemp = 0;
                for i = 1:length(LoneNodes)
                    Log = ismember(NodeCL(LoneNodes(i),:),WhereJunc);
                    if max(Log)
                        wj = NodeCL(LoneNodes(i),Log);
                        if SumOAdj(LoneNodes(i)) > 2 && i < length(LoneNodes)
                            wjtemp = wj(1);
                            itemp = i;
                        else
                            wj = wj(1);
                            Path{NPaths}(1) = wj;
                            JuncFlg{NPaths}(1) = true;
                            CurPathYN{NPaths}(wj) = true;
                            NodeNPaths(wj) = NodeNPaths(wj) + 1;
                            NJuncOnPath(NPaths) = 1;
                            
                            Path{NPaths}(2) = LoneNodes(i);
                            CurPathYN{NPaths}(LoneNodes(i)) = true;
                            NodeNPaths(LoneNodes(i)) = NodeNPaths(LoneNodes(i)) + 1;
                            LoneNodes(LoneNodes == wj) = [];
                            LoneNodes(LoneNodes == LoneNodes(i)) = [];
                            break;
                        end
                    end
                end
                if wjtemp && i == length(LoneNodes) && Path{NPaths}(1) == 0
                    wj = wjtemp;
                    Path{NPaths}(1) = wj;
                    JuncFlg{NPaths}(1) = true;
                    CurPathYN{NPaths}(wj) = true;
                    NodeNPaths(wj) = NodeNPaths(wj) + 1;
                    NJuncOnPath(NPaths) = 1;
                    
                    Path{NPaths}(2) = LoneNodes(itemp);
                    CurPathYN{NPaths}(LoneNodes(itemp)) = true;
                    NodeNPaths(LoneNodes(itemp)) = NodeNPaths(LoneNodes(itemp)) + 1;
                    LoneNodes(LoneNodes == wj) = [];
                    LoneNodes(LoneNodes == LoneNodes(itemp)) = [];
                end
            % If all of the junctions are in the previous paths, and they 
            % have no unvisited neighbors, then just pick the first 
            % unvisited node, or the first node in an unvisited edge.
            else
                if ~isempty(LoneNodes)
                    Path{NPaths}(1) = LoneNodes(1);
                    JuncFlg{NPaths}(1) = false;
                    CurPathYN{NPaths}(LoneNodes(1)) = true;
                    NodeNPaths(LoneNodes(1)) = NodeNPaths(LoneNodes(1)) + 1;
                    LoneNodes(LoneNodes == LoneNodes(1)) = [];
                else
                    CPN = BE2V(LoneBEdges(1),1);
                    Path{NPaths}(1) = CPN;
                    JuncFlg{NPaths}(1) = false;
                    CurPathYN{NPaths}(CPN) = true;
                    NodeNPaths(CPN) = NodeNPaths(CPN) + 1;
                    LoneNodes(LoneNodes == CPN) = [];
                end
            end
        end
                
    % If previous path has no junctions, but junctions do exist in the 
    % layer, then start at some unvisited junction elsewhere.
    elseif ~isempty(WhereJunc)
        if max(NodeNPaths(WhereJunc) == 0)
            wj = WhereJunc(NodeNPaths(WhereJunc) == 0);
            wj = wj(1);
            LoneNodes(LoneNodes == wj) = [];
            Path{NPaths}(1) = wj;
            JuncFlg{NPaths}(1) = true;
            CurPathYN{NPaths}(wj) = true;
            NodeNPaths(wj) = NodeNPaths(wj) + 1;
            NJuncOnPath(NPaths) = 1;
        % But if no unvisited junctions exist, then we need to find an
        % unvisited node that is connected to any junction, but start
	    % the path at the junction that the found node is connected to.
		% (The found node is the second node in the path.)
        else
            wjtemp = 0;
            for i = 1:length(LoneNodes)
                Log = ismember(NodeCL(LoneNodes(i),:),WhereJunc);
                if max(Log)
                    wj = NodeCL(LoneNodes(i),Log);
                    if SumOAdj(LoneNodes(i)) > 2 && i < length(LoneNodes)
                        wjtemp = wj(1);
                        itemp = i;
                    else
                        wj = wj(1);
                        Path{NPaths}(1) = wj;
                        JuncFlg{NPaths}(1) = true;
                        CurPathYN{NPaths}(wj) = true;
                        NodeNPaths(wj) = NodeNPaths(wj) + 1;
                        NJuncOnPath(NPaths) = 1;
                        
                        Path{NPaths}(2) = LoneNodes(i);
                        CurPathYN{NPaths}(LoneNodes(i)) = true;
                        NodeNPaths(LoneNodes(i)) = NodeNPaths(LoneNodes(i)) + 1;
                        LoneNodes(LoneNodes == wj) = [];
                        LoneNodes(LoneNodes == LoneNodes(i)) = [];
                        break;
                    end
                end
            end
            if wjtemp && i == length(LoneNodes) && Path{NPaths}(1) == 0
                wj = wjtemp;
                Path{NPaths}(1) = wj;
                JuncFlg{NPaths}(1) = true;
                CurPathYN{NPaths}(wj) = true;
                NodeNPaths(wj) = NodeNPaths(wj) + 1;
                NJuncOnPath(NPaths) = 1;
                
                Path{NPaths}(2) = LoneNodes(itemp);
                CurPathYN{NPaths}(LoneNodes(itemp)) = true;
                NodeNPaths(LoneNodes(itemp)) = NodeNPaths(LoneNodes(itemp)) + 1;
                LoneNodes(LoneNodes == wj) = [];
                LoneNodes(LoneNodes == LoneNodes(itemp)) = [];
            end
        end
        
    % If there are no junctions ANYWHERE, then just pick the first
    % unvisited node, or the first node of the first unvisited edge.
    else
        if ~isempty(LoneNodes)
            Path{NPaths}(1) = LoneNodes(1);
            JuncFlg{NPaths}(1) = false;
            CurPathYN{NPaths}(LoneNodes(1)) = true;
            NodeNPaths(LoneNodes(1)) = NodeNPaths(LoneNodes(1)) + 1;
            LoneNodes(LoneNodes == LoneNodes(1)) = [];
        else
            CPN = BE2V(LoneBEdges(1),1);
            Path{NPaths}(1) = CPN;
            JuncFlg{NPaths}(1) = false;
            CurPathYN{NPaths}(CPN) = true;
            NodeNPaths(CPN) = NodeNPaths(CPN) + 1;
            LoneNodes(LoneNodes == CPN) = [];
        end
    end  
    % If all of the above approaches failed, then just pick the first
    % unvisited node, or the first node of the first unvisted edge.
    if Path{NPaths}(1) == 0
        if ~isempty(LoneNodes)
            Path{NPaths}(1) = LoneNodes(1);
            JuncFlg{NPaths}(1) = false;
            CurPathYN{NPaths}(LoneNodes(1)) = true;
            NodeNPaths(LoneNodes(1)) = NodeNPaths(LoneNodes(1)) + 1;
            LoneNodes(LoneNodes == LoneNodes(1)) = [];
        else
            CPN = BE2V(LoneBEdges(1),1);
            Path{NPaths}(1) = CPN;
            JuncFlg{NPaths}(1) = false;
            CurPathYN{NPaths}(CPN) = true;
            NodeNPaths(CPN) = NodeNPaths(CPN) + 1;
            LoneNodes(LoneNodes == CPN) = [];
        end
    end
    
    if Path{NPaths}(2) == 0
        i = 1;
        CPN = Path{NPaths}(1);
    else
        i = 2;
        CPN = Path{NPaths}(2);
        % Determine the edge that has been added to path and update
        % EdgeNPaths, and the list of unvisited edges.
        if max(sum(BE2V == [Path{NPaths}(i-1),CPN],2)) > 1
            L = sum(BE2V == [Path{NPaths}(i-1),CPN],2);
            L = find(L == 2);
            EdgeNPaths(L) = EdgeNPaths(L) + 1;
            LoneBEdges(LoneBEdges == L) = [];
        elseif max(sum(BE2V == [CPN,Path{NPaths}(i-1)],2)) > 1
            L = sum(BE2V == [CPN,Path{NPaths}(i-1)],2);
            L = find(L == 2);
            EdgeNPaths(L) = EdgeNPaths(L) + 1;
            LoneBEdges(LoneBEdges == L) = [];
        end
    end

    loopcounter = 0;
    while true
        loopcounter = loopcounter + 1;
        if loopcounter > 1e5
           disp('Error: there exists a path that cannot be closed.')
           break;
        end
        CPNold = CPN;
        % If the first and current nodes are connected by an edge (and the
        % current node is not the second node in the path), then the path has
        % successfully closed, so take no further action.
        if i > 2 && (max(sum(BE2V == [Path{NPaths}(1),CPN],2)) > 1 || max(sum(BE2V == [CPN,Path{NPaths}(1)],2)) > 1)
            chkN = [];
        else
            i = i + 1;
            % Load the list of adjacent nodes to consider
            chkN = find(NodeCL(CPN,1:end) ~= 0);
        end
        q = 1;
        % Filter out nodes that are already in the path, or in a previous path
        % (if they are not junctions), or that have already been "tried".
        while q < length(chkN)+1
            AdjN = NodeCL(CPN,chkN(q));
            if (SumOAdj(AdjN) < 3 && ~ismember(AdjN,LoneNodes)) || CurPathYN{NPaths}(AdjN) || TriedNodes{NPaths}(AdjN)
                chkN(q) = [];
            else
                q = q + 1;
            end
        end
        
        j = 1;
        while j < length(chkN)+1
            AdjN = NodeCL(CPN,chkN(j));
            % Check whether or not nodes adjacent to current node are in 
            % current path and whether or not they are junction nodes.
            if ~(CurPathYN{NPaths}(AdjN))
                % If node is neither, then add the node to the path (if it
                % is not in a previous path).
                if (SumOAdj(AdjN) < 3 && ismember(AdjN,LoneNodes))
                    LoneNodes(LoneNodes == AdjN) = [];
                    Path{NPaths}(i) = AdjN;
                    JuncFlg{NPaths}(i) = false;
                    CurPathYN{NPaths}(AdjN) = true;
                    NodeNPaths(AdjN) = NodeNPaths(AdjN) + 1;
                    CPN = AdjN;
                    % Determine the edge that has been added to path and update
                    % EdgeNPaths, and the list of unvisited edges.
                    if max(sum(BE2V == [Path{NPaths}(i-1),CPN],2)) > 1
                        L = sum(BE2V == [Path{NPaths}(i-1),CPN],2);
                        L = find(L == 2);
                        EdgeNPaths(L) = EdgeNPaths(L) + 1;
                        LoneBEdges(LoneBEdges == L) = [];
                    elseif max(sum(BE2V == [CPN,Path{NPaths}(i-1)],2)) > 1
                        L = sum(BE2V == [CPN,Path{NPaths}(i-1)],2);
                        L = find(L == 2);
                        EdgeNPaths(L) = EdgeNPaths(L) + 1;
                        LoneBEdges(LoneBEdges == L) = [];
                    end
                    break;
                % If adjacent node is a junction, not in currently in the path,
                % and all other adjacent nodes not currently in the path are
                % junctions, then choose a remaining node to add the path.
                elseif (min(SumOAdj(NodeCL(CPN,chkN(j:end))) > 2))
                    % Of all remaining connected nodes, choose to add a
                    % junction that results in a path edge on the same element
                    % as the previous path edge if possible. Otherwise choose
                    % any junction arbitrarily.
                    
                    jNodes = NodeCL(CPN,chkN(j:end));
                    len = length(jNodes);
                    if i > 2
                        A = [LocP(Path{NPaths}(i-1),1)-LocP(Path{NPaths}(i-2),1),LocP(Path{NPaths}(i-1),2)-LocP(Path{NPaths}(i-2),2)];
                    end
                    % If only one node remains, then add it to the
                    % path, or if this is only the second node being
                    % added to the list, just choose the first node
                    % from the list of remaining potential nodes.
                    if (len == 1 || i < 3)
                        ind = 1;
                    % If there is more than one node remaining for
                    % consideration, then choose the node which would
                    % result in an edge on the same element as the previous
                    % path edge (if such a node exists).
                    else
                        % Determine edge ID, of the previous path edge.
                        jNodestemp = jNodes(1); % Store the first remaining node just in case none connected to the same element are found.
                        if max(sum(BE2V == [Path{NPaths}(i-2),Path{NPaths}(i-1)],2)) > 1
                            L1 = sum(BE2V == [Path{NPaths}(i-2),Path{NPaths}(i-1)],2);
                        elseif max(sum(BE2V == [Path{NPaths}(i-1),Path{NPaths}(i-2)],2)) > 1
                            L1 = sum(BE2V == [Path{NPaths}(i-1),Path{NPaths}(i-2)],2);
                        end
                        L1 = L1 == 2;
                        % Determine elements connected to previous path
                        % edge.
                        L1 = Ed2E(BE(L1),:);
                        L1 = L1(L1 ~= 0);
                        q = 1;
                        % Determine the elements connected to the
                        % resulting path edges from adding each
                        % remaining junction node under consideration.
                        while q < length(jNodes) + 1
                            AdjN = jNodes(q);
                            if max(sum(BE2V == [Path{NPaths}(i-1),AdjN],2)) > 1
                                L2 = sum(BE2V == [Path{NPaths}(i-1),AdjN],2);
                            elseif max(sum(BE2V == [AdjN,Path{NPaths}(i-1)],2)) > 1
                                L2 = sum(BE2V == [AdjN,Path{NPaths}(i-1)],2);
                            end
                            L2 = L2 == 2;
                            L2 = Ed2E(BE(L2),:);
                            L2 = L2(L2 ~= 0);
                            % If none of the connected elements are in
                            % common with the previous path edge, then
                            % remove this node from the list of
                            % considered nodes. Otherwise, continue.
                            if ~max(L2 == L1)
                                jNodes(q) = [];
                            else
                                q = q + 1;
                            end
                        end
                        len = length(jNodes);
                        % If only one edge shares an element with the
                        % previous edge, pick the corresponding node.
                        if len == 1
                            ind = 1;
                            % If there is more than one node remaining for
                            % consideration, then choose the node which results in
                            % the smallest change of angle in the path.
                        elseif len > 1
                            ang = zeros(1,len);
                            for q = 1:len
                                AdjN = jNodes(q);
                                % Compute changes in angle in path due to
                                % adding each choice.
                                B = [LocP(AdjN,1)-LocP(Path{NPaths}(i-1),1),LocP(AdjN,2)-LocP(Path{NPaths}(i-1),2)];
                                ang(q) = dot(A,B);
                                ang(q) = ang(q)/(sqrt(A(1)^2 + A(2)^2)*sqrt(B(1)^2 + B(2)^2));
                                ang(q) = acos(ang(q));
                            end
                            disp(ang)
                            [~,ind] = min(ang);
                            % If the junction we first choose is already in the
                            % current path, then choose the node which changes
                            % the path direction next least
                            
                            while CurPathYN{NPaths}(jNodes(ind)) && length(ang) > 1
                                ang(ind) = [];
                                jNodes(ind) = [];
                                [~,ind] = min(ang);
                            end
                        end
                    end
                    if ~isempty(jNodes)
                        AdjN = jNodes(ind);
                    else
                        AdjN = jNodestemp;
                    end
                    if ~CurPathYN{NPaths}(AdjN)
                        LoneNodes(LoneNodes == AdjN) = [];
                        Path{NPaths}(i) = AdjN;
                        JuncFlg{NPaths}(i) = true;
                        CurPathYN{NPaths}(AdjN) = true;
                        NodeNPaths(AdjN) = NodeNPaths(AdjN) + 1;
                        NJuncOnPath(NPaths) = NJuncOnPath(NPaths) + 1;
                        CPN = AdjN;
                        % Determine the edge that has been added to path and 
                        % update EdgeNPaths, and the list of unvisited edges.
                        if max(sum(BE2V == [Path{NPaths}(i-1),CPN],2)) > 1
                            L = sum(BE2V == [Path{NPaths}(i-1),CPN],2);
                            L = find(L == 2);
                            EdgeNPaths(L) = EdgeNPaths(L) + 1;
                            LoneBEdges(LoneBEdges == L) = [];
                        elseif max(sum(BE2V == [CPN,Path{NPaths}(i-1)],2)) > 1
                            L = sum(BE2V == [CPN,Path{NPaths}(i-1)],2);
                            L = find(L == 2);
                            EdgeNPaths(L) = EdgeNPaths(L) + 1;
                            LoneBEdges(LoneBEdges == L) = [];
                        end
                        break;
                    end
                end
            end
            j = j + 1;
        end
%         ii = i;
%         if i <= length(Path{NPaths})
%             if Path{NPaths}(i) == 0
%                 ii = i-1;
%             end
%         end
%         if mod(NPaths,2) == 1
%             if ii <= length(Path{NPaths})
%                 plot3(LocP(Path{NPaths}(1:ii),1),LocP(Path{NPaths}(1:ii),2),LocP(Path{NPaths}(1:ii),3),'-r*','MarkerSize',10,'LineWidth',2)
%                 axis([LocP(Path{NPaths}(ii),1)-.2 LocP(Path{NPaths}(ii),1)+.2 LocP(Path{NPaths}(ii),2)-.2 LocP(Path{NPaths}(ii),2)+.2])
%             end
%         else
%             if ii <= length(Path{NPaths})
%                 plot3(LocP(Path{NPaths}(1:ii),1),LocP(Path{NPaths}(1:ii),2),LocP(Path{NPaths}(1:ii),3),'-b*','MarkerSize',10,'LineWidth',2)
%                 axis([LocP(Path{NPaths}(ii),1)-.2 LocP(Path{NPaths}(ii),1)+.2 LocP(Path{NPaths}(ii),2)-.2 LocP(Path{NPaths}(ii),2)+.2])
%             end
%         end
%         pause(.1)
        % If no adjacent node can be found that hasn't already been added
        % to the path, then the path has ended.
        
        if CPNold == CPN
            % If the first and last nodes are connected by an edge, then the
            % path has successfully closed. Otherwise, there has been an error
            % and we must rewind.
            if max(sum(BE2V == [Path{NPaths}(1),CPN],2)) > 1 || max(sum(BE2V == [CPN,Path{NPaths}(1)],2)) > 1
                break;
            else
                i = i - 1;
                % Rewind along the path, removing each node until the nearest
                % junction is reached that has a currently "untried" branch.
                pathRewind
                % Add the first node of the "untried" branch to the path, and
                % continue business as usual from there.
                CPN = NodeCL(CPN,chkN(1));
                i = i + 1;
                LoneNodes(LoneNodes == CPN) = [];
                Path{NPaths}(i) = CPN;
                CurPathYN{NPaths}(CPN) = true;
                NodeNPaths(CPN) = NodeNPaths(CPN) + 1;
                if SumOAdj(CPN) > 2
                    JuncFlg{NPaths}(i) = true;
                    NJuncOnPath(NPaths) = NJuncOnPath(NPaths) + 1;
                else
                    JuncFlg{NPaths}(i) = false;
                end
                
                % Determine the ID of the edge that has been added to
                % path and update EdgeNPaths, and the list of unvisited edges.
                if max(sum(BE2V == [Path{NPaths}(i-1),CPN],2)) > 1
                    L = sum(BE2V == [Path{NPaths}(i-1),CPN],2);
                    L = find(L == 2);
                    EdgeNPaths(L) = EdgeNPaths(L) + 1;
                    LoneBEdges(LoneBEdges == L) = [];
                elseif max(sum(BE2V == [CPN,Path{NPaths}(i-1)],2)) > 1
                    L = sum(BE2V == [CPN,Path{NPaths}(i-1)],2);
                    L = find(L == 2);
                    EdgeNPaths(L) = EdgeNPaths(L) + 1;
                    LoneBEdges(LoneBEdges == L) = [];
                end
            end
        end
    end
    
    % Trim junction flag array if necessary and delete all the zeros left
    % in the path
    if length(JuncFlg{NPaths}) >= length(Path{NPaths})
        JuncFlg{NPaths}(Path{NPaths} == 0) = [];
    else
        L1 = length(JuncFlg{NPaths});
        L2 = length(Path{NPaths});
        JuncFlg{NPaths} = [JuncFlg{NPaths};false(L2-L1,1)];
    end
    Path{NPaths}(Path{NPaths} == 0) = [];
        
%     if mod(NPaths,2) == 1
%         plot3(LocP(Path{NPaths},1),LocP(Path{NPaths},2),LocP(Path{NPaths},3),'-r*','MarkerSize',10,'LineWidth',2)
%     else
%         plot3(LocP(Path{NPaths},1),LocP(Path{NPaths},2),LocP(Path{NPaths},3),'-b*','MarkerSize',10,'LineWidth',2)
%     end
%     pause(.1)
    
    % If the path's "closed loop" edge is a boundary edge, then count it as
    % visited, even though it does not actually appear in a path.
    if max(sum(BE2V(LoneBEdges,:) == [Path{NPaths}(end),Path{NPaths}(1)],2)) > 1
        L = sum(BE2V(LoneBEdges,:) == [Path{NPaths}(end),Path{NPaths}(1)],2);
        L = L == 2;
        EdgeNPaths(LoneBEdges(L)) = EdgeNPaths(LoneBEdges(L)) + 1;
    elseif max(sum(BE2V(LoneBEdges,:) == [Path{NPaths}(1),Path{NPaths}(end)],2)) > 1
        L = sum(BE2V(LoneBEdges,:) == [Path{NPaths}(1),Path{NPaths}(end)],2);
        L = L == 2;
        EdgeNPaths(LoneBEdges(L)) = EdgeNPaths(LoneBEdges(L)) + 1;
    end
                            
    LoneBEdges = find(EdgeNPaths == 0);
    LoneNodes = find(NodeNPaths == 0);
end
% mxL = 0;
% for i = 1:length(Path)
%     mxL = max(length(Path{i}),mxL);
% end
% for i = 1:length(Path)
%     Path{i} = [Path{i}; zeros(mxL-length(Path{i}),1)];
% end
% Path = cell2mat(Path);
end