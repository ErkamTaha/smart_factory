# 🏭 Smart Factory Complete Setup Guide

## 🎯 **Project Overview**

Your Smart Factory has been completely restructured and containerized with:

### ✅ **What's Fixed:**
- **Proper Project Structure** - Backend and frontend separated
- **Database Integration** - PostgreSQL replaces JSON files  
- **Full Containerization** - Docker setup for all services
- **Development Environment** - Hot reload and debugging
- **Production Ready** - Optimized builds and deployment

---

## 📁 **Project Structure**

```
smart_factory/
├── 📁 backend/              # Python FastAPI Backend
│   ├── 📁 app/
│   │   ├── 📁 models/       # Database models (ACL, SS, MQTT)
│   │   ├── 📁 routes/       # API endpoints
│   │   ├── 📁 security/     # ACL & SS managers
│   │   ├── 📁 mqtt/         # MQTT clients
│   │   ├── 📁 websocket/    # WebSocket manager
│   │   ├── 📁 database/     # Database setup
│   │   ├── config.py        # Configuration
│   │   └── main.py          # Application entry
│   ├── Dockerfile           # Backend container
│   ├── requirements.txt     # Python dependencies
│   └── .env.example         # Environment template
│
├── 📁 frontend/             # Vue.js Frontend
│   ├── 📁 src/
│   │   ├── 📁 components/   # Dashboard, MQTT Test
│   │   ├── 📁 services/     # API & WebSocket services
│   │   └── 📁 stores/       # State management
│   ├── Dockerfile           # Frontend container
│   ├── package.json         # Node dependencies
│   ├── vite.config.js       # Build configuration
│   └── nginx.conf           # Production web server
│
├── 📁 infrastructure/       # Docker & deployment
│   └── 📁 mosquitto/config/ # MQTT broker config
│
├── docker-compose.yml       # Development setup
├── docker-compose.prod.yml  # Production setup
├── Makefile                 # Development commands
└── README.md                # This guide
```

---

## 🚀 **Quick Start (5 Minutes)**

