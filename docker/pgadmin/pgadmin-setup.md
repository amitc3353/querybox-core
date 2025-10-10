# pgAdmin Setup Guide for QueryBox Core

## 🚀 Quick Access
- **URL**: http://localhost:5050
- **Email**: admin@querybox.local
- **Password**: admin123

## 📋 Step-by-Step Configuration

### 1. First-Time Access
1. Open your browser and navigate to: `http://localhost:5050`
2. You'll see the pgAdmin login screen
3. Enter credentials:
   - **Email**: `admin@querybox.local`
   - **Password**: `admin123`
4. Click "Login"

### 2. Add PostgreSQL Server

#### Method 1: Manual Configuration
1. In the left sidebar, right-click on **"Servers"**
2. Select **"Register" → "Server..."**
3. In the **General** tab:
   - **Name**: `QueryBox-Local` (or any name you prefer)
   - **Server group**: Leave as "Servers"
   - **Connect now?**: Check this box
   - **Background**: Choose a color (optional)
   - **Comments**: Add notes (optional)

4. Switch to the **Connection** tab:
   - **Host name/address**: `querybox-postgres` (⚠️ NOT localhost!)
   - **Port**: `5432`
   - **Maintenance database**: `querybox_core`
   - **Username**: `querybox`
   - **Password**: `querybox_dev_2024`
   - **Save password?**: Check this box
   - **Role**: Leave empty
   - **Service**: Leave empty

5. (Optional) **SSL** tab:
   - **SSL mode**: `Prefer` (default is fine for local dev)

6. (Optional) **Advanced** tab:
   - Leave all defaults

7. Click **"Save"**

#### Method 2: Using Docker Network Name
The key difference from typical setups is that pgAdmin runs inside Docker, so it must use the Docker service name (`querybox-postgres`) instead of `localhost` or `postgres`.

### 3. Verify Connection
After saving, you should see:
- ✅ "QueryBox-Local" server appears under "Servers" in the left sidebar
- ✅ Clicking on it expands to show databases
- ✅ You should see the `querybox_core` database

### 4. Explore Your Database
1. Expand: **QueryBox-Local → Databases → querybox_core → Schemas → public → Tables**
2. You should see your tables:
   - `documents`
   - `document_versions`
   - `processing_status`
   - `embeddings`
   - `processing_queue`

## 🔧 Common Issues & Solutions

### Issue: "Unable to connect to server"
**Solution**: Make sure you're using `querybox-postgres` as the hostname, not `localhost` or `postgres`.

### Issue: "fe_sendauth: no password supplied"
**Solution**: Ensure you've entered the password `querybox_dev_2024` and checked "Save password".

### Issue: pgAdmin won't load at http://localhost:5050
**Solutions**:
1. Check if containers are running: `docker ps`
2. Check pgAdmin logs: `docker logs querybox-pgadmin`
3. Try accessing via IP: `http://127.0.0.1:5050`

### Issue: "Connection timed out"
**Solution**: Ensure both containers are on the same network:
```bash
docker network inspect docker_querybox-network
```

## 🛠️ Useful pgAdmin Features

### Query Tool
- Right-click on `querybox_core` database → **"Query Tool"**
- Run SQL queries directly:
```sql
-- Check all tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';

-- View document count
SELECT COUNT(*) FROM documents;
```

### Table Quick Actions
- Right-click any table for options:
  - **View/Edit Data** → First 100 Rows
  - **Properties** → See table structure
  - **Count Rows** → Get total count

### SQL Export/Import
- Right-click database → **Backup** or **Restore**
- Useful for data migration and backups

## 📝 Docker Commands Reference

```bash
# Start pgAdmin (if not running)
docker compose up -d pgadmin

# Restart pgAdmin
docker restart querybox-pgadmin

# View pgAdmin logs
docker logs querybox-pgadmin

# Stop pgAdmin
docker stop querybox-pgadmin

# Remove pgAdmin data (reset to fresh state)
docker volume rm docker_pgadmin_data
```

## 🔐 Security Note
The current setup is for **development only**. For production:
- Change default passwords
- Use environment variables for credentials
- Enable SSL
- Restrict network access

## 💡 Pro Tips
1. **Bookmark Queries**: Save frequently used queries in pgAdmin
2. **Color Coding**: Use different colors for dev/staging/prod servers
3. **Auto-complete**: Press Ctrl+Space in Query Tool for suggestions
4. **Dashboard**: Click on server name to see real-time statistics