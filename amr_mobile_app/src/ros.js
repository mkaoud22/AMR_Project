const ROSLIB = window.ROSLIB;

class RosConnection {
  constructor() {
    this.ros = null;
    this.connected = false;
    this.listeners = [];
  }

  connect(url = 'ws://localhost:9090') {
    if (this.ros) return;

    this.ros = new ROSLIB.Ros({
      url: url
    });

    this.ros.on('connection', () => {
      console.log('Connected to websocket server.');
      this.connected = true;
      this.notifyListeners(true);
    });

    this.ros.on('error', (error) => {
      console.log('Error connecting to websocket server: ', error);
      this.connected = false;
      this.notifyListeners(false);
    });

    this.ros.on('close', () => {
      console.log('Connection to websocket server closed.');
      this.connected = false;
      this.notifyListeners(false);
      this.ros = null;
    });
  }

  disconnect() {
    if (this.ros) {
      this.ros.close();
    }
  }

  getRosObj() {
    return this.ros;
  }

  subscribeConnection(callback) {
    this.listeners.push(callback);
    callback(this.connected);
    return () => {
      this.listeners = this.listeners.filter(l => l !== callback);
    };
  }

  notifyListeners(status) {
    this.listeners.forEach(callback => callback(status));
  }

  // Publish coverage polygon
  sendCoveragePolygon(points) {
    if (!this.connected || !this.ros) {
      console.error("Cannot send polygon: ROS not connected");
      return;
    }

    const polygonTopic = new ROSLIB.Topic({
      ros: this.ros,
      name: '/coverage_polygon',
      messageType: 'geometry_msgs/PolygonStamped'
    });

    // points is an array of {x, y}
    const polygonMsg = new ROSLIB.Message({
      header: {
        frame_id: 'map'
      },
      polygon: {
        points: points.map(p => ({ x: p.x, y: p.y, z: 0.0 }))
      }
    });

    polygonTopic.publish(polygonMsg);
    console.log("Published polygon:", polygonMsg);
  }

  // Publish stop and dock command
  sendStopCommand() {
    if (!this.connected || !this.ros) {
      console.error("Cannot send stop command: ROS not connected");
      return;
    }

    const stopTopic = new ROSLIB.Topic({
      ros: this.ros,
      name: '/stop_and_dock',
      messageType: 'std_msgs/Empty'
    });

    const emptyMsg = new ROSLIB.Message({});
    stopTopic.publish(emptyMsg);
    console.log("Published stop and dock command");
  }

  // Publish no-go zone polygon
  sendNoGoZone(points) {
    if (!this.connected || !this.ros) {
      console.error("Cannot send no-go zone: ROS not connected");
      return;
    }

    const nogoTopic = new ROSLIB.Topic({
      ros: this.ros,
      name: '/nogo_zone',
      messageType: 'geometry_msgs/PolygonStamped'
    });

    // points is an array of {x, y}
    const polygonMsg = new ROSLIB.Message({
      header: {
        frame_id: 'map'
      },
      polygon: {
        points: points.map(p => ({ x: p.x, y: p.y, z: 0.0 }))
      }
    });

    nogoTopic.publish(polygonMsg);
    console.log("Published no-go zone:", polygonMsg);
  }
}

// Create a singleton instance
const rosConnection = new RosConnection();
export default rosConnection;
