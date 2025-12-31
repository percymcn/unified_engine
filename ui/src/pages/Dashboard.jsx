import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';

function Dashboard() {
  const [data, setData] = useState({
    accounts: [],
    positions: [],
    trades: [],
    signals: [],
    metrics: {}
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [accounts, positions, trades, signals, metrics] = await Promise.all([
        api.get('/api/v1/accounts'),
        api.get('/api/v1/positions'),
        api.get('/api/v1/trades'),
        api.get('/api/v1/signals'),
        api.get('/metrics')
      ]);

      setData({
        accounts: accounts.data || [],
        positions: positions.data || [],
        trades: trades.data || [],
        signals: signals.data || [],
        metrics: metrics.data || {}
      });
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading dashboard...</div>;
  }

  return (
    <div className="dashboard">
      <h1>Trading Dashboard</h1>
      
      <div className="metrics-grid">
        <div className="metric-card">
          <h3>Total Accounts</h3>
          <span>{data.accounts.length}</span>
        </div>
        <div className="metric-card">
          <h3>Open Positions</h3>
          <span>{data.positions.length}</span>
        </div>
        <div className="metric-card">
          <h3>Total Trades</h3>
          <span>{data.trades.length}</span>
        </div>
        <div className="metric-card">
          <h3>Active Signals</h3>
          <span>{data.signals.filter(s => s.status === 'active').length}</span>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="dashboard-section">
          <h2>Recent Accounts</h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Account ID</th>
                  <th>Broker</th>
                  <th>Balance</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.accounts.slice(0, 5).map(account => (
                  <tr key={account.id}>
                    <td>{account.account_id}</td>
                    <td>{account.broker}</td>
                    <td>${account.balance?.toFixed(2) || '0.00'}</td>
                    <td>{account.is_active ? 'Active' : 'Inactive'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="dashboard-section">
          <h2>Open Positions</h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Type</th>
                  <th>Volume</th>
                  <th>P&L</th>
                </tr>
              </thead>
              <tbody>
                {data.positions.slice(0, 5).map(position => (
                  <tr key={position.id}>
                    <td>{position.symbol}</td>
                    <td>{position.type}</td>
                    <td>{position.volume}</td>
                    <td className={position.unrealized_pnl >= 0 ? 'profit' : 'loss'}>
                      ${position.unrealized_pnl?.toFixed(2) || '0.00'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;