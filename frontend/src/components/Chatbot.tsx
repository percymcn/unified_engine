import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { MessageCircle, X, Send, Bot, User } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { ScrollArea } from './ui/scroll-area';
import { cn } from './ui/utils';

interface Message {
  id: string;
  text: string;
  sender: 'bot' | 'user';
  timestamp: Date;
}

interface ChatbotProps {
  /** If true, renders as a button in the sidebar. If false, renders as a floating button */
  inSidebar?: boolean;
  className?: string;
}

export function Chatbot({ inSidebar = false, className }: ChatbotProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: "Hi! I'm the TradeFlow assistant. How can I help you today?",
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');

  const quickReplies = [
    'MT4/MT5 EA Setup',
    'Pricing Plans',
    'Supported Brokers',
    'Trial Information',
    'Contact Support'
  ];

  const botResponses: Record<string, string> = {
    'mt4': 'MT4 and MT5 require the TradeFlow EA (Expert Advisor) installation. Download it from your dashboard after signup, install it in your MetaTrader platform, and configure your API credentials. Need help? Email support@fluxeo.net',
    'mt5': 'MT4 and MT5 require the TradeFlow EA (Expert Advisor) installation. Download it from your dashboard after signup, install it in your MetaTrader platform, and configure your API credentials. Need help? Email support@fluxeo.net',
    'pricing': 'We offer 3 plans: Starter ($20/mo, 1 broker), Pro ($40/mo, 2 brokers + 1 Fluxeo strategy), and Elite ($60/mo, 3 brokers + 3 strategies). All plans include a 3-day or 100-trade trial. Contact support@fluxeo.net for custom plans.',
    'broker': 'TradeFlow supports TradeLocker, Topstep (ProjectX), and TruForex. MT4/MT5 require our EA installation. TradeLocker, Topstep, and TruForex work via API. Questions? Email support@fluxeo.net',
    'trial': 'Your trial lasts 3 days OR 100 trades, whichever comes first. No credit card required to start! After the trial, choose a plan to continue. Support: support@fluxeo.net',
    'support': 'You can reach our support team at support@fluxeo.net. We typically respond within 24 hours for all plans, with priority support for Pro and Elite members.',
    'default': "I'm here to help! Ask me about MT4/MT5 EA setup, pricing, brokers, trials, or contact support@fluxeo.net directly."
  };

  const getBotResponse = (userMessage: string): string => {
    const lower = userMessage.toLowerCase();
    
    if (lower.includes('mt4') || lower.includes('mt5') || lower.includes('ea') || lower.includes('expert advisor')) {
      return botResponses.mt4;
    }
    if (lower.includes('price') || lower.includes('pricing') || lower.includes('plan') || lower.includes('cost')) {
      return botResponses.pricing;
    }
    if (lower.includes('broker') || lower.includes('tradelocker') || lower.includes('topstep') || lower.includes('truforex')) {
      return botResponses.broker;
    }
    if (lower.includes('trial') || lower.includes('free')) {
      return botResponses.trial;
    }
    if (lower.includes('support') || lower.includes('help') || lower.includes('contact')) {
      return botResponses.support;
    }
    
    return botResponses.default;
  };

  const handleSend = (text?: string) => {
    const messageText = text || inputValue.trim();
    if (!messageText) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      text: messageText,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');

    // Add bot response after a delay
    setTimeout(() => {
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: getBotResponse(messageText),
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botMessage]);
    }, 600);
  };

  // Sidebar button
  if (inSidebar) {
    return (
      <>
        {/* Sidebar Button */}
        <button
          onClick={() => setIsOpen(true)}
          className={cn(
            "w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors touch-manipulation min-h-[44px] text-gray-400 hover:text-white hover:bg-[#002b36] relative",
            className
          )}
        >
          <MessageCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm md:text-base">Support Chat</span>
          
          {/* Online indicator */}
          <span className="absolute top-2 left-9 flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00ffc2] opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00ffc2]"></span>
          </span>
        </button>

        {/* Chat Window */}
        <ChatWindow 
          isOpen={isOpen} 
          onClose={() => setIsOpen(false)}
          messages={messages}
          inputValue={inputValue}
          setInputValue={setInputValue}
          handleSend={handleSend}
          quickReplies={quickReplies}
        />
      </>
    );
  }

  // Floating button (original design)
  return (
    <>
      {/* Floating Chat Button */}
      <motion.button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 rounded-full bg-[#0EA5E9] p-4 shadow-lg hover:shadow-xl transition-all hover:bg-[#0284c7]"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        style={{ display: isOpen ? 'none' : 'block' }}
      >
        <MessageCircle className="w-6 h-6 text-white" />
        
        {/* Notification Pulse */}
        <span className="absolute -top-1 -right-1 flex h-3 w-3">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00ffc2] opacity-75"></span>
          <span className="relative inline-flex rounded-full h-3 w-3 bg-[#00ffc2]"></span>
        </span>
      </motion.button>

      {/* Chat Window */}
      <ChatWindow 
        isOpen={isOpen} 
        onClose={() => setIsOpen(false)}
        messages={messages}
        inputValue={inputValue}
        setInputValue={setInputValue}
        handleSend={handleSend}
        quickReplies={quickReplies}
      />
    </>
  );
}

