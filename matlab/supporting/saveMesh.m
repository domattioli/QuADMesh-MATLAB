function fullfileName	= saveMesh(input1,saveLocation)
%SAVEMESH Saves the CHILmesh object and/or it's plotted figure.
%   Detailed explanation goes here
%  
%==========================================================================

% Check whether input #1 is either a CHILmesh object or a .fig.

if strcmp(class(input1),'CHILmesh') && ~strcmp(class(input1),'matlab.ui.Figure')
    saveMesh= true;
    saveFig	= false;
elseif ~strcmp(class(input1),'CHILmesh') && strcmp(class(input1),'matlab.ui.Figure')
    saveMesh= true;
    saveFig	= false;
else
    errordlg('First input must be a CHILmesh or a figure.')
    return
end
    
% Select full-filename of saved mesh.
if nargin == 1
    % Ask for directory.
    saveLocation	= uigetdir('','Select folder for saving result');
    fileName    = cell2mat(inputdlg('Type name of file.'));
    
elseif nargin < 2
    errordlg('Too many inputs');
else
    % Check if titular-folder exists in saveLocation.
    fullfileName= fullfile(saveLocation,CM.GridName);	% Name of folder.
    checkFolder	= exist(fullfileName,'dir');
    if ~checkFolder
        mkdir(saveLocation,CM.GridName)
    end
end

% Save file according to input.
if saveMesh %%%%% Work in progress.
    fileName    = ['_',CM.Type,'_Mesh'];                      % Name of file.
    save(fullfile(saveLocation,fileName,),input1)
elseif saveFig
    save(fullfile(saveLocation,fileName,['_',CM.Type,'_Plot']),input1)
end
