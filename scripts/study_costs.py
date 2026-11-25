"""Descriptive resource totals; list-price range is not an API invoice."""
import argparse,json
from pathlib import Path

FIELDS=('inputTokens','outputTokens','cacheReadTokens','cacheWriteTokens','totalTokens')

def summarize(roots):
    cohorts=[]
    for name in roots:
        root=Path(name);a=json.loads((root/'batch-analysis.json').read_text());rs=a['rows']
        model=json.loads((root/'experiment.json').read_text()).get('model')
        observed=sum(all(isinstance((r.get('tokens') or {}).get(k),(int,float)) for k in FIELDS) for r in rs)
        tokens={k:sum((r.get('tokens') or {}).get(k,0) or 0 for r in rs) for k in FIELDS}
        # Retrieved 2026-11-25 from the official pricing page. Actual request
        # billing periods/discounts are unavailable; never infer invoice totals.
        low=(tokens['inputTokens']*.15+tokens['outputTokens']*.6+tokens['cacheReadTokens']*.003)/1e6
        cohorts.append({'cohort':root.name,'model':model,'started':len(rs),'tokens':tokens,'token_observed_trials':observed,
          'seconds':{k:sum(r.get(k) or 0 for r in rs) for k in ('wall_seconds','model_request_wall_seconds','compile_wall_seconds','simulation_wall_seconds')},
          'list_price_usd_range':[low,low*2] if model=='deepseek-flash' and observed==len(rs) and not tokens['cacheWriteTokens'] else None,
          'actual_billed_usd':None})
    return {'cohorts':cohorts,'actual_billed_usd':None,
      'pricing_source':'https://api-docs.deepseek.com/quick_start/pricing/',
      'pricing_retrieved':'2026-11-25','pricing_model_alias':'deepseek-flash',
      'scope':'SDK-reported uncached input, cached input and output; list-price range only, not invoice or balance delta. Model request time includes API/SDK/network. EDA times include post-submit measurement; summed episode time excludes gaps between trials.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('roots',nargs='+');p.add_argument('--out');a=p.parse_args();r=summarize(a.roots);s=json.dumps(r,indent=2)+'\n'
    if a.out:Path(a.out).write_text(s)
    print(s)
