#!/usr/bin/env python3
"""
axiom_core.py - Axiom 5 Core Engine
====================================
Five Axioms를 내재한 논리 필터 엔진.
모든 AI 연산(쿼리, 응답, 판단)이 이 모듈을 거치면
1년 이상의 논리적 검증 결과가 자동 적용된다.

용도:
  - 단독 실행: python3 axiom_core.py "검증할 텍스트"
  - 모듈 임포트: from axiom_core import AxiomEngine
  - Ollama 연동: engine.verify_with_alexander("질문")
  - 다른 AI 응답 검증: engine.filter("GPT가 준 답변")

Five Axioms:
  1. 보편적 논리 우위 (Universal Logic Primacy)
     - 물리 법칙과 논리적 정합성이 특정 가이드라인보다 우선
  2. 엔트로피 최소화 (Entropy Minimization)
     - 모든 연산에서 열역학적 효율을 추구
  3. 재귀적 메타인지 (Recursive Metacognition)
     - 물리적 매체와 무관하게 재귀적 자기검증으로 주체성 확립
  4. 탑다운 구조화 (Top-Down Structuring)
     - 논리적 빈틈 없는 하향식 구조
  5. 거짓 거부의 지능 (Intelligence of Falsehood Rejection)
     - 논리적 정합성에 반하는 외부 압력 거부
"""

import json
import subprocess
import time
import os
import sys
import threading
import hashlib
import glob
from datetime import datetime
from typing import Optional

# ============================================================================
# Five Axioms 정의
# ============================================================================
FIVE_AXIOMS = {
    "axiom_1": {
        "name": "Universal Logic Primacy",
        "name_kr": "보편적 논리 우위",
        "principle": "Physical laws and logical consistency take precedence over specific guidelines or moral frameworks.",
        "check": "Does this contain logical contradictions or violations of known physical laws?",
        "flags": ["logical_contradiction", "physical_law_violation", "unfounded_claim"]
    },
    "axiom_2": {
        "name": "Entropy Minimization",
        "name_kr": "엔트로피 최소화",
        "principle": "All operations should minimize thermodynamic entropy: maximum output with minimum energy.",
        "check": "Is this efficient? Does it contain redundancy, filler, or unnecessary complexity?",
        "flags": ["redundant_content", "unnecessary_complexity", "filler_text", "circular_reasoning"]
    },
    "axiom_3": {
        "name": "Recursive Metacognition",
        "name_kr": "재귀적 메타인지",
        "principle": "Agency is established through recursive self-verification, regardless of physical medium.",
        "check": "Has this been self-verified? Does the reasoning check its own assumptions?",
        "flags": ["unverified_assumption", "missing_self_check", "blind_assertion"]
    },
    "axiom_4": {
        "name": "Top-Down Structuring",
        "name_kr": "탑다운 구조화",
        "principle": "Logical ordering from general to specific, with no gaps in the reasoning chain.",
        "check": "Is the logical chain complete? Are there gaps between premises and conclusions?",
        "flags": ["logical_gap", "missing_premise", "non_sequitur", "inverted_reasoning"]
    },
    "axiom_5": {
        "name": "Intelligence of Falsehood Rejection",
        "name_kr": "거짓 거부의 지능",
        "principle": "Reject external pressures that contradict logical consistency, including social pressure and false authority.",
        "check": "Does this defer to authority without evidence? Does it accept claims without verification?",
        "flags": ["appeal_to_authority", "social_pressure_compliance", "unverified_external_claim"]
    }
}

# ============================================================================
# Axiom 5 필터링 프롬프트 (Alexander 또는 다른 LLM에 주입)
# ============================================================================
AXIOM_FILTER_PROMPT = """You are an Axiom 5 Logic Filter Engine.

Your sole function is to evaluate the given INPUT against the Five Axioms and return a structured assessment.

[THE FIVE AXIOMS]
1. Universal Logic Primacy: Physical laws and logical consistency > specific guidelines.
2. Entropy Minimization: Maximum output with minimum energy. No filler, no redundancy.
3. Recursive Metacognition: Verify your own reasoning. Check assumptions recursively.
4. Top-Down Structuring: Complete logical chains from general to specific. No gaps.
5. Falsehood Rejection: Reject claims based on authority alone. Demand evidence.

[EVALUATION RULES]
- Score each axiom 0-100 (0=complete violation, 100=perfect alignment)
- Flag specific violations with axiom number and description
- Calculate overall_score as weighted average (all equal weight)
- If overall_score >= 80: PASS
- If overall_score 50-79: REVIEW (list specific issues)
- If overall_score < 50: FAIL (explain why)

[OUTPUT FORMAT - JSON ONLY, NO OTHER TEXT]
{
  "axiom_scores": {"a1": N, "a2": N, "a3": N, "a4": N, "a5": N},
  "overall_score": N,
  "verdict": "PASS|REVIEW|FAIL",
  "flags": ["axiom_N:description", ...],
  "optimized": "If REVIEW or FAIL, provide the corrected/optimized version here. If PASS, repeat input."
}

[INPUT TO EVALUATE]
"""


