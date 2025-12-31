import React, { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Typography,
  TextField,
  Button,
  Paper,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  Grid,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Avatar,
  Divider,
} from '@mui/material'
import {
  Email as EmailIcon,
  Download as DownloadIcon,
  CheckCircle as CheckCircleIcon,
  TrendingUp as TrendingUpIcon,
  Security as SecurityIcon,
  Speed as SpeedIcon,
  Star as StarIcon,
  Send as SendIcon,
} from '@mui/icons-material'
import { useTheme } from '@mui/material/styles'

const FreeGuide = () => {
  const theme = useTheme()
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsSubmitting(true)
    setError('')

    try {
      const response = await fetch('/api/v1/funnel/lead/capture', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'funnel-api-key-2024', // This should be handled securely
        },
        body: JSON.stringify({
          email: formData.email,
          name: formData.name,
          phone: formData.phone,
          source: 'free_guide_landing',
          funnel_stage: 'free_guide',
          utm_source: new URLSearchParams(window.location.search).get('utm_source') || '',
          utm_medium: new URLSearchParams(window.location.search).get('utm_medium') || '',
          utm_campaign: new URLSearchParams(window.location.search).get('utm_campaign') || '',
        }),
      })

      const data = await response.json()

      if (data.success) {
        setSubmitted(true)
        // Trigger download
        window.open('/api/v1/funnel/guide/download', '_blank')
      } else {
        setError(data.message || 'Failed to submit. Please try again.')
      }
    } catch (err) {
      setError('Network error. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <Container maxWidth="md" sx={{ py: 8 }}>
        <Paper
          elevation={3}
          sx={{
            p: 6,
            textAlign: 'center',
            background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
            color: 'white',
          }}
        >
          <Avatar
            sx={{
              width: 80,
              height: 80,
              bgcolor: 'white',
              color: theme.palette.primary.main,
              mx: 'auto',
              mb: 3,
            }}
          >
            <CheckCircleIcon sx={{ fontSize: 48 }} />
          </Avatar>
          
          <Typography variant="h3" gutterBottom>
            Thank You!
          </Typography>
          
          <Typography variant="h6" sx={{ mb: 4, opacity: 0.9 }}>
            Your free trading guide is being downloaded. Check your email for additional resources.
          </Typography>
          
          <Button
            variant="contained"
            size="large"
            href="/apply"
            sx={{
              bgcolor: 'white',
              color: theme.palette.primary.main,
              '&:hover': {
                bgcolor: 'grey.100',
              },
            }}
          >
            Apply for Launchpad Access
          </Button>
        </Paper>
      </Container>
    )
  }

  return (
    <Box sx={{ bgcolor: 'grey.50', minHeight: '100vh' }}>
      {/* Hero Section */}
      <Box
        sx={{
          background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
          color: 'white',
          py: 8,
          textAlign: 'center',
        }}
      >
        <Container maxWidth="md">
          <Typography variant="h2" gutterBottom fontWeight="bold">
            Free Trading Guide 2024
          </Typography>
          
          <Typography variant="h5" sx={{ mb: 4, opacity: 0.9 }}>
            Discover the proven strategies used by professional traders to generate consistent returns
          </Typography>
          
          <Chip
            label="LIMITED TIME: FREE DOWNLOAD"
            color="secondary"
            size="large"
            sx={{ fontSize: '1.1rem', py: 2, px: 3 }}
          />
        </Container>
      </Box>

      <Container maxWidth="lg" sx={{ py: 8 }}>
        <Grid container spacing={4}>
          {/* Main Content */}
          <Grid item xs={12} md={8}>
            {/* What You'll Learn */}
            <Paper elevation={2} sx={{ p: 4, mb: 4 }}>
              <Typography variant="h4" gutterBottom fontWeight="bold">
                What You'll Learn Inside:
              </Typography>
              
              <List>
                {[
                  {
                    icon: <TrendingUpIcon />,
                    title: 'Market Analysis Mastery',
                    description: 'Technical and fundamental analysis techniques that work',
                  },
                  {
                    icon: <SecurityIcon />,
                    title: 'Risk Management Strategies',
                    description: 'Protect your capital while maximizing returns',
                  },
                  {
                    icon: <SpeedIcon />,
                    title: 'High-Probability Setups',
                    description: 'Entry and exit strategies with proven track records',
                  },
                  {
                    icon: <StarIcon />,
                    title: 'Trading Psychology',
                    description: 'Master the mental game of professional trading',
                  },
                ].map((item, index) => (
                  <ListItem key={index} sx={{ py: 2 }}>
                    <ListItemIcon>
                      <Avatar sx={{ bgcolor: theme.palette.primary.main }}>
                        {item.icon}
                      </Avatar>
                    </ListItemIcon>
                    <ListItemText
                      primary={item.title}
                      secondary={item.description}
                      primaryTypographyProps={{ fontWeight: 'bold' }}
                    />
                  </ListItem>
                ))}
              </List>
            </Paper>

            {/* Testimonials */}
            <Paper elevation={2} sx={{ p: 4 }}>
              <Typography variant="h4" gutterBottom fontWeight="bold">
                Success Stories
              </Typography>
              
              <Grid container spacing={3}>
                {[
                  {
                    name: 'Sarah M.',
                    result: '45% ROI in 6 months',
                    quote: 'This guide completely transformed my trading approach.',
                  },
                  {
                    name: 'John D.',
                    result: 'Consistent monthly profits',
                    quote: 'The risk management section alone is worth thousands.',
                  },
                ].map((testimonial, index) => (
                  <Grid item xs={12} md={6} key={index}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="body1" sx={{ mb: 2, fontStyle: 'italic' }}>
                          "{testimonial.quote}"
                        </Typography>
                        <Typography variant="subtitle2" fontWeight="bold">
                          {testimonial.name}
                        </Typography>
                        <Typography variant="caption" color="primary">
                          {testimonial.result}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Paper>
          </Grid>

          {/* Lead Capture Form */}
          <Grid item xs={12} md={4}>
            <Paper
              elevation={3}
              sx={{
                p: 4,
                position: 'sticky',
                top: 24,
              }}
            >
              <Typography variant="h5" gutterBottom fontWeight="bold">
                Get Your Free Guide
              </Typography>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Join 10,000+ traders who have downloaded this guide
              </Typography>

              {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  {error}
                </Alert>
              )}

              <form onSubmit={handleSubmit}>
                <TextField
                  fullWidth
                  label="Full Name"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  sx={{ mb: 2 }}
                />
                
                <TextField
                  fullWidth
                  label="Email Address"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  sx={{ mb: 2 }}
                />
                
                <TextField
                  fullWidth
                  label="Phone Number (Optional)"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  sx={{ mb: 3 }}
                />
                
                <Button
                  type="submit"
                  fullWidth
                  variant="contained"
                  size="large"
                  disabled={isSubmitting}
                  startIcon={isSubmitting ? <CircularProgress size={20} /> : <DownloadIcon />}
                  sx={{ py: 1.5 }}
                >
                  {isSubmitting ? 'Processing...' : 'Download Free Guide'}
                </Button>
              </form>

              <Divider sx={{ my: 3 }} />
              
              <Typography variant="caption" color="text.secondary">
                By downloading, you agree to receive trading tips and special offers. 
                We respect your privacy and will never share your information.
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Container>

      {/* Features Section */}
      <Box sx={{ py: 8, bgcolor: 'white' }}>
        <Container maxWidth="md">
          <Typography variant="h4" gutterBottom fontWeight="bold" textAlign="center">
            Why This Guide Is Different
          </Typography>
          
          <Grid container spacing={4} sx={{ mt: 2 }}>
            {[
              {
                title: 'No Fluff',
                description: 'Just actionable strategies you can implement today',
              },
              {
                title: 'Proven Methods',
                description: 'Strategies tested by professional traders',
              },
              {
                title: 'Beginner Friendly',
                description: 'Clear explanations with real-world examples',
              },
            ].map((feature, index) => (
              <Grid item xs={12} md={4} key={index} textAlign="center">
                <Avatar
                  sx={{
                    width: 64,
                    height: 64,
                    bgcolor: theme.palette.primary.main,
                    mx: 'auto',
                    mb: 2,
                  }}
                >
                  <CheckCircleIcon />
                </Avatar>
                <Typography variant="h6" gutterBottom fontWeight="bold">
                  {feature.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {feature.description}
                </Typography>
              </Grid>
            ))}
          </Grid>
        </Container>
      </Box>
    </Box>
  )
}

export default FreeGuide