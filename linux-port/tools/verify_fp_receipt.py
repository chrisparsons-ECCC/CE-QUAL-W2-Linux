"""Integer-only check of actual experimental startup/end FP receipts."""
from pathlib import Path
import hashlib,json,re,sys

def verify(run):
 if sys.flags.optimize:raise ValueError('Python optimization disables required FP checks and is not allowed')
 run=Path(run);capture=json.loads((run/'capture.json').read_text());inv=json.loads((run/'invocation.json').read_text())
 action=int(inv['only_authorized_mask_action']);p=run/'invalid-mask-receipt.txt';lines=p.read_text().splitlines()
 assert lines and lines[0]==f'W2_INVALID_MASK_DIAGNOSTIC 1 candidate={action}'
 rows={};markers=[]
 for line in lines[1:]:
  if line in ('BEGIN_GUARD_PASS','END_PRE_CLOSE_GUARD_PASS'):markers.append(line);continue
  m=re.fullmatch(r'(BEGIN_ENTRY|BEGIN_BEFORE|BEGIN_AFTER|BEGIN_LOG_AFTER|END_BEFORE|END_LOG_AFTER) fcw=([0-9a-f]{4}) fsw=([0-9a-f]{4}) ftw=([0-9a-f]{2}) mxcsr=([0-9a-f]{8}) mxcsr_mask=([0-9a-f]{8}) raw32=([0-9a-f]{64})',line)
  assert m and m[1] not in rows,('unexpected receipt line',line)
  row=[int(v,16) for v in m.groups()[1:6]];raw=bytes.fromhex(m[7])
  assert row==[int.from_bytes(raw[0:2],'little'),int.from_bytes(raw[2:4],'little'),raw[4],int.from_bytes(raw[24:28],'little'),int.from_bytes(raw[28:32],'little')]
  rows[m[1]]=row
 assert list(rows)[:4]==['BEGIN_ENTRY','BEGIN_BEFORE','BEGIN_AFTER','BEGIN_LOG_AFTER']
 before=rows['BEGIN_BEFORE'];after=rows['BEGIN_AFTER']
 assert rows['BEGIN_ENTRY']==before and rows['BEGIN_LOG_AFTER']==after
 assert not(before[0]&1) and not(before[3]&128),'Unexpected originally masked invalid state'
 expected=list(before);expected[0]|=action;expected[3]|=action*128
 assert after==expected,'Unexpected control or status change at startup'
 assert 'BEGIN_GUARD_PASS' in markers
 returned='END_BEFORE' in rows or 'END_LOG_AFTER' in rows
 if capture['exit_code']==0:assert returned,'Zero model exit requires complete END evidence'
 if returned:
  assert list(rows)==['BEGIN_ENTRY','BEGIN_BEFORE','BEGIN_AFTER','BEGIN_LOG_AFTER','END_BEFORE','END_LOG_AFTER']
  assert markers==['BEGIN_GUARD_PASS','END_PRE_CLOSE_GUARD_PASS']
  end=rows['END_BEFORE'];assert rows['END_LOG_AFTER']==end
  assert end[0]==after[0] and (end[3]&~63)==(after[3]&~63) and end[4]==after[4]
 else:
  assert list(rows)==['BEGIN_ENTRY','BEGIN_BEFORE','BEGIN_AFTER','BEGIN_LOG_AFTER'] and markers==['BEGIN_GUARD_PASS']
 result={'FP_receipt_valid':True,'candidate':bool(action),'model_exit':capture['exit_code'],'end_record_present':returned,'normal_return_and_post_close_guard_confirmed_by_zero_exit':returned and capture['exit_code']==0,'receipt_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'field_order':['FCW','FSW','FTW','MXCSR','MXCSR_MASK'],'raw_words':{k:[f'{v:x}' for v in vals] for k,vals in rows.items()},'only_startup_control_delta':{'FCW_xor':f'{before[0]^after[0]:04x}','MXCSR_xor':f'{before[3]^after[3]:08x}'},'startup_status_preserved':True,'all_other_control_bits_preserved':True,'limits':'A valid entry or END receipt is not model/output acceptance. A nonzero native exit remains failed even when the END record is well formed. A zero native exit is required to confirm the final close/guard and normal completion.'}
 return result

if __name__=='__main__':
 r=verify(sys.argv[1]);text=json.dumps(r,indent=2)+'\n'
 if len(sys.argv)>2:Path(sys.argv[2]).write_text(text)
 else:print(text,end='')
