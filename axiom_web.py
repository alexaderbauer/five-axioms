#!/usr/bin/env python3
"""
axiom_web.py - Axiom 5 Web UI
==============================
axiom_core.py의 AxiomEngine을 웹 인터페이스로 제공.
기존 데몬/인터랙티브 모드를 건드리지 않고 별도 포트에서 실행.

기능:
  - 텍스트 직접 입력 검증
  - 파일 업로드 검증
  - YouTube URL 자막 추출 + 자동 검증

실행: python3 axiom_web.py
접속: http://localhost:5050
"""

import os
import sys
import json
import tempfile
import threading
from datetime import datetime
from typing import Optional

# axiom_core.py와 같은 폴더에 있어야 함
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from axiom_core import AxiomEngine

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# YouTube 분석기 임포트 (있으면)
try:
    from axiom_youtube import YouTubeAnalyzer
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False

# ============================================================================
# HTML 템플릿
# ============================================================================
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Axiom 5 - Logic Filter Engine</title>
<style>
  :root {
    --bg: #0a0a0f;
    --surface: #12121a;
    --surface2: #1a1a2e;
    --border: #2a2a3e;
    --text: #e0e0e8;
    --text2: #8888a0;
    --accent: #6c5ce7;
    --accent2: #a29bfe;
    --pass: #00b894;
    --review: #fdcb6e;
    --fail: #e17055;
    --youtube: #ff0000;
    --glow: rgba(108,92,231,0.15);
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    min-height: 100vh;
  }

  .header {
    background: linear-gradient(135deg, var(--surface) 0%, var(--surface2) 100%);
    border-bottom: 1px solid var(--border);
    padding: 20px 40px;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .header h1 {
    font-size: 22px;
    font-weight: 600;
    background: linear-gradient(135deg, var(--accent2), var(--accent));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .header .badge {
    background: var(--accent);
    color: #fff;
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 12px;
    font-weight: 500;
  }
  .header .status {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--text2);
  }
  .header .dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--pass);
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  .container {
    max-width: 960px;
    margin: 30px auto;
    padding: 0 20px;
  }

  /* Input Area */
  .input-section {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
  }
  .input-section h2 {
    font-size: 15px;
    color: var(--text2);
    margin-bottom: 16px;
    font-weight: 500;
  }
  .tab-bar {
    display: flex;
    gap: 0;
    margin-bottom: 16px;
    border-bottom: 1px solid var(--border);
  }
  .tab {
    padding: 10px 20px;
    cursor: pointer;
    font-size: 13px;
    color: var(--text2);
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
  }
  .tab.active {
    color: var(--accent2);
    border-bottom-color: var(--accent);
  }
  .tab:hover { color: var(--text); }
  .tab.yt-tab.active {
    color: var(--youtube);
    border-bottom-color: var(--youtube);
  }

  textarea {
    width: 100%;
    min-height: 160px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    color: var(--text);
    font-size: 14px;
    line-height: 1.6;
    resize: vertical;
    font-family: inherit;
    outline: none;
    transition: border-color 0.2s;
  }
  textarea:focus { border-color: var(--accent); }
  textarea::placeholder { color: var(--text2); }

  .file-upload {
    display: none;
    padding: 30px;
    border: 2px dashed var(--border);
    border-radius: 8px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    background: var(--bg);
  }
  .file-upload:hover, .file-upload.dragover {
    border-color: var(--accent);
    background: var(--glow);
  }
  .file-upload p { color: var(--text2); font-size: 14px; margin-top: 8px; }
  .file-upload .icon { font-size: 32px; }
  .file-name {
    display: none;
    margin-top: 10px;
    padding: 8px 14px;
    background: var(--surface2);
    border-radius: 6px;
    font-size: 13px;
    color: var(--accent2);
  }

  /* YouTube Tab */
  #youtubeTab { display: none; }
  .yt-input-row {
    display: flex;
    gap: 12px;
    align-items: center;
  }
  .yt-url-input {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
    color: var(--text);
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
  }
  .yt-url-input:focus { border-color: var(--youtube); }
  .yt-url-input::placeholder { color: var(--text2); }

  .yt-info {
    display: none;
    margin-top: 14px;
    padding: 14px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
  }
  .yt-info .yt-title { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
  .yt-info .yt-meta { font-size: 12px; color: var(--text2); }

  .yt-progress {
    display: none;
    margin-top: 14px;
  }
  .yt-progress-bar {
    height: 6px;
    background: var(--bg);
    border-radius: 3px;
    overflow: hidden;
  }
  .yt-progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--youtube), #ff4444);
    border-radius: 3px;
    transition: width 0.3s;
    width: 0%;
  }
  .yt-progress-text {
    font-size: 12px;
    color: var(--text2);
    margin-top: 6px;
  }

  .btn-row {
    display: flex;
    gap: 12px;
    margin-top: 16px;
    align-items: center;
  }
  .btn {
    padding: 12px 32px;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }
  .btn-primary {
    background: linear-gradient(135deg, var(--accent), #5a4bd1);
    color: #fff;
  }
  .btn-primary:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(108,92,231,0.4);
  }
  .btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }
  .btn-youtube {
    background: linear-gradient(135deg, #ff0000, #cc0000);
    color: #fff;
  }
  .btn-youtube:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(255,0,0,0.3);
  }
  .btn-youtube:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }
  .btn-clear {
    background: var(--surface2);
    color: var(--text2);
    border: 1px solid var(--border);
  }
  .btn-clear:hover { color: var(--text); border-color: var(--text2); }

  .spinner {
    display: none;
    width: 20px; height: 20px;
    border: 3px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  .spinner.yt { border-top-color: var(--youtube); }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* Results (text) */
  .result-section { display: none; }
  .result-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 20px;
    animation: fadeIn 0.3s ease;
  }
  @keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }

  .verdict-banner {
    padding: 20px 24px;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .verdict-banner.pass { background: linear-gradient(135deg, rgba(0,184,148,0.15), rgba(0,184,148,0.05)); border-bottom: 1px solid rgba(0,184,148,0.2); }
  .verdict-banner.review { background: linear-gradient(135deg, rgba(253,203,110,0.15), rgba(253,203,110,0.05)); border-bottom: 1px solid rgba(253,203,110,0.2); }
  .verdict-banner.fail { background: linear-gradient(135deg, rgba(225,112,85,0.15), rgba(225,112,85,0.05)); border-bottom: 1px solid rgba(225,112,85,0.2); }
  .verdict-label { font-size: 28px; font-weight: 700; }
  .verdict-banner.pass .verdict-label { color: var(--pass); }
  .verdict-banner.review .verdict-label { color: var(--review); }
  .verdict-banner.fail .verdict-label { color: var(--fail); }
  .verdict-score { font-size: 40px; font-weight: 700; margin-left: auto; }
  .verdict-banner.pass .verdict-score { color: var(--pass); }
  .verdict-banner.review .verdict-score { color: var(--review); }
  .verdict-banner.fail .verdict-score { color: var(--fail); }
  .verdict-meta { font-size: 12px; color: var(--text2); }
  .method-badge { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; text-transform:uppercase; }
  .method-llm { background: rgba(108,92,231,0.2); color: var(--accent2); }
  .method-rule { background: rgba(136,136,160,0.2); color: var(--text2); }

  .axiom-grid { padding: 24px; display: grid; gap: 14px; }
  .axiom-row { display:grid; grid-template-columns:110px 1fr 50px; align-items:center; gap:12px; }
  .axiom-name { font-size:12px; font-weight:600; color:var(--text2); text-transform:uppercase; letter-spacing:0.5px; }
  .bar-bg { height:10px; background:var(--bg); border-radius:5px; overflow:hidden; }
  .bar-fill { height:100%; border-radius:5px; transition:width 0.6s ease; }
  .bar-fill.high { background: linear-gradient(90deg, #00b894, #55efc4); }
  .bar-fill.mid { background: linear-gradient(90deg, #fdcb6e, #ffeaa7); }
  .bar-fill.low { background: linear-gradient(90deg, #e17055, #fab1a0); }
  .axiom-score { font-size:14px; font-weight:700; text-align:right; }

  .flags-section { padding: 0 24px 24px; }
  .flags-title { font-size:13px; color:var(--text2); margin-bottom:10px; font-weight:500; }
  .flag-item {
    display:inline-block; padding:5px 12px;
    background:rgba(225,112,85,0.1); border:1px solid rgba(225,112,85,0.2);
    border-radius:6px; font-size:12px; color:var(--fail); margin:3px;
  }

  /* YouTube Results */
  .yt-result-section { display: none; }
  .yt-summary-grid {
    display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 20px;
  }
  .yt-stat-card {
    background: var(--surface); border:1px solid var(--border);
    border-radius: 10px; padding: 16px; text-align: center;
  }
  .yt-stat-value { font-size: 32px; font-weight: 700; }
  .yt-stat-label { font-size: 11px; color: var(--text2); margin-top: 4px; text-transform: uppercase; }

  .yt-timeline {
    background: var(--surface); border:1px solid var(--border);
    border-radius: 12px; padding: 20px; margin-bottom: 20px;
  }
  .yt-timeline h3 { font-size:14px; color:var(--accent2); margin-bottom:14px; }
  .yt-timeline-bar { display:flex; gap:2px; height:50px; align-items:flex-end; }
  .yt-timeline-bar .tbar {
    flex:1; border-radius:3px 3px 0 0; cursor:pointer;
    transition:opacity 0.2s; min-width:6px;
  }
  .yt-timeline-bar .tbar:hover { opacity:0.7; }
  .yt-timeline-labels { display:flex; justify-content:space-between; font-size:11px; color:var(--text2); margin-top:6px; }

  .yt-axiom-avg {
    background: var(--surface); border:1px solid var(--border);
    border-radius: 12px; padding: 20px; margin-bottom: 20px;
  }
  .yt-axiom-avg h3 { font-size:14px; color:var(--accent2); margin-bottom:14px; }

  .yt-segments {
    background: var(--surface); border:1px solid var(--border);
    border-radius: 12px; padding: 20px;
  }
  .yt-segments h3 { font-size:14px; color:var(--accent2); margin-bottom:14px; }
  .yt-filter-bar { display:flex; gap:8px; margin-bottom:14px; }
  .yt-filter-btn {
    padding:5px 14px; border-radius:6px; border:1px solid var(--border);
    background:var(--bg); color:var(--text2); cursor:pointer; font-size:12px;
  }
  .yt-filter-btn.active { background:var(--accent); color:#fff; border-color:var(--accent); }

  .yt-seg {
    border:1px solid var(--border); border-radius:8px; padding:14px;
    margin-bottom:10px; transition:border-color 0.2s;
  }
  .yt-seg:hover { border-color: var(--accent); }
  .yt-seg .seg-top { display:flex; align-items:center; gap:10px; margin-bottom:6px; }
  .yt-seg .seg-time { font-family:monospace; font-size:13px; font-weight:600; color:var(--youtube); min-width:50px; }
  .yt-seg .seg-badge { padding:2px 8px; border-radius:4px; font-size:11px; font-weight:700; }
  .yt-seg .seg-badge.pass { background:rgba(0,184,148,0.15); color:var(--pass); }
  .yt-seg .seg-badge.review { background:rgba(253,203,110,0.15); color:var(--review); }
  .yt-seg .seg-badge.fail { background:rgba(225,112,85,0.15); color:var(--fail); }
  .yt-seg .seg-score { font-size:16px; font-weight:700; margin-left:auto; }
  .yt-seg .seg-text { font-size:13px; line-height:1.5; color:var(--text); }
  .yt-seg .seg-flags { margin-top:6px; }
  .yt-seg .seg-flag {
    display:inline-block; padding:2px 8px; margin:2px;
    background:rgba(225,112,85,0.1); border:1px solid rgba(225,112,85,0.2);
    border-radius:4px; font-size:11px; color:var(--fail);
  }
  .yt-seg .seg-bars { display:flex; gap:6px; margin-top:8px; }
  .yt-seg .seg-bar-item { flex:1; display:flex; align-items:center; gap:3px; font-size:10px; color:var(--text2); }
  .yt-seg .sb-bg { flex:1; height:4px; background:var(--bg); border-radius:2px; overflow:hidden; }
  .yt-seg .sb-fill { height:100%; border-radius:2px; }

  /* History */
  .history-section {
    background:var(--surface); border:1px solid var(--border);
    border-radius:12px; padding:20px 24px; margin-top:20px;
  }
  .history-section h3 { font-size:14px; color:var(--text2); margin-bottom:14px; font-weight:500; }
  .history-item {
    display:grid; grid-template-columns:70px 80px 1fr 60px;
    gap:10px; align-items:center; padding:10px 0;
    border-bottom:1px solid var(--border); font-size:13px; cursor:pointer; transition:background 0.2s;
  }
  .history-item:hover { background:var(--glow); margin:0 -24px; padding:10px 24px; }
  .history-item:last-child { border-bottom: none; }
  .history-time { color: var(--text2); }
  .history-verdict { font-weight: 700; }
  .history-text { color:var(--text2); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

  .no-results { text-align:center; padding:60px 20px; color:var(--text2); }
  .no-results .icon { font-size:48px; margin-bottom:16px; }
  .no-results p { font-size:14px; }

  .footer { text-align:center; padding:30px; color:var(--text2); font-size:12px; }

  @media (max-width:768px) {
    .yt-summary-grid { grid-template-columns: repeat(2,1fr); }
  }
</style>
</head>
<body>

<div class="header">
  <h1>Axiom 5</h1>
  <span class="badge">Logic Filter Engine</span>
  <div class="status">
    <div class="dot"></div>
    <span id="engineStatus">Engine Ready</span>
  </div>
</div>

<div class="container">

  <!-- Input Section -->
  <div class="input-section">
    <h2>검증할 텍스트 입력</h2>
    <div class="tab-bar">
      <div class="tab active" data-tab="text" onclick="switchTab('text')">텍스트 직접 입력</div>
      <div class="tab" data-tab="file" onclick="switchTab('file')">파일 업로드 (.txt)</div>
      <div class="tab yt-tab" data-tab="youtube" onclick="switchTab('youtube')">YouTube 분석</div>
    </div>

    <div id="textTab">
      <textarea id="inputText" placeholder="Gemini, Grok, ChatGPT 등의 답변을 여기에 붙여넣으세요...&#10;&#10;Five Axioms 기반으로 논리적 정합성을 검증합니다."></textarea>
    </div>

    <div id="fileTab" style="display:none">
      <div class="file-upload" id="dropZone" onclick="document.getElementById('fileInput').click()">
        <div class="icon">📄</div>
        <p>클릭하거나 파일을 드래그하세요</p>
        <p style="font-size:12px; margin-top:4px">.txt, .md 파일 지원</p>
      </div>
      <input type="file" id="fileInput" accept=".txt,.md,.text" style="display:none" onchange="handleFile(this)">
      <div class="file-name" id="fileName"></div>
    </div>

    <div id="youtubeTab" style="display:none">
      <div class="yt-input-row">
        <input type="text" class="yt-url-input" id="ytUrl"
          placeholder="YouTube URL을 붙여넣으세요 (예: https://youtube.com/watch?v=...)" />
      </div>
      <div class="yt-info" id="ytInfo">
        <div class="yt-title" id="ytTitle"></div>
        <div class="yt-meta" id="ytMeta"></div>
      </div>
      <div class="yt-progress" id="ytProgress">
        <div class="yt-progress-bar"><div class="yt-progress-fill" id="ytProgressFill"></div></div>
        <div class="yt-progress-text" id="ytProgressText">자막 추출 중...</div>
      </div>
    </div>

    <div class="btn-row">
      <button class="btn btn-primary" id="verifyBtn" onclick="verify()">
        ⚡ 검증 실행
      </button>
      <button class="btn btn-youtube" id="ytBtn" onclick="analyzeYoutube()" style="display:none">
        ▶ YouTube 분석
      </button>
      <div class="spinner" id="spinner"></div>
      <select id="providerSelect" style="
        background:var(--bg); border:1px solid var(--border); border-radius:6px;
        padding:8px 12px; color:var(--text); font-size:13px; outline:none; cursor:pointer;
      ">
        <option value="alexander">Alexander (로컬)</option>
      </select>
      <button class="btn btn-clear" onclick="clearAll()">초기화</button>
    </div>
  </div>

  <!-- Text Result Section -->
  <div class="result-section" id="resultSection">
    <div class="result-card" id="resultCard">
      <div class="verdict-banner" id="verdictBanner">
        <div>
          <div class="verdict-label" id="verdictLabel"></div>
          <div class="verdict-meta">
            <span class="method-badge" id="methodBadge"></span>
            <span id="resultTime"></span>
          </div>
        </div>
        <div class="verdict-score" id="verdictScore"></div>
      </div>
      <div class="axiom-grid" id="axiomGrid"></div>
      <div class="flags-section" id="flagsSection" style="display:none">
        <div class="flags-title">Flags</div>
        <div id="flagsList"></div>
      </div>
    </div>
  </div>

  <!-- YouTube Result Section -->
  <div class="yt-result-section" id="ytResultSection">
    <div class="yt-summary-grid" id="ytSummaryGrid"></div>
    <div class="yt-timeline" id="ytTimeline">
      <h3>시간대별 점수 추이</h3>
      <div class="yt-timeline-bar" id="ytTimelineBar"></div>
      <div class="yt-timeline-labels" id="ytTimelineLabels"></div>
    </div>
    <div class="yt-axiom-avg" id="ytAxiomAvg">
      <h3>공리별 평균 점수</h3>
      <div class="axiom-grid" id="ytAxiomGrid"></div>
    </div>
    <div class="yt-segments" id="ytSegments">
      <h3>구간별 상세 분석</h3>
      <div class="yt-filter-bar">
        <button class="yt-filter-btn active" onclick="filterYtSegments('all',this)">전체</button>
        <button class="yt-filter-btn" onclick="filterYtSegments('FAIL',this)">FAIL</button>
        <button class="yt-filter-btn" onclick="filterYtSegments('REVIEW',this)">REVIEW</button>
        <button class="yt-filter-btn" onclick="filterYtSegments('PASS',this)">PASS</button>
      </div>
      <div id="ytSegmentList"></div>
    </div>
  </div>

  <!-- No Results -->
  <div class="no-results" id="noResults">
    <div class="icon">🏛️</div>
    <p>텍스트를 입력하거나 YouTube URL을 넣고 검증을 실행하면 결과가 여기에 표시됩니다.</p>
  </div>

  <!-- History -->
  <div class="history-section" id="historySection" style="display:none">
    <h3>검증 히스토리</h3>
    <div id="historyList"></div>
  </div>

</div>

<div class="footer">
  Axiom 5 Logic Filter Engine &middot; Five Axioms Framework &middot; Powered by Alexander (Ollama)
</div>

<script>
const API = '';
let history = [];
let fileContent = null;
let ytResults = [];

// 프로바이더 목록 로드
fetch(API + '/api/providers').then(r => r.json()).then(data => {
  const sel = document.getElementById('providerSelect');
  sel.innerHTML = '';
  (data.providers || ['alexander']).forEach(p => {
    const names = {
      alexander: 'Alexander (로컬)',
      claude: 'Claude'
    };
    const opt = document.createElement('option');
    opt.value = p;
    opt.textContent = names[p] || p;
    sel.appendChild(opt);
  });
}).catch(() => {});

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`.tab[data-tab="${tab}"]`).classList.add('active');
  document.getElementById('textTab').style.display = tab === 'text' ? 'block' : 'none';
  document.getElementById('fileTab').style.display = tab === 'file' ? 'block' : 'none';
  document.getElementById('youtubeTab').style.display = tab === 'youtube' ? 'block' : 'none';
  document.getElementById('verifyBtn').style.display = tab === 'youtube' ? 'none' : 'inline-block';
  document.getElementById('ytBtn').style.display = tab === 'youtube' ? 'inline-block' : 'none';
}

// Drag & Drop
const dropZone = document.getElementById('dropZone');
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files.length) handleFile({files: e.dataTransfer.files});
});

function handleFile(input) {
  const file = input.files[0];
  if (!file) return;
  const fn = document.getElementById('fileName');
  fn.style.display = 'block';
  fn.textContent = `📎 ${file.name} (${(file.size/1024).toFixed(1)} KB)`;
  const reader = new FileReader();
  reader.onload = e => { fileContent = e.target.result; };
  reader.readAsText(file);
}

// ===================== Text Verify =====================
async function verify() {
  const btn = document.getElementById('verifyBtn');
  const spinner = document.getElementById('spinner');
  const activeTab = document.querySelector('.tab.active').dataset.tab;

  let text = activeTab === 'text'
    ? document.getElementById('inputText').value.trim()
    : (fileContent || '').trim();

  if (!text) { alert('검증할 텍스트를 입력하세요.'); return; }

  btn.disabled = true;
  spinner.style.display = 'block';
  document.getElementById('engineStatus').textContent = 'Verifying...';

  try {
    const resp = await fetch(API + '/api/verify', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: text, provider: document.getElementById('providerSelect').value})
    });
    const data = await resp.json();
    if (data.error) { alert('Error: ' + data.error); }
    else { showResult(data, text); }
  } catch (err) { alert('서버 연결 실패: ' + err.message); }

  btn.disabled = false;
  spinner.style.display = 'none';
  document.getElementById('engineStatus').textContent = 'Engine Ready';
}

function showResult(data, text) {
  document.getElementById('noResults').style.display = 'none';
  document.getElementById('resultSection').style.display = 'block';
  document.getElementById('ytResultSection').style.display = 'none';

  const v = (data.verdict || 'REVIEW').toUpperCase();
  const banner = document.getElementById('verdictBanner');
  banner.className = 'verdict-banner ' + v.toLowerCase();
  document.getElementById('verdictLabel').textContent = v;
  document.getElementById('verdictScore').textContent = (data.overall_score || 0).toFixed(1);

  const method = data.method || 'rule_based';
  const prov = data.provider || '';
  const mb = document.getElementById('methodBadge');
  const methodLabel = method.startsWith('llm:') ? method.split(':')[1].toUpperCase() : (method === 'llm' ? 'LLM' : 'RULE');
  mb.textContent = methodLabel;
  mb.className = 'method-badge ' + (method.includes('llm') || method.includes('claude') ? 'method-llm' : 'method-rule');
  document.getElementById('resultTime').textContent = ' · ' + new Date().toLocaleTimeString('ko-KR');

  const scores = data.axiom_scores || {};
  renderAxiomBars('axiomGrid', scores);

  const flags = data.flags || [];
  const flagsSection = document.getElementById('flagsSection');
  if (flags.length > 0) {
    flagsSection.style.display = 'block';
    document.getElementById('flagsList').innerHTML = flags.map(f => `<span class="flag-item">${f}</span>`).join('');
  } else { flagsSection.style.display = 'none'; }

  history.unshift({time: new Date(), verdict: v, score: data.overall_score, text: text.substring(0, 80), data: data});
  if (history.length > 20) history.pop();
  updateHistory();
}

// ===================== YouTube Analysis =====================
async function analyzeYoutube() {
  const url = document.getElementById('ytUrl').value.trim();
  if (!url) { alert('YouTube URL을 입력하세요.'); return; }

  const btn = document.getElementById('ytBtn');
  const spinner = document.getElementById('spinner');
  const progress = document.getElementById('ytProgress');

  btn.disabled = true;
  spinner.style.display = 'block';
  spinner.classList.add('yt');
  progress.style.display = 'block';
  document.getElementById('engineStatus').textContent = 'YouTube 분석 중...';
  document.getElementById('ytProgressText').textContent = '자막 추출 중... (최대 1-2분 소요)';
  document.getElementById('ytProgressFill').style.width = '20%';

  try {
    const resp = await fetch(API + '/api/youtube', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url: url})
    });
    const data = await resp.json();

    if (data.error) {
      alert('Error: ' + data.error);
    } else {
      document.getElementById('ytProgressFill').style.width = '100%';
      document.getElementById('ytProgressText').textContent = '분석 완료!';

      if (data.info) {
        document.getElementById('ytInfo').style.display = 'block';
        document.getElementById('ytTitle').textContent = data.info.title || '';
        document.getElementById('ytMeta').textContent =
          (data.info.channel || '') + ' · ' +
          Math.floor((data.info.duration||0)/60) + '분 ' + ((data.info.duration||0)%60) + '초';
      }

      showYoutubeResult(data);
    }
  } catch (err) { alert('서버 연결 실패: ' + err.message); }

  btn.disabled = false;
  spinner.style.display = 'none';
  spinner.classList.remove('yt');
  document.getElementById('engineStatus').textContent = 'Engine Ready';
}

