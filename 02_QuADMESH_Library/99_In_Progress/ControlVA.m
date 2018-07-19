function [MESH,T,Q] = ControlVA(MESH,T,Q,fb,F)
    %ControlVA Reconfigures elements of vertices with > 5 attachments.
    %   This is a a work in progres script that I made a while back that
    %   explores the idea of fixing high valence (6+) vertices with quads
    %   attached. Not really much to see here...
    
    % Point and Connectivity lists of MESH.
    P	= MESH.Points;
    C	= MESH.ConnectivityList;
    
    % Interior vertices of MESH.
    idx = (1:size(P,1))';
    Vi	= idx(~ismember(idx,fb));
    
    % Vertex attachments of interior vertices.
    ViA	= vertexAttachments(MESH,Vi);
    
    % Vertices with more than 5 attachments.
    V5A	= find(cellfun(@length,ViA) > 5);
    
    % Coordinates of ViA.
    xyz = P(Vi(V5A),:);
    
    % Prioritize vertices by distance to free boundaries.
    [~,iD]	= sort(F(xyz(:,1),xyz(:,2)),'ascend');
    
    % Loop through iD.
    newQ    = [];
    for ind = 1:length(iD)
        % Get attachments of vertex.
        A       = cell2mat(ViA(V5A(iD(ind))));
        local   = MESH;
        local.ConnectivityList	= C(A,:);      
        
        % Get sequential list of interior edges of polygon.
        [EAlocal,Elocal]        = edgeAttachments(local);
        fblocal = freeBoundary(local);          % Local polygon boundaries.
        inElocal= Elocal(~ismember(Elocal,fblocal,'rows'),:);
        mpt     = [(P(inElocal(:,1),1) + P(inElocal(:,2),1))/2,...
            (P(inElocal(:,1),2) + P(inElocal(:,2),2))/2];
        list    = convhull(mpt(:,1),mpt(:,2));
        
        % Create triangle whose nodes are midpoints of alternating interior
        % edges of original polygon.
        edgeIdx	= [1 3 5];
        cT      = mpt(list(edgeIdx),:);
        cTiP  	= size(P,1)+1:size(P,1)+3;    	% P indices.
        newT    = cTiP;                         % Add new triangle to list.
        
        % Create triangles connecting nodes of cT to original polygon.
        verts   = [];
        for jnd = 1:3
            % Get edge along which node jnd of cT bisects.
            bisectedE	= inElocal(list(edgeIdx(jnd)),:);
            
            % Get edge attachments of bisectedE.
            EAbisectedE	= EAlocal{ismember(Elocal,bisectedE,'rows')};
            
            % Get all vertices of EAbisectedE.
            vertices    = unique(local.ConnectivityList(EAbisectedE,:));
            vertices    = vertices(vertices ~= mode(inElocal(:)));
            
            % EAbisectedE's fblocal edges.
            triEdges    = fblocal(sum(ismember(fblocal,vertices),2) == 2,:);
            
            % Store vertices which apart of only 1 triEdges.
            triEdgesU	= unique(triEdges);
            counts      = histc(triEdges(:),triEdgesU);
            verts       = cat(1,verts,triEdgesU(counts == 1));
            
            % New node for new tris.
            Node        = cTiP(jnd).*ones(size(triEdges,1),1);
            
            % Form triangles from each node in vertices to Node.   
            newT        = cat(1,newT,cat(2,triEdges,Node));
        end
        
        % Add the 3 triangles adjacent to the edges of tri cT.
        verts   = unique(verts);
        tE      = edges(MESH,'special',newT);
        intE    = tE(~ismember(tE,fblocal,'rows'),:);
        for jnd = 1:size(verts,1)
            % Get edges composed of 1 node from verts and 2 nodes from cT.
            verts_cT_E	= intE(sum(ismember(intE,verts(jnd)),2) > 0,:);
            newT        = cat(1,newT,unique(verts_cT_E)');
        end
        
        % Merge tri cT with one of its attachments.
        
        
        
        % Merge tris in an adjacent-matching pattern; begin with cT.
        tris    = MESH;   	M	= MESH;
        tris.ConnectivityList   = newT;
        tris.Points             = cat(1,P,cat(2,cT,zeros(3,1)));
        tEA		= edgeAttachments(tris);
        tEA     = cell2mat(tEA(cellfun(@length,tEA) == 2));
        pairedT = tEA(end,tEA(end,:) ~= 1);
        nextT   = tEA(find(sum(ismember(tEA(1:end-1,:),pairedT),2) > 0,1,'first'),:);
        nextT   = nextT(nextT ~= pairedT);
        M.Points= tris.Points;
        M.ConnectivityList	= newT(tEA(end,:),:);
        M       = tri2quad_v5(M,fb,F,[0 0]);
        newQ    = cat(1,newQ,M.ConnectivityList);
        usedT   = cat(1,1,pairedT);
        newT(usedT,:) = NaN;
        tEA(ismember(tEA,usedT))= NaN;
        
        % Continue with next available edge attachment until exhausted.
        while any(~isnan(newT(:,1)))
            % Get attached tri to nextT.
            t       = tEA(sum(ismember(tEA,nextT),2) > 0,:)
            pairedT = t(~ismember(t(~isnan(t)),cat(1,nextT,usedT)))
            usedT   = cat(1,nextT,pairedT)
            
            % Get next tri.
            t       = tEA(sum(ismember(tEA,pairedT),2) > 0,:)
            nextT   = t(~ismember(t,usedT))
            
            % Merge tris.
            M.ConnectivityList  = newT(usedT,:);
            M       = tri2quad_v5(M,fb,F,[0 0]);
            
            % Store new quad, flag used tris.
            newQ    = cat(1,newQ,M.ConnectivityList);
            newT(usedT,:)   = NaN;
            tEA(ismember(tEA,usedT))= NaN;
        end % End while.
    end % End for ind.
end

