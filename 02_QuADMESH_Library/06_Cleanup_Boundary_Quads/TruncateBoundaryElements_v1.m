function [MESH,mesh0,T,Q] = TruncateBoundaryElements(MESH,mesh0,T,Q)
    %======================================================================
    %TruncateBoundaryElements Removes tris on fb with only 1 attachment.
    %   [MESH,T,Q] = TruncateBoundaryElements(MESH,T,Q) returns the
    %   updated mesh object MESH removed of all bounday elements which
    %   originally had only 1 attached/neighboring elements.
    %
    %   See also 
    %======================================================================
    
    % Get details of MESH.
    C	= MESH.ConnectivityList;              	% Connectivivty list.
    MESH.AE     = elementAttachments(MESH);     % Element attachments list.
    AE  = MESH.AE;
    
    %----------------------------------------------------------------------
    % Remove any quad or tri with only 1 attachment
    %----------------------------------------------------------------------
    iAE = find(sum(isnan(AE),2) == 3);      iC	= [];
    if isempty(iAE)                             % End function.
        return
    end
    while ~isempty(iAE)
        % Store indices of removed elements.
        iAE(ismember(iAE,iC)) = [];
        iC   = cat(1,iC,iAE);
        
        % Flag quad(s)/tri(s) within MESH.AE field.
        AE(iAE,:)	= NaN;
        AE(ismember(AE,iAE))    = NaN;
        
        % Get any newly-eligible quad(s)/tri(s).
        iAE	= find(sum(isnan(AE),2) == 3);
    end
    
    %----------------------------------------------------------------------
    % % Update details of final (MESH) and original (mesh0).
    %----------------------------------------------------------------------
%     nT  = size(T,1);                            % Number of tris in MESH.
%     idx	= ismember(iC,1:nT);                    % Index any tris in iC to T.
%     T(iC(idx),:)    = NaN;                      % Flag tris in T.
%     Q(iC(~idx)-nT,:)= NaN;                      % Flag quads in Q.
%     MESH.ConnectivityList	= cat(1,T,Q);
%     [MESH.EA,MESH.E]	= edgeAttachments(MESH);
%     MESH.EA  	= EAcell2mat(MESH,'special',MESH.EA);
%     [MESH.FB.fb,MESH.FB.ifb,MESH.FB.I]	= freeBoundary(MESH);
     
    % Index to tris in mesh0 that correspond to removed elements of iC.
    CT  = mesh0.ConnectivityList;
    iCT	= sum(ismember(CT,C(iC,:)),2) > 2;
    
    % Flag iC in C and iCT in CT.
    C(iC,:)     = NaN;
    CT(iCT,:)	= NaN;
    
    % Update final (MESH) and original (mesh0) objects.
    MESH.ConnectivityList   = C;
    [MESH.EA,MESH.E]        = edgeAttachments(MESH);
    MESH.EA     = EAcell2mat(MESH,'special',MESH.EA);
    [MESH.FB.fb,MESH.FB.ifb,MESH.FB.I]  = freeBoundary(MESH);
    MESH.AE     = elementAttachments(MESH);
    mesh0.ConnectivityList  = CT;
    [mesh0.EA,mesh0.E]   	= edgeAttachments(mesh0);
    mesh0.EA   	= EAcell2mat(mesh0,'special',mesh0.EA);
    [mesh0.FB.fb,mesh0.FB.ifb,mesh0.FB.I]	= freeBoundary(mesh0);
    mesh0.AE   	= elementAttachments(mesh0);
    mesh0       = RemoveUnusedNodes(mesh0);
    [T,Q]       = splitMESH(MESH);
end

