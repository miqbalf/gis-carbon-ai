/**
 * MapStore Authentication Setup Script
 * Run this in MapStore's browser console to set up authentication
 */

// Function to set up GeoServer authentication
function setupGeoServerAuth() {
    console.log('🔧 Setting up GeoServer authentication...');
    
    // Store authentication credentials
    const authData = {
        username: 'admin',
        password: 'admin',
        timestamp: Date.now()
    };
    
    localStorage.setItem('geoserver_auth', JSON.stringify(authData));
    localStorage.setItem('mapstore_authenticated', 'true');
    
    console.log('✅ GeoServer authentication configured');
    return authData;
}

// Function to test layer access
async function testLayerAccess() {
    const authData = JSON.parse(localStorage.getItem('geoserver_auth'));
    
    if (!authData) {
        console.log('❌ No authentication data found');
        return false;
    }
    
    const testUrl = `http://${authData.username}:${authData.password}@localhost:8080/geoserver/demo_workspace/wms?service=WMS&version=1.3.0&request=GetMap&layers=demo_workspace:forest_areas&format=image/png&width=256&height=256&crs=EPSG:4326&bbox=106.8,-6.25,106.9,-6.15`;
    
    try {
        const response = await fetch(testUrl);
        if (response.ok) {
            console.log('✅ Layer access test successful');
            return true;
        } else {
            console.log('❌ Layer access test failed:', response.status);
            return false;
        }
    } catch (error) {
        console.log('❌ Layer access test error:', error);
        return false;
    }
}

// Function to add authenticated service to catalog
function addAuthenticatedService() {
    const serviceConfig = {
        type: 'wms',
        title: 'Demo Workspace (Authenticated)',
        url: 'http://admin:admin@localhost:8080/geoserver/demo_workspace/wms',
        format: 'image/png',
        version: '1.3.0',
        authRequired: true
    };
    
    // Store service configuration
    localStorage.setItem('catalog_service_demo', JSON.stringify(serviceConfig));
    
    console.log('✅ Authenticated service added to catalog');
    return serviceConfig;
}

// Function to create a test map with authenticated layer
function createTestMap() {
    const mapConfig = {
        version: 2,
        map: {
            center: { x: 106.8, y: -6.25, crs: 'EPSG:4326' },
            zoom: 10,
            layers: [
                {
                    type: 'osm',
                    title: 'OpenStreetMap',
                    name: 'osm',
                    visibility: true
                },
                {
                    type: 'wms',
                    name: 'forest_areas',
                    title: '🌲 Forest Areas (Demo)',
                    url: 'http://admin:admin@localhost:8080/geoserver/demo_workspace/wms',
                    layers: 'forest_areas',
                    format: 'image/png',
                    transparent: true,
                    visibility: true
                }
            ]
        }
    };
    
    // Store map configuration
    localStorage.setItem('test_map_authenticated', JSON.stringify(mapConfig));
    
    console.log('✅ Test map with authenticated layer created');
    return mapConfig;
}

// Main setup function
async function setupMapStoreAuth() {
    console.log('🚀 Starting MapStore authentication setup...');
    
    try {
        // 1. Set up authentication
        setupGeoServerAuth();
        
        // 2. Test layer access
        const accessTest = await testLayerAccess();
        
        if (accessTest) {
            // 3. Add authenticated service
            addAuthenticatedService();
            
            // 4. Create test map
            createTestMap();
            
            console.log('🎉 MapStore authentication setup complete!');
            console.log('📋 Next steps:');
            console.log('1. Refresh the page');
            console.log('2. Go to Catalog');
            console.log('3. Look for "Demo Workspace (Authenticated)" service');
            console.log('4. Add the forest_areas layer');
            
        } else {
            console.log('❌ Authentication setup failed - check GeoServer connection');
        }
        
    } catch (error) {
        console.error('❌ Setup error:', error);
    }
}

// Auto-run setup
if (typeof window !== 'undefined') {
    window.setupMapStoreAuth = setupMapStoreAuth;
    console.log('🔧 MapStore auth setup script loaded. Run setupMapStoreAuth() to configure authentication.');
}
