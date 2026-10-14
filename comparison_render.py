"""Editorial comparison cards with real affiliate catalog photos."""
import io
import math
import urllib.request as ur
from PIL import Image,ImageOps,ImageDraw
from core import ROOT
from editorial import label,rank_speech,beat_music
from render import command,duration
from affiliate import DISCLOSURE,price,safe_url
from comparison_facts import assessment,rank_label

def photo(p,path,platform):
    if not path.exists():
        domains=['coupangcdn.com','coupang.com'] if platform=='coupang' else ['alicdn.com']
        safe_url(p['image'],domains)
        with ur.urlopen(p['image'],timeout=30) as response:
            safe_url(response.geturl(),domains)
            raw=response.read(12*1024*1024+1)
        if len(raw)>12*1024*1024:raise ValueError('상품 사진 크기 초과')
        im=Image.open(io.BytesIO(raw));im.load()
        im.convert('RGB').save(path,quality=95)
    return Image.open(path).convert('RGB')

def card(c,snap,pair,dest,out):
    im=Image.new('RGB',(1080,1920),'#F7F4EE');d=ImageDraw.Draw(im)
    label(d,c,'THE COMPARISON EDIT',(70,130),30,'#8C6B54')
    label(d,c,snap['source']+' · 순위와 가격·기능 비교',(70,220),51)
    d.rounded_rectangle((60,330,1020,445),radius=20,fill='#E9E1D4')
    label(d,c,DISCLOSURE,(80,366),34,width=920)
    if pair:
        comparison=pair.get('assessment') or assessment(pair)
        label(d,c,rank_label(snap['platform'],pair['rank']),(70,480),55,'#667553')
        for index,tag in enumerate(('popular','alternative')):
            p=pair[tag];x=60+index*490
            d.rounded_rectangle((x,620,x+470,1505),radius=30,fill='white')
            label(d,c,'순위 상품' if tag=='popular' else '같은 종류 · 비교 상품',(x+25,650),29,'#667553',width=420)
            image=photo(p,out/(tag+'_'+p['id']+'.jpg'),snap['platform'])
            image=ImageOps.contain(image,(420,530));im.paste(image,(x+235-image.width//2,735+(530-image.height)//2))
            d=ImageDraw.Draw(im)
            # Titles wrap and are kept separate from unverifiable specification claims.
            text=p['name'];lines=[text[i:i+15] for i in range(0,min(len(text),45),15)]
            for n,line in enumerate(lines):label(d,c,line,(x+25,1290+n*45),30,width=420)
            label(d,c,price(p),(x+25,1440),44,'#8C6B54',width=420)
        label(d,c,comparison['price_line'],(70,1530),37,'#8C6B54',width=940)
        label(d,c,comparison['features'][0],(70,1590),29,'#667553',width=940)
    else:
        label(d,c,'오늘의 인기 상품',(70,630),80)
        label(d,c,'TOP 10 × 동종 대안',(70,780),68,'#667553')
        label(d,c,'상품 링크 → 채널 프로필',(70,1030),55,'#8C6B54')
        label(d,c,'사진·상품명·가격: 판매처 API 자료',(70,1200),34)
    label(d,c,'옵션·배송비·세금·쿠폰·재고는 구매 전 확인',(70,1660),29,width=940)
    label(d,c,'확인: '+snap['collected_at'][:16],(70,1720),27,'#777269')
    label(d,c,'범위: '+snap['scope'],(70,1770),27,'#777269')
    label(d,c,'국내 전체 판매순위 아님 · AI 합성 음성',(70,1820),27,'#777269')
    im.save(dest,quality=95)

def render_comparison(c,store,jid,script):
    snap=script['_affiliate'];out=ROOT/'output'/jid;out.mkdir(parents=True,exist_ok=True)
    pairs=[None,*snap['pairs'],None];clips=[];seconds=0
    for i,(pair,scene) in enumerate(zip(pairs,script['scenes'])):
        image=out/f'card_{i}.jpg';card(c,snap,pair,image,out)
        audio=out/f'voice_{i}.mp3';rank_speech(scene['narration'],audio,c,store)
        sec=math.ceil((duration(audio,c)+.2)*30)/30;frames=math.ceil(sec*30)
        clip=out/f'clip_{i}.mp4'
        command([c['ffmpeg'],'-y','-loglevel','error','-loop','1','-i',image,'-i',audio,
            '-vf',f"zoompan=z='1+0.006*on/{frames}':d=1:s=1080x1920:fps=30,fade=t=in:st=0:d=0.12",
            '-af','loudnorm=I=-17:TP=-2:LRA=7,apad','-t',str(sec),'-c:v','libx264','-preset','fast',
            '-crf','20','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-ac','2','-threads','2',clip])
        clips.append(clip);seconds+=sec
    if not 15<=seconds<=175:raise ValueError('쇼츠 길이 제한 초과')
    listing=out/'concat.txt';listing.write_text('\n'.join(f"file '{p.name}'" for p in clips))
    joined=out/'joined.mp4';command([c['ffmpeg'],'-y','-loglevel','error','-f','concat','-safe','0','-i',listing,'-c','copy',joined])
    bg=out/'music.wav';beat_music(bg);final=out/'short.mp4'
    command([c['ffmpeg'],'-y','-loglevel','error','-i',joined,'-stream_loop','-1','-i',bg,
        '-filter_complex','[1:a]volume=0.12[m];[0:a][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89[a]',
        '-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-movflags','+faststart','-shortest',final])
    return str(final.relative_to(ROOT)),round(seconds,2)
