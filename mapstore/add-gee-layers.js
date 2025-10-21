#!/usr/bin/env node
/**
 * Add GEE Layers to MapStore Configuration
 * This script fetches GEE layers from FastAPI and adds them to MapStore's localConfig.json
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

// Configuration
const CONFIG = {
    fastapiUrl: 'http://localhost:8001',
    mapstoreConfigPath: './localConfig.json',
    outputConfigPath: './localConfig-with-gee.json',
    backupPath: './localConfig.backup.json'
};

/**
 * Make HTTP request to FastAPI
 */
function makeRequest(url) {
    return new Promise((resolve, reject) => {
        const client = url.startsWith('https') ? https : http;
        
        client.get(url, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    const jsonData = JSON.parse(data);
                    resolve(jsonData);
                } catch (e) {
                    reject(new Error(`Failed to parse JSON: ${e.message}`));
                }
            });
        }).on('error', (err) => {
            reject(new Error(`Request failed: ${err.message}`));
        });
    });
}

/**
 * Get all registered projects from FastAPI
 */
async function getRegisteredProjects() {
    try {
        console.log('🔍 Fetching registered projects from FastAPI...');
        
        // First, let's try to get a list of projects
        // Since we don't have a list endpoint, we'll try common project IDs
        const commonProjectIds = [
            'test_project_001',
            'sentinel_analysis_20241020_171516',
            'sentinel_analysis_20241020_171516'
        ];
        
        const projects = [];
        
        for (const projectId of commonProjectIds) {
            try {
                const url = `${CONFIG.fastapiUrl}/layers/${projectId}`;
                console.log(`  Checking project: ${projectId}`);
                
                const project = await makeRequest(url);
                
                if (project.status === 'success' && project.layers) {
                    projects.push({
                        projectId,
                        ...project
                    });
                    console.log(`  ✅ Found project: ${projectId} (${Object.keys(project.layers).length} layers)`);
                }
            } catch (err) {
                console.log(`  ⚠️  Project ${projectId} not found or error: ${err.message}`);
            }
        }
        
        return projects;
    } catch (err) {
        console.error('❌ Error fetching projects:', err.message);
        return [];
    }
}

/**
 * Convert GEE layer to MapStore layer configuration
 */
function convertGeeLayerToMapstore(projectId, layerName, layerData) {
    const baseUrl = `${CONFIG.fastapiUrl}/tiles/gee/${layerName}`;
    
    return {
        type: 'tile',
        name: `${projectId}_${layerName}`,
        title: layerData.name || layerName.toUpperCase(),
        description: layerData.description || `${layerName} from GEE analysis`,
        url: baseUrl + '/{z}/{x}/{y}',
        format: 'image/png',
        transparent: true,
        tileSize: 256,
        visibility: false,
        opacity: 1.0,
        metadata: {
            source: 'Google Earth Engine',
            projectId: projectId,
            layerName: layerName,
            analysisDate: layerData.metadata?.analysis_date || new Date().toISOString(),
            satellite: layerData.metadata?.satellite || 'Sentinel-2',
            ...layerData.metadata
        }
    };
}

/**
 * Add GEE layers to MapStore configuration
 */
