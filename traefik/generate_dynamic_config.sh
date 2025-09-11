#!/bin/sh

# Remove 'http://' and 'https://' from WEBDOMAIN if present
WEBDOMAIN=${WEBDOMAIN#https://}
WEBDOMAIN=${WEBDOMAIN#http://}

# Remove 'http://' and 'https://' from WEBDOMAIN_GEONODE if present
WEBDOMAIN_GEONODE=${WEBDOMAIN_GEONODE#https://}
WEBDOMAIN_GEONODE=${WEBDOMAIN_GEONODE#http://}

cat << EOF > /traefik-config/dynamic.yml
http:
  routers:
    frontend-service-router-80:
      rule: "Host(\`${WEBDOMAIN}\`)"
      service: frontend-service
      entrypoints: web
      middlewares:
        - redirect-to-https

    frontend-service-router-443:
      entrypoints:
        - websecure
      rule: "Host(\`${WEBDOMAIN}\`)"
      service: frontend-service
      tls:
        certResolver: myresolver

    api-service-router-80:
      rule: "Host(\`${WEBDOMAIN}\`) && PathPrefix(\`/api\`)"
      service: api-service
      entrypoints: web
      middlewares:
        - redirect-to-https

    api-service-router-443:
      entrypoints:
        - websecure
      rule: "Host(\`${WEBDOMAIN}\`) && PathPrefix(\`/api\`)"
      service: api-service
      tls:
        certResolver: myresolver

    admin-service-router-80:
      rule: "Host(\`${WEBDOMAIN}\`) && PathPrefix(\`/admin\`)"
      service: api-service
      entrypoints: web
      middlewares:
        - redirect-to-https

    admin-service-router-443:
      entrypoints:
        - websecure
      rule: "Host(\`${WEBDOMAIN}\`) && PathPrefix(\`/admin\`)"
      service: api-service
      tls:
        certResolver: myresolver

    static-service-router-80:
      rule: "Host(\`${WEBDOMAIN}\`) && PathPrefix(\`/static\`)"
      service: api-service
      entrypoints: web
      middlewares:
        - redirect-to-https

    static-service-router-443:
      entrypoints:
        - websecure
      rule: "Host(\`${WEBDOMAIN}\`) && PathPrefix(\`/static\`)"
      service: api-service
      tls:
        certResolver: myresolver

    config-service-router-80:
      rule: "Host(\`${WEBDOMAIN}\`) && PathPrefix(\`/config.js\`)"
      service: api-service
      entrypoints: web
      middlewares:
        - redirect-to-https

    config-service-router-443:
      entrypoints:
        - websecure
      rule: "Host(\`${WEBDOMAIN}\`) && PathPrefix(\`/config.js\`)"
      service: api-service
      tls:
        certResolver: myresolver
      middlewares:
       - config-rewrite

    rundeck-service-router-80:
      rule: "Host(\`${WEBDOMAIN}\`) && PathPrefix(\`/rundeck\`)"
      service: rundeck-service
      entrypoints: web
      middlewares:
        - redirect-to-https

    rundeck-service-router-443:
      entrypoints:
        - websecure
      rule: "Host(\`${WEBDOMAIN}\`) && PathPrefix(\`/rundeck\`)"
      service: rundeck-service
      tls:
        certResolver: myresolver

    geonode-service-router-80:
      rule: "Host(\`${WEBDOMAIN_GEONODE}\`)"
      service: geonode-service
      entrypoints: web
      middlewares:
        - redirect-to-https

    geonode-service-router-443:
      entrypoints:
        - websecure
      rule: "Host(\`${WEBDOMAIN_GEONODE}\`)"
      service: geonode-service
      tls:
        certResolver: myresolver

    geoserver-service-router-80:
      rule: "Host(\`${WEBDOMAIN_GEONODE}\`) && PathPrefix(\`/geoserver\`)"
      service: geoserver-service
      entrypoints: web
      middlewares:
        - redirect-to-https

    geoserver-service-router-443:
      entrypoints:
        - websecure
      rule: "Host(\`${WEBDOMAIN_GEONODE}\`) && PathPrefix(\`/geoserver\`)"
      service: geoserver-service
      tls:
        certResolver: myresolver

  middlewares:
    redirect-to-https:
      redirectScheme:
        scheme: "https"
        permanent: true
    config-rewrite:
      replacePath:
        path: "/api/v1/config.js"


  services:
    frontend-service:
      loadBalancer:
        servers:
          - url: "http://app-frontend-1:3000"

    api-service:
      loadBalancer:
        servers:
          - url: "http://app-backend-1:8000"

    rundeck-service:
      loadBalancer:
        servers:
          - url: "http://rundeck:4440"

    geonode-service:
      loadBalancer:
        servers:
          - url: "http://django4drought_map_hub:8000"

    geoserver-service:
      loadBalancer:
        servers:
          - url: "http://geoserver4drought_map_hub:8080"

EOF