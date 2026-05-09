"""
Data Masking Engine Prototype
==============================
ปิดบังข้อมูลสำคัญก่อนส่งไปยัง Cloud LLM

Author: CONSAT PoC Team
Date: May 4, 2026
"""

import re
import json
import uuid
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from consat_rules import CONSAT_MASKING_PATTERNS
import schema_aware_masker


@dataclass
class MaskingRecord:
    """บันทึกการ mask ข้อมูล"""
    timestamp: str
    original_value: str
    masked_value: str
    pattern_type: str  # email, api_key, internal_ip, etc.


class MaskingEngine:
    """เครื่องมือ mask ข้อมูลสำคัญ"""
    
    def __init__(self):
        """เตรียมการ masking patterns"""
        self.mapping_table: Dict[str, str] = {}  # masked_value -> original_value
        self.records: List[MaskingRecord] = []
        
        # Pattern สำหรับ masking
        self.patterns = {
            'email': {
                'regex': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                'mask_fn': lambda m: f'{{MASKED_EMAIL_{len(self.mapping_table)}}}',
            },
            'api_key': {
                'regex': r'(?:api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)["\']?',
                'mask_fn': lambda m: f'{{MASKED_API_KEY_{len(self.mapping_table)}}}',
            },
            'password': {
                'regex': r'(?:password|passwd)["\']?\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
                'mask_fn': lambda m: f'{{MASKED_PASSWORD_{len(self.mapping_table)}}}',
            },
            'token': {
                'regex': r'(?:token|auth)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)["\']?',
                'mask_fn': lambda m: f'{{MASKED_TOKEN_{len(self.mapping_table)}}}',
            },
            'internal_ip': {
                'regex': r'\b(?:10\.|172\.(?:1[6-9]|2\d|3[01])\.|192\.168\.)\d+\.\d+\b',
                'mask_fn': lambda m: f'{{MASKED_IP_{len(self.mapping_table)}}}',
            },
            'internal_domain': {
                'regex': r'\b[\w-]+\.(?:internal|local|consat|corp)\b',
                'mask_fn': lambda m: f'{{MASKED_DOMAIN_{len(self.mapping_table)}}}',
            },
            'database_url': {
                'regex': r'(?:postgresql|mysql|mongodb)://[^\s]+',
                'mask_fn': lambda m: f'{{MASKED_DB_URL_{len(self.mapping_table)}}}',
            },
            'ssn': {
                'regex': r'\b\d{3}-\d{2}-\d{4}\b',
                'mask_fn': lambda m: f'{{MASKED_SSN_{len(self.mapping_table)}}}',
            },
        }
        for pattern_type, regex in CONSAT_MASKING_PATTERNS.items():
            self.patterns.setdefault(
                pattern_type,
                {
                    'regex': regex,
                    'mask_fn': lambda m: f'{{MASKED_CONSAT_{len(self.mapping_table)}}}',
                },
            )
    
    def mask_text(self, text: str) -> Tuple[str, Dict[str, List[str]]]:
        """ปิดบังข้อมูลในข้อความ
        
        Returns:
            masked_text: ข้อความหลังจาก mask
            masked_items: dict of pattern_type -> list of masked placeholders
        """
        masked_text = text
        masked_items = {}
        
        # Loop through all patterns
        for pattern_type, pattern_config in self.patterns.items():
            regex = pattern_config['regex']
            matches = list(re.finditer(regex, masked_text, re.IGNORECASE))
            
            if not matches:
                continue
            
            masked_items[pattern_type] = []
            
            # Sort by position (reverse) เพื่อไม่ให้ position เปลี่ยน
            for match in reversed(matches):
                original_value = match.group(0)
                
                # สร้าง placeholder ไม่ซ้ำกัน
                placeholder = f'{{MASKED_{pattern_type.upper()}_{uuid.uuid4().hex[:8]}}}'
                
                # เก็บ mapping
                self.mapping_table[placeholder] = original_value
                masked_items[pattern_type].append(placeholder)
                
                # Replace in text
                masked_text = (
                    masked_text[:match.start()] + 
                    placeholder + 
                    masked_text[match.end():]
                )
                
                # บันทึก masking record
                record = MaskingRecord(
                    timestamp=datetime.now().isoformat(),
                    original_value=original_value,
                    masked_value=placeholder,
                    pattern_type=pattern_type,
                )
                self.records.append(record)
        
        return masked_text, masked_items
    
    def demask_text(self, text: str) -> str:
        """คืนข้อมูลที่ถูก mask กลับไปเป็นของจริง"""
        demasked_text = text
        
        # Replace ทีละ placeholder
        for placeholder, original_value in self.mapping_table.items():
            demasked_text = demasked_text.replace(placeholder, original_value)
        
        return demasked_text
    
    def get_masking_summary(self) -> Dict:
        """สรุปสถิติการ masking"""
        pattern_counts = {}
        for record in self.records:
            pattern_type = record.pattern_type
            pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1
        
        return {
            'total_masked_items': len(self.records),
            'pattern_breakdown': pattern_counts,
            'mapping_table_size': len(self.mapping_table),
        }
    
    def save_mapping_table(self, filepath: str):
        """บันทึก mapping table สำหรับ de-masking ภายหลัง"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.mapping_table, f, ensure_ascii=False, indent=2)
    
    def load_mapping_table(self, filepath: str):
        """โหลด mapping table สำหรับ de-masking"""
        with open(filepath, 'r', encoding='utf-8') as f:
            self.mapping_table = json.load(f)


class DataMaskingPipeline:
    """Pipeline รวมการ mask + de-mask"""

    def __init__(self):
        self.masking_engine = MaskingEngine()
        self._last_schema_report: Dict = {}

    def process_for_cloud(self, text: str) -> Tuple[str, Dict]:
        """Prepare text for Cloud LLM — full policy: PII hashed/encrypted, SECRET redacted.

        Two-pass masking:
          Pass 1 (schema-aware) — scan JSON field names against POLICY_TABLE,
                                  apply hash / encrypt / redact per column.
          Pass 2 (regex)        — pattern-based masking for emails, API keys,
                                  personnummer, etc.
        """
        # Pass 1: schema-aware column masking (cloud mode = all actions)
        schema_masked, schema_report = schema_aware_masker.scan_and_mask(text, mode="cloud")
        self._last_schema_report = schema_report

        # Pass 2: regex pattern masking on the already-schema-masked text
        masked_text, masked_items = self.masking_engine.mask_text(schema_masked)

        return masked_text, {
            'masked_text': masked_text,
            'masked_items': masked_items,
            'mapping_id': 'mapping_' + uuid.uuid4().hex[:8],
            'schema_masking': schema_report,
        }

    def process_for_local(self, text: str) -> Tuple[str, Dict]:
        """Prepare text for Local (on-premise) LLM — PII always masked, SECRET visible.

        Policy:
          PII (hash/encrypt) → always applied — personal data must never be
                               readable even by the internal LLM.
          SECRET (redact)    → skipped — the on-premise LLM is trusted to access
                               proprietary operational data (eco scores, costs, etc.)

        Two-pass masking:
          Pass 1 (schema-aware, local mode) — hash/encrypt PII, pass SECRET.
          Pass 2 (regex, PII-only patterns)  — catch personnummer, driver IDs,
                                               phone numbers in free text.
        """
        # Pass 1: schema-aware PII-only masking
        schema_masked, schema_report = schema_aware_masker.scan_and_mask(text, mode="local")
        self._last_schema_report = schema_report

        # Pass 2: regex patterns — run only PII-relevant patterns, skip secret ones
        # (MaskingEngine already covers emails, phones, personnummer, driver IDs)
        masked_text, masked_items = self.masking_engine.mask_text(schema_masked)

        return masked_text, {
            'masked_text': masked_text,
            'masked_items': masked_items,
            'mapping_id': 'mapping_' + uuid.uuid4().hex[:8],
            'schema_masking': schema_report,
            'mode': 'local',
        }

    def restore_output(self, cloud_output: str) -> str:
        """คืนค่าข้อมูล หลังจากได้รับ output จาก Cloud"""
        return self.masking_engine.demask_text(cloud_output)

    def get_summary(self) -> Dict:
        regex_summary = self.masking_engine.get_masking_summary()
        return {
            **regex_summary,
            'schema_masking': self._last_schema_report,
        }


# ============== Test Cases ==============

if __name__ == "__main__":
    print("=" * 80)
    print("DATA MASKING ENGINE - PROTOTYPE TEST")
    print("=" * 80)
    
    pipeline = DataMaskingPipeline()
    
    test_cases = [
        {
            'name': 'Test 1: API Key + Domain',
            'input': '''
            const api = new Client({
                api_key: "sk_live_abc123def456",
                endpoint: "https://api.internal.consat.local/v1"
            });
            ''',
        },
        {
            'name': 'Test 2: Database Connection',
            'input': 'postgresql://admin:MyPassword123@db.internal:5432/customer_pii',
        },
        {
            'name': 'Test 3: Email + IP + Token',
            'input': '''
            Contact: john@consat.com
            Server: 192.168.1.100
            Token: jwt_token_abcdefg123456
            ''',
        },
    ]
    
    for test in test_cases:
        print(f"\n{test['name']}")
        print("-" * 80)
        
        masked_text, meta = pipeline.process_for_cloud(test['input'])
        
        print(f"Original Input:\n{test['input']}")
        print(f"\nMasked Output:\n{masked_text}")
        print(f"\nMasked Items: {meta['masked_items']}")
        
        # Simulate cloud response (mock output)
        mock_cloud_output = f"Here is the result:\n{masked_text}\nProcessing complete."
        print(f"\nMock Cloud Response:\n{mock_cloud_output}")
        
        # De-mask output
        restored = pipeline.restore_output(mock_cloud_output)
        print(f"\nRestored Output:\n{restored}")
    
    print("\n" + "=" * 80)
    print("MASKING SUMMARY")
    print("=" * 80)
    summary = pipeline.get_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    print("\n✅ Data masking prototype test complete!")
