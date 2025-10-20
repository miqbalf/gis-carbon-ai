/**
 * Script to update MapStore configuration for GeoServer authentication
 * Run this in MapStore's browser console or integrate into your config
 */

// Function to add authentication to WMS requests
function addAuthToWMSRequests() {
    // Override the WMS request function to include authentication
    const originalWMSRequest = window.MapStore2?.plugins?.catalog?.actions?.loadCatalogRecords;
    
    if (originalWMSRequest) {
        window.MapStore2.plugins.catalog.actions.loadCatalogRecords = function(service, options) {
            // Add authentication headers if user is logged in
            const authToken = localStorage.getItem('mapstore_token');
            const geoserverAuth = localStorage.getItem('geoserver_auth');
            
            if (authToken && geoserverAuth) {
                const credentials = JSON.parse(geoserverAuth);
                options = options || {};
                options.auth = {
                    type: 'basic',
                    username: credentials.username,
                    password: credentials.password
                };
            }
            
            return originalWMSRequest.call(this, service, options);
        };
    }
}

// Function to update catalog service configuration
function updateCatalogServices() {
    const catalogServices = {
        "services": [
            {
                "type": "wms",
                "title": "GeoServer - Demo Workspace (Auth Required)",
                "url": "http://localhost:8080/geoserver/demo_workspace/wms",
                "format": "image/png",
                "version": "1.3.0",
                "authRequired": true,
                "authType": "basic"
            },
            {
                "type": "wms", 
                "title": "GeoServer - Public Layers",
                "url": "http://localhost:8080/geoserver/gis_carbon/wms",
                "format": "image/png",
                "version": "1.3.0",
                "authRequired": false
            }
        ]
    };
    
    // Update MapStore configuration
    if (window.ConfigUtils) {
        window.ConfigUtils.setConfigProp('catalogServices', catalogServices);
    }
    
    return catalogServices;
}

// Function to test GeoServer authentication
async function testGeoServerAuth(username, password) {
    try {
        const response = await fetch('http://localhost:8080/geoserver/rest/security/validate-token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + btoa(username + ':' + password)
            },
            body: JSON.stringify({ token: 'test' })
        });
        
        // Even 401 is OK for this test - it means the auth is working
        if (response.status === 401 || response.ok) {
            console.log('✅ GeoServer authentication successful');
            return true;
        } else {
            console.log('❌ GeoServer authentication failed');
            return false;
        }
    } catch (error) {
        console.error('❌ GeoServer authentication error:', error);
        return false;
    }
}

// Function to add layer with authentication
async function addAuthenticatedLayer(layerName, username, password) {
    const wmsUrl = `http://localhost:8080/geoserver/demo_workspace/wms`;
    const layerUrl = `${wmsUrl}?service=WMS&version=1.3.0&request=GetMap&layers=demo_workspace:${layerName}&format=image/png&transparent=true&width=256&height=256&crs=EPSG:4326&bbox=106.8,-6.25,106.9,-6.15`;
    
    try {
        const response = await fetch(layerUrl, {
            headers: {
                'Authorization': 'Basic ' + btoa(username + ':' + password)
            }
        });
        
        if (response.ok) {
            console.log('✅ Layer accessible with authentication');
            return true;
        } else {
            console.log('❌ Layer not accessible:', response.status);
            return false;
        }
    } catch (error) {
        console.error('❌ Error accessing layer:', error);
        return false;
    }
}

// Main function to initialize authentication
function initializeGeoServerAuth() {
    console.log('🔧 Initializing GeoServer authentication for MapStore...');
    
    // Update catalog services
    updateCatalogServices();
    
    // Add auth to WMS requests
    addAuthToWMSRequests();
    
    console.log('✅ GeoServer authentication initialized');
    
    // Test authentication
    testGeoServerAuth('admin', 'admin').then(success => {
        if (success) {
            console.log('🎉 Ready to add authenticated layers!');
        }
    });
}

// Export functions for use
window.GeoServerAuth = {
    initialize: initializeGeoServerAuth,
    testAuth: testGeoServerAuth,
    addLayer: addAuthenticatedLayer,
    updateServices: updateCatalogServices
};

// Auto-initialize when script loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeGeoServerAuth);
} else {
    initializeGeoServerAuth();
}
