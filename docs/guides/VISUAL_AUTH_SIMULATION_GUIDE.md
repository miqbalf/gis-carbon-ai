# 🎯 Visual Authentication Layer Simulation Guide

## 🎬 **Demo Overview**

This guide will help you create a visual demonstration of login vs non-login layers in your GIS Carbon AI system. You'll be able to see the difference between public and private layers visually.

## 📋 **Step-by-Step Setup**

### **Step 1: Prepare Test Data in PostgreSQL**

#### **1.1 Connect to PostgreSQL**
```bash
cd /Users/miqbalf/gis-carbon-ai
docker exec -it gis_postgres_dev psql -U gis_user -d gis_carbon_data
```

#### **1.2 Run the SQL Script**
```sql
-- Copy and paste the contents of setup_test_layers.sql
\i /path/to/setup_test_layers.sql
```

Or run it directly:
```bash
docker exec -i gis_postgres_dev psql -U gis_user -d gis_carbon_data < geoserver/setup_test_layers.sql
```

### **Step 2: Set Up GeoServer Layers**

#### **2.1 Install Python Dependencies**
```bash
cd /Users/miqbalf/gis-carbon-ai
pip install requests
```

#### **2.2 Run the GeoServer Setup Script**
```bash
python geoserver/setup_geoserver_layers.py
```

This will create:
- ✅ **auth_demo** workspace
- ✅ **PostgreSQL data store**
- ✅ **3 test layers** with different access levels
- ✅ **Visual styles** (green for public, red for private)

### **Step 3: Verify Layers in GeoServer**

#### **3.1 Open GeoServer Admin**
- Go to: `http://localhost:8080/geoserver`
- Login: `admin:admin`

#### **3.2 Check Created Layers**
Navigate to **Layers** and verify you see:
- 🌍 **auth_demo:public_sample_geometries** (Green points)
- 🔒 **auth_demo:private_analysis_results** (Red polygons)
- 👑 **auth_demo:admin_system_config** (Admin points)

#### **3.3 Test Layer Access**
Try these URLs in your browser:

**Public Layer (should work without login):**
```
http://localhost:8080/geoserver/auth_demo/wms?service=WMS&version=1.3.0&request=GetMap&layers=auth_demo:public_sample_geometries&format=image/png&width=512&height=512&crs=EPSG:4326&bbox=106.8,-6.25,106.9,-6.15
```

**Private Layer (will show error without auth):**
```
http://localhost:8080/geoserver/auth_demo/wms?service=WMS&version=1.3.0&request=GetMap&layers=auth_demo:private_analysis_results&format=image/png&width=512&height=512&crs=EPSG:4326&bbox=106.8,-6.25,106.9,-6.15
```

### **Step 4: Configure MapStore for Testing**

#### **4.1 Update MapStore Configuration**
Copy the test configuration:
```bash
cp mapstore/mapstore-auth-test-config.json mapstore/localConfig.json
```

#### **4.2 Restart MapStore**
```bash
cd /Users/miqbalf/gis-carbon-ai
docker-compose -f docker-compose.dev.yml restart mapstore
```

### **Step 5: Visual Testing in MapStore**

#### **5.1 Open MapStore**
- Go to: `http://localhost:8082/mapstore`
- You should see the authentication test interface

#### **5.2 Test Without Login (Public Access)**
1. **Don't login** - stay as anonymous user
2. **Open Catalog** panel
3. **Add Service** → **WMS**
4. **URL**: `http://localhost:8080/geoserver/auth_demo/wms`
5. **Connect** and try to add layers

**Expected Result:**
- ✅ **public_sample_geometries** should be available (green points)
- ❌ **private_analysis_results** should be hidden or show error
- ❌ **admin_system_config** should be hidden

#### **5.3 Test With Login (Authenticated Access)**
1. **Click Login** in MapStore
2. **Use test credentials**:
   - Username: `analyst`
   - Password: `analyst123`
3. **Login** and refresh the catalog
4. **Try to add layers again**

**Expected Result:**
- ✅ **public_sample_geometries** should be available (green points)
- ✅ **private_analysis_results** should now be available (red polygons)
- ❌ **admin_system_config** should still be hidden (admin only)

#### **5.4 Test Admin Access**
1. **Logout** and **login as admin**:
   - Username: `admin`
   - Password: `admin123`
2. **Refresh catalog** and try to add layers

**Expected Result:**
- ✅ **public_sample_geometries** should be available (green points)
- ✅ **private_analysis_results** should be available (red polygons)
- ✅ **admin_system_config** should now be available (admin points)

## 🎨 **Visual Indicators**

### **Layer Colors:**
- 🟢 **Green Points**: Public layers (no authentication required)
- 🔴 **Red Polygons**: Private layers (authentication required)
- 🟡 **Yellow Points**: Admin layers (admin access required)

### **Layer Names:**
- 🌍 **Public**: `public_sample_geometries`
- 🔒 **Private**: `private_analysis_results`
- 👑 **Admin**: `admin_system_config`

## 🧪 **Testing Scenarios**

### **Scenario 1: Anonymous User**
```
User: Not logged in
Expected: Only green points visible
Result: ✅/❌
```

### **Scenario 2: Regular User**
```
User: analyst/analyst123
Expected: Green points + red polygons visible
Result: ✅/❌
```

### **Scenario 3: Admin User**
```
User: admin/admin123
Expected: All layers visible (green + red + yellow)
Result: ✅/❌
```

## 🔧 **Troubleshooting**

### **Common Issues:**

1. **Layers not showing in GeoServer**
   - Check if PostgreSQL data was created
   - Verify data store connection
   - Check layer configuration

2. **Authentication not working**
   - Verify JWT configuration
   - Check MapStore authentication settings
   - Test with different user credentials

3. **Layers not visible in MapStore**
   - Check catalog service configuration
   - Verify layer access control settings
   - Test direct WMS URLs

### **Debug Commands:**

```bash
# Check PostgreSQL data
docker exec -it gis_postgres_dev psql -U gis_user -d gis_carbon_data -c "SELECT * FROM auth_demo.public_sample_geometries;"

# Check GeoServer layers
curl -u admin:admin "http://localhost:8080/geoserver/rest/layers"

# Test WMS capabilities
curl "http://localhost:8080/geoserver/auth_demo/wms?service=WMS&version=1.3.0&request=GetCapabilities"
```

## 📊 **Expected Results Summary**

| User Type | Public Layer | Private Layer | Admin Layer |
|-----------|-------------|---------------|-------------|
| Anonymous | ✅ Visible   | ❌ Hidden     | ❌ Hidden   |
| Analyst   | ✅ Visible   | ✅ Visible    | ❌ Hidden   |
| Admin     | ✅ Visible   | ✅ Visible    | ✅ Visible  |

## 🎯 **Next Steps**

After successful testing:
1. **Document the results** of your visual simulation
2. **Take screenshots** of different access levels
3. **Integrate with your FastAPI** authentication system
4. **Deploy to production** with real user data

This visual simulation will help you understand and demonstrate how the authentication system works across all your services!
