from fastapi import FastAPI

app = FastAPI(title="Smart Home Vulnerability Manager")

@app.get("/api/health")
def health_check():
    return {"status": "ok"}