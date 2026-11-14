import test from 'node:test';
import assert from 'node:assert/strict';
import { flaskApi, api, isDemoMode } from './flaskApi.js';
import { resolveDemoMode } from './apiMode.js';
import { mockApi } from './mockApi.js';
import { basketSummary } from '../../features/stores/basket.js';
import { buildSync } from 'esbuild';
import { createRequire } from 'node:module';
const needs = [{ ingredient_id: 'ing_milk', name: 'milk' }, { ingredient_id: 'ing_egg', name: 'egg' }];
const reply = (body, source = 'catalog') => ({ ok: true, json: async () => body, headers: new Headers({ 'X-Refood-Source': source }) });
test('Flask default ignores old storage flags and offers explicit demo/live overrides', () => {
  globalThis.localStorage = { getItem: () => 'true' };
  assert.equal(isDemoMode, false); assert.equal(api, flaskApi);
  assert.equal(resolveDemoMode('', false), false);
  assert.equal(resolveDemoMode('?api_mode=demo', false), true);
  assert.equal(resolveDemoMode('?api_mode=live', true), false);
  delete globalThis.localStorage;
});
test('missing real recipe never returns samples; successful recipes stay cached', async () => {
  await assert.rejects(flaskApi.getRecipe('recipe_omelette'), /absente/);
  const original = globalThis.fetch;
  globalThis.fetch = async () => reply({ results: [{ recipe: { recipe_id: 'real_1', title: 'Imported', ingredients: [] }, match_score: 1, missing_ingredients: [] }] });
  try { await flaskApi.searchRecipes([]); assert.equal((await flaskApi.getRecipe('real_1')).title, 'Imported'); }
  finally { globalThis.fetch = original; }
});
test('failed real scan and grocery lookup never fabricate candidates or prices', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => { throw new Error('offline'); };
    await assert.rejects(flaskApi.scanImage(new Blob(['image'])), /serveur Flask/);
    await assert.rejects(flaskApi.groceryPrices(needs), /serveur Flask/);
    globalThis.fetch = async () => ({ ok: false, status: 503, json: async () => ({ error: { message: 'unavailable' } }) });
    await assert.rejects(flaskApi.scanImage(new Blob(['image'])), /503/);
    await assert.rejects(flaskApi.groceryPrices(needs), /503/);
  } finally { globalThis.fetch = original; }
});
test('successful HTTP responses containing internal fixtures are rejected', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => reply({ candidates: [] }, 'mock');
    await assert.rejects(flaskApi.scanImage(new Blob(['image'])), /démonstration/);
    globalThis.fetch = async () => reply({ results: [], source: 'mock' }, 'epiceries.ca');
    await assert.rejects(flaskApi.groceryPrices(needs), /démonstration/);
    globalThis.fetch = async () => reply({ results: [{ recipe: { recipe_id: 'sample', source: 'demo', ingredients: [] }, missing_ingredients: [] }] });
    await assert.rejects(flaskApi.searchRecipes([]), /démonstration/);
  } finally { globalThis.fetch = original; }
});
test('personal library excludes samples and favorites retain local provenance', async () => {
  assert.equal((await mockApi.listRecipes()).items.length, 0);
  const personal = await mockApi.createRecipe({ title: 'Mine', ingredients: [] });
  await mockApi.favoriteRecipe(personal.id, personal);
  const favorite = (await mockApi.getFavorites()).items.find((item) => item.id === personal.id);
  assert.equal(favorite.data_source, 'local'); assert.equal(favorite.persistence, 'browser');
  assert.equal((await mockApi.getLocalRecipe(personal.id)).data_source, 'local');
  await assert.rejects(flaskApi.getRecipe(personal.id), /absente/);
});
test('basket totals count distinct required verified products only', () => {
  const basket = basketSummary(needs, [
    { ingredient_id: 'ing_milk', price_cad: 2, relevance_verified: true },
    { ingredient_id: 'ing_milk', price_cad: 3, relevance_verified: true },
    { ingredient_id: 'ing_egg', price_cad: null, relevance_verified: true },
    { ingredient_id: 'ing_egg', price_cad: 0.01, relevance_verified: false },
    { ingredient_id: 'other', price_cad: 1, relevance_verified: true },
  ]);
  assert.equal(basket.total, 2); assert.equal(basket.covered, 1); assert.equal(basket.complete, false);
  assert.deepEqual(basket.missing, [needs[1]]);
});
test('demo warning, local labels and incomplete basket are visible in rendered UI', () => {
  const { outputFiles } = buildSync({ stdin: { contents: `
    import React from 'react'; import { renderToStaticMarkup } from 'react-dom/server';
    import { ApiModeControl } from './src/components/ApiModeControl.jsx';
    import { DataSource } from './src/components/DataSource.jsx';
    import { StoreCard } from './src/features/stores/StoreCard.jsx';
    export const mode = renderToStaticMarkup(<ApiModeControl />);
    export const local = renderToStaticMarkup(<DataSource source="local" />);
    export const basket = renderToStaticMarkup(<StoreCard merchant={{id:'one',name:'One'}} required={[{ingredient_id:'ing_egg',name:'egg'}]} offers={[]} />);
  `, resolveDir: process.cwd(), loader: 'jsx' }, bundle: true, write: false, platform: 'node', format: 'cjs', jsx: 'automatic', define: { 'import.meta.env.VITE_REFOOD_DEMO': '"true"' } });
  const module = { exports: {} };
  new Function('require', 'module', 'exports', outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
  assert.match(module.exports.mode, /Demo · Sample data/); assert.match(module.exports.mode, /role="alert"/);
  assert.match(module.exports.mode, /Retour au mode réel/); assert.match(module.exports.local, /Local · Browser storage/);
  assert.match(module.exports.basket, /Panier incomplet/); assert.match(module.exports.basket, /non comparable/);
  assert.match(module.exports.basket, /0\/1 ingrédients/); assert.match(module.exports.basket, /Sans prix dans ce magasin :.*Œuf/);
});
