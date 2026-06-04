"""
Core non-GUI logic for Security+ Study App.
This module contains database helpers and pure logic functions so the GUI
can remain focused on interface code.

Functions include:
- Database initialization and connection
- Adding and importing questions
- Retrieving questions and domains
- Recording attempts and calculating statistics
- Simple spaced repetition scheduling for flashcards
"""

# Import necessary modules
import sys
import sqlite3
import csv
import json
import datetime
from pathlib import Path


def resolve_asset_path(filename):
    candidates = []
    bundled = getattr(sys, '_MEIPASS', None)
    if bundled:
        bundle_path = Path(bundled)
        candidates.append(bundle_path / 'assets')
        candidates.append(bundle_path)

    project_root = Path(__file__).resolve().parents[1]
    candidates.append(project_root / 'assets')

    for base in candidates:
        candidate = base / filename
        if candidate.exists():
            return candidate
    return None

#Make a database file in a new directory in the user's home directory
APP_DIR = Path.home() / ".security_plus_study_app"
APP_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_DIR / "study.db"

# database connection helper
def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

# Initialize the database with necessary tables
def init_db():
    conn = get_conn()
    c = conn.cursor()
    
    # questions table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY,
            domain TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT,
            qtype TEXT DEFAULT 'free',
            metadata TEXT
        )
        """
    )
    
    # attempts table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY,
            question_id INTEGER,
            correct INTEGER,
            timestamp TEXT,
            FOREIGN KEY(question_id) REFERENCES questions(id)
        )
        """
    )
    
    # flashcards table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY,
            question_id INTEGER UNIQUE,
            interval INTEGER DEFAULT 1,
            ease REAL DEFAULT 2.5,
            next_review TEXT,
            FOREIGN KEY(question_id) REFERENCES questions(id)
        )
        """
    )
    
    # quizzes table for tracking quiz attempts
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY,
            domain TEXT,
            total_questions INTEGER,
            score INTEGER,
            timestamp TEXT
        )
        """
    )
    
    # quiz_answers table for tracking individual quiz question results
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS quiz_answers (
            id INTEGER PRIMARY KEY,
            quiz_id INTEGER,
            question_id INTEGER,
            user_answer TEXT,
            correct INTEGER,
            FOREIGN KEY(quiz_id) REFERENCES quizzes(id),
            FOREIGN KEY(question_id) REFERENCES questions(id)
        )
        """
    )
    conn.commit()
    conn.close()

# Add a single question to the database
def add_question(domain, question, answer, qtype='free', metadata=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO questions (domain,question,answer,qtype,metadata) VALUES (?,?,?,?,?)",
        (domain, question, answer, qtype, json.dumps(metadata) if metadata else None)
    )
    qid = c.lastrowid
    conn.commit()
    conn.close()
    return qid

def question_exists(question_text):
    """Check if a question already exists in the database."""
    conn = get_conn()
    c = conn.cursor()
    # Use exact match for question text
    c.execute("SELECT id FROM questions WHERE LOWER(TRIM(question)) = LOWER(TRIM(?))", (question_text,))
    result = c.fetchone()
    conn.close()
    return result is not None


DOMAIN_KEYWORDS = {
    "Threats, Attacks, and Mitigations": [
        # Malware types
        "malware", "trojan", "virus", "worm", "rootkit", "spyware", "ransomware", "adware",
        "botnet", "cryptolocker", "keylogger", "backdoor", "logic bomb", "wiperware",
        # Social engineering and phishing
        "phishing", "spearphishing", "smishing", "vishing", "social engineering", "pretexting",
        "baiting", "tailgating", "shoulder surfing",
        # Network attacks
        "denial of service", "dos", "ddos", "distributed denial", "syn flood", "ping flood",
        "ping of death", "smurf attack", "land attack",
        # Brute force and credential attacks
        "brute force", "credential stuffing", "password spray", "dictionary attack",
        "rainbow table", "pass the hash",
        # On-path and man-in-the-middle
        "replay attack", "spoofing", "on-path", "man-in-the-middle", "mitm", "arp spoofing",
        "dns spoofing", "arp poisoning", "cache poisoning", "dns poisoning",
        # Injection attacks
        "sql injection", "injection attack", "ldap injection", "command injection",
        "cross-site scripting", "xss", "cross-site request forgery", "csrf", "xxe",
        # Vulnerabilities and exploits
        "zero-day", "exploit", "vulnerability", "cve", "vulnerability disclosure",
        "vulnerability assessment", "penetration", "attacker", "unauthorized access",
        "privilege escalation", "lateral movement", "privilege abuse",
        # Other attack types
        "session hijacking", "session fixation", "certificate attack", "downgrade attack"
    ],
    "General Security Concepts": [
        # Core CIA triad concepts
        "confidentiality", "integrity", "availability", "non-repudiation", "cia triad",
        "authentication", "authorization", "accounting", "aaa",
        # Encryption and cryptography fundamentals
        "encryption", "cryptography", "symmetric", "asymmetric", "public key", "private key",
        "certificate", "pki", "public key infrastructure", "digital signature", "hash",
        "md5", "sha", "sha-256", "rsa", "aes", "des", "3des", "tls", "ssl",
        "diffie-hellman", "key exchange", "perfect forward secrecy", "ephemeral",
        "cipher", "cipher suite", "elliptic curve", "blockchain", "quantum",
        # Identity and access fundamentals
        "multi-factor", "mfa", "2fa", "totp", "hotp", "single sign-on", "sso",
        "saml", "oauth", "openid", "ldap", "kerberos", "rbac", "role-based",
        "attribute-based", "abac", "least privilege", "need to know",
        # Security control types
        "preventive control", "detective control", "corrective control", "compensating control",
        "technical control", "administrative control", "managerial control", "operational control",
        "physical control",
        # Secure protocols
        "dnssec", "sftp", "ssh", "secure shell", "dkim", "spf", "dmarc", "s/mime",
        "https", "tls", "imaps", "smtps",
        # Hardware security
        "tpm", "trusted platform", "hsm", "hardware security module", "secure enclave",
        "fde", "full disk encryption", "secure baseline",
        # Data concepts
        "data classification", "data handling", "masking", "tokenization", "deidentification",
        "data minimization", "data at rest", "data in transit", "data in use"
        # Email security
        "email security", "email", "smtp", "smtps", "pop3", "pop3s", "imap", "imaps", "phishing", "spoofing", 
        "dkim", "spf", "dmarc", "s/mime", "email filtering", "email gateway", "secure email", "email encryption"
        "email authentication", "email integrity", "email confidentiality"
    ],
    "Security Architecture": [
	# Network architecture
	"firewall", "next-generation firewall", "ngfw", "stateful firewall", "stateless",
	"ids", "ips", "intrusion detection", "intrusion prevention", "nids", "hids",
	"ids/ips", "waf", "web application firewall", "dlp", "data loss prevention",
	"vpn", "virtual private network", "site-to-site", "remote access", "split tunnel",
	"load balancer", "load balancing", "failover", "redundancy", "high availability",
	"virtual ip", "vip", "nat", "network address translation", "proxy", "reverse proxy",
	# Network segmentation
	"dmz", "demilitarized zone", "air gap", "air gapped", "zero trust", "microsegmentation",
	"vlan", "network segmentation", "screened subnet", "security zone",
	# Cloud architecture
	"cloud", "iaas", "paas", "saas", "faas", "hybrid cloud", "public cloud", "private cloud",
	"shared responsibility", "cloud security", "security group", "resource policy",
	"vm", "virtual machine", "hypervisor", "type 1", "type 2", "containerization",
	"docker", "kubernetes", "serverless",
	# Wireless
	"wireless", "wpa", "wpa2", "wpa3", "wep", "wpa-enterprise", "wpa-personal",
	"ieee 802.1x", "802.1x", "eap",
	# Physical security
	"physical security", "biometric", "fingerprint scan", "iris scan", "facial recognition",
	"bollard", "mantrap", "badge reader", "keypad", "card reader", "cctv",
	# Redundancy and recovery
	"raid", "backup", "replication", "warm site", "hot site", "cold site",
	"disaster recovery", "business continuity", "ups", "generator", "power"
    # Ports and protocols
    "ports", "port", "protocols", "tcp", "TCP", "udp", "UDP", "icmp", "http", "https", "ftp", "sftp",
    "ssh", "telnet", "smtp", "smtps", "pop3", "pop3s", "imap", "imaps", "dns", "dhcp", "ldap", "kerberos", "rdp", "vnc"
    "service", "well-known port", "registered port", "dynamic port"
    ],
    "Security Operations": [
        # Monitoring and logging
        "logging", "log", "audit log", "audit trail", "system log", "security log",
        "event log", "syslog", "centralized logging", "log aggregation", "siem",
        "security information event management", "soar", "security orchestration",
        "monitoring", "real-time monitoring", "continuous monitoring", "security monitoring",
        # Alerting and detection
        "alert", "alerting", "threshold", "anomaly detection", "baseline",
        "behavioral analytics", "ueba", "user behavior analytics",
        # Incident response
        "incident", "incident response", "incident management", "incident handler",
        "incident commander", "incident response plan", "incident response team",
        "incident response procedure", "incident response process",
        # Forensics and investigation
        "forensic", "forensics", "forensic investigation", "digital forensics",
        "evidence", "evidence preservation", "chain of custody", "eol", "end of life",
        "data retention", "legal hold",
        # Traffic analysis and network security
        "packet capture", "pcap", "wireshark", "tcpdump", "netflow", "network flow",
        "traffic analysis", "network analysis", "flow data",
        # Testing and assessment
        "security testing", "security assessment", "vulnerability scan", "vulnerability scanning",
        "vulnerability assessment", "penetration test", "penetration testing", "pentest",
        "red team", "blue team", "adversary simulation",
        # Auditing and compliance monitoring
        "audit", "auditing", "internal audit", "external audit", "compliance audit",
        "assessment", "evaluation", "review",
        # Reporting
        "report", "reporting", "dashboard", "dashboard reporting", "metrics", "kpi",
        "risk indicators", "risk trend", "risk trend analysis", "security metric",
        # Vulnerability management
        "vulnerability", "vulnerability management", "vulnerability disclosure",
        "responsible disclosure", "zero-day", "patch management"
    ],
    "Security Program Management and Oversight": [
        # Regulations and compliance frameworks
        "compliance", "regulatory compliance", "regulation", "regulatory", "regulatory requirement",
        "hipaa", "hitech", "gdpr", "ccpa", "pci-dss", "pci dss", "sox", "sarbanes-oxley",
        "nist", "cis", "iso", "iso 27001", "iso 27002", "iso 27035", "cobit",
        "hipaa compliance", "gdpr compliance", "ccpa compliance",
        # Standards and frameworks
        "framework", "security framework", "standard", "security standard",
        "best practice", "baseline", "security baseline", "critical security control",
        "control", "security control", "preventive control", "detective control",
        "corrective control", "compensating control",
        # Risk management
        "risk", "risk management", "risk assessment", "risk analysis", "risk evaluation",
        "risk mitigation", "risk acceptance", "risk avoidance", "risk transfer",
        "likelihood", "impact", "probability", "risk score", "risk rating",
        "quantitative risk", "qualitative risk",
        # Security governance
        "governance", "information security governance", "security governance",
        "policy", "security policy", "information security policy", "procedure",
        "standard", "guideline", "policy development",
        # Organizational practices
        "security awareness", "security training", "user training", "security culture",
        "separation of duties", "segregation of duties", "conflict of interest",
        "management review", "executive management",
        # Data protection and privacy
        "privacy", "data privacy", "personal information", "personal data", "pii",
        "sensitive data", "data classification", "data handling", "data protection",
        "data minimization", "purpose limitation", "data retention",
        # Third-party and vendor management
        "vendor", "vendor management", "third-party", "third party management",
        "service provider", "business associate", "vendor security", "vendor assessment",
        "sla", "service level agreement", "contract", "licensing", "license agreement",
        # Financial and business considerations
        "financial stability", "reputation", "business impact", "business continuity",
        "disaster recovery", "recovery time objective", "rto", "recovery point objective",
        "rpo", "continuity of operations", "coop", "business-critical", "critical system",
        # Legal and compliance monitoring
        "legal hold", "litigation hold", "compliance monitoring", "regulatory audit",
        "compliance violation", "compliance incident", "compliance requirement",
        # Risk and security program
        "information security program", "risk event", "risk register", "risk appetite",
        "risk tolerance", "risk indicator", "security metric", "kpi", "key performance indicator",
        "management", "executive management", "board", "governance committee"
    ]
}

def infer_domain(question_text):
    """Infer a CompTIA Security+ objective domain from question content."""
    text = question_text.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw.lower() in text for kw in keywords):
            return domain
    return "General"

def assign_missing_domains():
    """Infer domains for questions that are missing or still labeled as generic."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT id, question, metadata FROM questions WHERE domain IS NULL OR TRIM(domain)='' OR LOWER(domain)='general'"
    )
    rows = c.fetchall()
    updated = 0
    for row in rows:
        metadata = json.loads(row['metadata']) if row['metadata'] else {}
        explanation = metadata.get('explanation')
        inferred_domain = infer_domain(row['question'], explanation, metadata)
        c.execute("UPDATE questions SET domain=? WHERE id=?", (inferred_domain, row['id']))
        updated += 1
    conn.commit()
    c.execute("SELECT COUNT(*) FROM questions WHERE domain IS NULL OR TRIM(domain)='' OR LOWER(domain)='general'")
    remaining = c.fetchone()[0]
    conn.close()
    return {
        "updated": updated,
        "remaining": remaining
    }


