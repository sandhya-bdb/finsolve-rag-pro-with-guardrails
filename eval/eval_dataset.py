"""
eval_dataset.py — Golden Q&A evaluation dataset for FinSolve RAG Pro.

20 hand-crafted question-answer pairs covering all 5 role domains.
Used by the RAGAS evaluation pipeline to measure retrieval quality
and answer correctness before deploying changes.
"""

EVAL_DATASET = [
    # ── Finance (4 questions) ───────────────────────
    {
        "question": "What was the total revenue for Q3?",
        "ground_truth": "The Q3 revenue figures are documented in the finance department reports.",
        "role": "finance",
        "contexts_keywords": ["revenue", "quarter", "Q3", "finance"],
        "domain": "finance",
    },
    {
        "question": "What are the expense categories in the annual budget?",
        "ground_truth": "Budget expense categories include operational costs, salaries, marketing, and infrastructure.",
        "role": "finance",
        "contexts_keywords": ["budget", "expense", "annual", "cost"],
        "domain": "finance",
    },
    {
        "question": "What is the process for invoice approval?",
        "ground_truth": "Invoice approval follows a multi-step process involving department heads and finance review.",
        "role": "finance",
        "contexts_keywords": ["invoice", "approval", "process", "finance"],
        "domain": "finance",
    },
    {
        "question": "How is payroll processed at FinSolve?",
        "ground_truth": "Payroll is processed monthly through the HR and finance departments.",
        "role": "finance",
        "contexts_keywords": ["payroll", "salary", "monthly", "HR"],
        "domain": "finance",
    },

    # ── HR (4 questions) ────────────────────────────
    {
        "question": "What is the leave policy for employees?",
        "ground_truth": "Employees are entitled to paid leave as per the HR policy document.",
        "role": "hr",
        "contexts_keywords": ["leave", "policy", "vacation", "employee"],
        "domain": "hr",
    },
    {
        "question": "How does the performance review process work?",
        "ground_truth": "Performance reviews are conducted semi-annually with manager and peer feedback.",
        "role": "hr",
        "contexts_keywords": ["performance", "review", "appraisal", "manager"],
        "domain": "hr",
    },
    {
        "question": "What benefits are provided to full-time employees?",
        "ground_truth": "Full-time employees receive health insurance, provident fund, and other benefits.",
        "role": "hr",
        "contexts_keywords": ["benefits", "insurance", "employee", "health"],
        "domain": "hr",
    },
    {
        "question": "What is the onboarding process for new hires?",
        "ground_truth": "New hires complete a structured onboarding program covering compliance, tools, and team introduction.",
        "role": "hr",
        "contexts_keywords": ["onboarding", "new hire", "compliance", "orientation"],
        "domain": "hr",
    },

    # ── Engineering (4 questions) ───────────────────
    {
        "question": "What is the deployment process for production releases?",
        "ground_truth": "Production deployments follow a CI/CD pipeline with automated tests, code review, and staged rollouts.",
        "role": "engineering",
        "contexts_keywords": ["deployment", "CI/CD", "production", "pipeline"],
        "domain": "engineering",
    },
    {
        "question": "How are incidents handled in the engineering team?",
        "ground_truth": "Incidents are tracked in the incident management system with defined SLA and postmortem processes.",
        "role": "engineering",
        "contexts_keywords": ["incident", "SLA", "postmortem", "engineering"],
        "domain": "engineering",
    },
    {
        "question": "What is the system architecture overview?",
        "ground_truth": "The system uses a microservices architecture with API gateway, message queues, and distributed databases.",
        "role": "engineering",
        "contexts_keywords": ["architecture", "microservices", "API", "system"],
        "domain": "engineering",
    },
    {
        "question": "What coding standards does the team follow?",
        "ground_truth": "The engineering team follows PEP 8 for Python and enforces standards via linters in CI.",
        "role": "engineering",
        "contexts_keywords": ["coding", "standards", "linter", "review"],
        "domain": "engineering",
    },

    # ── Marketing (4 questions) ─────────────────────
    {
        "question": "What is the current marketing campaign strategy?",
        "ground_truth": "The current campaign focuses on digital channels including social media and content marketing.",
        "role": "marketing",
        "contexts_keywords": ["campaign", "strategy", "digital", "marketing"],
        "domain": "marketing",
    },
    {
        "question": "What are the key performance indicators for marketing?",
        "ground_truth": "Marketing KPIs include CTR, conversion rate, customer acquisition cost, and ROI.",
        "role": "marketing",
        "contexts_keywords": ["KPI", "CTR", "conversion", "ROI"],
        "domain": "marketing",
    },
    {
        "question": "How is the marketing budget allocated across channels?",
        "ground_truth": "The marketing budget is split across social media, SEO, events, and paid advertising.",
        "role": "marketing",
        "contexts_keywords": ["budget", "channels", "social", "SEO"],
        "domain": "marketing",
    },
    {
        "question": "What is the brand guideline for external communications?",
        "ground_truth": "Brand guidelines specify tone of voice, logo usage, color palette, and messaging frameworks.",
        "role": "marketing",
        "contexts_keywords": ["brand", "guideline", "communication", "tone"],
        "domain": "marketing",
    },

    # ── General / Employee (4 questions) ───────────
    {
        "question": "What is the company's remote work policy?",
        "ground_truth": "FinSolve supports a hybrid work model with defined in-office days and remote work guidelines.",
        "role": "employee",
        "contexts_keywords": ["remote", "hybrid", "work", "policy"],
        "domain": "general",
    },
    {
        "question": "How do I raise a grievance or HR complaint?",
        "ground_truth": "Employees can raise grievances through the HR portal or by contacting the POSH committee.",
        "role": "employee",
        "contexts_keywords": ["grievance", "complaint", "HR", "POSH"],
        "domain": "general",
    },
    {
        "question": "What is the code of conduct for FinSolve employees?",
        "ground_truth": "The code of conduct covers ethics, data privacy, conflict of interest, and professional behavior.",
        "role": "employee",
        "contexts_keywords": ["code of conduct", "ethics", "behavior", "policy"],
        "domain": "general",
    },
    {
        "question": "How do I request IT support?",
        "ground_truth": "IT support can be requested via the internal helpdesk portal or by emailing support@finsolve.com.",
        "role": "employee",
        "contexts_keywords": ["IT", "support", "helpdesk", "portal"],
        "domain": "general",
    },
]
