/**
 * Script to programmatically add GeoServer layers to MapStore
 * This can be used to automatically configure MapStore with your GeoServer data
 */

// GeoServer connection configuration
const geoserverConfig = {
    baseUrl: 'http://localhost:8080/geoserver',
    username: 'admin',
    password: 'admin',
    workspace: 'gis_carbon'
};

// Function to get GeoServer capabilities
async function getGeoserverCapabilities() {
    const wmsUrl = `${geoserverConfig.baseUrl}/${geoserverConfig.workspace}/wms?service=WMS&version=1.3.0&request=GetCapabilities`;
    
    try {
        const response = await fetch(wmsUrl);
        const xmlText = await response.text();
        
        // Parse XML to extract layer information
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
        
        const layers = xmlDoc.getElementsByTagName('Layer');
        const layerList = [];
        
        for (let i = 0; i < layers.length; i++) {
            const layer = layers[i];
            const name = layer.getElementsByTagName('Name')[0]?.textContent;
            const title = layer.getElementsByTagName('Title')[0]?.textContent;
            
            if (name && name !== geoserverConfig.workspace) {
                layerList.push({
                    name: name,
                    title: title || name,
                    type: 'wms',
                    url: `${geoserverConfig.baseUrl}/${geoserverConfig.workspace}/wms`,
                    layerName: `${geoserverConfig.workspace}:${name}`
                });
            }
        }
        
        return layerList;
    } catch (error) {
        console.error('Error fetching GeoServer capabilities:', error);
        return [];
    }
}

// Function to add layers to MapStore
function addLayersToMapStore(layers) {
    // This would be called from within MapStore's context
    layers.forEach(layer => {
        // Add WMS layer to MapStore
        const wmsLayer = {
            type: 'wms',
            name: layer.name,
            title: layer.title,
            url: layer.url,
            layers: layer.layerName,
            format: 'image/png',
            transparent: true,
            version: '1.3.0'
        };
        
        // Add to MapStore's layer tree
        // This is a simplified example - actual implementation would use MapStore's API
        console.log('Adding layer to MapStore:', wmsLayer);
    });
}

// Example usage
async function initializeMapStoreWithGeoServer() {
    console.log('Fetching GeoServer layers...');
    const layers = await getGeoserverCapabilities();
    console.log('Found layers:', layers);
    
    if (layers.length > 0) {
        addLayersToMapStore(layers);
        console.log('Successfully added GeoServer layers to MapStore');
    } else {
        console.log('No layers found in GeoServer');
    }
}

// Export for use in MapStore
module.exports = {
    getGeoserverCapabilities,
    addLayersToMapStore,
    initializeMapStoreWithGeoServer,
    geoserverConfig
};

/**
 * Manual Steps to Add GeoServer Layers:
 * 
 * 1. Open MapStore: http://localhost:8082/mapstore
 * 2. Login with admin:admin
 * 3. Click on "Catalog" in the left panel
 * 4. Click "Add Service"
 * 5. Select "WMS" as service type
 * 6. Enter URL: http://localhost:8080/geoserver/gis_carbon/wms
 * 7. Click "Connect"
 * 8. Select the layers you want to add
 * 9. Click "Add to Map"
 * 
 * For WFS layers:
 * 1. Follow same steps but select "WFS" as service type
 * 2. Use URL: http://localhost:8080/geoserver/gis_carbon/wfs
 */
