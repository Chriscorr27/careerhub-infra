# CareerHub Infrastructure

This directory contains the deployment and supporting infrastructure for CareerHub: a local Docker Compose stack, Kubernetes manifests, AWS helper scripts, and monitoring configuration.

## Contents

| Path | Purpose |
| --- | --- |
| `docker-compose.yml` | Local stack for the backend, MySQL, MongoDB, Redis, Kafka, Kafka UI, Prometheus, and Grafana |
| `docker/` | MySQL initialization SQL and Prometheus scrape configuration for Compose |
| `kubernetes/` | Kubernetes resources for the backend, databases, Redis, Kafka, Kafka UI, Prometheus, and Grafana |
| `secerts/backend.env.template` | Environment-variable template for local Compose setup |
| `AWS/docker-ecr.bash` | Example Docker image login, tag, and push commands for Amazon ECR |
| `AWS/create-lamda-python-layer.bash` | Builds and publishes a Python dependency layer for AWS Lambda |
| `AWS/lambda/` | Lambda handlers for upload notification, image resizing, and PDF watermarking |
| `grafana/grafana-dashboard.json` | Grafana dashboard definition |
| `documents/` | Supporting project diagrams |

## Local deployment with Docker Compose

Requirements: Docker Engine and the Docker Compose plugin. From this directory:

1. Create a local Compose environment file from the template:

   ```bash
   cp secerts/backend.env.template docker-compose.env.secret
   ```

2. Fill in the required values in `docker-compose.env.secret`. The file is ignored by Git; do not commit credentials or secrets.
3. Start the stack:

   ```bash
   docker compose up -d
   ```

4. Check service status and logs:

   ```bash
   docker compose ps
   docker compose logs -f careerhub-backend
   ```

Stop the stack with `docker compose down`. This preserves named data volumes; to remove application data as well, review the effect of `docker compose down --volumes` before using it.

The Compose configuration exposes the backend on port `8000`, MySQL on `3316`, MongoDB on `27017`, Redis on `6379`, Kafka on `9092` and `29092`, Kafka UI on `8086`, Prometheus on `9090`, and Grafana on `3000`. Adjust ports if these conflict with services on your machine.

The backend container mounts the local AWS credentials directory read-only at `/root/.aws`; configure AWS credentials locally if using AWS-backed functionality.

> **Security:** The Compose file is intended as a development setup, not a production deployment. Review and replace development credentials, avoid exposing infrastructure ports publicly, and use managed secrets and secure network configuration for shared or production environments.

## Kubernetes deployment

The `kubernetes/` directory contains separate manifests for the backend and its dependencies. Before applying them:

- Create the Kubernetes Secret(s) expected by the manifests using your own secure values. Do not apply example secret manifests without reviewing their contents and replacing any demonstration credentials.
- Review persistent-volume configuration and ensure any host paths or storage classes are supported by your cluster.
- Review image names, load balancer exposure, probes, resource limits, and AWS credential access for your environment.

Apply the reviewed manifests individually in dependency order: secret/configuration resources, storage and data services, Kafka, then the backend and observability services. For example:

```bash
kubectl apply -f kubernetes/mysql.yaml
kubectl apply -f kubernetes/mongodb.yaml
kubectl apply -f kubernetes/redis.yaml
kubectl apply -f kubernetes/kafka-app.yaml
kubectl apply -f kubernetes/careerhub-backend.yaml
```

Apply `kafka-ui.yaml`, `prometheus-config.yaml`, `prometheus.yaml`, and `grafana.yaml` as needed. The manifests are starting points: validate cluster-specific storage, credentials, networking, and resource requirements before deployment.

## AWS Lambda functions

The Python handlers are under `AWS/lambda/`:

| Function | Handler file | Purpose and integration |
| --- | --- | --- |
| Upload notification | `notifiy-backend/lambda_function.py` | Accepts an API Gateway-style request containing an S3 upload event, authenticates to the backend, signs the upload details with HMAC-SHA256, and sends a `PATCH` request to `/api/v1/files/file-uploaded`. |
| Image resizing | `resize-image/lambda_function.py` | Reads an image from S3 and returns it as a base64-encoded HTTP response. It takes the object key from `rawPath` and an optional target width from the `w` query parameter. |
| PDF watermarking | ` after-s3-file-uploaded/lamdba_function.py` | Handles S3 object-created events for PDF or TXT files, watermarks the document, and uploads the resulting PDF to a destination bucket. The supporting `process_pdf.py` contains the PDF conversion and watermark logic. |

Configure the relevant integrations when creating the functions:

- **Upload notification:** provide `API_BASE_URL`, `AWS_EMAIL`, `AWS_PASSWORD`, and `AWS_SECRET`. The invocation event must include `timestamp`, `requestContext.requestId`, and `requestPayload.Records[0].s3.object.key`. Protect these credentials with Lambda environment encryption or a secrets manager. The Lambda role needs permission to write logs; its backend access must be limited to the required route.
- **Image resizing:** provide `SOURCE_BUCKET` or use the handler's default. Configure an HTTP integration that forwards the requested path and query parameters, and grant the execution role `s3:GetObject` access to the source bucket. The handler imports Pillow (`PIL`), so deploy a compatible Pillow package or Lambda layer for the selected runtime and architecture.
- **PDF watermarking:** optionally provide `DESTINATION_BUCKET` and `WATERMARK_TEXT` or use the handler defaults. Configure an S3 object-created notification on the source bucket and grant the role read access to source objects and write access to destination objects. Attach a compatible layer containing `pypdf` and `reportlab`; `AWS/create-lamda-python-layer.bash` is an example layer publishing script. Restrict the trigger to supported input suffixes or prefixes and keep the destination bucket outside the trigger scope to prevent recursive invocations. The function uses `/tmp` for intermediate files; set sufficient Lambda temporary storage and timeout for expected PDF sizes.

Select a supported Python runtime and architecture, then package and configure each handler and its dependencies for that target. Validate event shapes, IAM permissions, bucket names, API Gateway binary response settings, and resource limits in the AWS environment before enabling production triggers.

## AWS helper scripts

The scripts in `AWS/` are operational examples and require the AWS CLI, Docker (for ECR operations), and valid AWS credentials. Review and update account, region, image, and layer settings for your AWS environment before running them. Run the Lambda layer script only from a dedicated, disposable working directory: it removes and recreates a local `python/` directory and `lambda_layer.zip` before publishing the layer. Its current settings target Python 3.14 on x86_64; ensure that runtime is supported by the target Lambda environment or adjust the script's runtime, Python version, and architecture together.

## Observability

Docker Compose and Kubernetes include Prometheus and Grafana configuration. Prometheus is configured to scrape the backend metrics endpoint at `/actuator/prometheus`. Grafana's dashboard definition is in `grafana/grafana-dashboard.json`; import it into Grafana as appropriate for your environment.
