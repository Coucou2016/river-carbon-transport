from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
ROOT=Path(__file__).resolve().parents[2]; p=ROOT/'tmp/review_20260927/revised_pdf'
files=sorted(p.glob('page-*.png'))
for start in range(0,len(files),6):
    board=Image.new('RGB',(1260,1240),'#d8dde3');d=ImageDraw.Draw(board)
    for j,f in enumerate(files[start:start+6]):
        im=Image.open(f).convert('RGB'); im.thumbnail((400,580));x=10+(j%3)*420;y=30+(j//3)*620
        board.paste(im,(x,y));d.text((x,y-20),f.stem,fill='black')
    board.save(p/f'contact_{start//6+1}.png')
print(len(files),'pages')
