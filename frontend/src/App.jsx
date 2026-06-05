import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [searchTerm, setSearchTerm] = useState('');
  const [devices, setDevices] = useState([]);
   const [metrics, setMetrics] = useState([]);
   const [loading, setLoading] = useState(true);
   const [error, setError] = useState(null);
   const [searchResults, setSearchResults] = useState([]);
   const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoading(true);
      setError(null);
      try {
        // 1. Fetch devices list
        const devicesResponse = await fetch('/api/devices');
        const devicesData = await devicesResponse.json();
        setDevices(devicesData.devices || []);

        // 2. Fetch system metrics
        const metricsResponse = await fetch('/api/metrics');
        const metricsData = await metricsResponse.json();
        setMetrics(metricsData.metrics || []);
      } catch (e) {
        console.error('Error fetching dashboard data:', e);
        setError('Failed to load dashboard data. Please check the backend API status.');
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;

    setIsSearching(true);
    setSearchResults([]);
    setError(null);

    try {
      const response = await fetch(`/api/search?q=${encodeURIComponent(searchTerm)}`);
      const data = await response.json();
      setSearchResults(data.results || []);
    } catch (e) {
      console.error('Search failed:', e);
      setError('Failed to perform search. Please check the backend API status.');
    } finally {
      setIsSearching(false);
    }
  };

  if (loading) {
    return <div className="App">Loading dashboard data...</div>;
  }

  if (error) {
    return <div className="App" style={{ color: 'red' }}>Error: {error}</div>;
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1 className="title">Network Dashboard</h1>
        <input
          type="text"
          placeholder="Search for IP or hostname..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />

        {/* Search Results Display */}
        <div className="results-container">
          {isSearching && <div className="result-item loading"><p>Searching...</p></div>}
          {error && <div className="result-item error"><p>{error}</p></div>}
          {searchTerm && searchResults.length > 0 && (
            <div className="result-item results-list">
              <h4 className="search-title">Results for "{searchTerm}" ({searchResults.length} found)</h4>
              {searchResults.map((result, index) => (
                <div key={index} className="result-item">
                  <p className="search-query-match">... matched</p>
                  <div className="details">
                    <p className="search-description">{result.description}</p>
                    <button className="search-button">View Details</button>
                  </div>
                </div>
              ))}
            </div>
          )}
          {searchTerm && searchResults.length === 0 && !isSearching && !error && (
            <div className="result-item">
              <p>No results found for "{searchTerm}".</p>
            </div>
          )}
          {!searchTerm && (
            <div className="result-item">
              <p>Start typing to view network results.</p>
            </div>
          )}
        </div>

        {/* Network Visualization Area */}
        <div className="visualization-placeholder">
          <h2 className="visualization-title">Network Topology Visualization</h2>
          {/* Placeholder for Network Diagram visualization using a dedicated library */}
          <div className="diagram-placeholder">
            <p>Visualization module to display device connectivity and network flows will be integrated here.</p>
            {/* Diagram visualization area */}
          </div>
        </div>
      </header>

      {/* Metrics Grid */}
      <div className="metrics-grid">
        {metrics.length > 0 && (
          <div className="card metrics-card">
            <h3>Influx Samples</h3>
            <p className="metric-value">{metrics.length}</p>
            <p className="metric-detail">Latest custom agent fields</p>
          </div>
        )}
        {devices.length > 0 && (
          <div className="card metrics-card">
            <h3>Devices Discovered</h3>
            <p className="metric-value">{devices.length}</p>
            <p className="metric-detail">Registered hosts</p>
          </div>
        )}
      </div>

      {/* Devices List */}
      <div className="devices-list-container">
        <h2>Discovered Devices ({devices.length})</h2>
        <table className="devices-table">
          <thead>
            <tr>
              <th>IP Address</th>
              <th>Hostname</th>
              <th>MAC Address</th>
              <th>Status</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((device, index) => (
              <tr key={index}>
                <td>{device.ip || 'N/A'}</td>
                <td>{device.hostname || 'N/A'}</td>
                <td>{device.mac || 'N/A'}</td>
                <td><span className={`status status-${(device.status || 'Unknown').toLowerCase()}`}>{device.status || 'Unknown'}</span></td>
                <td><button className="detail-button">View</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default App;
