# 📋 Deployment Information Required

To deploy your FastAPI application to your existing server, please gather the following information and update the `scripts/deploy_to_existing_server.sh` script.

## 🔧 **Configuration Required**

### 1. **Basic Project Settings**

```bash
PROJECT_NAME="your-project-name"           # Used for service names, directories
DOMAIN="yourdomain.com"                    # Your domain name
EMAIL="your-email@example.com"             # For SSL certificates
```

### 2. **Repository Access**

**For Private Repository:**

**Option A: GitHub Token (Recommended)**

```bash
REPO_URL="https://github.com/username/repo.git"
GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"    # Generate at: github.com/settings/tokens
```

**Option B: SSH Key**

```bash
REPO_URL="git@github.com:username/repo.git"
USE_SSH=true
# Make sure your server has SSH key access to the repo
```

**For Public Repository:**

```bash
REPO_URL="https://github.com/username/repo.git"
# Leave GITHUB_TOKEN empty
```

### 3. **Database Configuration**

```bash
DB_HOST="localhost"                        # Your PostgreSQL host
DB_PORT="5432"                            # PostgreSQL port
DB_NAME="your_database_name"              # Database name
DB_USER="your_db_username"                # Database user
DB_PASSWORD="your_secure_password"        # Database password
```

### 4. **Application Settings**

```bash
APP_USER="fastapi"                        # User to run the app (will be created)
PORT="8000"                               # Port for this app (ensure it's free)
WORKERS="auto"                            # Number of workers (auto = CPU cores * 2 + 1)
```

## 🔐 **How to Get GitHub Token (for Private Repos)**

1. Go to [GitHub Settings > Developer Settings > Personal Access Tokens](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Give it a name like "Production Deployment"
4. Select scopes: `repo` (Full control of private repositories)
5. Click "Generate token"
6. **Copy the token immediately** (you won't see it again)

## 📂 **Prerequisites on Your Server**

Make sure your server has:

- ✅ **Nginx** installed and running with other sites
- ✅ **PostgreSQL** installed and running
- ✅ **Python 3.8+** installed
- ✅ **Git** installed
- ✅ Database created with proper user permissions

## 🚀 **Quick Setup Steps**

1. **Update the script configuration:**

   ```bash
   nano scripts/deploy_to_existing_server.sh
   # Edit the configuration section at the top
   ```

2. **Make it executable:**

   ```bash
   chmod +x scripts/deploy_to_existing_server.sh
   ```

3. **Run deployment:**
   ```bash
   sudo scripts/deploy_to_existing_server.sh deploy
   ```

## 📋 **Example Configuration**

Here's a complete example of what to fill in:

```bash
# Project Configuration
PROJECT_NAME="myapi"
DOMAIN="api.mycompany.com"
EMAIL="admin@mycompany.com"

# Repository Configuration
REPO_URL="https://github.com/mycompany/fastapi-backend.git"
REPO_BRANCH="main"
GITHUB_TOKEN="ghp_1234567890abcdef1234567890abcdef12345678"

# Database Configuration
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="myapi_production"
DB_USER="myapi_user"
DB_PASSWORD="super_secure_password_123"

# Server Configuration
APP_USER="myapi"
APP_DIR="/opt/myapi"
PORT="8001"  # Different port since you have other sites
```

## 🔍 **What the Script Will Do**

1. **Clone your repository** from GitHub (private or public)
2. **Create application user** and directory structure
3. **Setup Python virtual environment** and install dependencies
4. **Create optimized Gunicorn configuration**
5. **Create systemd service** for process management
6. **Setup Nginx configuration** that integrates with your existing setup
7. **Configure SSL certificates** with Let's Encrypt
8. **Setup automated database backups**
9. **Create management scripts** for easy deployment updates

## ⚡ **Performance Expectations**

- **2000+ requests/second** with proper server resources
- **Sub-100ms response times** for most endpoints
- **Automatic scaling** with multiple Gunicorn workers
- **Zero-downtime deployments** with graceful restarts

## 🛡️ **Security Features Included**

- ✅ Rate limiting per endpoint
- ✅ Security headers and HTTPS enforcement
- ✅ Process isolation and privilege dropping
- ✅ Input validation and sanitization
- ✅ Automated security updates via systemd

## 📊 **Monitoring & Logs**

After deployment, you'll have:

- **Service status**: `sudo systemctl status myapi.service`
- **Live logs**: `sudo journalctl -u myapi.service -f`
- **Health checks**: `curl http://yourdomain.com/health/health`
- **Nginx logs**: `/var/log/nginx/myapi_*.log`

## 💡 **Tips**

1. **Test locally first** - Make sure your app runs with the current repository state
2. **Database ready** - Ensure PostgreSQL is set up with the database and user created
3. **Port availability** - Check that your chosen port isn't in use: `sudo netstat -tlnp | grep :8000`
4. **Domain setup** - Point your domain to your server's IP before running
5. **Backup** - Consider backing up your current nginx configuration first

Once you have all this information, just update the script and run it! 🚀
