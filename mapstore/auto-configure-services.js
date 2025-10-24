#!/usr/bin/env node
/**
 * Auto-configure MapStore with GeoServer and FastAPI services
 * This script runs during container startup to automatically add services
 */

const fs = require('fs');
const path = require('path');

// Service configurations
const SERVICES_CONFIG = {
    geoserver_gis_carbon: {
        name: 'GeoServer GIS Carbon WMS/WFS',
        type: 'wms',
        url: 'http://localhost:8080/geoserver/gis_carbon/wms',
        wfsUrl: 'http://localhost:8080/geoserver/gis_carbon/wfs',
        version: '1.3.0',
        format: 'image/png',
        transparent: true,
        authRequired: false,
        description: 'Local GeoServer WMS/WFS service for GIS Carbon data'
    },
    geoserver_demo: {
        name: 'GeoServer Demo WMS/WFS',
        type: 'wms',
        url: 'http://localhost:8080/geoserver/demo_workspace/wms',
        wfsUrl: 'http://localhost:8080/geoserver/demo_workspace/wfs',
        version: '1.3.0',
        format: 'image/png',
        transparent: true,
        authRequired: false,
        description: 'Local GeoServer WMS/WFS service for demo data'
    },
    fastapi: {
        name: 'GEE Analysis Layers',
        type: 'tile',
        url: 'http://localhost:8001/tiles/gee/{layer_name}/{z}/{x}/{y}',
        format: 'image/png',
        transparent: true,
        tileSize: 256,
        authRequired: false,
        description: 'Google Earth Engine analysis layers from FastAPI service'
    }
};

// Default layers to add
const DEFAULT_LAYERS = [
    {
        name: 'geoserver_sample',
        title: 'GIS Carbon Sample Layer',
        type: 'wms',
        url: 'http://localhost:8080/geoserver/gis_carbon/wms',
        layers: 'gis_carbon:sample_geometries',
        format: 'image/png',
        transparent: true,
        version: '1.3.0',
        visibility: true
    },
    {
        name: 'demo_sample',
        title: 'Demo Workspace Sample Layer',
        type: 'wms',
        url: 'http://localhost:8080/geoserver/demo_workspace/wms',
        layers: 'demo_workspace:sample_geometries',
        format: 'image/png',
        transparent: true,
        version: '1.3.0',
        visibility: false
    }
];

/**
 * Load MapStore configuration
 */
function loadMapStoreConfig() {
    const configPath = '/usr/local/tomcat/webapps/mapstore/configs/localConfig.json';
    const defaultConfigPath = '/usr/local/tomcat/webapps/mapstore/configs/default-localConfig.json';
    
    try {
        // First try to load existing configuration
        if (fs.existsSync(configPath)) {
            const configData = fs.readFileSync(configPath, 'utf8');
            const config = JSON.parse(configData);
            console.log('📋 Loaded existing MapStore configuration');
            return config;
        }
        
        // If no existing config, try to load default configuration
        if (fs.existsSync(defaultConfigPath)) {
            const defaultConfigData = fs.readFileSync(defaultConfigPath, 'utf8');
            const defaultConfig = JSON.parse(defaultConfigData);
            console.log('📋 Loaded default MapStore configuration');
            return defaultConfig;
        }
    } catch (error) {
        console.error('Error loading MapStore config:', error);
    }
    
    // Return minimal configuration if no files exist
    console.log('📋 Creating minimal MapStore configuration');
    return {
        map: {
            layers: [],
            projection: 'EPSG:3857',
            center: { x: 106.8456, y: -6.2088, crs: 'EPSG:4326' },
            zoom: 10
        },
        catalogServices: {
            services: []
        },
        authentication: {
            type: 'local',
            loginForm: {
                enabled: true,
                title: 'GIS Carbon AI Login'
            }
        }
    };
}

/**
 * Save MapStore configuration
 */
function saveMapStoreConfig(config) {
    const configPath = '/usr/local/tomcat/webapps/mapstore/configs/localConfig.json';
    const configDir = path.dirname(configPath);
    
    try {
        // Ensure config directory exists
        if (!fs.existsSync(configDir)) {
            fs.mkdirSync(configDir, { recursive: true });
        }
        
        // Write configuration
        fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
        console.log('✅ MapStore configuration saved successfully');
        return true;
    } catch (error) {
        console.error('❌ Error saving MapStore config:', error);
        return false;
    }
}

/**
 * Add services to MapStore configuration
 */
