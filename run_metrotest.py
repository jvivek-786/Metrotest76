import os
import sys
import uvicorn

if __name__ == "__main__":
    # Ensure current directory is on python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        
    port = int(os.getenv("PORT", 10000))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting MetroTest-76 (SIH26035) Server on http://{host}:{port}")
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)
