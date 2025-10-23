#!/bin/bash
# Test runner script for Jupyter Notebook Integration

echo "🧪 Jupyter Notebook Integration Test Runner"
echo "============================================="

# Check if we're in Docker environment
if [ -f "/usr/src/app/notebooks/gee_integration.py" ]; then
    echo "✅ Running in Docker environment"
    echo "📁 Working directory: $(pwd)"
    echo "🐍 Python path: $(which python3)"
    echo "📚 Notebooks path: /usr/src/app/notebooks"
    echo ""
    
    # Run the integration tests
    python3 test_notebook_integration.py
    
else
    echo "❌ Not in Docker environment"
    echo "Please run this from within the Jupyter container:"
    echo "  docker exec -it gis_jupyter_dev bash"
    echo "  cd /usr/src/app/jupyter/test"
    echo "  ./run_tests.sh"
    exit 1
fi
