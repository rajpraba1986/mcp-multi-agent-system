# Production Environment Configuration Guide

This guide provides step-by-step instructions for configuring production-grade database agents in enterprise environments.

## Quick Answer: One Agent Per Database

**For production environments, use ONE AGENT PER DATABASE**. This provides:

✅ **Better Security**: Isolated credentials and permissions  
✅ **Better Performance**: Optimized connection pools per database  
✅ **Better Reliability**: Independent failure domains  
✅ **Better Scaling**: Scale each agent independently  
✅ **Better Compliance**: Clear audit trails per database  

## Production Configuration Examples

### 1. Single-Database Agent Configurations

#### PostgreSQL Production Agent
```yaml
# config/production/postgres-main-agent.yaml
agent:
  id: "postgres-main-agent"
  database_type: "postgresql"
  environment: "production"
  
database:
  host: "${POSTGRES_MAIN_HOST}"
  port: 5432
  database: "${POSTGRES_MAIN_DB}"
  username: "${POSTGRES_MAIN_USER}"
  password: "${POSTGRES_MAIN_PASSWORD}"
  ssl_mode: "require"
  max_connections: 20
  connection_timeout: 30
  
security:
  encryption_at_rest: true
  audit_logging: enabled
  access_control: "rbac"
  query_validation: strict
  
monitoring:
  health_checks: enabled
  metrics_collection: enabled
  log_level: "info"
  
scaling:
  min_replicas: 2
  max_replicas: 10
  cpu_threshold: 70%
  memory_threshold: 80%

toolsets:
  - user-management
  - sales-analytics
  - operations
```

#### MongoDB Events Agent
```yaml
# config/production/mongo-events-agent.yaml
agent:
  id: "mongo-events-agent"
  database_type: "mongodb"
  environment: "production"
  
database:
  host: "${MONGO_EVENTS_HOST}"
  port: 27017
  database: "${MONGO_EVENTS_DB}"
  username: "${MONGO_EVENTS_USER}"
  password: "${MONGO_EVENTS_PASSWORD}"
  ssl_enabled: true
  replica_set: "events-rs"
  max_connections: 50
  
security:
  encryption_at_rest: true
  audit_logging: enabled
  access_control: "rbac"
  
monitoring:
  health_checks: enabled
  metrics_collection: enabled
  log_level: "info"
  
scaling:
  min_replicas: 3
  max_replicas: 15
  cpu_threshold: 60%

toolsets:
  - event-analytics
  - log-analysis
```

#### Redis Cache Agent
```yaml
# config/production/redis-cache-agent.yaml
agent:
  id: "redis-cache-agent"
  database_type: "redis"
  environment: "production"
  
database:
  host: "${REDIS_CACHE_HOST}"
  port: 6379
  password: "${REDIS_CACHE_PASSWORD}"
  ssl_enabled: true
  cluster_mode: true
  max_connections: 100
  
security:
  encryption_in_transit: true
  access_control: "acl"
  
monitoring:
  health_checks: enabled
  metrics_collection: enabled
  log_level: "warn"
  
scaling:
  min_replicas: 2
  max_replicas: 8
  memory_threshold: 75%

toolsets:
  - cache-management
  - session-management
```

### 2. Environment Variables (.env.production)

```bash
# PostgreSQL Main Database
POSTGRES_MAIN_HOST=postgres-main-cluster.internal
POSTGRES_MAIN_PORT=5432
POSTGRES_MAIN_DB=production_db
POSTGRES_MAIN_USER=prod_app_user
POSTGRES_MAIN_PASSWORD=<secure-password>

# MongoDB Events Database
MONGO_EVENTS_HOST=mongo-events-cluster.internal
MONGO_EVENTS_PORT=27017
MONGO_EVENTS_DB=events_production
MONGO_EVENTS_USER=events_app_user
MONGO_EVENTS_PASSWORD=<secure-password>

# Redis Cache
REDIS_CACHE_HOST=redis-cache-cluster.internal
REDIS_CACHE_PORT=6379
REDIS_CACHE_PASSWORD=<secure-password>

# Analytics Database (ClickHouse)
CLICKHOUSE_ANALYTICS_HOST=clickhouse-cluster.internal
CLICKHOUSE_ANALYTICS_PORT=9000
CLICKHOUSE_ANALYTICS_DB=analytics_prod
CLICKHOUSE_ANALYTICS_USER=analytics_user
CLICKHOUSE_ANALYTICS_PASSWORD=<secure-password>

# LLM Configuration
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-sonnet-20240229
LLM_API_KEY=<your-anthropic-api-key>
LLM_TEMPERATURE=0.1

# Security Configuration
ENCRYPTION_KEY=<your-encryption-key>
JWT_SECRET=<your-jwt-secret>
AUDIT_LOG_LEVEL=info

# Monitoring Configuration
PROMETHEUS_ENDPOINT=http://prometheus.internal:9090
GRAFANA_ENDPOINT=http://grafana.internal:3000
LOG_AGGREGATOR=elasticsearch.internal:9200
```

