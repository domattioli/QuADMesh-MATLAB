function [CM,qualityHistory] = MCSmooth(CM,plotProgress,nIter,VertIDs)
%======================================================================
% Angle Smoothing adapted from the paper: An Angle-Based Approach to
% Two-Dimensional Mesh Smoothing by Tian Zhou and Kenji Shimada
% Mixed-case element angle smoothing.
% Author: Dustin West, Dominik Mattioli.
%   
%   See also FEMSMOOTHER.
%======================================================================

% Check inputs.
if nargin == 1                                  % Plot each iteration.
    plotProgress	= false;
end
if nargin == 2                                  % Number of iterations.
    nIter	= inf;
end
if nargin == 3                                  % List of all interior nodes.
    VertIDs    = (1:size(CM.Points,1))';     	% Generate vector from 1 to nodes.
    % Remove constraints from edge list, store points.
    if ~isempty(CM.BoundaryCondition)
        ix      = find([CM.BoundaryCondition.id] == 18);
        if ~isempty(ix)
            for localPoly_nNodes	= 1:length(ix)
                n	= CM.BC(ix(localPoly_nNodes)).nodes;
                VertIDs= setdiff(VertIDs,n);
            end
        end
    end
end

% Ensure that VertIDs does not include boundary vertices.
VertIDs    = VertIDs(~ismember(VertIDs,CM.Layers.OV{1}));

% Remove edges defining triangular element(s)' "4th" edge(s).
%     if size(CM.stuff.fb,2) == 2
%         CM.stuff.fb	= CM.stuff.fb(...
%             CM.stuff.fb(:,1) ~= CM.stuff.fb(:,2),:); % Account for unique tri conn.
%     end

% Get vertices adjacent to each VertIDs.
vert2Edge	= MYcell2mat(CCWEdgesAroundVertsFun(CM,VertIDs),'zero');
vert2Vert   = zeros(length(VertIDs),size(vert2Edge,2)*2);
jdx	= 1:2;                                    	% Index to columns.
for idx	= 1:size(vert2Edge,2)
    vert2Vert(:,jdx) = CM.edge2Vert(vert2Edge(:,idx));
    jdx = jdx + 2;
end

% Prep for plotting progress of smoother.
if plotProgress == 1
    ax	= get(gca,'xlim');	ay	= get(gca,'ylim');
    delete(get(gca,'children'));
    hp = CM.plotElem(1:CM.nElems,'color','w');
    set(gca,'XLim',ax,'YLim',ay);
end

% Prep initial conditions for while loop.
currentXYZ	= CM.Points(:,[1 2]);
qualityHistory	= nan(nIter,3);
meshQuality	= CM.elemQuality;
previousAvgQ    = mean(meshQuality);
[previousMinQ,ipreviousMinQ]	= min(meshQuality);
qualityHistory(1,1)	= previousAvgQ;
qualityHistory(1,2)	= previousMinQ;
qualityHistory(1,3)	= ipreviousMinQ;

% Continue smoothing as average quality increases or until nIter reached.
iter	= 1;
while iter < nIter
    for iVertID	= 1:length(vert2Vert)
        % Perform smoothing on iVertID.
        currentXYZ = smoothingSubRoutine(VertIDs(iVertID),...
            vert2Vert(iVertID,vert2Vert(iVertID,:) > 0),currentXYZ);
    end
    
    % Update plot
    if plotProgress	== 1
        hp.Vertices	= currentXYZ;	drawnow;    pause(.1)
    end
    
    % Compare current condition to previous/initial condition.
    if iter == nIter                                % Only check if max iter hasn't been reached.
        break
    else
        meshQuality	= CM.elemQuality;
        currentAvgQ	= mean(meshQuality);
        [currentMinQ,icurrentMinQ]	= min(CM.elemQuality);
        qualityHistory(iter+1,1)	= currentAvgQ;
        qualityHistory(iter+1,2)	= currentMinQ;
        qualityHistory(iter+1,3)	= icurrentMinQ;
        
        % If the minimum element is improving, continue.
        if meshQuality(qualityHistory(iter,3)) < previousMinQ
            break                                   % PreviousMinQ is getting worse.
        else
            if currentAvgQ < previousAvgQ           % Average Quality is getting worse.
                break
            else
                previousAvgQ    = currentAvgQ;
                previousMinQ    = currentMinQ;
            end
        end
    end
    iter	= iter + 1;
end

% Assign new <x,y> coordinates.
CM.Points(:,1:2)	= real(currentXYZ);
end

function currentXYZ = smoothingSubRoutine(vertex,localPoly,currentXYZ)

% Remove redundancy and zero-values from localPoly.
localPoly(ismember(localPoly,[vertex, 0]))  = [];
if isempty(localPoly)
    return
end

% Assign coordinates to compute adjacent angles.
localPoly_nNodes    = length(localPoly);
pr  = currentXYZ(localPoly([end,1:end-1]),:);       % p_{j-1}.
pc  = currentXYZ(localPoly(1:end),:);               % p_{j}
pl  = currentXYZ(localPoly([2:end,1]),:);           % p_{j+1}

% Compute vectors.
vr	= (pr-pc);                                      % v_{j-1}
vc	= [currentXYZ(vertex,1)-pc(:,1),currentXYZ(vertex,2)-pc(:,2)];% v_{j}
vl	= (pl-pc);                                      % v_{j+1}

% Compute the two adjacent angles.
a1	= acos(sum(vc.*vl,2)./(sqrt(sum(vc.^2,2)).*sqrt(sum(vl.^2,2))));
a2	= acos(sum(vc.*vr,2)./(sqrt(sum(vc.^2,2)).*sqrt(sum(vr.^2,2))));

% Flag nodes in localPoly whose angles a1,a2 comprise a mixed element.
% [~,flag,~]	= intersect(localPoly,Tris);    	% Indices of 'polygon'.
flag = [];

% Initialize variables for computing angle.
mixed	= zeros(length(localPoly),1);	non	= mixed;	b	= mixed;

% Compute angle by which internal node iVertID will rotate.
if ~isempty(flag)                                   % Triangle detected in polygon.
    % Utilize flagged angles by indexing them into a seperate
    % vector from the non-flagged angles.
    mixed(flag)     = localPoly(flag);
    non(mixed == 0) = localPoly(mixed == 0);
    
    imix            = find(mixed ~= 0);             % Indices where mixed, non are
    inon            = find(non ~= 0);               % not equal to zero.
    
    % b is computed seperately for mixed elements and non-mixed
    % elements, via indices derived above.
    b(imix)         = (3.*a2(imix)-2.*a1(imix))./5; % Mixed element.
    b(inon)         = (3.*a2(inon)-2.*a1(inon))./5; % Not mixed.
    
else                                                % No triangle detected.
    non(mixed == 0) = localPoly(mixed ==0 );
    inon            = find(non ~= 0);              	% Indices.
    b(inon)         = (1.*a2(inon)-1.*a1(inon))./2;	% Not mixed.
end

% Rotate vc by angle b about NS(j), new iVertID coordinates:
x	= pc(:,1)+(currentXYZ(vertex,1)-pc(:,1)).*cos(b)-(currentXYZ(vertex,2)-pc(:,2)).*sin(b);
y	= pc(:,2)+(currentXYZ(vertex,1)-pc(:,1)).*sin(b)+(currentXYZ(vertex,2)-pc(:,2)).*cos(b);

% Average to determine the new location of iVertID.
currentXYZ(vertex,1)	= sum(x)/localPoly_nNodes;
currentXYZ(vertex,2)	= sum(y)/localPoly_nNodes;
end
