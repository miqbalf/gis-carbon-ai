import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [layers, setLayers] = useState([]);
  const [loading, setLoading] = useState(false);

  // API base URLs
  const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  const FASTAPI_BASE = process.env.REACT_APP_FASTAPI_URL || 'http://localhost:8001';
  const GEOSERVER_BASE = process.env.REACT_APP_GEOSERVER_URL || 'http://localhost:8080/geoserver';

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/api/projects/`);
      setProjects(response.data);
    } catch (error) {
      console.error('Error fetching projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectSelect = async (projectId) => {
    try {
      setLoading(true);
      setSelectedProject(projectId);
      
      // Fetch layers for the selected project
      const response = await axios.get(`${FASTAPI_BASE}/layers/${projectId}`);
      setLayers(response.data.layers);
    } catch (error) {
      console.error('Error fetching project layers:', error);
    } finally {
      setLoading(false);
    }
  };

  const processProject = async (projectId) => {
    try {
      setLoading(true);
      const response = await axios.post(`${FASTAPI_BASE}/process/${projectId}`, {
        // Add any configuration here
      });
      console.log('Processing result:', response.data);
    } catch (error) {
      console.error('Error processing project:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>GIS Carbon AI - MapStore</h1>
        <p>Google Earth Engine Integration with MapStore</p>
      </header>

      <main className="App-main">
        <div className="sidebar">
          <h2>Projects</h2>
          {loading && <p>Loading...</p>}
          
          <div className="project-list">
            {projects.map((project) => (
              <div 
                key={project.id} 
                className={`project-item ${selectedProject === project.id ? 'selected' : ''}`}
                onClick={() => handleProjectSelect(project.id)}
              >
                <h3>{project.name || `Project ${project.id}`}</h3>
                <p>{project.description || 'No description available'}</p>
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    processProject(project.id);
                  }}
                  className="process-btn"
                >
                  Process GEE
                </button>
              </div>
            ))}
          </div>

          {selectedProject && (
            <div className="layers-section">
              <h3>Available Layers</h3>
              <div className="layer-list">
                {Object.entries(layers).map(([key, layer]) => (
                  <div key={key} className="layer-item">
                    <h4>{layer.name}</h4>
                    <p>{layer.description}</p>
                    <div className="layer-controls">
                      <label>
                        <input type="checkbox" defaultChecked />
                        Show Layer
                      </label>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="map-container">
          <div className="map-placeholder">
            <h2>MapStore Map View</h2>
            <p>This will be replaced with the actual MapStore map component</p>
            {selectedProject && (
              <div className="map-info">
                <h3>Selected Project: {selectedProject}</h3>
                <p>Map layers will be loaded here</p>
                <div className="tile-info">
                  <h4>Tile URLs:</h4>
                  {Object.keys(layers).map((layerKey) => (
                    <div key={layerKey} className="tile-url">
                      <strong>{layerKey}:</strong>
                      <code>{FASTAPI_BASE}/tiles/{selectedProject}/{{z}}/{{x}}/{{y}}?layer={layerKey}</code>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      <footer className="App-footer">
        <p>GIS Carbon AI - Powered by Google Earth Engine, GeoServer, and MapStore</p>
      </footer>
    </div>
  );
}

export default App;
