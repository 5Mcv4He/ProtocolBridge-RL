"""Real DeepSeek Harness session, bounded capability tools dispatched by host.
No shell or unrestricted filesystem tool is exposed to the solver.
"""
import argparse,hashlib,json,os,re,time
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch
from .reset import reset,ROOT
from .test import test
from .submit import submit

def parse_action(text):
    """Accept the first valid capability object, even with prose/code fences.
    Never execute remaining objects implicitly; disclose this in tool feedback.
    """
    decoder=json.JSONDecoder()
    for match in re.finditer(r'\{',text):
        try: action,end=decoder.raw_decode(text[match.start():])
        except ValueError: continue
        if isinstance(action,dict) and action.get('tool') in ('read','edit','test','submit'):
            return action
    raise ValueError('Invalid response format: no tool was executed. Return one JSON object with tool read, edit, test, or submit. This is not a file-access error.')

def freeze():
    files=[p for d in ('tasks','verifier','environment','fixtures') for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in str(p)]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}

def run(out,model='deepseek-flash'):
    from deepseek_harness import DeepSeekHarness
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);work=out/'solve';reset(work)
    frozen=freeze();(out/'freeze.json').write_text(json.dumps(frozen,indent=2))
    settings=out/'harness.json'
    settings.write_text(json.dumps([{'id':x,'disabled':True} for x in ('persistent-bash','persistent-pwsh','tool-fs','tool-working-directory','llm-retry')]+[{'id':'session-log-deepseek','config':{'enabled':False}}]))
    prompt='''You are an RTL implementation agent. Implement the task using only these host-dispatched tools.
Return exactly one JSON object per turn, without markdown: {"tool":"read","file":"spec.md"},
{"tool":"read","file":"bridge.sv"}, {"tool":"edit","content":"complete RTL"},
{"tool":"test"}, or {"tool":"submit"}. Read both files first; implement RTL, run the public test, iterate if needed, then submit. Never request hidden tests or reference.
There are at most 14 turns. Tool feedback follows each action. No internal reasoning is requested.'''
    last_public=None
    trace=[];result={'reward':None,'category':'agent_incomplete'}
    key=os.environ['DEEPSEEK_API_KEY']
    env={'PATH':os.environ['PATH'],'LANG':'en_US.UTF-8','DEEPSEEK_API_KEY':key}
    with patch.dict(os.environ,env,clear=True):
      with DeepSeekHarness(cwd=str(work),dsh_home=str(out/'dsh'),profile='sdk-minimal',provider='deepseek-official',model=model,reasoning_effort='off',max_tokens=6000,patches=(str(settings),),request_timeout_seconds=150) as harness:
        session=harness.start_session()
        for i in range(14):
          response=session.run(prompt)
          # Preserve externally visible events locally; never export credentials.
          raw=json.dumps(asdict(response),ensure_ascii=False)
          if key in raw: raw=raw.replace(key,'[REDACTED]')
          (out/f'harness-{i:02d}.json').write_text(raw)
          text=response.final_response.strip()
          try:
            action=parse_action(text);tool=action['tool']
            if tool=='read' and action.get('file') in ('spec.md','bridge.sv'):
              feedback=(work/action['file']).read_text()
            elif tool=='edit':
              code=action['content']
              if len(code)>40000: raise ValueError('RTL size limit')
              (work/'bridge.sv').write_text(code);(out/f'candidate-{i:02d}.sv').write_text(code);feedback='bridge.sv written'
            elif tool=='test':
              public_dir=out/f'public-{i:02d}'
              feedback=test(work,public_dir)
              last_public=public_dir if (public_dir/'backend.json').exists() else None
            elif tool=='submit':
              if frozen!=freeze(): raise RuntimeError('frozen evaluator changed')
              reuse=last_public
              if reuse and json.loads((reuse/'backend.json').read_text())['inputs']['candidate']!=hashlib.sha256((work/'bridge.sv').read_bytes()).hexdigest():reuse=None
              result=submit(work,out/'submission',reuse_build=reuse);feedback='Submission accepted; final results are not exposed during solving.'
            else: feedback='Unknown tool or file'
          except (ValueError,KeyError) as e: action={'invalid':text};feedback=str(e)
          trace.append({'turn':i,'action':action,'feedback':feedback})
          (out/'trace.json').write_text(json.dumps(trace,indent=2))
          print(json.dumps({'turn':i,'tool':action.get('tool'),'feedback':feedback if action.get('tool')!='read' else 'file returned'}),flush=True)
          if action.get('tool')=='submit': break
          prompt=json.dumps({'tool_result':feedback,'protocol_note':'Only the first valid tool object in your response was executed. Other objects were not executed. Send one JSON tool object next.'})
    result.update(model=model,harness='DeepSeek Harness',turns=len(trace),freeze_unchanged=frozen==freeze())
    (out/'result.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('--model',default='deepseek-flash');a=p.parse_args()
    try: result=run(a.out,a.model)
    except FileExistsError:
        raise
    except Exception as error:
        result={'reward':None,'category':'infrastructure_error','stage':'agent_harness','error_type':type(error).__name__,'model':a.model}
        dest=Path(a.out)
        if dest.exists() and not (dest/'result.json').exists():(dest/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
