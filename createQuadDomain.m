function [CM,Domain] = createQuadDomain(CM,plotProgress)
    %CREATEQUADDOMAIN Create sub-mesh of global domain to become quads.
    %   [CM,Domain] = CREATEQUADDOMAIN(CM,plotProgress) 
    %   % Layers, distance from shoreline, edge size, custom polygon, etc.
    %   See also MAIN, TRI2QUADROUTINE, POSTPROCESSROUTINE.
    %======================================================================
    
    %% 1) Create Subdomain of Mesh For Tri2Quad.
    % Identify discretization strategy.
    strategies  = {'...Throughout Current Mesh',...     % Ideas for strategies.
        '...Distance From Shoreline',...
        '...Within A Drawn Domain'};
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
    
    % Implement strategy to identify triangles for tri2Quad.
    Domain  = CM;                                       % Initialize new object.
    selectedTriangles	= [];                         	% Selected triangles.
    for idx	= selectedStrategy(1:end)
        if idx == 1                                     % Completely quadrangular.
            selectedTriangles	= (1:CM.nElems)';      	% Select all triangles.
            break                                       % End procedure.
        end
        if idx == 2                                     % Triangles beyond
            beyondMinDistanceTriangles = [];            % a specific distance.
            selectedTriangles   = [selectedTriangles; beyondMinDistanceTriangles];
            endedTriangles   = [selectedTriangles; edgelengthTraingles];
        end
        if idx == 5                                     % Triangles within
            xy  = drawDomain(CM);
            polygonTraingles	= [];                 	% specific polygon.
            selectedTriangles   = [selectedTriangles; polygonTraingles];
        end
    end
    
    % Create 2 sub domains: 1 w/ tris to become quads, 1 w/ original tris.
    Domain.ConnectivityList	= CM.ConnectivityList(selectedTriangles,:);
    CM.ConnectivityList(selectedTriangles,:)    = [];   % Only original tris.
    
    %% 2) Fill Remaining Properties of Domain Object.
    Domain  = buildAdjacencies(Domain);              	% Adjacency lists.
    Domain  = meshLayers(Domain);                      	% Layers of mesh.
    
    %% 3) Show Quad Domain.
    if plotProgress
        plot(Domain,'ElemColor','blue');
    end
end

