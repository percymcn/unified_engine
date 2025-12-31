import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Tabs,
  Tab,
  CircularProgress,
  Alert,
} from '@mui/material';
import { api } from '../utils/api';
import DashboardStats from '../components/analytics/DashboardStats';
import UserSignupsChart from '../components/analytics/UserSignupsChart';
import SubscriptionDistribution from '../components/analytics/SubscriptionDistribution';
import RevenueChart from '../components/analytics/RevenueChart';
import APIUsageChart from '../components/analytics/APIUsageChart';

const Analytics = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tabValue, setTabValue] = useState(0);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [userSignups, setUserSignups] = useState([]);
  const [subscriptionDist, setSubscriptionDist] = useState([]);
  const [revenue, setRevenue] = useState([]);
  const [apiUsage, setApiUsage] = useState([]);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const [stats, signups, subs, rev, usage] = await Promise.all([
        api.get('/api/v1/analytics/dashboard'),
        api.get('/api/v1/analytics/user-signups?days=30'),
        api.get('/api/v1/analytics/subscription-distribution'),
        api.get('/api/v1/analytics/revenue?period=month&months=6'),
        api.get('/api/v1/analytics/api-usage?days=30'),
      ]);

      setDashboardStats(stats);
      setUserSignups(signups);
      setSubscriptionDist(subs);
      setRevenue(rev);
      setApiUsage(usage);
    } catch (err) {
      setError(err.message || 'Failed to load analytics');
      console.error('Analytics error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        Analytics Dashboard
      </Typography>

      <DashboardStats stats={dashboardStats} />

      <Paper sx={{ p: 3 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)} sx={{ mb: 3 }}>
          <Tab label="User Signups" />
          <Tab label="Subscriptions" />
          <Tab label="Revenue" />
          <Tab label="API Usage" />
        </Tabs>

        {tabValue === 0 && <UserSignupsChart data={userSignups} />}
        {tabValue === 1 && <SubscriptionDistribution data={subscriptionDist} />}
        {tabValue === 2 && <RevenueChart data={revenue} />}
        {tabValue === 3 && <APIUsageChart data={apiUsage} />}
      </Paper>
    </Container>
  );
};

export default Analytics;
