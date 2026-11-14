import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyGroceryProduct } from './productRelevance.js';

const milk = { ingredient_id: 'ing_milk', name: 'milk' };

test('rejects unrelated category even when search result matches by token', () => {
  assert.equal(classifyGroceryProduct(milk, { name: 'Savon au lait', category_id: 70 }).eligible, false);
  assert.equal(classifyGroceryProduct(milk, { name: 'Bretzels au chocolat au lait', category_id: 64 }).eligible, false);
});

test('accepts real milk with dairy category', () => {
  const result = classifyGroceryProduct(milk, { name: 'Lait 2% 2L', category_id: 7 });
  assert.equal(result.eligible, true);
  assert.equal(result.score, 0.95);
});

test('rejects unrelated groceries and supports bilingual egg matching', () => {
  assert.equal(classifyGroceryProduct(milk, { name: 'Fromage cheddar', category_id: 11 }).eligible, false);
  assert.equal(classifyGroceryProduct({ ingredient_id: 'ing_egg', name: 'egg' }, { name: 'Oeufs gros', category_id: 9 }).eligible, true);
});

test('rejects unlabeled products and obvious personal-care categories', () => {
  assert.equal(classifyGroceryProduct(milk, { name: '', category_id: 7 }).eligible, false);
  assert.equal(classifyGroceryProduct({ ingredient_id: 'ing_rice', name: 'rice' }, { name: 'Riz nettoyant', category_id: 70 }).eligible, false);
});

test('does not price ambiguous matches or soap with missing taxonomy', () => {
  assert.equal(classifyGroceryProduct(milk, {name:'Milk soap',category_id:null}).eligible,false);
  assert.equal(classifyGroceryProduct(milk, {name:'Lait 2%',category_id:null}).verified,false);
  assert.equal(classifyGroceryProduct(milk, {name:'Lait chocolat',category_id:7}).eligible,false);
  assert.equal(classifyGroceryProduct({ingredient_id:'ing_chicken',name:'chicken'}, {name:'Dinde',category_id:16}).eligible,false);
});

test('real provider misleading milk labels do not count as regular milk', () => {
  assert.equal(classifyGroceryProduct(milk,{name:'Lait de coco',category_id:7}).eligible,false);
  assert.equal(classifyGroceryProduct(milk,{name:'Lait 1% Edition Limitée',category_id:7}).verified,false);
  assert.equal(classifyGroceryProduct(milk,{name:'Lait 1%',category_id:7,retailer_link:'https://example.test/lait-aromatise-a-la-peche-et-mangue-1'}).eligible,false);
});

test('plain-milk vocabulary leaves unknown flavors visibly unverified',()=>{
  assert.equal(classifyGroceryProduct(milk,{name:'Lait frappé aux fraises',category_id:7}).eligible,false);
  assert.equal(classifyGroceryProduct(milk,{name:'Lait aux bleuets',category_id:7}).verified,false);
  assert.equal(classifyGroceryProduct(milk,{name:'Lait partiellement écrémé 2% 2 L',category_id:7}).verified,true);
});
