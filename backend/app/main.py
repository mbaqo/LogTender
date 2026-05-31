from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.router import api_router


app = FastAPI(
    title="LogTender API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

#  Recommended route placement going forward:

#   - Put HTTP endpoints in backend/app/api/routes/
#   - Keep one file per domain:
#       - users.py
#       - students.py
#       - guardians.py
#       - attendance.py
#       - pin_resets.py

#   - Keep shared router aggregation in backend/app/api/router.py
#   - Keep FastAPI app wiring in backend/app/main.py
#   - Keep database logic in backend/app/crud.py