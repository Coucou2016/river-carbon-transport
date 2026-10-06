"""Render the reviewed Markdown once to HTML/PDF; no scientific calculations."""
from pathlib import Path
import re,html,base64,shutil,json,difflib,hashlib
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,KeepTogether,PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from PIL import Image as PILImage
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent; OUT=HERE/'修订稿'
MD=OUT/'paper_revised.md'; source=MD.read_text(encoding='utf-8')
fontroot=ROOT/'.venv/Lib/site-packages/matplotlib/mpl-data/fonts/ttf'
for name,file in [('Body','DejaVuSerif.ttf'),('Bold','DejaVuSerif-Bold.ttf'),('Sans','DejaVuSans.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(fontroot/file)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold',italic='Body',boldItalic='Bold')
W,H=A4; usable=W-84
styles={
 'p':ParagraphStyle('p',fontName='Body',fontSize=9.4,leading=14,spaceAfter=7),
 'cap':ParagraphStyle('cap',fontName='Body',fontSize=8.2,leading=11.5,spaceAfter=10),
 'td':ParagraphStyle('td',fontName='Sans',fontSize=7.2,leading=9.7),
 'quote':ParagraphStyle('quote',fontName='Body',fontSize=9,leading=13,leftIndent=10,rightIndent=10,spaceBefore=6,spaceAfter=10,backColor=colors.HexColor('#f3f5f7')),
}
for i,size in [(1,19),(2,13),(3,11)]:styles[f'h{i}']=ParagraphStyle(f'h{i}',fontName='Bold',fontSize=size,leading=size*1.3,spaceBefore=12,spaceAfter=8,keepWithNext=True)
def inline(s):
    s=html.escape(s.replace('待补充','pending'))
    return re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',s)
def para(s,kind='p'):return Paragraph(inline(s),styles[kind])
story=[]; web=[]; fig_hashes=[]; lines=source.splitlines(); i=0
while i<len(lines):
    s=lines[i].strip();i+=1
    if not s:continue
    if s.startswith('|'):
        rows=[s]
        while i<len(lines) and lines[i].strip().startswith('|'):rows.append(lines[i].strip());i+=1
        cells=[[x.strip().replace('\\|','|') for x in re.split(r'(?<!\\)\|',r)[1:-1]] for r in rows]
        cells=[r for r in cells if not all(re.fullmatch(r'[-: ]+',v) for v in r)]
        n=len(cells[0]);weights=[1]*n
        if n==8:weights=[.7,1.4,1.0,1.0,.8,.9,.65,1.9]
        elif n==9:weights=[2.2,1,1,1,1,1,1,1.1,.6]
        elif n==6:weights=[1.2,2.3,1.0,1,1,.6]
        elif n==5:weights=[2.3,1,1.1,1.0,1.2]
        elif n==2:weights=[1.3,3]
        elif n==3:weights=[1.2,2.5,3]
        widths=[usable*x/sum(weights) for x in weights]
        data=[[para(v,'td') for v in row] for row in cells]
        tab=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eef2')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#64748b')),('LINEBELOW',(0,-1),(-1,-1),.4,colors.HexColor('#94a3b8')),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        if story and isinstance(story[-1],Paragraph) and story[-1].text.startswith('<b>Table '):
            caption=story.pop(); caption.keepWithNext=False
            story.extend([KeepTogether([caption,tab]),Spacer(1,12)])
        else:
            story.extend([KeepTogether([tab]),Spacer(1,12)])
        web.append('<table>'+''.join('<tr>'+''.join(f'<{"th" if k==0 else "td"}>{inline(v)}</{"th" if k==0 else "td"}>' for v in row)+'</tr>' for k,row in enumerate(cells))+'</table>')
        continue
    match=re.fullmatch(r'!\[(.*)\]\(([^)]+)\)',s)
    if match:
        cap,path=match.groups(); p=ROOT/path; dest=OUT/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        im=PILImage.open(p); w,h=im.size; scale=min(usable/w,390/h);img=Image(str(p),width=w*scale,height=h*scale)
        story.append(KeepTogether([Spacer(1,8),img,Spacer(1,5),para(cap,'cap')]))
        web.append('<figure><img src="data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()+'"><figcaption>'+inline(cap)+'</figcaption></figure>')
        fig_hashes.append({'source':path,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()});continue
    if s.startswith('#'):
        level=len(s)-len(s.lstrip('#'));txt=s[level:].strip();kind=f'h{min(level,3)}'
        if txt in ('Tables','References'):story.append(PageBreak())
        story.append(para(txt,kind));web.append(f'<h{level}>{inline(txt)}</h{level}>');continue
    if s.startswith('> '):story.append(para(s[2:],'quote'));web.append('<blockquote>'+inline(s[2:])+'</blockquote>');continue
    if s.startswith('- '):story.append(para('• '+s[2:]));web.append('<p>• '+inline(s[2:])+'</p>');continue
    block=para(s)
    if s.startswith('**Table '): block.keepWithNext=True
    story.append(block);web.append('<p>'+inline(s)+'</p>')
css='body{max-width:1040px;margin:40px auto;padding:0 25px;font:17px/1.65 Georgia,serif;color:#17212b}h1{line-height:1.25}h2{margin-top:2em}table{border-collapse:collapse;width:100%;font:13px/1.45 Arial,sans-serif;margin:18px 0}td,th{border-bottom:1px solid #ccd5dd;padding:8px;text-align:left}th{background:#e8eef2}img{width:100%;height:auto}figure{margin:30px 0}figcaption{font-size:14px}blockquote{background:#f3f5f7;padding:14px}a{overflow-wrap:anywhere}'
(OUT/'paper_revised.html').write_text('<!doctype html><meta charset="utf-8"><title>East River — reviewed draft</title><style>'+css+'</style>'+''.join(web),encoding='utf-8')
def footer(c,doc):
    c.setFont('Sans',7);c.setFillColor(colors.HexColor('#64748b'));c.drawString(42,23,'Author-review draft | 27 September 2026 | methodological qualifications retained');c.drawRightString(W-42,23,str(doc.page))
pdf=OUT/'paper_revised_20260927.pdf'
SimpleDocTemplate(str(pdf),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=36,bottomMargin=37,title='East River conditional process-allocation diagnostics — author-review draft',author='Author information pending').build(story,onFirstPage=footer,onLaterPages=footer)
orig=(ROOT/'tmp/review_20260927/packet/paper.md').read_text(encoding='utf-8')
diff=difflib.HtmlDiff(wrapcolumn=90).make_file(orig.splitlines(),source.splitlines(),fromdesc='Frozen original paper.md',todesc='Reviewed author draft',context=True,numlines=2,charset='utf-8')
(OUT/'逐段修改对照.html').write_text(diff,encoding='utf-8')
reader=PdfReader(pdf);text='\n'.join(p.extract_text() or '' for p in reader.pages)
(HERE/'evidence/revised_pdf_text.txt').write_text(text,encoding='utf-8')
checks={'pages':len(reader.pages),'original_words_whitespace':len(orig.split()),'revised_words_whitespace':len(source.split()),'figures':len(fig_hashes),'figure_hashes':fig_hashes,'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'replacement_character': '\ufffd' in text,'required_numbers_present':{x:x in text for x in ['0.0372','0.0486','0.1011','0.540','93.8%','0.1277','0.05843']}}
(HERE/'evidence/revision_build.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(checks,indent=2))
