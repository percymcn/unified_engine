import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';

function Positions() {
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPositions();
  }, []);

  const fetchPositions = async () => {
    try {
      const response = await api.getPositions();
      setPositions(response.positions || response);
    } catch (error) {
      console.error('Failed to fetch positions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleClosePosition = async (id) => {
    if (window.confirm('Are you sure you want to close this position?')) {
      try {
        await api.closePosition(id);
        fetchPositions();
      } catch (error) {
        console.error('Failed to close position:', error);
      }
    }
  };

  if (loading) {
    return <div className="loading">Loading positions...</div>;
  }

  return (
    <div className="positions">
      <div className="page-header">
        <h1>Open Positions</h1>
        <button className="btn btn-secondary" onClick={fetchPositions}>
          Refresh
        </button>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Type</th>
              <th>Volume</th>
              <th>Open Price</th>
              <th>Current Price</th>
              <th>Stop Loss</th>
              <th>Take Profit</th>
              <th>P&L</th>
              <th>Margin</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {positions.map(position => (
              <tr key={position.id}>
                <td>{position.symbol}</td>
                <td>
                  <span className={`position-type ${position.type.toLowerCase()}`}>
                    {position.type}
                  </span>
                </td>
                <td>{position.volume}</td>
                <td>${position.open_price?.toFixed(5) || '0.00000'}</td>
                <td>${position.current_price?.toFixed(5) || '0.00000'}</td>
                <td>${position.stop_loss?.toFixed(5) || '-'}</td>
                <td>${position.take_profit?.toFixed(5) || '-'}</td>
                <td className={position.unrealized_pnl >= 0 ? 'profit' : 'loss'}>
                  ${position.unrealized_pnl?.toFixed(2) || '0.00'}
                </td>
                <td>${position.margin?.toFixed(2) || '0.00'}</td>
                <td>
                  <button 
                    className="btn btn-sm btn-danger"
                    onClick={() => handleClosePosition(position.id)}
                  >
                    Close
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {positions.length === 0 && (
          <div className="no-data">
            <p>No open positions found</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Positions;