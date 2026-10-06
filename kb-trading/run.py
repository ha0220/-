"""실행: python run.py  (기본 http://127.0.0.1:8000)"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app_factory", factory=True, host=os.environ.get("KB_HOST", "127.0.0.1"),
                port=int(os.environ.get("KB_PORT", "8000")))
