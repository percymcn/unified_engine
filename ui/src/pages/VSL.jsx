import React, { useState, useEffect, useRef } from 'react'
import {
  Box,
  Container,
  Typography,
  Button,
  Paper,
  Avatar,
  Chip,
  LinearProgress,
  Card,
  CardContent,
  Grid,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
} from '@mui/material'
import {
  PlayArrow as PlayArrowIcon,
  Pause as PauseIcon,
  VolumeUp as VolumeUpIcon,
  VolumeOff as VolumeOffIcon,
  CheckCircle as CheckCircleIcon,
  TrendingUp as TrendingUpIcon,
  AccessTime as AccessTimeIcon,
  People as PeopleIcon,
  Star as StarIcon,
  Email as EmailIcon,
  Send as SendIcon,
} from '@mui/icons-material'
import { useTheme } from '@mui/material/styles'

const VSL = () => {
  const theme = useTheme()
  const videoRef = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [watchTime, setWatchTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [showEmailCapture, setShowEmailCapture] = useState(false)
  const [leadId, setLeadId] = useState('')
  const [emailSubmitted, setEmailSubmitted] = useState(false)
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const videoData = {
    title: 'The Trading Secret That Changed Everything',
    duration: '18:42',
    thumbnail: '/api/v1/funnel/vsl/thumbnail.jpg',
    videoUrl: '/api/v1/funnel/vsl/video.mp4',
  }

  const milestones = [
    { time: 300, title: 'The Problem with Traditional Trading' },
    { time: 600, title: 'Professional Risk Management Revealed' },
    { time: 900, title: 'The 3-Step Profit System' },
    { time: 1122, title: 'Your Path to Financial Freedom' },
  ]

  const testimonials = [
    {
      name: 'Robert T.',
      result: '78% ROI in 6 months',
      quote: 'This system completely changed how I approach trading.',
      avatar: 'RT',
    },
    {
      name: 'Amanda K.',
      result: 'Quit her job in 4 months',
      quote: 'Finally found a strategy that actually works consistently.',
      avatar: 'AK',
    },
  ]

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const updateTime = () => {
      setWatchTime(Math.floor(video.currentTime))
    }

    const updateDuration = () => {
      setDuration(Math.floor(video.duration))
    }

    const handleEnded = () => {
      setIsPlaying(false)
      setShowEmailCapture(true)
      trackVSLProgress(true)
    }

    video.addEventListener('timeupdate', updateTime)
    video.addEventListener('loadedmetadata', updateDuration)
    video.addEventListener('ended', handleEnded)

    return () => {
      video.removeEventListener('timeupdate', updateTime)
      video.removeEventListener('loadedmetadata', updateDuration)
      video.removeEventListener('ended', handleEnded)
    }
  }, [])

  useEffect(() => {
    // Track progress at milestones
    const currentMilestone = milestones.find(m => Math.abs(watchTime - m.time) < 5)
    if (currentMilestone) {
      trackVSLProgress(false, currentMilestone.title)
    }
  }, [watchTime])

  const trackVSLProgress = async (completed = false, milestone = '') => {
    try {
      await fetch('/api/v1/funnel/vsl/track', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'funnel-api-key-2024',
        },
        body: JSON.stringify({
          lead_id: leadId || 'anonymous',
          video_id: 'main-vsl',
          watch_time_seconds: watchTime,
          completed: completed,
          timestamp: new Date().toISOString(),
          milestone: milestone,
        }),
      })
    } catch (error) {
      console.error('Error tracking VSL progress:', error)
    }
  }

  const handlePlayPause = () => {
    const video = videoRef.current
    if (isPlaying) {
      video.pause()
    } else {
      video.play()
    }
    setIsPlaying(!isPlaying)
  }

  const handleMuteToggle = () => {
    const video = videoRef.current
    video.muted = !isMuted
    setIsMuted(!isMuted)
  }

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const handleEmailSubmit = async () => {
    if (!email) return

    setSubmitting(true)

    try {
      // First capture the lead
      const leadResponse = await fetch('/api/v1/funnel/lead/capture', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'funnel-api-key-2024',
        },
        body: JSON.stringify({
          email: email,
          source: 'vsl_page',
          funnel_stage: 'vsl_watcher',
        }),
      })

      const leadData = await leadResponse.json()
      
      if (leadData.success) {
        setLeadId(leadData.lead_id)
        setEmailSubmitted(true)
        
        // Track that they watched the VSL
        await trackVSLProgress(false)
      }
    } catch (error) {
      console.error('Error submitting email:', error)
    } finally {
      setSubmitting(false)
    }
  }

  const progress = duration > 0 ? (watchTime / duration) * 100 : 0

  return (
    <Box sx={{ bgcolor: 'black', color: 'white', minHeight: '100vh' }}>
      <Container maxWidth="lg">
        {/* Video Section */}
        <Box sx={{ py: 4 }}>
          <Typography variant="h3" gutterBottom fontWeight="bold" textAlign="center">
            {videoData.title}
          </Typography>
          
          <Typography variant="h6" color="text.secondary" textAlign="center" sx={{ mb: 4 }}>
            Watch this free presentation before it's taken down
          </Typography>

          {/* Video Player */}
          <Paper
            elevation={8}
            sx={{
              position: 'relative',
              bgcolor: 'black',
              borderRadius: 2,
              overflow: 'hidden',
              maxWidth: 900,
              mx: 'auto',
            }}
          >
            {/* Video Element */}
            <video
              ref={videoRef}
              style={{
                width: '100%',
                height: 'auto',
                display: 'block',
              }}
              poster={videoData.thumbnail}
            >
              <source src={videoData.videoUrl} type="video/mp4" />
              Your browser does not support the video tag.
            </video>

            {/* Custom Controls Overlay */}
            <Box
              sx={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                right: 0,
                bggradient: 'linear-gradient(to top, rgba(0,0,0,0.8), transparent)',
                p: 2,
              }}
            >
              {/* Progress Bar */}
              <Box sx={{ mb: 2 }}>
                <LinearProgress
                  variant="determinate"
                  value={progress}
                  sx={{
                    height: 6,
                    borderRadius: 3,
                    bgcolor: 'rgba(255,255,255,0.3)',
                  }}
                />
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                  <Typography variant="caption">
                    {formatTime(watchTime)}
                  </Typography>
                  <Typography variant="caption">
                    {formatTime(duration)}
                  </Typography>
                </Box>
              </Box>

              {/* Control Buttons */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Button
                  variant="contained"
                  onClick={handlePlayPause}
                  startIcon={isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
                  sx={{
                    bgcolor: 'rgba(255,255,255,0.2)',
                    '&:hover': {
                      bgcolor: 'rgba(255,255,255,0.3)',
                    },
                  }}
                >
                  {isPlaying ? 'Pause' : 'Play'}
                </Button>

                <Button
                  variant="contained"
                  onClick={handleMuteToggle}
                  startIcon={isMuted ? <VolumeOffIcon /> : <VolumeUpIcon />}
                  sx={{
                    bgcolor: 'rgba(255,255,255,0.2)',
                    '&:hover': {
                      bgcolor: 'rgba(255,255,255,0.3)',
                    },
                  }}
                >
                  {isMuted ? 'Unmute' : 'Mute'}
                </Button>

                <Box sx={{ flexGrow: 1 }} />

                <Chip
                  label={`${videoData.duration} duration`}
                  variant="outlined"
                  size="small"
                  sx={{ borderColor: 'rgba(255,255,255,0.5)', color: 'white' }}
                />
              </Box>
            </Box>

            {/* Email Capture Overlay (shows at strategic times) */}
            {!emailSubmitted && showEmailCapture && (
              <Box
                sx={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  bgcolor: 'rgba(0,0,0,0.9)',
                  p: 4,
                  borderRadius: 2,
                  textAlign: 'center',
                  maxWidth: 400,
                }}
              >
                <Typography variant="h6" gutterBottom>
                  Don't Miss This Opportunity
                </Typography>
                
                <Typography variant="body2" sx={{ mb: 3 }}>
                  Enter your email to get exclusive access to our trading system
                </Typography>

                <TextField
                  fullWidth
                  label="Email Address"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  sx={{ 
                    bgcolor: 'white',
                    borderRadius: 1,
                    mb: 2,
                    '& .MuiOutlinedInput-root': {
                      color: 'black',
                    },
                  }}
                />

                <Button
                  variant="contained"
                  fullWidth
                  onClick={handleEmailSubmit}
                  disabled={submitting || !email}
                  startIcon={submitting ? <CircularProgress size={20} /> : <SendIcon />}
                  sx={{ mb: 2 }}
                >
                  {submitting ? 'Submitting...' : 'Get Instant Access'}
                </Button>

                <Button
                  variant="text"
                  onClick={() => setShowEmailCapture(false)}
                  sx={{ color: 'white' }}
                >
                  Continue watching
                </Button>
              </Box>
            )}
          </Paper>

          {/* Video Milestones */}
          <Box sx={{ mt: 4, maxWidth: 900, mx: 'auto' }}>
            <Typography variant="h6" gutterBottom>
              What You'll Discover:
            </Typography>
            
            <Grid container spacing={2}>
              {milestones.map((milestone, index) => (
                <Grid item xs={12} sm={6} key={index}>
                  <Card variant="outlined" sx={{ bgcolor: 'rgba(255,255,255,0.05)' }}>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <AccessTimeIcon sx={{ mr: 1, color: theme.palette.primary.main }} />
                        <Typography variant="caption">
                          {formatTime(milestone.time)}
                        </Typography>
                      </Box>
                      <Typography variant="body2">
                        {milestone.title}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>
        </Box>

        {/* Social Proof Section */}
        <Box sx={{ py: 6, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
          <Grid container spacing={4} alignItems="center">
            <Grid item xs={12} md={6}>
              <Typography variant="h4" gutterBottom fontWeight="bold">
                Join Thousands of Successful Traders
              </Typography>
              
              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <PeopleIcon sx={{ mr: 2, color: theme.palette.primary.main }} />
                  <Typography variant="h6">
                    12,847+
                  </Typography>
                  <Typography variant="body2" sx={{ ml: 1 }}>
                    Active Students
                  </Typography>
                </Box>
                
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <TrendingUpIcon sx={{ mr: 2, color: theme.palette.success.main }} />
                  <Typography variant="h6">
                    94%
                  </Typography>
                  <Typography variant="body2" sx={{ ml: 1 }}>
                    Success Rate
                  </Typography>
                </Box>
                
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <StarIcon sx={{ mr: 2, color: theme.palette.warning.main }} />
                  <Typography variant="h6">
                    4.9/5
                  </Typography>
                  <Typography variant="body2" sx={{ ml: 1 }}>
                    Average Rating
                  </Typography>
                </Box>
              </Box>
            </Grid>

            <Grid item xs={12} md={6}>
              {testimonials.map((testimonial, index) => (
                <Card key={index} variant="outlined" sx={{ mb: 2, bgcolor: 'rgba(255,255,255,0.05)' }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <Avatar sx={{ bgcolor: theme.palette.primary.main, mr: 2, fontSize: 14 }}>
                        {testimonial.avatar}
                      </Avatar>
                      <Box>
                        <Typography variant="subtitle2">
                          {testimonial.name}
                        </Typography>
                        <Typography variant="caption" color="primary">
                          {testimonial.result}
                        </Typography>
                      </Box>
                    </Box>
                    <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                      "{testimonial.quote}"
                    </Typography>
                  </CardContent>
                </Card>
              ))}
            </Grid>
          </Grid>
        </Box>

        {/* Final CTA */}
        <Box sx={{ py: 6, textAlign: 'center' }}>
          <Typography variant="h4" gutterBottom fontWeight="bold">
            Ready to Transform Your Trading?
          </Typography>
          
          <Typography variant="h6" color="text.secondary" sx={{ mb: 4 }}>
            Get started today with our proven trading system
          </Typography>

          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Button
              variant="contained"
              size="large"
              href="/apply"
              sx={{ py: 2, px: 4 }}
            >
              Apply for Launchpad
            </Button>
            
            <Button
              variant="outlined"
              size="large"
              href="/free-guide"
              sx={{ 
                py: 2, 
                px: 4,
                borderColor: 'white',
                color: 'white',
                '&:hover': {
                  borderColor: 'white',
                  bgcolor: 'rgba(255,255,255,0.1)',
                },
              }}
            >
              Download Free Guide
            </Button>
          </Box>
        </Box>
      </Container>
    </Box>
  )
}

export default VSL