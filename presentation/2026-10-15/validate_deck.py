"""Validate the finished seminar, source protection and numerical provenance."""
from pathlib import Path
import csv, hashlib, json, math, statistics, subprocess, zipfile, sys
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BUILD=HERE/'.build'
def source(rel):
    p=(ROOT/rel).resolve()
    if not p.is_relative_to(ROOT): raise ValueError('Outside repository')
    return p
def rows(rel):
    with source(rel).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def command(args):return subprocess.run(args,check=True,capture_output=True,text=True,encoding='utf-8',errors='replace').stdout

deck=json.loads((BUILD/'deck.json').read_text(encoding='utf-8'))
result={'source_protection':{},'data_checks':{},'pptx':{},'pdf':{}}
for r in json.loads((HERE/'data'/'source_inventory.json').read_text(encoding='utf-8-sig')):
    p=HERE/'sources_local'/r['source']
    ok=hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
    result['source_protection'][r['source']]=ok
    assert ok,f'Source modified: {p}'
for rel,digest in json.loads((HERE/'data'/'provenance.json').read_text()).items():
    assert hashlib.sha256(source(rel).read_bytes()).hexdigest()==digest

runs=rows('analysis/presentation_spp_comparison_ja_v2/data/event_runs.csv')
summaries=rows('analysis/presentation_spp_comparison_ja_v2/data/event_summary.csv')
groups={}
for r in runs:groups.setdefault(r['condition_id'],[]).append(float(r['delta_P_max']))
for s in summaries:
    v=groups[s['condition_id']]
    assert len(v)==int(s['n_runs'])
    assert math.isclose(statistics.mean(v),float(s['delta_P_max_mean']),abs_tol=1e-13)
    assert math.isclose(statistics.stdev(v)/math.sqrt(len(v)),float(s['delta_P_max_sem']),abs_tol=1e-13)
result['data_checks'].update(runs=len(runs),conditions=len(summaries),maximum_jump_mean_sem='all match')
g=rows('analysis/presentation_spp_comparison_ja_v2/data/request_guarantees.csv')
unbounded=[r for r in g if r['label']=='UNBOUNDED']
for r in unbounded:
    observed=int(r['delta_largest_cluster_size'])
    bound=max(0,int(r['final_largest_cluster_size'])-1)
    assert int(r['future_integer_jump_bound'])==bound
    assert (observed>=bound)==(r['guaranteed_full_process_maximum']=='True')
assert len(unbounded)==2550 and all(r['guaranteed_full_process_maximum']=='True' for r in unbounded)
t=rows('analysis/presentation_spp_comparison_ja_v2/data/tail_guarantees.csv')
for r in t:
    upper=float(r['mean_smax_at_common_end'])
    assert math.isclose(upper,int(r['N'])*float(r['mean_P_at_common_end']),abs_tol=1e-8)
    assert math.isclose(upper,float(r['future_mean_S_upper_bound']),abs_tol=1e-8)
    assert (float(r['observed_peak_mean_S'])>upper)==(r['guaranteed_full_process_S_peak']=='True')
assert sum(r['guaranteed_full_process_S_peak']=='True' for r in t)==21
assert all(r['guaranteed_full_process_S_peak']=='True' for r in t if int(r['L'])==128)
result['data_checks'].update(unbounded_full_max_certified=2550,mean_S_full_peak_certified='21/34',L128_S_peaks_certified='3/3')
if '--data-only' in sys.argv:
    (BUILD/'data_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0)

ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main','c':'http://schemas.openxmlformats.org/drawingml/2006/chart'}
pptx=HERE/'slides'/'seminar.pptx'
with zipfile.ZipFile(pptx) as z:
    slide_names=[f'ppt/slides/slide{i}.xml' for i in range(1,36)]
    for i,name in enumerate(slide_names):
        doc=ET.fromstring(z.read(name))
        text=''.join(doc.itertext())
        for line in deck['slides'][i]['title'].splitlines():assert line in text,(i+1,line)
        notes=ET.fromstring(z.read(f'ppt/notesSlides/notesSlide{i+1}.xml'))
        assert '【根拠】' in ''.join(notes.itertext())
    chart_names=sorted([n for n in z.namelist() if n.startswith('ppt/charts/chart') and n.endswith('.xml')])
    assert len(chart_names)==4,len(chart_names)
    # Every native chart's cached X/Y values agree with the intended actual series.
    chart_keys=['concept','P128','jump','S128']
    for name,key in zip(chart_names,chart_keys):
        doc=ET.fromstring(z.read(name))
        actual=doc.findall('.//c:scatterChart/c:ser',ns)
        expected=deck['charts'][key]['series']
        for a,e in zip(actual,expected):
            for tag,dim in [('xVal','x'),('yVal','y')]:
                values=[float(p.find('c:v',ns).text) for p in a.findall(f'c:{tag}//c:pt',ns)]
                assert len(values)==len(e[dim]),(key,dim,len(values),len(e[dim]))
                assert all(math.isclose(x,y,abs_tol=1e-10,rel_tol=1e-10) for x,y in zip(values,e[dim]))
        if key=='jump':
            err=actual[0].find('c:errBars',ns);assert err is not None
            for side in ['plus','minus']:
                values=[float(p.find('c:v',ns).text) for p in err.findall(f'c:{side}//c:pt',ns)]
                assert len(values)==16
                assert all(math.isclose(x,y,abs_tol=1e-12) for x,y in zip(values,expected[0]['sem']))
            assert doc.find('.//c:logBase',ns) is not None
    result['pptx'].update(slides=35,notes=35,editable_native_charts=4,chart_data='all cached values match',custom_sem_errorbars=16,
        embedded_workbooks=len([n for n in z.namelist() if n.startswith('ppt/embeddings/')]))
info=command(['pdfinfo',str(HERE/'slides'/'seminar.pdf')])
assert 'Pages:           35' in info,info
fonts=command(['pdffonts',str(HERE/'slides'/'seminar.pdf')])
(BUILD/'pdf_fonts.txt').write_text(fonts,encoding='utf-8')
text=command(['pdftotext','-layout',str(HERE/'slides'/'seminar.pdf'),'-'])
assert text.count('\f')==35
assert '質疑' in text and 'B10' in text
result['pdf'].update(pages=35,readable=True,font_report='.build/pdf_fonts.txt')
report=json.loads((BUILD/'powerpoint_com_report.json').read_text(encoding='utf-8-sig'))
assert report['output']['reopened_successfully']
result['pptx']['layout_warnings']=report['layout_warnings']
(BUILD/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
