"""
Sensitivity Router Prototype
============================
Manages data sensitivity classification and decides whether to route to Local LLM or Cloud LLM

Author: CONSAT PoC Team
Date: May 4, 2026
"""

import re
import json
import importlib
from enum import Enum
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from consat_rules import (
    CONSAT_INTERNAL_PATTERNS,
    CONSAT_PII_PATTERNS,
    CONSAT_SECRET_PATTERNS,
    CONSAT_SENSITIVE_KEYWORDS,
)


class SensitivityLevel(Enum):
    """Data sensitivity level"""
    LOW = "low"              # Safe -> route to Cloud
    MEDIUM = "medium"        # Moderate -> requires consideration
    HIGH = "high"            # Dangerous -> force Local


class RoutingDecision(Enum):
    """Routing decision"""
    LOCAL = "local"          # Use Local LLM (safe, slow)
    CLOUD = "cloud"          # Use Cloud LLM (fast, requires masking)


@dataclass
class RoutingLog:
    """Routing log record"""
    timestamp: str
    input_text: str
    sensitivity_level: str
    detected_patterns: List[str]
    routing_decision: str
    reason: str
    confidence: float  # 0.0 - 1.0


class SensitivityDetector:
    """Detects data sensitivity level"""

    def __init__(self):
        """Initialise classification patterns"""
        # PII Pattern
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(?:\+?\d{1,3}[-.\s]?)?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'name': r'\b(John|Jane|Alice|Bob|Michael|Sarah|David|Emma|Lars|Anna)\b',
        }
        self.pii_patterns.update(CONSAT_PII_PATTERNS)

        # Secret/Credentials Pattern
        self.secret_patterns = {
            'api_key': r'(?:api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)["\']?',
            'password': r'(?:password|passwd)["\']?\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
            'token': r'(?:token|auth)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)["\']?',
            'private_key': r'-----BEGIN (RSA|OPENSSH|EC|PGP) PRIVATE KEY-----',
            'aws_secret': r'(?:aws_secret_access_key|AKIA)[A-Za-z0-9/+=]{40}',
        }
        self.secret_patterns.update(CONSAT_SECRET_PATTERNS)

        # Internal/Infrastructure Pattern
        self.internal_patterns = {
            'internal_ip': r'\b(?:10\.|172\.(?:1[6-9]|2\d|3[01])\.|192\.168\.)\d+\.\d+\b',
            'internal_domain': r'\b[\w-]+\.(?:internal|local|consat|corp)\b',
            'database_url': r'(?:postgresql|mysql|mongodb)://[^\s]+',
            'aws_region': r'\b(?:us-east-1|eu-west-1|ap-southeast-1)\b',
        }
        self.internal_patterns.update(CONSAT_INTERNAL_PATTERNS)

        # Sensitive Keyword Pattern
        self.sensitive_keywords = {
            'customer_pii': ['customer_name', 'customer_id', 'user_ssn', 'credit_card'],
            'salary_info': ['salary', 'payroll', 'bonus', 'compensation', 'wage'],
            'security_info': ['vulnerability', 'exploit', 'backdoor', 'zero-day'],
            'business_secret': ['trade_secret', 'proprietary', 'confidential', 'restricted'],
        }
        self._refresh_sensitive_keywords()

    def _refresh_sensitive_keywords(self) -> None:
        """
        Refresh keyword lists from consat_rules at runtime.

        Some dev servers can keep module state in memory even after file edits.
        Reloading keeps routing behavior aligned with the latest rule set.
        """
        try:
            import consat_rules as _rules
            importlib.reload(_rules)
            latest = getattr(_rules, "CONSAT_SENSITIVE_KEYWORDS", {})
        except Exception:
            latest = CONSAT_SENSITIVE_KEYWORDS

        for category, keywords in latest.items():
            self.sensitive_keywords.setdefault(category, [])
            for kw in keywords:
                if kw not in self.sensitive_keywords[category]:
                    self.sensitive_keywords[category].append(kw)

    def detect_pii(self, text: str) -> List[str]:
        """Detect personally identifiable information (PII)"""
        found = []
        for pattern_name, pattern in self.pii_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                found.append(f"PII:{pattern_name}")
        return found

    def detect_secrets(self, text: str) -> List[str]:
        """Detect secrets and credentials"""
        found = []
        for pattern_name, pattern in self.secret_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                found.append(f"SECRET:{pattern_name}")
        return found

    def detect_internal_resources(self, text: str) -> List[str]:
        """Detect internal resources (internal IP, domain, DB)"""
        found = []
        for pattern_name, pattern in self.internal_patterns.items():
            if re.search(pattern, text):
                found.append(f"INTERNAL:{pattern_name}")
        return found

    def detect_sensitive_keywords(self, text: str) -> List[str]:
        """Detect sensitive keywords"""
        found = []
        self._refresh_sensitive_keywords()
        text_lower = text.lower()
        for category, keywords in self.sensitive_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    found.append(f"KEYWORD:{category}")
                    break
        return found

    def classify(self, text: str) -> Tuple[SensitivityLevel, List[str]]:
        """Classify data by sensitivity level"""
        detected_patterns = []

        # Collect all patterns
        detected_patterns.extend(self.detect_secrets(text))      # highest priority
        detected_patterns.extend(self.detect_pii(text))           # high priority
        detected_patterns.extend(self.detect_internal_resources(text))  # high priority
        detected_patterns.extend(self.detect_sensitive_keywords(text))  # medium priority

        # Make decision based on findings
        if detected_patterns:
            secret_count = sum(1 for p in detected_patterns if p.startswith("SECRET"))
            pii_count = sum(1 for p in detected_patterns if p.startswith("PII"))
            internal_count = sum(1 for p in detected_patterns if p.startswith("INTERNAL"))
            keyword_count = sum(1 for p in detected_patterns if p.startswith("KEYWORD"))

            high_risk_keywords = any(p in [
                "KEYWORD:consat_eco_drive", "KEYWORD:consat_iot_internal",
                "KEYWORD:consat_operations", "KEYWORD:consat_finance",
                "KEYWORD:consat_driver_pii",   # driver PII field names → HIGH
                "KEYWORD:salary_info",          # salary/compensation → HIGH
            ] for p in detected_patterns)

            if secret_count > 0 or internal_count > 0 or pii_count > 0 or high_risk_keywords:
                return SensitivityLevel.HIGH, detected_patterns
            elif keyword_count > 0:
                return SensitivityLevel.MEDIUM, detected_patterns
            else:
                return SensitivityLevel.LOW, detected_patterns

        return SensitivityLevel.LOW, detected_patterns


