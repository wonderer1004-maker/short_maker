"""Cream editorial product-ranking Shorts, matching the approved preview."""
import json
import math
from pathlib import Path
import subprocess
from PIL import Image,ImageOps,ImageDraw,ImageFont,ImageFilter
from core import ROOT
from popularity import assets
from render import command,duration,speech,music

COLORS=['#8C6B54','#667553','#3D4B57','#9B655B','#5A8091']

def product_tags(name):
    tags=[]
    if any(k in name for k in ('후드','후디드')):tags.append('후드 디자인')
    for key,label in [('브이넥','브이넥'),('라운드넥','라운드넥'),('집업','집업'),('케이블','케이블 니트'),('퀼팅','퀼팅')]:
        if key in name:tags.append(label)
    if '다운' in name:tags.append('다운 제품명 표기')
    return ' · '.join(tags[:2]) if tags else '매출 · 조회수 · 후기수 반영'

def beat_music(path):
    """Original 110 BPM instrumental; no copyrighted song samples."""
    import numpy as np
    import wave
    rate=32000;seconds=16*60/110;t=np.arange(int(seconds*rate))/rate
    beat=60/110;out=np.zeros_like(t);rng=np.random.default_rng(31)
    roots=[130.8128,110,87.3071,98]
    for k,bt in enumerate(np.arange(0,seconds,beat)):
        mask=(t>=bt)&(t<bt+.35);x=t[mask]-bt
        out[mask]+=.30*np.sin(2*np.pi*(48*x+10*(1-np.exp(-x*25))))*np.exp(-x*14)
        if k%2:
            mask=(t>=bt)&(t<bt+.14);x=t[mask]-bt
            out[mask]+=.07*rng.normal(size=len(x))*np.exp(-x*30)
        root=roots[(k//4)%4]/2;mask=(t>=bt)&(t<bt+.38);x=t[mask]-bt
        out[mask]+=.11*np.sin(2*np.pi*root*x)*np.minimum(x*70,1)*np.exp(-x*6)
    for k,bt in enumerate(np.arange(0,seconds,beat/2)):
        mask=(t>=bt)&(t<bt+.055);x=t[mask]-bt
        n=rng.normal(size=len(x));n=np.concatenate(([0],np.diff(n)))
        out[mask]+=.012*n*np.exp(-x*75)
        tone=roots[int(bt/(beat*4))%4]*[2,2.5,3,4][k%4]
        mask=(t>=bt)&(t<bt+.45);x=t[mask]-bt
        out[mask]+=.07*(np.sin(2*np.pi*tone*x)+.25*np.sin(2*np.pi*tone*2*x))*np.exp(-x*8)
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate)
        w.writeframes((np.clip(out,-.95,.95)*32767).astype('<i2').tobytes())

def font(c,size,weight=650):
    f=ImageFont.truetype(str(ROOT/c['font_path']),size)
    try:f.set_variation_by_axes([weight])
    except (OSError,AttributeError):pass
    return f

def label(draw,c,text,xy,size=38,color='#262C2E',width=910,weight=650):
    f=font(c,size,weight)
    while draw.textlength(text,font=f)>width and size>20:
        size-=1;f=font(c,size,weight)
    if draw.textlength(text,font=f)>width:
        while draw.textlength(text+'…',font=f)>width:text=text[:-1]
        text+='…'
    draw.text(xy,text,font=f,fill=color)

def base(c,snapshot):
    im=Image.new('RGB',(1080,1920),'#F7F4EE');d=ImageDraw.Draw(im)
    label(d,c,'THE POPULARITY EDIT',(80,125),29,'#8D887E')
    d.line((80,195,1000,195),fill='#D8D2C6',width=2)
    label(d,c,'무신사 상품 인기순위 / '+snapshot['category'],(80,1685),27,'#777269',weight=500)
    label(d,c,'순위 갱신: '+snapshot['display_updated_at'],(80,1734),25,'#918A7E',weight=450)
    label(d,c,'쿠폰 전 표시가 · 가격·재고 변동 가능',(80,1780),25,'#918A7E',weight=450)
    label(d,c,'브랜드 전체 / 국내 전체 판매순위 아님',(80,1825),23,'#999388',weight=450)
    return im

def product(c,snapshot,p,path,dest):
    im=base(c,snapshot);d=ImageDraw.Draw(im);accent=COLORS[(p['rank']-1)%5]
    label(d,c,f'{p["rank"]:02}',(80,220),165,accent,weight=500)
    label(d,c,'POPULARITY RANK',(315,268),28,accent)
    label(d,c,'무신사 카테고리 '+str(p['rank'])+'위',(315,315),32,'#7F7A72',width=650)
    label(d,c,p['brand'],(82,436),62,weight=750)
    # Two lines preserve product names without overflowing the panel.
    name=p['name'];size=38;f=font(c,size,500);lines=[];line=''
    for ch in name:
        if d.textlength(line+ch,font=f)>910:lines.append(line);line=ch
        else:line+=ch
    if line:lines.append(line)
    for n,line in enumerate(lines[:2]):label(d,c,line,(82,530+n*48),size,'#6E6B65',weight=500)
    panel_top=650 if len(lines)>1 else 602
    shadow=Image.new('RGBA',im.size);sd=ImageDraw.Draw(shadow)
    sd.rounded_rectangle((107,panel_top+20,973,1510),radius=40,fill=(45,40,32,28))
    im=Image.alpha_composite(im.convert('RGBA'),shadow.filter(ImageFilter.GaussianBlur(22)))
    d=ImageDraw.Draw(im);d.rounded_rectangle((108,panel_top,972,1502),radius=36,fill='white')
    photo=ImageOps.contain(Image.open(path).convert('RGB'),(790,1378-panel_top))
    im.paste(photo,(540-photo.width//2,panel_top+15+(1378-panel_top-photo.height)//2));d=ImageDraw.Draw(im)
    d.rounded_rectangle((130,1324,950,1390),radius=16,fill='#F2F3EF')
    label(d,c,product_tags(p['name']),(148,1338),31,'#575852',width=780)
    d.rounded_rectangle((108,1406,972,1625),radius=30,fill=accent)
    label(d,c,'쿠폰 전 표시 판매가',(150,1430),25,'#EDE9E2')
    label(d,c,f'{p["price"]:,}',(150,1475),94,'white',width=660,weight=750)
    label(d,c,'원',(820,1518),40,'white',width=100)
    im.convert('RGB').save(dest,quality=96)

def bookend(c,snapshot,paths,dest,closing=False):
    im=base(c,snapshot);d=ImageDraw.Draw(im)
    title='인기순 한눈에' if closing else '오늘의 인기 TOP 5'
    label(d,c,title,(80,280),85,weight=780)
    label(d,c,snapshot['category'],(84,413),43,'#8C6B54',weight=600)
    if closing:
        for i,p in enumerate(snapshot['products']):
            y=650+i*175;d.rounded_rectangle((80,y,1000,y+145),radius=24,fill='white')
            label(d,c,str(p['rank']),(108,y+38),49,COLORS[i],width=70)
            label(d,c,p['brand'],(190,y+45),40,width=480)
            label(d,c,f'{p["price"]:,}',(720,y+43),43,COLORS[i],width=225)
        label(d,c,'저장하고 구매 전에 다시 확인',(82,1580),39,'#6E6B65')
    else:
        label(d,c,'공개 랭킹 그대로 · 실제 제품 사진',(84,500),33,'#8C6B54')
        for i,(p,path) in enumerate(zip(snapshot['products'],paths)):
            x=70+i%2*486;y=690+i//2*295
            if i==4:x=315
            d.rounded_rectangle((x,y,x+450,y+260),radius=22,fill='white',outline='#E5DFD4',width=2)
            a=ImageOps.contain(Image.open(path).convert('RGB'),(178,230));im.paste(a,(x+12+(178-a.width)//2,y+12+(230-a.height)//2));d=ImageDraw.Draw(im)
            label(d,c,f'{p["rank"]:02}',(x+207,y+38),46,COLORS[i],width=210)
            label(d,c,p['brand'],(x+207,y+107),29,width=220)
            label(d,c,f'{p["price"]:,}원',(x+207,y+163),29,COLORS[i],width=220)
    im.save(dest,quality=96)

def rank_speech(text,path,c,store):
    if path.exists() and path.stat().st_size>1000:return
    if c.get('speech_provider','openai')=='openai':
        speech(text,path,c,store);return
    if c['speech_provider']!='edge':raise ValueError('알 수 없는 음성 제공자')
    import asyncio,ssl,edge_tts,edge_tts.communicate
    edge_tts.communicate._SSL_CTX=ssl.create_default_context()
    store.reserve_request(c['max_ai_requests_daily'])
    async def make():
        speaker=edge_tts.Communicate(text,voice=c.get('edge_voice','ko-KR-SunHiNeural'),rate='+12%',connect_timeout=15,receive_timeout=45)
        temp=path.with_suffix('.partial')
        try:
            await asyncio.wait_for(speaker.save(str(temp)),80)
            temp.replace(path)
        finally:temp.unlink(missing_ok=True)
    asyncio.run(make())

def render_ranking(c,store,id,snapshot,script):
    import datetime as dt
    from core import KST
    out=ROOT/'output'/id;out.mkdir(parents=True,exist_ok=True)
    snapshot=dict(snapshot)
    stamp=dt.datetime.fromisoformat(snapshot['source_updated_at']).astimezone(KST)
    snapshot['display_updated_at']=stamp.strftime('%Y.%m.%d %H:%M KST')
    photos=assets(snapshot,out/'products')
    first=out/'intro.jpg';last=out/'outro.jpg'
    bookend(c,snapshot,photos,first);bookend(c,snapshot,photos,last,True)
    cards=[first]
    for p,path in reversed(list(zip(snapshot['products'],photos))):
        file=out/f'rank_{p["rank"]}.jpg';product(c,snapshot,p,path,file);cards.append(file)
    cards.append(last);clips=[];seconds=0
    for i,(card,scene) in enumerate(zip(cards,script['scenes'])):
        audio=out/f'voice_{i}.mp3';rank_speech(scene['narration'],audio,c,store)
        sec=max(1.5,duration(audio,c)+.15);frames=math.ceil(sec*30);sec=frames/30
        clip=out/f'clip_{i}.mp4'
        vf=f"zoompan=z='1+0.012*on/{frames}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x1920:fps=30,fade=t=in:st=0:d=0.12"
        command([c['ffmpeg'],'-y','-loglevel','error','-loop','1','-i',card,'-i',audio,'-vf',vf,'-af','loudnorm=I=-17:TP=-2:LRA=7,apad',
          '-t',str(sec),'-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-ac','2','-threads','2',clip])
        clips.append(clip);seconds+=sec
    if not 20<=seconds<=90:raise ValueError('인기 영상 길이 범위 20~90초 초과')
    listing=out/'concat.txt';listing.write_text('\n'.join(f"file '{p.name}'" for p in clips))
    joined=out/'joined.mp4';command([c['ffmpeg'],'-y','-loglevel','error','-f','concat','-safe','0','-i',listing,'-c','copy',joined])
    bg=out/'original_music.wav';beat_music(bg)
    if c.get('music_path'):
        if not c.get('music_rights_confirmed'):raise ValueError('음악 사용 권한 확인 필요')
        bg=ROOT/c['music_path']
    final=out/'short.mp4'
    command([c['ffmpeg'],'-y','-loglevel','error','-i',joined,'-stream_loop','-1','-i',bg,
      '-filter_complex','[1:a]volume=0.20[m];[0:a]asplit=2[v][side];[m][side]sidechaincompress=threshold=0.015:ratio=5:attack=10:release=200[d];[v][d]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89[a]',
      '-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',final])
    streams=json.loads(command([c['ffprobe'],'-v','error','-show_streams','-of','json',final]))['streams']
    if not any(v.get('width')==1080 and v.get('height')==1920 for v in streams):raise ValueError('세로 영상 검증 실패')
    return str(final.relative_to(ROOT)),round(seconds,2)
