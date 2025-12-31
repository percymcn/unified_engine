import React from 'react';
import { Box, Grid, Card, CardContent, Typography } from '@mui/material';
import {
  TrendingUp,
  People,
  Business,
  AttachMoney,
  Api,
  Timeline,
} from '@mui/icons-material';

const StatCard = ({ title, value, icon: Icon, color = 'primary' }) => (
  <Card sx={{ height: '100%', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
    <CardContent>
      <Box display="flex" justifyContent="space-between" alignItems="center">
        <Box>
          <Typography color="textSecondary" gutterBottom variant="body2">
            {title}
          </Typography>
          <Typography variant="h4" component="div" sx={{ fontWeight: 'bold', color: 'white' }}>
            {value}
          </Typography>
        </Box>
        <Icon sx={{ fontSize: 48, opacity: 0.3, color: 'white' }} />
      </Box>
    </CardContent>
  </Card>
);

const DashboardStats = ({ stats }) => {
  if (!stats) return null;

  const statCards = [
    {
      title: 'Total Users',
      value: stats.total_users?.toLocaleString() || '0',
      icon: People,
      color: 'primary',
    },
    {
      title: 'Active Users',
      value: stats.active_users?.toLocaleString() || '0',
      icon: TrendingUp,
      color: 'success',
    },
    {
      title: 'Organizations',
      value: stats.total_organizations?.toLocaleString() || '0',
      icon: Business,
      color: 'info',
    },
    {
      title: 'Revenue (This Month)',
      value: `$${stats.revenue_this_month?.toFixed(2) || '0.00'}`,
      icon: AttachMoney,
      color: 'warning',
    },
    {
      title: 'API Calls (Today)',
      value: stats.api_calls_today?.toLocaleString() || '0',
      icon: Api,
      color: 'secondary',
    },
    {
      title: 'Signals (Today)',
      value: stats.signals_today?.toLocaleString() || '0',
      icon: Timeline,
      color: 'error',
    },
  ];

  return (
    <Grid container spacing={3} sx={{ mb: 3 }}>
      {statCards.map((stat, index) => (
        <Grid item xs={12} sm={6} md={4} key={index}>
          <StatCard {...stat} />
        </Grid>
      ))}
    </Grid>
  );
};

export default DashboardStats;
