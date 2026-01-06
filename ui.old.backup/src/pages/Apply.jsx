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
  Stepper,
  Step,
  StepLabel,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  FormControlLabel,
  RadioGroup,
  Radio,
  Grid,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material'
import {
  Person as PersonIcon,
  School as SchoolIcon,
  TrendingUp as TrendingUpIcon,
  AttachMoney as MoneyIcon,
  Schedule as ScheduleIcon,
  Security as SecurityIcon,
  CheckCircle as CheckCircleIcon,
  ArrowForward as ArrowForwardIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material'
import { useTheme } from '@mui/material/styles'

const Apply = () => {
  const theme = useTheme()
  const [activeStep, setActiveStep] = useState(0)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')
  const [leadId, setLeadId] = useState('')

  const steps = [
    'Personal Information',
    'Trading Experience',
    'Goals & Commitment',
    'Review & Submit',
  ]

  const [formData, setFormData] = useState({
    // Personal Info
    full_name: '',
    email: '',
    phone: '',
    
    // Trading Experience
    experience_level: '',
    years_traded: '',
    previous_education: [],
    trading_platforms: [],
    
    // Goals & Commitment
    trading_goals: [],
    initial_capital: '',
    time_commitment: '',
    risk_tolerance: '',
    
    // Additional
    why_interested: '',
    expectations: '',
  })

  useEffect(() => {
    // Get lead ID from URL params or localStorage
    const urlParams = new URLSearchParams(window.location.search)
    const lead = urlParams.get('lead') || localStorage.getItem('lead_id')
    if (lead) {
      setLeadId(lead)
      setFormData(prev => ({ ...prev, email: urlParams.get('email') || '' }))
    }
  }, [])

  const handleNext = () => {
    setActiveStep((prevStep) => prevStep + 1)
  }

  const handleBack = () => {
    setActiveStep((prevStep) => prevStep - 1)
  }

  const handleChange = (field) => (event) => {
    const value = event.target.type === 'checkbox' 
      ? event.target.checked 
      : event.target.value
    
    setFormData({
      ...formData,
      [field]: value,
    })
  }

  const handleMultiSelect = (field) => (event) => {
    setFormData({
      ...formData,
      [field]: event.target.value,
    })
  }

  const handleSubmit = async () => {
    setIsSubmitting(true)
    setError('')

    try {
      const response = await fetch('/api/v1/funnel/application/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'funnel-api-key-2024',
        },
        body: JSON.stringify({
          lead_id: leadId,
          full_name: formData.full_name,
          email: formData.email,
          phone: formData.phone,
          experience_level: formData.experience_level,
          trading_goals: formData.trading_goals,
          initial_capital: formData.initial_capital,
          time_commitment: formData.time_commitment,
          risk_tolerance: formData.risk_tolerance,
          additional_data: {
            years_traded: formData.years_traded,
            previous_education: formData.previous_education,
            trading_platforms: formData.trading_platforms,
            why_interested: formData.why_interested,
            expectations: formData.expectations,
          },
        }),
      })

      const data = await response.json()

      if (data.success) {
        setSubmitted(true)
      } else {
        setError(data.message || 'Failed to submit application. Please try again.')
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
            background: `linear-gradient(135deg, ${theme.palette.success.main} 0%, ${theme.palette.success.dark} 100%)`,
            color: 'white',
          }}
        >
          <CheckCircleIcon sx={{ fontSize: 80, mb: 3 }} />
          
          <Typography variant="h3" gutterBottom>
            Application Submitted!
          </Typography>
          
          <Typography variant="h6" sx={{ mb: 4 }}>
            Thank you for your interest in our Launchpad program. Our team will review your application 
            and contact you within 24-48 hours.
          </Typography>
          
          <Typography variant="body1" sx={{ mb: 4 }}>
            Application ID: #{Math.random().toString(36).substr(2, 9).toUpperCase()}
          </Typography>
          
          <Button
            variant="contained"
            size="large"
            href="/"
            sx={{
              bgcolor: 'white',
              color: theme.palette.success.main,
              '&:hover': {
                bgcolor: 'grey.100',
              },
            }}
          >
            Return to Dashboard
          </Button>
        </Paper>
      </Container>
    )
  }

  const renderStepContent = (step) => {
    switch (step) {
      case 0:
        return (
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Full Name"
                value={formData.full_name}
                onChange={handleChange('full_name')}
                required
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Email Address"
                type="email"
                value={formData.email}
                onChange={handleChange('email')}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Phone Number"
                value={formData.phone}
                onChange={handleChange('phone')}
                required
              />
            </Grid>
          </Grid>
        )

      case 1:
        return (
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <FormControl fullWidth required>
                <InputLabel>Trading Experience Level</InputLabel>
                <Select
                  value={formData.experience_level}
                  onChange={handleChange('experience_level')}
                >
                  <MenuItem value="beginner">Beginner (0-1 years)</MenuItem>
                  <MenuItem value="intermediate">Intermediate (1-3 years)</MenuItem>
                  <MenuItem value="advanced">Advanced (3-5 years)</MenuItem>
                  <MenuItem value="expert">Expert (5+ years)</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="How many years have you been actively trading?"
                value={formData.years_traded}
                onChange={handleChange('years_traded')}
                multiline
                rows={2}
              />
            </Grid>
            
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>
                Previous Trading Education (Select all that apply)
              </Typography>
              <FormControl component="fieldset">
                <FormGroup>
                  {['Self-taught', 'Online courses', 'Trading books', 'Mentorship', 'Formal education'].map((option) => (
                    <FormControlLabel
                      key={option}
                      control={
                        <Checkbox
                          checked={formData.previous_education.includes(option)}
                          onChange={(e) => {
                            const updated = e.target.checked
                              ? [...formData.previous_education, option]
                              : formData.previous_education.filter(item => item !== option)
                            setFormData({ ...formData, previous_education: updated })
                          }}
                        />
                      }
                      label={option}
                    />
                  ))}
                </FormGroup>
              </FormControl>
            </Grid>
            
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>
                Trading Platforms Used (Select all that apply)
              </Typography>
              <FormControl component="fieldset">
                <FormGroup>
                  {['MT4', 'MT5', 'TradingView', 'Thinkorswim', 'Interactive Brokers', 'Other'].map((platform) => (
                    <FormControlLabel
                      key={platform}
                      control={
                        <Checkbox
                          checked={formData.trading_platforms.includes(platform)}
                          onChange={(e) => {
                            const updated = e.target.checked
                              ? [...formData.trading_platforms, platform]
                              : formData.trading_platforms.filter(item => item !== platform)
                            setFormData({ ...formData, trading_platforms: updated })
                          }}
                        />
                      }
                      label={platform}
                    />
                  ))}
                </FormGroup>
              </FormControl>
            </Grid>
          </Grid>
        )

      case 2:
        return (
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>
                What are your primary trading goals? (Select all that apply)
              </Typography>
              <FormControl component="fieldset">
                <FormGroup>
                  {['Generate consistent income', 'Build long-term wealth', 'Learn professional strategies', 'Replace current income', 'Supplement retirement'].map((goal) => (
                    <FormControlLabel
                      key={goal}
                      control={
                        <Checkbox
                          checked={formData.trading_goals.includes(goal)}
                          onChange={(e) => {
                            const updated = e.target.checked
                              ? [...formData.trading_goals, goal]
                              : formData.trading_goals.filter(item => item !== goal)
                            setFormData({ ...formData, trading_goals: updated })
                          }}
                        />
                      }
                      label={goal}
                    />
                  ))}
                </FormGroup>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FormControl fullWidth required>
                <InputLabel>Initial Capital to Start</InputLabel>
                <Select
                  value={formData.initial_capital}
                  onChange={handleChange('initial_capital')}
                >
                  <MenuItem value="under-1k">Under $1,000</MenuItem>
                  <MenuItem value="1k-5k">$1,000 - $5,000</MenuItem>
                  <MenuItem value="5k-10k">$5,000 - $10,000</MenuItem>
                  <MenuItem value="10k-25k">$10,000 - $25,000</MenuItem>
                  <MenuItem value="25k-50k">$25,000 - $50,000</MenuItem>
                  <MenuItem value="over-50k">Over $50,000</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FormControl fullWidth required>
                <InputLabel>Time Commitment</InputLabel>
                <Select
                  value={formData.time_commitment}
                  onChange={handleChange('time_commitment')}
                >
                  <MenuItem value="1-2-hours">1-2 hours per day</MenuItem>
                  <MenuItem value="2-4-hours">2-4 hours per day</MenuItem>
                  <MenuItem value="4-6-hours">4-6 hours per day</MenuItem>
                  <MenuItem value="6-plus-hours">6+ hours per day</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>
                Risk Tolerance
              </Typography>
              <FormControl component="fieldset">
                <RadioGroup
                  value={formData.risk_tolerance}
                  onChange={handleChange('risk_tolerance')}
                >
                  <FormControlLabel value="conservative" control={<Radio />} label="Conservative (Preserve capital, lower returns)" />
                  <FormControlLabel value="moderate" control={<Radio />} label="Moderate (Balanced risk/reward)" />
                  <FormControlLabel value="aggressive" control={<Radio />} label="Aggressive (Higher risk for higher returns)" />
                </RadioGroup>
              </FormControl>
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Why are you interested in our Launchpad program?"
                value={formData.why_interested}
                onChange={handleChange('why_interested')}
                multiline
                rows={3}
                required
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="What are your expectations from this program?"
                value={formData.expectations}
                onChange={handleChange('expectations')}
                multiline
                rows={3}
              />
            </Grid>
          </Grid>
        )

      case 3:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Please review your application before submitting:
            </Typography>
            
            <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
              <List>
                <ListItem>
                  <ListItemIcon><PersonIcon /></ListItemIcon>
                  <ListItemText
                    primary="Personal Information"
                    secondary={`${formData.full_name} • ${formData.email} • ${formData.phone}`}
                  />
                </ListItem>
                
                <Divider />
                
                <ListItem>
                  <ListItemIcon><SchoolIcon /></ListItemIcon>
                  <ListItemText
                    primary="Experience Level"
                    secondary={formData.experience_level}
                  />
                </ListItem>
                
                <Divider />
                
                <ListItem>
                  <ListItemIcon><TrendingUpIcon /></ListItemIcon>
                  <ListItemText
                    primary="Trading Goals"
                    secondary={formData.trading_goals.join(', ')}
                  />
                </ListItem>
                
                <Divider />
                
                <ListItem>
                  <ListItemIcon><MoneyIcon /></ListItemIcon>
                  <ListItemText
                    primary="Initial Capital"
                    secondary={formData.initial_capital}
                  />
                </ListItem>
                
                <Divider />
                
                <ListItem>
                  <ListItemIcon><ScheduleIcon /></ListItemIcon>
                  <ListItemText
                    primary="Time Commitment"
                    secondary={formData.time_commitment}
                  />
                </ListItem>
                
                <Divider />
                
                <ListItem>
                  <ListItemIcon><SecurityIcon /></ListItemIcon>
                  <ListItemText
                    primary="Risk Tolerance"
                    secondary={formData.risk_tolerance}
                  />
                </ListItem>
              </List>
            </Paper>
            
            <Typography variant="body2" color="text.secondary">
              By submitting this application, you confirm that all information provided is accurate 
              and you understand that our team will review it for program eligibility.
            </Typography>
          </Box>
        )

      default:
        return null
    }
  }

  return (
    <Container maxWidth="md" sx={{ py: 8 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom fontWeight="bold" textAlign="center">
          Launchpad Application
        </Typography>
        
        <Typography variant="body1" color="text.secondary" textAlign="center" sx={{ mb: 4 }}>
          Apply for our exclusive trading mentorship program
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        <Box sx={{ mb: 4 }}>
          {renderStepContent(activeStep)}
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Button
            disabled={activeStep === 0}
            onClick={handleBack}
            startIcon={<ArrowBackIcon />}
          >
            Back
          </Button>
          
          {activeStep === steps.length - 1 ? (
            <Button
              variant="contained"
              onClick={handleSubmit}
              disabled={isSubmitting}
              startIcon={isSubmitting ? <CircularProgress size={20} /> : <CheckCircleIcon />}
            >
              {isSubmitting ? 'Submitting...' : 'Submit Application'}
            </Button>
          ) : (
            <Button
              variant="contained"
              onClick={handleNext}
              endIcon={<ArrowForwardIcon />}
            >
              Next
            </Button>
          )}
        </Box>
      </Paper>
    </Container>
  )
}

export default Apply