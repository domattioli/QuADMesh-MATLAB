function [X,Y]  = drawSubdomain(axisHandle)

% Get current axis for plotting.
axes(axisHandle);   hold on;
ax  = get(gca,'XLim');
ay  = get(gca,'YLim');

% Initialize plotted line object.
pl  = line(0,0,'color','r','linewidth',2,'marker','s','markerfacecolor','r','markersize',7);
pl.XData    = [];                                   % Empty line.
pl.YData    = [];

% Draw polygon(s).
try
    button      = 1;
    closeIdx    = 1;                             	% Index to 1st point in poly.
    while button ~= 3
        % Get new point.
        [newX,newY,button]	= ginput(1);
        
        % Plot point.
        if button == 1
            pl.XData    = [pl.XData, newX];       	% Add vert and edge.
            pl.YData    = [pl.YData, newY];
            
        else                                    	% Close polygon.
            if isnan(pl.XData(end))             	% Cease all drawing.
                button	= 3;
                continue
            end
            pl.XData    = [pl.XData, pl.XData(closeIdx), NaN];
            pl.YData    = [pl.YData, pl.YData(closeIdx), NaN];
            if button == 2                          % Begin new polygon.
                if isnan(pl.XData(end)) && isnan(pl.XData(end-1))
                    pl.XData(end)   = [];
                    pl.YData(end)   = [];
                end
                closeIdx    = length(pl.XData)+1;
                
            else                                    % Cease all drawing.
                
            end
        end
        drawnow;
        set(gca,'XLim',ax,'YLim',ay);
    end
    
    % Repackage output.
    iNaN    = find(isnan(pl.XData));
    if isempty(iNaN)                                % Only one polygon.
        X   = pl.XData;
        Y   = pl.YData;
    
    else                                            % Multiple polygons.
        X   = cell(length(iNaN),1);
        Y   = X;
        jdx = 1;
        for idx = 1:length(iNaN)
            X{idx}  = pl.XData(jdx:iNaN(idx)-1);
            Y{idx}  = pl.YData(jdx:iNaN(idx)-1);
            jdx = iNaN(idx)+1;
        end
    end
    
catch
    children = get(gca,'children');
    delete(children(1));
    X	= {}; Y = {};
end

% Ensure that output(s) is/are column vectors.
X   = X';
Y   = Y';