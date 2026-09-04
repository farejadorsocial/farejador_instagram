import os
import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=os.getenv("FAREJADOR_HOST", "127.0.0.1"),
        port=int(os.getenv("FAREJADOR_PORT", "8000")),
        reload=os.getenv("FAREJADOR_RELOAD", "1") == "1",
    )
