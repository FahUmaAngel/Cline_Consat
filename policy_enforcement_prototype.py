"""
Policy Enforcement Layer Prototype
====================================
ตรวจสอบผลลัพธ์จาก LLM ตามนโยบายความปลอดภัย

Author: CONSAT PoC Team
Date: May 4, 2026
"""

import re
import json
from enum import Enum
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from consat_rules import (
    CONSAT_COMPLIANCE_PATTERNS,
    CONSAT_FORBIDDEN_LIBRARIES,
    CONSAT_SECURITY_PATTERNS,
)


class PolicyViolationSeverity(Enum):
    """ระดับความรุนแรงของการละเมิดนโยบาย"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PolicyViolation:
    """บันทึกการละเมิดนโยบาย"""
    timestamp: str
    violation_type: str
    severity: str
    message: str
    code_snippet: str
    recommendation: str


class PolicyChecker:
    """ตรวจสอบโค้ดตามนโยบาย CONSAT"""
    
    def __init__(self):
        """เตรียมการ policy rules"""
        self.violations: List[PolicyViolation] = []
        
        # Security-related patterns ที่ต้อง block
        self.security_patterns = {
            'hardcoded_password': {
                'regex': r'(?:password|passwd)\s*=\s*["\']([^"\']+)["\']',
                'severity': PolicyViolationSeverity.CRITICAL,
                'message': 'Hardcoded password found - use environment variables instead',
                'recommendation': 'Use os.environ.get() หรือ config management',
            },
            'hardcoded_api_key': {
                'regex': r'(?:api[_-]?key|apikey)\s*=\s*["\']([a-zA-Z0-9_-]+)["\']',
                'severity': PolicyViolationSeverity.CRITICAL,
                'message': 'Hardcoded API key found - security risk',
                'recommendation': 'Move to .env file หรือ secrets manager',
            },
            'sql_injection_risk': {
                'regex': r'(?:SELECT|INSERT|UPDATE|DELETE).*f[\"\']',
                'severity': PolicyViolationSeverity.CRITICAL,
                'message': 'Potential SQL injection vulnerability (f-string with SQL)',
                'recommendation': 'Use parameterized queries หรือ ORM',
            },
            'insecure_deserialization': {
                'regex': r'pickle\.loads|eval\(',
                'severity': PolicyViolationSeverity.CRITICAL,
                'message': 'Insecure deserialization/code execution detected',
                'recommendation': 'Use json.loads() หรือ other safe alternatives',
            },
        }
        self.security_patterns.update(
            {
                name: {
                    **config,
                    'severity': PolicyViolationSeverity(config['severity']),
                }
                for name, config in CONSAT_SECURITY_PATTERNS.items()
            }
        )
        
        # Compliance-related patterns
        self.compliance_patterns = {
            'no_audit_log': {
                'regex': r'(?!.*(?:log|audit|record))database.*delete',
                'severity': PolicyViolationSeverity.WARNING,
                'message': 'Database operations without audit trail',
                'recommendation': 'Add logging สำหรับทุก database operation',
            },
            'missing_error_handling': {
                'regex': r'(?:api|database|external).*call(?!.*try)',
                'severity': PolicyViolationSeverity.WARNING,
                'message': 'External API call without error handling',
                'recommendation': 'Wrap external calls in try-except',
            },
            'unencrypted_transmission': {
                'regex': r'http://(?!localhost)',
                'severity': PolicyViolationSeverity.WARNING,
                'message': 'Unencrypted HTTP transmission detected',
                'recommendation': 'Use HTTPS for all external communications',
            },
        }
        self.compliance_patterns.update(
            {
                name: {
                    **config,
                    'severity': PolicyViolationSeverity(config['severity']),
                }
                for name, config in CONSAT_COMPLIANCE_PATTERNS.items()
            }
        )
        
        # Library/Framework restrictions
        self.library_whitelist = {
            'allowed': [
                'requests', 'flask', 'django', 'fastapi',
                'sqlalchemy', 'psycopg2', 'pymongo',
                'pandas', 'numpy', 'scikit-learn',
                'pydantic', 'jwt', 'cryptography',
            ],
            'forbidden': [
                'pickle', 'eval', 'exec',
            ],
        }
        for library in CONSAT_FORBIDDEN_LIBRARIES:
            if library not in self.library_whitelist['forbidden']:
                self.library_whitelist['forbidden'].append(library)
    
    def check_security_issues(self, code: str) -> List[PolicyViolation]:
        """ตรวจสอบปัญหาด้านความปลอดภัย"""
        issues = []
        
        for pattern_name, pattern_config in self.security_patterns.items():
            matches = re.finditer(pattern_config['regex'], code, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                violation = PolicyViolation(
                    timestamp=datetime.now().isoformat(),
                    violation_type=pattern_name,
                    severity=pattern_config['severity'].value,
                    message=pattern_config['message'],
                    code_snippet=match.group(0)[:100],
                    recommendation=pattern_config['recommendation'],
                )
                issues.append(violation)
        
        return issues
    
    def check_compliance(self, code: str) -> List[PolicyViolation]:
        """ตรวจสอบการสอดคล้องตามนโยบาย CONSAT"""
        issues = []
        
        for pattern_name, pattern_config in self.compliance_patterns.items():
            matches = re.finditer(pattern_config['regex'], code, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                violation = PolicyViolation(
                    timestamp=datetime.now().isoformat(),
                    violation_type=pattern_name,
                    severity=pattern_config['severity'].value,
                    message=pattern_config['message'],
                    code_snippet=match.group(0)[:100],
                    recommendation=pattern_config['recommendation'],
                )
                issues.append(violation)
        
        return issues
    
    def check_libraries(self, code: str) -> List[PolicyViolation]:
        """ตรวจสอบ import statements"""
        issues = []
        
        # Check for forbidden libraries
        for forbidden_lib in self.library_whitelist['forbidden']:
            pattern = rf'(?:import|from)\s+{forbidden_lib}\b'
            if re.search(pattern, code, re.IGNORECASE):
                violation = PolicyViolation(
                    timestamp=datetime.now().isoformat(),
                    violation_type=f'forbidden_library_{forbidden_lib}',
                    severity=PolicyViolationSeverity.CRITICAL.value,
                    message=f'Forbidden library "{forbidden_lib}" detected',
                    code_snippet=f'import {forbidden_lib}',
                    recommendation=f'Replace with CONSAT-approved alternative',
                )
                issues.append(violation)
        
        return issues
    
    def validate_code(self, code: str) -> Dict:
        """ตรวจสอบโค้ดทั้งหมด"""
        all_violations = []
        all_violations.extend(self.check_security_issues(code))
        all_violations.extend(self.check_compliance(code))
        all_violations.extend(self.check_libraries(code))
        
        self.violations.extend(all_violations)
        
        # ตัดสินใจว่า approve หรือ reject
        critical_count = sum(1 for v in all_violations if v.severity == 'critical')
        
        return {
            'code_approved': critical_count == 0,
            'total_violations': len(all_violations),
            'critical_violations': critical_count,
            'violations': [asdict(v) for v in all_violations],
        }
    
    def get_violation_summary(self) -> Dict:
        """สรุป violations"""
        severity_counts = {
            'critical': 0,
            'warning': 0,
            'info': 0,
        }
        
        violation_types = {}
        
        for violation in self.violations:
            severity_counts[violation.severity] += 1
            violation_types[violation.violation_type] = \
                violation_types.get(violation.violation_type, 0) + 1
        
        return {
            'total_violations': len(self.violations),
            'severity_breakdown': severity_counts,
            'violation_types': violation_types,
        }


class PolicyEnforcementPipeline:
    """Pipeline สำหรับตรวจสอบ policy"""
    
    def __init__(self):
        self.policy_checker = PolicyChecker()
    
    def validate_ai_output(self, code: str) -> Dict:
        """ตรวจสอบผลลัพธ์จาก AI"""
        return self.policy_checker.validate_code(code)
    
    def get_summary(self) -> Dict:
        return self.policy_checker.get_violation_summary()


# ============== Test Cases ==============

if __name__ == "__main__":
    print("=" * 80)
    print("POLICY ENFORCEMENT LAYER - PROTOTYPE TEST")
    print("=" * 80)
    
    pipeline = PolicyEnforcementPipeline()
    
    test_cases = [
        {
            'name': 'Test 1: Safe Code (PASS)',
            'code': '''
import requests
from config import get_api_key

def fetch_user_data(user_id):
    try:
        api_key = get_api_key()  # From env vars
        url = f"https://api.example.com/users/{user_id}"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(url, headers=headers, timeout=10)
        return response.json()
    except requests.RequestException as e:
        logger.error(f"API error: {e}")
        raise
            ''',
        },
        {
            'name': 'Test 2: Hardcoded Password (FAIL)',
            'code': '''
import mysql.connector

def connect_db():
    conn = mysql.connector.connect(
        host="db.internal",
        user="admin",
        password="MySecret123!",  # CRITICAL: Hardcoded password
        database="users"
    )
    return conn
            ''',
        },
        {
            'name': 'Test 3: SQL Injection Risk (FAIL)',
            'code': '''
def search_user(name):
    query = f"SELECT * FROM users WHERE name = '{name}'"  # SQL Injection!
    cursor.execute(query)
    return cursor.fetchall()
            ''',
        },
        {
            'name': 'Test 4: Forbidden Library (FAIL)',
            'code': '''
import pickle

def deserialize_data(data_bytes):
    return pickle.loads(data_bytes)  # CRITICAL: Unsafe deserialization
            ''',
        },
    ]
    
    for test in test_cases:
        print(f"\n{test['name']}")
        print("-" * 80)
        
        result = pipeline.validate_ai_output(test['code'])
        
        print(f"Code snippet:\n{test['code'][:100]}...")
        print(f"\nApproved: {'✅ YES' if result['code_approved'] else '❌ NO'}")
        print(f"Total Violations: {result['total_violations']}")
        print(f"Critical Violations: {result['critical_violations']}")
        
        if result['violations']:
            print(f"\nViolations:")
            for i, violation in enumerate(result['violations'][:2], 1):  # Show first 2
                print(f"  {i}. [{violation['severity'].upper()}] {violation['message']}")
                print(f"     → {violation['recommendation']}")
    
    print("\n" + "=" * 80)
    print("POLICY VIOLATION SUMMARY")
    print("=" * 80)
    summary = pipeline.get_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    print("\n✅ Policy enforcement prototype test complete!")
