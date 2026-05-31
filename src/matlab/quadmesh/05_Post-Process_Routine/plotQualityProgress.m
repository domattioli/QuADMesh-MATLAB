function mainAxis = plotQualityProgress(mainAxis,CM,plotProgress)
if plotProgress
    % Keep window size.
    ax  = get(mainAxis,'XLim');
    ay  = get(mainAxis,'YLim');
    
    % Delete old mesh domain.
    cla;
    
    % Replot updated mesh domain.
    CM.plot;
    
    % Keep window.
    set(gca,'XLim',ax,'YLim',ay);
    drawnow
end