### 3. Kubernetes Deployment (Production)

#### PostgreSQL Agent Deployment
```yaml
# k8s/postgres-main-agent-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-main-agent
  namespace: database-agents
  labels:
    app: postgres-main-agent
    database-type: postgresql
spec:
  replicas: 3
  selector:
    matchLabels:
      app: postgres-main-agent
  template:
    metadata:
      labels:
        app: postgres-main-agent
        database-type: postgresql
    spec:
      containers:
      - name: postgres-agent
        image: your-registry/postgres-agent:v1.0.0
        ports:
        - containerPort: 8080
        env:
        - name: POSTGRES_MAIN_HOST
          valueFrom:
            secretKeyRef:
              name: postgres-main-credentials
              key: host
        - name: POSTGRES_MAIN_USER
          valueFrom:
            secretKeyRef:
              name: postgres-main-credentials
              key: username
        - name: POSTGRES_MAIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-main-credentials
              key: password
        - name: AGENT_CONFIG_PATH
          value: "/config/postgres-main-agent.yaml"
        volumeMounts:
        - name: config
          mountPath: /config
        - name: logs
          mountPath: /logs
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: postgres-main-agent-config
      - name: logs
        emptyDir: {}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-main-agent-service
  namespace: database-agents
spec:
  selector:
    app: postgres-main-agent
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: postgres-main-agent-hpa
  namespace: database-agents
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: postgres-main-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### Agent Registry Deployment
```yaml
# k8s/agent-registry-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-registry
  namespace: database-agents
spec:
  replicas: 2
  selector:
    matchLabels:
      app: agent-registry
  template:
    metadata:
      labels:
        app: agent-registry
    spec:
      containers:
      - name: agent-registry
        image: your-registry/agent-registry:v1.0.0
        ports:
        - containerPort: 8080
        env:
        - name: REGISTRY_CONFIG_PATH
          value: "/config/registry.yaml"
        - name: DISCOVERY_NAMESPACE
          value: "database-agents"
        volumeMounts:
        - name: config
          mountPath: /config
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "200m"
      volumes:
      - name: config
        configMap:
          name: agent-registry-config
```

### 4. Database-Specific Toolset Configurations

#### PostgreSQL Toolsets
```yaml
# config/toolsets/postgresql-production.yaml
toolsets:
  user-management:
    description: "User management operations for PostgreSQL"
    tools:
      - search-users-by-name
      - search-users-by-email
      - get-user-activity
      - update-user-status
    permissions:
      - SELECT on users table
      - UPDATE on users.status column
    security_level: "high"
    
  sales-analytics:
    description: "Sales analytics and reporting"
    tools:
      - sales-summary-by-period
      - top-selling-products
      - revenue-by-category
      - customer-analysis
    permissions:
      - SELECT on orders, order_items, products, customers tables
    security_level: "medium"
    
  operations:
    description: "Operational monitoring and alerts"
    tools:
      - low-stock-alert
      - order-processing-status
      - system-health-check
    permissions:
      - SELECT on products, orders tables
    security_level: "high"
```

#### MongoDB Toolsets
```yaml
# config/toolsets/mongodb-production.yaml
toolsets:
  event-analytics:
    description: "Event stream analytics"
    tools:
      - search-events-by-type
      - get-event-timeline
      - aggregate-events-by-user
      - event-pattern-analysis
    permissions:
      - read on events collection
      - aggregate on events collection
    security_level: "medium"
    
  log-analysis:
    description: "Application log analysis"
    tools:
      - search-logs-by-level
      - get-error-patterns
      - performance-metrics
      - trace-user-journey
    permissions:
      - read on logs collection
      - aggregate on logs collection
    security_level: "high"
```

### 5. Security Configuration

#### RBAC Configuration
```yaml
# config/security/rbac.yaml
roles:
  database_admin:
    permissions:
      - agent:manage:*
      - tools:execute:*
      - query:validate:bypass
    agents:
      - postgres-main-agent
      - mongo-events-agent
      - redis-cache-agent
      
  analytics_user:
    permissions:
      - tools:execute:analytics
      - query:read_only
    agents:
      - postgres-main-agent
    toolsets:
      - sales-analytics
      - customer-insights
      
  operations_user:
    permissions:
      - tools:execute:operations
      - query:read_only
    agents:
      - postgres-main-agent
      - mongo-events-agent
    toolsets:
      - operations
      - monitoring