function showYoutubeResult(data) {
  document.getElementById('noResults').style.display = 'none';
  document.getElementById('resultSection').style.display = 'none';
  document.getElementById('ytResultSection').style.display = 'block';

  const stats = data.stats || {};
  const results = data.results || [];
  ytResults = results;

  // Summary cards
  const grid = document.getElementById('ytSummaryGrid');
  grid.innerHTML = `
    <div class="yt-stat-card"><div class="yt-stat-value" style="color:var(--text)">${(stats.avg_score||0).toFixed(1)}</div><div class="yt-stat-label">평균 점수</div></div>
    <div class="yt-stat-card"><div class="yt-stat-value" style="color:var(--pass)">${stats.pass_count||0}</div><div class="yt-stat-label">PASS</div></div>
    <div class="yt-stat-card"><div class="yt-stat-value" style="color:var(--review)">${stats.review_count||0}</div><div class="yt-stat-label">REVIEW</div></div>
    <div class="yt-stat-card"><div class="yt-stat-value" style="color:var(--fail)">${stats.fail_count||0}</div><div class="yt-stat-label">FAIL</div></div>`;

  // Timeline bar
  const tlBar = document.getElementById('ytTimelineBar');
  tlBar.innerHTML = '';
  results.forEach((r, i) => {
    const pct = Math.max(8, r.overall_score);
    const color = r.verdict === 'PASS' ? 'var(--pass)' : (r.verdict === 'REVIEW' ? 'var(--review)' : 'var(--fail)');
    const bar = document.createElement('div');
    bar.className = 'tbar';
    bar.style.height = pct + '%';
    bar.style.background = color;
    bar.title = r.timestamp + ' - ' + r.verdict + ' (' + r.overall_score.toFixed(1) + ')';
    bar.onclick = () => document.getElementById('ytseg-' + i).scrollIntoView({behavior:'smooth'});
    tlBar.appendChild(bar);
  });
  const tlLabels = document.getElementById('ytTimelineLabels');
  if (results.length > 0) {
    tlLabels.innerHTML = '<span>'+results[0].timestamp+'</span>' +
      (results.length > 2 ? '<span>'+results[Math.floor(results.length/2)].timestamp+'</span>' : '') +
      '<span>'+results[results.length-1].timestamp+'</span>';
  }

  // Axiom averages
  const axiomAvgs = stats.axiom_averages || {};
  renderAxiomBars('ytAxiomGrid', axiomAvgs);

  // Segments
  renderYtSegments('all');
}

