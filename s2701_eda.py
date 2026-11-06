"""ACS S2701 EDA. Run in the extracted package folder with pandas and matplotlib.
No survey estimates are bundled. Supply official flat CSV/ZIP exports or set
CENSUS_API_KEY privately in the notebook environment. Never commit the key.
"""
from pathlib import Path
from datetime import datetime, timezone
import os, re, io, json, zipfile, urllib.request, urllib.parse
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
OUT = ROOT / 'results'
STATES = {'10':'Delaware','11':'District of Columbia','24':'Maryland',
          '42':'Pennsylvania','51':'Virginia'}
PERIODS = {2019:'2015–2019',2024:'2020–2024'}
ROWS = {'001':'All ages','011':'Under 19 years','012':'19 to 64 years',
        '013':'65 years and older','014':'Male','015':'Female'}
COLS = {'C01':'population','C02':'insured_count','C03':'insured_pct',
        'C04':'uninsured_count','C05':'uninsured_pct'}
class DataNotReady(RuntimeError): pass

def read_exports(year):
    """Accept Census flat downloads, including ZIPs; never extract archive paths."""
    frames=[]
    for f in sorted(DATA.rglob('*')):
        if not f.is_file(): continue
        if f.suffix.lower()!='.zip' and str(year) not in f.name: continue
        if f.suffix.lower()=='.csv' and ('data' in f.stem.lower()):
            candidates=[(str(f.relative_to(ROOT)),f.read_bytes())]
        elif f.suffix.lower()=='.zip':
            with zipfile.ZipFile(f) as z:
                candidates=[(f'{f.name}:{n}',z.read(n)) for n in z.namelist()
                            if str(year) in n and n.lower().endswith('-data.csv')]
        else: continue
        for name,raw in candidates:
            frame=pd.read_csv(io.BytesIO(raw),dtype=str,keep_default_na=False,
                              encoding='utf-8-sig')
            if 'S2701_C05_001E' not in frame.columns: continue
            if 'GEO_ID' not in frame.columns: continue
            frame=frame[frame.GEO_ID.str.fullmatch(r'0400000US\d{2}')].copy()
            frame['state']=frame.GEO_ID.str[-2:]
            frame=frame[frame.state.isin(STATES)]
            frame['source_file']=name
            frames.append(frame)
    if not frames:return None
    frame=pd.concat(frames,ignore_index=True)
    # Identical repeated exports can be collapsed. Conflicting values must stop.
    keys=[c for c in frame if re.fullmatch(r'S2701_C\d{2}_\d{3}(E|M|EA|MA)',c)]
    frame=frame.drop_duplicates(subset=['state']+keys)
    if frame.state.duplicated().any():
        raise ValueError(f'Conflicting duplicate exports for {year}; retain one source per state.')
    return frame

def fetch_api(year,key):
    params={'get':'NAME,group(S2701)','for':'state:'+','.join(STATES),'key':key}
    url=f'https://api.census.gov/data/{year}/acs/acs5/subject?'+urllib.parse.urlencode(params)
    try:
        raw=urllib.request.urlopen(url,timeout=60).read()
        body=json.loads(raw)
    except Exception:
        # Do not echo request URLs, which contain the private key.
        raise DataNotReady('Census request failed. Check the active API key or use flat CSV/ZIP downloads.') from None
    if not isinstance(body,list) or len(body)<2:
        raise DataNotReady('Census did not return a data table.')
    frame=pd.DataFrame(body[1:],columns=body[0])
    frame['source_file']=f'Census API {year} ACS five-year subject S2701'
    # Save data only; request URL and key are deliberately excluded.
    frame.to_csv(DATA/f'ACSST5Y{year}.S2701-Data.csv',index=False)
    return frame

def numeric(value):
    """Preserve sentinels as missing; never replace unavailable values with zero."""
    if value is None:return np.nan
    text=str(value).strip().replace(',','').replace('%','').replace('±','')
    try: value=float(text)
    except ValueError:return np.nan
    return value if np.isfinite(value) and value>=0 else np.nan