def _ensure_flashcard_for(question_id):
    """Create a flashcards row for question_id if one does not exist.
    New flashcards are scheduled for today so they appear in the due list.
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM flashcards WHERE question_id=?", (question_id,))
    if not c.fetchone():
        interval = 1
        ease = 2.5
        next_review = (datetime.date.today()).isoformat()
        c.execute(
            "INSERT INTO flashcards (question_id,interval,ease,next_review) VALUES (?,?,?,?)",
            (question_id, interval, ease, next_review)
        )
        conn.commit()
    conn.close()

def _parse_question_metadata(metadata):
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            return {}
    return metadata if isinstance(metadata, dict) else {}


def _normalize_question_record(item):
    option_fields = ['option a', 'option b', 'option c', 'option d']

    if not isinstance(item, dict):
        return None

    question = item.get('question') or item.get('prompt') or item.get('text')
    answer = item.get('answer') or item.get('correct_answer') or item.get('correct') or ''
    domain = item.get('domain') or item.get('Domain') or ''
    explanation = item.get('explanation')
    metadata = _parse_question_metadata(item.get('metadata'))
    if not explanation:
        explanation = metadata.get('explanation')

    options = item.get('options')
    if options is None:
        options = item.get('answers')
    if options is None:
        options = metadata.get('options')

    csv_options = []
    for field in option_fields:
        value = item.get(field) or item.get(field.upper())
        if value:
            csv_options.append(value)
    if csv_options:
        options = csv_options
    if not isinstance(options, list):
        options = [] if options in (None, '') else [options]

    normalized = {
        'question': question,
        'answer': answer,
    }
    if domain:
        normalized['domain'] = domain
    if explanation:
        normalized['explanation'] = explanation
    if options:
        normalized['options'] = options
    return normalized if question else None



def convert_questions_to_import(path, output_path=None):
    input_path = Path(path)
    if output_path is None:
        output_path = input_path.with_name(f"{input_path.stem}_import_ready.json")
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    converted = []
    if input_path.suffix.lower() == '.csv':
        with input_path.open('r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                normalized = _normalize_question_record(row)
                if normalized:
                    converted.append(normalized)
    else:
        with input_path.open('r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, dict):
            if 'questions' in data and isinstance(data['questions'], list):
                data = data['questions']
            else:
                data = [data]

        for item in data:
            normalized = _normalize_question_record(item)
            if normalized:
                converted.append(normalized)

    with output_path.open('w', encoding='utf-8') as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)

    return len(converted), str(output_path)


# Import questions from CSV or JSON file
def import_csv(path):
    added = 0
    duplicates = 0
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            q = row.get('question') or row.get('Question')
            a = row.get('answer') or row.get('Answer') or ''
            t = row.get('type') or row.get('Type') or 'free'
            
            # Check for MCQ format (option a, option b, option c, option d)
            options = []
            for opt_key in ['option a', 'option b', 'option c', 'option d']:
                opt_val = row.get(opt_key) or row.get(opt_key.upper())
                if opt_val:
                    options.append(opt_val)
            
            metadata = {}
            explanation = row.get('explanation') or row.get('Explanation')
            if explanation:
                metadata['explanation'] = explanation
            if options:
                t = 'MCQ'
                metadata['options'] = options

            domain = row.get('domain') or row.get('Domain')
            if not domain or str(domain).strip().lower() == 'general':
                domain = infer_domain(q, explanation, metadata)
            
            if q:
                # Check for duplicates
                if question_exists(q):
                    duplicates += 1
                else:
                    qid = add_question(domain, q, a, t, metadata or None)
                    try:
                        _ensure_flashcard_for(qid)
                    except Exception:
                        # non-fatal: flashcard creation failure shouldn't stop import
                        pass
                    added += 1
    return added, duplicates

def import_json(path):
    added = 0
    duplicates = 0
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for item in data:
            domain = item.get('domain') or infer_domain(item.get('question', ''))
            q = item.get('question')
            a = item.get('answer', '')
            t = item.get('type', 'free')
            metadata = item.get('metadata')
            if not isinstance(metadata, dict):
                metadata = {}

            if 'options' in item:
                t = 'MCQ'
                metadata['options'] = item.get('options', [])

            explanation = item.get('explanation')
            if explanation:
                metadata['explanation'] = explanation

            domain = item.get('domain')
            if not domain or str(domain).strip().lower() == 'general':
                domain = infer_domain(q, explanation, metadata)

            if q:
                # Check for duplicates
                if question_exists(q):
                    duplicates += 1
                else:
                    qid = add_question(domain, q, a, t, metadata)
                    try:
                        _ensure_flashcard_for(qid)
                    except Exception:
                        pass
                    added += 1
    return added, duplicates

# Retrieve distinct domains
def list_domains():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT DISTINCT domain FROM questions ORDER BY domain")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows

# Retrieve questions, optionally filtered by domain and limited in number
def get_questions(domain=None, limit=None):
    conn = get_conn()
    c = conn.cursor()
    if domain and domain != 'All':
        c.execute("SELECT * FROM questions WHERE domain=? ORDER BY id", (domain,))
    else:
        c.execute("SELECT * FROM questions ORDER BY id")
    rows = c.fetchall()
    conn.close()
    if limit:
        return rows[:limit]
    return rows

# Record an attempt at answering a question
def record_attempt(question_id, correct):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO attempts (question_id, correct, timestamp) VALUES (?,?,?)",
        (question_id, 1 if correct else 0, datetime.datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

# Calculate statistics per domain
def stats_per_domain():
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        SELECT q.domain,
          COUNT(a.id) as attempts,
          SUM(a.correct) as correct
        FROM questions q
        LEFT JOIN attempts a ON a.question_id = q.id
        GROUP BY q.domain
        ORDER BY attempts DESC
        """
    )
    rows = c.fetchall()
    conn.close()
    stats = []
    for r in rows:
        attempts = r['attempts'] or 0
        correct = r['correct'] or 0
        pct = (correct / attempts * 100) if attempts > 0 else 0
        stats.append({'domain': r['domain'], 'attempts': attempts, 'correct': correct, 'pct': pct})
    return stats