function renderYtSegments(filter) {
  const list = document.getElementById('ytSegmentList');
  list.innerHTML = '';
  const axiomKeys = {a1:'A1', a2:'A2', a3:'A3', a4:'A4', a5:'A5'};

  ytResults.forEach((r, i) => {
    if (filter !== 'all' && r.verdict !== filter) return;
    const vClass = r.verdict.toLowerCase();
    const color = r.verdict === 'PASS' ? 'var(--pass)' : (r.verdict === 'REVIEW' ? 'var(--review)' : 'var(--fail)');

    let flagsHtml = '';
    if (r.flags && r.flags.length) {
      flagsHtml = '<div class="seg-flags">' + r.flags.map(f => '<span class="seg-flag">'+f+'</span>').join('') + '</div>';
    }

    let barsHtml = '<div class="seg-bars">';
    for (const [k, label] of Object.entries(axiomKeys)) {
      const v = (r.axiom_scores && r.axiom_scores[k]) || 0;
      const c = v >= 75 ? 'var(--pass)' : (v >= 50 ? 'var(--review)' : 'var(--fail)');
      barsHtml += `<div class="seg-bar-item"><span>${label}</span><div class="sb-bg"><div class="sb-fill" style="width:${v}%;background:${c}"></div></div><span>${v}</span></div>`;
    }
    barsHtml += '</div>';

    list.innerHTML += `<div class="yt-seg" id="ytseg-${i}">
      <div class="seg-top">
        <span class="seg-time">${r.timestamp}</span>
        <span class="seg-badge ${vClass}">${r.verdict}</span>
        <span style="font-size:11px;color:var(--text2)">${r.method||''}</span>
        <span class="seg-score" style="color:${color}">${r.overall_score.toFixed(1)}</span>
      </div>
      <div class="seg-text">${r.text}</div>
      ${flagsHtml}
      ${barsHtml}
    </div>`;
  });
}