function addGeeLayersToConfig(config, projects) {
    if (!config.catalogServices) {
        config.catalogServices = { services: [] };
    }
    
    if (!config.catalogServices.services) {
        config.catalogServices.services = [];
    }
    
    // Add GEE tile service
    const geeService = {
        type: 'tile',
        title: 'GEE Analysis Layers',
        description: 'Google Earth Engine analysis layers from FastAPI service',
        url: `${CONFIG.fastapiUrl}/tiles/gee/{layer_name}/{z}/{x}/{y}`,
        format: 'image/png',
        transparent: true,
        tileSize: 256,
        authRequired: false
    };
    
    // Check if GEE service already exists
    const existingGeeService = config.catalogServices.services.find(s => s.title === 'GEE Analysis Layers');
    if (existingGeeService) {
        console.log('  🔄 Updating existing GEE service...');
        Object.assign(existingGeeService, geeService);
    } else {
        console.log('  ➕ Adding new GEE service...');
        config.catalogServices.services.push(geeService);
    }
    
    // Add individual layers to map layers
    if (!config.map.layers) {
        config.map.layers = [];
    }
    
    // Remove existing GEE layers
    config.map.layers = config.map.layers.filter(layer => 
        !layer.name || !layer.name.startsWith('sentinel_analysis_') && !layer.name.startsWith('test_project_')
    );
    
    // Add new GEE layers
    let layerCount = 0;
    projects.forEach(project => {
        console.log(`  📁 Processing project: ${project.projectId}`);
        
        Object.entries(project.layers).forEach(([layerName, layerData]) => {
            const mapstoreLayer = convertGeeLayerToMapstore(project.projectId, layerName, layerData);
            config.map.layers.push(mapstoreLayer);
            layerCount++;
            console.log(`    ➕ Added layer: ${mapstoreLayer.name}`);
        });
    });
    
    console.log(`  ✅ Added ${layerCount} GEE layers to MapStore configuration`);
    
    return config;
}

/**
 * Main function
 */
async function main() {
    console.log('🚀 Starting GEE Layers Integration with MapStore...\n');
    
    try {
        // 1. Load current MapStore configuration
        console.log('📖 Loading MapStore configuration...');
        if (!fs.existsSync(CONFIG.mapstoreConfigPath)) {
            throw new Error(`MapStore config not found: ${CONFIG.mapstoreConfigPath}`);
        }
        
        const config = JSON.parse(fs.readFileSync(CONFIG.mapstoreConfigPath, 'utf8'));
        console.log('  ✅ Configuration loaded');
        
        // 2. Create backup
        console.log('💾 Creating backup...');
        fs.writeFileSync(CONFIG.backupPath, JSON.stringify(config, null, 2));
        console.log(`  ✅ Backup created: ${CONFIG.backupPath}`);
        
        // 3. Get GEE layers from FastAPI
        const projects = await getRegisteredProjects();
        
        if (projects.length === 0) {
            console.log('⚠️  No GEE projects found. Make sure to run the Jupyter notebook first.');
            console.log('   Run: jupyter/notebooks/02_gee_calculations.ipynb');
            return;
        }
        
        // 4. Add GEE layers to configuration
        console.log('\n🔧 Adding GEE layers to MapStore configuration...');
        const updatedConfig = addGeeLayersToConfig(config, projects);
        
        // 5. Save updated configuration
        console.log('💾 Saving updated configuration...');
        fs.writeFileSync(CONFIG.outputConfigPath, JSON.stringify(updatedConfig, null, 2));
        console.log(`  ✅ Updated config saved: ${CONFIG.outputConfigPath}`);
        
        // 6. Show summary
        console.log('\n📊 Summary:');
        console.log(`  Projects processed: ${projects.length}`);
        const totalLayers = projects.reduce((sum, p) => sum + Object.keys(p.layers).length, 0);
        console.log(`  Total layers added: ${totalLayers}`);
        console.log(`  MapStore layers: ${updatedConfig.map.layers.length}`);
        console.log(`  Catalog services: ${updatedConfig.catalogServices.services.length}`);
        
        console.log('\n🎉 Integration complete!');
        console.log('\nNext steps:');
        console.log('  1. Copy the updated config:');
        console.log(`     cp ${CONFIG.outputConfigPath} ${CONFIG.mapstoreConfigPath}`);
        console.log('  2. Restart MapStore container:');
        console.log('     docker-compose -f docker-compose.dev.yml restart mapstore');
        console.log('  3. Open MapStore:');
        console.log('     http://localhost:8082/mapstore');
        console.log('  4. Check the Catalog for GEE layers');
        
    } catch (error) {
        console.error('\n❌ Error:', error.message);
        process.exit(1);
    }
}

// Run if called directly
if (require.main === module) {
    main();
}

module.exports = { main, getRegisteredProjects, convertGeeLayerToMapstore };