def prepare():
    DATA.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
    tidy=[]; manifest=[]
    for year in PERIODS:
        frame=read_exports(year)
        if frame is None:
            key=os.environ.get('CENSUS_API_KEY','').strip()
            if not key:
                raise DataNotReady(f'Actual {year} estimates are not loaded. Put the official ACSST5Y{year}.S2701 flat CSV/ZIP in data/, or set CENSUS_API_KEY privately.')
            frame=fetch_api(year,key)
        if set(frame.state)!=set(STATES) or frame.state.duplicated().any():
            raise ValueError(f'{year}: expected exactly DE, DC, MD, PA, VA once each; got {frame.state.tolist()}.')
        for _,r in frame.iterrows():
            for row,group in ROWS.items():
                item={'vintage':year,'period':PERIODS[year],'state_fips':r.state,
                      'geography':STATES[r.state],'group':group,'source':r.source_file}
                for col,measure in COLS.items():
                    base=f'S2701_{col}_{row}'
                    for suffix,name in [('E',measure),('M',measure+'_moe90')]:
                        if base+suffix not in frame.columns:
                            raise ValueError(f'Missing required column {base+suffix}. Use flat ZIP export.')
                        item[name]=numeric(r[base+suffix])
                        item[name+'_raw']=r[base+suffix]
                        annotation=base+suffix+'A'
                        item[name+'_annotation']=r.get(annotation,'') or ''
                tidy.append(item)
        manifest.append({'vintage':year,'period':PERIODS[year],
          'source_files':frame.source_file.unique().tolist(),'geographies':list(STATES.values()),
          'table':'S2701','product':'ACS 5-year estimates subject tables'})
    df=pd.DataFrame(tidy)
    assert len(df)==60 and not df.duplicated(['vintage','state_fips','group']).any()
    df.to_csv(OUT/'s2701_clean_selected.csv',index=False)
    (OUT/'provenance.json').write_text(json.dumps({'executed_utc':datetime.now(timezone.utc).isoformat(),
      'sources':manifest,'code':'s2701_eda.py','status':'calculated from supplied official estimates'},indent=2))
    return df

def analyze(df):
    measures=list(COLS.values())
    checks=[]
    for (year,group),g in df.groupby(['vintage','group']):
        checks.append({'vintage':year,'group':group,'records':len(g),
          'missing_estimate_cells':int(g[measures].isna().sum().sum()),
          'missing_moe_cells':int(g[[m+'_moe90' for m in measures]].isna().sum().sum()),
          'nonempty_annotation_cells':int(g.filter(regex='_annotation$').apply(lambda c:c.astype(str).str.len().gt(0)).sum().sum()),
          'percent_outside_0_100':int(((g[['insured_pct','uninsured_pct']]<0)|(g[['insured_pct','uninsured_pct']]>100)).sum().sum()),
          'composition_outside_rounding_tolerance':int(((g.insured_pct+g.uninsured_pct-100).abs()>.11).sum()),
          'count_identity_failures':int(((g.insured_count+g.uninsured_count-g.population).abs()>0).sum())})
    quality=pd.DataFrame(checks);quality.to_csv(OUT/'quality_checks.csv',index=False)
    if quality.percent_outside_0_100.sum() or quality.count_identity_failures.sum():
        raise ValueError('Data consistency check failed. Inspect quality_checks.csv before publishing.')
    total=df[df.group.eq('All ages')].copy()
    total['lower90']=total.uninsured_pct-total.uninsured_pct_moe90
    total['upper90']=total.uninsured_pct+total.uninsured_pct_moe90
    total.to_csv(OUT/'overall_estimates.csv',index=False)
    a=total[total.vintage.eq(2019)].set_index('geography')
    b=total[total.vintage.eq(2024)].set_index('geography')
    change=pd.DataFrame({'uninsured_pct_2015_2019':a.uninsured_pct,
      'uninsured_pct_2020_2024':b.uninsured_pct,
      'change_percentage_points':b.uninsured_pct-a.uninsured_pct})
    # Descriptive change only. No inferential or causal conclusions are made.
    change.to_csv(OUT/'descriptive_period_change.csv')
    summary=total.groupby('period').uninsured_pct.agg(['min','max','median','mean','std'])
    summary.to_csv(OUT/'jurisdiction_summary_unweighted.csv')
    # Mean is across five selected geographies, NOT a regional population rate.
    weighted=total.groupby('period').apply(lambda g:100*g.uninsured_count.sum(min_count=1)/g.population.sum(min_count=1) if g[['uninsured_count','population']].notna().all().all() else np.nan,include_groups=False)
    weighted.rename('pooled_uninsured_pct_from_counts').to_csv(OUT/'pooled_descriptive_rate.csv')
    return total,change,quality

