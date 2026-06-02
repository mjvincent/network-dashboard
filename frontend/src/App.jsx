import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Server, 
  Search, 
  Cpu, 
  Database, 
  Activity
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';
import './App.css';

const App = () => {
  // State variables
  const [networkData, setNetworkData] = useState(null);
  const [portData, setPortData] = useState(null);
  const [ubuntuMetrics, setUbuntuMetrics] = useState(null);

  // Function to check API health
  const checkApiHealth = async () => {
    try {
      const response = await axios.get('/api/health');
      console.log('API is healthy:', response.data);
    } catch (error) {
      console.error('Error checking API health:', error);
    }
  };

  const fetchNetworkData = async () => {
    try {
      const response = await axios.get('/api/scan?network_range=192.168.1.0/24');
      setNetworkData(response.data);
    } catch (error) {
      console.error('Error fetching network data:', error);
    }
  };

  const fetchPortData = async (host) => {
    try {
      const response = await axios.get(`/api/scan/ports?host=${host}&port_range=1-1024`);
      setPortData(response.data);
    } catch (error) {
      console.error('Error fetching port data:', error);
    }
  };

  const fetchUbuntuMetrics = async () => {
    try {
      const response = await axios.get('/api/metrics/ubuntu');
      setUbuntuMetrics(response.data);
    } catch (error) {
      console.error('Error fetching Ubuntu metrics:', error);
    }
  };

  // useEffect to call the fetch functions on component mount
  useEffect(() => {
    checkApiHealth();
    fetchNetworkData();
    fetchUbuntuMetrics();
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Network Dashboard</h1>
        <div className="status-container">
          <div className={`status-item ${ubuntuMetrics ? 'online' : 'offline'}`}>
            <Activity size={20} />
            <span className="status-text">Ubuntu Metrics: {ubuntuMetrics ? 'Online' : 'Offline'}</span>
          </div>
          <div className={`status-item ${networkData ? 'online' : 'offline'}`}>
            <Search size={20} />
            <span className="status-text">Network Scan: {networkData ? 'Ready' : 'Idle'}</span>
          </div>
        </div>
      </header>
      
      <main className="App-main">
        <section className="dashboard-section">
          <h2>Network Scan Results</h2>
          {networkData && networkData.length > 0 ? (
            <div className="network-grid">
              {networkData.map((device) => (
                <div key={device.ip} className="device-card" onClick={() => fetchPortData(device.ip)}>
                  <Server size={32} />
                  <h3 className="device-ip">{device.ip}</h3>
                  <p className="device-hostname">{device.hostname || 'Unknown Host'}</p>
                  {portData && portData.find(p => p.port === device.ip) && (
                    <div className="port-info">
                      {/* Port info would go here */}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p>No devices found or scanning...</p>
          )}
        </section>

        {ubuntuMetrics && (
          <section className="metrics-section">
            <h2>Ubuntu System Metrics</h2>
            <div className="metrics-grid">
              <div className="metric-card">
                <Cpu size={32} />
                <p>CPU Usage: {ubuntuMetrics.cpu_usage}%</p>
              </div>
              <div className="metric-card">
                <Database size={32} />
                <p>Memory Usage: {ubuntuMetrics.memory_usage}%</p>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
};

export default App;