# --- Simple flashcard SRS update (SM-2 simplified) ---
def schedule_update(question_id, quality):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id,interval,ease FROM flashcards WHERE question_id=?", (question_id,))
    row = c.fetchone()
    if not row:
        interval = 1
        ease = 2.5
        next_review = (datetime.date.today() + datetime.timedelta(days=interval)).isoformat()
        c.execute(
            "INSERT OR REPLACE INTO flashcards (question_id,interval,ease,next_review) VALUES (?,?,?,?)",
            (question_id, interval, ease, next_review)
        )
    else:
        interval = row[1]
        ease = row[2]
        if quality < 3:
            interval = 1
        else:
            interval = int(round(interval * ease))
            ease = max(1.3, ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        next_review = (datetime.date.today() + datetime.timedelta(days=interval)).isoformat()
        c.execute(
            "UPDATE flashcards SET interval=?, ease=?, next_review=? WHERE question_id=?",
            (interval, ease, next_review, question_id)
        )
    conn.commit()
    conn.close()


def due_flashcards():
    conn = get_conn()
    c = conn.cursor()
    today = datetime.date.today().isoformat()
    c.execute(
        "SELECT f.id as fid, q.* FROM flashcards f JOIN questions q ON f.question_id=q.id WHERE f.next_review<=? ORDER BY f.next_review",
        (today,)
    )
    rows = c.fetchall()
    conn.close()
    return rows


# Quiz tracking functions
def create_quiz(domain, total_questions):
    """Create a new quiz attempt and return the quiz ID."""
    conn = get_conn()
    c = conn.cursor()
    timestamp = datetime.datetime.utcnow().isoformat()
    c.execute(
        "INSERT INTO quizzes (domain, total_questions, score, timestamp) VALUES (?, ?, ?, ?)",
        (domain, total_questions, 0, timestamp)
    )
    quiz_id = c.lastrowid
    conn.commit()
    conn.close()
    return quiz_id


def record_quiz_answer(quiz_id, question_id, user_answer, correct):
    """Record an individual answer in a quiz."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO quiz_answers (quiz_id, question_id, user_answer, correct) VALUES (?, ?, ?, ?)",
        (quiz_id, question_id, user_answer, 1 if correct else 0)
    )
    conn.commit()
    conn.close()


def update_quiz_score(quiz_id, score):
    """Update the quiz score after completion."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE quizzes SET score = ? WHERE id = ?",
        (score, quiz_id)
    )
    conn.commit()
    conn.close()


