function [CM,removedVertIDs]	= TruncateBoundaryQuads(CM)
    %======================================================================
    %TRUNCATEBOUNDARYQUADS Removes unsmoothable quads on mesh boundaries.
    %   [CM,removedVertIDs] = TRUNCATEBOUNDARYQUADS(CM) 
    %   
    %   These quads are identified as those on the boundary with interior
    %   angles exceeding 134 degrees defined by two boundary edges. These
    %   quads will have a quality of zero by our definition and cannot be
    %   smoothed to a better quality since the angle defined by the
    %   boundary edges is unsmoothable. Some additional work should include
    %   a capability for removing or refining quads with 4 nodes on the
    %   boundary.
    %   
    %   See also: QUADVERTEXMERGE, DOUBLETCOLLAPSE.
    %======================================================================
    
    % Identify and remove quads that are eligible due to 1 of their boundary verts.
    Qi  = (1:size(Q,1))';                           % Index to all quads.
    iQ  = [];                                       % Quads to be removed.
    stoppingCriterionMet	= false;
    while ~stoppingCriterionMet
        % Identify all quads on mesh boundary.
        
        % Identify quads w/ 3 and 4 boundary vertices.
        
        iQbv	= Qi(sum(ismember(Q,MESH.BE{1}),2) >= 3 & ~ismember(Qi,iQ));
        if isempty(iQbv)
            stoppingCriterionMet = true;
        end
        
        % Identify iQbv with a boundary vertex > 135 degrees.
        Theta   = interiorAngles(MESH,Q(iQbv,:));
        badAngles	= ismember(Q(iQbv,:),MESH.BE{1}) & Theta > 135;
        ibadAngles  = sum(badAngles,2) > 0;
        iQbvi   = (1:numel(iQbv))';                 % Index to Theta.
        iTheta  = iQbvi(ibadAngles);
        
        % Remove unsmoothable, degenerate quads.
        if numel(iTheta) >= 1 && ~ismember(iTheta(1),iQ)
            % Info of quad.
            iQ	= [iQ;iQbv(iTheta(1))];             % Quad index.
            angles  = badAngles(iTheta(1),:);       % Angle of cause.
            iP  = Q(iQ(end),angles);                % Point of interest.
            edges   = [Q(iQ(end),1:2);Q(iQ(end),2:3);...
                Q(iQ(end),3:4);Q(iQ(end),[4 1])];
            cedges  = edges(sum(ismember(...        % Edges to collapse.
                edges,iP(1)),2) > 0,:);
%             plot(MESH,iQ(end),'g');plot(MESH.Points(iP(end),1),MESH.Points(iP(end),2),'r*');pause
            % Change connectivity of iQ's cedges attachments.
            for jdx = 1:2
                v   = cedges(jdx,~ismember(cedges(jdx,:),iP(1)));
                Q(ismember(Q,v)) = iP(1);       	% Sub iP for v.
            end
        else
            stoppingCriterionMet	= true;
        end
    end
    
    % Update Q and MESH.
    Q(iQ,:)     = [];
    MESH.ConnectivityList = [Q;T];
    MESH    = MESHFacets(MESH,'EN','BE');%,'FN');
    MESH    = MESHLayers(MESH);
    
    % Perform Other Quad Removal Operations that may now be eligible.
    try
        [MESH,Q]	= DoubletCollapse(MESH,Q,T);
    end
    try
        [MESH,Q,T]	= QuadVertexMerge(MESH,Q);
    end
end