### **Prerequisites:**
- ✅ Docker installed ([Install Docker Guide](https://docs.docker.com/get-docker/))
- ✅ Docker Compose installed
- ✅ 8GB+ RAM available
- ✅ Ports 3000, 8000, 5432, 1883, 8080 free

### **Step 1: Get the Code**
```bash
# Clone your updated project (or download the files)
git clone https://github.com/YourUsername/smart_factory.git
cd smart_factory
```

### **Step 2: Start Everything**
```bash
# Start all services with one command!
make up-dev

# Alternative if make is not available:
docker-compose up -d
```

### **Step 3: Access Your Application**
- 🎮 **Frontend Dashboard**: http://localhost:3000
- 🔧 **Backend API**: http://localhost:8000
- 📊 **API Documentation**: http://localhost:8000/docs
- 🗄️ **Database Admin**: http://localhost:8080
- ❤️ **Health Check**: http://localhost:8000/api/health

---

## 🔍 **What Happens on Startup**

### **1. Services Start in Order:**
```
1️⃣ PostgreSQL Database    (port 5432)
2️⃣ MQTT Broker           (ports 1883, 9001) 
3️⃣ Redis Cache           (port 6379)
4️⃣ Backend API           (port 8000)
5️⃣ Frontend Web App      (port 3000)
6️⃣ pgAdmin Interface     (port 8080)
```

### **2. Database Auto-Setup:**
- ✅ Creates all tables (ACL, SS, MQTT data)
- ✅ Inserts default users (alice, bob, charlie, dave, eve, erkam)
- ✅ Creates default roles (admin, operator, viewer, device_owner)
- ✅ Sets up sensor security rules

### **3. Your Data Migration:**
- ✅ **ACL data** from `acl_config.json` → PostgreSQL tables
- ✅ **SS data** from `ss_config.json` → PostgreSQL tables  
- ✅ **MQTT data** from memory → PostgreSQL persistence

---

## 🛠️ **Development Commands**

### **Essential Commands:**
```bash
# Start development environment
make up-dev

# View all logs
make logs

# View specific service logs
make logs-be    # Backend logs
make logs-fe    # Frontend logs
make logs-db    # Database logs

# Stop everything
make down

# Shell access
make shell-be   # Backend container shell
make shell-db   # Database shell

# Check status
make status
```

### **Database Operations:**
```bash
# Initialize fresh database
make db-init

# Create backup
make db-backup

# Reset database (WARNING: deletes all data)
make db-reset

# Restore from backup
make db-restore
```

---

## 🗄️ **PostgreSQL Integration Details**

### **What's Stored in Database:**

#### **🔐 ACL (Access Control) Tables:**
```sql
acl_users         -- User accounts and settings
acl_roles         -- Role definitions (admin, operator, etc.)
acl_user_roles    -- User-role assignments  
acl_config        -- System configuration
acl_audit_logs    -- Complete audit trail
```

#### **🛡️ SS (Sensor Security) Tables:**
```sql
ss_sensors        -- Sensor definitions and limits
ss_sensor_types   -- Temperature, humidity, etc.
ss_sensor_limits  -- Upper/lower thresholds
ss_alerts         -- Alert history and tracking
ss_config         -- Security configuration
```

#### **📡 MQTT Data Tables:**
```sql
mqtt_devices      -- Device registry and metadata
mqtt_sensor_readings  -- All sensor data (persistent!)
mqtt_commands     -- Command history and tracking
mqtt_sessions     -- User session management
mqtt_topic_stats  -- Usage analytics
```

### **Database Access:**
```bash
# Direct SQL access
make shell-db

# Web interface (pgAdmin)
# URL: http://localhost:8080
# Email: admin@smartfactory.local  
# Password: admin123

# Connection details for external tools:
Host: localhost
Port: 5432
Database: smartfactory
Username: smartfactory
Password: password123
```

---

## 🌐 **API Endpoints**

### **System Status:**
- `GET /` - Service status and features
- `GET /api/health` - Comprehensive health check
- `GET /api/database/status` - Database connection and table counts

### **ACL Management:**
- `GET /api/acl/info` - ACL configuration info
- `GET /api/acl/users` - List all users
- `POST /api/acl/users` - Create new user
- `PUT /api/acl/users/{user_id}` - Update user
- `DELETE /api/acl/users/{user_id}` - Delete user
- `POST /api/acl/check` - Check permissions

### **Sensor Security:**
- `GET /api/ss/info` - SS configuration info
- `GET /api/ss/sensors` - List all sensors
- `POST /api/ss/check` - Check sensor limits
- `POST /api/ss/sensors` - Add new sensor

### **IoT Data:**
- `GET /api/iot/devices` - List all devices
- `GET /api/iot/data/{device_id}` - Get device data
- `POST /api/iot/data` - Publish sensor data
- `POST /api/iot/command` - Send device command
- `GET /api/iot/latest` - Latest sensor readings

---

## 🧪 **Testing Your Setup**

### **1. Backend Health Check:**
```bash
curl http://localhost:8000/api/health
# Should return: {"status": "ok", "database": "connected", ...}
```

### **2. Database Check:**
```bash
curl http://localhost:8000/api/database/status
# Should show table counts
```

### **3. Frontend Access:**
```bash
curl http://localhost:3000
# Should return HTML page
```

### **4. Send Test Sensor Data:**
```bash
curl -X POST http://localhost:8000/api/iot/data \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test_device_001",
    "sensor_type": "temperature", 
    "value": 25.5,
    "unit": "C"
  }'
```

### **5. Check ACL Users:**
```bash
curl http://localhost:8000/api/acl/users
# Should return alice, bob, charlie, dave, eve, erkam
```

---

## 🚀 **Production Deployment**

### **Environment Setup:**
```bash
# Create production environment file
cp backend/.env.example backend/.env

# Edit with production values:
nano backend/.env
```

### **Production Environment Variables:**
```bash
DATABASE_URL=postgresql://user:secure_password@prod-db:5432/smartfactory
SECRET_KEY=your-super-secure-secret-key-here
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
POSTGRES_PASSWORD=secure_database_password
REDIS_PASSWORD=secure_redis_password
```

### **Start Production:**
```bash
# Start production environment
make up-prod

# Or manually:
docker-compose -f docker-compose.prod.yml up -d
```

### **Production Features:**
- ✅ **Optimized Docker images** (smaller, faster)
- ✅ **Security hardening** (non-root users, health checks)
- ✅ **Nginx reverse proxy** (SSL, caching, compression)
- ✅ **Resource limits** and auto-restart policies
- ✅ **Production logging** and monitoring

---

## 🔧 **Configuration**

### **Backend Configuration (`backend/app/config.py`):**
```python
# Database
database_url: str = "postgresql://..."

# MQTT
mqtt_broker_host: str = "mosquitto"
mqtt_broker_port: int = 1883

# Security
secret_key: str = "change-in-production"
allowed_origins: List[str] = ["http://localhost:3000"]
```

### **Frontend Configuration (`frontend/vite.config.js`):**
```javascript
server: {
  proxy: {
    '/api': 'http://backend:8000',
    '/ws': 'ws://backend:8000'
  }
}
```

---

## 📊 **Monitoring and Logs**

### **Application Logs:**
```bash
# Real-time logs
docker-compose logs -f

# Service-specific logs
docker-compose logs backend
docker-compose logs postgres
docker-compose logs mosquitto
```

### **Database Monitoring:**
```sql
-- Table sizes
SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size 
FROM pg_tables WHERE schemaname = 'public';

-- Recent sensor activity
SELECT device_id, COUNT(*) as readings, MAX(timestamp) as latest 
FROM mqtt_sensor_readings 
WHERE timestamp > NOW() - INTERVAL '1 hour' 
GROUP BY device_id;

-- Active user sessions  
SELECT user_id, connected_at, is_active 
FROM mqtt_sessions 
WHERE is_active = true;
```

---

## 🔒 **Security Features**

### **✅ Implemented Security:**
- **Database ACL** with role-based permissions
- **MQTT Authentication** and topic-level access control
- **Sensor Security** with configurable limits and alerts
- **Audit Logging** for all permission checks and actions
- **Input Validation** with Pydantic models
- **CORS Configuration** for frontend security
- **Health Checks** for service monitoring

### **🔐 Production Security Checklist:**
- [ ] Change all default passwords
- [ ] Use environment variables for secrets
- [ ] Enable HTTPS with SSL certificates
- [ ] Set up firewall rules
- [ ] Configure log rotation and retention
- [ ] Set up monitoring and alerting
- [ ] Regular database backups
- [ ] Security scanning of Docker images

---

## 🚨 **Troubleshooting**

### **Common Issues:**

#### **Port Already in Use:**
```bash
# Check what's using the port
lsof -i :3000
lsof -i :8000
lsof -i :5432

# Stop conflicting services or change ports in docker-compose.yml
```

#### **Database Connection Failed:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Reset database
make db-reset
```

#### **Frontend Can't Connect to Backend:**
```bash
# Check backend is running
curl http://localhost:8000/api/health

# Check proxy configuration in vite.config.js
# Ensure CORS origins include frontend URL
```

#### **MQTT Connection Issues:**
```bash
# Check Mosquitto logs
docker-compose logs mosquitto

# Test MQTT connection
docker-compose exec mosquitto mosquitto_sub -h localhost -t 'test' -v
```

#### **Out of Memory:**
```bash
# Check Docker resource usage
docker stats

# Free up space
make clean

# Increase Docker memory limits in Docker Desktop
```

---

## 📁 **File Locations**

All files are organized in the new structure:

1. **[smart_factory/](computer:///mnt/user-data/outputs/smart_factory/)** - Complete project root
2. **[backend/](computer:///mnt/user-data/outputs/smart_factory/backend/)** - Python FastAPI backend
3. **[frontend/](computer:///mnt/user-data/outputs/smart_factory/frontend/)** - Vue.js frontend  
4. **[docker-compose.yml](computer:///mnt/user-data/outputs/smart_factory/docker-compose.yml)** - Development setup
5. **[Makefile](computer:///mnt/user-data/outputs/smart_factory/Makefile)** - Development commands

---

## 🎉 **What You've Achieved**

### **Before → After:**

| **Aspect** | **Before** | **After** |
|------------|------------|-----------|
| **Structure** | Mixed files in one directory | Proper backend/frontend separation |
| **Data Storage** | JSON files + in-memory | PostgreSQL database |
| **Development** | Manual setup, no containers | Docker containerization |
| **Frontend** | Single Vue files | Proper Vue.js project structure |
| **Backend** | Basic FastAPI setup | Enterprise-grade structure |
| **Database** | File-based ACL/SS | Database ACL/SS with audit logs |
| **MQTT Data** | Lost on restart | Persistent storage |
| **Deployment** | Manual process | Single command deployment |
| **Scaling** | Limited | Horizontally scalable |
| **Monitoring** | Basic logs | Health checks, metrics, admin tools |

Your Smart Factory is now **enterprise-ready** with proper architecture, data persistence, and scalable deployment! 🏭✨

**Next Steps:**
1. Run `make up-dev` to start your new system
2. Access the dashboard at http://localhost:3000  
3. Check the health endpoint at http://localhost:8000/api/health
4. Explore the database at http://localhost:8080

Welcome to Smart Factory 3.0! 🚀
