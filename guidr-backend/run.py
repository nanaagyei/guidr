"""Script to start the backend server."""

import uvicorn
from src.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

    print("Backend server started on port 8000")

