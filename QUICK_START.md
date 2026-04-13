# ⚡ Quick Start Guide - Backend

## 🎯 Get Running in 5 Minutes

### Step 1: Setup Python Environment (2 min)

```bash
# Open Terminal/Command Prompt
# Navigate to backend folder
cd healthcare-backend

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate

# You should see (venv) in your terminal now
```

### Step 2: Install Dependencies (2 min)

```bash
pip install -r requirements.txt
```

Wait for installation to complete...

### Step 3: Run the Server (1 min)

```bash
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**✅ Done! Your backend is running!**

---

## 🧪 Test It Works

### Option 1: Browser Test
Open: http://localhost:8000

You should see:
```json
{
  "message": "MediGraph Healthcare API",
  "version": "1.0.0",
  "status": "running"
}
```

### Option 2: Interactive Docs
Open: http://localhost:8000/docs

You'll see a beautiful Swagger UI where you can test all endpoints!

---

## 🔗 Connect with Frontend

1. **Keep backend running** (don't close the terminal)
2. **Open a NEW terminal**
3. **Navigate to frontend folder:**
   ```bash
   cd healthcare-frontend
   npm start
   ```
4. **Both should be running now:**
   - Backend: http://localhost:8000
   - Frontend: http://localhost:3000

---

## 🎮 Test the Full Flow

### 1. Register a User

**In Swagger UI** (http://localhost:8000/docs):
- Click on `POST /api/auth/register`
- Click "Try it out"
- Enter:
  ```json
  {
    "user_id": "TEST123",
    "password": "test123",
    "user_type": "Patient"
  }
  ```
- Click "Execute"

### 2. Login

- Click on `POST /api/auth/login`
- Click "Try it out"
- Enter:
  ```json
  {
    "user_id": "TEST123",
    "password": "test123"
  }
  ```
- Click "Execute"

### 3. Test on Frontend

1. Go to http://localhost:3000
2. Login with:
   - User ID: TEST123
   - Password: test123
3. Upload a prescription image
4. Watch the 6 agents process it in real-time!

---

## 📁 File Structure

```
healthcare-backend/
├── main.py              ← The main server file
├── requirements.txt     ← Dependencies list
├── README.md           ← Full documentation
├── QUICK_START.md      ← This file
└── .env.example        ← Environment variables template
```

---

## 🐛 Common Issues

### "python: command not found"
**Fix:** Install Python from python.org

### "pip: command not found"
**Fix:** Use `python -m pip install -r requirements.txt`

### "Module not found"
**Fix:** Make sure venv is activated (you see `(venv)` in terminal)

### Port 8000 already in use
**Fix:** Change port in main.py:
```python
uvicorn.run(app, host="0.0.0.0", port=8001)  # Changed to 8001
```

### Neo4j connection error
**Fix:** The credentials in main.py should work. If not:
1. Create free Neo4j Aura account: https://neo4j.com/cloud/aura/
2. Replace credentials in main.py

### Google API error
**Fix:** The API key in main.py should work. If rate limited:
1. Get your own key: https://makersuite.google.com/app/apikey
2. Replace in main.py

---

## 🎯 What Each Agent Does

When you upload a prescription:

1. **Agent 1 - OCR** 🔍
   - Extracts text from image
   - ~2 seconds

2. **Agent 2 - Correction** ✏️
   - Fixes spelling mistakes
   - ~2 seconds

3. **Agent 3 - Understanding** 🧠
   - Extracts medical info
   - ~3 seconds

4. **Agent 4 - FHIR Format** 📋
   - Converts to standard format
   - ~3 seconds

5. **Agent 5 - Graph Database** 🗄️
   - Stores in Neo4j
   - ~2 seconds

6. **Agent 6 - Analysis** 📊
   - AI generates insights
   - ~5 seconds

**Total: ~17 seconds** for complete processing

---

## 💡 Pro Tips

### View Real-time Logs
Watch the terminal where backend is running - you'll see all API calls!

### Stop the Server
Press `Ctrl + C` in the terminal

### Restart the Server
```bash
python main.py
```

### Test Individual Endpoints
Use Swagger UI at http://localhost:8000/docs
- Click any endpoint
- Click "Try it out"
- Fill in parameters
- Click "Execute"

### Check Server Health
Visit: http://localhost:8000/health

---

## 🚀 Next Steps

1. ✅ Backend running
2. ✅ Frontend running
3. ✅ Both connected
4. 📸 Upload a prescription image
5. 🎉 See the magic happen!

---

## 🆘 Need Help?

**Backend not starting?**
1. Check Python is installed: `python --version`
2. Check venv is activated: Look for `(venv)` in terminal
3. Reinstall dependencies: `pip install -r requirements.txt`

**Frontend can't connect?**
1. Make sure backend is running on port 8000
2. Check terminal for errors
3. Try restarting both servers

**Still stuck?**
1. Check the full README.md
2. Look at server logs in terminal
3. Test endpoints in Swagger UI

---

**You're all set! 🎊**

Your complete healthcare system is now running:
- 🎨 Beautiful React frontend
- ⚡ Powerful FastAPI backend  
- 🤖 AI-powered processing
- 📊 Graph database storage

**Enjoy your project! 🚀**
