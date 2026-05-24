function ph	= dplot(varargin)
    %DPLOT Discontinuous linear plot.
    %   ph = DPLOT(X,Y) plots vector Y versus vector X as discontinous line
    %   segments. The functionality of DPLOT is similar to the built-in
    %   MATLAB plot function, except all lines are discontinuous segments.
    %   ph is the handle to the resulting Line object.
    %
    %   DPLOT(Y) plots the columns of Y versus their index.
    %
    %   DPLOT operates as if the input is that of multiple inputs to
    %   MATLAB's plot, i.e. plot(X1,Y1,S1,X2,Y2,S2,...XN,YN,SN), where the
    %   X's and Y's are vectors or matrices and the S's are strings.
    %   
    %   Example:
    %      x = [1 1 2 2 3 3 4 4 5 5];
    %      y = [1 2 2 3 3 4 4 5 5 6];
    %      plot(x,y,'--rs','LineWidth',2,...
    %                      'MarkerEdgeColor','k',...
    %                      'MarkerFaceColor','g',...
    %                      'MarkerSize',10)
    %
    %   See also PLOT.
    %======================================================================
    
    % Check I/O argument(s).
    if nargin <= 1 && nargin ~= 0                  	% Compute number of plotting iterations.
        iter	= 1;                                % Only one plotting iteration.
        switch nargin                               % Ensure parse compatibility.
            case 0  
                error('Not Enough Inputs');
                
            case 1
                varargin = {varargin{1},[],[]};     % Add two empties.
                
            case 2
                varargin = {varargin{1},[]};        % Add one empty.
                
            otherwise                               % 3 varargin. Do nuthin.
        end
    else                                            % Many plotting iterations.
        iter	= nargin/3;
    end
    
    % Parse input(s), plot.
    iArg1   = 1:3:nargin;                          	% Index to 1st of 3 args.
    for i	= 1:iter                                % For each Xi,Yi,Si input.
        ip  = inputParser;                          % Parse inputs (3 at a time).
        addRequired(ip,'X',@isnumeric);             % X-Coordinate(s).
        addOptional(ip,'Y',@isnumeric);             % Y-Coordinate(s).
        parse(ip,varargin{iArg1(i):iArg1(i)+1});
        
        % Assign X and Y.
        if ~isreal(ip.Results.X)                    % First, only input is complex.
            error('gotta do something for this');
        end
        if isempty(ip.Results.Y)                    % Only one input.
            X   = 1:size(ip.Results.X,2);         	% Input.
            Y   = ip.Results.X;                 	% Indices of input.
        else
            X   = ip.Results.X;
            Y   = ip.Results.Y;
        end
        
        % Pad X, Y coordinate vectors with NaNs.
        sX  = size(X);
        sY  = size(Y);
        minX    = min(sX);                          % Determine if X and/or
        minY    = min(sY);                          % Y are matrices.
        if minX == 1 && minY == 1                   % Both are vectors.
            
            
        elseif minX == 1 && minY ~= 1               % Only Y is a matrix.
            % X must be a column vector
            if sX(1) ~= 1
                X	= X';
            end
            X	= [X; NaN
            
        elseif minX ~= 1 && minY == 1               % Only X is a matrix.
            
            
        elseif minX ~= 1 && minY ~= 1               % Neither is a matrix.
            
        end
        emptyCoords	= NaN(1,length(X));
        X   = repmat([X; emptyCoords],size(Y,2),1)
        
        x   = [CM.Points(VertIDs(1,:),1)';...   % X-Coordinates.
            CM.Points(VertIDs(2,:),1)'; emptyCoords];
        y   = [CM.Points(VertIDs(1,:),2)';...   % X-Coordinates.
            CM.Points(VertIDs(2,:),2)'; emptyCoords];
        
    end
end

