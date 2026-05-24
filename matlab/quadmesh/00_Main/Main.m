%==========================================================================
% Main file for mesh stuff.
%==========================================================================
%% 0.1 Establish Working Directory and Path.
path(pathdef);  clc;
% Set directory and path to folder of ADMESH, QuADMESH libraries and test cases.
loadLocation	= uigetdir('','Select ''The_CHIL_OSU'' Folder');
% loadLocation	= '';                               % Custom string for directory.
% loadLocation	= 'R:\Labs\C.H.I.L\dropbox\Dominik\Tri2Quad\Working_Folder';% Ethan PC.
% loadLocation	= '/Users/dominik/Downloads/MATLAB';% Dom mac.
cd(loadLocation);  addpath(genpath(loadLocation));
set(0,'DefaultFigureWindowStyle','docked');	format shortg

%% 0.2 Load Mesh.
clearvars -EXCEPT loadLocation saveLocation;	close all;	clc;
% FILENAME	= 'structuredMesh1.14';
% FILENAME	= 'structuredMesh2.14';
% FILENAME	= 'structuredMesh3.14';
% FILENAME	= 'structuredMesh4.14';
% FILENAME	= 'simple_test_case.14';
% FILENAME	= 'Baranja_Hill_ADMESH_v2.14';
FILENAME	= 'Block_O.14';
% FILENAME	= 'circle.14';                  
% FILENAME	= 'Chesapeake_Bay.14';                  
% FILENAME	= 'Deleware_Bay.14';
% FILENAME	= 'Great_Lakes.14';   
% FILENAME	= 'islands1.14';   
% FILENAME	= 'Italy.14';                           
% FILENAME	= 'LakeErie_5k_500.14';
% FILENAME	= 'Lake_Erie_mesh_refined.14';
% FILENAME	= 'LakeGeorgeBasinGeometry_frontal1.msh';% Doesn't load.
% FILENAME	= 'Lake_Michigan_mesh.14';
% FILENAME	= 'Mixed_Test.14';
% FILENAME	= 'square_mesh_test.14';
% FILENAME	= 'test1.14';
% FILENAME	= 'Test_Case_1.14';     % Block-O.
% FILENAME	= 'Test_Case_2.14';     % Pac-man.
% FILENAME	= 'Test_Case_3.14';     % Ear-horn.
% FILENAME	= 'Test_Case_4.2.14';	% Hour glass.
% FILENAME	= 'wetting_and_drying_test.14';
% FILENAME	= 'WNAT_53K_Nodes.14';                  % *Error*.
% FILENAME	= 'WNAT_Hagen.14';
% FILENAME	= 'WNAT_Onur.14';                       
% FILENAME	= 'WNAT_Test.14';
CM	= CHILmesh(FILENAME);                        	% Create mesh class.
% CM	= CHILmesh(delaunayTriangulation(rand(10,2)));	% Random mesh.
try
    load(FILENAME(1:end-3))                         % Load PTS structure.
catch
    PTS.Points = [];
end
original = CM;

%% 1. Create Sub-Domain Of Mesh For Tri2Quad.
%%% TEMPORARY USER INPUTS
canRemoveEdges  = true;                             % For removing tris on mesh (not subdomain) boundary.
plotProgress    = true;                             % Plot progress.
nSmoothIterations   = 100;
time    = {'Triangular',CM,0};                      % Track comp. time.
tic;                                                % Begin timer.
[CM,Domain]	= createQuadDomain(CM);                 

%% 2. Create Quadrilaterals in Domain.
[CM,Domain]	= Tri2QuadRoutine(CM,Domain,canRemoveEdges,plotProgress);
time    = [time;{'Tri2Quad',CM,toc}];               % Track comp. time.

%% 3. Perform Quality Improvement Operations.
[CM,Domain]	= PostProcessRoutine(CM,Domain,canRemoveEdges,plotProgress,nSmoothIterations);
time    = [time;{'Post-Process',CM,toc}];           % Track comp. time.

%% 4. Results.
close all;
figure;original.plot;title('Original Triangular');
figure;CM.plot;title(['Final Quadrangular, Duration: ',num2str(sum(cell2mat(time(:,3))))]);
figure;original.plotLayer;title('Original Triangular: Layers');
figure;CM.plotLayer;title('Final Quadrangular, Layers');
figure;original.plotQuality;title(['Original Triangular, Avg. Quality: ',num2str(mean(original.elemQuality))]);
figure;CM.plotQuality;title(['Final Quadrangular, Avg. Quality: ',num2str(mean(CM.elemQuality))]);
% meshSavedFileName	= saveMesh(CM)
% plotSavedFileName	= saveMesh(figure(2))

%%% FYI, the scarlet rgb is [187/255 0 0] -> https://brand.osu.edu/color/