class RoutingDecider:
    """Decides whether to route to Local or Cloud"""

    def __init__(self):
        """Initialise routing rules"""
        self.rules = {
            SensitivityLevel.HIGH: RoutingDecision.LOCAL,
            SensitivityLevel.MEDIUM: RoutingDecision.CLOUD,  # requires masking first
            SensitivityLevel.LOW: RoutingDecision.CLOUD,
        }

    def decide(self, sensitivity_level: SensitivityLevel, text: str) -> Tuple[RoutingDecision, str]:
        """Make routing decision"""
        decision = self.rules[sensitivity_level]

        if decision == RoutingDecision.LOCAL:
            reason = "HIGH SENSITIVITY data -> force Local LLM for security"
        elif decision == RoutingDecision.CLOUD:
            if sensitivity_level == SensitivityLevel.MEDIUM:
                reason = "MEDIUM SENSITIVITY data -> route to Cloud after Data Masking"
            else:
                reason = "LOW SENSITIVITY data -> route to Cloud LLM for performance"

        return decision, reason


class AuditTrail:
    """Records routing Audit Trail"""

    def __init__(self):
        """Create audit log"""
        self.logs: List[RoutingLog] = []

    def record(self, routing_log: RoutingLog):
        """Record a routing decision"""
        self.logs.append(routing_log)

    def save_to_file(self, filepath: str):
        """Save to file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            for log in self.logs:
                f.write(json.dumps(asdict(log), ensure_ascii=False) + '\n')

    def get_summary(self) -> Dict:
        """Summarise the audit trail"""
        local_count = sum(1 for log in self.logs if log.routing_decision == "local")
        cloud_count = sum(1 for log in self.logs if log.routing_decision == "cloud")

        return {
            'total_requests': len(self.logs),
            'local_routing': local_count,
            'cloud_routing': cloud_count,
            'cloud_percentage': f"{(cloud_count / len(self.logs) * 100):.1f}%" if self.logs else "0%",
        }


class SensitivityRouter:
    """Main Sensitivity Router system"""

    def __init__(self):
        self.detector = SensitivityDetector()
        self.decider = RoutingDecider()
        self.audit = AuditTrail()

    def route(self, input_text: str) -> Dict:
        """Analyse input and decide routing"""
        # Step 1: Detect sensitivity
        sensitivity_level, detected_patterns = self.detector.classify(input_text)

        # Step 2: Decide routing
        routing_decision, reason = self.decider.decide(sensitivity_level, input_text)

        # Step 3: Record audit trail
        log = RoutingLog(
            timestamp=datetime.now().isoformat(),
            input_text=input_text[:100],  # store only the first 100 chars
            sensitivity_level=sensitivity_level.value,
            detected_patterns=detected_patterns,
            routing_decision=routing_decision.value,
            reason=reason,
            confidence=0.95,
        )
        self.audit.record(log)

        # Return result
        return {
            'sensitivity_level': sensitivity_level.value,
            'detected_patterns': detected_patterns,
            'routing_decision': routing_decision.value,
            'reason': reason,
            'use_local_llm': routing_decision == RoutingDecision.LOCAL,
            'require_masking': routing_decision == RoutingDecision.CLOUD and detected_patterns,
        }

    def get_audit_summary(self) -> Dict:
        """Get audit trail summary"""
        return self.audit.get_summary()


# ============== Test Cases ==============

if __name__ == "__main__":
    print("=" * 80)
    print("SENSITIVITY ROUTER - PROTOTYPE TEST")
    print("=" * 80)

    router = SensitivityRouter()

    # Test Case 1: LOW SENSITIVITY (safe)
    test_cases = [
        {
            'name': 'Test 1: General Data (LOW)',
            'input': 'Help me write a Python function to calculate the average',
        },
        {
            'name': 'Test 2: Contains Email (MEDIUM)',
            'input': 'Contact support@consat.com for access issues',
        },
        {
            'name': 'Test 3: Contains API Key (HIGH)',
            'input': '''
            const client = new ApiClient({
                api_key: "sk_live_51234567890abcdefghij",
                endpoint: "https://api.internal.consat.local/v1/query"
            });
            ''',
        },
        {
            'name': 'Test 4: Contains Database URL (HIGH)',
            'input': 'postgresql://admin:password123@db.internal:5432/customer_pii_database',
        },
        {
            'name': 'Test 5: Contains Internal IP + Credential (HIGH)',
            'input': '''
            ssh admin@192.168.1.100
            password: MySecretPassword@2024
            ''',
        },
    ]

    for test in test_cases:
        print(f"\n{test['name']}")
        print("-" * 80)
        result = router.route(test['input'])

        print(f"Input (first 60 chars): {test['input'][:60]}...")
        print(f"Sensitivity Level: {result['sensitivity_level'].upper()}")
        print(f"Detected Patterns: {result['detected_patterns']}")
        print(f"Routing Decision: {result['routing_decision'].upper()}")
        print(f"Reason: {result['reason']}")
        print(f"Use Local LLM: {result['use_local_llm']}")
        print(f"Require Masking: {result['require_masking']}")

    print("\n" + "=" * 80)
    print("AUDIT TRAIL SUMMARY")
    print("=" * 80)
    summary = router.get_audit_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\n✅ Prototype test complete!")
