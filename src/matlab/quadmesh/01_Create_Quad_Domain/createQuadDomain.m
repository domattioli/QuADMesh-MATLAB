function [CM,Domain] = createQuadDomain(CM)
%CREATEQUADDOMAIN Create sub-mesh of global domain to become quads.
%   [CM,Domain] = CREATEQUADDOMAIN(CM,plotProgress)
%   % Layers, distance from shoreline, edge size, custom polygon, etc.
%   See also MAIN, TRI2QUADROUTINE, POSTPROCESSROUTINE.
%==========================================================================

%% 1. Create Subdomain of Mesh For Tri2Quad.
% Identify discretization strategy.
figure; CM.plot;
strategies  = {'...Throughout Current Mesh',...     % Ideas for strategies.
    '...Distance From Shoreline',...
    '...Within A Drawn Subdomain'};
OK	= 0;                                         	% Initialize selection.
attempt	= 1;                                        % Max # attempts = 3.
while OK == 0                                       % Until strategy selected.
    [selectedStrategy,OK] = listdlg('PromptString','Quads will be created:',...
        'SelectionMode','multiple',...            	% Select multiple options.
        'InitialValue',1,'ListString',strategies,...% Default: all quads.
        'ListSize',[160 75],'Name','Quad Domain');
    if attempt ~= 3                                 % Track attempts.
        attempt = attempt + 1;                      % Next attempt.
        
    else                                            % Exit selection.
        selectedStrategy = 1;                       % Quads everywhere.
        OK = 1;
    end
end

% If "Select All" chosen, default to "Throughout Current Mesh".
if sum(ismember(1:3,selectedStrategy)) == 3
    selectedStrategy    = 1;
end

% Implement strategy to identify triangles for tri2Quad.
domainIsSatisfactory	= false;
while domainIsSatisfactory  == false
    ElemIDs	= false(CM.nElems,1);                	% Selected triangles.
    cla;    CM.plot;	drawnow;
    switch selectedStrategy
        case 1                                    	% Completely quadrangular.
            ElemIDs(1:end)	= 1:CM.nElems;       	% Select all triangles.
            
        case {2,3}                                 	% Find points meeting criterion/a.
            inPoints	= false(CM.nVerts,1);      	% Points for choosing triangles.
            
            % Find all points exceeding specified distance from mesh boundaries.
            if selectedStrategy == 2
                warndlg('Implementation not yet available.');
                selectedStrategy = 3;             	% Draw domain instead.
            end
            
            % Find all points within custom-drawn subdomain polygon(s).
            [X,Y]	= drawSubdomain(gca);         	% Draw polygon(s) over region(s) of mesh.
            
            % Find points that are within polygon defined by [X,Y].
            inPoints= false(CM.nVerts,1);
            for jdx = 1:length(X)
                inPoints(inpolygon(CM.Points(:,1),CM.Points(:,2),X{jdx},Y{jdx}))    = true;
            end
            
            % Identify triangles with at least one vertex within the polygon(s).
            VertIDs	= unique(find(inPoints));    	% Vertices meeting criterion/a.
            ElemIDs(sum(ismember(CM.ConnectivityList,VertIDs),2) > 0)	= true;
    end
    ElemIDs	= unique(find(ElemIDs));                % Triangles meeting criteria.
    Domain	= CHILmesh(CM.ConnectivityList(ElemIDs,:),CM.Points);
    
    % Verify selected region(s).
    axisChildren	= findobj(gca,'type','line');
    if selectedStrategy ~= 1                        % Delete poly(s) object(s).
        delete(axisChildren(1));
    end
    
    Domain.plotEdge(Domain.boundaryEdges,'color','r','linewidth',2);
    satisfied = questdlg('Proceed with this subdomain?','Selected Subdomain','Yes','No','Yes');
    if strcmp(satisfied,'Yes')                      % If not, try again.
        domainIsSatisfactory    = true;
    end
end

% Remove triangles of Domain from original mesh to make room for quads.
CM.ConnectivityList(ElemIDs,:)    = [];             % Only original tris.

