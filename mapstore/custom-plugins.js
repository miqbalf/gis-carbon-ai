/**
 * Custom MapStore Plugins for GIS Carbon AI
 * This file contains custom plugins that can be integrated into MapStore
 */

// Carbon Analysis Plugin
const CarbonAnalysisPlugin = {
    name: 'CarbonAnalysis',
    component: require('./plugins/CarbonAnalysis'),
    reducers: {
        carbonAnalysis: require('./reducers/carbonAnalysis')
    },
    epics: {
        carbonAnalysis: require('./epics/carbonAnalysis')
    }
};

// GEE Integration Plugin  
const GEEIntegrationPlugin = {
    name: 'GEEIntegration',
    component: require('./plugins/GEEIntegration'),
    reducers: {
        geeIntegration: require('./reducers/geeIntegration')
    },
    epics: {
        geeIntegration: require('./epics/geeIntegration')
    }
};

// Custom Toolbar Plugin
const CustomToolbarPlugin = {
    name: 'CustomToolbar',
    component: require('./plugins/CustomToolbar'),
    reducers: {
        customToolbar: require('./reducers/customToolbar')
    }
};

// Export all custom plugins
module.exports = {
    CarbonAnalysisPlugin,
    GEEIntegrationPlugin,
    CustomToolbarPlugin
};

/**
 * Usage in MapStore:
 * 1. Copy this file to MapStore's plugins directory
 * 2. Import in your localConfig.json
 * 3. Add to plugins.desktop array
 * 
 * Example localConfig.json:
 * {
 *   "plugins": {
 *     "desktop": [
 *       "Map",
 *       "Toolbar",
 *       "CarbonAnalysis",
 *       "GEEIntegration",
 *       "CustomToolbar"
 *     ]
 *   }
 * }
 */