function filterYtSegments(filter, el) {
  document.querySelectorAll('.yt-filter-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  renderYtSegments(filter);
}

// ===================== Common =====================
const axiomNames = {
  a1: {short:'A1 Logic', full:'보편적 논리 우위'},
  a2: {short:'A2 Entropy', full:'엔트로피 최소화'},
  a3: {short:'A3 MetaCog', full:'재귀적 메타인지'},
  a4: {short:'A4 Structure', full:'탑다운 구조화'},
  a5: {short:'A5 Reject', full:'거짓 거부'}
};

function renderAxiomBars(containerId, scores) {
  const grid = document.getElementById(containerId);
  grid.innerHTML = '';
  for (const [key, info] of Object.entries(axiomNames)) {
    const score = scores[key] || 0;
    const s = typeof score === 'number' ? score : 0;
    const cls = s >= 75 ? 'high' : (s >= 50 ? 'mid' : 'low');
    const color = s >= 75 ? 'var(--pass)' : (s >= 50 ? 'var(--review)' : 'var(--fail)');
    grid.innerHTML += `<div class="axiom-row" title="${info.full}">
      <div class="axiom-name">${info.short}</div>
      <div class="bar-bg"><div class="bar-fill ${cls}" style="width:${s}%"></div></div>
      <div class="axiom-score" style="color:${color}">${s.toFixed?s.toFixed(1):s}</div>
    </div>`;
  }
}

function updateHistory() {
  if (history.length === 0) return;
  document.getElementById('historySection').style.display = 'block';
  const list = document.getElementById('historyList');
  list.innerHTML = history.map((h, i) => {
    const vColor = h.verdict === 'PASS' ? 'var(--pass)' : (h.verdict === 'REVIEW' ? 'var(--review)' : 'var(--fail)');
    return `<div class="history-item" onclick='replayHistory(${i})'>
      <span class="history-time">${h.time.toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit'})}</span>
      <span class="history-verdict" style="color:${vColor}">${h.verdict} ${h.score.toFixed(1)}</span>
      <span class="history-text">${h.text}...</span>
      <span style="color:var(--text2);text-align:right;font-size:12px">보기</span>
    </div>`;
  }).join('');
}

function replayHistory(idx) {
  const h = history[idx];
  showResult(h.data, h.text);
  window.scrollTo({top:0, behavior:'smooth'});
}

function clearAll() {
  document.getElementById('inputText').value = '';
  document.getElementById('ytUrl').value = '';
  fileContent = null;
  document.getElementById('fileName').style.display = 'none';
  document.getElementById('ytInfo').style.display = 'none';
  document.getElementById('ytProgress').style.display = 'none';
  document.getElementById('resultSection').style.display = 'none';
  document.getElementById('ytResultSection').style.display = 'none';
  document.getElementById('noResults').style.display = 'block';
}

document.getElementById('inputText').addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') verify();
});
document.getElementById('ytUrl').addEventListener('keydown', e => {
  if (e.key === 'Enter') analyzeYoutube();
});
</script>
</body>
</html>"""


# ============================================================================
# HTTP 서버 핸들러
# ============================================================================
class AxiomWebHandler(BaseHTTPRequestHandler):
    engine = None
    yt_analyzer = None

    def log_message(self, format, *args):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"  [{timestamp}] {args[0]}")

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif self.path == "/api/status":
            self._json_response({
                "status": "ok",
                "engine": "axiom5",
                "model": self.engine.model,
                "youtube": YOUTUBE_AVAILABLE
            })
        elif self.path == "/api/providers":
            # Alexander(로컬) + Claude만 사용
            all_providers = self.engine.get_available_providers()
            providers = [p for p in all_providers if p in ("alexander", "claude")]
            self._json_response({"providers": providers})
        else:
            self.send_error(404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if self.path == "/api/verify":
            self._handle_verify(body)
        elif self.path == "/api/youtube":
            self._handle_youtube(body)
        else:
            self.send_error(404)

    def _handle_verify(self, body):
        try:
            data = json.loads(body.decode("utf-8"))
            text = data.get("text", "").strip()
            provider = data.get("provider", "alexander")

            if not text:
                self._json_response({"error": "텍스트가 비어있습니다."})
                return
            if len(text) > 10000:
                self._json_response({"error": "텍스트가 너무 깁니다 (최대 10,000자)."})
                return

            old_verbose = self.engine.verbose
            self.engine.verbose = False

            # 모든 프로바이더를 동일 경로로 처리
            result = self.engine.filter_with_provider(
                text, provider=provider, context="web_ui")

            self.engine.verbose = old_verbose

            clean = {
                "verdict": result.get("verdict", "REVIEW"),
                "overall_score": result.get("overall_score", 50),
                "axiom_scores": result.get("axiom_scores", {}),
                "flags": [str(f) for f in result.get("flags", [])],
                "method": result.get("method", "unknown"),
                "provider": result.get("provider", provider),
                "timestamp": result.get("timestamp", ""),
                "optimized": result.get("optimized", "")
            }
            self._json_response(clean)

        except json.JSONDecodeError:
            self._json_response({"error": "잘못된 JSON 형식"})
        except Exception as e:
            self._json_response({"error": str(e)})

    def _handle_youtube(self, body):
        if not YOUTUBE_AVAILABLE:
            self._json_response({
                "error": "axiom_youtube.py가 설치되지 않았습니다. ~/axiom5/ 폴더에 axiom_youtube.py를 넣어주세요."
            })
            return

        try:
            data = json.loads(body.decode("utf-8"))
            url = data.get("url", "").strip()

            if not url:
                self._json_response({"error": "URL이 비어있습니다."})
                return

            if "youtube.com" not in url and "youtu.be" not in url:
                self._json_response({"error": "유효한 YouTube URL을 입력하세요."})
                return

            print(f"  [YouTube] 분석 시작: {url}")

            # 분석 실행
            if self.yt_analyzer is None:
                self.yt_analyzer = YouTubeAnalyzer(engine=self.engine)

            analysis = self.yt_analyzer.analyze_url(url)

            if "error" in analysis:
                self._json_response({"error": analysis["error"]})
                return

            # 영상 정보 추가
            info = self.yt_analyzer.extractor._get_video_info(url)

            response = {
                "results": analysis.get("results", []),
                "stats": analysis.get("stats", {}),
                "info": {
                    "title": info.get("title", ""),
                    "channel": info.get("channel", ""),
                    "duration": info.get("duration", 0)
                } if info else None,
                "source": url,
                "analyzed_at": analysis.get("analyzed_at", "")
            }
            self._json_response(response)

        except json.JSONDecodeError:
            self._json_response({"error": "잘못된 JSON 형식"})
        except Exception as e:
            print(f"  [YouTube Error] {e}")
            self._json_response({"error": str(e)})

    def _json_response(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# ============================================================================
# 메인 실행
# ============================================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Axiom 5 Web UI")
    parser.add_argument("--port", type=int, default=5050, help="포트 (기본: 5050)")
    parser.add_argument("--host", default="127.0.0.1", help="호스트 (기본: 127.0.0.1)")
    parser.add_argument("--model", default="alexander", help="Ollama 모델 (기본: alexander)")
    args = parser.parse_args()

    engine = AxiomEngine(model=args.model, verbose=False)
    AxiomWebHandler.engine = engine

    if YOUTUBE_AVAILABLE:
        AxiomWebHandler.yt_analyzer = YouTubeAnalyzer(engine=engine)

    server = HTTPServer((args.host, args.port), AxiomWebHandler)

    yt_status = "✅ YouTube 분석 가능" if YOUTUBE_AVAILABLE else "❌ axiom_youtube.py 필요"

    print(f"""
============================================================
🏛️  Axiom 5 Web UI - Logic Filter Interface
============================================================
  URL:     http://{args.host}:{args.port}
  Model:   {args.model}
  Engine:  AxiomEngine (Five Axioms Framework)
  YouTube: {yt_status}
============================================================
  브라우저에서 위 URL을 열어주세요.
  Ctrl+C로 중단
""")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 [Web UI 중단]")
        server.server_close()


if __name__ == "__main__":
    main()
