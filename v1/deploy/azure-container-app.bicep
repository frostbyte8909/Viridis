param location string = resourceGroup().location

// --- Networking ---
resource nirvanaVnet 'Microsoft.Network/virtualNetworks@2023-09-01' = {
  name: 'viridis-vnet'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }
  }
}

// --- Managed Services ---
resource redisCache 'Microsoft.Cache/redis@2023-08-01' = {
  name: 'viridis-redis-cache'
  location: location
  properties: {
    sku: {
      name: 'Premium'
      family: 'P'
      capacity: 1
    }
    enableNonSslPort: false
  }
}

resource postgresDB 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: 'viridis-postgres'
  location: location
  sku: {
    name: 'Standard_D2ds_v4'
    tier: 'GeneralPurpose'
  }
  properties: {
    version: '16'
    storage: {
      storageSizeGB: 128
    }
    highAvailability: {
      mode: 'ZoneRedundant'
    }
  }
}

// --- Container Apps Environment ---
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-02-01' = {
  name: 'viridis-env'
  location: location
  properties: {
    vnetConfiguration: {
      infrastructureSubnetId: '${nirvanaVnet.id}/subnets/default'
    }
  }
}

// --- FastAPI App ---
resource containerApp 'Microsoft.App/containerApps@2024-02-01' = {
  name: 'viridis-api'
  location: location
  managedEnvironmentId: containerAppsEnv.id
  properties: {
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
      }
    }
    template: {
      containers: [
        {
          name: 'api'
          image: 'viridisacr.azurecr.io/viridis-api:latest'
          env: [
            { name: 'POSTGRES_HOST', value: postgresDB.properties.fullyQualifiedDomainName }
            { name: 'REDIS_HOST', value: redisCache.properties.hostName }
          ]
          resources: {
            cpu: json('1.0')
            memory: '2.0Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
        rules: [
          {
            name: 'http-scaling-rule'
            custom: {
              type: 'http'
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}
