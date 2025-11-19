# Quick Logging Test Guide

## ✅ Test Frontend Logging (Browser Console)

### **Step 1: Start Frontend**
```bash
cd masfro-frontend
npm run dev
```

### **Step 2: Open Browser**
- Navigate to `http://localhost:3000`
- Open DevTools (F12)
- Go to Console tab

### **Step 3: Observe Logs**

You should see logs appearing automatically:

```
[AgentDataPanel][INFO][2025-11-19T18:50:00.123Z] AgentDataPanel mounted - initializing data fetch
[AgentDataPanel][DEBUG][2025-11-19T18:50:00.145Z] Fetching agent status { endpoint: "http://localhost:8000/api/agents/status" }
[AgentDataPanel][INFO][2025-11-19T18:50:00.456Z] Agent status updated successfully { agents: [...], activeCount: 4 }
```

### **Step 4: Interact with UI**

**Click "Scout Reports" tab**:
```
[AgentDataPanel][INFO] Tab changed to: scout
[AgentDataPanel][INFO] Fetching scout reports { endpoint: "..." }
[AgentDataPanel][DEBUG] Scout reports response received { status: 200, ok: true }
[AgentDataPanel][INFO] Scout reports loaded: 0 reports
```

**Click "Flood Data" tab**:
```
[AgentDataPanel][INFO] Tab changed to: flood
[AgentDataPanel][INFO] Fetching flood data { endpoint: "..." }
[AgentDataPanel][DEBUG] Flood data response received { status: 200, ok: true }
[AgentDataPanel][INFO] Flood data loaded successfully { dataPoints: 0, source: "..." }
```

---

## ✅ Test Backend Logging (Terminal)

### **Option 1: Watch Live Logs**
```bash
cd masfro-backend
tail -f logs/masfro.log
```

### **Option 2: Search Specific Logs**
```bash
# View all FloodAgent logs
grep "flood_agent" logs/masfro.log

# View all API requests
grep "GET /api" logs/masfro.log

# View errors only
cat logs/masfro_errors.log
```

### **Option 3: Check Latest Logs**
```bash
# Last 50 lines
tail -n 50 logs/masfro.log

# Last 100 lines with follow
tail -n 100 -f logs/masfro.log
```

---

## 🎯 Expected Results

### ✅ **Frontend Console Output**

Every 30 seconds (automatic refresh):
```
[AgentDataPanel][DEBUG] Fetching agent status
[AgentDataPanel][INFO] Agent status updated successfully
```

When switching tabs:
```
[AgentDataPanel][INFO] Tab changed to: scout
[AgentDataPanel][INFO] Fetching scout reports
[AgentDataPanel][INFO] Scout reports loaded: X reports
```

### ✅ **Backend Log File Output**

Real-time flood data collection (every 5 minutes):
```
2025-11-19 18:48:04 - app.agents.flood_agent - INFO - flood_agent_001 collecting flood data from all sources...
2025-11-19 18:48:15 - app.agents.flood_agent - INFO - River level is 22.36m at Montalban
2025-11-19 18:48:15 - app.agents.flood_agent - INFO - [OK] Collected REAL river data: 4 stations
```

API request logs:
```
INFO: 127.0.0.1:50693 - "GET /api/agents/status HTTP/1.1" 200 OK
INFO: 127.0.0.1:50743 - "GET /api/agents/scout/reports?limit=10&hours=24 HTTP/1.1" 200 OK
```

---

## 🔍 Debugging Tips

### **Filter Console Logs**

In Chrome DevTools Console:
1. Click the filter icon (funnel)
2. Type: `[AgentDataPanel]` to show only AgentDataPanel logs
3. Select log levels: Info, Warnings, Errors

### **Export Logs**

Right-click in console → "Save as..." to export logs to file

### **Clear Logs**

Click 🚫 (Clear console) button or press Ctrl+L

---

## ✨ What to Look For

### ✅ **Good Signs**
- Logs appear with proper timestamps
- Request/response logs show HTTP 200 status
- Agent status shows agents as "active"
- No red error messages

### ⚠️ **Warning Signs**
- Yellow warnings about failed fetches
- "offline" or "inactive" agent status
- Network errors in console

### ❌ **Error Signs**
- Red error messages
- "Failed to fetch" errors
- CORS errors (check backend CORS settings)
- 500 Internal Server Error responses

---

## 📊 Current Backend Status

**Backend is RUNNING** ✅
- Server: `http://localhost:8000`
- Process ID: Available via `netstat -ano | findstr :8000`
- Logs: `masfro-backend/logs/masfro.log`

**Agents Active**:
- ✅ FloodAgent (collecting real data)
- ✅ HazardAgent
- ✅ RoutingAgent
- ✅ EvacuationManagerAgent
- ❌ ScoutAgent (inactive)

**Recent Activity**:
- Collected 4 river stations (Montalban, Nangka, Sto Nino, Tumana Bridge)
- Collected 9 dam levels
- Collected weather data (0.0mm rainfall)
- 6 WebSocket connections active
