import React, { useEffect, useRef, useState } from 'react';
import { Trash2 } from 'lucide-react';
import rosConnection from './ros';

function MapComponent({ onPolygonChange }) {
  const mapContainerRef = useRef(null);
  const [viewer, setViewer] = useState(null);
  const [points, setPoints] = useState([]);
  const [robotPose, setRobotPose] = useState(null);
  const polygonMarkerRef = useRef(null);
  const robotMarkerRef = useRef(null);
  const viewerRef = useRef(null);
  const gridClientRef = useRef(null);
  const costmapClientRef = useRef(null);
  const tfClientRef = useRef(null);
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef(null);
  const [mapMode, setMapMode] = useState('both'); // 'static', 'costmap', or 'both'
  const mapModeRef = useRef(mapMode);

  useEffect(() => {
    // We only initialize if ROS is connected and window.ROS2D exists
    const rosObj = rosConnection.getRosObj();
    if (!rosObj || !window.ROS2D || !window.createjs) return;

    if (mapContainerRef.current) {
      mapContainerRef.current.innerHTML = '';
    }

    const width = mapContainerRef.current.clientWidth || 300;
    const height = width;

    const newViewer = new window.ROS2D.Viewer({
      divID: mapContainerRef.current.id,
      width: width,
      height: height
    });

    const newGridClient = new window.ROS2D.OccupancyGridClient({
      ros: rosObj,
      rootObject: newViewer.scene,
      continuous: true
    });

    const newCostmapClient = new window.ROS2D.OccupancyGridClient({
      ros: rosObj,
      rootObject: newViewer.scene,
      continuous: true,
      topic: '/global_costmap/costmap'
    });

    newCostmapClient.on('change', () => {
      if (newCostmapClient.currentGrid) {
        newCostmapClient.currentGrid.visible = (mapModeRef.current === 'costmap' || mapModeRef.current === 'both');
        newCostmapClient.currentGrid.alpha = mapModeRef.current === 'costmap' ? 1.0 : 0.4;
        
        // Push costmap down just above the static map (index 0) so it doesn't cover UI
        try {
          newViewer.scene.setChildIndex(newCostmapClient.currentGrid, 1);
        } catch (e) {
          // Ignore if scene isn't ready
        }
      }
      if (newViewer.scene && newViewer.scene.stage) {
        newViewer.scene.stage.update();
      }
    });

    newGridClient.on('change', () => {
      if (newGridClient.currentGrid) {
        newGridClient.currentGrid.visible = (mapModeRef.current === 'static' || mapModeRef.current === 'both');
      }
      newViewer.scaleToDimensions(newGridClient.currentGrid.width, newGridClient.currentGrid.height);
      newViewer.shift(newGridClient.currentGrid.pose.position.x, newGridClient.currentGrid.pose.position.y);

      if (!tfClientRef.current && window.ROSLIB) {
        tfClientRef.current = new window.ROSLIB.Topic({
          ros: rosObj,
          name: '/robot_pose',
          messageType: 'geometry_msgs/msg/PoseStamped'
        });

        tfClientRef.current.subscribe((msg) => {
          const q = msg.pose.orientation;
          const yaw = q ? Math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z)) : 0;
          setRobotPose({
            x: msg.pose.position.x, 
            y: msg.pose.position.y,
            orientation: q,
            theta: yaw
          });
        });
      }
    });

    setViewer(newViewer);
    viewerRef.current = newViewer;
    gridClientRef.current = newGridClient;
    costmapClientRef.current = newCostmapClient;

    return () => {
      if (tfClientRef.current) {
        tfClientRef.current.unsubscribe();
      }
    };
  }, []);

  useEffect(() => {
    mapModeRef.current = mapMode;
    if (gridClientRef.current && gridClientRef.current.currentGrid) {
      gridClientRef.current.currentGrid.visible = (mapMode === 'static' || mapMode === 'both');
    }
    if (costmapClientRef.current && costmapClientRef.current.currentGrid) {
      costmapClientRef.current.currentGrid.visible = (mapMode === 'costmap' || mapMode === 'both');
      costmapClientRef.current.currentGrid.alpha = mapMode === 'costmap' ? 1.0 : 0.4;
    }
    if (viewerRef.current && viewerRef.current.scene && viewerRef.current.scene.stage) {
      viewerRef.current.scene.stage.update();
    }
  }, [mapMode]);

  const calculateCoordinate = (clientX, clientY) => {
    if (!viewerRef.current || !gridClientRef.current) return null;
    const canvas = document.querySelector(`#${mapContainerRef.current.id} canvas`);
    if (!canvas) return null;

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    
    const internalX = (clientX - rect.left) * scaleX;
    const internalY = (clientY - rect.top) * scaleY;
    
    const pt = viewerRef.current.scene.globalToLocal(internalX, internalY);
    
    const grid = gridClientRef.current.currentGrid;
    if (!grid) return null;

    const fracX = internalX / canvas.width;
    const fracY = internalY / canvas.height;
    
    const rosX = grid.pose.position.x + fracX * grid.width;
    const rosY = grid.pose.position.y + (1.0 - fracY) * grid.height;

    return { visual: { x: pt.x, y: pt.y }, ros: { x: rosX, y: rosY }, clientX, clientY };
  };

  const handlePointerDown = (e) => {
    const coord = calculateCoordinate(e.clientX, e.clientY);
    if (!coord) return;
    
    isDraggingRef.current = true;
    dragStartRef.current = coord;
    
    // Start with a zero-area rectangle at the click point
    setPoints([coord, coord, coord, coord]);
  };

  const handlePointerMove = (e) => {
    if (!isDraggingRef.current || !dragStartRef.current) return;
    
    const start = dragStartRef.current;
    const current = calculateCoordinate(e.clientX, e.clientY);
    if (!current) return;

    // Build the 4 corners of the rectangle dynamically
    const p1 = start;
    const p2 = calculateCoordinate(current.clientX, start.clientY);
    const p3 = current;
    const p4 = calculateCoordinate(start.clientX, current.clientY);

    if (p1 && p2 && p3 && p4) {
      setPoints([p1, p2, p3, p4]);
    }
  };

  const handlePointerUp = () => {
    if (isDraggingRef.current) {
      isDraggingRef.current = false;
      dragStartRef.current = null;
    }
  };

  // Notify parent and redraw when points change
  useEffect(() => {
    onPolygonChange(points);
    drawPolygon(points);
  }, [points]);

  useEffect(() => {
    if (robotPose) {
      drawRobot(robotPose);
    }
  }, [robotPose]);

  const drawRobot = (pose) => {
    if (!viewerRef.current || !window.createjs || !gridClientRef.current) return;
    const scene = viewerRef.current.scene;

    if (robotMarkerRef.current) {
      scene.removeChild(robotMarkerRef.current);
    }

    const grid = gridClientRef.current.currentGrid;
    const canvas = document.querySelector(`#${mapContainerRef.current.id} canvas`);
    if (!grid || !canvas) return;

    const rosX = pose.x;
    const rosY = pose.y;

    const fracX = (rosX - grid.pose.position.x) / grid.width;
    const fracY = 1.0 - (rosY - grid.pose.position.y) / grid.height;

    const internalX = fracX * canvas.width;
    const internalY = fracY * canvas.height;

    const pt = scene.globalToLocal(internalX, internalY);

    const graphics = new window.createjs.Graphics();
    const radius = (8 / scene.scaleX) || 0.2;
    
    graphics.beginFill("#3b82f6");
    graphics.drawCircle(0, 0, radius);
    graphics.beginStroke("#ffffff").setStrokeStyle(radius * 0.3);
    graphics.moveTo(0, 0).lineTo(radius, 0);

    const shape = new window.createjs.Shape(graphics);
    shape.x = pt.x;
    shape.y = pt.y;

    if (pose.orientation) {
      const q = pose.orientation;
      const yaw = Math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z));
      shape.rotation = -yaw * (180.0 / Math.PI);
    }

    robotMarkerRef.current = shape;
    scene.addChild(shape);

    if (scene.stage) {
      scene.stage.update();
    }
  };

  const drawPolygon = (pts) => {
    if (!viewerRef.current || !window.createjs) return;
    const scene = viewerRef.current.scene;

    if (polygonMarkerRef.current) {
      scene.removeChild(polygonMarkerRef.current);
    }

    if (pts.length === 0) return;

    const graphics = new window.createjs.Graphics();
    graphics.setStrokeStyle(0.1); 
    graphics.beginStroke("#10b981");
    graphics.beginFill("rgba(16, 185, 129, 0.3)");
    
    graphics.moveTo(pts[0].visual.x, pts[0].visual.y);
    for (let i = 1; i < pts.length; i++) {
      graphics.lineTo(pts[i].visual.x, pts[i].visual.y);
    }
    
    if (pts.length > 2) {
      graphics.lineTo(pts[0].visual.x, pts[0].visual.y);
    }
    
    const shape = new window.createjs.Shape(graphics);
    polygonMarkerRef.current = shape;
    scene.addChild(shape);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', width: '100%', position: 'relative' }}>
      <div className="map-mode-selector">
        <button 
          className={`map-mode-btn ${mapMode === 'static' ? 'active' : ''}`}
          onClick={() => setMapMode('static')}
        >
          Static Map
        </button>
        <button 
          className={`map-mode-btn ${mapMode === 'costmap' ? 'active' : ''}`}
          onClick={() => setMapMode('costmap')}
        >
          Costmap
        </button>
        <button 
          className={`map-mode-btn ${mapMode === 'both' ? 'active' : ''}`}
          onClick={() => setMapMode('both')}
        >
          Overlay
        </button>
      </div>

      <div style={{ position: 'relative', width: '100%', aspectRatio: '1' }}>
        {!viewer && (
          <div style={{ 
            position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
            display: 'flex', alignItems: 'center', 
            justifyContent: 'center', color: '#94a3b8', zIndex: 10,
            pointerEvents: 'none'
          }}>
            Loading map...
          </div>
        )}
        <div 
          id="ros2d-map-container" 
          ref={mapContainerRef}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
          style={{ 
            width: '100%', 
            height: '100%', 
            backgroundColor: '#0f172a',
            borderRadius: '12px',
            overflow: 'hidden',
            border: '2px dashed #334155',
            touchAction: 'none' 
          }} 
        />
      </div>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '14px', color: '#94a3b8' }}>
          {points.length === 0 ? "Drag on map to draw coverage area" : `Area Selected`}
        </span>
        {points.length > 0 && (
          <button 
            onClick={() => setPoints([])}
            style={{ 
              background: 'transparent', 
              color: '#ef4444', 
              border: '1px solid #ef4444',
              padding: '6px 12px',
              fontSize: '14px'
            }}
          >
            <Trash2 size={16} /> Clear
          </button>
        )}
      </div>
      {robotPose && (
        <div style={{ fontSize: '12px', color: '#10b981', textAlign: 'center' }}>
          Live Robot Pose: X: {robotPose.x.toFixed(2)} | Y: {robotPose.y.toFixed(2)} | θ: {(robotPose.theta * 180 / Math.PI).toFixed(1)}° ({robotPose.theta.toFixed(2)} rad)
        </div>
      )}
    </div>
  );
}

export default MapComponent;
