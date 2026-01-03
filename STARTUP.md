# 快速启动指南

## 1. 环境要求
- **Python**: 3.10+
- **Node.js**: 18+

## 2. 首次安装
```bash
# 1. 安装前端依赖
cd frontend
npm install
cd ..

# 2. 安装后端依赖
# (建议在虚拟环境中执行)
pip install django djangorestframework django-cors-headers
```

## 3. 一键启动
```bash
./scripts/start_services.sh
```

- **前端访问**: [http://localhost:5173](http://localhost:5173)
- **后端接口**: [http://localhost:8020](http://localhost:8020)

## 4. 停止服务
```bash
./scripts/stop_services.sh
```
