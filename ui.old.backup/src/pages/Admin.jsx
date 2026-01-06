import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';

function Admin() {
  const [activeTab, setActiveTab] = useState('api-keys');
  const [apiKeys, setApiKeys] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateKeyForm, setShowCreateKeyForm] = useState(false);
  const [keyFormData, setKeyFormData] = useState({
    name: '',
    expires_days: 30
  });

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'api-keys') {
        const response = await api.getApiKeys();
        setApiKeys(response.api_keys || response);
      } else if (activeTab === 'strategies') {
        const [strategiesResponse, topStrategiesResponse] = await Promise.all([
          api.getStrategies(),
          api.getTopStrategies()
        ]);
        setStrategies(topStrategiesResponse.strategies || topStrategiesResponse || strategiesResponse.strategies || strategiesResponse);
      }
    } catch (error) {
      console.error(`Failed to fetch ${activeTab}:`, error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateApiKey = async (e) => {
    e.preventDefault();
    try {
      await api.createApiKey(keyFormData.name, keyFormData.expires_days);
      setShowCreateKeyForm(false);
      setKeyFormData({ name: '', expires_days: 30 });
      fetchData();
    } catch (error) {
      console.error('Failed to create API key:', error);
    }
  };

  const handleDeleteApiKey = async (id) => {
    if (window.confirm('Are you sure you want to revoke this API key?')) {
      try {
        await api.deleteApiKey(id);
        fetchData();
      } catch (error) {
        console.error('Failed to revoke API key:', error);
      }
    }
  };

  const handleEnableStrategy = async (strategyId, accountId) => {
    try {
      await api.enableStrategy(strategyId, accountId);
      fetchData();
    } catch (error) {
      console.error('Failed to enable strategy:', error);
    }
  };

  const handleDisableStrategy = async (strategyId, accountId) => {
    try {
      await api.disableStrategy(strategyId, accountId);
      fetchData();
    } catch (error) {
      console.error('Failed to disable strategy:', error);
    }
  };

  if (loading) {
    return <div className="loading">Loading admin data...</div>;
  }

  return (
    <div className="admin">
      <div className="page-header">
        <h1>Admin Panel</h1>
      </div>

      <div className="admin-tabs">
        <button 
          className={`tab-btn ${activeTab === 'api-keys' ? 'active' : ''}`}
          onClick={() => setActiveTab('api-keys')}
        >
          API Keys
        </button>
        <button 
          className={`tab-btn ${activeTab === 'strategies' ? 'active' : ''}`}
          onClick={() => setActiveTab('strategies')}
        >
          Strategies
        </button>
      </div>

      {activeTab === 'api-keys' && (
        <div className="admin-section">
          <div className="section-header">
            <h2>API Keys</h2>
            <button 
              className="btn btn-primary"
              onClick={() => setShowCreateKeyForm(true)}
            >
              Generate API Key
            </button>
          </div>

          {showCreateKeyForm && (
            <div className="modal">
              <div className="modal-content">
                <h2>Generate API Key</h2>
                <form onSubmit={handleCreateApiKey}>
                  <div className="form-group">
                    <label>Key Name:</label>
                    <input
                      type="text"
                      value={keyFormData.name}
                      onChange={(e) => setKeyFormData({...keyFormData, name: e.target.value})}
                      placeholder="e.g., Trading Bot Key"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Expires In (days):</label>
                    <input
                      type="number"
                      value={keyFormData.expires_days}
                      onChange={(e) => setKeyFormData({...keyFormData, expires_days: parseInt(e.target.value)})}
                      min="1"
                      max="365"
                    />
                  </div>
                  <div className="form-actions">
                    <button type="submit" className="btn btn-primary">Generate</button>
                    <button 
                      type="button" 
                      className="btn btn-secondary"
                      onClick={() => setShowCreateKeyForm(false)}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Created</th>
                  <th>Last Used</th>
                  <th>Expires</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {apiKeys.map(key => (
                  <tr key={key.id}>
                    <td>{key.id}</td>
                    <td>{key.name}</td>
                    <td>{key.created_at ? new Date(key.created_at).toLocaleDateString() : '-'}</td>
                    <td>{key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : 'Never'}</td>
                    <td>{key.expires_at ? new Date(key.expires_at).toLocaleDateString() : 'Never'}</td>
                    <td>
                      <span className={`status ${key.is_active ? 'active' : 'inactive'}`}>
                        {key.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      <button 
                        className="btn btn-sm btn-danger"
                        onClick={() => handleDeleteApiKey(key.id)}
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {apiKeys.length === 0 && (
              <div className="no-data">
                <p>No API keys found</p>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'strategies' && (
        <div className="admin-section">
          <div className="section-header">
            <h2>Strategy Management</h2>
          </div>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Version</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {strategies.map(strategy => (
                  <tr key={strategy.id}>
                    <td>{strategy.id}</td>
                    <td>{strategy.strategy_name}</td>
                    <td>{strategy.strategy_version}</td>
                    <td>{strategy.strategy_source}</td>
                    <td>
                      <span className={`status ${strategy.is_active ? 'active' : 'inactive'}`}>
                        {strategy.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>{strategy.created_at ? new Date(strategy.created_at).toLocaleDateString() : '-'}</td>
                    <td>
                      <button className="btn btn-sm btn-secondary">
                        Configure
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {strategies.length === 0 && (
              <div className="no-data">
                <p>No strategies found</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Admin;