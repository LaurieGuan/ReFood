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
