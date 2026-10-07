from pathlib import Path
import re

root=Path('.')
www=root/'app/src/main/assets/www'
app=www/'app.js'
text=app.read_text()
lines=text.splitlines()
names=['VERIFIED_AT','SUBJECTS','MEDICAL_SOURCES','LESSONS','QUESTIONS','FLASHCARDS']
vals={}
for i,name in enumerate(names):
    line=lines[i]
    m=re.fullmatch(rf"const {re.escape(name)} = (.*);", line)
    if not m:
        raise SystemExit(f'Unexpected content declaration for {name}: {line[:80]}')
    vals[name]=m.group(1)
content="""/* NurseStudy content database. Keep medical content separate from UI/learning engine. */\n(function(){\n  'use strict';\n  window.NS_CONTENT = {\n"""
for idx,name in enumerate(names):
    content += f"    {name}: {vals[name]}" + ("," if idx<len(names)-1 else "") + "\n"
content += "  };\n})();\n"
(www/'content-data.js').write_text(content)
rest='\n'.join(lines[6:])+'\n'
header="""if(!window.NS_CONTENT){throw new Error('NurseStudy content-data.js was not loaded');}\nconst {VERIFIED_AT,SUBJECTS,MEDICAL_SOURCES,LESSONS,QUESTIONS,FLASHCARDS}=window.NS_CONTENT;\n"""
app.write_text(header+rest)

idx=www/'index.html'
s=idx.read_text()
if 'content-data.js' not in s:
    s=s.replace('<script src="app.js" defer></script>','<script src="content-data.js" defer></script>\n  <script src="app.js" defer></script>')
idx.write_text(s)

bg=root/'app/build.gradle'
b=bg.read_text().replace('versionCode 6','versionCode 7').replace("versionName '0.6.0-test'","versionName '0.7.0-test'")
bg.write_text(b)

sw=www/'sw.js'
s=sw.read_text().replace('nursestudy-v6-core','nursestudy-v7-content-arch')
if "'content-data.js'" not in s and '"content-data.js"' not in s:
    s=s.replace("'app.js',", "'app.js','content-data.js',")
    s=s.replace('"app.js",', '"app.js","content-data.js",')
sw.write_text(s)

(root/'tools').mkdir(exist_ok=True)
validator=r'''import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('app/src/main/assets/www/content-data.js','utf8');
const context={window:{}};
vm.createContext(context);
vm.runInContext(source,context,{filename:'content-data.js'});
const db=context.window.NS_CONTENT;
if(!db) throw new Error('NS_CONTENT missing');
const {SUBJECTS,MEDICAL_SOURCES,LESSONS,QUESTIONS,FLASHCARDS,VERIFIED_AT}=db;
const errors=[];
const seen=new Map();
function unique(type,id){const key=`${type}:${id}`;if(seen.has(key))errors.push(`Duplicate ${type} id: ${id}`);seen.set(key,true)}
function sourceExists(id,where){if(!id||!MEDICAL_SOURCES[id])errors.push(`${where}: missing/unknown source ${String(id)}`)}
function subjectExists(id,where){if(!SUBJECTS.some(s=>s.id===id))errors.push(`${where}: unknown subject ${id}`)}
if(!/^\d{2}\.\d{2}\.\d{4}$/.test(VERIFIED_AT||'')) errors.push('VERIFIED_AT must be DD.MM.YYYY');
for(const s of SUBJECTS){unique('subject',s.id);if(!s.name||!s.desc)errors.push(`Subject ${s.id}: missing name/desc`)}
for(const [sid,list] of Object.entries(LESSONS)){
  subjectExists(sid,`lessons/${sid}`);
  for(const l of list){unique(`lesson:${sid}`,l.id);if(!l.title||!l.body)errors.push(`lesson ${sid}/${l.id}: missing title/body`);for(const src of l.sources||[])sourceExists(src,`lesson ${sid}/${l.id}`)}
}
for(const q of QUESTIONS){
  unique('question',q.id);subjectExists(q.subject,`question ${q.id}`);sourceExists(q.source,`question ${q.id}`);
  if(!Array.isArray(q.answers)||q.answers.length!==4)errors.push(`question ${q.id}: must have 4 answers`);
  if(!Number.isInteger(q.correct)||q.correct<0||q.correct>=q.answers.length)errors.push(`question ${q.id}: invalid correct index`);
  if(!q.q||!q.explain)errors.push(`question ${q.id}: missing text/explanation`);
}
for(const f of FLASHCARDS){unique('flashcard',f.id);subjectExists(f.subject,`flashcard ${f.id}`);sourceExists(f.source,`flashcard ${f.id}`);if(!f.front||!f.back)errors.push(`flashcard ${f.id}: missing front/back`)}
for(const [id,src] of Object.entries(MEDICAL_SOURCES)){if(!src.org||!src.title||!src.year||!src.url)errors.push(`source ${id}: incomplete metadata`);try{new URL(src.url)}catch{errors.push(`source ${id}: invalid URL`)}}
if(errors.length){console.error(errors.join('\n'));process.exit(1)}
const lessons=Object.values(LESSONS).reduce((n,x)=>n+x.length,0);
console.log(JSON.stringify({subjects:SUBJECTS.length,lessons,questions:QUESTIONS.length,flashcards:FLASHCARDS.length,sources:Object.keys(MEDICAL_SOURCES).length,verifiedAt:VERIFIED_AT},null,2));
'''
(root/'tools/validate-content.mjs').write_text(validator)

readme=root/'README.md'
r=readme.read_text() if readme.exists() else ''
if '## v0.7 content architecture' not in r:
    r += '\n\n## v0.7 content architecture\nTreści medyczne są w `content-data.js`, logika aplikacji w `app.js`, a `tools/validate-content.mjs` kontroluje spójność banku przed buildem.\n'
readme.write_text(r)
