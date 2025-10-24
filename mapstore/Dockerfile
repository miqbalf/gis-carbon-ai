FROM tomcat:9-jdk11 AS mother
LABEL maintainer="muh.firdausiqbal@#gmail.com"
ARG MAPSTORE_VERSION
ARG MAPSTORE_WEBAPP_SRC="https://github.com/geosolutions-it/MapStore2/releases/download/${MAPSTORE_VERSION}/mapstore.war"
ADD "${MAPSTORE_WEBAPP_SRC}" "/mapstore/"

# Create docker directory (no custom docker files to copy)
RUN mkdir -p /mapstore/docker/

# Copy unified SSO configuration files (as backup, not as main config)
COPY ./mapstore-unified-auth-config.json /usr/local/tomcat/webapps/mapstore/configs/mapstore-unified-auth-config.json
COPY ./setup-mapstore-auth.js /usr/local/tomcat/webapps/mapstore/
COPY ./update-mapstore-auth.js /usr/local/tomcat/webapps/mapstore/
COPY ./plugins/GeoServerAuthPlugin.js /usr/local/tomcat/webapps/mapstore/plugins/

# Copy service auto-configuration script and default config
COPY ./auto-configure-services.js /usr/local/tomcat/webapps/mapstore/auto-configure-services.js
COPY ./default-localConfig.json /usr/local/tomcat/webapps/mapstore/configs/default-localConfig.json
COPY ./geoserver-integration-config.json /usr/local/tomcat/webapps/mapstore/configs/geoserver-integration-config.json
COPY ./gee-integration-config.json /usr/local/tomcat/webapps/mapstore/configs/gee-integration-config.json

# Create auth directory (auth files will be copied by external scripts if needed)
RUN mkdir -p /usr/local/tomcat/webapps/mapstore/auth/

WORKDIR /mapstore

FROM tomcat:9-jdk11
ARG UID=1001
ARG GID=1001
ARG UNAME=tomcat
# Tomcat specific options
ENV CATALINA_BASE "$CATALINA_HOME"
ENV MAPSTORE_WEBAPP_DST="${CATALINA_BASE}/webapps"
ARG INITIAL_MEMORY="512m"
ARG MAXIMUM_MEMORY="2048m"
ENV JAVA_OPTS="${JAVA_OPTS} -Xms${INITIAL_MEMORY} -Xmx${MAXIMUM_MEMORY}"

ARG OVR=""
# ENV GEOSTORE_OVR_OPT="-Dgeostore-ovr=file://${CATALINA_BASE}/conf/${OVR}"
ARG DATA_DIR="${CATALINA_BASE}/datadir"
ENV GEOSTORE_OVR_OPT="-Dgeostore-ovr=file://${CATALINA_BASE}/conf/geostore-datasource-ovr-postgres.properties"
ENV JAVA_OPTS="${JAVA_OPTS} ${GEOSTORE_OVR_OPT} -Ddatadir.location=${DATA_DIR}"
ENV TERM xterm

COPY --from=mother "/mapstore/mapstore.war" "${MAPSTORE_WEBAPP_DST}/mapstore.war"
COPY --from=mother "/mapstore/docker" "${CATALINA_BASE}/docker/"

# Extract the WAR file to ensure proper deployment
RUN cd "${MAPSTORE_WEBAPP_DST}" && \
    mkdir -p mapstore && \
    cd mapstore && \
    jar -xf ../mapstore.war && \
    rm ../mapstore.war

# Copy scripts and configs to a staging directory (will be copied after WAR deployment)
COPY --from=mother "/usr/local/tomcat/webapps/mapstore/auto-configure-services.js" "${CATALINA_BASE}/scripts/auto-configure-services.js"
COPY --from=mother "/usr/local/tomcat/webapps/mapstore/setup-mapstore-auth.js" "${CATALINA_BASE}/scripts/setup-mapstore-auth.js"
COPY --from=mother "/usr/local/tomcat/webapps/mapstore/update-mapstore-auth.js" "${CATALINA_BASE}/scripts/update-mapstore-auth.js"
COPY --from=mother "/usr/local/tomcat/webapps/mapstore/plugins/GeoServerAuthPlugin.js" "${CATALINA_BASE}/scripts/GeoServerAuthPlugin.js"
COPY --from=mother "/usr/local/tomcat/webapps/mapstore/configs/mapstore-unified-auth-config.json" "${CATALINA_BASE}/scripts/mapstore-unified-auth-config.json"
COPY --from=mother "/usr/local/tomcat/webapps/mapstore/configs/default-localConfig.json" "${CATALINA_BASE}/scripts/default-localConfig.json"
COPY --from=mother "/usr/local/tomcat/webapps/mapstore/configs/geoserver-integration-config.json" "${CATALINA_BASE}/scripts/geoserver-integration-config.json"
COPY --from=mother "/usr/local/tomcat/webapps/mapstore/configs/gee-integration-config.json" "${CATALINA_BASE}/scripts/gee-integration-config.json"

# Copy server.xml configuration (create default if not exists)
RUN if [ ! -f "${CATALINA_BASE}/conf/server.xml" ]; then \
        echo "Creating default server.xml"; \
    fi
RUN sed -i -e 's/8082/8080/g' ${CATALINA_BASE}/conf/server.xml 2>/dev/null || true

