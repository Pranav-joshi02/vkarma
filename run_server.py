"""
3D Cadastral Registry & 3D ULPIN Platform - Unified Server Runner
Runs FastAPI with Uvicorn and pre-initializes the default pilot cadastre.
"""

import uvicorn
import os
import sys

# Ensure project root is in python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import socket

if __name__ == "__main__":
    print("==================================================================")
    print(" [3D Cadastral Registry & 3D ULPIN System - Government of India] ")
    print(" ISO 19152 (LADM) Compliant Land Administration Digital Twin     ")
    port = int(os.getenv("PORT", 8000))
    print(" Starting WebGIS and REST API server on port:")
    print(f"   -> http://localhost:{port}")
    print(f"   -> http://127.0.0.1:{port}")
    print("==================================================================")

    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        sock.bind(('::', port))
        sock.listen(128)
        config = uvicorn.Config("backend.app:app", port=port, log_level="info")
        server = uvicorn.Server(config)
        server.run(sockets=[sock])
    except Exception as e:
        print(f"Dual-stack notice: {e}. Falling back to standard bind...")
        uvicorn.run("backend.app:app", host="0.0.0.0", port=port, reload=False)


