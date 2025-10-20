# MapStore Admin Interface Setup

## Accessing MapStore Admin

1. **Admin URL**: `http://localhost:8082/mapstore/#/admin`
2. **Default Credentials**: 
   - Username: `admin`
   - Password: `admin`

## Admin Features

### 1. Service Management
- **Add/Edit/Delete WMS/WFS services**
- **Configure authentication**
- **Set default parameters**

### 2. Layer Management
- **Browse all available layers**
- **Configure layer properties**
- **Set default styles**
- **Manage layer groups**

### 3. User Management
- **Create user accounts**
- **Assign roles and permissions**
- **Manage user groups**

## Quick Setup for Your Demo Workspace

### Step 1: Add GeoServer Service
1. Go to **Admin** → **Services**
2. Click **"Add Service"**
3. Select **"WMS"**
4. Configure:
   - **Name**: `Demo Workspace`
   - **URL**: `http://localhost:8080/geoserver/demo_workspace/wms`
   - **Version**: `1.3.0`
   - **Authentication**: Basic
   - **Username**: `admin`
   - **Password**: `admin`

### Step 2: Configure Layer Access
1. Go to **Admin** → **Layers**
2. **Browse layers** from your service
3. **Configure each layer**:
   - Set visibility rules
   - Configure authentication requirements
   - Set default styles

### Step 3: User Role Configuration
1. Go to **Admin** → **Users**
2. **Create test users**:
   - `demo_user` (password: `demo123`)
   - `analyst_user` (password: `analyst123`)
3. **Assign roles**:
   - `demo_user` → `ROLE_AUTHENTICATED`
   - `analyst_user` → `ANALYST`

## Benefits of Admin Interface

✅ **No JSON editing required**
✅ **Visual layer management**
✅ **User-friendly interface**
✅ **Real-time configuration**
✅ **Built-in authentication handling**
