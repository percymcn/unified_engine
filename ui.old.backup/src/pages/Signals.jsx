import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';

function Signals() {
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({
    symbol: '',
    action: 'BUY',
    volume: 0.01,
    price: 0,
    stop_loss: 0,
    take_profit: 0,
    comment: ''
  });

  useEffect(() => {
    fetchSignals();
  }, []);

  const fetchSignals = async () => {
    try {
      const response = await api.getSignals();
      setSignals(response.signals || response);
    } catch (error) {
      console.error('Failed to fetch signals:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSignal = async (e) => {
    e.preventDefault();
    try {
      await api.createSignal(formData);
      setShowCreateForm(false);
      setFormData({
        symbol: '',
        action: 'BUY',
        volume: 0.01,
        price: 0,
        stop_loss: 0,
        take_profit: 0,
        comment: ''
      });
      fetchSignals();
    } catch (error) {
      console.error('Failed to create signal:', error);
    }
  };

  const handleCancelSignal = async (id) => {
    if (window.confirm('Are you sure you want to cancel this signal?')) {
      try {
        await api.post(`/api/v1/signals/${id}/cancel`);
        fetchSignals();
      } catch (error) {
        console.error('Failed to cancel signal:', error);
      }
    }
  };

  const handleExecuteSignal = async (id) => {
    try {
      await api.post('/api/v1/signals/execute', { signal_id: id });
      fetchSignals();
    } catch (error) {
      console.error('Failed to execute signal:', error);
    }
  };

  if (loading) {
    return <div className="loading">Loading signals...</div>;
  }

  return (
    <div className="signals">
      <div className="page-header">
        <h1>Trading Signals</h1>
        <div className="actions">
          <button 
            className="btn btn-primary"
            onClick={() => setShowCreateForm(true)}
          >
            Create Signal
          </button>
          <button className="btn btn-secondary" onClick={fetchSignals}>
            Refresh
          </button>
        </div>
      </div>

      {showCreateForm && (
        <div className="modal">
          <div className="modal-content">
            <h2>Create New Signal</h2>
            <form onSubmit={handleCreateSignal}>
              <div className="form-group">
                <label>Symbol:</label>
                <input
                  type="text"
                  value={formData.symbol}
                  onChange={(e) => setFormData({...formData, symbol: e.target.value})}
                  placeholder="e.g., EURUSD"
                  required
                />
              </div>
              <div className="form-group">
                <label>Action:</label>
                <select
                  value={formData.action}
                  onChange={(e) => setFormData({...formData, action: e.target.value})}
                >
                  <option value="BUY">BUY</option>
                  <option value="SELL">SELL</option>
                  <option value="CLOSE">CLOSE</option>
                </select>
              </div>
              <div className="form-group">
                <label>Volume:</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.volume}
                  onChange={(e) => setFormData({...formData, volume: parseFloat(e.target.value)})}
                  required
                />
              </div>
              <div className="form-group">
                <label>Price (optional, 0 for market):</label>
                <input
                  type="number"
                  step="0.00001"
                  value={formData.price}
                  onChange={(e) => setFormData({...formData, price: parseFloat(e.target.value)})}
                />
              </div>
              <div className="form-group">
                <label>Stop Loss (optional):</label>
                <input
                  type="number"
                  step="0.00001"
                  value={formData.stop_loss}
                  onChange={(e) => setFormData({...formData, stop_loss: parseFloat(e.target.value)})}
                />
              </div>
              <div className="form-group">
                <label>Take Profit (optional):</label>
                <input
                  type="number"
                  step="0.00001"
                  value={formData.take_profit}
                  onChange={(e) => setFormData({...formData, take_profit: parseFloat(e.target.value)})}
                />
              </div>
              <div className="form-group">
                <label>Comment:</label>
                <textarea
                  value={formData.comment}
                  onChange={(e) => setFormData({...formData, comment: e.target.value})}
                  rows="3"
                />
              </div>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary">Create Signal</button>
                <button 
                  type="button" 
                  className="btn btn-secondary"
                  onClick={() => setShowCreateForm(false)}
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
              <th>Signal ID</th>
              <th>Symbol</th>
              <th>Action</th>
              <th>Volume</th>
              <th>Price</th>
              <th>Stop Loss</th>
              <th>Take Profit</th>
              <th>Status</th>
              <th>Strategy</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {signals.map(signal => (
              <tr key={signal.id}>
                <td>{signal.signal_id}</td>
                <td>{signal.symbol}</td>
                <td>
                  <span className={`signal-action ${signal.action.toLowerCase()}`}>
                    {signal.action}
                  </span>
                </td>
                <td>{signal.volume}</td>
                <td>${signal.price?.toFixed(5) || 'Market'}</td>
                <td>${signal.stop_loss?.toFixed(5) || '-'}</td>
                <td>${signal.take_profit?.toFixed(5) || '-'}</td>
                <td>
                  <span className={`status ${signal.status}`}>
                    {signal.status}
                  </span>
                </td>
                <td>{signal.strategy_name || '-'}</td>
                <td>{signal.created_at ? new Date(signal.created_at).toLocaleString() : '-'}</td>
                <td>
                  {signal.status === 'pending' && (
                    <>
                      <button 
                        className="btn btn-sm btn-success"
                        onClick={() => handleExecuteSignal(signal.id)}
                      >
                        Execute
                      </button>
                      <button 
                        className="btn btn-sm btn-warning"
                        onClick={() => handleCancelSignal(signal.id)}
                      >
                        Cancel
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {signals.length === 0 && (
          <div className="no-data">
            <p>No signals found</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Signals;