"""Full E2E test: Extract → Validate → Taba → Confirm → Process → Download"""
import subprocess, json, time, os, sys

BASE = 'http://localhost:8000'
PDF = 'data/reference/סיכום בדיקת התכנות מותנה.pdf'

def c(m, p, d=None):
    cmd = ['curl', '-s', '-X', m]
    if d:
        cmd += ['-H', 'Content-Type: application/json', '-d', json.dumps(d, ensure_ascii=False)]
    cmd.append(f'{BASE}{p}')
    r = subprocess.run(cmd, capture_output=True, timeout=60)
    return json.loads(r.stdout.decode('utf-8', 'replace'))

def cu(p, f, timeout=60):
    r = subprocess.run(['curl', '-s', '-X', 'POST', '-F', f'files=@{f}', f'{BASE}{p}'],
                       capture_output=True, timeout=timeout)
    return json.loads(r.stdout.decode('utf-8', 'replace'))

print('=' * 60)
print('FULL E2E: Extract -> Taba -> Submit -> Process -> Download')
print('=' * 60)

# Step 1: Extract
print('\n[1] Extracting buildings from PDF (timeout 180s)...')
ext = cu('/api/v1/extract', PDF, timeout=180)
print(f'    Buildings: {ext.get("building_count", 0)}')
print(f'    Tabas: {ext.get("taba_count", 0)}')
for w in ext.get('warnings', []):
    print(f'    Warning: {w}')
for b in ext.get('buildings', []):
    print(f'    Building #{b.get("id")} {b.get("name","")} | {b.get("building_type")} | {b.get("main_area_sqm")}sqm')
for cl in ext.get('document_classifications', []):
    print(f'    Doc: {cl.get("filename","")} -> {cl.get("detected_type","")} (relevant={cl.get("is_relevant")})')

buildings = ext.get('buildings', [])
if not buildings:
    print('    No buildings from AI, using manual test data')
    buildings = [
        {'id': 1, 'name': 'בית מגורים ראשון', 'building_type': 'residential',
         'status': 'compliant', 'main_area_sqm': 180, 'service_area_sqm': 40,
         'mamad_area_sqm': 12, 'building_order': 1, 'user_confirmed': True},
        {'id': 2, 'name': 'בית מגורים שני', 'building_type': 'residential',
         'status': 'deviation', 'main_area_sqm': 160, 'deviation_sqm': 30,
         'building_order': 2, 'user_confirmed': True},
    ]
for b in buildings:
    b['user_confirmed'] = True
    b.setdefault('building_order', b.get('id', 1))

# Step 2: Taba
print('\n[2] Taba data (manual)...')
tabas = [{
    'taba_number': '616-0902908', 'taba_name': 'תבע נהלל',
    'status': 'approved', 'plot_size_sqm': 2500,
    'num_units_allowed': 2, 'main_area_sqm': 160, 'service_area_sqm': 55,
    'split_allowed': True, 'pool_allowed': False,
    'is_primary': True, 'source': 'manual',
}]
print(f'    {tabas[0]["taba_number"]} | plot={tabas[0]["plot_size_sqm"]}sqm | main={tabas[0]["main_area_sqm"]}sqm')

# Step 3: Submit
print('\n[3] Submitting job...')
r = c('POST', '/api/v1/jobs', {
    'owner_name': 'מותנה אריק', 'moshav_name': 'בני ראם',
    'gush': 3657, 'helka': 42, 'num_existing_houses': 2,
    'authorization_type': 'choze_chachira_mehuvon', 'is_capitalized': True,
    'capitalization_track': '375',
    'client_goals': ['regularization', 'capitalization', 'split'],
    'has_intergenerational_continuity': True,
    'ownership_type': 'single', 'has_demolition_orders': False,
    'shovi_per_sqm': 7000,
    'pre_extracted_buildings': buildings,
    'pre_extracted_tabas': tabas,
})
jid = r['job_id']
print(f'    Job: {jid}')

# Step 4: Upload file
print('\n[4] Uploading PDF...')
up = cu(f'/api/v1/jobs/{jid}/files', PDF)
print(f'    {up.get("message")}')

# Step 5: Poll
print('\n[5] Processing...')
for i in range(60):
    time.sleep(5)
    s = c('GET', f'/api/v1/jobs/{jid}/status')
    st = s['status']
    if i % 3 == 0 or st in ('complete', 'failed', 'checkpoint'):
        print(f'    [{i*5:3d}s] {st} | {s["phase"]} | {s["progress_percent"]}%')

    if st == 'checkpoint':
        print('    >>> Checkpoint — confirming...')
        bldgs = c('GET', f'/api/v1/jobs/{jid}/buildings')
        c('POST', f'/api/v1/jobs/{jid}/classify/confirm', {
            'buildings': [{'id': b['id'], 'building_type': b.get('building_type', 'residential'),
                          'status': b.get('status', 'compliant'),
                          'main_area_sqm': b.get('main_area_sqm', 0),
                          'name': b.get('name', '')}
                         for b in bldgs.get('buildings', [])]
        })
        print('    >>> Confirmed!')

    elif st == 'complete':
        res = c('GET', f'/api/v1/jobs/{jid}/results')
        print(f'\n{"="*60}')
        print('RESULTS')
        print('='*60)
        print(f'  Usage fees:       {res["total_usage_fees"]:>12,.0f} ILS')
        print(f'  Permit fees:      {res["total_permit_fees"]:>12,.0f} ILS')
        print(f'  Betterment levy:  {res["betterment_levy"]:>12,.0f} ILS')
        h375 = res.get('hivun_375_total', 0) or 0
        h33 = res.get('hivun_33_total', 0) or 0
        print(f'  Hivun 3.75%:      {h375:>12,.0f} ILS')
        print(f'  Hivun 33%:        {h33:>12,.0f} ILS')
        print(f'  Downloads:        {res["download_types"]}')

        for ft in res.get('download_types', []):
            out = f'output/e2e_{ft}'
            subprocess.run(['curl', '-s', '-o', out,
                f'{BASE}/api/v1/jobs/{jid}/download/{ft}'], timeout=30)
            sz = os.path.getsize(out) if os.path.exists(out) else 0
            print(f'  File {ft}: {sz:,} bytes')

        print(f'\n  === VALIDATION ===')
        ok = 0
        total = 5
        for name, val in [
            ('Permit fees > 0', res['total_permit_fees'] > 0),
            ('Hivun 3.75% > 0', h375 > 0),
            ('Hivun 33% > 0', h33 > 0),
            ('Word download', 'word' in res['download_types']),
            ('Audit download', 'audit' in res['download_types']),
        ]:
            r = 'PASS' if val else 'FAIL'
            if val: ok += 1
            print(f'  {r}: {name}')
        print(f'\n  {ok}/{total} checks passed')
        break

    elif st == 'failed':
        print(f'\n  FAILED: {s["message"]}')
        sys.exit(1)
        break
else:
    print('\n  TIMEOUT')
    sys.exit(1)

print(f'\n{"="*60}')
print('E2E COMPLETE')
print('='*60)
