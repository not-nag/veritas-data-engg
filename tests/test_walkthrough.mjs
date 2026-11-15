import test from 'node:test';
import assert from 'node:assert/strict';
import { readProgress, completeFromEvent, canContinue, processingEvent } from '../web/lib/walkthrough-state.mjs';

test('a write step stays locked until its matching success event',()=>{
 const step={id:'retry',event:'retry-succeeded'};
 assert.equal(canContinue(step,[]),false);
 assert.deepEqual(completeFromEvent([],step,'retry-failed'),[]);
 assert.deepEqual(completeFromEvent([],step,'button-clicked'),[]);
 assert.equal(canContinue(step,completeFromEvent([],step,'retry-succeeded')),true);
});
test('events do not credit unrelated steps or duplicate completed actions',()=>{
 const step={id:'review',event:'record-reviewed'};
 assert.deepEqual(completeFromEvent([],step,'samples-processed'),[]);
 assert.deepEqual(completeFromEvent(['review'],step,'record-reviewed'),['review']);
});
test('reading steps need an explicit Continue but no action event',()=>{
 assert.equal(canContinue({id:'coverage'},[]),true);
 assert.deepEqual(completeFromEvent([],{id:'coverage'},'record-reviewed'),[]);
});
test('invalid and obsolete saved progress is ignored',()=>{
 for(const raw of [null,'{','null','{}','{"version":0,"stepId":"samples","completed":[]}','{"version":1,"stepId":"removed","completed":[]}'])
   assert.equal(readProgress(raw,['samples']),null);
});
test('saved progress is restricted to known steps and contains no patient data',()=>{
 const raw=JSON.stringify({version:1,stepId:'retry',completed:['samples','samples','removed',12],patient:'private'});
 assert.deepEqual(readProgress(raw,['samples','retry']),{stepId:'retry',completed:['samples']});
});
test('resuming a pending step does not mark it completed',()=>{
 const saved=readProgress('{"version":1,"stepId":"retry","completed":["samples"]}',['samples','retry']);
 assert.equal(canContinue({id:saved.stepId,event:'retry-succeeded'},saved.completed),false);
});

test('empty, failed, and partial sample batches do not unlock the sample step',()=>{
 for(const result of [{processed:0,failed:0},{processed:0,failed:5},{processed:4,failed:1}])
  assert.equal(processingEvent({...result,upload:false,reprocess:false}),null);
 assert.equal(processingEvent({processed:5,failed:0,upload:false,reprocess:false}),'samples-processed');
 assert.equal(processingEvent({processed:0,failed:1,upload:true,reprocess:false}),'upload-failed');
 assert.equal(processingEvent({processed:1,failed:0,upload:true,reprocess:false}),'upload-succeeded');
});
