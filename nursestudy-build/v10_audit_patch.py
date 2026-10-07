from pathlib import Path
import re,json,csv,hashlib,shutil,datetime
root=Path('.')
www=root/'app/src/main/assets/www'
p=www/'content-data.js'
s=p.read_text()
m=re.search(r"window\.NS_CONTENT\s*=\s*(\{.*\});\s*\n\}\)\(\);?\s*$",s,re.S)
if not m: raise SystemExit('parse failure')
db=json.loads(m.group(1))

db['MEDICAL_SOURCES']['S23']={
 'org':'NHS Specialist Pharmacy Service',
 'title':'DOACs (Direct Oral Anticoagulants) monitoring',
 'year':'2026',
 'url':'https://www.sps.nhs.uk/monitorings/doacs-direct-oral-anticoagulants-monitoring/',
 'note':'DOAC nie są rutynowo monitorowane INR; wymagają oceny klinicznej oraz okresowego monitorowania m.in. morfologii, funkcji nerek i wątroby zależnie od preparatu i sytuacji.'
}
db['MEDICAL_SOURCES']['S24']={
 'org':'Centers for Disease Control and Prevention',
 'title':"Healthy Habits: Antibiotic Do's and Don'ts",
 'year':'2025',
 'url':'https://www.cdc.gov/antibiotic-use/about/',
 'note':'Antybiotyki leczą tylko określone zakażenia bakteryjne, nie działają na wirusy; niepotrzebne stosowanie zwiększa ryzyko działań niepożądanych i oporności.'
}
new_sources={
'S45':{'org':'Institute for Safe Medication Practices (ISMP)','title':'ISMP List of High-Alert Medications in Acute Care Settings','year':'2024','url':'https://www.ismp.org/system/files/resources/2024-01/ISMP_HighAlert_AcuteCare_List_010924_MS5760.pdf','note':'Insulina, leki przeciwkrzepliwe i opioidy należą do leków wysokiego ryzyka; błędy mogą powodować szczególnie ciężką szkodę.'},
'S46':{'org':'NHS Specialist Pharmacy Service','title':'Warfarin monitoring','year':'2025','url':'https://www.sps.nhs.uk/monitorings/warfarin-monitoring/','note':'Warfaryna wymaga monitorowania INR; częstotliwość zależy od etapu terapii, stabilności wyniku, ryzyka i leków współistniejących.'},
'S47':{'org':'U.S. National Library of Medicine / DailyMed','title':'Ramipril – current prescribing information','year':'2025–2026','url':'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=e8d9a115-71a7-4580-abbd-865e98b5d3f6','note':'Aktualna informacja o produkcie: kaszel, hiperkaliemia i obrzęk naczynioruchowy są znanymi działaniami/ostrzeżeniami inhibitorów ACE.'},
'S48':{'org':'U.S. National Library of Medicine / DailyMed','title':'Metoprolol succinate ER – current prescribing information','year':'2025','url':'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=38429f45-5dc7-4455-840c-dee48f60d95b','note':'Metoprolol może powodować bradykardię; zalecane jest monitorowanie częstości rytmu serca i odpowiednia reakcja przy ciężkiej bradykardii.'},
'S49':{'org':'U.S. National Library of Medicine / DailyMed','title':'Hydrochlorothiazide – current prescribing information','year':'2026','url':'https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=1d6ea4b4-1e3c-4f3f-989c-1a3a3c0da6bd','note':'Tiazydy mogą powodować zaburzenia elektrolitowe, w tym hipokaliemię; u pacjentów z ryzykiem wskazane jest monitorowanie elektrolitów.'},
'S50':{'org':'Centers for Disease Control and Prevention','title':'C. diff: Facts for Clinicians','year':'2026','url':'https://www.cdc.gov/c-diff/hcp/clinical-overview/','note':'C. difficile jest częstą przyczyną biegunki związanej z antybiotykami; biegunka w trakcie lub po antybiotykoterapii może wymagać oceny.'},
'S51':{'org':'World Health Organization','title':'Medication safety for look-alike, sound-alike medicines','year':'2023','url':'https://www.who.int/publications/i/item/9789240058897','note':'Leki look-alike/sound-alike (LASA) są uznanym źródłem błędów lekowych i wymagają strategii zapobiegających pomyłkom.'},
'S52':{'org':'World Health Organization','title':'The selection and use of essential medicines, 2025: WHO AWaRe classification of antibiotics','year':'2025','url':'https://www.who.int/publications/i/item/B09489','note':'Aktualna klasyfikacja AWaRe dzieli antybiotyki na Access, Watch i Reserve i wspiera monitorowanie oraz stewardship.'},
'S53':{'org':'World Health Organization','title':'Medication safety in transitions of care','year':'2019','url':'https://www.who.int/docs/default-source/patient-safety/who-uhc-sds-2019-9-eng.pdf','note':'Rekoncyliacja lekowa to formalny proces zapewniający dokładny i kompletny transfer informacji o lekach na styku miejsc opieki.'},
}
db['MEDICAL_SOURCES'].update(new_sources)
L={x['id']:x for x in db['LESSONS']['farmakologia']}
L['high-alert']['sources']=sorted(set(L['high-alert'].get('sources',[])+['S45']))
L['antykoagulanty']['sources']=sorted(set(['S3','S19','S23','S46']))
L['antybiotyki']['body']=L['antybiotyki']['body'].replace('Antybiotyki leczą zakażenia bakteryjne, a ich niepotrzebne lub niewłaściwe stosowanie zwiększa ryzyko działań niepożądanych i narastania oporności.', 'Antybiotyki są stosowane do leczenia określonych zakażeń bakteryjnych; nie działają na wirusy. Ich niepotrzebne lub niewłaściwe stosowanie zwiększa ryzyko działań niepożądanych i narastania oporności.')
L['antybiotyki']['sources']=sorted(set(['S16','S24','S50','S52']))
Q={x['id']:x for x in db['QUESTIONS'] if x['subject']=='farmakologia'}
Q['q12']['source']='S45'
Q['q13']['source']='S19'
Q['q14']['source']='S19'
Q['q16']['answers'][2]='Lekiem przeciwpłytkowym'
Q['ph15']['source']='S53'
Q['ph19']['source']='S51'
Q['ph33']['q']='Jeżeli wynik mikrobiologiczny pozwala zawęzić terapię i węższy antybiotyk jest klinicznie odpowiedni, dlaczego deeskalacja może być korzystna?'
Q['ph33']['answers']=['Ponieważ każdy węższy antybiotyk zawsze działa szybciej','Ponieważ eliminuje potrzebę oceny klinicznej','Ponieważ zawsze skraca leczenie do jednej dawki','Może ograniczyć niepotrzebnie szeroką ekspozycję na antybiotyki i presję selekcyjną']
Q['ph33']['correct']=3
Q['ph33']['explain']='Stewardship dąży do skutecznego leczenia możliwie ukierunkowanym antybiotykiem, jeśli wynik mikrobiologiczny, miejsce zakażenia i stan kliniczny na to pozwalają.'
Q['ph33']['source']='S24'
Q['ph34']['source']='S50'
Q['ph36']['source']='S46'
for qid in ['ph42','ph43','ph44']: Q[qid]['source']='S47'
for qid in ['ph45','ph46']: Q[qid]['source']='S48'
Q['ph47']['source']='S49'
Q['ph48']['source']='S45'
Q['ph49']['explain']='ADA 2026 definiuje hipoglikemię poziomu 1 jako glikemię <70 mg/dl (3,9 mmol/l) i ≥54 mg/dl (3,0 mmol/l). Próg 70 mg/dl lub mniej jest jednocześnie wartością, przy której zaleca się rozpoczęcie leczenia hipoglikemii; wynik 68 mg/dl spełnia kryterium poziomu 1.'
F={x['id']:x for x in db['FLASHCARDS'] if x['subject']=='farmakologia'}
F['f17']['source']='S52'
meta=db.setdefault('AUDIT_META',{})
meta['farmakologia']={
 'version':'v1.0-pharmacology-claim-audit',
 'audited_at':'07.10.2026',
 'scope':'Farmakologia: 5 lekcji, 60 pytań, 8 fiszek',
 'method':'Item-by-item review against Katzung 16e, WHO, ISMP, FDA/DailyMed, CDC, ADA 2026 and NHS SPS; source-to-claim matching checked separately from factual correctness.',
 'status':'Corrections and source upgrades applied; see Pharmacology_Audit_v1.0.md.'
}
p.write_text("/* NurseStudy content database — medically audited v1.0 (Interna + Pharmacology). */\n(function(){\n  'use strict';\n  window.NS_CONTENT = "+json.dumps(db,ensure_ascii=False,indent=2)+";\n})();\n")
bg=root/'app/build.gradle'; t=bg.read_text(); t=t.replace('versionCode 9','versionCode 10').replace("versionName '0.9.0-test'","versionName '1.0.0-test'"); bg.write_text(t)
sw=www/'sw.js'; sw.write_text(sw.read_text().replace('nursestudy-v9-interna-audit','nursestudy-v10-pharm-audit'))
rd=root/'README.md'; rt=rd.read_text(); add='\n\n## v1.0 – audyt Farmakologii 1:1\nFarmakologia (5 lekcji, 60 pytań, 8 fiszek) została sprawdzona element po elemencie względem aktualnych źródeł. Skorygowano precyzję definicji hipoglikemii ADA, przypisanie źródeł dla warfaryny/DOAC, AWaRe 2025, LASA, high-alert oraz źródła dla ACEI, beta-adrenolityków, tiazydów i biegunki związanej z antybiotykami.\n';
if '## v1.0 – audyt Farmakologii 1:1' not in rt: rd.write_text(rt+add)