function addServicesToConfig(config) {
    console.log('🔧 Adding services to MapStore configuration...');
    
    // Ensure catalogServices exists
    if (!config.catalogServices) {
        config.catalogServices = { services: [] };
    }
    if (!config.catalogServices.services) {
        config.catalogServices.services = [];
    }
    
    // Preserve existing authentication configuration
    const existingAuth = config.authentication || {};
    console.log('🔐 Preserving existing authentication configuration');
    
    // Add GeoServer GIS Carbon service
    const geoserverGisCarbonService = {
        type: SERVICES_CONFIG.geoserver_gis_carbon.type,
        title: SERVICES_CONFIG.geoserver_gis_carbon.name,
        url: SERVICES_CONFIG.geoserver_gis_carbon.url,
        version: SERVICES_CONFIG.geoserver_gis_carbon.version,
        format: SERVICES_CONFIG.geoserver_gis_carbon.format,
        transparent: SERVICES_CONFIG.geoserver_gis_carbon.transparent,
        authRequired: SERVICES_CONFIG.geoserver_gis_carbon.authRequired,
        description: SERVICES_CONFIG.geoserver_gis_carbon.description
    };
    
    // Add GeoServer Demo service
    const geoserverDemoService = {
        type: SERVICES_CONFIG.geoserver_demo.type,
        title: SERVICES_CONFIG.geoserver_demo.name,
        url: SERVICES_CONFIG.geoserver_demo.url,
        version: SERVICES_CONFIG.geoserver_demo.version,
        format: SERVICES_CONFIG.geoserver_demo.format,
        transparent: SERVICES_CONFIG.geoserver_demo.transparent,
        authRequired: SERVICES_CONFIG.geoserver_demo.authRequired,
        description: SERVICES_CONFIG.geoserver_demo.description
    };
    
    // Add FastAPI service
    const fastapiService = {
        type: SERVICES_CONFIG.fastapi.type,
        title: SERVICES_CONFIG.fastapi.name,
        url: SERVICES_CONFIG.fastapi.url,
        format: SERVICES_CONFIG.fastapi.format,
        transparent: SERVICES_CONFIG.fastapi.transparent,
        tileSize: SERVICES_CONFIG.fastapi.tileSize,
        authRequired: SERVICES_CONFIG.fastapi.authRequired,
        description: SERVICES_CONFIG.fastapi.description
    };
    
    // Check if services already exist and update or add them
    let geoserverGisCarbonExists = false;
    let geoserverDemoExists = false;
    let fastapiExists = false;
    
    // Convert services to array format if it's an object
    if (config.catalogServices.services && !Array.isArray(config.catalogServices.services)) {
        // Convert object to array
        const servicesArray = Object.values(config.catalogServices.services);
        config.catalogServices.services = servicesArray;
        console.log('  🔄 Converted services from object to array format');
    }
    
    // Handle services as array (correct MapStore format)
    config.catalogServices.services.forEach((service, index) => {
        if (service.title === SERVICES_CONFIG.geoserver_gis_carbon.name) {
            config.catalogServices.services[index] = geoserverGisCarbonService;
            geoserverGisCarbonExists = true;
            console.log('  🔄 Updated existing GeoServer GIS Carbon service');
        }
        if (service.title === SERVICES_CONFIG.geoserver_demo.name) {
            config.catalogServices.services[index] = geoserverDemoService;
            geoserverDemoExists = true;
            console.log('  🔄 Updated existing GeoServer Demo service');
        }
        if (service.title === SERVICES_CONFIG.fastapi.name) {
            config.catalogServices.services[index] = fastapiService;
            fastapiExists = true;
            console.log('  🔄 Updated existing FastAPI service');
        }
    });
    
    if (!geoserverGisCarbonExists) {
        config.catalogServices.services.push(geoserverGisCarbonService);
        console.log('  ➕ Added GeoServer GIS Carbon service');
    }
    
    if (!geoserverDemoExists) {
        config.catalogServices.services.push(geoserverDemoService);
        console.log('  ➕ Added GeoServer Demo service');
    }
    
    if (!fastapiExists) {
        config.catalogServices.services.push(fastapiService);
        console.log('  ➕ Added FastAPI service');
    }
    
    // Restore authentication configuration
    if (Object.keys(existingAuth).length > 0) {
        config.authentication = { ...existingAuth };
        console.log('🔐 Restored authentication configuration');
    }
    
    return config;
}

/**
 * Add default layers to MapStore configuration
 */
