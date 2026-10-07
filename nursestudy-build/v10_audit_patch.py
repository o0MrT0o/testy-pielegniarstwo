from pathlib import Path
import re,json,copy,hashlib,csv
root=Path('.')
p=root/'app/src/main/assets/www/content-data.js'
s=p.read_text()
m=re.search(r"window\.NS_CONTENT\s*=\s*(\{.*\});\s*\n\}\)\(\);?\s*$",s,re.S)
if not m: raise SystemExit('parse failed')
db=json.loads(m.group(1))
# source metadata corrections
S=db['MEDICAL_SOURCES']
S['S23']={'org':'NHS Specialist Pharmacy Service','title':'DOACs (Direct Oral Anticoagulants) monitoring','year':'2026','url':'https://sps.nhs.uk/monitorings/doacs-direct-oral-anticoagulants-monitoring/','note':'Aktualizacja 6.08.2026. DOAC nie wymagają rutynowego monitorowania INR; wymagają okresowej oceny klinicznej, FBC, funkcji nerek/wątroby i interakcji zależnie od preparatu.'}
S['S24']={'org':'Centers for Disease Control and Prevention','title':"Healthy Habits: Antibiotic Do's and Don'ts",'year':'2025; sprawdzone 2026','url':'https://www.cdc.gov/antibiotic-use/about/','note':'Antybiotyki leczą tylko określone zakażenia bakteryjne, nie działają na wirusy; niepotrzebne użycie może powodować działania niepożądane i wspierać rozwój oporności.'}
# new direct sources
S.update({
'S45':{'org':'Institute for Safe Medication Practices (ISMP)','title':'ISMP List of High-Alert Medications in Acute Care Settings','year':'2024','url':'https://www.ismp.org/system/files/resources/2024-01/ISMP_HighAlert_AcuteCare_List_010924_MS5760.pdf','note':'Insuliny, leki przeciwzakrzepowe i opioidy znajdują się na liście leków high-alert; błędy nie muszą być częstsze, ale ich następstwa mogą być cięższe.'},
'S46':{'org':'World Health Organization','title':'Medication safety for look-alike, sound-alike medicines','year':'2023','url':'https://www.who.int/publications/i/item/9789240058897','note':'LASA są uznaną przyczyną błędów lekowych; podobieństwo nazw/opakowań wymaga systemowych zabezpieczeń i dokładnej weryfikacji.'},
'S47':{'org':'U.S. Food and Drug Administration','title':'NARCAN (naloxone hydrochloride) Nasal Spray – Prescribing Information','year':'2023; sprawdzone 2026','url':'https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/208411s007lbl.pdf','note':'Nalokson jest antagonistą opioidowym stosowanym w podejrzeniu przedawkowania; depresja oddechowa może nawrócić, dlatego wymagana jest dalsza obserwacja i możliwość kolejnych dawek.'},
'S48':{'org':'NHS Specialist Pharmacy Service','title':'Warfarin monitoring','year':'2025','url':'https://sps.nhs.uk/monitorings/warfarin-monitoring/','note':'Warfaryna wymaga monitorowania INR; częstotliwość kontroli zależy od etapu leczenia, stabilności INR, interakcji i ryzyka krwawienia.'},
'S49':{'org':'NHS Specialist Pharmacy Service','title':'DOACs (Direct Oral Anticoagulants) monitoring','year':'2026','url':'https://sps.nhs.uk/monitorings/doacs-direct-oral-anticoagulants-monitoring/','note':'DOAC nie wymagają rutynowego monitorowania INR; należy okresowo oceniać m.in. krwawienie/anemię, adherencję, funkcję nerek i wątroby oraz interakcje.'},
'S50':{'org':'Rejestr Produktów Leczniczych / eZdrowie (Polska)','title':'Paracetamol DOZ 500 mg – Charakterystyka Produktu Leczniczego','year':'bieżąca ChPL; sprawdzona 07.10.2026','url':'https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/24677/characteristic','note':'Dla tego produktu ChPL podaje maksymalną dawkę dobową 4000 mg u dorosłych i młodzieży >12 lat; dawkowanie zawsze zależy od konkretnego produktu i pacjenta.'},
'S51':{'org':'Rejestr Produktów Leczniczych / eZdrowie (Polska)','title':'Ibuprofen Dermogen 400 mg – Charakterystyka Produktu Leczniczego','year':'bieżąca ChPL; sprawdzona 07.10.2026','url':'https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/32851/characteristic','note':'NLPZ mogą powodować krwawienie/owrzodzenie/perforację przewodu pokarmowego; istnieje także ryzyko sercowo-naczyniowe i interakcje zwiększające krwawienie.'},
'S52':{'org':'Rejestr Produktów Leczniczych / eZdrowie (Polska)','title':'Enalapril – Charakterystyka Produktu Leczniczego','year':'bieżąca baza RPL; sprawdzona 07.10.2026','url':'https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/2198/characteristic','note':'ACE-I mogą powodować suchy kaszel, hiperkaliemię i obrzęk naczynioruchowy; obrzęk języka/głośni/krtani może zagrażać drożności dróg oddechowych.'},
'S53':{'org':'Rejestr Produktów Leczniczych / eZdrowie (Polska)','title':'Metoprolol – Charakterystyka Produktu Leczniczego','year':'bieżąca baza RPL; sprawdzona 07.10.2026','url':'https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/10594/characteristic','note':'Metoprolol może powodować bradykardię i niedociśnienie; przeciwwskazania i decyzja o podaniu zależą od parametrów pacjenta, wskazania i zlecenia.'},
'S54':{'org':'Rejestr Produktów Leczniczych / eZdrowie (Polska)','title':'Hydrochlorothiazide Orion – Charakterystyka Produktu Leczniczego','year':'bieżąca baza RPL; sprawdzona 07.10.2026','url':'https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/37114/characteristic','note':'Tiazydy, w tym hydrochlorotiazyd, mogą powodować zaburzenia elektrolitowe, w tym hipokaliemię.'},
'S55':{'org':'World Health Organization','title':'The selection and use of essential medicines, 2025: WHO AWaRe classification of antibiotics','year':'2025','url':'https://www.who.int/publications/i/item/B09489','note':'Aktualna klasyfikacja WHO Access, Watch, Reserve służy monitorowaniu i stewardship antybiotyków oraz ograniczaniu presji selekcyjnej i oporności.'},
'S56':{'org':'Centers for Disease Control and Prevention','title':"Healthy Habits: Antibiotic Do's and Don'ts",'year':'2025; sprawdzone 2026','url':'https://www.cdc.gov/antibiotic-use/about/','note':'Antybiotyki nie działają na wirusy; niepotrzebne użycie nie pomaga, może szkodzić i przyczynia się do oporności.'},
'S57':{'org':'Centers for Disease Control and Prevention','title':'Side Effects of Antibiotics','year':'2026','url':'https://www.cdc.gov/antibiotic-use/communication-resources/side-effects.html','note':'Antybiotyki mogą powodować działania niepożądane; biegunka może wymagać oceny, w tym pod kątem C. difficile w odpowiednim kontekście klinicznym.'},
'S58':{'org':'U.S. Food and Drug Administration','title':'FDA updates prescribing information for all opioid pain medicines to provide additional guidance for safe use','year':'2023; bieżące ostrzeżenia sprawdzone 2026','url':'https://www.fda.gov/drugs/drug-safety-communications/fda-updates-prescribing-information-all-opioid-pain-medicines-provide-additional-guidance-safe-use','note':'Łączenie opioidów z alkoholem, benzodiazepinami i innymi depresantami OUN może zwiększać ryzyko sedacji, przedawkowania i depresji oddechowej.'},
'S59':{'org':'World Health Organization','title':'Medication safety in transitions of care','year':'2019; nadal referencyjne w programie Medication Without Harm','url':'https://www.who.int/docs/default-source/patient-safety/who-uhc-sds-2019-9-eng.pdf','note':'Formalna rekoncyliacja lekowa w punktach przejścia opieki ogranicza pominięcia, dublowanie i niezamierzone rozbieżności w listach leków.'}
})
# helpers
q_by={x['id']:x for x in db['QUESTIONS']}
f_by={x['id']:x for x in db['FLASHCARDS']}
l_by={x['id']:x for x in db['LESSONS']['farmakologia']}
# lesson sources
l_by['bezpieczne-leki']['sources']=['S1','S3','S45','S46']
l_by['high-alert']['sources']=['S45','S5']
l_by['antykoagulanty']['sources']=['S48','S49','S20']
l_by['opioidy']['sources']=['S15','S47','S58']
l_by['antybiotyki']['sources']=['S55','S16','S56','S57']
# question source upgrades
source_map={
'q12':'S45','q13':'S20','q14':'S20','q17':'S56','ph14':'S45','ph19':'S46','ph23':'S50','ph24':'S51','ph26':'S47','ph28':'S58','ph29':'S56','ph30':'S56','ph33':'S55','ph34':'S57','ph36':'S48','ph37':'S49','ph39':'S49','ph40':'S49','ph42':'S52','ph43':'S52','ph44':'S52','ph45':'S53','ph46':'S53','ph47':'S54','ph48':'S45','ph50':'S6','ph53':'S6'
}
for i,sid in source_map.items(): q_by[i]['source']=sid
# content corrections/precision
x=q_by['ph23']
x['q']='Zgodnie z ChPL Paracetamol DOZ 500 mg maksymalna dawka dobowa paracetamolu u dorosłego wynosi:'
x['answers']=['10 000 mg','400 mg','1000 mg','4000 mg; inne preparaty lub sytuacja kliniczna mogą wymagać niższego limitu']
x['correct']=3
x['explain']='ChPL Paracetamol DOZ 500 mg podaje 4000 mg/dobę jako maksymalną dawkę dla dorosłych. Nie wolno jednak traktować 4 g jako uniwersalnego limitu dla każdego preparatu i każdego pacjenta — obowiązuje konkretna ChPL, zlecenie i czynniki ryzyka.'
x=q_by['ph49']
x['answers']=['Prawidłowej glikemii bez potrzeby reakcji','Ciężkiej hiperglikemii','Kwasicy ketonowej na podstawie samego wyniku','Hipoglikemii poziomu 1 (54–69 mg/dl)']
x['correct']=3
x['explain']='ADA 2026 definiuje hipoglikemię poziomu 1 jako glukozę <70 mg/dl i jednocześnie ≥54 mg/dl (czyli 54–69 mg/dl). Poziom 2 to <54 mg/dl.'
x=q_by['ph50']
x['explain']='Reguła 15/15 (15 g szybko działających węglowodanów i kontrola po 15 minutach) jest standardowym podejściem u większości przytomnych osób; u części osób korzystających z automatycznego podawania insuliny (AID) może być potrzebna mniejsza ilość węglowodanów zgodnie z indywidualnym planem.'
# flashcard source/precision
f_by['f12']['source']='S45'
f_by['f15']['source']='S20'
f_by['f16'].update({'front':'Czy DOAC monitoruje się rutynowo INR tak jak warfarynę?','back':'Nie. Warfaryna wymaga monitorowania INR, natomiast DOAC nie są rutynowo dawkowane na podstawie INR; wymagają innych kontroli klinicznych i laboratoryjnych.','source':'S49'})
f_by['f17']['source']='S55'
f_by['f35']['source']='S56'
# update metadata
old_meta=db.get('AUDIT_META',{})
db['AUDIT_META']={
 'version':'v1.0-pharmacology-claim-audit','audited_at':'07.10.2026',
 'scopes':{
  'interna':{'status':'audited in v0.9','items':106,'previous_meta':old_meta},
  'farmakologia':{'status':'audited and corrected in v1.0','items':73,'lessons':5,'questions':60,'flashcards':8}
 },
 'method':'Claim-by-claim review against current official guidance, product information/SmPC, safety standards, scientific/academic sources; pharmacology textbook used mainly for foundational PK/PD and class mechanisms.'
}
# write audited data
p.write_text("/* NurseStudy content database — medically audited v1.0 (Interna + Farmakologia). */\n(function(){\n  'use strict';\n  window.NS_CONTENT = "+json.dumps(db,ensure_ascii=False,indent=2)+";\n})();\n")
# bump Android/app version
bg=root/'app/build.gradle'; txt=bg.read_text(); txt=txt.replace('versionCode 9','versionCode 10').replace("versionName '0.9.0-test'","versionName '1.0.0-test'"); bg.write_text(txt)
sw=root/'app/src/main/assets/www/sw.js'; sw.write_text(sw.read_text().replace('nursestudy-v9-interna-audit','nursestudy-v10-pharma-audit'))
# README note
rd=root/'README.md'; r=rd.read_text(); add='''\n\n## v1.0 – audyt Farmakologii 1:1\nFarmakologia (5 lekcji, 60 pytań, 8 fiszek) została poddana audytowi twierdzenie-po-twierdzeniu. Źródła wzmocniono o aktualne dokumenty WHO/ISMP/ADA/CDC, NHS SPS, FDA oraz polskie Charakterystyki Produktów Leczniczych z Rejestru Produktów Leczniczych. Skorygowano m.in. definicję hipoglikemii poziomu 1 i doprecyzowano maksymalną dawkę paracetamolu jako zależną od konkretnej ChPL i pacjenta.\n'''; rd.write_text(r if '## v1.0 – audyt Farmakologii 1:1' in r else r+add)
print('content sha256',hashlib.sha256(p.read_bytes()).hexdigest())
print('sources',len(S),'q',sum(x['subject']=='farmakologia' for x in db['QUESTIONS']),'f',sum(x['subject']=='farmakologia' for x in db['FLASHCARDS']))
