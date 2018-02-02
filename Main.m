%==========================================================================
% Main file for new version of mesh stuff.
%==========================================================================
%% Establish Working Directory and Path.
path(pathdef);  clc;
% Set directory and path to folder of ADMESH, QuADMESH libraries and test cases.
if ~exist('loadLocation','var')
%     loadLocation	= input('Input location of CHILmesh Library: \n\n','s'); % This is the parent folder to ADMESH, qADMESH.
%     loadLocation	= 'R:\Labs\C.H.I.L\dropbox\Dominik\Tri2Quad\Working_Folder'; % Ethan cpu.
%     loadLocation	= 'L:\C.H.I.L\dropbox\Dominik\Tri2Quad\Working_Folder'; % Dom CHIL cpu.
%     loadLocation    = '/Users/dominik/Downloads/MATLAB';    % Dom home cpu.
    loadLocation    = 'R:\Ortho-Biomechanics\Dominik\Downloads';
end
cd(loadLocation);  addpath(genpath(loadLocation));
if ~exist('loadLocation','var') % For saving stuff.
%     SaveLocation	= [];%input('\n Will you be saving any files? Y/N [Y}: \n','s');
%     if ~isempty(SaveLocation) && strcmpi(SaveLocation,'y')
%         SaveLocation	= input('\n Enter path to folder where file(s)/figure(s) will be saved to: \n\n','s');
        saveLocation	= [loadLocation,'\04_Results'];
%     end
end
set(0,'DefaultFigureWindowStyle','docked');	format shortg

%% 0. Load Mesh.
clearvars -EXCEPT loadLocation saveLocation;	close all;	clc;
% FILENAME	= 'Baranja_Hill_ADMESH_v2.14'; % Error -> meshlayers doesn't recognize interior boundary.
FILENAME	= 'Block_O.14'; % Error -> meshlayers doesn't recognize interior boundary.
% FILENAME	= 'Chesapeake_Bay.14';
% FILENAME	= 'Deleware_Bay_hmin_100_hmax_20000.14';
% FILENAME	= 'Great_Lakes.14';
% FILENAME	= 'Italy.14';
% FILENAME	= 'LakeErie_5k_500.14';
% FILENAME	= 'Lake_Erie_mesh_refined.14';
% FILENAME	= 'LakeGeorgeBasinGeometry_frontal1.msh';
% FILENAME	= 'Lake_Michigan_mesh.14';
% FILENAME	= 'Mixed_Test.14';
% FILENAME	= 'square_mesh_test.14';
% FILENAME	= 'Test_Case_1.14';                     % Block-O.
% FILENAME	= 'Test_Case_2.14';                     % Pac-man on his back.
% FILENAME	= 'Test_Case_3.14';                     % Ear-horn.
% FILENAME	= 'Test_Case_4.2.14';                 	% Hour glass.
% FILENAME	= 'Test_Case_4_right.14';            	% Hour glass.
% FILENAME	= 'wetting_and_drying_test.14';
% FILENAME	= 'WNAT_53K_Nodes.14';
% FILENAME	= 'WNAT_Onur.14';
% FILENAME	= 'WNAT_Test.14';
% FILENAME	= 'Mixed_Test.14';
CM	= CHILmesh(FILENAME);                        	% Create mesh class.
% CM	= CHILmesh(delaunayTriangulation(rand(10,2)));	% Random mesh.
try
    load(FILENAME(1:end-3))                         % Load PTS structure.
catch
    PTS.Points = [];
end

%% 1. Create Sub-Domain Of Mesh For Tri2Quad.
plotProgress    = true;                             % Plot progress.
time    = {'Triangular',CM,0};                      % Track comp. time.
tic;                                                % Begin timer.
[CM,Domain]	= createQuadDomain(CM,plotProgress);                 
time	= [time; {'PreProcess',Domain,toc}];       	% Time spent.

%% 2. Create Quadrilaterals in Domain.
[Domain,time]	= Tri2QuadRoutine(Domain,time);

%% 3. Perform Quality Improvement Operations.
[MESH,Q,T,time]	= PostProcessRoutine(MESH,Q,T,PLOT,time);
% time    = [time;{'Total'},sum([time{:,2}])];	disp(time);	


