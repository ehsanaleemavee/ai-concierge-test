# ai-concierge-test

Disposable AWS test rig for the Jazzware rebuild plan: CloudFront -> ALB -> four ECS Fargate
apps -> RDS Postgres 16 + ElastiCache Redis, all in a new VPC. Everything is named
`jazzaiconcierge-test-*`. Smallest sizes, one NAT, no deletion protection.

## The four apps (`services/`, each its own image)
| App | What it does | Port |
| --- | --- | --- |
| `web` | HTTP API: `/health /db /redis /status` | 8000 (via ALB) |
| `voice` | WebSockets `/ws/echo`, `/ws/hold?seconds=300` | 8000 (via ALB, path `/ws/*`) |
| `worker` | Pops jobs from Redis, writes them to Postgres | none |
| `scheduler` | Heartbeat to Postgres + enqueues a job in Redis every 30s | none |

## Run locally first
```bash
docker compose up --build
curl localhost:8000/status      # counts grow every ~10s: scheduler -> Redis -> worker -> Postgres
```

## Network (verify before apply)
| Tier | AZ a | AZ b |
| --- | --- | --- |
| VPC | 10.20.0.0/16 | |
| Public (ALB, NAT) | 10.20.0.0/24 | 10.20.1.0/24 |
| Private app (ECS) | 10.20.10.0/24 | 10.20.11.0/24 |
| Data (RDS, Redis) | 10.20.20.0/24 | 10.20.21.0/24 |

## Deploy to AWS (first time)
Terraform asks for the region (no default). Use ap-southeast-1.
```bash
cd terraform
terraform init
terraform apply -target='aws_ecr_repository.svc'   # 1. create the four image repos only
cd ..
./scripts/push-images.sh ap-southeast-1            # 2. push the first four images
cd terraform
terraform apply                                    # 3. everything else (~15 min)
```
Open the `cloudfront_url` output. `curl http://<alb_dns_name>/` must return **403**.

## Automatic deploys (GitHub Actions)
Every push to `main` builds all four images, pushes them to ECR and rolls each ECS service
(`deploy.yml`), then smoke-tests through CloudFront. Pull requests only run `ci.yml`.
Terraform infrastructure changes are NOT auto-applied; run `terraform apply` yourself.

One-time setup after the first `terraform apply` (GitHub -> repo -> Settings -> Secrets and
variables -> Actions):
- Secret `AWS_ROLE_ARN` = output `github_deploy_role_arn`
- Variable `AWS_REGION` = `ap-southeast-1`
- Variable `CLOUDFRONT_URL` = output `cloudfront_url` (enables the smoke test)

"OIDC" = GitHub hands each run a short-lived token and AWS lets it assume a role that trusts only
`ehsanaleemavee/ai-concierge-test` on `main`. Terraform creates that role; no AWS keys are stored.
If the account already has a GitHub OIDC provider, apply with `-var enable_github_oidc=false`.

To prove it works: change the `/` response text in `services/web/main.py`, push to `main`, watch
the Actions tab, then `curl <cloudfront_url>/`.

## Destroy
`terraform destroy` removes everything Terraform created (VPC, RDS, Redis, ALB, CloudFront, ECS,
ECR repos and images, secrets, IAM roles, the OIDC provider). Needs the same local state file and
region. Not removed: nothing billable. Old ECS task-definition revisions registered by Actions
stay as free inactive records. CloudFront deletion takes ~15 minutes.

## Test-only shortcuts (not for prod)
CloudFront -> ALB runs over HTTP (no custom domain/cert); the secret header and CloudFront prefix
list still block direct access. Secrets live in local Terraform state. Single NAT, single-AZ RDS,
single Redis node, Spot tasks.