def charts(df,total,change):
    if total[['uninsured_pct','uninsured_pct_moe90','insured_pct']].isna().any().any():
        raise DataNotReady('Overall estimates or margins of error are missing. Tables were saved; resolve annotations before charting.')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    current=total[total.vintage.eq(2024)].sort_values('uninsured_pct')
    names=current.geography.tolist(); vals=current.uninsured_pct.to_numpy(); moe=current.uninsured_pct_moe90.to_numpy()
    foot='Source: U.S. Census Bureau, ACS S2701. Civilian noninstitutionalized population.'
    def save(fig,name):
        fig.text(.02,.015,foot,fontsize=8)
        fig.savefig(OUT/name,dpi=180,bbox_inches='tight');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.7));ax.barh(names,vals,color='#23618c',xerr=moe,capsize=4)
    ax.set(xlabel='Uninsured population (%)',title='Uninsured shares across five jurisdictions\n2020–2024 ACS five-year estimates',xlim=(0,max(vals+moe)*1.2))
    for i,v in enumerate(vals):ax.text(v+moe[i]+.1,i,f'{v:.1f}%',va='center')
    ax.text(0,-.2,'Error bars show published 90% margins of error.',transform=ax.transAxes,fontsize=9)
    fig.tight_layout(rect=(0,.09,1,1));save(fig,'01_bar.png')
    fig,ax=plt.subplots(figsize=(9,4.7));ax.errorbar(vals,names,xerr=moe,fmt='o',color='#23618c',capsize=4)
    ax.set(xlabel='Uninsured population (%)',title='Dot plot makes sampling uncertainty visible\n2020–2024 ACS five-year estimates',xlim=(0,max(vals+moe)*1.2))
    fig.tight_layout(rect=(0,.08,1,1));save(fig,'02_dot_moe90.png')
    fig,ax=plt.subplots(figsize=(9,4.7));ax.hlines(names,0,vals,color='#6c8da5');ax.scatter(vals,names,color='#23618c',s=60)
    ax.set(xlabel='Uninsured population (%)',title='Lollipop chart for comparing uninsured shares\n2020–2024 ACS five-year estimates',xlim=(0,max(vals)*1.2))
    fig.tight_layout(rect=(0,.08,1,1));save(fig,'03_lollipop.png')
    fig,ax=plt.subplots(figsize=(9,4.7));ax.barh(names,current.insured_pct,color='#adbcc7',label='Insured');ax.barh(names,vals,left=current.insured_pct,color='#23618c',label='Uninsured')
    for i,(_,r) in enumerate(current.iterrows()):
        ax.text(r.insured_pct/2,i,f'{r.insured_pct:.1f}%',ha='center',va='center');ax.text(101,i,f'{r.uninsured_pct:.1f}%',ha='left',va='center',color='black',fontsize=9) if r.uninsured_pct<4 else ax.text(r.insured_pct+r.uninsured_pct/2,i,f'{r.uninsured_pct:.1f}%',ha='center',va='center',color='white',fontsize=9)
    ax.set(xlim=(0,100),xlabel='Share of population (%)',title='Insured and uninsured composition\n2020–2024 ACS five-year estimates');fig.legend(loc='lower center',bbox_to_anchor=(.6,.06),ncol=2)
    fig.tight_layout(rect=(0,.18,1,1));save(fig,'04_stacked100.png')
    fig,ax=plt.subplots(figsize=(9,5))
    colors=plt.get_cmap('tab10').colors
    for i,(name,r) in enumerate(change.iterrows()):
        ax.plot([0,1],[r.iloc[0],r.iloc[1]],marker='o',color=colors[i],label=f'{name} ({r.iloc[2]:+.1f} pp)')
    ax.set(xticks=[0,1],xticklabels=['2015–2019','2020–2024'],ylabel='Uninsured population (%)',title='Change between non-overlapping five-year periods\nDescriptive comparison; significance not tested',ylim=(0,float(change.iloc[:,:2].max().max())*1.2))
    ax.legend(bbox_to_anchor=(1.02,1),loc='upper left',fontsize=9);fig.tight_layout(rect=(0,.08,1,1));save(fig,'05_slope.png')
    age=df[(df.vintage.eq(2024))&df.group.isin(['Under 19 years','19 to 64 years','65 years and older'])]
    pivot=age.pivot(index='geography',columns='group',values='uninsured_pct')
    pivot.to_csv(OUT/'age_group_rates.csv')
    fig,ax=plt.subplots(figsize=(9,5));pivot[['Under 19 years','19 to 64 years','65 years and older']].plot.barh(ax=ax,color=['#adbcc7','#23618c','#c98732'])
    ax.set(xlabel='Uninsured population within age group (%)',title='Age groups provide an additional comparison example\n2020–2024 ACS five-year estimates');ax.legend(title='Age group',bbox_to_anchor=(1.02,1),loc='upper left')
    fig.tight_layout(rect=(0,.08,1,1));save(fig,'06_age_groups.png')

def run():
    df=prepare();total,change,quality=analyze(df);charts(df,total,change)
    print('Actual-data analysis completed. Results:',OUT)
    print(total[total.vintage.eq(2024)][['geography','population','uninsured_count','uninsured_pct','uninsured_pct_moe90']].to_string(index=False))
    print('\nDescriptive change in percentage points:\n',change.to_string())
    print('\nQuality checks:\n',quality.to_string(index=False))
    return df,total,change,quality

if __name__=='__main__':
    try:run()
    except DataNotReady as e:print('DATA REQUIRED:',e)
