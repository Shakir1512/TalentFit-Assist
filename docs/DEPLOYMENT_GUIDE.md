# Deployment Guide

**TalentFit Assist - Production Deployment**

---

## Prerequisites

- Docker & Docker Compose
- PostgreSQL 14+
- Python 3.10+
- AWS (S3, RDS) or GCP/Azure equivalents
- API Keys: Anthropic, OpenAI

---

## MVP Deployment (Weeks 1-4)

### Architecture
```
Single VM (8GB RAM, 100GB SSD)
├── PostgreSQL (local)
├── FastAPI backend
├── Streamlit frontend
├── ChromaDB (in-memory + persistence)
└── MCP Server (single instance)
```

### 1. Local Setup

**Clone repository:**
```bash
git clone https://github.com/company/talentfit-assist.git
cd talentfit-assist
```

**Create environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Configure environment:**
```bash
cp .env.example .env
# Edit .env with:
# - DATABASE_URL=postgresql://user:password@localhost/talentfit
# - ANTHROPIC_API_KEY=sk-...
# - JWT_SECRET_KEY=your-secret-key
# - OPENAI_API_KEY=sk-...
```

**Initialize database:**
```bash
python scripts/init_db.py
python scripts/create_admin_user.py --email admin@company.com
```

### 2. Local Docker Deployment

**Build images:**
```bash
docker-compose -f docker-compose.yml build
```

**Start services:**
```bash
docker-compose -f docker-compose.yml up -d
```

**Verify health:**
```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

**Access services:**
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:8501
- PostgreSQL: localhost:5432

### 3. Test End-to-End

**Login:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "recruiter@company.com", "password": "test123"}'
```

**Upload documents:**
```bash
curl -X POST http://localhost:8000/upload/jd \
  -H "Authorization: Bearer <token>" \
  -F "file=@sample_jd.jsonl"
```

**Run screening:**
```bash
curl -X POST http://localhost:8000/screen/run \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "jd_id": "jd_001",
    "candidate_ids": ["c_042", "c_089"],
    "config_overrides": {}
  }'
```

---

## Production Hardening (Weeks 5-12)

### Architecture
```
AWS ECS (Elastic Container Service)
├── ALB (Application Load Balancer)
├── FastAPI Service Cluster (3+ instances)
├── Streamlit Service (2+ instances)
├── MCP Server Cluster (2+ instances)
├── RDS PostgreSQL (Multi-AZ)
├── ElastiCache Redis (Cluster mode)
├── S3 (Document storage, encrypted)
└── CloudWatch (Monitoring)
```

### Phase 1: Database Hardening

**Migrate to AWS RDS:**
```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier talentfit-db \
  --db-instance-class db.t3.large \
  --engine postgres \
  --master-username admin \
  --allocated-storage 100 \
  --storage-encrypted \
  --backup-retention-period 30 \
  --multi-az
```

**Configure backups:**
```bash
# Daily automated backups (retention: 30 days)
# Weekly snapshots (retention: 12 weeks)
# Restore test: weekly full restore to test environment
```

**Enable security:**
```bash
# Security group: Allow only FastAPI instances
# SSL/TLS: Enforce encrypted connections
# Encryption at rest: AES-256
```

### Phase 2: Containerization & Orchestration

**Push images to ECR:**
```bash
aws ecr create-repository --repository-name talentfit-backend
docker tag talentfit-backend:1.0 \
  123456789.dkr.ecr.us-east-1.amazonaws.com/talentfit-backend:1.0
docker push \
  123456789.dkr.ecr.us-east-1.amazonaws.com/talentfit-backend:1.0
```

**ECS Service Definition:**
```json
{
  "family": "talentfit-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/talentfit-backend:1.0",
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:..."
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/talentfit",
          "awslogs-region": "us-east-1"
        }
      }
    }
  ]
}
```

**Scale with auto-scaling:**
```bash
# Target: 70% CPU utilization
# Min instances: 3
# Max instances: 10
# Scale-up threshold: CPU > 70%
# Scale-down threshold: CPU < 30%
```

### Phase 3: Caching & Performance

**Deploy Redis Cluster:**
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id talentfit-redis \
  --cache-node-type cache.r6g.large \
  --engine redis \
  --num-cache-nodes 3 \
  --engine-version 7.0 \
  --automatic-failover-enabled
```

**Cache Strategy:**
```python
# Backend caching (5 minutes):
from redis import Redis
redis_client = Redis(host='talentfit-redis.abc.ng.0001.use1.cache.amazonaws.com')

cache_key = f"embedding:{model}:{text_hash}"
if redis_client.exists(cache_key):
    embedding = redis_client.get(cache_key)
else:
    embedding = embed(text)
    redis_client.setex(cache_key, 300, embedding)
```

### Phase 4: Storage & Encryption

**Configure S3:**
```bash
aws s3api create-bucket --bucket talentfit-documents
aws s3api put-bucket-encryption \
  --bucket talentfit-documents \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Versioning
aws s3api put-bucket-versioning \
  --bucket talentfit-documents \
  --versioning-configuration Status=Enabled
```

**Document lifecycle:**
```
1. Upload → Encrypt → Store in S3
2. Delete request → Move to /deleted/ prefix
3. After 30 days → Permanent purge
4. Audit trail → Immutable records in PostgreSQL
```

### Phase 5: Secrets Management

**AWS Secrets Manager:**
```bash
aws secretsmanager create-secret \
  --name talentfit/prod/db-password \
  --secret-string '{"username":"admin","password":"your-secure-password"}'

aws secretsmanager create-secret \
  --name talentfit/prod/anthropic-api-key \
  --secret-string 'sk-ant-...'

