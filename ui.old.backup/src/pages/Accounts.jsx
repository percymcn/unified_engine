import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';

function Accounts() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({
    account_id: '',
    broker: 'mt4',
    account_type: 'demo',
    currency: 'USD'
  });

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const response = await api.getAccounts();
      setAccounts(response.accounts || response);
    } catch (error) {
      console.error('Failed to fetch accounts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAccount = async (e) => {
    e.preventDefault();
    try {
      await api.createAccount(formData);
      setShowCreateForm(false);
      setFormData({
        account_id: '',
        broker: 'mt4',
        account_type: 'demo',
        currency: 'USD'
      });
      fetchAccounts();
    } catch (error) {
      console.error('Failed to create account:', error);
    }
  };

  const handleDeleteAccount = async (id) => {
    if (window.confirm('Are you sure you want to delete this account?')) {
      try {
        await api.deleteAccount(id);
        fetchAccounts();
      } catch (error) {
        console.error('Failed to delete account:', error);
      }
    }
  };

  const handleSyncAccount = async (id) => {
    try {
      await api.put(`/api/v1/accounts/${id}/sync`);
      fetchAccounts();
    } catch (error) {
      console.error('Failed to sync account:', error);
    }
  };

  if (loading) {
    return <div className="loading">Loading accounts...</div>;
  }

  return (
    <div className="accounts">
      <div className="page-header">
        <h1>Trading Accounts</h1>
        <button 
          className="btn btn-primary"
          onClick={() => setShowCreateForm(true)}
        >
          Add Account
        </button>
      </div>

      {showCreateForm && (
        <div className="modal">
          <div className="modal-content">
            <h2>Create New Account</h2>
            <form onSubmit={handleCreateAccount}>
              <div className="form-group">
                <label>Account ID:</label>
                <input
                  type="text"
                  value={formData.account_id}
                  onChange={(e) => setFormData({...formData, account_id: e.target.value})}
                  required
                />
              </div>
              <div className="form-group">
                <label>Broker:</label>
                <select
                  value={formData.broker}
                  onChange={(e) => setFormData({...formData, broker: e.target.value})}
                >
                  <option value="mt4">MT4</option>
                  <option value="mt5">MT5</option>
                  <option value="tradelocker">TradeLocker</option>
                  <option value="tradovate">Tradovate</option>
                  <option value="projectx">ProjectX</option>
                </select>
              </div>
              <div className="form-group">
                <label>Account Type:</label>
                <select
                  value={formData.account_type}
                  onChange={(e) => setFormData({...formData, account_type: e.target.value})}
                >
                  <option value="demo">Demo</option>
                  <option value="live">Live</option>
                  <option value="evaluation">Evaluation</option>
                </select>
              </div>
              <div className="form-group">
                <label>Currency:</label>
                <select
                  value={formData.currency}
                  onChange={(e) => setFormData({...formData, currency: e.target.value})}
                >
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="GBP">GBP</option>
                </select>
              </div>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary">Create</button>
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
              <th>Account ID</th>
              <th>Broker</th>
              <th>Type</th>
              <th>Currency</th>
              <th>Balance</th>
              <th>Equity</th>
              <th>Status</th>
              <th>Connected</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map(account => (
              <tr key={account.id}>
                <td>{account.account_id}</td>
                <td>{account.broker}</td>
                <td>{account.account_type}</td>
                <td>{account.currency}</td>
                <td>${account.balance?.toFixed(2) || '0.00'}</td>
                <td>${account.equity?.toFixed(2) || '0.00'}</td>
                <td>
                  <span className={`status ${account.is_active ? 'active' : 'inactive'}`}>
                    {account.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>
                  <span className={`status ${account.is_connected ? 'connected' : 'disconnected'}`}>
                    {account.is_connected ? 'Connected' : 'Disconnected'}
                  </span>
                </td>
                <td>
                  <button 
                    className="btn btn-sm btn-secondary"
                    onClick={() => handleSyncAccount(account.id)}
                  >
                    Sync
                  </button>
                  <button 
                    className="btn btn-sm btn-danger"
                    onClick={() => handleDeleteAccount(account.id)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Accounts;