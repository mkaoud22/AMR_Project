import { useState, useEffect } from 'react';
import { 
  BatteryMedium, 
  Play, 
  Square,
  Crosshair
} from 'lucide-react';
import rosConnection from './ros';
import MapComponent from './MapComponent';

function App() {
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState('Idle');
  const [battery, setBattery] = useState(85);
  const [ip, setIp] = useState(window.location.hostname || 'localhost');
  const [polygonPoints, setPolygonPoints] = useState([]);

  useEffect(() => {
    // Subscribe to ROS connection status
    const unsubscribe = rosConnection.subscribeConnection((isConnected) => {
      setConnected(isConnected);
      if (isConnected) {
        setStatus('Ready');
      } else {
        setStatus('Offline');
      }
    });

    return () => {
      unsubscribe();
      rosConnection.disconnect();
    };
  }, []);

  const handleConnect = () => {
    if (connected) {
      rosConnection.disconnect();
    } else {
      let connectionUrl = ip;
      // If the user enters a full ngrok/localtunnel URL, use it directly.
      // Otherwise, assume it's a local IP and append ws:// and port 9090.
      if (!connectionUrl.startsWith('ws://') && !connectionUrl.startsWith('wss://')) {
        connectionUrl = `ws://${ip}:9090`;
      }
      rosConnection.connect(connectionUrl);
    }
  };

  const handleStartCoverage = () => {
    if (!connected) {
      alert("Please connect to the robot first.");
      return;
    }
    
    if (polygonPoints.length < 3) {
      alert("Please tap at least 3 points on the map to draw a coverage zone.");
      return;
    }

    setStatus('Sending Path...');
    const rosPoints = polygonPoints.map(p => p.ros);
    rosConnection.sendCoveragePolygon(rosPoints);
    setTimeout(() => setStatus('Cleaning'), 1000);
  };

  const handleStop = () => {
    if (!connected) return;
    setStatus('Returning to Dock...');
    rosConnection.sendStopCommand();
  };

  return (
    <div className="app-container">
      <div className="header">
        <h1>AMR Control</h1>
        <div 
          className={`status-badge ${connected ? 'connected' : 'disconnected'}`}
          onClick={handleConnect}
          style={{ cursor: 'pointer' }}
          title="Tap to connect/disconnect"
        >
          <div className="status-dot" />
          {connected ? 'Connected' : 'Offline'}
        </div>
      </div>

      {!connected && (
        <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
          <input 
            type="text" 
            value={ip} 
            onChange={(e) => setIp(e.target.value)} 
            placeholder="Robot IP"
            style={{ flex: 1, padding: '8px 12px', borderRadius: '8px', border: '1px solid #334155', background: '#1e293b', color: '#fff' }}
          />
          <button className="primary" onClick={handleConnect} style={{ padding: '8px 16px', borderRadius: '8px' }}>Connect</button>
        </div>
      )}

      <div className="card">
        <div className="card-title">Live Map</div>
        {connected ? (
          <MapComponent onPolygonChange={setPolygonPoints} />
        ) : (
          <div className="map-placeholder" style={{ padding: '20px' }}>
            <span style={{opacity: 0.5}}>Connect to view map</span>
          </div>
        )}
      </div>

      <div className="stats-grid">
        <div className="stat-item">
          <div className="stat-icon">
            <BatteryMedium size={24} />
          </div>
          <div className="stat-value">
            <span>Battery</span>
            <span>{battery}%</span>
          </div>
        </div>
        <div className="stat-item">
          <div className="stat-icon">
            <Crosshair size={24} />
          </div>
          <div className="stat-value">
            <span>Status</span>
            <span>{status}</span>
          </div>
        </div>
      </div>

      <div className="controls">
        <button className="primary" onClick={handleStartCoverage} disabled={!connected || polygonPoints.length < 3} style={{ opacity: connected && polygonPoints.length >= 3 ? 1 : 0.5 }}>
          <Play size={20} />
          Start Coverage Area
        </button>
        <button className="danger" onClick={handleStop} disabled={!connected} style={{ opacity: connected ? 1 : 0.5 }}>
          <Square size={20} />
          Stop & Return to Dock
        </button>
      </div>
    </div>
  );
}

export default App;
