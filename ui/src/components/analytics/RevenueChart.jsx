import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, Typography, Box } from '@mui/material';

const RevenueChart = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography>No data available</Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Revenue Over Time
        </Typography>
        <Box sx={{ width: '100%', height: 300, mt: 2 }}>
          <ResponsiveContainer>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="revenue" fill="#8884d8" name="Revenue ($)" />
              <Bar dataKey="subscriptions" fill="#82ca9d" name="Subscriptions" />
            </BarChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
};

export default RevenueChart;