function addDefaultLayers(config) {
    console.log('🗺️ Adding default layers to MapStore...');
    
    // Ensure map.layers exists
    if (!config.map) {
        config.map = {};
    }
    if (!config.map.layers) {
        config.map.layers = [];
    }
    
    // Remove existing default layers to avoid duplicates
    config.map.layers = config.map.layers.filter(layer => 
        !DEFAULT_LAYERS.some(defaultLayer => defaultLayer.name === layer.name)
    );
    
    // Add default layers
    DEFAULT_LAYERS.forEach(layer => {
        config.map.layers.push(layer);
        console.log(`  ➕ Added layer: ${layer.title}`);
    });
    
    return config;
}

/**
 * Wait for services to be ready
 */
async function waitForServices() {
    console.log('⏳ Waiting for services to be ready...');
    
    const services = [
        { name: 'GeoServer', url: 'http://geoserver:8080/geoserver/rest/about/version.json' },
        { name: 'FastAPI', url: 'http://fastapi:8000/health' }
    ];
    
    for (const service of services) {
        let attempts = 0;
        const maxAttempts = 30;
        
        while (attempts < maxAttempts) {
            try {
                const response = await fetch(service.url);
                if (response.ok) {
                    console.log(`  ✅ ${service.name} is ready`);
                    break;
                }
            } catch (error) {
                // Service not ready yet
            }
            
            attempts++;
            if (attempts < maxAttempts) {
                console.log(`  ⏳ ${service.name} not ready yet (attempt ${attempts}/${maxAttempts})...`);
                await new Promise(resolve => setTimeout(resolve, 2000));
            } else {
                console.log(`  ⚠️ ${service.name} not ready after ${maxAttempts} attempts, continuing anyway...`);
            }
        }
    }
}

/**
 * Merge unified SSO configuration if available
 */
function mergeUnifiedSSOConfig(config) {
    const unifiedConfigPath = '/usr/local/tomcat/webapps/mapstore/configs/mapstore-unified-auth-config.json';
    
    try {
        if (fs.existsSync(unifiedConfigPath)) {
            console.log('🔐 Merging unified SSO configuration...');
            const unifiedConfigData = fs.readFileSync(unifiedConfigPath, 'utf8');
            const unifiedConfig = JSON.parse(unifiedConfigData);
            
            // Merge authentication configuration
            if (unifiedConfig.authentication) {
                config.authentication = { ...config.authentication, ...unifiedConfig.authentication };
                console.log('  ✅ Merged authentication configuration');
            }
            
            // Merge services configuration if it exists
            if (unifiedConfig.services) {
                config.services = { ...config.services, ...unifiedConfig.services };
                console.log('  ✅ Merged services configuration');
            }
            
            // Merge plugins configuration if it exists
            if (unifiedConfig.plugins) {
                config.plugins = { ...config.plugins, ...unifiedConfig.plugins };
                console.log('  ✅ Merged plugins configuration');
            }
        }
    } catch (error) {
        console.error('⚠️ Error merging unified SSO config:', error);
    }
    
    return config;
}

/**
 * Main configuration function
 */
async function configureMapStore() {
    console.log('🚀 Starting MapStore auto-configuration...');
    
    try {
        // Wait for services to be ready
        await waitForServices();
        
        // Load current configuration
        console.log('📋 Loading MapStore configuration...');
        let config = loadMapStoreConfig();
        
        // Merge unified SSO configuration if available
        config = mergeUnifiedSSOConfig(config);
        
        // Add services
        config = addServicesToConfig(config);
        
        // Add default layers
        config = addDefaultLayers(config);
        
        // Save configuration
        console.log('💾 Saving updated configuration...');
        if (saveMapStoreConfig(config)) {
            console.log('✅ MapStore auto-configuration completed successfully!');
            console.log('🎯 Services added:');
            console.log('  - GeoServer GIS Carbon WMS/WFS (http://geoserver:8080/geoserver/gis_carbon)');
            console.log('  - GeoServer Demo WMS/WFS (http://geoserver:8080/geoserver/demo_workspace)');
            console.log('  - FastAPI GEE Tiles (http://fastapi:8000)');
            console.log('🗺️ Default layers added:');
            DEFAULT_LAYERS.forEach(layer => {
                console.log(`  - ${layer.title}`);
            });
            console.log('🔐 Unified SSO configuration preserved and merged');
        } else {
            console.log('❌ Failed to save MapStore configuration');
        }
        
    } catch (error) {
        console.error('❌ Error during MapStore configuration:', error);
    }
}

// Run configuration if this script is executed directly
if (require.main === module) {
    configureMapStore();
}

module.exports = {
    configureMapStore,
    addServicesToConfig,
    addDefaultLayers,
    SERVICES_CONFIG,
    DEFAULT_LAYERS
};
