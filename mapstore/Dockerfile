# MapStore Custom Dockerfile
# Pre-extracts WAR file for faster startup and better persistence support

FROM geosolutionsit/mapstore2:v2025.01.02-stable

# Switch to root to perform extraction
USER root

# Install unzip if not available, then extract WAR file during build
# This prevents issues with volume mounts and makes startup instant
RUN apt-get update && apt-get install -y unzip && \
    cd /usr/local/tomcat/webapps && \
    unzip -q mapstore.war -d mapstore && \
    rm -f mapstore.war && \
    apt-get remove -y unzip && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Create data directory for uploads/extensions (can be volume-mounted)
RUN mkdir -p /usr/local/tomcat/webapps/mapstore/data

# Add CORS configuration to web.xml
RUN echo '<?xml version="1.0" encoding="UTF-8"?>' > /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '<web-app xmlns="http://xmlns.jcp.org/xml/ns/javaee"' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '         xsi:schemaLocation="http://xmlns.jcp.org/xml/ns/javaee http://xmlns.jcp.org/xml/ns/javaee/web-app_3_1.xsd"' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '         version="3.1">' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '    <filter>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '        <filter-name>CorsFilter</filter-name>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '        <filter-class>org.apache.catalina.filters.CorsFilter</filter-class>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '        <init-param>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '            <param-name>cors.allowed.origins</param-name>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '            <param-value>*</param-value>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '        </init-param>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '        <init-param>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '            <param-name>cors.allowed.methods</param-name>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '            <param-value>GET,POST,PUT,DELETE,OPTIONS,HEAD</param-value>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '        </init-param>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '        <init-param>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '            <param-name>cors.allowed.headers</param-name>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '            <param-value>Content-Type,X-Requested-With,accept,Origin,Access-Control-Request-Method,Access-Control-Request-Headers</param-value>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '        </init-param>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '        <init-param>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '            <param-name>cors.support.credentials</param-name>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '            <param-value>false</param-value>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '        </init-param>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '    </filter>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '    <filter-mapping>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '        <filter-name>CorsFilter</filter-name>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '        <url-pattern>/*</url-pattern>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '    </filter-mapping>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml && \
    echo '</web-app>' >> /usr/local/tomcat/webapps/mapstore/WEB-INF/web.xml

# Expose standard Tomcat port
EXPOSE 8080

# Use the default CMD from base image (inherits from parent)
# The base image will handle user switching if needed

