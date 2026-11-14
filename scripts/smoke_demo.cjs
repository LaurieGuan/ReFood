// Run with NODE_PATH pointing to an installed Playwright; no mocked provider calls.
// Usage: NODE_PATH=/tmp/refood-browser/node_modules node scripts/smoke_demo.cjs PHOTO
const { chromium } = require('playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
(async () => {
  if (!process.argv[2]) throw Error('Supply a test image; this invokes the configured live vision provider.');
  const browser = await chromium.launch({headless:true,args:['--no-sandbox']});
  const context = await browser.newContext({acceptDownloads:true});
  const page = await context.newPage();
  const failures=[];
  page.on('pageerror',e=>failures.push(e.message));
  page.on('console',m=>{if(m.type()==='error')failures.push(m.text())});
  page.on('response',r=>{if(r.url().includes('/api/v1/')&&r.status()>=400)failures.push(`${r.status()} ${r.url()}`)});
  const base=process.env.REFOOD_UI_URL||'http://127.0.0.1:5173';
  const original=await context.request.get(base+'/api/v1/pantry');
  assert.equal(original.status(),200);
  const snapshot=await original.json();
  try {
    await page.goto(base);
    await page.getByRole('button',{name:/Découvrir la démo/}).click();
    await page.getByRole('button',{name:/Préférences/}).click();
    await page.locator('input[name=max_minutes]').fill('600');
    await page.locator('input[name=calories_max]').fill('200');
    await page.getByRole('button',{name:'Enregistrer les préférences'}).click();
    await page.getByRole('button',{name:/Scanner/}).click();
    await page.locator('input[type=file]').setInputFiles(process.argv[2]);
    const scanResponse=page.waitForResponse(r=>r.url().endsWith('/api/v1/scans'),{timeout:60000});
    await page.getByRole('button',{name:/Analyser la photo/}).click();
    const scan=await (await scanResponse).json();
    assert.ok(scan.candidates.length);
    assert.ok(scan.candidates.every(c=>c.quantity.amount===null));
    await page.locator('.ingredient-name').first().fill('flour');
    await page.locator('.quantity-input').first().fill('500');
    await page.locator('.unit-select').first().selectOption('g');
    // Exercise adding/removing one candidate before adding actual pantry labels.
    const add=async name=>{await page.getByPlaceholder('Un ingrédient oublié ? Ajoutez-le ici').fill(name);await page.getByRole('button',{name:/Ajouter$/,exact:false}).click()};
    await add('incorrect detection');
    await page.locator('.candidate-row').last().locator('input[type=checkbox]').first().uncheck();
    for(const name of ['salt','dry mustard','garlic powder','oil']) await add(name);
    const searchEvent=page.waitForRequest(r=>r.url().endsWith('/recipes/search'));
    await page.getByRole('button',{name:/Confirmer et trouver/}).click();
    const searchRequest=await searchEvent;
    assert.equal(searchRequest.postDataJSON().preferences.max_minutes,600);
    assert.equal(searchRequest.postDataJSON().preferences.nutrition_limits.calories.max,200);
    await page.locator('.recipe-card').first().waitFor({timeout:30000});
    const saved=await (await context.request.get(base+'/api/v1/pantry')).json();
    assert.ok(saved.items.some(i=>i.ingredient_id==='ing_flour'&&i.quantity.amount===500));
    assert.ok(!saved.items.some(i=>i.name==='incorrect detection'));
    const filtered=await context.request.post(base+'/api/v1/recipes/search',{data:{ingredients:saved.items,preferences:{max_minutes:30}}});
    assert.equal(filtered.status(),200);
    assert.ok((await filtered.json()).results.every(r=>r.recipe.preparation_minutes<=30));
    await page.getByRole('heading',{name:'chicken lickin  good  pork chops'}).click();
    await page.getByRole('button',{name:/Comparer les magasins/}).click();
    await page.getByRole('button',{name:/Continuer vers/}).waitFor({timeout:60000});
    // Wait for actual offers or a visible error; neither is mocked.
    await page.waitForFunction(()=>document.querySelector('.store-card')||document.querySelector('.unpriced-note'),{timeout:60000});
    await page.screenshot({path:'/tmp/refood-stores.png',fullPage:true});
    await page.getByRole('button',{name:/Continuer vers/}).click();
    const downloadEvent=page.waitForEvent('download');
    await page.getByRole('button',{name:/Télécharger la liste/}).click();
    const download=await downloadEvent;
    await download.saveAs('/tmp/refood-shopping-list.txt');
    const list=fs.readFileSync('/tmp/refood-shopping-list.txt','utf8');
    assert.ok(list.includes('REFOOD'));
    assert.deepEqual(failures,[]);
    console.log(JSON.stringify({scan_candidates:scan.candidates,confirmed:saved.items,shopping_list:list,failures},null,2));
  } finally {
    const restored=await context.request.put(base+'/api/v1/pantry',{data:snapshot});
    console.log('Pantry restore HTTP',restored.status());
    await browser.close();
  }
})().catch(e=>{console.error(e.message);process.exitCode=1});