// Separate Chat Window component for reuse
function ChatWindow({
  isOpen,
  onClose,
  messages,
  inputValue,
  setInputValue,
  handleSend,
  quickReplies
}: {
  isOpen: boolean;
  onClose: () => void;
  messages: Message[];
  inputValue: string;
  setInputValue: (value: string) => void;
  handleSend: (text?: string) => void;
  quickReplies: string[];
}) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          className="fixed bottom-6 right-6 z-50 w-[90vw] sm:w-96 h-[600px] max-h-[80vh] bg-[#001f29] border border-[#0EA5E9]/30 rounded-2xl shadow-2xl flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-[#0EA5E9] to-[#0284c7] p-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div>
                <span className="text-white font-semibold">TradeFlow Support</span>
                <div className="flex items-center gap-1 text-xs text-white/80">
                  <div className="w-2 h-2 rounded-full bg-[#00ffc2] animate-pulse"></div>
                  <span>Online</span>
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-white hover:bg-white/20 p-2 rounded-full transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Messages */}
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className="flex items-start gap-2 max-w-[85%]">
                    {message.sender === 'bot' && (
                      <div className="w-8 h-8 rounded-full bg-[#0EA5E9] flex items-center justify-center flex-shrink-0">
                        <Bot className="w-4 h-4 text-white" />
                      </div>
                    )}
                    <div
                      className={`rounded-2xl px-4 py-2.5 ${
                        message.sender === 'user'
                          ? 'bg-[#0EA5E9] text-white rounded-br-none'
                          : 'bg-[#002b36] text-gray-200 border border-gray-700 rounded-bl-none'
                      }`}
                    >
                      <p className="text-sm leading-relaxed">{message.text}</p>
                      <p className="text-xs opacity-60 mt-1">
                        {message.timestamp.toLocaleTimeString([], { 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                      </p>
                    </div>
                    {message.sender === 'user' && (
                      <div className="w-8 h-8 rounded-full bg-[#00ffc2] flex items-center justify-center flex-shrink-0">
                        <User className="w-4 h-4 text-[#002b36]" />
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>

          {/* Quick Replies */}
          {messages.length <= 2 && (
            <div className="px-4 pb-2 border-t border-gray-800">
              <p className="text-xs text-gray-400 mb-2 mt-2">Quick replies:</p>
              <div className="flex flex-wrap gap-2">
                {quickReplies.map((reply) => (
                  <button
                    key={reply}
                    onClick={() => handleSend(reply)}
                    className="text-xs px-3 py-1.5 rounded-full bg-[#002b36] text-[#0EA5E9] border border-[#0EA5E9]/30 hover:bg-[#0EA5E9]/10 transition-colors"
                  >
                    {reply}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="p-4 border-t border-gray-800 bg-[#001f29]">
            <div className="flex gap-2">
              <Input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Type your message..."
                className="bg-[#002b36] border-gray-700 text-white placeholder:text-gray-500 focus:border-[#0EA5E9]"
              />
              <Button
                onClick={() => handleSend()}
                className="bg-[#0EA5E9] text-white hover:bg-[#0284c7]"
                size="icon"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center">
              Or email us at{' '}
              <a href="mailto:support@fluxeo.net" className="text-[#0EA5E9] hover:underline">
                support@fluxeo.net
              </a>
            </p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
