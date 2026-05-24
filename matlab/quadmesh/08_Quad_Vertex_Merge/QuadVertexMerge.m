function [CM,removedVertIDs]	= QuadVertexMerge(CM)
%QUADVERTEXMERGE Removes quads w/ valence-3 diagonals nodes.
%   [CM,removedVertIDs] = QuadVertexMerge(CM) returns ...
%
%   At some point, change code to not have the stupid vertex
%   attachments part and so that the rest of the code operates
%   soley on information provided by Q (don't output T). Also,
%   make it so other topological operations are incorporated
%   into this, i.e. a "QuadRemoval" function that calls QVM and
%   other functions.
%   See also: POSTPROCESSROUTINE, DOUBLETCOLLAPSE, TRUNCATEBOUNDARYQUADS.
%==========================================================================

% Identify diagonals not extending from the mesh boundaries.
[~,iQ]  = CM.elemType;
[VertIDs,ElemIDs]	= CM.diagonals('ElemIDs',iQ,'store','m');
ibVertIDs   = CM.edge2Vert(CM.boundaryEdges);       % Boundary diags.
VertIDs(ibVertIDs,:)	= [];                    	% Remove D that extend
ElemIDs(ibVertIDs)	= [];                           % from CM boundaries
idxTriElemIDs	= sum(VertIDs == 0,2) > 0;        	% Triangles.
VertIDs(idxTriElemIDs,:)= [];                     	% Remove D of tris.
ElemIDs(idxTriElemIDs)	= [];

% Get valence of VertIDs.
valenceVertIDs	= {CM.vert2Elem('vertids',VertIDs(:,1),'store','m'),...
    CM.vert2Elem('vertids',VertIDs(:,2),'store','m')};
maxValence	= max([size(valenceVertIDs{1},2),size(valenceVertIDs{2},2)]);

% Collapse quads
iLayer   = 1;                                       % Current layer.
stoppingCriteria	= true(CM.nLayers+1,1);     	% Stopping criteria.
while stoppingCriteria(end)
    % Populate list of eligible quads EQL.
    if stoppingCriteria(end-1)                      % Get index to inner elems.
        idxIE	= ismember(ElemIDs,CM.Layers.IE{iLayer});
    end
    
    % Index to eligible diagonals.
    idxEligibleD	= sum([sum(valenceVertIDs{1} > 0,2) == 3,...
        sum(valenceVertIDs{2} > 0,2) == 3],2) == 2;
    
    % Priority: iLayer IE quads, then iLayer OE, iLayer IE, then iLayer OE.
    if stoppingCriteria(1)                          % iLayer IE quads.
        % Search for eligible IW quads in iLayer.
        idxEligibleElemIDs	= idxIE & idxEligibleD;
        EligibleElemIDs	= ElemIDs(idxEligibleElemIDs);
        if isempty(EligibleElemIDs)                 % None eligible.
            stoppingCriteria(iLayer)   = false;   	% Update stop criteria.
            iLayer   = iLayer + 1;              	% Next layer.
            continue
        end
        
    elseif stoppingCriteria(end-1)                  % iLayer-1 OE, iLayer IE, then iLayer OE.
        % Search for eligible iLayer-1 OE quads.
        idxOEiLayerm1	= ismember(ElemIDs,CM.Layers.OE{iLayer-1});
        idxOEiLayer	= ismember(ElemIDs,CM.Layers.OE{iLayer});
        idxEligibleElemIDs	= idxOEiLayerm1 & idxEligibleD;
        EligibleElemIDs	= ElemIDs(idxEligibleElemIDs);
        
        if isempty(EligibleElemIDs)                 % No iLayer-1 OE quads eligible.
            % Search for eligible iLayer IE quads.
            idxEligibleElemIDs	= idxIE & idxEligibleD;
            EligibleElemIDs	= ElemIDs(idxEligibleElemIDs);
            
            if isempty(EligibleElemIDs)             % No iLayer IE quads eligible.
                % Search for eligible iLayer OF quads.
                idxEligibleElemIDs	= idxOEiLayer & idxEligibleD;
                EligibleElemIDs	= ElemIDs(idxEligibleElemIDs);
                
                if isempty(EligibleElemIDs)         % No iLayer OE quads eligible.
                    stoppingCriteria(iLayer)   = false;
                    iLayer   = iLayer + 1;
                    continue
                end
            end
        end
        
    else
        % Check if any eligible quads remain.
        if any(idxEligibleD)                        % Eligible quads still exist.
            idxEligibleElemIDs	= idxEligibleD;
            EligibleElemIDs	= ElemIDs(idxEligibleElemIDs);
            
        else                                        % No eligible quads exist.
            stoppingCriteria(end)	= false;      	% End operation.
            continue
        end
    end
    
    % Eligible quad's diagonal's vertices and their respective incident elems.
    diagonalVertIDs   = VertIDs(EligibleElemIDs(1),:);
    valenceDiagonalVertIDs	= valenceVertIDs{1}(EligibleElemIDs(1),:);
    
    % Perform Quad Vertex Merge operation.
    quads   = [EligibleElemIDs(1),...
        valenceDiagonalVertIDs(1,~ismember(valenceDiagonalVertIDs(1,:),...
        EligibleElemIDs(1) & valenceDiagonalVertIDs(1,:)>0))]';
    CM.ConnectivityList(q,:)	= QVMfun(CM,quads,diagonalVertIDs);
    
    % Update VertIDs and ElemIDs by flagging, substitutine nodes, flagging quads.
    idx_q1	= ismember(ElemIDs,q(1));
    VertIDs(idx_q1,:)	= 0;                        % Remove unused diags.
    VertIDs(ismember(VertIDs,diagonalVertIDs(1,1)))   = diagonalVertIDs(1,2);
    ElemIDs(idx_q1)	= 0;                            % Remove unused quad.

    % Update Dva.
    Dva1    = valenceVertIDs{1};                  	% Create variables for
    Dva2	= valenceVertIDs{2};                    % easier code-reading.
    Dva1(idx_q1,:)	= 0;                            % Remove q(1)'s diags'
    Dva2(idx_q1,:)	= 0;                            % va from Dva.
    Dva1(ismember(Dva1,q(1)))   = 0;
    Dva2(ismember(Dva2,q(1)))   = 0;
    newDva  = [quads(2:3); CM.VA{...
        diagonalVertIDs(1,2)}(~ismember(CM.VA{diagonalVertIDs(1,2)},q(1)))]';
    newdiagva	= NaN(1,maxValence);     	% New diagonal(s)'s va.
    newdiagva(1:length(newDva))	= newDva;

    iq2_Dva1	= sum(ismember(Dva1,q),2) == 3;
    if any(iq2_Dva1)    % Identify diagonal va that includes all of q.
        Dva1(iq2_Dva1,:)= repmat(newdiagva,size(Dva1(iq2_Dva1,:),1),1);
    else                % and update the indexed diagonal(s).
        iq2_Dva2	= sum(ismember(Dva2,q),2) == 3;
        Dva2(iq2_Dva2,:)= repmat(newdiagva,size(Dva2(iq2_Dva2,:),1),1);
    end
    Dva{1}  = Dva1;                 	% Update Dva.
    Dva{2}  = Dva2;
end

% Update CM.
CM.ConnectivityList(...               % Remove flagged quads.
    isnan(CM.ConnectivityList(:,1)),:)	= [];
CM.ConnectivityList   = CWpoly(CM); % Ensure CCW orientation.
[iT,iQ]	= splitMESH(CM);
T   = CM.ConnectivityList(iT,:);      % Triangles in CM.
Q   = CM.ConnectivityList(iQ,:);      % Quads in CM.
CM.ConnectivityList   = [Q;T];
CM    = MESHFacets(CM,'EN','BE');%,'FN','VA');
CM    = MESHLayers(CM);
end

function newConn = QVMfun(CM,quads,diagonalVertIDs)
%QVMfun Squeezes out first quad listed in "quads".
%==========================================================================

quadsConn  = CM.ConnectivityList(quads,:);
quadsConn(2,ismember(quadsConn(2,:),diagonalVertIDs(1,1)))	= diagonalVertIDs(1,2);
quadsConn(3,ismember(quadsConn(3,:),diagonalVertIDs(1,1)))	= diagonalVertIDs(1,2);
newConn  = [zeros(1,4); quadsConn(2:3,:)];
end