function [Domain,newMesh] = edgeBisection(Case,Domain,newMesh,iLayer,...
    tElemID,tConn,tEdgeIDs,tEdge2VertIDs,tElem2ElemIDs,itbEdgeIDs)
%EDGEBISECTION Bisect one of the outer boundary edges into two edges.
%   [Domain,newMesh] = EDGEBISECTION(Case,...) returns CHILmesh object
%   Domain updated for all layers iLayer-1:-1:1 and data for defining the
%   new quadrilateral mesh object newMesh, which is comprised of a points
%   list and quadrilateral elements' connectivity.
%   
%   When Case is equal to 1:
%       There is only one edge of tri on the mesh boundary and the user
%       does not want to remove an edge a new point is projected from the
%       boundary to convert this tri into a quad.
%   
%   When Case is equal to 2: 
%       There are 1-3 edges of the tri on the interior-layer boundary and
%       one of them is chosen to be bisected. This tri then becomes a
%       (degenerate) quad and the triangle in iLayer-1 that previously
%       neighbored it is bisected into two tris.
%   
%   See also: EDGEINSERTION, EDGEREMOVAL, REMOVETRIANGLESFUN.
%==========================================================================

% Get VertIDs of tri's boundary edge.
edgeVertIDs	= tEdge2VertIDs(itbEdgeIDs(1),:);

% Compute midpoint coordinate of tElemID's boundary edge.
[x,y,z]	= Domain.edgeMidpoint(tEdgeIDs(itbEdgeIDs(1)));
npID	= size(Domain.Points,1) + 1;                % Index to new point.

% Create quad by inserting point at midpoint of boundary edge.
Domain.Points	= [Domain.Points; [x y z]];
itConn	= find(ismember(tConn,edgeVertIDs));
while itConn(2) ~= (itConn(1)+1)                    % Rotate so verts are
    tConn	= tConn([2:3 1]);                       % adj in conn.
    itConn	= find(ismember(tConn,edgeVertIDs));
end
newMesh.ConnectivityList	= [newMesh.ConnectivityList;...
    [tConn(1:itConn(1)), npID, tConn(itConn(2):end)]];

% Depending on geometry; either project point from mesh boundary or bisect edge.
if Case == 1                                        % Project point from mesh boundary.
    % Project point from boundary. This is tough to do (see comment in
    % EdgeInsertion's else statement. Will just perform EdgeRemoval here.
    [Domain,newMesh]	= edgeRemoval(Domain,newMesh,tElemID,tEdgeIDs,...
        tEdge2VertIDs,itbEdgeIDs);
    
else % Case == 2                                  	% Bisect interior edge.
    % Identify triElem2Elem across from itriEdgeIDs.
    opp_tElemID	= tElem2ElemIDs(itbEdgeIDs(1),...
        ~ismember(tElem2ElemIDs(itbEdgeIDs(1),:),tElemID));
    opp_tConn	= Domain.ConnectivityList(opp_tElemID,:);
    
    % Retriangulate points of tris in iLayer-1.
    opp_t_newVerts	= [opp_tConn, npID];
    rt  = delaunayTriangulation(Domain.Points(opp_t_newVerts,1:2));
    switch size(rt.ConnectivityList,1)              % Check for errors.
        case 2                                      % good to go.
            % Don't need anything here.
            
        case 3                                      % Delaunay created a
            i_dt	= sum(ismember(...              % degenerate (linear) tri.
                opp_t_newVerts(rt.ConnectivityList),...
                [edgeVertIDs,npID]),2) == 3;
            if any(i_dt)                            % Remove degenerate tris.
                P   = Domain.Points(opp_t_newVerts,1:2);
                C   = rt.ConnectivityList(~i_dt,:);
                rt  = triangulation(C,P);
            end
            
        otherwise
            error('probably shouldnt happen; somehow got 1,4, or more triangles from delaunay');
    end
    replacementTris	= [opp_t_newVerts(rt.ConnectivityList(1,:));...
        opp_t_newVerts(rt.ConnectivityList(2,:))];
    
    % Replace iLayer-1 tri (opp_tElemID) with the 2 new tris.
    nElem	= size(Domain.ConnectivityList,1) + 1;
    Domain.ConnectivityList(opp_tElemID,:) = replacementTris(1,:);
    Domain.ConnectivityList	= [Domain.ConnectivityList; replacementTris(2,:)];
    Domain.Layers.IE{iLayer-1}	= [Domain.Layers.IE{iLayer-1}; nElem];
    
    % Pretend that tElemID is also split into 2 tris within Domain.
    replacementTris(~ismember(replacementTris,[npID, edgeVertIDs]))	=...
        tConn(~ismember(tConn,edgeVertIDs)).*uint32(ones(2,1));
    Domain.ConnectivityList(tElemID,:)  = replacementTris(1,:);
    Domain.ConnectivityList	= [Domain.ConnectivityList; replacementTris(2,:)];
    [~,Domain]	= Domain.isPolyCCW('index',[tElemID opp_tElemID Domain.nElems-1:Domain.nElems]);
    Domain.Layers.OE{iLayer}= [Domain.Layers.OE{iLayer}; size(Domain.ConnectivityList,1)];
    Domain.Layers.OV{iLayer}= [Domain.Layers.OV{iLayer}; npID];
    Domain.Layers.IV{iLayer-1}	= [Domain.Layers.IV{iLayer-1}; npID];
    
    % Do a really convoluted update of the Domain adjacency lists.
    Domain.nEdges   = Domain.nEdges - 1 + 4;
    Domain.nElems   = size(Domain.ConnectivityList,1);
    Domain.nVerts   = npID;
    Domain  = Domain.buildAdjacencies;
%     figure(1);ax=get(gca,'xlim');ay=get(gca,'ylim');figure(2);cla;Domain.plot;set(gca,'xlim',ax,'ylim',ay);
    %%% For real-team plotting:
    hold on;    triplot(rt,'color','k');
end

