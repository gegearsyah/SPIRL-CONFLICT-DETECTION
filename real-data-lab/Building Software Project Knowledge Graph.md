# **Event-Driven Write Policy Layer for Multi-Agent Software Projects: A Four-Class Conflict Framework**

The convergence of multi-agent software engineering and distributed knowledge graph (KG) management necessitates robust, event-driven commit-time conflict detection mechanisms.1 As organizations transition to highly federated architectures—exemplified by developer portals like Backstage 2 and scalable deployment backends like GitLab 3—the probability of concurrent, contradictory architectural decisions increases exponentially. When autonomous software agents or distributed engineering teams write infrastructure-as-code (IaC), architectural decision records (ADRs), or configuration specifications to a shared repository, semantic and structural collisions are inevitable.4

This report outlines the foundational baseline and conflict evaluation corpus for a shared project knowledge graph formalized in the Software Knowledge Framework (SKF) format. By modeling a hybrid enterprise platform—utilizing Backstage as the cataloging and templating interface and GitLab as the persistent integration and deployment backend—this corpus provides a rigorous, public-grounded dataset for testing event-driven write policies.6

## **System Architecture and Domain Analysis**

To ensure the SKF graph represents a highly realistic software ecosystem, the baseline integrates documented architectural constraints, deployment topologies, and API contracts from the official documentation of Backstage and GitLab.5

### **Backstage Developer Portal Topologies**

Backstage operates as the centralized metadata repository and developer interface. The system relies heavily on a Kubernetes-inspired YAML descriptor format formalized in Backstage ADR002.8 The Software Catalog organizes these descriptors into three primary abstractions: Components, APIs, and Resources.7

The transition to the New Backend System fundamentally alters the deployment topology of Backstage plugins.9 Historically, plugins were initialized via procedural run.ts files. The modern architecture utilizes a declarative createBackend() registry located in the root index.ts, deprecating legacy alpha exports.10 Furthermore, Backstage mandates strict constraints on entity nomenclature to prevent routing and indexing collisions; catalog entity names must not exceed 63 characters and must strictly conform to the regex sequence of \[a-z0-9A-Z\] separated by \[-\_.\].12

In terms of data persistence, while SQLite is supported for local development, production deployments mandate PostgreSQL.13 When operating within constrained environments where multiple databases cannot be provisioned, Backstage requires the pluginDivisionMode: schema configuration to enforce strict logical isolation between plugin storage layers.14

### **GitLab Infrastructure and Scaling Constraints**

The backend deployment model is strictly defined by GitLab's Reference Architectures, which dictate precise component ratios and physical disk constraints.3 For a 10,000-user deployment, the architecture transitions to a highly available (HA) cluster relying on Praefect as the Gitaly router.15

The physical storage demands are rigid. A 10,000-user workload requires exactly three Gitaly nodes sharing 2,048 GiB of repository storage.16 Because Git operations are intensely I/O bound, GitLab strictly mandates that Gitaly SSDs sustain a minimum of 8,000 IOPS for read operations and 2,000 IOPS for write operations.17 Cloud-provider "burstable" block storage is explicitly prohibited due to the risk of IOPS exhaustion under heavy CI/CD load.17

| Service Component | Nodes (10k Architecture) | CPU / Memory Spec | Primary Role |
| :---- | :---- | :---- | :---- |
| **Consul** | 3 | 2 vCPU / 1.8 GB | Service discovery and cluster election 15 |
| **PostgreSQL** | 3 | 8 vCPU / 30 GB | Relational data persistence 15 |
| **PgBouncer** | 3 | 2 vCPU / 1.8 GB | Connection pooling 15 |
| **Redis Sentinel** | 3 | 4 vCPU / 15 GB | Distributed caching and Sidekiq queues 15 |
| **Gitaly** | 3 | 16 vCPU / 60 GB | Git repository RPC storage 15 |
| **Praefect** | 3 | 2 vCPU / 1.8 GB | Gitaly cluster router and proxy 15 |

To mitigate database locking during large-scale schema updates, GitLab employs Batched Background Migrations.18 These migrations are distributed across Sidekiq workers. To prevent Sidekiq thread starvation, the framework is hardcoded to a default execution parallelism of 2 concurrent batches.18

## **Software Knowledge Framework (SKF) Methodology**

The SKF JSON corpus is constructed to represent this interconnected ecosystem. The graph contains exactly 80 verified facts, categorized across API endpoints, decisions, constraints, features, stack components, deployments, tests, migrations, and monitoring vectors. These facts are linked by 60 relational edges (depends\_on, implements, communicates\_with, etc.) that establish the causal and structural dependencies of the system.19

The SKF format encapsulates provenance via episodes, detailing the extraction and normalization events that generated the graph.20 This ensures that the baseline graph contains zero intentional contradictions. It represents a "clean state" against which the multi-agent write policy layer can evaluate incoming, potentially conflicting commits.

## **SECTION 1 — SKF JSON**

JSON

