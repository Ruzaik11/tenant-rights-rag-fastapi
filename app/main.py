from fastapi import FastAPI

app = FastAPI(title="Tenant Rights Helper")


@app.get("/health")
def health():
    return {"status": "ok"}
