from fastapi import FastAPI

app = FastAPI(title="Fynd API")

@app.get("/health")
def health_check():
    return {"status": "ok"}