users:
  admin:
    roles: [database_admin]
    mfa_required: true
    
  analyst:
    roles: [analytics_user]
    mfa_required: false
    
  ops:
    roles: [operations_user]
    mfa_required: true
```

### 6. Monitoring and Alerting

#### Prometheus Configuration
```yaml
# config/monitoring/prometheus.yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'database-agents'
    kubernetes_sd_configs:
    - role: pod
      namespaces:
        names:
        - database-agents
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_label_app]
      regex: '.*-agent'
      action: keep
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
      action: keep
      regex: true
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
      action: replace
      target_label: __metrics_path__
      regex: (.+)

rule_files:
  - "agent_alerts.yml"

alerting:
  alertmanagers:
  - static_configs:
    - targets:
      - alertmanager:9093
```

#### Alert Rules
```yaml
# config/monitoring/agent_alerts.yml
groups:
- name: database_agents
  rules:
  - alert: AgentDown
    expr: up{job="database-agents"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Database agent {{ $labels.instance }} is down"
      
  - alert: HighQueryFailureRate
    expr: rate(agent_queries_failed_total[5m]) / rate(agent_queries_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High query failure rate for agent {{ $labels.agent_id }}"
      
  - alert: SlowQueryResponse
    expr: avg(agent_query_duration_seconds) > 5.0
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "Slow query response time for agent {{ $labels.agent_id }}"
```

### 7. Backup and Disaster Recovery

#### Backup Configuration
```yaml
# config/backup/backup-config.yaml
backup_policies:
  postgres-main:
    schedule: "0 2 * * *"  # Daily at 2 AM
    retention_days: 30
    encryption: enabled
    storage:
      type: s3
      bucket: database-backups-prod
      region: us-west-2
      
  mongo-events:
    schedule: "0 3 * * *"  # Daily at 3 AM
    retention_days: 7
    encryption: enabled
    storage:
      type: s3
      bucket: database-backups-prod
      region: us-west-2

disaster_recovery:
  rpo_hours: 1  # Recovery Point Objective
  rto_hours: 4  # Recovery Time Objective
  backup_validation: enabled
  cross_region_replication: enabled
```

## Migration Checklist

### Pre-Migration (Week 1)
- [ ] Inventory all existing databases and access patterns
- [ ] Map current user roles and permissions
- [ ] Identify database dependencies and relationships
- [ ] Plan agent boundaries and responsibilities
- [ ] Design security architecture

### Development (Weeks 2-4)
- [ ] Implement single-database agents
- [ ] Set up agent registry
- [ ] Configure monitoring and logging
- [ ] Implement security controls
- [ ] Create test environments

### Testing (Weeks 5-6)
- [ ] Unit testing for individual agents
- [ ] Integration testing for agent interactions
- [ ] Load testing for performance validation
- [ ] Security testing and penetration testing
- [ ] Disaster recovery testing

### Production Deployment (Weeks 7-8)
- [ ] Deploy to staging environment
- [ ] Gradual rollout to production
- [ ] Monitor metrics and performance
- [ ] Validate security controls
- [ ] Update documentation

## Best Practices Summary

### ✅ Production DO's
1. **Use one agent per database** for isolation and security
2. **Implement comprehensive monitoring** with alerts
3. **Use proper secret management** (Kubernetes secrets, Vault)
4. **Enable audit logging** for all database operations
5. **Set up automated backups** with tested restore procedures
6. **Use connection pooling** for optimal performance
7. **Implement circuit breakers** for resilience
8. **Follow principle of least privilege** for permissions

### ❌ Production DON'Ts
1. **Don't use multi-database agents** in production
2. **Don't hardcode credentials** in configuration files
3. **Don't skip security validation** for queries
4. **Don't ignore monitoring** and alerting
5. **Don't deploy without testing** disaster recovery
6. **Don't use default passwords** or weak authentication
7. **Don't mix environments** (dev/staging/prod)
8. **Don't skip regular security reviews**

## Conclusion

For production environments, the **single-database agent pattern** provides the best balance of security, performance, reliability, and maintainability. This guide provides all the necessary configurations and best practices to implement a production-grade system that can scale from small teams to large enterprises.

The key is to start with proper architectural foundations and gradually scale up while maintaining security and reliability standards.