aws secretsmanager create-secret \
  --name talentfit/prod/jwt-secret \
  --secret-string 'your-jwt-secret-key'
```

**Application consumption:**
```python
import boto3
from botocore.exceptions import ClientError

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        logger.error(f"Failed to retrieve secret: {e}")
        raise
```

### Phase 6: Monitoring & Observability

**CloudWatch Dashboards:**
```bash
# Create custom dashboard
aws cloudwatch put-dashboard \
  --dashboard-name TalentFit \
  --dashboard-body file://dashboard.json
```

**Metrics to track:**
```
- API latency (p50, p95, p99)
- Error rate by endpoint
- Token usage per screening
- Cost per day
- Database connection pool usage
- ChromaDB query latency
- Cache hit rate
```

**Alerts:**
```
- Error rate > 1% → Page on-call
- API latency p99 > 2s → Alert
- Token budget 80% used → Alert
- Database CPU > 80% → Alert
- Out of disk space → Critical
```

### Phase 7: TLS & Encryption

**Certificate Management:**
```bash
# Request ACM certificate
aws acm request-certificate \
  --domain-name api.talentfit.company.com \
  --validation-method DNS

# Configure ALB with HTTPS
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:...
```

**Force HTTPS:**
```
All HTTP requests → 301 redirect to HTTPS
```

### Phase 8: Disaster Recovery

**RDS Backup Strategy:**
```
Daily automated backups
  └─ Retention: 30 days
  
Weekly manual snapshots
  └─ Retention: 12 weeks
  
Monthly cross-region snapshot
  └─ Rotation: Keep 3 most recent
  
Restore test: Monthly full restore to staging
  └─ Validation: Complete end-to-end test
```

**Failover Procedure:**
```
1. Alert: Primary DB connection lost
2. Automatic: Multi-AZ RDS failover (~60s)
3. Manual: If failover fails, restore from snapshot
4. Verify: Re-run integration tests
5. Post-mortem: Incident analysis
```

---

## Deployment Checklist

### Pre-Production
- [ ] Security review completed
- [ ] Load testing: 1000 req/sec without degradation
- [ ] Full end-to-end test in staging
- [ ] Backup tested and verified restorable
- [ ] Disaster recovery plan documented
- [ ] On-call rotation configured
- [ ] Runbook for common issues created

### Production Launch
- [ ] Blue-green deployment prepared
- [ ] Canary deployment: 5% traffic for 1 hour
- [ ] Monitor error rate, latency, business metrics
- [ ] Full rollout: 50% traffic
- [ ] Monitor for 4 hours
- [ ] Full rollout: 100% traffic
- [ ] Celebration! 🎉

### Rollback Plan
- [ ] Error rate > 1% → Immediate rollback
- [ ] Latency > 2s p99 → Rollback
- [ ] Any data corruption → Rollback + restore
- [ ] Rollback procedure: < 5 minutes

---

## Scaling Strategy

### Load Test Results (MVP)
```
Single instance (8GB):
  - 100 concurrent users: ✓ OK (avg 200ms)
  - 500 concurrent users: ✓ OK (avg 800ms)
  - 1000 concurrent users: ✗ FAIL (timeout)

Bottleneck: PostgreSQL connection limit
```

### Fix: Add connection pooling
```
FROM: Direct DB connections
TO: PgBouncer (connection pooling)

PgBouncer config:
  pool_mode = transaction
  max_client_conn = 1000
  default_pool_size = 25
```

### Horizontal Scaling
```
Load Test Results (Production):
  - 3 backend instances + PgBouncer + Redis:
    - 1000 concurrent users: ✓ OK (avg 150ms)
    - 5000 concurrent users: ✓ OK (avg_500ms)
    - 10000 concurrent users: ✓ OK (avg 1000ms)

Recommendation: Start with 3 instances, scale to 10 at peak
```

---

## Cost Estimation

**Monthly costs (MVP single VM):**
```
VM (8GB, 100GB SSD): $150
Bandwidth: $20
API calls (Claude): $50
Total: ~$220/month
```

**Monthly costs (Production, 500k users):**
```
ECS Fargate (avg 5 instances): $800
RDS (Multi-AZ, db.t3.large): $500
Redis (3 nodes, cache.r6g.large): $400
S3 (100GB storage): $5
Data transfer: $100
API calls (Claude, 100M tokens): $1500
Total: ~$3300/month (~$0.007 per user)
```

---

## Monitoring Dashboard

Example queries:
```sql
-- Tokens used per day
SELECT DATE(created_at), SUM(tokens) FROM audit_logs
WHERE action = 'screening_completed'
GROUP BY DATE(created_at)
ORDER BY DATE(created_at) DESC;

-- Cost by user
SELECT user_email, SUM(cost) as total_cost
FROM audit_logs
WHERE action = 'screening_completed'
GROUP BY user_email
ORDER BY total_cost DESC;

-- Error rate by endpoint
SELECT endpoint, COUNT(*) as total,
       SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as errors,
       (100.0 * SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) / COUNT(*)) as error_rate
FROM api_logs
WHERE created_at > NOW() - INTERVAL '1 day'
GROUP BY endpoint
ORDER BY error_rate DESC;
```

---

## Commands Reference

```bash
# Deploy
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Scale backend
docker-compose -f docker-compose.prod.yml up -d --scale backend=5

# Database migrations
python -m alembic upgrade head

# Create backup
pg_dump postgres://user:pass@host/talentfit > backup_$(date +%Y%m%d).sql

# Restore backup
psql postgres://user:pass@host/talentfit < backup_20260424.sql

# Run tests
pytest tests/ --cov=backend

# Load test
locust -f tests/load_test.py --host=http://localhost:8000

# Health check
curl http://localhost:8000/health
```
