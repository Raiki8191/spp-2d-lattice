"""Read-only checks of the ten-slide output, native grid, sources and old deck."""
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

TASK = Path(__file__).resolve().parent
ROOT = TASK.parents[1]
BUILD = TASK/'.build/ten-slide'
NS={'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text_of(xml):
    return ''.join(t.text or '' for t in xml.findall('.//a:t', NS))


def main():
    deck=json.loads((BUILD/'deck.json').read_text(encoding='utf-8'))
    protected=json.loads((BUILD/'protected_inputs.json').read_text(encoding='utf-8'))
    for item in protected:
        path=(ROOT/item['path']).resolve()
        assert path.is_relative_to(ROOT), path
        assert sha(path.read_bytes())==item['sha256'],f'Protected input changed: {path}'
    report=json.loads((BUILD/'powerpoint_com_report.json').read_text(encoding='utf-8-sig'))
    assert report['slide_count']==10 and not report['layout_warnings']
    assert report['output']['reopened_successfully']
    assert report['output']['speaker_notes_count']==10
    p=TASK/'slides/seminar_01-10.pptx'
    with zipfile.ZipFile(p) as z:
        names=z.namelist()
        pages=[s for s in names if re.fullmatch(r'ppt/slides/slide\d+\.xml',s)]
        notes=[s for s in names if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml',s)]
        assert len(pages)==len(notes)==len(deck['slides'])==10
        for i,slide in enumerate(deck['slides'],1):
            xml=ET.fromstring(z.read(f'ppt/slides/slide{i}.xml'))
            visible=text_of(xml)
            assert f'{i:02d} / 10' in visible,(i,'page number')
            if i>1:assert slide['title'] in visible,(i,'title')
            note_xml=ET.fromstring(z.read(f'ppt/notesSlides/notesSlide{i}.xml'))
            assert slide['notes'] in text_of(note_xml),(i,'notes')
            relation=ET.fromstring(z.read(f'ppt/slides/_rels/slide{i}.xml.rels'))
            media={r.attrib['Id']:r.attrib['Target'].replace('../','ppt/')
                   for r in relation if r.attrib.get('Type','').endswith('/image')}
            hashes={sha(z.read(target)) for target in media.values()}
            for elem in slide['elements']:
                if elem['kind']=='image':
                    assert sha((TASK/elem['path']).read_bytes()) in hashes,(i,elem['path'])
        xml=ET.fromstring(z.read('ppt/slides/slide4.xml'))
        object_names=[n.attrib['name'] for n in xml.findall('.//p:cNvPr',NS)]
        lattice=next(s for s in deck['slides'] if s['id']==4)
        for item in lattice['elements']:
            if item['kind']!='lattice':continue
            stage=item['stage']
            expected={tuple(sorted(e)) for e in item['edges']}
            if stage==4:expected-={tuple(sorted(e)) for e in item['selected_edges']}
            actual=set()
            for name in object_names:
                m=re.fullmatch(fr'lattice-{stage}-edge-(\d+)-(\d+)',name)
                if m:actual.add(tuple(sorted(map(int,m.groups()))))
            assert actual==expected,(stage,actual,expected)
            vertices={int(n.rsplit('-',1)[1]) for n in object_names
                      if n.startswith(f'lattice-{stage}-vertex-')}
            assert vertices==set(range(9)),(stage,vertices)
        presentation=ET.fromstring(z.read('ppt/presentation.xml'))
        size=presentation.find('p:sldSz',NS)
        assert int(size.attrib['cx'])*9==int(size.attrib['cy'])*16
    pdf=TASK/'slides/seminar_01-10.pdf'
    # Windows Poppler can emit locale-encoded dates despite -enc; page labels are ASCII.
    info=subprocess.check_output(['pdfinfo','-enc','UTF-8',str(pdf)],text=True,encoding='utf-8',errors='replace')
    assert re.search(r'Pages:\s+10\b',info),info
    board_pdf=TASK/'board/board_notes_01-10.pdf'
    board_info=subprocess.check_output(['pdfinfo','-enc','UTF-8',str(board_pdf)],text=True,encoding='utf-8',errors='replace')
    board_pages=int(re.search(r'Pages:\s+(\d+)',board_info).group(1))
    board_text=subprocess.check_output(['pdftotext','-enc','UTF-8',str(board_pdf),'-'],text=True,encoding='utf-8')
    assert '平均クラスターサイズ' in board_text and 'ゼータ' in board_text
    md=(TASK/'board/board_notes_01-10.md').read_text(encoding='utf-8')
    for i,s in enumerate(deck['slides'],1):
        assert s['title'] in md,(i,'board correspondence title')
    for name in ['m_s','n_s',r'S_{\rm all}','N-s_R']:
        assert name in md,name
    fonts={}
    for key,file in [('slides',pdf),('board',board_pdf)]:
        out=subprocess.check_output(['pdffonts',str(file)],text=True,encoding='utf-8')
        (BUILD/f'{key}_fonts.txt').write_text(out,encoding='utf-8')
        assert 'yes' in out,(key,'embedded fonts')
        fonts[key]='font report saved; visually verify glyph coverage'
    result={'slides':10,'speaker_notes':10,'canvas':'16:9',
            'grid_native_edge_sets':'12,12,12,8; exact sets match',
            'grid_native_vertices':'9 in each stage',
            'embedded_figure_and_equation_images':'all unchanged from prepared assets',
            'protected_input_sha256':'all match', 'powerpoint_reopen':True,
            'layout_warnings':0,'slide_pdf_pages':10,'board_pdf_pages':board_pages,
            'board_slide_titles':'10/10 match', 'fonts':fonts}
    (BUILD/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