# Create all necessary directories for persistence
RUN mkdir -p ${DATA_DIR} \
    && mkdir -p ${CATALINA_BASE}/webapps/mapstore/data \
    && mkdir -p ${CATALINA_BASE}/webapps/mapstore/configs \
    && mkdir -p ${CATALINA_BASE}/webapps/mapstore/auth \
    && mkdir -p ${CATALINA_BASE}/webapps/mapstore/plugins \
    && mkdir -p ${CATALINA_BASE}/webapps/mapstore/uploads \
    && mkdir -p ${CATALINA_BASE}/webapps/mapstore/custom \
    && mkdir -p ${CATALINA_BASE}/logs \
    && mkdir -p ${CATALINA_BASE}/temp \
    && mkdir -p ${CATALINA_BASE}/work

# Copy wait-for-postgres script if it exists
RUN if [ -f "${CATALINA_BASE}/docker/wait-for-postgres.sh" ]; then \
        cp ${CATALINA_BASE}/docker/wait-for-postgres.sh /usr/bin/wait-for-postgres; \
    else \
        echo '#!/bin/bash\nwhile ! pg_isready -h "$1" -p "$2" -U "$3"; do\n  echo "Waiting for postgres..."\n  sleep 2\ndone\necho "Postgres is ready!"' > /usr/bin/wait-for-postgres; \
    fi && \
    chmod +x /usr/bin/wait-for-postgres

# Create unified SSO and service setup script
RUN echo '#!/bin/bash\n\
echo "🔐 Setting up MapStore Unified SSO and Services..."\n\
# Wait for MapStore to be ready\n\
sleep 15\n\
# Copy scripts and configs from staging directory to webapp after WAR deployment\n\
if [ -d "/usr/local/tomcat/webapps/mapstore" ]; then\n\
  echo "📁 Copying scripts and configs to MapStore webapp..."\n\
  cp /usr/local/tomcat/scripts/auto-configure-services.js /usr/local/tomcat/webapps/mapstore/ 2>/dev/null || true\n\
  cp /usr/local/tomcat/scripts/setup-mapstore-auth.js /usr/local/tomcat/webapps/mapstore/ 2>/dev/null || true\n\
  cp /usr/local/tomcat/scripts/update-mapstore-auth.js /usr/local/tomcat/webapps/mapstore/ 2>/dev/null || true\n\
  cp /usr/local/tomcat/scripts/GeoServerAuthPlugin.js /usr/local/tomcat/webapps/mapstore/plugins/ 2>/dev/null || true\n\
  cp /usr/local/tomcat/scripts/mapstore-unified-auth-config.json /usr/local/tomcat/webapps/mapstore/configs/ 2>/dev/null || true\n\
  cp /usr/local/tomcat/scripts/default-localConfig.json /usr/local/tomcat/webapps/mapstore/configs/ 2>/dev/null || true\n\
  cp /usr/local/tomcat/scripts/geoserver-integration-config.json /usr/local/tomcat/webapps/mapstore/configs/ 2>/dev/null || true\n\
  cp /usr/local/tomcat/scripts/gee-integration-config.json /usr/local/tomcat/webapps/mapstore/configs/ 2>/dev/null || true\n\
fi\n\
# Run service auto-configuration first\n\
if [ -f "/usr/local/tomcat/webapps/mapstore/auto-configure-services.js" ]; then\n\
  echo "🔧 Auto-configuring MapStore services..."\n\
  node /usr/local/tomcat/webapps/mapstore/auto-configure-services.js\n\
fi\n\
# Run authentication setup scripts if they exist\n\
if [ -f "/usr/local/tomcat/webapps/mapstore/setup-mapstore-auth.js" ]; then\n\
  echo "🔐 Running MapStore auth setup..."\n\
  node /usr/local/tomcat/webapps/mapstore/setup-mapstore-auth.js\n\
fi\n\
echo "✅ MapStore setup complete!"' > /usr/bin/setup-mapstore-sso && \
    chmod +x /usr/bin/setup-mapstore-sso

RUN apt-get update \
    && apt-get install --yes postgresql-client curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install --yes nodejs \
    && apt-get clean \
    && apt-get autoclean \
    && apt-get autoremove -y \
    && rm -rf /var/cache/apt/* \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /usr/share/man/* \
    && rm -rf /usr/share/doc/*

RUN groupadd -g $GID $UNAME
RUN useradd -m -u $UID -g $GID --system $UNAME
RUN chown -R $UID:$GID ${CATALINA_BASE} ${MAPSTORE_WEBAPP_DST} ${DATA_DIR} \
    && chown -R $UID:$GID ${CATALINA_BASE}/webapps/mapstore/data \
    && chown -R $UID:$GID ${CATALINA_BASE}/webapps/mapstore/configs \
    && chown -R $UID:$GID ${CATALINA_BASE}/webapps/mapstore/auth \
    && chown -R $UID:$GID ${CATALINA_BASE}/webapps/mapstore/plugins \
    && chown -R $UID:$GID ${CATALINA_BASE}/webapps/mapstore/uploads \
    && chown -R $UID:$GID ${CATALINA_BASE}/webapps/mapstore/custom \
    && chown -R $UID:$GID ${CATALINA_BASE}/logs \
    && chown -R $UID:$GID ${CATALINA_BASE}/temp \
    && chown -R $UID:$GID ${CATALINA_BASE}/work
USER $UNAME
WORKDIR ${CATALINA_BASE}

VOLUME ["/usr/local/tomcat/datadir", "/usr/local/tomcat/webapps/mapstore/data", "/usr/local/tomcat/webapps/mapstore/configs", "/usr/local/tomcat/webapps/mapstore/auth", "/usr/local/tomcat/webapps/mapstore/plugins", "/usr/local/tomcat/webapps/mapstore/uploads", "/usr/local/tomcat/webapps/mapstore/custom", "/usr/local/tomcat/logs", "/usr/local/tomcat/temp", "/usr/local/tomcat/work"]

EXPOSE 8080