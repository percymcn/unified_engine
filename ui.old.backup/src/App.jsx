import React, { useState, useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import {
  Box,
  CssBaseline,
  ThemeProvider,
  createTheme,
  AppBar,
  Toolbar,
  Typography,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  IconButton,
  useMediaQuery,
  useTheme,
  Avatar,
  Menu,
  MenuItem,
  Badge,
  Chip,
  LinearProgress,
} from '@mui/material'
import {
  Dashboard as DashboardIcon,
  AccountBalanceWallet as AccountIcon,
  TrendingUp as PositionsIcon,
  SwapHoriz as TradesIcon,
  Timeline as SignalsIcon,
  Webhook as WebhooksIcon,
  Settings as SettingsIcon,
  Menu as MenuIcon,
  Notifications as NotificationsIcon,
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
  Logout as LogoutIcon,
  Person as PersonIcon,
} from '@mui/icons-material'

import { useAuthStore } from './stores/authStore'
import { useWebSocket } from './services/websocket'
import Sidebar from './layout/Sidebar'
import TopBar from './layout/TopBar'

import Dashboard from './pages/Dashboard'
import Accounts from './pages/Accounts'
import Positions from './pages/Positions'
import Trades from './pages/Trades'
import Signals from './pages/Signals'
import Admin from './pages/Admin'
import Analytics from './pages/Analytics'
import Login from './auth/Login'
import FreeGuide from './pages/FreeGuide'
import Apply from './pages/Apply'
import Launchpad from './pages/Launchpad'
import PremiumOffer from './pages/PremiumOffer'
import VSL from './pages/VSL'

const drawerWidth = 240

function App() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const location = useLocation()
  
  const { user, isAuthenticated, logout } = useAuthStore()
  const { connectionStatus, notifications } = useWebSocket()

  // Create theme with mode support
  const [darkMode, setDarkMode] = useState(
    localStorage.getItem('darkMode') === 'true' || false
  )
  
  // Import premium themes
  const { lightTheme, darkTheme } = require('./theme/theme')
  const muiTheme = darkMode ? darkTheme : lightTheme
  
  // Save theme preference
  useEffect(() => {
    localStorage.setItem('darkMode', darkMode.toString())
  }, [darkMode])

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const handleLogout = () => {
    logout()
  }

  const toggleDarkMode = () => {
    setDarkMode(!darkMode)
  }

  // Protected route wrapper
  const ProtectedRoute = ({ children }) => {
    if (!isAuthenticated) {
      return <Navigate to="/login" state={{ from: location }} replace />
    }
    return children
  }

  // Public route wrapper (only accessible when not authenticated)
  const PublicRoute = ({ children }) => {
    if (isAuthenticated) {
      return <Navigate to="/dashboard" replace />
    }
    return children
  }

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
    { text: 'Analytics', icon: <SignalsIcon />, path: '/analytics', premiumOnly: true },
    { text: 'Accounts', icon: <AccountIcon />, path: '/accounts' },
    { text: 'Positions', icon: <PositionsIcon />, path: '/positions' },
    { text: 'Trades', icon: <TradesIcon />, path: '/trades' },
    { text: 'Signals', icon: <SignalsIcon />, path: '/signals' },
    { text: 'Webhooks', icon: <WebhooksIcon />, path: '/webhooks' },
    { text: 'Admin', icon: <SettingsIcon />, path: '/admin', adminOnly: true },
  ]

  const filteredMenuItems = menuItems.filter(item => {
    if (item.adminOnly && (!user || user.role !== 'admin' && user.role !== 'super_admin')) {
      return false
    }
    if (item.premiumOnly && (!user || (user.subscription_tier !== 'premium' && user.subscription_tier !== 'enterprise' && user.role !== 'admin' && user.role !== 'super_admin'))) {
      return false
    }
    return true
  })

  if (!isAuthenticated) {
    return <Login />
  }

  return (
    <ThemeProvider theme={muiTheme}>
      <Box sx={{ display: 'flex' }}>
        <CssBaseline />
        
        {/* Top Bar */}
        <AppBar
          position="fixed"
          sx={{
            width: { isMobile ? '100%' : `calc(100% - ${drawerWidth}px)`},
            ml: isMobile ? 0 : drawerWidth,
            transition: theme.transitions.create(['margin', 'width'], {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.leavingScreen,
            }),
          }}
        >
          <Toolbar>
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: 2, display: { isMobile ? 'flex' : 'none' } }}
            >
              <MenuIcon />
            </IconButton>
            
            <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
              Unified Trading Engine
            </Typography>
            
            {/* Connection Status */}
            <Box sx={{ display: 'flex', alignItems: 'center', mr: 2 }}>
              <Chip
                label={connectionStatus}
                color={connectionStatus === 'connected' ? 'success' : 'error'}
                size="small"
                sx={{ mr: 1 }}
              />
              
              {/* Notifications */}
              <IconButton color="inherit">
                <Badge badgeContent={notifications.length} color="error">
                  <NotificationsIcon />
                </Badge>
              </IconButton>
              
              {/* Dark Mode Toggle */}
              <IconButton color="inherit" onClick={toggleDarkMode}>
                {darkMode ? <LightModeIcon /> : <DarkModeIcon />}
              </IconButton>
              
              {/* User Menu */}
              <IconButton color="inherit">
                <Avatar sx={{ width: 32, height: 32 }}>
                  {user?.username?.charAt(0)?.toUpperCase() || <PersonIcon />}
                </Avatar>
              </IconButton>
            </Box>
          </Toolbar>
        </AppBar>

        {/* Sidebar */}
        <Box
          component="nav"
          sx={{
            width: { isMobile ? 0 : drawerWidth },
            flexShrink: { isMobile ? 0 : 0 },
          }}
        >
          <Drawer
            variant={isMobile ? 'temporary' : 'persistent'}
            open={isMobile ? mobileOpen : true}
            onClose={handleDrawerToggle}
            ModalProps={{
              keepMounted: true,
            }}
            sx={{
              display: { isMobile ? 'block' : 'none' },
              '& .MuiDrawer-paper': {
                boxSizing: 'border-box',
                width: drawerWidth,
              },
            }}
          >
            <Toolbar />
            <List>
              {filteredMenuItems.map((item) => (
                <ListItem
                  button
                  key={item.text}
                  component="a"
                  href={item.path}
                  onClick={(e) => {
                    e.preventDefault()
                    window.location.hash = item.path
                  }}
                  sx={{
                    '&.active': {
                      backgroundColor: 'primary.main',
                      color: 'primary.contrastText',
                    },
                  }}
                >
                  <ListItemIcon>
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItem>
              ))}
            </List>
            
            <Box sx={{ flexGrow: 1 }} />
            
            <List>
              <ListItem button onClick={handleLogout}>
                <ListItemIcon>
                  <LogoutIcon />
                </ListItemIcon>
                <ListItemText primary="Logout" />
              </ListItem>
            </List>
          </Drawer>
        </Box>

        {/* Main Content */}
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: 3,
            width: { isMobile ? '100%' : `calc(100% - ${drawerWidth}px)`,
            mt: '64px',
            transition: theme.transitions.create(['margin', 'width'], {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.leavingScreen,
            }),
          }}
        >
          <Routes>
            <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
            <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/accounts" element={<ProtectedRoute><Accounts /></ProtectedRoute>} />
            <Route path="/positions" element={<ProtectedRoute><Positions /></ProtectedRoute>} />
            <Route path="/trades" element={<ProtectedRoute><Trades /></ProtectedRoute>} />
            <Route path="/signals" element={<ProtectedRoute><Signals /></ProtectedRoute>} />
            <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
            <Route path="/webhooks" element={<ProtectedRoute><Admin /></ProtectedRoute>} />
            <Route path="/admin" element={<ProtectedRoute><Admin /></ProtectedRoute>} />
            {/* Funnel Routes - Public */}
            <Route path="/free-guide" element={<FreeGuide />} />
            <Route path="/apply" element={<Apply />} />
            <Route path="/vsl" element={<VSL />} />
            <Route path="/premium-offer" element={<PremiumOffer />} />
            {/* Funnel Routes - Protected */}
            <Route path="/launchpad" element={<ProtectedRoute><Launchpad /></ProtectedRoute>} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Box>
      </Box>
    </ThemeProvider>
  )
}

export default App