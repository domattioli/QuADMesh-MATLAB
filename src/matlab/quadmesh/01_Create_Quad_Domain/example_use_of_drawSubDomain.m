% Create triangulation
meshSize    = 10000;
points = rand(meshSize,2);
dt = delaunayTriangulation(points);
figure; triplot(dt);

% Draw subdomain(s).
[X,Y]  = drawSubdomain(gca);

% Find points that are within polygon defined by [X,Y];
inPoints= false(length(points),1);
for idx = 1:length(X)
    inPoints(inpolygon(points(:,1),points(:,2),X{idx},Y{idx}))	= true;
end

% If this were a CHILmesh object we could identify and highlight specific
% edges that define the new subDomain. I need to poo and then go home,
% otherwise I'd code it up myself so here is just the plotted points.
hold on; plot(points(inPoints,1),points(inPoints,2),'r*');

% We could just do a simple ismember of the connectivity list to determine
% which triangles will be the new subdomain.