# Jupyter Lab with same environment as Django and FastAPI
FROM python:3.10.12-slim

# Install system dependencies
RUN apt-get update \
    && apt-get install -y \
        build-essential \
        git \
        curl \
        wget \
        libpq-dev \
        libgdal-dev \
        gdal-bin \
        libspatialindex-dev \
        libgeos-dev \
        libproj-dev \
        libffi-dev \
        libssl-dev \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
        libjpeg-dev \
        libpng-dev \
        libfreetype6-dev \
        pkg-config \
        netcat-openbsd \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV GDAL_DATA=/usr/share/gdal
ENV PROJ_LIB=/usr/share/proj

# Set working directory
WORKDIR /app

# Install core packages first (most reliable)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        jupyterlab==4.0.9 \
        jupyter==1.0.0 \
        ipykernel==6.25.2 \
        ipywidgets==8.1.1 \
        notebook==7.0.6

# Install data science packages
RUN pip install --no-cache-dir \
    numpy==1.24.3 \
    pandas==2.0.3 \
    matplotlib==3.7.2 \
    seaborn==0.12.2 \
    plotly==5.17.0

# Install geospatial packages
RUN pip install --no-cache-dir \
    geopandas==0.14.0 \
    shapely==2.0.2 \
    pyproj==3.6.1 \
    fiona==1.9.5 \
    rasterio==1.3.9 \
    folium==0.15.0

# Install GEE and ArcGIS packages
RUN pip install --no-cache-dir \
    earthengine-api==0.1.370 \
    geemap==0.30.0 \
    arcgis==2.1.0.3

# Install web framework packages
RUN pip install --no-cache-dir \
    django==4.2.7 \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    requests==2.31.0

# Install database packages
RUN pip install --no-cache-dir \
    psycopg2-binary==2.9.9 \
    redis==5.0.1

# Install utility packages
RUN pip install --no-cache-dir \
    python-dotenv==1.0.0

# Copy the application code
COPY . .

# Create directories for notebooks and data
RUN mkdir -p /app/notebooks /app/data /app/shared

# Set permissions
RUN chmod -R 755 /app

# Expose Jupyter Lab port
EXPOSE 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8888/lab || exit 1

# Start Jupyter Lab
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''", "--NotebookApp.disable_check_xsrf=True"]