def get_quiz_history(limit=20):
    """Get the last N quiz attempts with details."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        SELECT id, domain, total_questions, score, timestamp 
        FROM quizzes 
        ORDER BY timestamp DESC 
        LIMIT ?
        """,
        (limit,)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def get_quiz_details(quiz_id):
    """Get detailed results for a specific quiz."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        SELECT qa.id, q.question, q.answer, q.metadata, qa.user_answer, qa.correct
        FROM quiz_answers qa
        JOIN questions q ON qa.question_id = q.id
        WHERE qa.quiz_id = ?
        ORDER BY qa.id
        """,
        (quiz_id,)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def clear_quiz_history():
    """Remove all stored quiz history and per-question quiz answers."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM quiz_answers")
    c.execute("DELETE FROM quizzes")
    conn.commit()
    conn.close()


def delete_all_questions():
    """Delete all questions from the database."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM flashcards")
    c.execute("DELETE FROM questions")
    conn.commit()
    conn.close()

def consolidate_domains():
    """Consolidate similar domains into a single canonical domain."""
    conn = get_conn()
    c = conn.cursor()

    for new_domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            c.execute(
                "UPDATE questions SET domain=? WHERE LOWER(domain)=? OR LOWER(domain) LIKE ?",
                (new_domain, keyword.lower(), f"%{keyword.lower()}%")
            )

    conn.commit()
    conn.close()

def reassign_domains():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, question, metadata FROM questions")
    rows = c.fetchall()

    updated = 0
    for row in rows:
        new_domain = infer_domain(row['question'])
        if new_domain != 'General':
            c.execute("UPDATE questions SET domain=? WHERE id=?", (new_domain, row['id']))
            updated += 1
    
    conn.commit()
    conn.close()
    return updated