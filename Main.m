%==========================================================================
% Main file for new version of mesh stuff.
%==========================================================================
%% Set Path.
path(pathdef);  clc;
% Set directory and path to folder of ADMESH, QuADMESH libraries and test cases.
if ~exist('LoadLocation','var')
%     LoadLocation	= input('Input location of CHILmesh Library: \n\n','s'); % This is the parent folder to ADMESH, qADMESH.
%     LoadLocation	= 'R:\Labs\C.H.I.L\dropbox\Dominik\Tri2Quad\Working_Folder'; % Ethan cpu.
%     LoadLocation	= 'L:\C.H.I.L\dropbox\Dominik\Tri2Quad\Working_Folder'; % Dom CHIL cpu.
    LoadLocation    = '/Users/dominik/Downloads/MATLAB';    % Dom home cpu.
end
cd(LoadLocation);  addpath(genpath(LoadLocation));
if ~exist('LoadLocation','var') % For saving stuff.
%     SaveLocation	= [];%input('\n Will you be saving any files? Y/N [Y}: \n','s');
%     if ~isempty(SaveLocation) && strcmpi(SaveLocation,'y')
%         SaveLocation	= input('\n Enter path to folder where file(s)/figure(s) will be saved to: \n\n','s');
        SaveLocation	= [LoadLocation,'\04_Results'];
%     end
end
set(0,'DefaultFigureWindowStyle','docked');	format shortg

%% Load Mesh.
clearvars -EXCEPT LoadLocation SaveLocation;	close all;	clc;
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

%% 1) Create Sub-Domain Of Mesh For Tri2Quad.
plotProgress    = true;                             % Plot progress.
time    = {'Triangular',CM,0};                      % Track comp. time.
tic;                                                % Begin timer.
[CM,Domain]	= createQuadDomain(CM,plotProgress);                 
time	= [time; {'PreProcess',Domain,toc}];       	% Time spent.

%% 2) Create Quadrilaterals in Domain.
[Domain,time]	= Tri2QuadRoutine(Domain,plotProgress,time);

%% 3) Perform Quality Improvement Operations.
[MESH,Q,T,time]	= PostProcessRoutine(MESH,Q,T,PLOT,time);
% time    = [time;{'Total'},sum([time{:,2}])];	disp(time);	


