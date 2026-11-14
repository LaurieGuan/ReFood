import test from 'node:test';
import assert from 'node:assert/strict';
import { confirmedItems } from './confirmation.js';
const item=(name,quantityText='')=>({approved:true,editedName:name,quantityText,unitChoice:'piece'});
test('renames, bilingual deduplication and discarded items',()=>{
  const result=confirmedItems([item('oeufs'),item('eggs'),{...item('milk'),approved:false},item('tomates','2')]);
  assert.deepEqual(result.map(x=>x.ingredient_id),['ing_egg','ing_tomato']);
  assert.equal(result[0].quantity,null);
  assert.equal(result[1].quantity,2);
});
test('conflicting duplicates and invalid quantities are rejected',()=>{
  assert.throws(()=>confirmedItems([item('egg','2'),item('oeufs','4')]));
  assert.throws(()=>confirmedItems([item('milk','Infinity')]));
});
