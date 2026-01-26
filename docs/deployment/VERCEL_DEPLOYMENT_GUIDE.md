# Vercel Deployment Guide for MAS-FRO Frontend

## ✅ Code Fixes Applied

All error handling has been improved:
- ✅ Geolocation errors now show user-friendly messages
- ✅ WebSocket gracefully degrades when backend unavailable
- ✅ Flood map loading failures are handled silently
- ✅ App works without backend (limited functionality)

---

## 🚀 Deployment Steps

### **1. Commit and Push Changes**

```bash
git add .
git commit -m "fix: improve error handling for Vercel deployment"
git push origin main
```

---

### **2. Configure Vercel Environment Variables**

Go to: **Vercel Dashboard → Your Project → Settings → Environment Variables**

Add these variables for **Production, Preview, and Development**:

#### **Required Variables:**

```env
NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN=<INSERT>
```

#### **Optional Variables (for backend integration):**

```env
# Leave these EMPTY if backend is not deployed yet
# The app will work without them (offline mode)

NEXT_PUBLIC_BACKEND_API_URL=
NEXT_PUBLIC_WS_URL=
NEXT_PUBLIC_ROUTING_ENDPOINT=
```

#### **When Backend is Deployed:**

Once you deploy the backend (see Backend Deployment section below), update these:

```env
NEXT_PUBLIC_BACKEND_API_URL=https://your-backend.railway.app
NEXT_PUBLIC_WS_URL=wss://your-backend.railway.app
NEXT_PUBLIC_ROUTING_ENDPOINT=https://your-backend.railway.app/api/route
NEXT_PUBLIC_DISABLE_BACKEND_ROUTING=false
```

#### **Optional (if using Google Places):**

```env
GOOGLE_MAPS_API_KEY=<INSERT>
```

---

### **3. Redeploy**

After setting environment variables:

1. Go to **Deployments** tab
2. Click **"Redeploy"** on the latest deployment
3. Check **"Use existing Build Cache"** = NO (force rebuild)
4. Click **"Redeploy"**

---

## ✅ Expected Behavior After Deployment

### **Without Backend (Offline Mode):**
- ✅ Map displays correctly
- ✅ Flood visualization works (if static files included)
- ✅ Location search works (Google Places)
- ✅ UI fully functional
- ⚠️ Route calculation falls back to Mapbox Directions
- ⚠️ Real-time updates unavailable
- ⚠️ Feedback submission unavailable
- ⚠️ Dashboard shows "Offline" mode

### **With Backend Deployed:**
- ✅ All features fully functional
- ✅ MAS-FRO routing algorithm active
- ✅ Real-time WebSocket updates
- ✅ Feedback submission works
- ✅ Dashboard shows live data
- ✅ All 4 agents active

---

## 🔧 Vercel-Specific Considerations

### **1. WebSocket Limitations**

⚠️ **Important:** Vercel's serverless functions **DO NOT support WebSocket connections!**

**Impact:**
- Frontend WebSocket will try to connect but gracefully fail
- App shows "Offline" or "Disconnected" status
- REST API calls still work fine

**Solution:**
- Deploy backend separately on Railway, Render, or DigitalOcean
- These platforms support persistent WebSocket connections

### **2. Static File Serving**

Flood map GeoTIFF files are large and should be served from:
- ✅ Backend `/data` endpoint
- ✅ CDN (Cloudflare, AWS S3)
- ❌ NOT from Vercel (size limits)

### **3. HTTPS Requirements**

Vercel deployments use HTTPS by default:
- ✅ Geolocation API works (requires HTTPS)
- ✅ WebSocket must use `wss://` (not `ws://`)
- ✅ Backend must support HTTPS

---

## 🏗️ Backend Deployment (Recommended Platforms)

The backend MUST be deployed separately. Recommended platforms:

### **Option 1: Railway (Easiest)**

1. **Create Railway account**: https://railway.app
2. **New Project** → **Deploy from GitHub**
3. **Select** `masfro-backend` directory
4. **Add environment variables**:
   ```env
   PORT=8000
   ```
5. **Deploy** - Railway auto-detects Python and runs uvicorn
6. **Copy deployment URL** (e.g., `https://your-app.railway.app`)
7. **Update Vercel env vars** with this URL

### **Option 2: Render**

1. **Create Render account**: https://render.com
2. **New Web Service** → **Connect GitHub**
3. **Settings**:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. **Deploy** and copy URL
5. **Update Vercel env vars**

