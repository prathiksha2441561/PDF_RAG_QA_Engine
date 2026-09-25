import fitz  # PyMuPDF
from pathlib import Path


def create_sample_pdf():
    output_dir = Path(__file__).resolve().parent.parent / "documents"
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / "cloud_architecture_specification.pdf"

    doc = fitz.open()

    # Page 1: Architecture & Operations
    page1 = doc.new_page()
    text_p1 = """Cloud Architecture Specification
Version 2.4 - Production Reference Manual

1. Executive Overview and Service Level Agreements
The Cloud Architecture platform provides distributed microservice orchestration for high-throughput AI workloads.
The system guarantees an uptime SLA of 99.95% availability across all multi-region availability zones.
The target latency Service Level Objective (SLO) is strictly 250 milliseconds for 99th percentile (p99) retrieval requests.
Workload clusters run across primary regions in North America and Western Europe with automated failover routing.
"""
    page1.insert_text(fitz.Point(50, 72), text_p1, fontsize=12)

    # Page 2: Security & Authentication
    page2 = doc.new_page()
    text_p2 = """Cloud Architecture Specification
Section 2: Security, Authentication, and Governance

2. Identity and Access Management
The primary authentication protocol used across all external and internal API gateways is OAuth 2.0 with PKCE (Proof Key for Code Exchange).
Authentication tokens are issued as JSON Web Tokens (JWT) with a mandatory 15-minute expiration time to mitigate token theft.
For communication across public and private networks, TLS 1.3 is mandated for in-transit communication.
All persistent storage volumes enforce AES-256 encryption at rest.

3. Role-Based Access Control (RBAC)
User authorization adheres to strict least-privilege principles.
The four defined roles under RBAC are Admin, Developer, Auditor, and Guest.
Admin users possess full infrastructure provisioning rights, Developer users manage application deployments, Auditor users access read-only compliance logs, and Guest users maintain rate-limited query privileges.
"""
    page2.insert_text(fitz.Point(50, 72), text_p2, fontsize=12)

    # Page 3: Vector Search & Data Storage
    page3 = doc.new_page()
    text_p3 = """Cloud Architecture Specification
Section 3: Storage and Vector Retrieval Infrastructure

3. Data Persistence and Database Architecture
Relational document metadata, tenant settings, and security audit logs are managed using PostgreSQL 16.
Data at rest is encrypted using AES-256 across all tablespaces and block devices.
Automatic database backups run nightly at 02:00 UTC and are replicated to offsite cold storage with a 30-day retention policy.

4. Vector Retrieval System
The vector search infrastructure uses ChromaDB with an HNSW index and cosine distance metric.
It stores dense vector embeddings with an embedding dimension of 384 generated from domain-tuned sentence transformers.
Top-k similarity queries execute within the retrieval microservice with an internal latency threshold of under 50 milliseconds.
"""
    page3.insert_text(fitz.Point(50, 72), text_p3, fontsize=12)

    # Page 4: Financial Budgets & Operational Costs
    page4 = doc.new_page()
    text_p4 = """Cloud Architecture Specification
Section 4: Financial Accounting, Cost Allocation, and Service Tiers

4. Subscription Tiers and Usage Limits
The platform offers two primary enterprise subscription tiers:
The Tier 1 plan costs $49 per month with 10,000 queries, whereas the Enterprise plan costs $499 per month with unlimited queries.
Dedicated support response times are 24 hours for Tier 1 and 1 hour for Enterprise subscribers.

5. Operating Infrastructure Expenses
Operational expenditure is reviewed quarterly by engineering leadership.
The compute infrastructure budget was $120,000 in Q3, compared to $95,000 in Q2, reflecting higher model training demands.
Network data egress fee is $0.08 per gigabyte across cross-zone endpoints.
"""
    page4.insert_text(fitz.Point(50, 72), text_p4, fontsize=12)

    doc.save(str(pdf_path))
    doc.close()
    print(f"Sample PDF created successfully at: {pdf_path}")


if __name__ == "__main__":
    create_sample_pdf()
