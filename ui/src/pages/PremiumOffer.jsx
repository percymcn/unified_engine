import React, { useState } from 'react'
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Button,
  Grid,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Avatar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
  Divider,
} from '@mui/material'
import {
  Star as StarIcon,
  CheckCircle as CheckCircleIcon,
  TrendingUp as TrendingUpIcon,
  School as SchoolIcon,
  People as PeopleIcon,
  Support as SupportIcon,
  LocalOffer as LocalOfferIcon,
  CreditCard as CreditCardIcon,
  Security as SecurityIcon,
  Timer as TimerIcon,
} from '@mui/icons-material'
import { useTheme } from '@mui/material/styles'

const PremiumOffer = () => {
  const theme = useTheme()
  const [selectedPlan, setSelectedPlan] = useState('annual')
  const [paymentDialog, setPaymentDialog] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [paymentComplete, setPaymentComplete] = useState(false)
  const [paymentData, setPaymentData] = useState({
    cardNumber: '',
    expiryDate: '',
    cvv: '',
    name: '',
  })

  const plans = {
    monthly: {
      name: 'Monthly',
      price: 197,
      originalPrice: 297,
      period: 'month',
      savings: 0,
      features: [
        'Access to all learning modules',
        'Weekly group coaching calls',
        'Community access',
        'Trading signals',
        'Email support',
      ],
    },
    quarterly: {
      name: 'Quarterly',
      price: 497,
      originalPrice: 891,
      period: 'quarter',
      savings: 44,
      popular: true,
      features: [
        'Everything in Monthly',
        'Monthly 1-on-1 coaching session',
        'Advanced strategy workshops',
        'Priority email support',
        'Trading journal access',
      ],
    },
    annual: {
      name: 'Annual',
      price: 1497,
      originalPrice: 3564,
      period: 'year',
      savings: 58,
      bestValue: true,
      features: [
        'Everything in Quarterly',
        'Weekly 1-on-1 coaching',
        'Custom trading plan development',
        'Live trading room access',
        'Risk management consultation',
        'Priority support (24hr response)',
        'Certificate of completion',
      ],
    },
  }

  const testimonials = [
    {
      name: 'Michael R.',
      result: '62% ROI in 4 months',
      quote: 'The premium coaching completely transformed my trading. The 1-on-1 sessions alone paid for the membership.',
      avatar: 'MR',
    },
    {
      name: 'Jennifer L.',
      result: 'Consistent monthly income',
      quote: 'Finally replaced my 9-5 income thanks to the strategies and support from the premium program.',
      avatar: 'JL',
    },
    {
      name: 'David K.',
      result: 'Mastered risk management',
      quote: 'The personalized coaching helped me develop a trading plan that actually works for my lifestyle.',
      avatar: 'DK',
    },
  ]

  const handlePayment = async () => {
    setProcessing(true)
    
    try {
      const response = await fetch('/api/v1/funnel/premium/purchase', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          plan_type: selectedPlan,
          payment_method: 'credit_card',
          amount: plans[selectedPlan].price,
          currency: 'USD',
        }),
      })

      const data = await response.json()

      if (data.success) {
        setPaymentComplete(true)
        setTimeout(() => {
          setPaymentDialog(false)
          window.location.href = '/launchpad'
        }, 3000)
      } else {
        throw new Error(data.message || 'Payment failed')
      }
    } catch (error) {
      console.error('Payment error:', error)
    } finally {
      setProcessing(false)
    }
  }

  const currentPlan = plans[selectedPlan]

  return (
    <Box sx={{ bgcolor: 'grey.50', minHeight: '100vh' }}>
      {/* Hero Section */}
      <Box
        sx={{
          background: `linear-gradient(135deg, ${theme.palette.secondary.main} 0%, ${theme.palette.secondary.dark} 100%)`,
          color: 'white',
          py: 8,
          textAlign: 'center',
        }}
      >
        <Container maxWidth="md">
          <Typography variant="h2" gutterBottom fontWeight="bold">
            Premium Trading Membership
          </Typography>
          
          <Typography variant="h5" sx={{ mb: 4, opacity: 0.9 }}>
            Join elite traders with personalized coaching and advanced strategies
          </Typography>
          
          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, flexWrap: 'wrap' }}>
            <Chip
              icon={<TimerIcon />}
              label="Limited Time: 58% OFF Annual"
              color="primary"
              size="large"
              sx={{ fontSize: '1rem', py: 2, px: 3 }}
            />
            <Chip
              icon={<SecurityIcon />}
              label="30-Day Money Back Guarantee"
              variant="outlined"
              size="large"
              sx={{ fontSize: '1rem', py: 2, px: 3, borderColor: 'white', color: 'white' }}
            />
          </Box>
        </Container>
      </Box>

      <Container maxWidth="lg" sx={{ py: 8 }}>
        {/* Pricing Plans */}
        <Typography variant="h4" gutterBottom fontWeight="bold" textAlign="center" sx={{ mb: 6 }}>
          Choose Your Path to Success
        </Typography>

        <Grid container spacing={4} sx={{ mb: 8 }}>
          {Object.entries(plans).map(([key, plan]) => (
            <Grid item xs={12} md={4} key={key}>
              <Card
                sx={{
                  height: '100%',
                  position: 'relative',
                  transform: plan.popular || plan.bestValue ? 'scale(1.05)' : 'scale(1)',
                  boxShadow: plan.popular || plan.bestValue ? theme.shadows[8] : theme.shadows[2],
                }}
              >
                {plan.popular && (
                  <Chip
                    label="MOST POPULAR"
                    color="primary"
                    sx={{
                      position: 'absolute',
                      top: -12,
                      left: '50%',
                      transform: 'translateX(-50%)',
                      zIndex: 1,
                    }}
                  />
                )}
                
                {plan.bestValue && (
                  <Chip
                    label="BEST VALUE"
                    color="secondary"
                    sx={{
                      position: 'absolute',
                      top: -12,
                      left: '50%',
                      transform: 'translateX(-50%)',
                      zIndex: 1,
                    }}
                  />
                )}

                <CardContent sx={{ p: 4 }}>
                  <Box sx={{ textAlign: 'center', mb: 3 }}>
                    <Typography variant="h5" gutterBottom fontWeight="bold">
                      {plan.name}
                    </Typography>
                    
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="h3" color="primary" fontWeight="bold">
                        ${plan.price}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        per {plan.period}
                      </Typography>
                    </Box>
                    
                    {plan.savings > 0 && (
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ textDecoration: 'line-through' }}>
                          ${plan.originalPrice} per {plan.period}
                        </Typography>
                        <Chip
                          label={`Save ${plan.savings}%`}
                          color="success"
                          size="small"
                        />
                      </Box>
                    )}
                  </Box>

                  <List sx={{ mb: 3 }}>
                    {plan.features.map((feature, index) => (
                      <ListItem key={index} sx={{ py: 0.5 }}>
                        <ListItemIcon>
                          <CheckCircleIcon color="success" />
                        </ListItemIcon>
                        <ListItemText primary={feature} />
                      </ListItem>
                    ))}
                  </List>

                  <Button
                    variant={selectedPlan === key ? 'contained' : 'outlined'}
                    fullWidth
                    size="large"
                    onClick={() => {
                      setSelectedPlan(key)
                      setPaymentDialog(true)
                    }}
                    sx={{
                      py: 1.5,
                    }}
                  >
                    {selectedPlan === key ? 'Selected' : `Choose ${plan.name}`}
                  </Button>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* Testimonials */}
        <Typography variant="h4" gutterBottom fontWeight="bold" textAlign="center" sx={{ mb: 6 }}>
          Success Stories
        </Typography>

        <Grid container spacing={4} sx={{ mb: 8 }}>
          {testimonials.map((testimonial, index) => (
            <Grid item xs={12} md={4} key={index}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Avatar sx={{ bgcolor: theme.palette.primary.main, mr: 2 }}>
                      {testimonial.avatar}
                    </Avatar>
                    <Box>
                      <Typography variant="subtitle1" fontWeight="bold">
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
            </Grid>
          ))}
        </Grid>

        {/* Guarantee Section */}
        <Card sx={{ bgcolor: theme.palette.success.main, color: 'white', mb: 6 }}>
          <CardContent sx={{ p: 4, textAlign: 'center' }}>
            <SecurityIcon sx={{ fontSize: 64, mb: 2 }} />
            
            <Typography variant="h4" gutterBottom fontWeight="bold">
              30-Day Money Back Guarantee
            </Typography>
            
            <Typography variant="h6" sx={{ mb: 3 }}>
              Try Premium risk-free. If you're not completely satisfied, get a full refund.
            </Typography>
            
            <Button
              variant="contained"
              size="large"
              sx={{
                bgcolor: 'white',
                color: theme.palette.success.main,
                '&:hover': {
                  bgcolor: 'grey.100',
                },
              }}
              onClick={() => setPaymentDialog(true)}
            >
              Start Risk-Free Trial
            </Button>
          </CardContent>
        </Card>

        {/* FAQ Section */}
        <Typography variant="h4" gutterBottom fontWeight="bold" textAlign="center" sx={{ mb: 6 }}>
          Frequently Asked Questions
        </Typography>

        <Grid container spacing={4}>
          {[
            {
              question: 'Can I cancel anytime?',
              answer: 'Yes, you can cancel your membership at any time. No questions asked.',
            },
            {
              question: 'Is the coaching really 1-on-1?',
              answer: 'Yes, premium members get personalized 1-on-1 coaching sessions tailored to their specific trading goals.',
            },
            {
              question: 'What if I\'m a beginner?',
              answer: 'Our program is designed for all levels. We\'ll assess your experience and create a customized learning path.',
            },
            {
              question: 'Do you provide trading signals?',
              answer: 'Yes, premium members receive real-time trading signals with entry, exit, and risk management guidance.',
            },
          ].map((faq, index) => (
            <Grid item xs={12} md={6} key={index}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h6" gutterBottom fontWeight="bold" color="primary">
                    {faq.question}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {faq.answer}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* Payment Dialog */}
      <Dialog open={paymentDialog} onClose={() => !processing && setPaymentDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {paymentComplete ? 'Payment Successful!' : `Complete Your ${currentPlan.name} Purchase`}
        </DialogTitle>
        
        <DialogContent>
          {paymentComplete ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <CheckCircleIcon sx={{ fontSize: 64, color: theme.palette.success.main, mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                Welcome to Premium!
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Redirecting you to your Launchpad...
              </Typography>
            </Box>
          ) : (
            <Box>
              <Box sx={{ mb: 3, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                <Typography variant="h6" gutterBottom>
                  Order Summary
                </Typography>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography>{currentPlan.name} Plan</Typography>
                  <Typography fontWeight="bold">${currentPlan.price}</Typography>
                </Box>
                {currentPlan.savings > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', color: 'success.main' }}>
                    <Typography>Savings</Typography>
                    <Typography>-${currentPlan.originalPrice - currentPlan.price}</Typography>
                  </Box>
                )}
                <Divider sx={{ my: 1 }} />
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="h6">Total</Typography>
                  <Typography variant="h6" color="primary">${currentPlan.price}</Typography>
                </Box>
              </Box>

              <Typography variant="subtitle2" gutterBottom>
                Payment Information
              </Typography>
              
              <TextField
                fullWidth
                label="Card Number"
                value={paymentData.cardNumber}
                onChange={(e) => setPaymentData({ ...paymentData, cardNumber: e.target.value })}
                sx={{ mb: 2 }}
              />
              
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="Expiry Date"
                    placeholder="MM/YY"
                    value={paymentData.expiryDate}
                    onChange={(e) => setPaymentData({ ...paymentData, expiryDate: e.target.value })}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="CVV"
                    value={paymentData.cvv}
                    onChange={(e) => setPaymentData({ ...paymentData, cvv: e.target.value })}
                  />
                </Grid>
              </Grid>
              
              <TextField
                fullWidth
                label="Name on Card"
                value={paymentData.name}
                onChange={(e) => setPaymentData({ ...paymentData, name: e.target.value })}
                sx={{ mt: 2, mb: 2 }}
              />

              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="caption">
                  Your payment information is secure and encrypted. We never store your card details.
                </Typography>
              </Alert>
            </Box>
          )}
        </DialogContent>
        
        <DialogActions>
          {!paymentComplete && (
            <Button onClick={() => setPaymentDialog(false)} disabled={processing}>
              Cancel
            </Button>
          )}
          <Button
            variant="contained"
            onClick={handlePayment}
            disabled={processing || paymentComplete}
            startIcon={processing ? <CircularProgress size={20} /> : <CreditCardIcon />}
          >
            {processing ? 'Processing...' : paymentComplete ? 'Complete' : `Pay $${currentPlan.price}`}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default PremiumOffer