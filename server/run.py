#!/usr/bin/env python3
"""
启动脚本
"""
import uvicorn
from api.config import settings

if __name__ == "__main__":
    uvicorn.run("api.main:app", host=settings.HOST, port=settings.PORT, reload=True, access_log=False)
