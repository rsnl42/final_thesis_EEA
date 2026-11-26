#!/usr/bin/env python3
"""
patch_kpi_provenance.py
=======================
Three targeted patches to index.html:

1. REAL-MODE WIRE-UP: updateSurveyDiscrepancyCards() now reads from
   CURRENT_SURVEY.countrySignals (real Kobo data) instead of bailing out
   with `return`, so values update automatically when real data arrives.

2. DATA FRESHNESS: Adds a provenance bar beneath the matrix subtitle
   showing source (Demo / Live Kobo), last-updated timestamp, and
   suppression notice. Updated dynamically in both modes.

3. PARTICIPANT COUNT: Shows a compact "N=X contributors from [Country]"
   pill inside the header area of the Discrepancy Matrix section,
   built from both demo and real countrySignals.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / 'index.html'

html = HTML.read_text(encoding='utf-8')

# ─────────────────────────────────────────────────────────────────
# PATCH 1  HTML: Add provenance bar + N-pill inside the matrix header
# ─────────────────────────────────────────────────────────────────
OLD_HEADER_BOTTOM = '''            <div class="text-xs text-stone-500 font-mono bg-stone-100 px-3 py-1.5 rounded-lg border border-stone-200">
              Verified Sources: UIS · WDI · ITU · IMF vs. Ground-Truth Telemetry
            </div>'''

NEW_HEADER_BOTTOM = '''            <div class="flex flex-col items-end gap-1.5 shrink-0">
              <div class="text-xs text-stone-500 font-mono bg-stone-100 px-3 py-1.5 rounded-lg border border-stone-200">
                Verified Sources: UIS · WDI · ITU · IMF vs. Ground-Truth Telemetry
              </div>
              <div id="discrepancy-provenance-bar" class="flex flex-wrap items-center gap-2 text-[11px]">
                <span id="discrepancy-n-pill" class="badge-pill bg-emerald-100 text-emerald-900 font-mono font-bold border border-emerald-300 text-[11px]">
                  N=600 teacher · N=120 provider · N=80 expert
                </span>
                <span id="discrepancy-freshness" class="text-stone-400 font-mono">
                  Calibrated synthetic baseline · 2026-10-30
                </span>
              </div>
            </div>'''

assert OLD_HEADER_BOTTOM in html, "OLD_HEADER_BOTTOM not found — layout may have changed"
html = html.replace(OLD_HEADER_BOTTOM, NEW_HEADER_BOTTOM, 1)

# ─────────────────────────────────────────────────────────────────
# PATCH 2  JS: updateSurveyDiscrepancyCards — real-mode wire-up
#
# Replace the early-return guard and add real-mode logic that
# reads from CURRENT_SURVEY.countrySignals (by country name).
# ─────────────────────────────────────────────────────────────────
OLD_FUNC_OPEN = '''    function updateSurveyDiscrepancyCards(iso) {
      if (surveyDataMode === 'real') return;
      const targetIso = iso || _activeIso || 'KEN';
      const cData = (typeof countryData !== 'undefined' && countryData[targetIso]) ? countryData[targetIso] : {};
      const rawName = cData.name || (targetIso === 'KEN' ? 'Kenya' : targetIso);
      const countryName = rawName.replace(/^[^\\w\\s]+\\s*/, '').replace(/\\s*\\([A-Z]{3}\\)$/, '').trim();
      const flagEmoji = rawName.match(/^(\\p{Extended_Pictographic}+)/u)?.[1] || '';

      const sig = (typeof SURVEY_COUNTRY_SIGNALS !== 'undefined' && (SURVEY_COUNTRY_SIGNALS[targetIso] || SURVEY_COUNTRY_SIGNALS[countryName])) || null;
      const bench = (typeof SURVEY_COUNTRY_SIGNALS !== 'undefined' && SURVEY_COUNTRY_SIGNALS['_BENCHMARK']) ? SURVEY_COUNTRY_SIGNALS['_BENCHMARK'] : {
        rural_outage_pct: 82.5,
        rural_outage_count: 217,
        rural_n: 263,
        personal_data_pct: 39.3,
        personal_data_count: 236,
        teachers_n: 600,
        phone_pct: 70.8,
        offline_pct: 31.7,
        providers_n: 120,
        donor_risk_pct: 85.0,
        donor_risk_count: 68,
        experts_n: 80,
        macro_rural_elec_pct: 28.4,
        macro_fixed_bb: '< 1.2'
      };

      // Header Context Badge
      const elActiveBadge = document.getElementById('discrepancy-active-country-badge');
      if (elActiveBadge) {
        elActiveBadge.textContent = `${flagEmoji ? flagEmoji + ' ' : ''}${countryName} Focal Telemetry`;
      }'''

NEW_FUNC_OPEN = '''    function updateSurveyDiscrepancyCards(iso) {
      const targetIso = iso || _activeIso || 'KEN';
      const cData = (typeof countryData !== 'undefined' && countryData[targetIso]) ? countryData[targetIso] : {};
      const rawName = cData.name || (targetIso === 'KEN' ? 'Kenya' : targetIso);
      const countryName = rawName.replace(/^[^\\w\\s]+\\s*/, '').replace(/\\s*\\([A-Z]{3}\\)$/, '').trim();
      const flagEmoji = rawName.match(/^(\\p{Extended_Pictographic}+)/u)?.[1] || '';

      // ── Real-mode: use live Kobo country signals from CURRENT_SURVEY ──────────
      // countrySignals keyed by country name (e.g. "Kenya"), each entry has
      // { n, powerN, pct, reliablePowerPct } from process_kobo_surveys.py.
      // Values are suppressed (undefined) when the country cell is below the
      // publication threshold, so we gracefully fall back to the SSA benchmark.
      let sig = null;
      let dataSource = 'demo';
      let generatedAt = SURVEY_BASELINE?.metadata?.lastUpdated || '2026-10-30';
      let suppressionNote = '';

      if (surveyDataMode === 'real' && CURRENT_SURVEY?.countrySignals) {
        const realSig = CURRENT_SURVEY.countrySignals[countryName];
        if (realSig && realSig.n >= 1) {
          // Translate real-schema fields → same shape as demo sig
          sig = {
            teachers_n: realSig.n,
            rural_n: realSig.powerN || realSig.n,
            // reliablePowerPct → rural_outage_pct (unreliable = 100 - reliable)
            rural_outage_pct: realSig.reliablePowerPct !== undefined
              ? Math.round((100 - realSig.reliablePowerPct) * 10) / 10
              : null,
            rural_outage_count: null,       // not available in Kobo aggregate
            personal_data_pct: null,        // not measured by Kobo instrument
            personal_data_count: null,
            providers_n: CURRENT_SURVEY.providers?.total || null,
            phone_pct: null,                // not in Kobo cross-national aggregate
            offline_pct: null,
            experts_n: CURRENT_SURVEY.experts?.total || null,
            donor_risk_pct: null,           // only as absolute count in Kobo
            donor_risk_count: CURRENT_SURVEY.experts?.postGrantRiskCount || null,
            _live: true,
          };
          dataSource = 'live';
          generatedAt = CURRENT_SURVEY.generatedAt || generatedAt;
          suppressionNote = ` · N<${CURRENT_SURVEY.suppressionThreshold || 5} suppressed`;
        } else {
          // Country below publication threshold → SSA aggregate fallback
          dataSource = 'live-agg';
          generatedAt = CURRENT_SURVEY.generatedAt || generatedAt;
          suppressionNote = ` · ${countryName} cell suppressed (N<${CURRENT_SURVEY.suppressionThreshold || 5}); showing cross-national aggregate`;
        }
      } else if (surveyDataMode !== 'real') {
        // Demo / simulation: use precomputed multi-country signals
        sig = (typeof SURVEY_COUNTRY_SIGNALS !== 'undefined' &&
               (SURVEY_COUNTRY_SIGNALS[targetIso] || SURVEY_COUNTRY_SIGNALS[countryName])) || null;
      }

      const bench = (typeof SURVEY_COUNTRY_SIGNALS !== 'undefined' && SURVEY_COUNTRY_SIGNALS['_BENCHMARK']) ? SURVEY_COUNTRY_SIGNALS['_BENCHMARK'] : {
        rural_outage_pct: 82.5,
        rural_outage_count: 217,
        rural_n: 263,
        personal_data_pct: 39.3,
        personal_data_count: 236,
        teachers_n: 600,
        phone_pct: 70.8,
        offline_pct: 31.7,
        providers_n: 120,
        donor_risk_pct: 85.0,
        donor_risk_count: 68,
        experts_n: 80,
        macro_rural_elec_pct: 28.4,
        macro_fixed_bb: '< 1.2'
      };

      // ── Provenance bar ────────────────────────────────────────────────────────
      const elProvBar = document.getElementById('discrepancy-provenance-bar');
      const elNpill = document.getElementById('discrepancy-n-pill');
      const elFreshness = document.getElementById('discrepancy-freshness');

      const tN = sig?.teachers_n || bench.teachers_n;
      const pN = sig?.providers_n || bench.providers_n;
      const eN = sig?.experts_n || bench.experts_n;

      if (elNpill) {
        if (dataSource === 'live') {
          elNpill.textContent = `N=${tN} teachers · ${countryName} live`;
          elNpill.className = 'badge-pill bg-indigo-100 text-indigo-900 font-mono font-bold border border-indigo-300 text-[11px]';
        } else if (dataSource === 'live-agg') {
          elNpill.textContent = `N=${tN} teachers · ${pN} providers · ${eN} experts (SSA cross-national)`;
          elNpill.className = 'badge-pill bg-amber-100 text-amber-900 font-mono font-bold border border-amber-300 text-[11px]';
        } else {
          const countryTN = sig?.teachers_n;
          const countryPN = sig?.providers_n;
          const countryEN = sig?.experts_n;
          elNpill.textContent = countryTN
            ? `N=${countryTN} teachers · N=${countryPN || '—'} providers · N=${countryEN || '—'} experts (${countryName})`
            : `N=${bench.teachers_n} teachers · N=${bench.providers_n} providers · N=${bench.experts_n} experts (SSA)`;
          elNpill.className = 'badge-pill bg-emerald-100 text-emerald-900 font-mono font-bold border border-emerald-300 text-[11px]';
        }
      }

      if (elFreshness) {
        const modeLabel = dataSource === 'live' ? '🟢 Live Kobo' :
                          dataSource === 'live-agg' ? '🟡 Live Kobo (agg)' :
                          '🔵 Calibrated synthetic baseline';
        elFreshness.textContent = `${modeLabel} · ${generatedAt}${suppressionNote}`;
      }

      // ── Header Context Badge ──────────────────────────────────────────────────
      const elActiveBadge = document.getElementById('discrepancy-active-country-badge');
      if (elActiveBadge) {
        elActiveBadge.textContent = `${flagEmoji ? flagEmoji + ' ' : ''}${countryName} Focal Telemetry`;
      }'''

assert OLD_FUNC_OPEN in html, "OLD_FUNC_OPEN not found — function signature may have changed"
html = html.replace(OLD_FUNC_OPEN, NEW_FUNC_OPEN, 1)

# ─────────────────────────────────────────────────────────────────
# PATCH 3  JS: renderRealSurveyDashboard — also refresh cards after
#          live data loads so provenance bar and N-pill update
# ─────────────────────────────────────────────────────────────────
OLD_REAL_BADGE = '''      const elActiveBadge = document.getElementById('discrepancy-active-country-badge');
      if (elActiveBadge) {
        elActiveBadge.textContent = 'Published Kobo Aggregate (Cross-National)';
      }

      const rural = (teachers.elecByLocation || [])'''

NEW_REAL_BADGE = '''      // Refresh country-aware KPI cards with live Kobo data
      if (typeof updateSurveyDiscrepancyCards === 'function') {
        updateSurveyDiscrepancyCards(_activeIso || 'KEN');
      }

      const rural = (teachers.elecByLocation || [])'''

assert OLD_REAL_BADGE in html, "OLD_REAL_BADGE not found — renderRealSurveyDashboard may have changed"
html = html.replace(OLD_REAL_BADGE, NEW_REAL_BADGE, 1)

# ─────────────────────────────────────────────────────────────────
# Write out
# ─────────────────────────────────────────────────────────────────
HTML.write_text(html, encoding='utf-8')
print("Done — 3 patches applied successfully.")
