import { Hono } from "npm:hono";
import { cors } from "npm:hono/cors";
import { logger } from "npm:hono/logger";
import { createClient } from "npm:@supabase/supabase-js";
import * as kv from "./kv_store.tsx";

const app = new Hono();

// Create Supabase client
const supabase = createClient(
  Deno.env.get('SUPABASE_URL') ?? '',
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
);

// Enable logger
app.use('*', logger(console.log));

// Enable CORS for all routes and methods
app.use(
  "/*",
  cors({
    origin: "*",
    allowHeaders: ["Content-Type", "Authorization"],
    allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    exposeHeaders: ["Content-Length"],
    maxAge: 600,
  }),
);

// Health check endpoint
app.get("/make-server-d751d621/health", (c) => {
  return c.json({ status: "ok" });
});

// Signup endpoint
app.post("/make-server-d751d621/auth/signup", async (c) => {
  try {
    const { email, password, name, plan } = await c.req.json();

    // Create user with Supabase Auth
    const { data: authData, error: authError } = await supabase.auth.admin.createUser({
      email,
      password,
      user_metadata: { name },
      // Automatically confirm the user's email since an email server hasn't been configured.
      email_confirm: true
    });

    if (authError) {
      console.error('Auth error during signup:', authError);
      return c.json({ error: authError.message }, 400);
    }

    // Create user profile in KV store
    const userId = authData.user.id;
    const trialEndsAt = new Date();
    trialEndsAt.setDate(trialEndsAt.getDate() + 3); // 3-day trial

    const userProfile = {
      id: userId,
      email,
      name,
      role: email.includes('admin') ? 'admin' : 'user', // Simple admin detection
      plan,
      trialEndsAt: trialEndsAt.toISOString(),
      tradesCount: 0,
      createdAt: new Date().toISOString()
    };

    await kv.set(`user:${userId}`, userProfile);

    return c.json({ 
      success: true, 
      userId,
      message: 'Account created successfully'
    });
  } catch (error) {
    console.error('Signup error:', error);
    return c.json({ error: 'Failed to create account' }, 500);
  }
});

// Get user profile
app.get("/make-server-d751d621/user/profile", async (c) => {
  try {
    const accessToken = c.req.header('Authorization')?.split(' ')[1];
    
    if (!accessToken) {
      return c.json({ error: 'Unauthorized' }, 401);
    }

    const { data: { user }, error } = await supabase.auth.getUser(accessToken);
    
    if (error || !user) {
      console.error('Auth error while fetching profile:', error);
      return c.json({ error: 'Unauthorized' }, 401);
    }

    // Get user profile from KV store
    const profile = await kv.get(`user:${user.id}`);

    if (!profile) {
      // Create default profile if not found
      const defaultProfile = {
        id: user.id,
        email: user.email,
        name: user.user_metadata?.name || 'User',
        role: user.email?.includes('admin') ? 'admin' : 'user',
        plan: 'starter',
        trialEndsAt: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
        tradesCount: 0
      };
      
      await kv.set(`user:${user.id}`, defaultProfile);
      return c.json(defaultProfile);
    }

    return c.json(profile);
  } catch (error) {
    console.error('Error fetching user profile:', error);
    return c.json({ error: 'Failed to fetch profile' }, 500);
  }
});

// Update user profile
app.put("/make-server-d751d621/user/profile", async (c) => {
  try {
    const accessToken = c.req.header('Authorization')?.split(' ')[1];
    
    if (!accessToken) {
      return c.json({ error: 'Unauthorized' }, 401);
    }

    const { data: { user }, error } = await supabase.auth.getUser(accessToken);
    
    if (error || !user) {
      return c.json({ error: 'Unauthorized' }, 401);
    }

    const updates = await c.req.json();
    const existingProfile = await kv.get(`user:${user.id}`);

    const updatedProfile = {
      ...existingProfile,
      ...updates,
      id: user.id, // Ensure ID can't be changed
      email: existingProfile?.email || user.email // Ensure email can't be changed
    };

    await kv.set(`user:${user.id}`, updatedProfile);

    return c.json({ success: true, profile: updatedProfile });
  } catch (error) {
    console.error('Error updating profile:', error);
    return c.json({ error: 'Failed to update profile' }, 500);
  }
});

Deno.serve(app.fetch);