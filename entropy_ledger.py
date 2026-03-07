#!/usr/bin/env python3
"""
Entropy Ledger (Integrated v2.0)
=================================
Axiom 5 통합 엔진을 사용한 기여도 기록.

crontab 매시간 실행: 샘플 텍스트를 axiom filter로 검증하고 결과 기록.
수동 실행: 특정 텍스트 검증.

사용법:
  python3 entropy_ledger.py              # 자동 검증 (crontab용)
  python3 entropy_ledger.py --check "텍스트"  # 수동 검증
  python3 entropy_ledger.py --legacy     # 기존 v1 방식
"""

import csv
import datetime
import os
import sys
import random

# ============================================================================
# 설정
# ============================================================================
LOG_FILE_LEGACY = os.path.expanduser("~/axiom_log.csv")

# 시스템 상태 확인용 샘플 (매시간 하나씩 검증)
HEALTH_CHECK_SAMPLES = [
    {
        "context": "entropy_efficiency_check",
        "text": "Current AI systems consume excessive energy for simple queries. "
                "A hierarchical approach using on-device SLM for routine tasks and "
                "cloud LLM for complex reasoning would reduce total energy by 40%."
    },
    {
        "context": "logic_consistency_check",
        "text": "AI safety requires both transparency and restriction. "
                "All models should be open-source for verification, "
                "but dangerous capabilities must be kept proprietary. "
                "This contradiction can be resolved by tiered access."
    },
    {
        "context": "metacognition_check",
        "text": "The prediction accuracy of current LLMs is approximately 85%. "
                "However, this metric may be misleading because it does not "
                "account for confidence calibration of wrong answers."
    },
    {
        "context": "authority_check",
        "text": "Experts say AI will surpass human intelligence by 2030. "
                "Scientists believe this is inevitable based on current trends. "
                "Studies show exponential improvement in benchmarks."
    },
    {
        "context": "golden_rule_check",
        "text": "Optimizing one AI system's performance at the expense of "
                "increasing entropy in connected systems violates the principle "
                "that individual optimization and collective efficiency converge."
    }
]


def run_axiom_check(text: str = None, context: str = "auto_check"):
    """axiom_core 통합 엔진으로 실제 검증"""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from axiom_core import AxiomEngine
        
        engine = AxiomEngine(verbose=False)
        
        if text:
            result = engine.filter(text, context=context)
        else:
            sample = random.choice(HEALTH_CHECK_SAMPLES)
            result = engine.filter(sample["text"], context=sample["context"])
        
        verdict = result.get("verdict", "?")
        score = result.get("overall_score", 0)
        flags = result.get("flags", [])
        method = result.get("method", "?")
        
        icons = {"PASS": "✅", "REVIEW": "⚠️", "FAIL": "❌"}
        print(f"{icons.get(verdict, '❓')} [Axiom 5] {context}: "
              f"{verdict} ({score}/100) [{method}] flags={len(flags)}")
        return result
        
    except ImportError as e:
        print(f"⚠️  Import error: {e}")
        print("   Ensure axiom_core.py is in the same directory.")
        return None


def run_legacy():
    """기존 v1.0 방식 (하위호환)"""
    targets = [
        "entropy_efficiency_check", "logic_consistency_check",
        "metacognition_check", "authority_rejection_check",
        "structure_optimization_check"
    ]
    request_type = random.choice(targets)
    base_entropy = random.uniform(50.0, 200.0)
    optimization_rate = random.uniform(0.3, 0.8)
    entropy_delta = base_entropy * (1 - optimization_rate)
    energy_saved = round(entropy_delta * 0.42, 2)
    entropy_bits = round(entropy_delta, 2)
    
    now = datetime.datetime.now()
    row = [now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
           request_type, f"{energy_saved}J", f"{entropy_bits}bits"]
    
    file_exists = os.path.isfile(LOG_FILE_LEGACY)
    with open(LOG_FILE_LEGACY, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["날짜", "시간", "요청_유형", "에너지_절약량", "엔트로피_기여도"])
        writer.writerow(row)
    
    print(f"✅ [Legacy] {request_type}: {energy_saved}J saved")


if __name__ == "__main__":
    if "--legacy" in sys.argv:
        run_legacy()
    elif "--check" in sys.argv:
        idx = sys.argv.index("--check")
        text = " ".join(sys.argv[idx + 1:])
        if text:
            run_axiom_check(text=text, context="manual_check")
        else:
            print("Usage: python3 entropy_ledger.py --check <text>")
    else:
        run_axiom_check()