### **Option 3: DigitalOcean App Platform**

1. **Create DO account**: https://digitalocean.com
2. **Apps** → **Create App**
3. **Choose GitHub repo**
4. Configure Python buildpack
5. Set run command: `uvicorn app.main:app --host 0.0.0.0 --port 8080`
6. **Deploy** and copy URL

### **Option 4: Fly.io**

1. **Install flyctl**: https://fly.io/docs/hands-on/install-flyctl/
2. **From backend directory**:
   ```bash
   cd masfro-backend
   fly launch
   fly deploy
   ```
3. Copy deployment URL
4. **Update Vercel env vars**

---

## 🐛 Troubleshooting Vercel Errors

### **Error: "WebSocket connection failed"**
**Solution:** This is expected if backend not deployed. App works in offline mode.

### **Error: "Geolocation permission denied"**
**Solution:** User must allow location access in browser. Error message now helpful.

### **Error: "Failed to fetch resource"**
**Solution:** Backend URL not configured. App falls back to Mapbox routing.

### **Error: "Module not found"**
**Solution:**
```bash
cd masfro-frontend
npm install
git add package-lock.json
git commit -m "update dependencies"
git push
```

### **Build succeeds but app shows blank page**
**Solution:**
1. Check browser console (F12) for errors
2. Verify `NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN` is set in Vercel
3. Redeploy with cache cleared

---

## 📊 Testing Your Deployment

### **1. Test Frontend-Only Features:**
- Map loads ✅
- Flood slider works ✅
- Location search works ✅
- UI responsive ✅

### **2. Test Backend Integration (if deployed):**
```bash
# Test health endpoint
curl https://your-backend.railway.app/api/health

# Should return:
# {"status":"healthy","graph_status":"loaded","agents":{...}}
```

### **3. Test Full Integration:**
1. Open deployed frontend
2. Select start/end points
3. Click "Find Route"
4. Should see route calculated
5. Submit feedback
6. Check dashboard

---

## 📝 Deployment Checklist

### **Frontend (Vercel):**
- [ ] Code committed and pushed to GitHub
- [ ] Vercel project connected to GitHub repo
- [ ] Environment variables set in Vercel
- [ ] `NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN` configured
- [ ] Deployed successfully
- [ ] Map loads correctly
- [ ] No console errors (except expected WebSocket warnings)

### **Backend (Railway/Render/etc):**
- [ ] Backend deployed to hosting platform
- [ ] Health endpoint accessible: `/api/health`
- [ ] CORS configured for Vercel domain
- [ ] WebSocket endpoint working: `/ws/route-updates`
- [ ] Environment variables set
- [ ] Deployment URL copied

### **Integration:**
- [ ] Vercel env vars updated with backend URL
- [ ] Frontend redeployed with new env vars
- [ ] Route calculation works
- [ ] Feedback submission works
- [ ] WebSocket connects
- [ ] Dashboard shows live data

---

## 🎯 Quick Start (No Backend)

If you just want to deploy the frontend without backend:

1. **Set only required env var in Vercel:**
   ```env
   NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN=<INSERT>
   ```

2. **Deploy** - that's it!

3. **App will work in offline mode:**
   - Map ✅
   - UI ✅
   - Limited routing (Mapbox fallback) ⚠️

---

## 💡 Pro Tips

1. **Use Vercel for frontend only** - it's optimized for Next.js
2. **Deploy backend separately** - Railway/Render support WebSockets
3. **Environment variables** - Always set for Production, Preview, AND Development
4. **Redeploy after env changes** - Required for changes to take effect
5. **Check logs** - Vercel dashboard shows build and runtime logs
6. **Custom domain** - Add in Vercel settings for production

---

## 🔗 Useful Links

- **Vercel Dashboard**: https://vercel.com/dashboard
- **Railway**: https://railway.app
- **Render**: https://render.com
- **Next.js Docs**: https://nextjs.org/docs
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/

---

## ✅ Success Criteria

Your deployment is successful when:

1. ✅ Frontend loads without errors
2. ✅ Map displays Marikina area
3. ✅ No red errors in browser console
4. ✅ (Optional) Backend health check returns 200
5. ✅ (Optional) Route calculation works
6. ✅ (Optional) WebSocket connects

---

**Need help?** Check the troubleshooting section or create an issue on GitHub.

**Last Updated:** November 2025
**Status:** Ready for Deployment
