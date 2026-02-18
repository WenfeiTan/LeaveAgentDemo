from fastapi import FastAPI

from routers.directory import router as directory_router
from routers.leave_balances import router as leave_balances_router
from routers.cases import router as cases_router

app = FastAPI(title="HR Agent Day1 API", version="0.1.0")

app.include_router(directory_router)
app.include_router(leave_balances_router)
app.include_router(cases_router)


@app.get("/health")
def health():
    return {"status": "ok"}
