import { useState, useEffect } from 'react';
import { 
  BatteryMedium, 
  Play, 
  Square,
  Crosshair,
  ShieldAlert
} from 'lucide-react';
import rosConnection from './ros';
import MapComponent from './MapComponent';

function App() {
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState('Idle');
  const [battery, setBattery] = useState(85);
  const [ip, setIp] = useState(window.location.hostname || 'localhost');
  const [activeMode, setActiveMode] = useState('coverage'); // 'coverage' or 'nogo'
  const [coveragePoints, setCoveragePoints] = useState([]);
  const [nogoPoints, setNogoPoints] = useState([]);

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
    
    if (coveragePoints.length < 3) {
      alert("Please drag on the map to draw a coverage zone first.");
      return;
    }

    setStatus('Sending Path...');
    const rosPoints = coveragePoints.map(p => p.ros);
    rosConnection.sendCoveragePolygon(rosPoints);
    setTimeout(() => setStatus('Cleaning'), 1000);
  };

  const handleSendNoGoZone = () => {
    if (!connected) {
      alert("Please connect to the robot first.");
      return;
    }
    
    if (nogoPoints.length < 3) {
      alert("Please drag on the map to draw a no-go zone first.");
      return;
    }

    setStatus('Sending No-Go Zone...');
    const rosPoints = nogoPoints.map(p => p.ros);
    rosConnection.sendNoGoZone(rosPoints);
    setTimeout(() => {
      setStatus('No-Go Zone Set');
      setTimeout(() => setStatus('Ready'), 2000);
    }, 1000);
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="card-title">Live Map</div>
          {connected && (
            <div className="draw-mode-toggle">
              <button 
                className={`toggle-btn ${activeMode === 'coverage' ? 'active-coverage' : ''}`}
                onClick={() => setActiveMode('coverage')}
              >
                Draw Coverage
              </button>
              <button 
                className={`toggle-btn ${activeMode === 'nogo' ? 'active-nogo' : ''}`}
                onClick={() => setActiveMode('nogo')}
              >
                Draw No-Go
              </button>
            </div>
          )}
        </div>
        {connected ? (
          <MapComponent 
            activeMode={activeMode}
            coveragePoints={coveragePoints}
            onCoverageChange={setCoveragePoints}
            nogoPoints={nogoPoints}
            onNoGoChange={setNogoPoints}
          />
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
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <button 
            className="primary" 
            onClick={handleStartCoverage} 
            disabled={!connected || coveragePoints.length < 3} 
            style={{ opacity: connected && coveragePoints.length >= 3 ? 1 : 0.5 }}
          >
            <Play size={20} />
            Start Coverage
          </button>
          <button 
            className="warning-nogo" 
            onClick={handleSendNoGoZone} 
            disabled={!connected || nogoPoints.length < 3} 
            style={{ opacity: connected && nogoPoints.length >= 3 ? 1 : 0.5 }}
          >
            <ShieldAlert size={20} />
            Send No-Go
          </button>
        </div>
        <button className="danger" onClick={handleStop} disabled={!connected} style={{ opacity: connected ? 1 : 0.5 }}>
          <Square size={20} />
          Stop & Return to Dock
        </button>
      </div>
    </div>
  );
}

export default App;
