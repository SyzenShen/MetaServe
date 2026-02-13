# 快速启动指南 / Quick Start Guide

## 1. 环境要求 / Requirements
- **Python**: 3.10+
- **Node.js**: 18+

## 2. 首次安装 / First-time Installation
```bash
# 1. 安装前端依赖 Install frontend dependencies
cd frontend
npm install
cd ..

# 2. 安装后端依赖 Install backend dependencies
# (建议在虚拟环境中执行) (Recommended to run in a virtual environment)
pip install django djangorestframework django-cors-headers
```

## 3. 一键启动 / One-click Start
```bash
./scripts/start_services.sh
```

- **前端访问 Frontend Access**: [http://localhost:5173](http://localhost:5173)
- **后端接口 Backend API**: [http://localhost:8020](http://localhost:8020)

## 4. 停止服务 / Stop Services
```bash
./scripts/stop_services.sh
```
