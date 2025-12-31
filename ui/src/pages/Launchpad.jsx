import React, { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  Chip,
  LinearProgress,
  Avatar,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material'
import {
  School as SchoolIcon,
  TrendingUp as TrendingUpIcon,
  Timeline as TimelineIcon,
  Assessment as AssessmentIcon,
  PlayArrow as PlayArrowIcon,
  CheckCircle as CheckCircleIcon,
  Lock as LockIcon,
  Star as StarIcon,
  CalendarToday as CalendarIcon,
  AccessTime as AccessTimeIcon,
  Group as GroupIcon,
} from '@mui/icons-material'
import { useTheme } from '@mui/material/styles'

const Launchpad = () => {
  const theme = useTheme()
  const [userAccess, setUserAccess] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedModule, setSelectedModule] = useState(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  useEffect(() => {
    // Check user access level
    const checkAccess = async () => {
      try {
        const response = await fetch('/api/v1/funnel/launchpad/status', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
        })
        const data = await response.json()
        setUserAccess(data)
      } catch (error) {
        console.error('Error checking access:', error)
      } finally {
        setLoading(false)
      }
    }
    
    checkAccess()
  }, [])

  const modules = [
    {
      id: 'foundations',
      title: 'Trading Foundations',
      description: 'Master the basics of market analysis and trading psychology',
      duration: '2 weeks',
      level: 'Beginner',
      lessons: 12,
      icon: <SchoolIcon />,
      progress: userAccess?.progress?.foundations || 0,
      locked: false,
    },
    {
      id: 'technical-analysis',
      title: 'Advanced Technical Analysis',
      description: 'Deep dive into chart patterns, indicators, and trading strategies',
      duration: '3 weeks',
      level: 'Intermediate',
      lessons: 18,
      icon: <TimelineIcon />,
      progress: userAccess?.progress?.technical_analysis || 0,
      locked: userAccess?.access_level !== 'premium',
    },
    {
      id: 'risk-management',
      title: 'Risk Management Mastery',
      description: 'Learn professional risk management and position sizing techniques',
      duration: '2 weeks',
      level: 'Intermediate',
      lessons: 10,
      icon: <AssessmentIcon />,
      progress: userAccess?.progress?.risk_management || 0,
      locked: false,
    },
    {
      id: 'live-trading',
      title: 'Live Trading Sessions',
      description: 'Join live trading sessions with professional traders',
      duration: 'Ongoing',
      level: 'Advanced',
      lessons: 0,
      icon: <TrendingUpIcon />,
      progress: userAccess?.progress?.live_trading || 0,
      locked: userAccess?.access_level !== 'premium',
    },
  ]

  const upcomingEvents = [
    {
      title: 'Live Market Analysis',
      date: '2025-12-07',
      time: '2:00 PM EST',
      type: 'webinar',
    },
    {
      title: 'Q&A with Senior Trader',
      date: '2025-12-09',
      time: '4:00 PM EST',
      type: 'qa',
    },
    {
      title: 'Strategy Deep Dive: Scalping',
      date: '2025-12-11',
      time: '3:00 PM EST',
      type: 'workshop',
    },
  ]

  const handleModuleClick = (module) => {
    if (module.locked) {
      setSelectedModule(module)
      setDialogOpen(true)
    } else {
      // Navigate to module
      window.location.href = `/launchpad/module/${module.id}`
    }
  }

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 8 }}>
        <LinearProgress />
        <Typography variant="h6" sx={{ mt: 2, textAlign: 'center' }}>
          Loading your Launchpad...
        </Typography>
      </Container>
    )
  }

  if (!userAccess) {
    return (
      <Container maxWidth="md" sx={{ py: 8 }}>
        <Alert severity="warning">
          You don't have access to Launchpad yet. 
          <Button href="/apply" sx={{ ml: 2 }}>
            Apply Now
          </Button>
        </Alert>
      </Container>
    )
  }

  return (
    <Container maxWidth="lg" sx={{ py: 8 }}>
      {/* Welcome Header */}
      <Box sx={{ mb: 6, textAlign: 'center' }}>
        <Typography variant="h3" gutterBottom fontWeight="bold">
          Welcome to Launchpad
        </Typography>
        
        <Typography variant="h6" color="text.secondary" sx={{ mb: 3 }}>
          Your personalized trading education journey starts here
        </Typography>
        
        <Chip
          label={`${userAccess.access_level === 'premium' ? 'Premium' : 'Basic'} Access`}
          color={userAccess.access_level === 'premium' ? 'primary' : 'default'}
          size="large"
        />
      </Box>

      {/* Progress Overview */}
      <Card sx={{ mb: 6, bgcolor: theme.palette.primary.main, color: 'white' }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" gutterBottom>
            Your Progress
          </Typography>
          
          <Grid container spacing={4}>
            <Grid item xs={12} md={3}>
              <Box textAlign="center">
                <Typography variant="h3">
                  {userAccess.total_progress || 0}%
                </Typography>
                <Typography variant="body2">
                  Overall Progress
                </Typography>
              </Box>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Box textAlign="center">
                <Typography variant="h3">
                  {userAccess.modules_completed || 0}
                </Typography>
                <Typography variant="body2">
                  Modules Completed
                </Typography>
              </Box>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Box textAlign="center">
                <Typography variant="h3">
                  {userAccess.lessons_completed || 0}
                </Typography>
                <Typography variant="body2">
                  Lessons Completed
                </Typography>
              </Box>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Box textAlign="center">
                <Typography variant="h3">
                  {userAccess.streak_days || 0}
                </Typography>
                <Typography variant="body2">
                  Day Streak
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Grid container spacing={4}>
        {/* Learning Modules */}
        <Grid item xs={12} lg={8}>
          <Typography variant="h4" gutterBottom fontWeight="bold">
            Learning Modules
          </Typography>
          
          <Grid container spacing={3}>
            {modules.map((module) => (
              <Grid item xs={12} md={6} key={module.id}>
                <Card
                  sx={{
                    height: '100%',
                    cursor: module.locked ? 'not-allowed' : 'pointer',
                    opacity: module.locked ? 0.7 : 1,
                    transition: 'transform 0.2s',
                    '&:hover': {
                      transform: module.locked ? 'none' : 'translateY(-4px)',
                    },
                  }}
                  onClick={() => handleModuleClick(module)}
                >
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <Avatar sx={{ bgcolor: theme.palette.primary.main, mr: 2 }}>
                        {module.icon}
                      </Avatar>
                      <Box sx={{ flexGrow: 1 }}>
                        <Typography variant="h6" fontWeight="bold">
                          {module.title}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {module.level} • {module.duration}
                        </Typography>
                      </Box>
                      {module.locked && <LockIcon color="action" />}
                    </Box>
                    
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {module.description}
                    </Typography>
                    
                    {module.lessons > 0 && (
                      <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
                        {module.lessons} lessons
                      </Typography>
                    )}
                    
                    <Box sx={{ mt: 2 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="caption">
                          Progress
                        </Typography>
                        <Typography variant="caption">
                          {module.progress}%
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={module.progress}
                        sx={{
                          height: 8,
                          borderRadius: 4,
                          bgcolor: 'grey.200',
                        }}
                      />
                    </Box>
                    
                    <Button
                      variant="contained"
                      fullWidth
                      sx={{ mt: 2 }}
                      disabled={module.locked}
                      startIcon={module.locked ? <LockIcon /> : <PlayArrowIcon />}
                    >
                      {module.locked ? 'Upgrade to Premium' : 'Continue Learning'}
                    </Button>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} lg={4}>
          {/* Upcoming Events */}
          <Card sx={{ mb: 4 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom fontWeight="bold">
                Upcoming Events
              </Typography>
              
              <List>
                {upcomingEvents.map((event, index) => (
                  <React.Fragment key={index}>
                    <ListItem>
                      <ListItemIcon>
                        <CalendarIcon color="primary" />
                      </ListItemIcon>
                      <ListItemText
                        primary={event.title}
                        secondary={`${event.date} • ${event.time}`}
                      />
                    </ListItem>
                    {index < upcomingEvents.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            </CardContent>
          </Card>

          {/* Community Stats */}
          <Card sx={{ mb: 4 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom fontWeight="bold">
                Community
              </Typography>
              
              <Box sx={{ textAlign: 'center', mb: 2 }}>
                <GroupIcon sx={{ fontSize: 48, color: theme.palette.primary.main, mb: 1 }} />
                <Typography variant="h4">
                  1,247
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Active Students
                </Typography>
              </Box>
              
              <Button variant="outlined" fullWidth>
                Join Community
              </Button>
            </CardContent>
          </Card>

          {/* Upgrade CTA */}
          {userAccess.access_level !== 'premium' && (
            <Card sx={{ bgcolor: theme.palette.secondary.main, color: 'white' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <StarIcon sx={{ fontSize: 48, mb: 2 }} />
                
                <Typography variant="h6" gutterBottom fontWeight="bold">
                  Upgrade to Premium
                </Typography>
                
                <Typography variant="body2" sx={{ mb: 3 }}>
                  Unlock all modules, live trading sessions, and personalized coaching
                </Typography>
                
                <Button
                  variant="contained"
                  href="/premium-offer"
                  sx={{
                    bgcolor: 'white',
                    color: theme.palette.secondary.main,
                    '&:hover': {
                      bgcolor: 'grey.100',
                    },
                  }}
                >
                  Upgrade Now
                </Button>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>

      {/* Upgrade Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>
          Upgrade to Premium Access
        </DialogTitle>
        <DialogContent>
          <Typography>
            This module is only available to Premium members. Upgrade your account to access:
          </Typography>
          <List sx={{ mt: 2 }}>
            <ListItem>
              <ListItemIcon>
                <CheckCircleIcon color="primary" />
              </ListItemIcon>
              <ListItemText primary="All learning modules" />
            </ListItem>
            <ListItem>
              <ListItemIcon>
                <CheckCircleIcon color="primary" />
              </ListItemIcon>
              <ListItemText primary="Live trading sessions" />
            </ListItem>
            <ListItem>
              <ListItemIcon>
                <CheckCircleIcon color="primary" />
              </ListItemIcon>
              <ListItemText primary="Personalized coaching" />
            </ListItem>
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>
            Maybe Later
          </Button>
          <Button
            variant="contained"
            href="/premium-offer"
            onClick={() => setDialogOpen(false)}
          >
            Upgrade Now
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}

export default Launchpad