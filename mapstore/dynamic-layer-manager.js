/**
 * Dynamic Layer Manager for MapStore
 * Automatically discovers and adds layers from GeoServer
 */

class MapStoreLayerManager {
    constructor() {
        this.geoserverUrl = 'http://localhost:8080/geoserver';
        this.credentials = {
            username: 'admin',
            password: 'admin'
        };
    }

    /**
     * Discover all layers from a GeoServer workspace
     */
    async discoverLayers(workspace) {
        try {
            const response = await fetch(`${this.geoserverUrl}/rest/workspaces/${workspace}/layers`, {
                headers: {
                    'Authorization': 'Basic ' + btoa(this.credentials.username + ':' + this.credentials.password)
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch layers: ${response.status}`);
            }

            const data = await response.json();
            return data.layers.layer || [];
        } catch (error) {
            console.error('Error discovering layers:', error);
            return [];
        }
    }

    /**
     * Get layer details including capabilities
     */
    async getLayerDetails(workspace, layerName) {
        try {
            const response = await fetch(`${this.geoserverUrl}/rest/workspaces/${workspace}/layers/${layerName}`, {
                headers: {
                    'Authorization': 'Basic ' + btoa(this.credentials.username + ':' + this.credentials.password)
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch layer details: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error fetching layer details:', error);
            return null;
        }
    }

    /**
     * Generate MapStore layer configuration
     */
    generateLayerConfig(workspace, layer) {
        const wmsUrl = `${this.geoserverUrl}/${workspace}/wms`;
        const authUrl = `http://${this.credentials.username}:${this.credentials.password}@localhost:8080/geoserver/${workspace}/wms`;

        return {
            type: 'wms',
            name: layer.name,
            title: layer.name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
            url: authUrl, // URL with embedded credentials
            layers: layer.name,
            format: 'image/png',
            transparent: true,
            version: '1.3.0',
            authRequired: true,
            description: `Layer from ${workspace} workspace`,
            metadata: {
                workspace: workspace,
                originalName: layer.name,
                source: 'geoserver'
            }
        };
    }

    /**
     * Add layer to MapStore configuration
     */
    addLayerToMapStore(layerConfig) {
        // This would integrate with MapStore's layer management system
        console.log('Adding layer to MapStore:', layerConfig);
        
        // In a real implementation, you would:
        // 1. Add to MapStore's layer registry
        // 2. Update the map configuration
        // 3. Refresh the layer tree
        
        return layerConfig;
    }

    /**
     * Auto-discover and add all layers from a workspace
     */
    async autoDiscoverAndAddLayers(workspace) {
        console.log(`🔍 Discovering layers in workspace: ${workspace}`);
        
        const layers = await this.discoverLayers(workspace);
        console.log(`Found ${layers.length} layers:`, layers.map(l => l.name));

        const layerConfigs = [];
        
        for (const layer of layers) {
            const layerConfig = this.generateLayerConfig(workspace, layer);
            layerConfigs.push(layerConfig);
            
            // Add to MapStore
            this.addLayerToMapStore(layerConfig);
        }

        return layerConfigs;
    }

    /**
     * Create a service configuration for the workspace
     */
    generateServiceConfig(workspace) {
        const authUrl = `http://${this.credentials.username}:${this.credentials.password}@localhost:8080/geoserver/${workspace}/wms`;
        
        return {
            type: 'wms',
            title: `${workspace} Workspace (Auto-discovered)`,
            url: authUrl,
            format: 'image/png',
            version: '1.3.0',
            authRequired: true,
            authType: 'basic',
            authConfig: this.credentials
        };
    }

    /**
     * Generate complete MapStore configuration
     */
    async generateMapStoreConfig(workspaces) {
        const config = {
            mapstore: {
                catalogServices: {
                    services: []
                },
                layers: []
            }
        };

        for (const workspace of workspaces) {
            // Add service configuration
            const serviceConfig = this.generateServiceConfig(workspace);
            config.mapstore.catalogServices.services.push(serviceConfig);

            // Discover and add layers
            const layerConfigs = await this.autoDiscoverAndAddLayers(workspace);
            config.mapstore.layers.push(...layerConfigs);
        }

        return config;
    }
}

// Usage example
const layerManager = new MapStoreLayerManager();

// Auto-discover layers from demo_workspace
layerManager.autoDiscoverAndAddLayers('demo_workspace').then(layers => {
    console.log('✅ Auto-discovery complete!');
    console.log('Layers added:', layers);
});

// Generate complete configuration for multiple workspaces
layerManager.generateMapStoreConfig(['demo_workspace', 'gis_carbon']).then(config => {
    console.log('📋 Complete MapStore configuration:', config);
    
    // Save to file or apply to MapStore
    const configJson = JSON.stringify(config, null, 2);
    console.log('Configuration JSON:', configJson);
});

// Export for use in other scripts
window.MapStoreLayerManager = MapStoreLayerManager;