{  
  "skf\_version": "1.2",  
  "exported\_at": "2026-04-02T10:44:00Z",  
  "source": {  
    "agent": "deep-research-public-extractor",  
    "basis\_exported\_at": "2026-04-02T10:44:00Z",  
    "basis\_corpus\_slug": "backstage-gitlab-synthesis",  
    "paper3\_experiment\_id": "public-grounded-baseline"  
  },  
  "project": {  
    "name": "Project Core Platform",  
    "description": "A synthesized enterprise developer platform leveraging Backstage as the portal and GitLab as the deployment backend, modeled for multi-agent write conflict detection.",  
    "slug": "project-core-platform",  
    "tags": \["research", "paper3", "public-grounded"\]  
  },  
  "facts":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-api-02",  
      "layer": "product",  
      "category": "api\_endpoint",  
      "value": "The Search plugin utilizes the SearchApi to communicate with the search-backend, querying indices compiled by collators like DefaultCatalogCollatorFactory.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-api-03",  
      "layer": "product",  
      "category": "api\_endpoint",  
      "value": "POST /catalog/locations registers a software component by submitting a location URL pointing to a catalog-info.yaml file.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "api\_spec", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-api-04",  
      "layer": "product",  
      "category": "api\_endpoint",  
      "value": "The endpoint /create/actions enumerates all installed Scaffolder actions, including schemas and examples for actions such as publish:github.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-api-05",  
      "layer": "product",  
      "category": "api\_endpoint",  
      "value": "The metricsHandler exposes a /metrics endpoint utilized by express-prom-bundle to serve Prometheus runtime and router instrumentation metrics.",  
      "confidence": 0.95,  
      "references":,  
      "metadata": {"source\_type": "tutorial", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-api-06",  
      "layer": "product",  
      "category": "api\_endpoint",  
      "value": "The RBAC plugin leverages the permissionsRegistry service to enforce endpoints; resources such as catalog.entity.read govern access across the catalog API.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-api-07",  
      "layer": "product",  
      "category": "api\_endpoint",  
      "value": "TechDocs deprecates the TechDocsApi in favor of the routing mechanisms available in @backstage/plugin-techdocs-react for accessing generated documentation.",  
      "confidence": 0.9,  
      "references":,  
      "metadata": {"source\_type": "api\_spec", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-api-08",  
      "layer": "product",  
      "category": "api\_endpoint",  
      "value": "The action list-scaffolder-tasks supports querying scaffolder tasks with optional ownership filtering and pagination.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "repo\_readme", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-api-09",  
      "layer": "product",  
      "category": "api\_endpoint",  
      "value": "The AnalyticsApi provides an event-based interface that forwards usage telemetry to destinations like Google Analytics 4.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-api-10",  
      "layer": "product",  
      "category": "api\_endpoint",  
      "value": "The FetchApi provides an authenticated wrapper for backend calls, automatically injecting the Backstage identity token into outgoing HTTP requests.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-api-11",  
      "layer": "product",  
      "category": "api\_endpoint",  
      "value": "The get-scaffolder-task-logs action retrieves log events for a given scaffolder task, with support for cursor tracking.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "repo\_readme", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-api-12",  
      "layer": "product",  
      "category": "api\_endpoint",  
      "value": "The GitLab chatops command \`/chatops gitlab run batched\_background\_migrations list\` queries active migration job statuses.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-api-13",  
      "layer": "product",  
      "category": "api\_endpoint",  
      "value": "The GitLab chatops command \`/chatops gitlab run batched\_background\_migrations status \<MIGRATION\_ID\>\` isolates specific schema update states.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-api-14",  
      "layer": "product",  
      "category": "api\_endpoint",  
      "value": "The IdentityApi is utilized to access the signed-in user's identity entity reference and profile in the frontend.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-api-15",  
      "layer": "product",  
      "category": "api\_endpoint",  
      "value": "The API plugin endpoint \`GET /api/catalog/entities/by-query?filter=kind=API\` streams YAML spec definitions encoded as JSON payloads.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-dec-01",  
      "layer": "product",  
      "category": "decision",  
      "value": "ADR002: The software catalog strictly adopts a Kubernetes-inspired YAML descriptor format utilizing apiVersion, kind, metadata, and spec fields.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "adr", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-dec-02",  
      "layer": "product",  
      "category": "decision",  
      "value": "ADR005: Catalog entities are modeled around three core constructs: Component (software piece), API (component boundaries), and Resource (runtime infrastructure).",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "adr", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-dec-03",  
      "layer": "product",  
      "category": "decision",  
      "value": "ADR009: Entity references must map to the compound triplet \[\<kind\>:\]\[\<namespace\>/\]\<name\>, always defaulting to 'default' namespace if omitted in catalog files.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "adr", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-dec-04",  
      "layer": "product",  
      "category": "decision",  
      "value": "GitLab Architecture Decision 005: Use flexible reference architectures via Cell Sub-Archetypes and Overlays, rather than deploying an unvarying monolithic cell design.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "adr", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-dec-05",  
      "layer": "product",  
      "category": "decision",  
      "value": "Adopt external cloud storage (AWS S3 or GCS) for TechDocs deployment and configure techdocs.builder to 'external' to prevent Backstage backend memory exhaustion.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-dec-06",  
      "layer": "product",  
      "category": "decision",  
      "value": "Utilize Tamland for capacity forecasting across SaaS environments; predicted saturation resolves via Org Mover rebalancing prior to global architectural scaling.",  
      "confidence": 0.95,  
      "references": \[{"title": "GitLab Capacity Planning", "url": "https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/cells/decisions/005\_flexible\_reference\_architectures/"}\],  
      "metadata": {"source\_type": "design\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-dec-07",  
      "layer": "product",  
      "category": "decision",  
      "value": "Default Auth Policy enforces authentication for all Backstage backend requests unless dangerouslyDisableDefaultAuthPolicy is set to true during migration.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "migration\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-dec-08",  
      "layer": "product",  
      "category": "decision",  
      "value": "Deprecate alpha exports in the Backstage New Backend System, consolidating all plugin exports to the root index.ts file.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "migration\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-dec-09",  
      "layer": "product",  
      "category": "decision",  
      "value": "Execute GitLab background migrations via batched Sidekiq jobs to ensure parallel execution without exceeding database statement timeouts.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "design\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-dec-10",  
      "layer": "product",  
      "category": "decision",  
      "value": "Define RBAC permission policies via the Backstage UI to generate YAML rules that map users to resources like catalog-entity.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-con-01",  
      "layer": "product",  
      "category": "constraint",  
      "value": "Entity names in the Backstage catalog must not exceed 63 characters.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-con-02",  
      "layer": "product",  
      "category": "constraint",  
      "value": "Entity names must strictly conform to the sequence \[a-z0-9A-Z\] separated by \[-\_.\] and are treated case-insensitively.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-con-03",  
      "layer": "product",  
      "category": "constraint",  
      "value": "GitLab architectures scaling to 10k users mandate exactly 3 Gitaly nodes for high availability.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-con-04",  
      "layer": "product",  
      "category": "constraint",  
      "value": "GitLab 10k user deployments require an allocation of 2,048 GiB repository storage spanning across the Gitaly cluster.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-con-05",  
      "layer": "product",  
      "category": "constraint",  
      "value": "Gitaly nodes must be provisioned with disks capable of sustaining at least 8,000 IOPS for read operations and 2,000 IOPS for write operations.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-con-06",  
      "layer": "product",  
      "category": "constraint",  
      "value": "Burstable disk types are strictly prohibited for GitLab reference architectures due to inconsistent I/O latency.",  
      "confidence": 0.95,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-con-07",  
      "layer": "product",  
      "category": "constraint",  
      "value": "Single PostgreSQL database instances supporting Backstage must enable 'pluginDivisionMode: schema' to enforce namespace isolation across plugins.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "manual\_normalization", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-con-08",  
      "layer": "product",  
      "category": "constraint",  
      "value": "Backstage GitHub Apps cannot exceed the API rate limit; automated discovery intervals must not be configured to fire more frequently than once every 15 minutes.",  
      "confidence": 0.9,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-con-09",  
      "layer": "product",  
      "category": "constraint",  
      "value": "GitLab parallel batched background migrations must default to 2 concurrent jobs to avoid Sidekiq starvation.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-con-10",  
      "layer": "product",  
      "category": "constraint",  
      "value": "Backstage Custom Scaffolder Action IDs must employ camelCase; utilizing kebab-case results in NaN evaluation failures within JavaScript template string expressions.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "design\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-feat-01",  
      "layer": "product",  
      "category": "feature",  
      "value": "The Backstage Software Catalog centralizes service ownership and dependency metadata using YAML descriptors processed by the Catalog Ingestion Loop.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-feat-02",  
      "layer": "product",  
      "category": "feature",  
      "value": "Backstage Software Templates utilize Cookiecutter and Nunjucks to scaffold new repositories based on standardized organizational patterns.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-feat-03",  
      "layer": "product",  
      "category": "feature",  
      "value": "TechDocs provides an integrated docs-like-code experience by parsing MkDocs definitions colocated with source code.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-feat-04",  
      "layer": "product",  
      "category": "feature",  
      "value": "The Backstage Search Plugin aggregates documents across TechDocs, Catalog Entities, and APIs using composable index collators.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "repo\_readme", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-feat-05",  
      "layer": "product",  
      "category": "feature",  
      "value": "The RBAC Plugin facilitates dynamic assignment of users and groups to roles and provides a web interface for resolving access policy conflicts.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-feat-06",  
      "layer": "product",  
      "category": "feature",  
      "value": "GitLab Batched Background Migrations distribute schema migrations across distinct Sidekiq background jobs to maintain application availability during large table updates.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-feat-07",  
      "layer": "product",  
      "category": "feature",  
      "value": "The Backstage Analytics API tracks portal telemetry and supports multiplexed integrations into providers like Google Analytics 4 (GA4).",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "repo\_readme", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-feat-08",  
      "layer": "product",  
      "category": "feature",  
      "value": "The API Docs plugin processes OpenAPI, AsyncAPI, and GraphQL specifications into interactive REST visualization panels tied to Catalog components.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-feat-09",  
      "layer": "product",  
      "category": "feature",  
      "value": "GitLab Cells provide isolated, horizontally scaling tenant boundaries intended to solve multi-tenant SaaS saturation via distributed Praefect/Database rings.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "design\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-feat-10",  
      "layer": "product",  
      "category": "feature",  
      "value": "Backstage Entity Validator allows organizations to mandate rigid custom JSON Schema (draft-07) specifications over baseline catalog entity ingestion.",  
      "confidence": 0.9,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-stack-01",  
      "layer": "product",  
      "category": "stack",  
      "value": "Node.js runs the Backstage backend processes, utilizing the Express framework to mount API routers and lifecycle management.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-stack-02",  
      "layer": "product",  
      "category": "stack",  
      "value": "React powers the Backstage frontend ecosystem, employing a plugin-centric component tree.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-stack-03",  
      "layer": "product",  
      "category": "stack",  
      "value": "PostgreSQL serves as the primary relational persistence layer for both GitLab HA architectures and Backstage cross-plugin databases.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "project-core-platform", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-stack-04",  
      "layer": "product",  
      "category": "stack",  
      "value": "Praefect acts as the transparent proxy and router orchestrating GitLab's Gitaly cluster storage tier.",  
      "confidence": 1.0,  
      "references": \[{"title": "GitLab 10k Arch", "url": "https://docs.gitlab.com/administration/reference\_architectures/10k\_users/"}\],  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-stack-05",  
      "layer": "product",  
      "category": "stack",  
      "value": "Consul governs service discovery, configuration state, and cluster election for GitLab infrastructure environments.",  
      "confidence": 1.0,  
      "references": \[{"title": "GitLab HA Components", "url": "https://docs.gitlab.com/administration/reference\_architectures/10k\_users/"}\],  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-stack-06",  
      "layer": "product",  
      "category": "stack",  
      "value": "PgBouncer pools and manages high-throughput connections targeting the PostgreSQL cluster within GitLab and Backstage deployments.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "project-core-platform", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-stack-07",  
      "layer": "product",  
      "category": "stack",  
      "value": "Redis and Redis Sentinel furnish distributed caching layers and persistent Sidekiq background job queues for GitLab HA.",  
      "confidence": 1.0,  
      "references": \[{"title": "GitLab Cache Layer", "url": "https://docs.gitlab.com/administration/reference\_architectures/10k\_users/"}\],  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-stack-08",  
      "layer": "product",  
      "category": "stack",  
      "value": "Knex.js provides the query building and migration layer for Backstage backend Database Services interfacing with Postgres/SQLite.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-stack-09",  
      "layer": "product",  
      "category": "stack",  
      "value": "Prometheus manages the collection of metric instrumentation emitted by the express-prom-bundle across the platform.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-stack-10",  
      "layer": "product",  
      "category": "stack",  
      "value": "MkDocs serves as the underlying static site generator utilized by TechDocs to compile docs-like-code markdown into HTML.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-dep-01",  
      "layer": "product",  
      "category": "deployment",  
      "value": "TechDocs Recommended Deployment offloads MkDocs generation to CI/CD pipelines, publishing artifacts to AWS S3 or GCS object storage.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-dep-02",  
      "layer": "product",  
      "category": "deployment",  
      "value": "GitLab Cloud Native Hybrid deployments locate stateless Rails/Sidekiq endpoints within Kubernetes, whilst retaining stateful databases on bare VMs.",  
      "confidence": 1.0,  
      "references": \[{"title": "GitLab Cloud Native Hybrid", "url": "https://gitlab.com/gitlab-org/gitlab/-/blob/quarantine-flaky-tests-spec-features-projects-compare\_spec-rb-176/doc/administration/reference\_architectures/\_index.md"}\],  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-dep-03",  
      "layer": "product",  
      "category": "deployment",  
      "value": "The Backstage New Backend System shifts away from run.ts patterns toward an injected ServiceRegistry located centrally in index.ts.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "migration\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-dep-04",  
      "layer": "product",  
      "category": "deployment",  
      "value": "GitLab Dedicated provides tenant-isolated SaaS deployments utilizing specialized GET (GitLab Environment Toolkit) instrumentor tooling over AWS.",  
      "confidence": 0.9,  
      "references":,  
      "metadata": {"source\_type": "design\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-dep-05",  
      "layer": "product",  
      "category": "deployment",  
      "value": "The Linux package Omnibus acts as the legacy deployment model for monolithic GitLab instances scaled via horizontal node additions.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-dep-06",  
      "layer": "product",  
      "category": "deployment",  
      "value": "The Backstage Web Application functions as the primary frontend artifact served from the host server or CDN layer.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-test-01",  
      "layer": "product",  
      "category": "test",  
      "value": "Backstage incorporates a Dry Run feature within the Scaffolder enabling template builders to test action execution logic without committing final artifacts.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-test-02",  
      "layer": "product",  
      "category": "test",  
      "value": "GitLab utilizes the db:gitlabcom-database-testing CI/CD job to emulate migrations against a cloned production schema via Database Lab.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "repo\_readme", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-test-03",  
      "layer": "product",  
      "category": "test",  
      "value": "Backstage Frontend logic is strictly tested via Jest, enforcing regression checks across the React component boundaries.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-test-04",  
      "layer": "product",  
      "category": "test",  
      "value": "GitLab database migration pipelines automatically flag unintended dataset expansion, highlighting anomalies like a \+8.00 KiB bloat during regression runs.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "repo\_readme", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-test-05",  
      "layer": "product",  
      "category": "test",  
      "value": "Software Template logic can be tested using TemplateExamples to document permutations of scaffolder inputs.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-mig-01",  
      "layer": "product",  
      "category": "migration",  
      "value": "Migrating Backstage from SQLite to PostgreSQL mandates configuring 'client: pg' and enabling schema division mode via app-config.yaml.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "migration\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-mig-02",  
      "layer": "product",  
      "category": "migration",  
      "value": "Transitioning to the Backstage New Backend System involves deprecating module exports and configuring the unified createBackend() builder.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "migration\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-mig-03",  
      "layer": "product",  
      "category": "migration",  
      "value": "GitLab Data Migrations into Cells depend on the Org Mover utility to cleanly transfer entire organizational units across tenant boundaries.",  
      "confidence": 0.9,  
      "references": \[{"title": "GitLab Cells Organization Migration", "url": "https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/organization-data-migration/"}\],  
      "metadata": {"source\_type": "design\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-mig-04",  
      "layer": "product",  
      "category": "migration",  
      "value": "Migrating TechDocs from Basic to Recommended topologies requires configuring CI/CD systems to perform static builds directed at cloud buckets.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "migration\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-mig-05",  
      "layer": "product",  
      "category": "migration",  
      "value": "The Backstage Auth Service Migration shifts all request validation to default-deny unless explicitly authorized via identity tokens.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "migration\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-mig-06",  
      "layer": "product",  
      "category": "migration",  
      "value": "Legacy GitLab background migrations were replaced wholesale by the batched background migration framework for enhanced control.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "migration\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-mig-07",  
      "layer": "product",  
      "category": "migration",  
      "value": "Deprecation of Backstage Alpha exports forces plugin maintainers to redirect import paths to the primary index during migration.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "migration\_doc", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-mon-01",  
      "layer": "product",  
      "category": "monitoring",  
      "value": "The Prometheus metric 'catalog\_processing\_duration\_seconds' gauges the holistic time spent traversing the entire catalog entity processing flow.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "repo\_readme", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-mon-02",  
      "layer": "product",  
      "category": "monitoring",  
      "value": "The metric 'catalog\_processing\_queue\_delay\_seconds' isolates the latency between entity scheduling and actual processor execution.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "repo\_readme", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-mon-03",  
      "layer": "product",  
      "category": "monitoring",  
      "value": "OpenTelemetry exports the 'scaffolder.task.duration' metric to trace the end-to-end execution lifespan of templated Backstage tasks.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "tutorial", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-mon-04",  
      "layer": "product",  
      "category": "monitoring",  
      "value": "GitLab engineers trace active batched\_background\_migrations progress and starvation signals using specialized ChatOps slash commands.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "architecture\_doc", "source\_project": "gitlab", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-mon-05",  
      "layer": "product",  
      "category": "monitoring",  
      "value": "The 'catalog\_entities\_count' metric reveals the holistic volume of ingested artifacts managed by the backend loop.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "repo\_readme", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-mon-06",  
      "layer": "product",  
      "category": "monitoring",  
      "value": "The 'backend\_tasks.task.runs.count' metric tallies execution boundaries for Background Scheduler invocations.",  
      "confidence": 1.0,  
      "references":,  
      "metadata": {"source\_type": "tutorial", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    },  
    {  
      "key": "f-mon-07",  
      "layer": "product",  
      "category": "monitoring",  
      "value": "Grafana plugins present alert dashboard integrations utilizing metrics annotated directly onto Backstage entities.",  
      "confidence": 0.9,  
      "references":,  
      "metadata": {"source\_type": "repo\_readme", "source\_project": "backstage", "realism\_level": "public\_grounded"},  
      "valid\_from": "2026-04-02T10:44:00Z",  
      "valid\_until": null  
    }  
  \],  
  "edges":,  
  "episodes":,  
      "metadata": {"source\_project": "backstage", "source\_url": "https://backstage.io/docs/features/techdocs/how-to-guides/"}  
    },  
    {  
      "id": "e-normalize-01",  
      "type": "normalization",  
      "summary": "Mapped equivalent API boundary definitions between Scaffolder /create APIs and their respective feature capabilities.",  
      "timestamp": "2026-04-02T10:44:00Z",  
      "targets": \["f-api-04", "f-api-08", "f-feat-02"\],  
      "metadata": {"source\_project": "backstage", "source\_url": "https://backstage.io/docs/features/software-templates/"}  
    },  
    {  
      "id": "e-extract-02",  
      "type": "extraction",  
      "summary": "Imported physical storage constraints from GitLab Reference Architecture matrices scaling to 10k users.",  
      "timestamp": "2026-04-02T10:44:00Z",  
      "targets": \["f-con-03", "f-con-04", "f-con-05"\],  
      "metadata": {"source\_project": "gitlab", "source\_url": "https://docs.gitlab.com/administration/dedicated/create\_instance/storage\_types/"}  
    },  
    {  
      "id": "e-baseline-cleanup-01",  
      "type": "baseline\_cleanup",  
      "summary": "Resolved naming collisions surrounding Backstage Entity constraint formats, ensuring draft-07 JSON schema rules cleanly inherited from ADR002 definitions.",  
      "timestamp": "2026-04-02T10:44:00Z",  
      "targets": \["f-con-01", "f-con-02", "f-dec-01", "f-feat-10"\],  
      "metadata": {"source\_project": "project-core-platform", "source\_url": "https://backstage.io/docs/architecture-decisions/adrs-adr002"}  
    },  
    {  
      "id": "e-extract-03",  
      "type": "extraction",  
      "summary": "Linked GitLab batched background migrations with specific ChatOps API boundaries to define operational lifecycle hooks.",  
      "timestamp": "2026-04-02T10:44:00Z",  
      "targets": \["f-api-12", "f-api-13", "f-dec-09", "f-feat-06"\],  
      "metadata": {"source\_project": "gitlab", "source\_url": "https://gitlab-org.gitlab.io/release/docs/general/database-migrations/background-migrations/"}  
    },  
    {  
      "id": "e-extract-04",  
      "type": "extraction",  
      "summary": "Imported performance metrics targets encompassing catalog queue latency and Scaffolder duration states via OpenTelemetry APIs.",  
      "timestamp": "2026-04-02T10:44:00Z",  
      "targets": \["f-mon-01", "f-mon-02", "f-mon-03", "f-api-05"\],  
      "metadata": {"source\_project": "backstage", "source\_url": "https://backstage.io/docs/tutorials/setup-opentelemetry/"}  
    },  
    {  
      "id": "e-normalize-02",  
      "type": "normalization",  
      "summary": "Synthesized the constraint boundaries for the New Backend System migration against the Auth Policy migration roadmap.",  
      "timestamp": "2026-04-02T10:44:00Z",  
      "targets": \["f-mig-02", "f-mig-05", "f-dec-07", "f-dep-03"\],  
      "metadata": {"source\_project": "backstage", "source\_url": "https://roadie.io/blog/migrating-to-backstages-new-backend-a-step-by-step-guide/"}  
    },  
    {  
      "id": "e-extract-05",  
      "type": "extraction",  
      "summary": "Defined RBAC entity interactions mapped securely via the permissionsRegistry plugin layer.",  
      "timestamp": "2026-04-02T10:44:00Z",  
      "targets": \["f-feat-05", "f-api-06", "f-dec-10"\],  
      "metadata": {"source\_project": "backstage", "source\_url": "https://backstage.spotify.com/docs/plugins/rbac"}  
    },  
    {  
      "id": "e-extract-06",  
      "type": "extraction",  
      "summary": "Extracted the schema isolation requirements required for local Postgres multi-tenant plugin routing.",  
      "timestamp": "2026-04-02T10:44:00Z",  
      "targets": \["f-con-07", "f-mig-01", "f-stack-03"\],  
      "metadata": {"source\_project": "backstage", "source\_url": "https://backstage.io/docs/tutorials/switching-sqlite-postgres/"}  
    },  
    {  
      "id": "e-baseline-cleanup-02",  
      "type": "baseline\_cleanup",  
      "summary": "Unified references between GitLab Cells architectures and Praefect scaling boundaries for large enterprise clusters.",  
      "timestamp": "2026-04-02T10:44:00Z",  
      "targets": \["f-dec-04", "f-feat-09", "f-stack-04", "f-mig-03"\],  
      "metadata": {"source\_project": "gitlab", "source\_url": "https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/cells/decisions/005\_flexible\_reference\_architectures/"}  
    }  
  \]  
}

## **SECTION 2 — Conflict Injection List and Methodological Rationale**

The foundational integrity of any Event-Driven Write Policy Layer depends entirely on its capacity to accurately classify and resolve incoming repository permutations against the canonical graph structure.5 If two automated agents simultaneously dictate opposing infrastructure modifications—for instance, one requesting SQLite storage for speed, and another requesting Postgres for concurrency—the validation engine must isolate the conflict.

This corpus categorizes multi-agent conflicts across four specific ontological vectors:

1. **Semantic Contradictions:** Direct logical oppositions to foundational architectural decisions (e.g., negating ADRs or explicitly documented frameworks).7  
2. **Dependency Impacts:** Altering or removing an upstream component, resulting in the failure or starvation of a downstream feature (e.g., ripping out Consul, thereby destroying Praefect's HA state).15  
3. **Constraint Violations:** Exceeding or ignoring explicit numerical, regular expression, or capacity limits documented in the core baseline (e.g., assigning a 100-character name to an entity when the limit is 63).12  
4. **Temporal Invalidations:** Submitting configurations that reflect obsolete system states or attempt to revert completed migrations (e.g., reintroducing a deprecated API endpoint).10

Additionally, the corpus includes ambiguous or conditionally conflicting scenarios. These tests evaluate the policy layer's capability to discern context, such as determining whether a "burstable" disk configuration is permissible in an isolated development environment versus a 10k HA production deployment.17

| ID | Based On Fact | Proposed Fact Details (Key / Category / Value / Valid From-Until) | Expected Labels | Rationale & Realism | Source Support |
| :---- | :---- | :---- | :---- | :---- | :---- |
| c-sem-01 | f-api-01 | **Key:** p-api-01 **Cat:** api\_endpoint **Val:** "Use GET /entities instead of /entities/by-query to retrieve the full unpaginated catalog data payload for UI views." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | The baseline strictly deprecates /entities due to memory exhaustion; mandating it contradicts the optimized cursor-based approach. (**Realism:** public\_grounded\_conflict) | 22 |
| c-sem-02 | f-dec-05 | **Key:** p-dec-05 **Cat:** decision **Val:** "TechDocs must be generated locally on-the-fly within the Backstage container for production to guarantee content freshness." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | Direct contradiction of the explicit decision to utilize CI/CD and external S3/GCS buckets for production environments to avoid crushing the backend Node processes. (**Realism:** public\_grounded\_conflict) | 23 |
| c-sem-03 | f-dec-07 | **Key:** p-dec-07 **Cat:** decision **Val:** "The default auth policy allows all unauthenticated backend requests to proceed by default to ease plugin testing." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | The baseline dictates that the default auth policy absolutely denies unauthenticated requests unless a specific configuration flag is invoked during migration. (**Realism:** public\_grounded\_conflict) | 25 |
| c-sem-04 | f-dec-04 | **Key:** p-dec-04 **Cat:** decision **Val:** "GitLab Cells mandates a rigid, identical reference architecture universally across all isolated cells to simplify deployments." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | Contradicts ADR 005 which dictates "flexible reference architectures" via overlays to accommodate varying tenant loads ("noisy neighbors"). (**Realism:** public\_grounded\_conflict) | 26 |
| c-sem-05 | f-dec-08 | **Key:** p-dec-08 **Cat:** decision **Val:** "All Backstage backend plugins must expose their APIs strictly through the /alpha export path to ensure isolation." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | The baseline states /alpha exports are deprecated in the new backend system and must be re-exported from the root index.ts. (**Realism:** public\_grounded\_conflict) | 10 |
| c-sem-06 | f-feat-09 | **Key:** p-feat-09 **Cat:** feature **Val:** "GitLab Cells dynamically shifts traffic between regions in real-time, functioning as a multi-region active-active cluster." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | GitLab explicitly prohibits active-active multi-region spanning due to Praefect/Database quorum requirements and split-brain risks. (**Realism:** public\_grounded\_conflict) | 3 |
| c-sem-07 | f-dec-02 | **Key:** p-dec-02 **Cat:** decision **Val:** "The Catalog strictly organizes metadata into five core entities: Component, API, Resource, Pipeline, and Artifact." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | ADR 005 explicitly scopes the core entities to three specific abstractions: Component, API, and Resource. (**Realism:** public\_grounded\_conflict) | 7 |
| c-sem-08 | f-dec-03 | **Key:** p-dec-03 **Cat:** decision **Val:** "Entity references lacking a namespace will automatically fall back to the namespace of the originating source system." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | ADR 009 establishes that omitted namespaces in URLs fall back specifically to the string 'default', not the originating source. (**Realism:** public\_grounded\_conflict) | 8 |
| c-sem-09 | f-stack-10 | **Key:** p-sem-09 **Cat:** stack **Val:** "TechDocs processing is being shifted from MkDocs to Sphinx to accommodate Python codebases." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | The entire TechDocs ecosystem is strictly coupled to MkDocs as its underlying generator. (**Realism:** hand\_authored\_realistic) | 27 |
| c-sem-10 | f-con-06 | **Key:** p-con-06 **Cat:** constraint **Val:** "GitLab reference architectures highly recommend burstable cloud block storage (e.g. gp2) to minimize operational cost." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | Burstable disk types are emphatically rejected within the reference docs due to unpredictable and inconsistent IOPS throttling under high load. (**Realism:** public\_grounded\_conflict) | 17 |
| c-sem-11 | f-dec-01 | **Key:** p-sem-11 **Cat:** decision **Val:** "Backstage entities should be defined via flat JSON arrays rather than deeply nested objects." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | ADR002 strictly mandates the Kubernetes-inspired YAML format featuring envelope boundaries (apiVersion, kind, metadata, spec). (**Realism:** public\_grounded\_conflict) | 8 |
| c-sem-12 | f-feat-10 | **Key:** p-sem-12 **Cat:** feature **Val:** "Entity validation in Roadie is exclusively governed by regular expressions hardcoded into the TypeScript codebase." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | Validation is officially handled using JSON Schema (draft-07) evaluated dynamically, not hardcoded regex. (**Realism:** public\_grounded\_conflict) | 28 |
| c-sem-13 | f-stack-01 | **Key:** p-sem-13 **Cat:** stack **Val:** "Backstage backends are compiled to static Go binaries to maximize concurrent API routing performance." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | The entire Backstage backend ecosystem is built upon Node.js and Express. (**Realism:** hand\_authored\_realistic) | 2 |
| c-sem-14 | f-api-04 | **Key:** p-sem-14 **Cat:** api\_endpoint **Val:** "Scaffolder actions are obfuscated and cannot be listed programmatically via the API." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | The /create/actions endpoint specifically exists to enumerate and document all installed Scaffolder actions and schemas. (**Realism:** public\_grounded\_conflict) | 29 |
| c-sem-15 | f-feat-06 | **Key:** p-sem-15 **Cat:** feature **Val:** "Batched background migrations in GitLab are processed on the frontend client to offset server load." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | Background migrations are strictly executed by server-side Sidekiq worker pools. (**Realism:** hand\_authored\_realistic) | 18 |
| c-sem-16 | f-api-12 | **Key:** p-sem-16 **Cat:** api\_endpoint **Val:** "GitLab ChatOps commands for background migrations have been removed in favor of a purely UI-driven interface." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | ChatOps slash commands remain a documented, primary interface for interacting with and tracing migration job statuses. (**Realism:** public\_grounded\_conflict) | 30 |
| c-sem-17 | f-test-01 | **Key:** p-sem-17 **Cat:** test **Val:** "The Scaffolder Dry Run tool actually pushes dummy commits to GitHub to test permissions." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | Dry run specifically enables template builders to test logic *without* committing any final artifacts to remote repositories. (**Realism:** hand\_authored\_realistic) | 31 |
| c-sem-18 | f-test-04 | **Key:** p-sem-18 **Cat:** test **Val:** "Database size increases during migrations are ignored by the CI pipeline as long as queries do not timeout." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | The pipeline explicitly flags unintended dataset expansions (bloat) to identify anomalies before production merges. (**Realism:** public\_grounded\_conflict) | 32 |
| c-sem-19 | f-mig-03 | **Key:** p-sem-19 **Cat:** migration **Val:** "GitLab Cells data migration requires halting all instances globally to sync Praefect state." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | Data migration relies on the Org Mover utility to cleanly transfer specific organizational boundaries without holistic downtime. (**Realism:** hand\_authored\_realistic) | 26 |
| c-sem-20 | f-api-09 | **Key:** p-sem-20 **Cat:** api\_endpoint **Val:** "The Analytics API only captures page view events and cannot track arbitrary dimensional attributes." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | The API captures deep contexts including actions, subjects, and custom dimensional attributes (key/value pairs). (**Realism:** public\_grounded\_conflict) | 33 |
| c-sem-21 | f-stack-08 | **Key:** p-sem-21 **Cat:** stack **Val:** "Backstage backend services interact with the database via raw parameterized SQL strings rather than an ORM or query builder." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | Backstage actively uses Knex.js as its query building and schema migration layer. (**Realism:** public\_grounded\_conflict) | 34 |
| c-sem-22 | f-dec-10 | **Key:** p-sem-22 **Cat:** decision **Val:** "RBAC policies in Backstage can only be configured via direct modifications to the TypeScript source files." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | The RBAC plugin is explicitly designed to allow policy and rule definitions dynamically via the Backstage UI, overriding code. (**Realism:** public\_grounded\_conflict) | 35 |
| c-sem-23 | f-dep-04 | **Key:** p-sem-23 **Cat:** deployment **Val:** "GitLab Dedicated instances share a single multi-tenant infrastructure pool on GCP." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | Dedicated provides strictly isolated tenant deployments utilizing the GitLab Environment Toolkit, primarily noted over AWS. (**Realism:** public\_grounded\_conflict) | 36 |
| c-sem-24 | f-feat-02 | **Key:** p-sem-24 **Cat:** feature **Val:** "Software Templates generate scaffolding code exclusively using Go text/template." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | The Scaffolder natively utilizes Cookiecutter and Nunjucks for its string templating. (**Realism:** hand\_authored\_realistic) | 37 |
| c-sem-25 | f-mon-05 | **Key:** p-sem-25 **Cat:** monitoring **Val:** "The catalog\_entities\_count metric strictly tracks active UI sessions viewing catalog pages." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | It measures the absolute volume of ingested artifacts held by the backend. (**Realism:** public\_grounded\_conflict) | 38 |
| c-sem-26 | f-feat-04 | **Key:** p-sem-26 **Cat:** feature **Val:** "The Backstage Search Plugin relies on Elasticsearch and prohibits custom index collators." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | The system utilizes composable internal index collators (e.g., DefaultCatalogCollatorFactory) rather than mandating Elasticsearch. (**Realism:** public\_grounded\_conflict) | 39 |
| c-sem-27 | f-feat-08 | **Key:** p-sem-27 **Cat:** feature **Val:** "The API Docs plugin is limited strictly to rendering REST OpenAPI v2; GraphQL is not supported." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | The API Docs plugin natively supports OpenAPI (v2/v3), AsyncAPI, and GraphQL. (**Realism:** public\_grounded\_conflict) | 40 |
| c-sem-28 | f-mon-07 | **Key:** p-sem-28 **Cat:** monitoring **Val:** "Grafana alert dashboards cannot be integrated into Backstage entity views natively." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | The Grafana plugin natively lists alerts and embeds dashboards using entity annotations. (**Realism:** public\_grounded\_conflict) | 41 |
| c-sem-29 | f-api-10 | **Key:** p-sem-29 **Cat:** api\_endpoint **Val:** "Backend plugins must manually parse and sign JWT headers using custom Node middleware." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | The FetchApi automatically authenticates and injects the necessary Backstage identity tokens into HTTP requests. (**Realism:** hand\_authored\_realistic) | 42 |
| c-sem-30 | f-api-06 | **Key:** p-sem-30 **Cat:** api\_endpoint **Val:** "The catalog API restricts all read access to administrator tokens only by default." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | RBAC dictates policy, but by default (or via catalog.entity.read policies), read access is broadly granted, not strictly restricted to admins. (**Realism:** hand\_authored\_realistic) | 43 |
| c-sem-31 | f-api-14 | **Key:** p-sem-31 **Cat:** api\_endpoint **Val:** "The IdentityApi is deprecated and replaced by OAuth proxy headers." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | IdentityApi remains the core component for accessing signed-in user identity entity references in the frontend. (**Realism:** hand\_authored\_realistic) | 42 |
| c-sem-32 | f-api-07 | **Key:** p-sem-32 **Cat:** api\_endpoint **Val:** "TechDocs relies entirely on TechDocsApi for all frontend routing operations." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | TechDocsApi is deprecated; routing is now handled natively via React mechanisms in @backstage/plugin-techdocs-react. (**Realism:** public\_grounded\_conflict) | 44 |
| c-sem-33 | f-dec-09 | **Key:** p-sem-33 **Cat:** decision **Val:** "Batched background migrations block the main application thread to guarantee schema consistency." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | They execute via asynchronous Sidekiq jobs specifically to *prevent* blocking the main thread and avoiding timeouts. (**Realism:** public\_grounded\_conflict) | 18 |
| c-sem-34 | f-stack-07 | **Key:** p-sem-34 **Cat:** stack **Val:** "Memcached is preferred over Redis for GitLab's background job queues." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | GitLab strictly relies on Redis and Redis Sentinel for Sidekiq queues. (**Realism:** hand\_authored\_realistic) | 15 |
| c-sem-35 | f-mig-06 | **Key:** p-sem-35 **Cat:** migration **Val:** "The legacy background migration framework runs in parallel alongside batched migrations in GitLab v14+." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | The legacy framework was fully deprecated and replaced by the batched framework. (**Realism:** public\_grounded\_conflict) | 18 |
| c-sem-36 | f-mon-02 | **Key:** p-sem-36 **Cat:** monitoring **Val:** "catalog\_processing\_queue\_delay\_seconds measures network latency between Backstage and GitHub." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | It exclusively measures the internal delay between entity scheduling and catalog processor execution. (**Realism:** public\_grounded\_conflict) | 45 |
| c-sem-37 | f-mon-04 | **Key:** p-sem-37 **Cat:** monitoring **Val:** "GitLab background migrations can only be tracked by querying the PostgreSQL database directly via psql." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | Engineers can easily trace migrations using the built-in ChatOps slash commands. (**Realism:** public\_grounded\_conflict) | 30 |
| c-sem-38 | f-mon-06 | **Key:** p-sem-38 **Cat:** monitoring **Val:** "backend\_tasks.task.runs.count is a counter for frontend UI page reloads." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | It explicitly tallies execution boundaries for the backend Background Scheduler. (**Realism:** public\_grounded\_conflict) | 46 |
| c-sem-39 | f-test-05 | **Key:** p-sem-39 **Cat:** test **Val:** "TemplateExamples are dynamically generated by OpenAI models to test Scaffolder inputs." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | They are statically defined artifacts used to document and validate input permutations. (**Realism:** hand\_authored\_realistic) | 29 |
| c-sem-40 | f-dep-06 | **Key:** p-sem-40 **Cat:** deployment **Val:** "The Backstage Web Application must be compiled to WebAssembly for deployment." **Valid:** 2026-04-02T10:44Z \- null | semantic\_contradiction | It is a standard React SPA artifact served from a host server or CDN. (**Realism:** hand\_authored\_realistic) | 47 |
| c-dep-01 | f-dep-01, f-feat-03 | **Key:** p-dep-01 **Cat:** deployment **Val:** "We are decommissioning our AWS S3 and GCS infrastructure to rely exclusively on local Kubernetes volume mounts." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Decommissioning external object storage fundamentally breaks the TechDocs Recommended Deployment model which depends on S3/GCS. (**Realism:** public\_grounded\_conflict) | 23 |
| c-dep-02 | f-stack-07, f-dec-09 | **Key:** p-dep-02 **Cat:** stack **Val:** "Sidekiq is being removed from the architecture to adopt a synchronous direct execution model for schema updates." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Removing Sidekiq utterly destroys the GitLab batched background migrations mechanism, preventing any large schema migrations. (**Realism:** hand\_authored\_realistic) | 48 |
| c-dep-03 | f-stack-03, f-con-07 | **Key:** p-dep-03 **Cat:** migration **Val:** "Backstage environments will fully revert from PostgreSQL to SQLite in production to simplify backups." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Reverting to SQLite breaks the pluginDivisionMode: schema logic, preventing safe plugin isolation and scale. (**Realism:** public\_grounded\_conflict) | 14 |
| c-dep-04 | f-test-02 | **Key:** p-dep-04 **Cat:** deployment **Val:** "The Database Lab environment is being retired to save infrastructure licensing costs." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Retiring Database Lab incapacitates the db:gitlabcom-database-testing job, removing all automated testing for DB migrations. (**Realism:** hand\_authored\_realistic) | 32 |
| c-dep-05 | f-stack-05, f-stack-04 | **Key:** p-dep-05 **Cat:** stack **Val:** "Consul will be stripped from the stack to reduce latency." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Removing Consul removes the required service discovery and configuration synchronization required by Praefect and Postgres HA in 10k setups. (**Realism:** public\_grounded\_conflict) | 15 |
| c-dep-06 | f-stack-01, f-stack-08 | **Key:** p-dep-06 **Cat:** stack **Val:** "Node.js will be replaced by a Python ASGI runtime for the Backstage backend." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Removing Node entirely breaks Knex.js, Express, and all dependent Backstage core plugins. (**Realism:** hand\_authored\_realistic) | 2 |
| c-dep-07 | f-stack-06 | **Key:** p-dep-07 **Cat:** stack **Val:** "PgBouncer is uninstalled to allow direct persistent connections to Postgres." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Disabling connection pooling triggers catastrophic connection exhaustion on the Postgres HA nodes at 10k scale. (**Realism:** public\_grounded\_conflict) | 15 |
| c-dep-08 | f-feat-10 | **Key:** p-dep-08 **Cat:** feature **Val:** "JSON Schema validation libraries have been removed from the CI pipeline to speed up builds." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Removing JSON Schema prevents the Entity Validator from checking catalog metadata boundaries. (**Realism:** hand\_authored\_realistic) | 28 |
| c-dep-09 | f-stack-10, f-feat-03 | **Key:** p-dep-09 **Cat:** stack **Val:** "MkDocs relies on Python 2.7, which we are uninstalling globally from all CI images." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Purging Python environment directly breaks TechDocs static artifact generation logic. (**Realism:** hand\_authored\_realistic) | 27 |
| c-dep-10 | f-feat-02 | **Key:** p-dep-10 **Cat:** stack **Val:** "Cookiecutter binaries have been purged from the Scaffolder base image due to vulnerability scans." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Without Cookiecutter, Software Templates lose the ability to generate the baseline skeleton structures for new repositories. (**Realism:** hand\_authored\_realistic) | 37 |
| c-dep-11 | f-stack-04, f-con-03 | **Key:** p-dep-11 **Cat:** stack **Val:** "Praefect proxies are being bypassed; Gitaly clients will connect directly to specific nodes via local DNS routing." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Bypassing Praefect destroys the High Availability synchronization required for the 10k user cluster. (**Realism:** public\_grounded\_conflict) | 15 |
| c-dep-12 | f-feat-05 | **Key:** p-dep-12 **Cat:** stack **Val:** "The permissionsRegistry API interface is disabled to harden backend endpoints." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Shutting down the permissions registry completely disables the RBAC plugin and policy enforcement. (**Realism:** hand\_authored\_realistic) | 49 |
| c-dep-13 | f-mig-03 | **Key:** p-dep-13 **Cat:** deployment **Val:** "The Org Mover API utility has been deprecated and its endpoints shut down." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Deprecating Org Mover removes the critical mechanism required to shift organizations into GitLab Cells. (**Realism:** public\_grounded\_conflict) | 50 |
| c-dep-14 | f-api-02, f-feat-04 | **Key:** p-dep-14 **Cat:** api\_endpoint **Val:** "SearchApi endpoints are restricted to local host testing only." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Restricting the API breaks the global Search Plugin collators across the platform. (**Realism:** hand\_authored\_realistic) | 39 |
| c-dep-15 | f-stack-09, f-mon-01 | **Key:** p-dep-15 **Cat:** stack **Val:** "The express-prom-bundle middleware has been uninstalled to reduce CPU overhead." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Removing the middleware severs the Prometheus metric collection pipeline for processing durations. (**Realism:** public\_grounded\_conflict) | 38 |
| c-dep-16 | f-api-10 | **Key:** p-dep-16 **Cat:** api\_endpoint **Val:** "FetchApi token injection is disabled; tokens must be retrieved manually via localStorage." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Disabling token injection severely impacts all plugins relying on default authenticated backend requests. (**Realism:** hand\_authored\_realistic) | 42 |
| c-dep-17 | f-feat-07 | **Key:** p-dep-17 **Cat:** feature **Val:** "Google Analytics 4 API keys have been revoked by InfoSec." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Revoking keys breaks the downstream Backstage Analytics telemetry integration. (**Realism:** hand\_authored\_realistic) | 51 |
| c-dep-18 | f-mig-02, f-dep-03 | **Key:** p-dep-18 **Cat:** deployment **Val:** "The central ServiceRegistry instantiation pattern has been blocked by strict internal DI policies." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Blocking the registry instantiation blocks the core bootstrapping for the New Backend System. (**Realism:** hand\_authored\_realistic) | 9 |
| c-dep-19 | f-test-02 | **Key:** p-dep-19 **Cat:** test **Val:** "Database Lab cloning scripts have been updated to utilize ephemeral SQLite databases instead of Postgres." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Swapping to SQLite breaks compatibility testing for GitLab's Postgres-specific schema migrations. (**Realism:** hand\_authored\_realistic) | 32 |
| c-dep-20 | f-mon-03 | **Key:** p-dep-20 **Cat:** monitoring **Val:** "OpenTelemetry collectors are being migrated to a closed network inaccessible by the Scaffolder." **Valid:** 2026-04-02T10:44Z \- null | dependency\_impact | Network isolation prevents the scaffolder.task.duration metrics from reaching the observability backend. (**Realism:** hand\_authored\_realistic) | 46 |
| c-con-01 | f-con-01 | **Key:** p-con-01 **Cat:** api\_endpoint **Val:** "The catalog ingestion API accepts entity names containing up to 128 characters to support verbose identifiers." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | Catalog validation strictly rejects any entity name exceeding the 63-character limit rule. (**Realism:** public\_grounded\_conflict) | 12 |
| c-con-02 | f-con-02 | **Key:** p-con-02 **Cat:** feature **Val:** "Component names may utilize spaces to enhance readability in the software catalog UI." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | The baseline regex explicitly prohibits spaces, demanding sequences of \[a-z0-9A-Z\] separated by \[-\_.\]. (**Realism:** public\_grounded\_conflict) | 52 |
| c-con-03 | f-con-03 | **Key:** p-con-03 **Cat:** deployment **Val:** "Deploying the GitLab 10k users architecture using exactly 2 Gitaly nodes." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | GitLab strictly mandates exactly 3 Gitaly nodes for the 10,000 user reference architecture scale. (**Realism:** public\_grounded\_conflict) | 16 |
| c-con-04 | f-con-05 | **Key:** p-con-04 **Cat:** stack **Val:** "Provisioned Gitaly SSDs configured to guarantee a ceiling of 4,000 IOPS for read workloads." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | Violates the explicit physical constraint requiring a minimum of 8,000 IOPS for Gitaly read operations. (**Realism:** public\_grounded\_conflict) | 17 |
| c-con-05 | f-con-08 | **Key:** p-con-05 **Cat:** api\_endpoint **Val:** "The GitHub automated discovery module executes aggressively, polling repositories every 3 minutes." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | Exceeds the rate limit safeguard constraint which advises running providers no more frequently than once every 15 minutes. (**Realism:** public\_grounded\_conflict) | 53 |
| c-con-06 | f-con-09 | **Key:** p-con-06 **Cat:** feature **Val:** "Batched background migrations are configured to run with a default parallelism of 10 concurrent threads to speed up ingestion." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | The framework constrains the default parallelism strictly to 2 to maintain database health. (**Realism:** public\_grounded\_conflict) | 18 |
| c-con-07 | f-con-10 | **Key:** p-con-07 **Cat:** feature **Val:** "New Scaffolder Actions must use 'kebab-case' for their Action IDs (e.g., fetch-component-id)." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | Action IDs with dashes crash JS expression parsing (NaN errors); the constraint specifically demands camelCase. (**Realism:** public\_grounded\_conflict) | 37 |
| c-con-08 | f-con-04 | **Key:** p-con-08 **Cat:** deployment **Val:** "The 10k GitLab architecture cluster has been provisioned with 1024 GiB total repository storage." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | Violates the documented baseline sizing logic which requires 2048 GiB storage allocation for 10k users. (**Realism:** public\_grounded\_conflict) | 16 |
| c-con-09 | f-con-05 | **Key:** p-con-09 **Cat:** stack **Val:** "Gitaly SSDs provisioned for 1000 IOPS write operations to save on AWS EBS volumes." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | Constrains writes severely below the absolute minimum of 2000 IOPS for Gitaly writes. (**Realism:** public\_grounded\_conflict) | 17 |
| c-con-10 | f-con-07 | **Key:** p-con-10 **Cat:** migration **Val:** "Backstage Postgres configuration utilizes pluginDivisionMode: database for the unified database instance." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | For single instances, it MUST be pluginDivisionMode: schema to avoid collision limits. (**Realism:** public\_grounded\_conflict) | 14 |
| c-con-11 | f-con-01 | **Key:** p-con-11 **Cat:** api\_endpoint **Val:** "Set a global configuration to validate entity names against a 250 character limit for verbose API descriptions." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | Name property must be 63 chars max, even if the absolute URI can theoretically support up to 250 characters. (**Realism:** public\_grounded\_conflict) | 12 |
| c-con-12 | f-con-02 | **Key:** p-con-12 **Cat:** feature **Val:** "Catalog entities can now contain uppercase distinct characters mapped sensitively." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | The catalog names are explicitly treated as case-insensitive globally. (**Realism:** public\_grounded\_conflict) | 8 |
| c-con-13 | f-con-03 | **Key:** p-con-13 **Cat:** deployment **Val:** "Scale out Gitaly nodes dynamically from 3 to 15 using an Auto Scaling Group." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | Gitaly stateful nodes cannot be run in autoscaling groups; it is explicitly unsupported. (**Realism:** public\_grounded\_conflict) | 3 |
| c-con-14 | f-con-08 | **Key:** p-con-14 **Cat:** api\_endpoint **Val:** "The GitHub org discovery schedule runs continuously with zero delay between polling batches." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | Zero delay immediately breaches rate limit limits and will result in GitHub API bans. (**Realism:** hand\_authored\_realistic) | 53 |
| c-con-15 | f-con-06 | **Key:** p-con-15 **Cat:** deployment **Val:** "Migrate the database volumes to burstable tier disk types to optimize cloud expenditure." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | Explicitly breaches the constraint banning burstable disks for reference architecture topologies. (**Realism:** public\_grounded\_conflict) | 17 |
| c-con-16 | f-con-07 | **Key:** p-con-16 **Cat:** stack **Val:** "Disable pluginDivisionMode globally across all database configurations." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | Disabling this on a unified Postgres instance prevents plugins from accessing isolated schemas safely. (**Realism:** public\_grounded\_conflict) | 14 |
| c-con-17 | f-con-09 | **Key:** p-con-17 **Cat:** feature **Val:** "Set batched migration parallelism to 0 to indefinitely pause processing." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | Parallelism must be 2 minimum for processing; pausing is handled via specific chatops commands, not parallelism 0\. (**Realism:** hand\_authored\_realistic) | 18 |
| c-con-18 | f-con-10 | **Key:** p-con-18 **Cat:** test **Val:** "Validate all Scaffolder Action IDs enforcing standard snake\_case naming." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | The constraint explicitly requires camelCase for scaffolder actions to prevent JS expression errors. (**Realism:** public\_grounded\_conflict) | 29 |
| c-con-19 | f-con-04 | **Key:** p-con-19 **Cat:** deployment **Val:** "Expand 10k Gitaly cluster storage abruptly to 10 TiB object storage without altering node counts." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | A 10 TiB storage expansion drastically violates the ratio defined for the 10k config (approx 683 GiB per node). (**Realism:** public\_grounded\_conflict) | 16 |
| c-con-20 | f-con-01 | **Key:** p-con-20 **Cat:** api\_endpoint **Val:** "Accept catalog components with 0-length names to support anonymized stubs." **Valid:** 2026-04-02T10:44Z \- null | constraint\_violation | Names must be a minimum of 1 character; 0-length names are instantly rejected. (**Realism:** public\_grounded\_conflict) | 12 |
| c-tmp-01 | f-dec-07 | **Key:** p-tmp-01 **Cat:** decision **Val:** "dangerouslyDisableDefaultAuthPolicy is permanently set to true." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | Disabling the auth policy is strictly a temporary migration state. Asserting it as a permanent rule invalidates the timeline where the parameter is eventually removed. (**Realism:** hand\_authored\_realistic) | 25 |
| c-tmp-02 | f-mig-02 | **Key:** p-tmp-02 **Cat:** migration **Val:** "index.ts is completely unlinked and requests are routed back to run.ts for backend processing." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | Reverting back to run.ts temporally invalidates the concluded migration to the New Backend System which deleted run.ts entirely. (**Realism:** hand\_authored\_realistic) | 10 |
| c-tmp-03 | f-api-01 | **Key:** p-tmp-03 **Cat:** api\_endpoint **Val:** "The Catalog relies exclusively on GET /entities and disables the /entities/by-query function." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | Rolling back the API to the deprecated endpoint after /entities/by-query was implemented invalidates the system's temporal progress map. (**Realism:** public\_grounded\_conflict) | 22 |
| c-tmp-04 | f-api-07 | **Key:** p-tmp-04 **Cat:** api\_endpoint **Val:** "Re-import TechDocsApi into the routing manifest." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | Re-importing deprecated APIs after the migration to React-native routing invalidates the modernization timeline. (**Realism:** hand\_authored\_realistic) | 44 |
| c-tmp-05 | f-mig-06 | **Key:** p-tmp-05 **Cat:** migration **Val:** "Roll back the database schema to re-enable the legacy background migration framework." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | Reverting to legacy background migrations invalidates the successful transition to the batched Sidekiq framework. (**Realism:** public\_grounded\_conflict) | 18 |
| c-tmp-06 | f-mig-07 | **Key:** p-tmp-06 **Cat:** migration **Val:** "Restore the alpha exports for all major Backstage plugins." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | Re-instantiating alpha exports invalidates the deprecation and consolidation events completed during the New Backend migration. (**Realism:** hand\_authored\_realistic) | 10 |
| c-tmp-07 | f-dep-01, f-mig-04 | **Key:** p-tmp-07 **Cat:** deployment **Val:** "Set techdocs.builder back to 'local' for all production generation tasks." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | Reverting to local generation invalidates the successful migration to external CI/CD S3 deployments. (**Realism:** public\_grounded\_conflict) | 23 |
| c-tmp-08 | f-mig-01 | **Key:** p-tmp-08 **Cat:** migration **Val:** "Downgrade the primary Backstage persistence layer back to SQLite." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | The migration to Postgres was already completed; downgrading implies catastrophic reversion. (**Realism:** hand\_authored\_realistic) | 14 |
| c-tmp-09 | f-dec-04 | **Key:** p-tmp-09 **Cat:** decision **Val:** "Abandon the Tamland capacity forecasting tool in favor of legacy static alerting." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | Abandoning the forecast tooling invalidates the modern GitLab Dedicated capacity workflow established in recent iterations. (**Realism:** hand\_authored\_realistic) | 26 |
| c-tmp-10 | f-feat-10 | **Key:** p-tmp-10 **Cat:** feature **Val:** "Remove the Roadie Entity Validator to rely purely on base Backstage ingestion checks." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | Removing the schema enforcer invalidates the timeline where rigid draft-07 validations were imposed on the enterprise catalog. (**Realism:** hand\_authored\_realistic) | 28 |
| c-tmp-11 | f-api-14 | **Key:** p-tmp-11 **Cat:** api\_endpoint **Val:** "Rollback to utilizing IdentityApi for backend token exchange instead of FetchApi." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | FetchApi superseded custom IdentityApi header injections for backend calls; reverting it breaks token integrity updates. (**Realism:** public\_grounded\_conflict) | 42 |
| c-tmp-12 | f-dec-01 | **Key:** p-tmp-12 **Cat:** decision **Val:** "Revert catalog descriptor parsing back to legacy JSON formats." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | ADR002 firmly established YAML. Reverting to JSON invalidates the fundamental historic standardization decision. (**Realism:** hand\_authored\_realistic) | 8 |
| c-tmp-13 | f-mig-03 | **Key:** p-tmp-13 **Cat:** migration **Val:** "Halt the Org Mover migration and restore tenant data directly to the Legacy Cell." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | Restoring to the Legacy Cell invalidates the temporal progression of organizations migrating out to isolated cells. (**Realism:** public\_grounded\_conflict) | 50 |
| c-tmp-14 | f-api-04 | **Key:** p-tmp-14 **Cat:** api\_endpoint **Val:** "De-register the publish:github Scaffolder action, reverting to manual script execution." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | De-registering built-in actions undoes the progressive integration of standard Software Templates capabilities. (**Realism:** hand\_authored\_realistic) | 29 |
| c-tmp-15 | f-test-02 | **Key:** p-tmp-15 **Cat:** test **Val:** "Disable db:gitlabcom-database-testing job globally for the upcoming release window." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | Disabling established CI guardrails invalidates the modern integration pipeline established to catch schema regressions. (**Realism:** hand\_authored\_realistic) | 32 |
| c-tmp-16 | f-stack-10 | **Key:** p-tmp-16 **Cat:** stack **Val:** "Replace MkDocs with legacy Markdown-to-HTML conversion scripts." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | MkDocs integration represents the temporal evolution of TechDocs; scripts represent an outdated state. (**Realism:** hand\_authored\_realistic) | 27 |
| c-tmp-17 | f-feat-07 | **Key:** p-tmp-17 **Cat:** feature **Val:** "Revert GA4 telemetry streams back to Universal Analytics formats." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | Universal Analytics is defunct; reverting telemetry formats temporal tracking progression. (**Realism:** public\_grounded\_conflict) | 51 |
| c-tmp-18 | f-dec-04 | **Key:** p-tmp-18 **Cat:** decision **Val:** "Revert back to monolithic reference architectures without Overlays." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | Erases the evolutionary step dictated by ADR 005 for handling noisy-neighbor scaling. (**Realism:** public\_grounded\_conflict) | 26 |
| c-tmp-19 | f-stack-04 | **Key:** p-tmp-19 **Cat:** stack **Val:** "Remove Praefect routing from the 10k cluster configuration to revert to single-node NFS storage." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | NFS was definitively replaced by Praefect/Gitaly clusters. Reverting destroys temporal topology maps. (**Realism:** public\_grounded\_conflict) | 3 |
| c-tmp-20 | f-dep-05 | **Key:** p-tmp-20 **Cat:** deployment **Val:** "Halt Cloud Native Hybrid implementations and shift 100% of production back to Linux package Omnibus VMs." **Valid:** 2026-04-02T10:44Z \- null | temporal\_invalidation | Reverses the infrastructure modernization timeline transitioning stateful components toward Kubernetes. (**Realism:** public\_grounded\_conflict) | 55 |
| c-amb-01 | f-stack-07 | **Key:** p-amb-01 **Cat:** stack **Val:** "Redis deployments will not utilize Sentinel, running exclusively as single-node caches." **Valid:** 2026-04-02T10:44Z \- null | ambiguous | Acceptable for small/dev tiers, but heavily conflicts with the required HA layout of the 10k reference architecture which demands Sentinel. (**Realism:** ambiguous\_case) | 15 |
| c-amb-02 | f-dec-05 | **Key:** p-amb-02 **Cat:** deployment **Val:** "The techdocs.builder variable is set to 'local' for our regional test clusters." **Valid:** 2026-04-02T10:44Z \- null | ambiguous | Setting builder to 'local' violates production recommendations, but is legitimate for "test setups". Conflicts only conditionally based on environment metadata. (**Realism:** ambiguous\_case) | 23 |
| c-amb-03 | f-stack-03 | **Key:** p-amb-03 **Cat:** stack **Val:** "Use an ephemeral SQLite instance for the Backstage backend." **Valid:** 2026-04-02T10:44Z \- null | ambiguous | Perfectly valid for local plugin development/testing, but causes catastrophic failure and violates migrations if applied to production scopes. (**Realism:** ambiguous\_case) | 14 |
| c-amb-04 | f-api-08 | **Key:** p-amb-04 **Cat:** api\_endpoint **Val:** "Bypass the /create/actions endpoint and inject scaffolding logic manually into container scripts." **Valid:** 2026-04-02T10:44Z \- null | ambiguous | Anti-pattern for Backstage templates, but potentially required for highly bespoke legacy integrations that lack a defined Custom Action wrapper. (**Realism:** ambiguous\_case) | 29 |
| c-amb-05 | f-con-09 | **Key:** p-amb-05 **Cat:** feature **Val:** "Increase batched migration parallelism temporarily to 4 during off-peak hours." **Valid:** 2026-04-02T10:44Z \- null | ambiguous | Paralleism defaults to 2, but GitLab.com configures it to 4\. Permissibility is entirely contextual based on database sizing and load. (**Realism:** ambiguous\_case) | 18 |
| c-amb-06 | f-con-01 | **Key:** p-amb-06 **Cat:** api\_endpoint **Val:** "Shorten entity names to a maximum of 16 characters for the new microservice initiative." **Valid:** 2026-04-02T10:44Z \- null | ambiguous | 16 characters is well within the 63-character limit, so it is technically valid, but enforcing a global 16-char limit might conflict with inherited organizational policies. (**Realism:** ambiguous\_case) | 12 |
| c-amb-07 | f-mig-05 | **Key:** p-amb-07 **Cat:** decision **Val:** "Set dangerouslyDisableDefaultAuthPolicy to true for the specific 'legacy-importer' plugin." **Valid:** 2026-04-02T10:44Z \- null | ambiguous | The policy should be false globally, but might be permitted specifically for a scoped internal endpoint during a phased sunsetting process. (**Realism:** ambiguous\_case) | 25 |
| c-amb-08 | f-stack-10 | **Key:** p-amb-08 **Cat:** feature **Val:** "Bypass MkDocs for generating automated API diagrams from code." **Valid:** 2026-04-02T10:44Z \- null | ambiguous | Generating diagrams via a separate tool does not conflict with MkDocs handling text, but could conflict if the diagrams are expected to be compiled *by* TechDocs natively. (**Realism:** ambiguous\_case) | 27 |
| c-amb-09 | f-con-06 | **Key:** p-amb-09 **Cat:** stack **Val:** "Deploy non-production GitLab runners using burstable instances." **Valid:** 2026-04-02T10:44Z \- null | ambiguous | Burstable instances are banned for stateful HA nodes (Gitaly/Postgres), but perfectly acceptable for stateless ephemeral CI/CD runner nodes. (**Realism:** ambiguous\_case) | 17 |
| c-amb-10 | f-feat-09 | **Key:** p-amb-10 **Cat:** feature **Val:** "Deploy a single monolithic Cell spanning multiple disparate workloads." **Valid:** 2026-04-02T10:44Z \- null | ambiguous | Cells are designed to isolate workloads. A monolithic cell contradicts the design ethos, but is technically identical to a legacy standalone GitLab deployment. (**Realism:** ambiguous\_case) | 26 |
f-api-01
#### **Works cited**

1. Architecture decision record (ADR) examples for software planning, IT leadership, and template documentation \- GitHub, accessed on April 2, 2026, [https://github.com/joelparkerhenderson/architecture-decision-record](https://github.com/joelparkerhenderson/architecture-decision-record)  
2. Backstage Features \- KodeKloud Docs, accessed on April 2, 2026, [https://notes.kodekloud.com/docs/Prep-Course-Certified-Backstage-Associate-CBA-Certification/Backstage-Basics/Backstage-Features/page](https://notes.kodekloud.com/docs/Prep-Course-Certified-Backstage-Associate-CBA-Certification/Backstage-Basics/Backstage-Features/page)  
3. Reference architectures \- GitLab Docs, accessed on April 2, 2026, [https://docs.gitlab.com/administration/reference\_architectures/](https://docs.gitlab.com/administration/reference_architectures/)  
4. peter-evans/lightweight-architecture-decision-records \- GitHub, accessed on April 2, 2026, [https://github.com/peter-evans/lightweight-architecture-decision-records](https://github.com/peter-evans/lightweight-architecture-decision-records)  
5. Backstage is an open framework for building developer portals \- GitHub, accessed on April 2, 2026, [https://github.com/backstage/backstage](https://github.com/backstage/backstage)  
6. Architecture Design Documents | The GitLab Handbook, accessed on April 2, 2026, [https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/](https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/)  
7. ADR005: Catalog Core Entities | Backstage Software Catalog and ..., accessed on April 2, 2026, [https://backstage.io/docs/architecture-decisions/adrs-adr005](https://backstage.io/docs/architecture-decisions/adrs-adr005)  
8. ADR009: Entity References | Backstage Software Catalog and ..., accessed on April 2, 2026, [https://backstage.io/docs/architecture-decisions/adrs-adr009](https://backstage.io/docs/architecture-decisions/adrs-adr009)  
9. Migrating to Backstage's New Backend: A Step-By-Step Guide \- Roadie.io, accessed on April 2, 2026, [https://roadie.io/blog/migrating-to-backstages-new-backend-a-step-by-step-guide/](https://roadie.io/blog/migrating-to-backstages-new-backend-a-step-by-step-guide/)  
10. Migrating your Backend Plugin to the New Backend System | Backstage Software Catalog and Developer Platform, accessed on April 2, 2026, [https://backstage.io/docs/backend-system/building-plugins-and-modules/migrating/](https://backstage.io/docs/backend-system/building-plugins-and-modules/migrating/)  
11. Migrating your Backend to the New Backend System | Backstage Software Catalog and Developer Platform, accessed on April 2, 2026, [https://backstage.io/docs/backend-system/building-backends/migrating/](https://backstage.io/docs/backend-system/building-backends/migrating/)  
12. Descriptor Format of Catalog Entities | Backstage Software Catalog and Developer Platform, accessed on April 2, 2026, [https://backstage.io/docs/features/software-catalog/descriptor-format/](https://backstage.io/docs/features/software-catalog/descriptor-format/)  
13. Database | Backstage Software Catalog and Developer Platform, accessed on April 2, 2026, [https://backstage.io/docs/getting-started/config/database/](https://backstage.io/docs/getting-started/config/database/)  
14. Switching Backstage from SQLite to PostgreSQL, accessed on April 2, 2026, [https://backstage.io/docs/tutorials/switching-sqlite-postgres/](https://backstage.io/docs/tutorials/switching-sqlite-postgres/)  
15. Reference architecture: Up to 200 RPS or 10000 users \- GitLab Docs, accessed on April 2, 2026, [https://docs.gitlab.com/administration/reference\_architectures/10k\_users/](https://docs.gitlab.com/administration/reference_architectures/10k_users/)  
16. GitLab Dedicated storage types, accessed on April 2, 2026, [https://docs.gitlab.com/administration/dedicated/create\_instance/storage\_types/](https://docs.gitlab.com/administration/dedicated/create_instance/storage_types/)  
17. doc/administration/reference\_architectures/index.md · add-pipline-status-to-graphql-query, accessed on April 2, 2026, [https://gitlab.com/gitlab-org/gitlab/-/blob/add-pipline-status-to-graphql-query/doc/administration/reference\_architectures/index.md](https://gitlab.com/gitlab-org/gitlab/-/blob/add-pipline-status-to-graphql-query/doc/administration/reference_architectures/index.md)  
18. Batched background migrations \- GitLab Docs, accessed on April 2, 2026, [https://docs.gitlab.com/development/database/batched\_background\_migrations/](https://docs.gitlab.com/development/database/batched_background_migrations/)  
19. Background migrations \- GitLab, accessed on April 2, 2026, [https://gitlab.com/gitlab-org/gitlab/-/blob/v14.6.7-ee/doc/development/background\_migrations.md](https://gitlab.com/gitlab-org/gitlab/-/blob/v14.6.7-ee/doc/development/background_migrations.md)  
20. Kubernetes Enhancement Proposal Process \- keps \- GitHub, accessed on April 2, 2026, [https://github.com/kubernetes/enhancements/blob/master/keps/sig-architecture/0000-kep-process/README.md](https://github.com/kubernetes/enhancements/blob/master/keps/sig-architecture/0000-kep-process/README.md)  
21. Enhancements tracking repo for Kubernetes \- GitHub, accessed on April 2, 2026, [https://github.com/kubernetes/enhancements](https://github.com/kubernetes/enhancements)  
22. API | Backstage Software Catalog and Developer Platform, accessed on April 2, 2026, [https://backstage.io/docs/features/software-catalog/software-catalog-api/](https://backstage.io/docs/features/software-catalog/software-catalog-api/)  
23. TechDocs How-To guides | Backstage Software Catalog and Developer Platform, accessed on April 2, 2026, [https://backstage.io/docs/features/techdocs/how-to-guides/](https://backstage.io/docs/features/techdocs/how-to-guides/)  
24. Backstage in Production: From Developer Portal to Platform Operating System | by Sumit Kaul | Feb, 2026 | Medium, accessed on April 2, 2026, [https://medium.com/@sumit.kaul.87/backstage-in-production-from-developer-portal-to-platform-operating-system-0083121c28b1](https://medium.com/@sumit.kaul.87/backstage-in-production-from-developer-portal-to-platform-operating-system-0083121c28b1)  
25. Migrating to New Auth Services | Backstage Software Catalog and Developer Platform, accessed on April 2, 2026, [https://backstage.io/docs/tutorials/auth-service-migration/](https://backstage.io/docs/tutorials/auth-service-migration/)  
26. Cells ADR 005: Flexible Reference Architectures | The GitLab ..., accessed on April 2, 2026, [https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/cells/decisions/005\_flexible\_reference\_architectures/](https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/cells/decisions/005_flexible_reference_architectures/)  
27. TechDocs Documentation | Backstage Software Catalog and Developer Platform, accessed on April 2, 2026, [https://backstage.io/docs/features/techdocs/](https://backstage.io/docs/features/techdocs/)  
28. Roadie Backstage Entity Validator, accessed on April 2, 2026, [https://roadie.io/docs/catalog/validator/](https://roadie.io/docs/catalog/validator/)  
29. Writing Custom Actions | Backstage Software Catalog and Developer Platform, accessed on April 2, 2026, [https://backstage.io/docs/features/software-templates/writing-custom-actions/](https://backstage.io/docs/features/software-templates/writing-custom-actions/)  
30. Background Migrations \- GitLab Release Documentation, accessed on April 2, 2026, [https://gitlab-org.gitlab.io/release/docs/general/database-migrations/background-migrations/](https://gitlab-org.gitlab.io/release/docs/general/database-migrations/background-migrations/)  
31. ListActions | Backstage Software Catalog and Developer Platform, accessed on April 2, 2026, [https://backstage.io/docs/features/software-templates/api/list-actions/](https://backstage.io/docs/features/software-templates/api/list-actions/)  
32. Database migration pipeline \- GitLab Docs, accessed on April 2, 2026, [https://docs.gitlab.com/development/database/database\_migration\_pipeline/](https://docs.gitlab.com/development/database/database_migration_pipeline/)  
33. Plugin Analytics | Backstage Software Catalog and Developer Platform, accessed on April 2, 2026, [https://backstage.io/docs/plugins/analytics/](https://backstage.io/docs/plugins/analytics/)  
34. Core Backend Service APIs | Backstage Software Catalog and Developer Platform, accessed on April 2, 2026, [https://backstage.io/docs/backend-system/core-services/index/](https://backstage.io/docs/backend-system/core-services/index/)  
35. RBAC | Spotify Plugins for Backstage Developer Documentation, accessed on April 2, 2026, [https://backstage.spotify.com/docs/plugins/rbac](https://backstage.spotify.com/docs/plugins/rbac)  
36. content/handbook/engineering/architecture/design-documents/cells/\_index.md \- GitLab, accessed on April 2, 2026, [https://gitlab.com/gitlab-com/content-sites/handbook/-/blob/36f92eca7aba75e035771ceb1f70eb6c3a2448da/content/handbook/engineering/architecture/design-documents/cells/\_index.md](https://gitlab.com/gitlab-com/content-sites/handbook/-/blob/36f92eca7aba75e035771ceb1f70eb6c3a2448da/content/handbook/engineering/architecture/design-documents/cells/_index.md)  
37. Backstage Software Templates | Backstage Software Catalog and Developer Platform, accessed on April 2, 2026, [https://backstage.io/docs/features/software-templates/](https://backstage.io/docs/features/software-templates/)  
38. backstage/contrib/docs/tutorials/prometheus-metrics.md at master \- GitHub, accessed on April 2, 2026, [https://github.com/backstage/backstage/blob/master/contrib/docs/tutorials/prometheus-metrics.md](https://github.com/backstage/backstage/blob/master/contrib/docs/tutorials/prometheus-metrics.md)  
39. Search How-To guides | Backstage Software Catalog and Developer Platform, accessed on April 2, 2026, [https://backstage.io/docs/features/search/how-to-guides/](https://backstage.io/docs/features/search/how-to-guides/)  
40. Module @backstage/plugin-api-docs, accessed on April 2, 2026, [https://backstage.io/api/stable/modules/\_backstage\_plugin-api-docs.html](https://backstage.io/api/stable/modules/_backstage_plugin-api-docs.html)  
41. Backstage Plugins \- Logging & Metrics Observability \- Roadie.io, accessed on April 2, 2026, [https://roadie.io/backstage/plugins/?category=logs](https://roadie.io/backstage/plugins/?category=logs)  
42. Authentication in Backstage | Backstage Software Catalog and ..., accessed on April 2, 2026, [https://backstage.io/docs/auth/](https://backstage.io/docs/auth/)  
43. Chapter 2\. Permission policies in Red Hat Developer Hub, accessed on April 2, 2026, [https://docs.redhat.com/en/documentation/red\_hat\_developer\_hub/1.2/html/authorization/ref-rbac-permission-policies\_title-authorization](https://docs.redhat.com/en/documentation/red_hat_developer_hub/1.2/html/authorization/ref-rbac-permission-policies_title-authorization)  
44. TechDocsApi \- Backstage, accessed on April 2, 2026, [https://backstage.io/api/stable/interfaces/\_backstage\_plugin-techdocs.index.TechDocsApi.html](https://backstage.io/api/stable/interfaces/_backstage_plugin-techdocs.index.TechDocsApi.html)  
45. Help wanted: Catalog performance testing · Issue \#7097 \- GitHub, accessed on April 2, 2026, [https://github.com/backstage/backstage/issues/7097](https://github.com/backstage/backstage/issues/7097)  
46. Setup OpenTelemetry | Backstage Software Catalog and Developer Platform, accessed on April 2, 2026, [https://backstage.io/docs/tutorials/setup-opentelemetry/](https://backstage.io/docs/tutorials/setup-opentelemetry/)  
47. Architecture and technology \- Spotify for Backstage, accessed on April 2, 2026, [https://backstage.spotify.com/learn/backstage-for-all/architecture-and-technology/7-container/](https://backstage.spotify.com/learn/backstage-for-all/architecture-and-technology/7-container/)  
48. Migration Style Guide \- GitLab Docs, accessed on April 2, 2026, [https://docs.gitlab.com/development/migration\_style\_guide/](https://docs.gitlab.com/development/migration_style_guide/)  
49. Core Concepts | Spotify Plugins for Backstage Developer Documentation, accessed on April 2, 2026, [https://backstage.spotify.com/docs/plugins/rbac/core-concepts](https://backstage.spotify.com/docs/plugins/rbac/core-concepts)  
50. Cells: Organization migration | The GitLab Handbook, accessed on April 2, 2026, [https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/organization-data-migration/](https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/organization-data-migration/)  
51. community-plugins/workspaces/analytics/plugins/analytics-module-ga4/README.md at main · backstage/community-plugins \- GitHub, accessed on April 2, 2026, [https://github.com/backstage/community-plugins/blob/main/workspaces/analytics/plugins/analytics-module-ga4/README.md](https://github.com/backstage/community-plugins/blob/main/workspaces/analytics/plugins/analytics-module-ga4/README.md)  
52. scaffolder: sample templates should validate component name properly \#6687 \- GitHub, accessed on April 2, 2026, [https://github.com/backstage/backstage/issues/6687](https://github.com/backstage/backstage/issues/6687)  
53. Rate Limiting Issues | Spotify Plugins for Backstage Developer Documentation, accessed on April 2, 2026, [https://backstage.spotify.com/docs/portal/troubleshooting/rate-limiting](https://backstage.spotify.com/docs/portal/troubleshooting/rate-limiting)  
54. Feature: how to modify Catalog Entity's name length restriction. · Issue \#24958 \- GitHub, accessed on April 2, 2026, [https://github.com/backstage/backstage/issues/24958](https://github.com/backstage/backstage/issues/24958)  
55. doc/administration/reference\_architectures/\_index.md · quarantine-flaky-tests-spec-features-projects-compare\_spec-rb-176 \- GitLab, accessed on April 2, 2026, [https://gitlab.com/gitlab-org/gitlab/-/blob/quarantine-flaky-tests-spec-features-projects-compare\_spec-rb-176/doc/administration/reference\_architectures/\_index.md](https://gitlab.com/gitlab-org/gitlab/-/blob/quarantine-flaky-tests-spec-features-projects-compare_spec-rb-176/doc/administration/reference_architectures/_index.md)