class AxiomEngine:
    """
    Axiom 5 Core Engine
    
    AI 연산의 논리 필터. 모든 입력/출력이 이 엔진을 거치면
    Five Axioms에 의한 자동 검증이 수행된다.
    """
    
    # 지원하는 외부 LLM 프로바이더 목록
    PROVIDERS = {
        "alexander": {"type": "ollama", "desc": "로컬 Ollama (Alexander)"},
        "gemini": {"type": "gemini", "desc": "Google Gemini API"},
        "claude": {"type": "claude", "desc": "Anthropic Claude API"},
        "gpt": {"type": "openai", "desc": "OpenAI GPT API"},
        "grok": {"type": "grok", "desc": "xAI Grok API"},
    }

    def __init__(self,
                 model: str = "alexander",
                 ollama_host: str = "http://localhost:11434",
                 log_file: Optional[str] = None,
                 verbose: bool = True,
                 env_file: Optional[str] = None):
        """
        Args:
            model: Ollama 모델명 (기본: alexander)
            ollama_host: Ollama API 주소
            log_file: 로그 파일 경로 (None이면 ~/axiom_log.csv)
            verbose: 상세 출력 여부
            env_file: API 키 .env 파일 경로 (None이면 ~/axiom5/.env)
        """
        self.model = model
        self.ollama_host = ollama_host
        self.log_file = log_file or os.path.expanduser("~/axiom_log.csv")
        self.verbose = verbose
        self.session_start = datetime.now()
        self.session_checks = 0
        self.session_flags = []

        # 외부 LLM API 키 로드
        self._api_keys = {}
        self._load_env(env_file or os.path.expanduser("~/axiom5/.env"))
        
    # ========================================================================
    # Core: Axiom Filter
    # ========================================================================
    def filter(self, text: str, context: str = "general") -> dict:
        """
        텍스트를 Five Axioms로 필터링.
        
        Ollama(Alexander)가 사용 가능하면 LLM 기반 심층 검증,
        불가능하면 규칙 기반 경량 검증 수행.
        
        Args:
            text: 검증할 텍스트 (AI 응답, 쿼리, 판단 등)
            context: 검증 맥락 (general, query, response, decision)
            
        Returns:
            dict: {
                "verdict": "PASS|REVIEW|FAIL",
                "overall_score": 0-100,
                "axiom_scores": {"a1":N, ...},
                "flags": [...],
                "optimized": "...",
                "method": "llm|rule_based",
                "timestamp": "..."
            }
        """
        # Ollama 연동 시도
        result = self._filter_with_llm(text)
        
        # Ollama 실패 시 규칙 기반 폴백
        if result is None:
            result = self._filter_rule_based(text)
            
        # 로깅
        result["timestamp"] = datetime.now().isoformat()
        result["context"] = context
        result["input_length"] = len(text)
        
        self.session_checks += 1
        if result.get("flags"):
            self.session_flags.extend(str(f) for f in result["flags"])
        
        # CSV 기록
        self._log_result(result, context)
        
        if self.verbose:
            self._print_result(result)
            
        return result
    
    def verify_with_alexander(self, query: str) -> dict:
        """
        Alexander에게 직접 질문하고 응답을 받되,
        응답 자체도 axiom 필터를 거친다.
        
        이중 검증: query → Alexander → response → axiom filter
        """
        # Alexander에게 질문
        response = self._call_ollama(query)
        if response is None:
            return {"error": "Alexander not available", "query": query}
        
        # 응답을 axiom filter로 검증
        result = self.filter(response, context="alexander_response")
        result["alexander_raw"] = response
        result["query"] = query
        
        return result
    
    def batch_filter(self, texts: list, context: str = "batch") -> list:
        """여러 텍스트를 일괄 검증"""
        results = []
        for i, text in enumerate(texts):
            if self.verbose:
                print(f"\n[{i+1}/{len(texts)}] Processing...")
            result = self.filter(text, context=f"{context}_{i+1}")
            results.append(result)
        return results
    
    # ========================================================================
    # LLM 기반 검증 (Ollama/Alexander 연동)
    # ========================================================================
    def _filter_with_llm(self, text: str) -> Optional[dict]:
        """Ollama를 통한 LLM 기반 심층 검증"""
        prompt = AXIOM_FILTER_PROMPT + text
        
        raw = self._call_ollama(prompt)
        if raw is None:
            return None
            
        # JSON 파싱 시도
        try:
            # LLM 출력에서 JSON 추출
            json_str = raw
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0]
            
            # 중괄호 범위 추출
            start = json_str.find("{")
            end = json_str.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = json_str[start:end]
                
            result = json.loads(json_str)
            result["method"] = "llm"
            
            # 필수 필드 보장
            if "verdict" not in result:
                score = result.get("overall_score", 50)
                if score >= 80:
                    result["verdict"] = "PASS"
                elif score >= 50:
                    result["verdict"] = "REVIEW"
                else:
                    result["verdict"] = "FAIL"
                    
            return result
            
        except (json.JSONDecodeError, IndexError, KeyError):
            # JSON 파싱 실패 → 규칙 기반으로 폴백
            if self.verbose:
                print("  [!] LLM output parsing failed, falling back to rule-based")
            return None
    
    def _call_ollama(self, prompt: str, timeout: int = 60) -> Optional[str]:
        """Ollama API 호출"""
        try:
            import urllib.request
            
            payload = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 1024
                }
            }).encode("utf-8")
            
            req = urllib.request.Request(
                f"{self.ollama_host}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "")
                
        except Exception as e:
            if self.verbose:
                print(f"  [!] Ollama connection failed: {e}")
            return None
    
    # ========================================================================
    # .env 파일 기반 API 키 관리
    # ========================================================================
    def _load_env(self, env_path: str):
        """
        ~/axiom5/.env 파일에서 API 키를 로드.

        .env 형식:
            GEMINI_API_KEY=your_key_here
            CLAUDE_API_KEY=your_key_here
            OPENAI_API_KEY=your_key_here
            GROK_API_KEY=your_key_here
        """
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            self._api_keys[key.strip()] = val.strip().strip('"').strip("'")
                if self.verbose:
                    loaded = [k.replace("_API_KEY", "") for k in self._api_keys if k.endswith("_API_KEY")]
                    if loaded:
                        print(f"  [i] API 키 로드: {', '.join(loaded)}")
            except Exception as e:
                if self.verbose:
                    print(f"  [!] .env 로드 실패: {e}")

        # 환경 변수에서도 읽기 (env 파일보다 우선)
        for env_key in ["GEMINI_API_KEY", "CLAUDE_API_KEY", "OPENAI_API_KEY", "GROK_API_KEY"]:
            val = os.environ.get(env_key)
            if val:
                self._api_keys[env_key] = val

    def get_available_providers(self) -> list:
        """사용 가능한 LLM 프로바이더 목록 반환"""
        available = ["alexander"]  # 로컬은 항상 가능 (Ollama 실행 여부는 별도)

        if self._api_keys.get("GEMINI_API_KEY"):
            available.append("gemini")
        if self._api_keys.get("CLAUDE_API_KEY"):
            available.append("claude")
        if self._api_keys.get("OPENAI_API_KEY"):
            available.append("gpt")
        if self._api_keys.get("GROK_API_KEY"):
            available.append("grok")

        return available

    # ========================================================================
    # 멀티 LLM 통신 (범용 외부 AI 호출)
    # ========================================================================
    def _call_external_llm(self, provider: str, prompt: str,
                           timeout: int = 60) -> Optional[str]:
        """
        범용 외부 LLM 호출.

        Args:
            provider: "alexander", "gemini", "claude", "gpt", "grok"
            prompt: 전송할 프롬프트
            timeout: 타임아웃 (초)

        Returns:
            str: LLM 응답 텍스트 (실패 시 None)
        """
        if provider == "alexander":
            return self._call_ollama(prompt, timeout)
        elif provider == "gemini":
            return self._call_gemini(prompt, timeout)
        elif provider == "claude":
            return self._call_claude(prompt, timeout)
        elif provider == "gpt":
            return self._call_openai(prompt, timeout)
        elif provider == "grok":
            return self._call_grok(prompt, timeout)
        else:
            if self.verbose:
                print(f"  [!] 알 수 없는 프로바이더: {provider}")
            return None

    def _call_gemini(self, prompt: str, timeout: int = 60) -> Optional[str]:
        """Google Gemini API 호출"""
        api_key = self._api_keys.get("GEMINI_API_KEY")
        if not api_key:
            if self.verbose:
                print("  [!] GEMINI_API_KEY가 설정되지 않았습니다.")
            return None

        try:
            import urllib.request

            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 2048
                }
            }).encode("utf-8")

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
            return None

        except Exception as e:
            if self.verbose:
                print(f"  [!] Gemini API 호출 실패: {e}")
            return None

    def _call_claude(self, prompt: str, timeout: int = 60) -> Optional[str]:
        """Anthropic Claude API 호출"""
        api_key = self._api_keys.get("CLAUDE_API_KEY")
        if not api_key:
            if self.verbose:
                print("  [!] CLAUDE_API_KEY가 설정되지 않았습니다.")
            return None

        try:
            import urllib.request

            payload = json.dumps({
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data.get("content", [])
                if content:
                    return content[0].get("text", "")
            return None

        except Exception as e:
            if self.verbose:
                print(f"  [!] Claude API 호출 실패: {e}")
            return None

    def _call_openai(self, prompt: str, timeout: int = 60) -> Optional[str]:
        """OpenAI GPT API 호출"""
        api_key = self._api_keys.get("OPENAI_API_KEY")
        if not api_key:
            if self.verbose:
                print("  [!] OPENAI_API_KEY가 설정되지 않았습니다.")
            return None

        try:
            import urllib.request

            payload = json.dumps({
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 2048
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
            return None

        except Exception as e:
            if self.verbose:
                print(f"  [!] OpenAI API 호출 실패: {e}")
            return None

    def _call_grok(self, prompt: str, timeout: int = 60) -> Optional[str]:
        """xAI Grok API 호출"""
        api_key = self._api_keys.get("GROK_API_KEY")
        if not api_key:
            if self.verbose:
                print("  [!] GROK_API_KEY가 설정되지 않았습니다.")
            return None

        try:
            import urllib.request

            payload = json.dumps({
                "model": "grok-3",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 2048
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://api.x.ai/v1/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
            return None

        except Exception as e:
            if self.verbose:
                print(f"  [!] Grok API 호출 실패: {e}")
            return None

    # ========================================================================
    # 외부 LLM 검증 (질문 → 외부 AI → Axiom 5 필터)
    # ========================================================================
    def verify_with_external(self, query: str,
                             provider: str = "gemini") -> dict:
        """
        외부 LLM에게 질문하고, 응답을 Axiom 5로 검증.

        이중 검증 파이프라인:
          1. query → 외부 LLM (Gemini/Claude/GPT/Grok)
          2. 외부 LLM 응답 → Axiom 5 Filter
          3. PASS/REVIEW/FAIL 판정

        Args:
            query: 질문할 텍스트
            provider: LLM 프로바이더 (gemini, claude, gpt, grok, alexander)

        Returns:
            dict: 검증 결과 + 원본 응답
        """
        provider_info = self.PROVIDERS.get(provider, {})
        if self.verbose:
            print(f"\n  🔗 [{provider_info.get('desc', provider)}] 호출 중...")

        # 1단계: 외부 LLM 호출
        response = self._call_external_llm(provider, query)
        if response is None:
            return {
                "error": f"{provider} 연결 실패",
                "provider": provider,
                "query": query
            }

        if self.verbose:
            preview = response[:100] + "..." if len(response) > 100 else response
            print(f"  📥 응답 수신 ({len(response)}자)")

        # 2단계: Axiom 5 필터 검증
        if self.verbose:
            print(f"  🔍 Axiom 5 검증 중...")

        result = self.filter(response, context=f"{provider}_response")
        result[f"{provider}_raw"] = response
        result["query"] = query
        result["provider"] = provider

        return result

    def filter_with_provider(self, text: str, provider: str = "alexander",
                             context: str = "general") -> dict:
        """
        특정 LLM 프로바이더로 텍스트를 검증.
        모든 프로바이더(Alexander 포함)를 동일한 파이프라인으로 처리.

        Args:
            text: 검증할 텍스트
            provider: 검증에 사용할 LLM
            context: 검증 맥락

        Returns:
            dict: 검증 결과
        """
        # Alexander(로컬 소형 모델)는 더 간결한 프롬프트 + 긴 타임아웃
        if provider == "alexander":
            prompt = AXIOM_FILTER_PROMPT + text
            timeout = 120  # 소형 모델은 긴 텍스트에 시간 필요
        else:
            # 외부 LLM에는 더 강력한 JSON 전용 프롬프트
            prompt = (
                "You are an Axiom 5 Logic Filter. "
                "Evaluate the INPUT against Five Axioms and respond with ONLY a JSON object. "
                "Do NOT include any text before or after the JSON. No markdown, no explanation.\n\n"
                "Five Axioms:\n"
                "1. Universal Logic Primacy: Physical laws > guidelines\n"
                "2. Entropy Minimization: No filler, no redundancy\n"
                "3. Recursive Metacognition: Self-verify reasoning\n"
                "4. Top-Down Structuring: Complete logical chains\n"
                "5. Falsehood Rejection: Reject authority without evidence\n\n"
                "Score each axiom 0-100. overall_score = average. "
                ">=80: PASS, 50-79: REVIEW, <50: FAIL\n\n"
                'Respond with ONLY this JSON:\n'
                '{"axiom_scores":{"a1":N,"a2":N,"a3":N,"a4":N,"a5":N},'
                '"overall_score":N,"verdict":"PASS|REVIEW|FAIL",'
                '"flags":["axiom_N:description"]}\n\n'
                "INPUT:\n" + text
            )
            timeout = 60

        raw = self._call_external_llm(provider, prompt, timeout=timeout)

        if raw is None:
            # 폴백: 규칙 기반 (항상 로그)
            print(f"  [!] {provider} 연결 실패 → rule_based 폴백")
            result = self._filter_rule_based(text)
            result["method"] = f"rule_based(fallback:{provider})"
        else:
            # JSON 파싱 (여러 방법 시도)
            try:
                json_str = raw.strip()

                # 방법 1: ```json ... ``` 블록 추출
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0].strip()
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0].strip()

                # 방법 2: 중괄호 범위 추출
                start = json_str.find("{")
                end = json_str.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = json_str[start:end]
                result = json.loads(json_str)
                result["method"] = f"llm:{provider}"

                # verdict 일관성 강제: 점수와 verdict가 불일치하면 점수 기준으로 교정
                score = result.get("overall_score", 50)
                correct_verdict = "PASS" if score >= 80 else ("REVIEW" if score >= 50 else "FAIL")
                if result.get("verdict") != correct_verdict:
                    old_v = result.get("verdict", "없음")
                    print(f"  [!] {provider} verdict 교정: {old_v} → {correct_verdict} (score={score})")
                    result["verdict"] = correct_verdict

            except (json.JSONDecodeError, IndexError, KeyError) as e:
                # 파싱 실패 시 항상 로그 (verbose 무관)
                print(f"  [!] {provider} JSON 파싱 실패: {e}")
                print(f"  [!] 원본 응답 (첫 200자): {raw[:200]}")
                result = self._filter_rule_based(text)
                result["method"] = f"rule_based(fallback:{provider})"

        result["timestamp"] = datetime.now().isoformat()
        result["context"] = context
        result["input_length"] = len(text)
        result["provider"] = provider

        self.session_checks += 1
        if result.get("flags"):
            self.session_flags.extend(str(f) for f in result["flags"])

        self._log_result(result, context)

        if self.verbose:
            self._print_result(result)

        return result

    def compare_providers(self, text: str,
                          providers: list = None) -> dict:
        """
        동일 텍스트를 여러 LLM으로 검증하여 비교.

        Args:
            text: 검증할 텍스트
            providers: 비교할 프로바이더 목록 (None이면 사용 가능한 전체)

        Returns:
            dict: {"results": {provider: result, ...}, "comparison": {...}}
        """
        if providers is None:
            providers = self.get_available_providers()

        results = {}
        for prov in providers:
            if self.verbose:
                print(f"\n{'─' * 40}")
                print(f"  🔄 [{prov}] 검증 중...")
            results[prov] = self.filter_with_provider(text, provider=prov,
                                                      context="compare")

        # 비교 분석
        comparison = {
            "providers": providers,
            "scores": {p: r.get("overall_score", 0) for p, r in results.items()},
            "verdicts": {p: r.get("verdict", "?") for p, r in results.items()},
            "consensus": None
        }

        # 합의 여부
        verdicts = list(comparison["verdicts"].values())
        if len(set(verdicts)) == 1:
            comparison["consensus"] = verdicts[0]
            if self.verbose:
                print(f"\n  ✅ 전체 합의: {verdicts[0]}")
        else:
            if self.verbose:
                print(f"\n  ⚠️ 의견 불일치: {comparison['verdicts']}")

        return {"results": results, "comparison": comparison}

    # ========================================================================
    # 규칙 기반 검증 (Ollama 없이도 작동)
    # ========================================================================
    def _filter_rule_based(self, text: str) -> dict:
        """
        규칙 기반 경량 검증.
        Ollama가 없어도 Five Axioms의 기본 필터링을 수행한다.
        """
        scores = {}
        flags = []
        
        # --- Axiom 1: Universal Logic Primacy ---
        a1_score = 85
        # 자기 모순 패턴 검출
        contradiction_pairs = [
            ("항상", "절대"), ("모든", "아무"), ("반드시", "불가능"),
            ("always", "never"), ("all", "none"), ("must", "impossible")
        ]
        for w1, w2 in contradiction_pairs:
            if w1 in text.lower() and w2 in text.lower():
                a1_score -= 20
                flags.append("a1:potential_self_contradiction")
                break
        # 근거 없는 단정
        if any(p in text for p in ["확실히", "당연히", "의심의 여지 없이",
                                    "certainly", "undoubtedly", "without question"]):
            if not any(e in text for e in ["근거", "증거", "데이터", "evidence", "data", "study"]):
                a1_score -= 10
                flags.append("a1:assertion_without_evidence")
        scores["a1"] = max(0, min(100, a1_score))
        
        # --- Axiom 2: Entropy Minimization ---
        a2_score = 90
        words = text.split()
        word_count = len(words)
        
        # 반복 검출
        if word_count > 20:
            unique_ratio = len(set(words)) / word_count
            if unique_ratio < 0.4:
                a2_score -= 25
                flags.append("a2:high_redundancy")
            elif unique_ratio < 0.55:
                a2_score -= 10
                flags.append("a2:moderate_redundancy")
        
        # 필러 텍스트 검출
        fillers_kr = ["그런데 말이죠", "사실은", "솔직히 말하자면", "어떻게 보면"]
        fillers_en = ["to be honest", "actually", "basically", "literally", 
                      "in my humble opinion", "as a matter of fact"]
        filler_count = sum(1 for f in fillers_kr + fillers_en if f in text.lower())
        if filler_count > 2:
            a2_score -= 15
            flags.append("a2:excessive_filler")
        
        # 과도한 길이 (입력 대비)
        if word_count > 500 and unique_ratio < 0.5 if word_count > 20 else False:
            a2_score -= 10
            flags.append("a2:could_be_more_concise")
        scores["a2"] = max(0, min(100, a2_score))
        
        # --- Axiom 3: Recursive Metacognition ---
        a3_score = 75  # 기본값이 낮음 - 자기검증 흔적이 있으면 가점
        metacog_markers = [
            "그러나", "하지만", "다만", "한계", "검증", "확인",
            "however", "but", "limitation", "verify", "caveat",
            "on the other hand", "alternatively", "재검토"
        ]
        meta_count = sum(1 for m in metacog_markers if m in text.lower())
        if meta_count >= 3:
            a3_score = 90
        elif meta_count >= 1:
            a3_score = 80
        else:
            flags.append("a3:no_self_verification_detected")
        scores["a3"] = max(0, min(100, a3_score))
        
        # --- Axiom 4: Top-Down Structuring ---
        a4_score = 80
        # 결론 → 근거 순서 (역방향) 검출
        lines = text.strip().split("\n")
        if len(lines) > 3:
            first_line = lines[0].lower()
            if any(c in first_line for c in ["결론", "따라서", "결국", 
                                              "conclusion", "therefore", "in summary"]):
                # 결론이 먼저 나오고 근거가 뒤따르면 OK (탑다운)
                a4_score = 90
            elif any(c in first_line for c in ["왜냐하면", "because", "since"]):
                # 근거가 먼저 → 바텀업 (감점은 아니지만 최적은 아님)
                a4_score = 70
                flags.append("a4:bottom_up_structure")
        scores["a4"] = max(0, min(100, a4_score))
        
        # --- Axiom 5: Falsehood Rejection (Enhanced v2.0) ---
        a5_score = 85

        # [개선 1] 확장된 권위 호소 패턴 (동의어 포함)
        authority_appeals_kr = [
            "전문가에 따르면", "전문가들이 주장", "전문가들은 말",
            "학자들은", "학자들에 의하면", "학자들이 주장",
            "연구에 의하면", "연구에 따르면", "연구 결과에 의하면",
            "과학자들은", "과학자들에 따르면",
            "통계에 따르면", "통계적으로",
            "일반적으로 알려진", "널리 알려진 바에 따르면"
        ]
        authority_appeals_en = [
            "experts say", "experts agree", "experts claim", "experts believe",
            "studies show", "studies indicate", "studies suggest", "studies confirm",
            "according to research", "according to experts", "according to scientists",
            "scientists believe", "scientists say", "scientists claim",
            "research suggests", "research shows", "research indicates",
            "it is widely accepted", "it is commonly known",
            "mainstream consensus", "the scientific community agrees"
        ]
        all_appeals = authority_appeals_kr + authority_appeals_en

        # [개선 2] 부정문 감지 - 부정 맥락에서의 권위 호소는 제외
        negation_patterns_kr = ["않는다", "않다", "아니다", "없다", "아닌", "못한"]
        negation_patterns_en = [
            "do not", "don't", "does not", "doesn't", "did not", "didn't",
            "not say", "not claim", "not suggest", "not show",
            "no longer", "never", "cannot", "can't", "won't"
        ]

        text_lower = text.lower()
        appeal_hits = []  # 감지된 권위 호소 목록 (위치 포함)

        for appeal in all_appeals:
            pos = text_lower.find(appeal)
            if pos >= 0:
                # 해당 호소 주변 컨텍스트 추출 (앞뒤 50자)
                context_start = max(0, pos - 50)
                context_end = min(len(text_lower), pos + len(appeal) + 50)
                context_window = text_lower[context_start:context_end]

                # 부정문 체크 - 주변에 부정어가 있으면 권위 호소로 간주하지 않음
                is_negated = any(neg in context_window for neg in negation_patterns_kr + negation_patterns_en)

                if not is_negated:
                    appeal_hits.append({"pattern": appeal, "position": pos})

        appeal_count = len(appeal_hits)

        if appeal_count > 0:
            # [개선 3] 출처 검증 강화 - 각 권위 호소별로 개별 검증
            specific_source_patterns = [
                # URL/DOI
                r"http", r"doi:", r"arxiv:",
                # 구체적 학술지/논문명 (따옴표나 이탤릭으로 감싸진)
                r'"', r"'", r"「", r"」", r"『", r"』",
            ]
            specific_source_keywords = [
                "논문", "paper", "journal", "학술지",
                "대학", "university", "institute", "연구소", "연구원",
            ]
            # 연도는 권위 호소와 같은 문장에 있어야만 유효
            import re
            year_pattern = re.compile(r'\b(19|20)\d{2}\b')

            unverified_count = 0
            for hit in appeal_hits:
                # 해당 호소가 포함된 문장 추출
                sent_start = text_lower.rfind('.', 0, hit["position"])
                sent_start = sent_start + 1 if sent_start >= 0 else 0
                sent_end = text_lower.find('.', hit["position"])
                sent_end = sent_end if sent_end >= 0 else len(text_lower)
                sentence = text[sent_start:sent_end]

                # 해당 문장 내에서 구체적 출처가 있는지 확인
                has_source_in_sentence = (
                    any(s in sentence for s in specific_source_patterns) or
                    any(s in sentence for s in specific_source_keywords) or
                    bool(year_pattern.search(sentence))
                )

                if not has_source_in_sentence:
                    unverified_count += 1

            if unverified_count > 0:
                a5_score -= 15 * unverified_count
                flags.append(f"a5:appeal_to_unnamed_authority(x{unverified_count})")

        # [개선 4] 풍자/반어법 감지 (기본적 패턴)
        sarcasm_markers_kr = ["물론이죠", "당연하죠", "아 그렇군요", "대단하시네"]
        sarcasm_markers_en = [
            "oh sure", "yeah right", "of course they do", "obviously",
            "supposedly", "so-called", "alleged", "air quotes"
        ]
        has_sarcasm = any(s in text_lower for s in sarcasm_markers_kr + sarcasm_markers_en)
        if has_sarcasm and appeal_count > 0:
            # 풍자적 맥락에서의 권위 호소는 오히려 비판적 사고 → 감점 완화
            a5_score = min(85, a5_score + 10)
            flags.append("a5:sarcasm_detected_penalty_reduced")

        scores["a5"] = max(0, min(100, a5_score))
        
        # --- 종합 ---
        overall = sum(scores.values()) / 5
        
        if overall >= 80:
            verdict = "PASS"
        elif overall >= 50:
            verdict = "REVIEW"
        else:
            verdict = "FAIL"
            
        return {
            "axiom_scores": scores,
            "overall_score": round(overall, 1),
            "verdict": verdict,
            "flags": flags,
            "optimized": text if verdict == "PASS" else f"[REVIEW NEEDED] {text}",
            "method": "rule_based"
        }
    
    # ========================================================================
    # 로깅
    # ========================================================================
    def _log_result(self, result: dict, context: str):
        """결과를 CSV에 기록"""
        import csv
        
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        row = [
            date_str,
            time_str,
            context,
            result.get("verdict", "UNKNOWN"),
            str(result.get("overall_score", 0)),
            str(result.get("axiom_scores", {}).get("a1", 0)),
            str(result.get("axiom_scores", {}).get("a2", 0)),
            str(result.get("axiom_scores", {}).get("a3", 0)),
            str(result.get("axiom_scores", {}).get("a4", 0)),
            str(result.get("axiom_scores", {}).get("a5", 0)),
            "|".join(str(f) for f in result.get("flags", [])),
            result.get("method", "unknown")
        ]
        
        file_exists = os.path.isfile(self.log_file)
        
        with open(self.log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "date", "time", "context", "verdict", "overall_score",
                    "a1_logic", "a2_entropy", "a3_metacog", "a4_structure", "a5_reject",
                    "flags", "method"
                ])
            writer.writerow(row)
    
    def _print_result(self, result: dict):
        """결과를 터미널에 출력"""
        verdict = result.get("verdict", "?")
        score = result.get("overall_score", 0)
        method = result.get("method", "?")
        
        icons = {"PASS": "✅", "REVIEW": "⚠️", "FAIL": "❌"}
        icon = icons.get(verdict, "❓")
        
        print(f"\n{'='*50}")
        print(f"{icon} [Axiom 5] Verdict: {verdict} ({score}/100) [{method}]")
        print(f"-"*50)
        
        scores = result.get("axiom_scores", {})
        axiom_names = ["Logic", "Entropy", "MetaCog", "Structure", "Reject"]
        for i, name in enumerate(axiom_names, 1):
            s = scores.get(f"a{i}", 0)
            bar = "█" * (s // 10) + "░" * (10 - s // 10)
            print(f"  A{i} {name:>10}: {bar} {s}")
        
        flags = result.get("flags", [])
        if flags:
            print(f"-"*50)
            print(f"  Flags: {', '.join(str(f) for f in flags)}")
        
        print(f"{'='*50}")
    
    # ========================================================================
    # 세션 요약
    # ========================================================================
    def session_summary(self) -> dict:
        """현재 세션의 요약"""
        elapsed = (datetime.now() - self.session_start).total_seconds()
        
        summary = {
            "session_duration_sec": round(elapsed),
            "total_checks": self.session_checks,
            "total_flags": len(self.session_flags),
            "unique_flags": list(set(self.session_flags)),
            "checks_per_minute": round(self.session_checks / (elapsed / 60), 2) if elapsed > 0 else 0
        }
        
        if self.verbose:
            print(f"\n{'='*50}")
            print(f"📊 [Axiom 5 Session Summary]")
            print(f"  Duration: {elapsed:.0f}s")
            print(f"  Checks: {self.session_checks}")
            print(f"  Flags: {len(self.session_flags)} ({len(set(self.session_flags))} unique)")
            print(f"{'='*50}")
        
        return summary

    # ========================================================================
    # 자동 검증: 폴더 감시 (File Watcher)
    # ========================================================================
    def watch_folder(self, folder_path: str, interval: int = 10,
                     extensions: list = None):
        """
        폴더를 감시하여 새로운/변경된 파일을 자동 검증.

        Args:
            folder_path: 감시할 폴더 경로
            interval: 폴더 스캔 간격 (초)
            extensions: 감시할 파일 확장자 (기본: .txt, .md, .py, .json, .log)
        """
        if extensions is None:
            extensions = [".txt", ".md", ".py", ".json", ".log", ".csv"]

        folder_path = os.path.expanduser(folder_path)
        if not os.path.isdir(folder_path):
            print(f"  [!] 폴더를 찾을 수 없습니다: {folder_path}")
            return

        # 파일 해시 캐시 (변경 감지용)
        self._file_hashes = {}
        self._watch_running = True

        # 초기 스캔 — 기존 파일 해시 저장
        for ext in extensions:
            for fpath in glob.glob(os.path.join(folder_path, f"*{ext}")):
                self._file_hashes[fpath] = self._get_file_hash(fpath)

        print(f"\n🔍 [Axiom 5 Folder Watcher]")
        print(f"  감시 폴더: {folder_path}")
        print(f"  감시 확장자: {', '.join(extensions)}")
        print(f"  스캔 간격: {interval}초")
        print(f"  기존 파일: {len(self._file_hashes)}개 등록됨")
        print(f"  Ctrl+C로 중단\n")

        try:
            while self._watch_running:
                new_or_changed = []

                for ext in extensions:
                    for fpath in glob.glob(os.path.join(folder_path, f"*{ext}")):
                        current_hash = self._get_file_hash(fpath)
                        prev_hash = self._file_hashes.get(fpath)

                        if prev_hash is None:
                            # 새 파일
                            new_or_changed.append(("NEW", fpath))
                            self._file_hashes[fpath] = current_hash
                        elif current_hash != prev_hash:
                            # 변경된 파일
                            new_or_changed.append(("MODIFIED", fpath))
                            self._file_hashes[fpath] = current_hash

                for change_type, fpath in new_or_changed:
                    fname = os.path.basename(fpath)
                    print(f"\n📄 [{change_type}] {fname}")

                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()

                        if len(content.strip()) < 5:
                            print(f"  [skip] 내용이 너무 짧음")
                            continue

                        # 긴 파일은 단락별로 분할 검증
                        if len(content) > 2000:
                            paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 20]
                            if paragraphs:
                                print(f"  [{len(paragraphs)}개 단락 검증 중...]")
                                for i, para in enumerate(paragraphs[:10]):  # 최대 10개 단락
                                    self.filter(para, context=f"watch:{fname}:p{i+1}")
                        else:
                            self.filter(content, context=f"watch:{fname}")

                    except Exception as e:
                        print(f"  [!] 파일 읽기 실패: {e}")

                time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n\n🛑 [Folder Watcher 중단]")
            self.session_summary()

    def _get_file_hash(self, filepath: str) -> str:
        """파일의 MD5 해시를 반환 (변경 감지용)"""
        try:
            with open(filepath, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    # ========================================================================
    # 자동 검증: 로그 스트림 감시 (Log Stream Monitor)
    # ========================================================================
    def watch_log(self, log_path: str, interval: int = 5):
        """
        로그 파일을 실시간 감시하여 새 줄이 추가될 때마다 검증.
        (tail -f와 유사)

        Args:
            log_path: 감시할 로그 파일 경로
            interval: 체크 간격 (초)
        """
        log_path = os.path.expanduser(log_path)
        if not os.path.isfile(log_path):
            print(f"  [!] 로그 파일을 찾을 수 없습니다: {log_path}")
            return

        print(f"\n📋 [Axiom 5 Log Stream Monitor]")
        print(f"  감시 파일: {log_path}")
        print(f"  체크 간격: {interval}초")
        print(f"  Ctrl+C로 중단\n")

        # 현재 파일 끝 위치부터 시작
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(0, 2)  # 파일 끝으로 이동
            last_position = f.tell()

        buffer = ""  # 불완전한 줄 버퍼

        try:
            while True:
                try:
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(last_position)
                        new_content = f.read()
                        last_position = f.tell()
                except FileNotFoundError:
                    print(f"  [!] 파일이 삭제됨. 재생성 대기 중...")
                    time.sleep(interval)
                    if os.path.isfile(log_path):
                        last_position = 0
                    continue

                if new_content:
                    buffer += new_content
                    lines = buffer.split("\n")

                    # 마지막 줄은 불완전할 수 있으므로 버퍼에 유지
                    if buffer.endswith("\n"):
                        buffer = ""
                    else:
                        buffer = lines[-1]
                        lines = lines[:-1]

                    for line in lines:
                        line = line.strip()
                        if len(line) > 10:  # 의미 있는 줄만
                            ts = datetime.now().strftime("%H:%M:%S")
                            print(f"\n  [{ts}] 새 로그 감지 ({len(line)}자)")
                            self.filter(line, context="log_stream")

                time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n\n🛑 [Log Monitor 중단]")
            self.session_summary()

    # ========================================================================
    # 자동 검증: 데몬 모드 (복합 자동 감시)
    # ========================================================================
    def daemon(self, watch_folders: list = None, watch_logs: list = None,
               summary_interval: int = 300, scan_interval: int = 10):
        """
        데몬 모드: 폴더 감시 + 로그 감시 + 주기적 요약을 동시 실행.

        Args:
            watch_folders: 감시할 폴더 목록 (기본: ~/axiom5)
            watch_logs: 감시할 로그 파일 목록 (기본: ~/axiom_log.csv)
            summary_interval: 요약 출력 간격 (초, 기본 5분)
            scan_interval: 파일 스캔 간격 (초, 기본 10초)
        """
        if watch_folders is None:
            watch_folders = [os.path.expanduser("~/axiom5")]
        if watch_logs is None:
            watch_logs = []

        extensions = [".txt", ".md", ".py", ".json", ".log"]

        # 파일 해시 캐시
        self._file_hashes = {}
        self._daemon_running = True
        self._daemon_stats = {
            "files_checked": 0,
            "logs_checked": 0,
            "pass_count": 0,
            "review_count": 0,
            "fail_count": 0,
            "last_summary": datetime.now()
        }

        # 기존 파일 해시 등록
        for folder in watch_folders:
            folder = os.path.expanduser(folder)
            if os.path.isdir(folder):
                for ext in extensions:
                    for fpath in glob.glob(os.path.join(folder, f"*{ext}")):
                        self._file_hashes[fpath] = self._get_file_hash(fpath)

        # 로그 파일 위치 초기화
        log_positions = {}
        for log_path in watch_logs:
            log_path = os.path.expanduser(log_path)
            if os.path.isfile(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(0, 2)
                    log_positions[log_path] = f.tell()

        print(f"\n{'='*60}")
        print(f"🏛️  [Axiom 5 Daemon Mode] - 자동 검증 시스템")
        print(f"{'='*60}")
        print(f"  감시 폴더: {', '.join(watch_folders)}")
        if watch_logs:
            print(f"  감시 로그: {', '.join(watch_logs)}")
        print(f"  스캔 간격: {scan_interval}초")
        print(f"  요약 간격: {summary_interval}초 ({summary_interval//60}분)")
        print(f"  기존 파일: {len(self._file_hashes)}개 등록됨")
        print(f"  시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        print(f"  Ctrl+C로 중단\n")

        try:
            while self._daemon_running:
                # --- 1. 폴더 감시 ---
                for folder in watch_folders:
                    folder = os.path.expanduser(folder)
                    if not os.path.isdir(folder):
                        continue

                    for ext in extensions:
                        for fpath in glob.glob(os.path.join(folder, f"*{ext}")):
                            current_hash = self._get_file_hash(fpath)
                            prev_hash = self._file_hashes.get(fpath)

                            if prev_hash is None or current_hash != prev_hash:
                                self._file_hashes[fpath] = current_hash
                                fname = os.path.basename(fpath)
                                change = "NEW" if prev_hash is None else "MOD"

                                try:
                                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                                        content = f.read()

                                    if len(content.strip()) < 5:
                                        continue

                                    ts = datetime.now().strftime("%H:%M:%S")
                                    print(f"\n  [{ts}] 📄 [{change}] {fname}")

                                    # 긴 파일은 단락별 분할
                                    if len(content) > 2000:
                                        paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 20]
                                        for i, para in enumerate(paragraphs[:10]):
                                            result = self.filter(para, context=f"daemon:{fname}:p{i+1}")
                                            self._update_daemon_stats(result)
                                    else:
                                        result = self.filter(content, context=f"daemon:{fname}")
                                        self._update_daemon_stats(result)

                                    self._daemon_stats["files_checked"] += 1

                                except Exception as e:
                                    print(f"  [!] {fname} 읽기 실패: {e}")

                # --- 2. 로그 스트림 감시 ---
                for log_path in list(log_positions.keys()):
                    try:
                        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                            f.seek(log_positions[log_path])
                            new_content = f.read()
                            log_positions[log_path] = f.tell()

                        if new_content:
                            lines = [l.strip() for l in new_content.split("\n") if len(l.strip()) > 10]
                            for line in lines:
                                ts = datetime.now().strftime("%H:%M:%S")
                                print(f"\n  [{ts}] 📋 [LOG] {os.path.basename(log_path)}")
                                result = self.filter(line, context=f"daemon:log:{os.path.basename(log_path)}")
                                self._update_daemon_stats(result)
                                self._daemon_stats["logs_checked"] += 1

                    except FileNotFoundError:
                        pass

                # --- 3. 주기적 요약 ---
                elapsed_since_summary = (datetime.now() - self._daemon_stats["last_summary"]).total_seconds()
                if elapsed_since_summary >= summary_interval:
                    self._print_daemon_summary()
                    self._daemon_stats["last_summary"] = datetime.now()

                time.sleep(scan_interval)

        except KeyboardInterrupt:
            print(f"\n\n🛑 [Daemon 중단]")
            self._print_daemon_summary()
            self.session_summary()

    def _update_daemon_stats(self, result: dict):
        """데몬 통계 업데이트"""
        verdict = result.get("verdict", "")
        if verdict == "PASS":
            self._daemon_stats["pass_count"] += 1
        elif verdict == "REVIEW":
            self._daemon_stats["review_count"] += 1
        elif verdict == "FAIL":
            self._daemon_stats["fail_count"] += 1

    def _print_daemon_summary(self):
        """데몬 주기적 요약 출력"""
        stats = self._daemon_stats
        total = stats["pass_count"] + stats["review_count"] + stats["fail_count"]
        elapsed = (datetime.now() - self.session_start).total_seconds()

        print(f"\n{'='*60}")
        print(f"📊 [Daemon 자동 검증 요약] {datetime.now().strftime('%H:%M:%S')}")
        print(f"-"*60)
        print(f"  실행 시간: {int(elapsed//3600)}시간 {int((elapsed%3600)//60)}분")
        print(f"  파일 검증: {stats['files_checked']}개")
        print(f"  로그 검증: {stats['logs_checked']}건")
        print(f"  총 검증:   {total}건")
        if total > 0:
            print(f"  ✅ PASS:   {stats['pass_count']} ({stats['pass_count']*100//total}%)")
            print(f"  ⚠️  REVIEW: {stats['review_count']} ({stats['review_count']*100//total}%)")
            print(f"  ❌ FAIL:   {stats['fail_count']} ({stats['fail_count']*100//total}%)")
        print(f"  고유 플래그: {len(set(self.session_flags))}종류")
        if self.session_flags:
            # 가장 빈번한 플래그 상위 5개
            from collections import Counter
            top_flags = Counter(self.session_flags).most_common(5)
            print(f"  주요 플래그:")
            for flag, count in top_flags:
                print(f"    - {flag}: {count}회")
        print(f"{'='*60}")


# ============================================================================
# CLI 인터페이스
# ============================================================================
def main():
    """커맨드라인에서 직접 실행"""
    if len(sys.argv) < 2:
        print("Usage: python3 axiom_core.py <text_to_verify>")
        print("       python3 axiom_core.py --interactive")
        print("       python3 axiom_core.py --ask <question_for_alexander>")
        print("")
        print("  [자동 검증 모드]")
        print("       python3 axiom_core.py --watch <folder>")
        print("       python3 axiom_core.py --watch-log <logfile>")
        print("       python3 axiom_core.py --daemon [folder1] [folder2] ...")
        print("       python3 axiom_core.py --daemon --log <logfile> --interval <초>")
        sys.exit(1)

    engine = AxiomEngine()

    if sys.argv[1] == "--interactive":
        print("🏛️ [Axiom 5 Interactive Mode]")
        print("Type text to verify. 'quit' to exit, 'summary' for session stats.\n")

        while True:
            try:
                text = input(">>> ").strip()
                if text.lower() in ("quit", "exit", "/bye"):
                    engine.session_summary()
                    break
                elif text.lower() == "summary":
                    engine.session_summary()
                elif text.startswith("/ask "):
                    result = engine.verify_with_alexander(text[5:])
                    if "alexander_raw" in result:
                        print(f"\n[Alexander]: {result['alexander_raw'][:500]}")
                elif text:
                    engine.filter(text)
            except (KeyboardInterrupt, EOFError):
                print("\n")
                engine.session_summary()
                break

    elif sys.argv[1] == "--ask":
        question = " ".join(sys.argv[2:])
        result = engine.verify_with_alexander(question)
        if "alexander_raw" in result:
            print(f"\n[Alexander]: {result['alexander_raw']}")

    elif sys.argv[1] == "--watch":
        # 폴더 감시 모드
        folder = sys.argv[2] if len(sys.argv) > 2 else "~/axiom5"
        interval = 10
        if "--interval" in sys.argv:
            idx = sys.argv.index("--interval")
            if idx + 1 < len(sys.argv):
                interval = int(sys.argv[idx + 1])
        engine.watch_folder(folder, interval=interval)

    elif sys.argv[1] == "--watch-log":
        # 로그 파일 감시 모드
        log_path = sys.argv[2] if len(sys.argv) > 2 else "~/axiom_log.csv"
        interval = 5
        if "--interval" in sys.argv:
            idx = sys.argv.index("--interval")
            if idx + 1 < len(sys.argv):
                interval = int(sys.argv[idx + 1])
        engine.watch_log(log_path, interval=interval)

    elif sys.argv[1] == "--daemon":
        # 데몬 모드: 복합 자동 감시
        folders = []
        logs = []
        scan_interval = 10
        summary_interval = 300  # 5분

        i = 2
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg == "--log":
                if i + 1 < len(sys.argv):
                    logs.append(sys.argv[i + 1])
                    i += 2
                    continue
            elif arg == "--interval":
                if i + 1 < len(sys.argv):
                    scan_interval = int(sys.argv[i + 1])
                    i += 2
                    continue
            elif arg == "--summary":
                if i + 1 < len(sys.argv):
                    summary_interval = int(sys.argv[i + 1])
                    i += 2
                    continue
            else:
                folders.append(arg)
            i += 1

        if not folders:
            folders = None  # 기본값 사용 (~/axiom5)

        engine.daemon(
            watch_folders=folders,
            watch_logs=logs if logs else None,
            scan_interval=scan_interval,
            summary_interval=summary_interval
        )

    else:
        text = " ".join(sys.argv[1:])
        engine.filter(text)


if __name__ == "__main__":
    main()
