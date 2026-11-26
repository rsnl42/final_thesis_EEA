#!/usr/bin/env python3
"""
compile_survey_country_signals.py
=================================
Precomputes multi-country ground-truth telemetry signals across all 48 SSA nations
calibrated against the N=800 survey dataset (600 Teachers, 120 Providers, 80 Experts).

Outputs:
- data/processed/survey_country_signals.json
Used by the Community Evidence Layer to dynamically populate the 4 Discrepancy KPI cards
based on the selected country, with comparison against the SSA Continental Benchmark.
"""

import json
from pathlib import Path
from process_kobo_surveys import COUNTRY_NAMES

def main():
    root = Path(__file__).resolve().parent.parent
    calibrated_path = root / 'data/processed/survey_data_calibrated.json'
    out_path = root / 'data/processed/survey_country_signals.json'

    with open(calibrated_path, 'r', encoding='utf-8') as f:
        cal = json.load(f)

    t_records = cal['teachers']['records']
    p_records = cal['providers']['records']
    e_records = cal['experts']['records']

    name_to_iso = {v: k for k, v in COUNTRY_NAMES.items()}
    all_countries = sorted(list(set(r['country'] for r in t_records)))

    # Continental Benchmarks
    rural_all = [r for r in t_records if 'rural' in r.get('location', '').lower()]
    rural_outage_all = [r for r in rural_all if r.get('elec') in ['Unreliable (frequent cuts)', 'No electricity at all']]
    personal_data_all = [r for r in t_records if r.get('internet') == 'Mobile data only (personal cost)']
    p_phone_all = [p for p in p_records if p.get('minDevice') == 'A low-cost smartphone']
    p_offline_all = [p for p in p_records if p.get('offline') == 'Yes, fully offline']
    e_risk_all = [e for e in e_records if e.get('donorExit') in ['It stops completely or collapses', 'It shrinks to a small token presence']]

    benchmark = {
        'rural_outage_pct': round(len(rural_outage_all) * 100 / len(rural_all), 1),
        'rural_outage_count': len(rural_outage_all),
        'rural_n': len(rural_all),
        'personal_data_pct': round(len(personal_data_all) * 100 / len(t_records), 1),
        'personal_data_count': len(personal_data_all),
        'teachers_n': len(t_records),
        'phone_pct': round(len(p_phone_all) * 100 / len(p_records), 1),
        'offline_pct': round(len(p_offline_all) * 100 / len(p_records), 1),
        'providers_n': len(p_records),
        'donor_risk_pct': round(len(e_risk_all) * 100 / len(e_records), 1),
        'donor_risk_count': len(e_risk_all),
        'experts_n': len(e_records),
        'macro_rural_elec_pct': 28.4,
        'macro_fixed_bb': '< 1.2'
    }

    data = {'_BENCHMARK': benchmark}

    for c in all_countries:
        iso = name_to_iso.get(c, '')
        t_c = [r for r in t_records if r.get('country') == c]
        rural_t = [r for r in t_c if 'rural' in r.get('location', '').lower()]
        rural_outage = [r for r in rural_t if r.get('elec') in ['Unreliable (frequent cuts)', 'No electricity at all']]
        personal_data = [r for r in t_c if r.get('internet') == 'Mobile data only (personal cost)']
        digital_use = [r for r in t_c if r.get('usesDigital') == 'Yes']

        p_c = [p for p in p_records if c in p.get('operatingCountries', '') or p.get('hqCountry') == c]
        p_phone = [p for p in p_c if p.get('minDevice') == 'A low-cost smartphone']
        p_offline = [p for p in p_c if p.get('offline') == 'Yes, fully offline']
        
        e_c = [e for e in e_records if e.get('country') == c]
        e_risk = [e for e in e_c if e.get('donorExit') in ['It stops completely or collapses', 'It shrinks to a small token presence']]

        entry = {
            'n': len(t_c),
            'pct': round(len(digital_use) * 100 / len(t_c), 1) if t_c else 0.0,
            'iso': iso,
            'country': c,
            'teachers_n': len(t_c),
            'rural_n': len(rural_t),
            'rural_outage_count': len(rural_outage),
            'rural_outage_pct': round(len(rural_outage) * 100 / len(rural_t), 1) if rural_t else benchmark['rural_outage_pct'],
            'personal_data_count': len(personal_data),
            'personal_data_pct': round(len(personal_data) * 100 / len(t_c), 1) if t_c else benchmark['personal_data_pct'],
            'providers_n': len(p_c),
            'phone_pct': round(len(p_phone) * 100 / len(p_c), 1) if p_c else benchmark['phone_pct'],
            'offline_pct': round(len(p_offline) * 100 / len(p_c), 1) if p_c else benchmark['offline_pct'],
            'experts_n': len(e_c),
            'donor_risk_count': len(e_risk),
            'donor_risk_pct': round(len(e_risk) * 100 / len(e_c), 1) if e_c else benchmark['donor_risk_pct']
        }
        data[c] = entry
        if iso:
            data[iso] = entry

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f'Successfully compiled survey signals for {len(all_countries)} SSA nations into {out_path}')

if __name__ == '__main__':
    main()
