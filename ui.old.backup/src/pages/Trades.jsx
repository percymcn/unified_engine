import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';

function Trades() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchTrades();
  }, []);

  const fetchTrades = async () => {
    try {
      const response = await api.getTrades();
      setTrades(response.trades || response);
    } catch (error) {
      console.error('Failed to fetch trades:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredTrades = trades.filter(trade => {
    if (filter === 'all') return true;
    if (filter === 'open') return trade.status === 'open';
    if (filter === 'closed') return trade.status === 'closed';
    return true;
  });

  if (loading) {
    return <div className="loading">Loading trades...</div>;
  }

  return (
    <div className="trades">
      <div className="page-header">
        <h1>Trade History</h1>
        <div className="filters">
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">All Trades</option>
            <option value="open">Open Trades</option>
            <option value="closed">Closed Trades</option>
          </select>
          <button className="btn btn-secondary" onClick={fetchTrades}>
            Refresh
          </button>
        </div>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Trade ID</th>
              <th>Symbol</th>
              <th>Type</th>
              <th>Volume</th>
              <th>Open Price</th>
              <th>Close Price</th>
              <th>Stop Loss</th>
              <th>Take Profit</th>
              <th>Profit</th>
              <th>Status</th>
              <th>Open Time</th>
              <th>Close Time</th>
            </tr>
          </thead>
          <tbody>
            {filteredTrades.map(trade => (
              <tr key={trade.id}>
                <td>{trade.trade_id}</td>
                <td>{trade.symbol}</td>
                <td>
                  <span className={`trade-type ${trade.type.toLowerCase()}`}>
                    {trade.type}
                  </span>
                </td>
                <td>{trade.volume}</td>
                <td>${trade.open_price?.toFixed(5) || '0.00000'}</td>
                <td>${trade.close_price?.toFixed(5) || '-'}</td>
                <td>${trade.stop_loss?.toFixed(5) || '-'}</td>
                <td>${trade.take_profit?.toFixed(5) || '-'}</td>
                <td className={trade.profit >= 0 ? 'profit' : 'loss'}>
                  ${trade.profit?.toFixed(2) || '0.00'}
                </td>
                <td>
                  <span className={`status ${trade.status}`}>
                    {trade.status}
                  </span>
                </td>
                <td>{trade.open_time ? new Date(trade.open_time).toLocaleString() : '-'}</td>
                <td>{trade.close_time ? new Date(trade.close_time).toLocaleString() : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredTrades.length === 0 && (
          <div className="no-data">
            <p>No trades found</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Trades;