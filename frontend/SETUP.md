# 🚀 TradeFlow Setup Guide

Complete step-by-step guide to get TradeFlow running.

---

## ✅ Prerequisites Check

Before starting, ensure you have:

- [ ] **Node.js 18+** installed
  ```bash
  node --version  # Should show v18.x.x or higher
  ```

- [ ] **npm 9+** installed
  ```bash
  npm --version  # Should show 9.x.x or higher
  ```

- [ ] **Git** (optional, for version control)

---

## 📦 Step 1: Install Dependencies

```bash
cd "Enterprise-Ready SaaS Upgrade (5)"
npm install
```

**Expected output:**
```
added 218 packages, and audited 219 packages
```

**If you see errors:**
- Make sure you're using Node.js 18+
- Try deleting `node_modules` and `package-lock.json`, then run `npm install` again
- Check your internet connection

---

## ⚙️ Step 2: Configure Environment Variables

### Option A: Use Default Configuration (Quick Start)

The project comes with `.env.local` pre-configured for development with mock backend.

**No action needed** - you can skip to Step 3!

### Option B: Custom Configuration

1. **Copy the example file:**
   ```bash
   cp .env.example .env.local
   ```

2. **Edit `.env.local`** with your values:
   ```bash
   # Use your text editor
   nano .env.local
   # or
   code .env.local
   ```

3. **Required variables:**
   - `VITE_SUPABASE_URL` - Your Supabase project URL
   - `VITE_SUPABASE_ANON_KEY` - Your Supabase anon key
   - `VITE_STRIPE_PUBLIC_KEY` - Your Stripe public key (for billing)
   - `VITE_API_BASE_URL` - Your backend API URL

---

## 🎯 Step 3: Start Development Server

```bash
npm run dev
```

**Expected output:**
```
  VITE v6.3.5  ready in XXX ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

**The app should automatically open in your browser!**

If it doesn't, manually navigate to: `http://localhost:3000`

---

## 🧪 Step 4: Verify Installation

### Quick Test

1. **Landing Page** should load
2. **Click "Start Free Trial"**
3. **Signup page** should appear
4. **Create a test account**
5. **Dashboard** should load (with mock data)

### If Something Goes Wrong

**Issue:** Port 3000 already in use
```bash
# Kill the process using port 3000
# Linux/Mac:
lsof -ti:3000 | xargs kill -9

# Or change port in vite.config.ts
```

**Issue:** Build errors
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm run dev
```

**Issue:** Module not found errors
```bash
# Reinstall dependencies
rm -rf node_modules
npm install
```

---

## 🎨 Step 5: Explore the Application

### Default Routes

- `/` - Landing page
- `/login` - Login page
- `/signup` - Signup page
- `/dashboard` - Main dashboard (requires login)
- `/admin` - Admin dashboard (requires admin login)

### Test Credentials (Mock Backend)

When using mock backend (`VITE_USE_MOCK_BACKEND=true`):

- **Email:** `demo@tradeflow.com`
- **Password:** `demo123`

Or create a new account through signup.

---

## 🔧 Step 6: Development Workflow

### Making Changes

1. **Edit files** in `src/` directory
2. **Save** - Vite will hot-reload automatically
3. **Check browser** - Changes appear instantly

### Project Structure

```
src/
├── components/     # React components
├── contexts/      # React contexts (state management)
├── utils/         # Utility functions
├── App.tsx        # Main app component
└── main.tsx       # Entry point
```

### Adding New Features

1. Create component in `src/components/`
2. Import and use in `src/App.tsx`
3. Add route if needed
4. Test in browser

---

## 🏗️ Step 7: Build for Production

When ready to deploy:

```bash
# Build production bundle
npm run build

# Preview production build locally
npm run preview
```

**Output:** `build/` directory with optimized production files

---

## 📚 Next Steps

### Learn More

- **Read:** `README.md` - Full documentation
- **Read:** `src/START_HERE_V6_FINAL.md` - Detailed implementation guide
- **Read:** `src/WIRING_MANIFEST_V6.json` - API documentation

### Connect to Real Backend

1. Set `VITE_USE_MOCK_BACKEND=false` in `.env.local`
2. Configure `VITE_API_BASE_URL` to your backend
3. Ensure backend is running and accessible
4. Restart dev server

### Deploy

See `README.md` section on "Deployment" for Vercel/Netlify instructions.

---

## 🆘 Troubleshooting

### Common Issues

**Problem:** `npm install` fails
- **Solution:** Update Node.js to 18+, clear npm cache: `npm cache clean --force`

**Problem:** App won't start
- **Solution:** Check `.env.local` exists, verify all required variables are set

**Problem:** API calls failing
- **Solution:** Check `VITE_API_BASE_URL` is correct, verify backend is running

**Problem:** TypeScript errors
- **Solution:** Run `npm run type-check` to see detailed errors

**Problem:** Styling broken
- **Solution:** Ensure Tailwind CSS is configured (should be automatic)

---

## ✅ Setup Complete!

You're all set! The project is running and ready for development.

**Quick Commands:**
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build

**Need Help?**
- Check `README.md` for full documentation
- See `src/` directory for detailed guides
- Review error messages in terminal/browser console

**Happy Coding! 🚀**
