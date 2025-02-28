from core.orm import create_db_and_tables
from core import app
import uvicorn

app = app

if __name__ == "__main__":
    create_db_and_tables()
    uvicorn.run("core:app", host="0.0.0.0", port=8000, reload=True)