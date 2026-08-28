Here are the step-by-step instructions to run the TwinStock AI project locally on your machine.

Option 1: One-Command Launcher (Recommended & Easiest)
Open your terminal in the project root directory (c:\Users\R S Prathvir\Desktop\projects\problemstatement) and run:

bash
python start.py
This single command will automatically:

Clear any zombie process locks on ports 8000, 8001, and 8080.
Start the ML Forecasting Service on http://127.0.0.1:8001.
Start the Backend FastAPI Server on http://127.0.0.1:8000 (auto-creates the SQLite database and seeds 3,200+ inventory items).
Start the Frontend Web Server on http://127.0.0.1:8080.
🔗 Accessing the Application:
Landing / Role Selection: http://127.0.0.1:8080/index.html
Manager Dashboard: http://127.0.0.1:8080/manager.html
Worker Dashboard: http://127.0.0.1:8080/worker.html
Backend API Interactive Docs: http://127.0.0.1:8000/docs
To stop all services, press Ctrl + C in the terminal.

Option 2: Running Services Manually (Separate Terminals)
If you prefer to inspect logs for each service individually, open 3 separate terminal windows:

Terminal 1: ML Service
bash
cd ml-service
python -m uvicorn app:app --host 127.0.0.1 --port 8001
Terminal 2: Backend API
bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Terminal 3: Frontend Web Server
bash
cd frontend
python dev_server.py
Then open http://127.0.0.1:8080/index.html in your browser!



# 1. ML Service (Node.js)
cd ml-service
npm run start

# 2. Backend API (Python)
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 3. Frontend Web (Node.js)
cd frontend
npm run dev
