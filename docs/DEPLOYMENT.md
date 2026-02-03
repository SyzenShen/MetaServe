# Deployment Guide

## 1. Prerequisites
- Docker & Docker Compose installed
- Git installed
- Domain name (optional but recommended)

## 2. Environment Setup
Create a `.env.prod` file:
```bash
DEBUG=0
SECRET_KEY=change_me_in_production
DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1]
SQL_ENGINE=django.db.backends.postgresql
SQL_DATABASE=metaserve
SQL_USER=metaserve_user
SQL_PASSWORD=metaserve_password
SQL_HOST=db
SQL_PORT=5432
FILE_UPLOAD_PERMISSIONS=0o644
```

## 3. Build and Run
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

## 4. Post-Deployment Steps
1. **Migrate Database**:
   ```bash
   docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
   ```
2. **Collect Static Files**:
   ```bash
   docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --no-input
   ```
3. **Create Superuser**:
   ```bash
   docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
   ```

## 5. Maintenance
- **Logs**: `docker-compose -f docker-compose.prod.yml logs -f`
- **Backup**: Backup the `postgres_data` volume regularly.
