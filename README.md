# PA Copilot API

A learning project to build a **Prior Authorization Copilot API** using **FastAPI**, **Postgres**, and eventually **Terraform** for cloud infrastructure.  

This repo is the **backend service** — designed to be deployed separately from its frontend and infrastructure code.

---

## Running Locally

### 1. Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Install dependencies
```
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run the FastAPI app
```
uvicorn app.main:app --reload
```

### 4. Test locally
```
Open:
- Health check: http://127.0.0.1:8000/health
- API docs: http://127.0.0.1:8000/docs
```

