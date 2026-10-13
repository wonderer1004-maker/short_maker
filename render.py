"""Original portrait motion cards, optional licensed images, scene-aligned TTS."""
import array
import json
import math
from pathlib import Path
import subprocess
import urllib.request
import wave
import os
from PIL import Image, ImageDraw, ImageFont, ImageOps
from core import ROOT

def command(args):
    p=subprocess.run([str(x) for x in args], capture_output=True, text=True)
    if p.returncode: raise RuntimeError(p.stderr[-1400:])
    return p.stdout

def duration(path,c):
    return float(command([c['ffprobe'],'-v','error','-show_entries','format=duration',
                          '-of','default=noprint_wrappers=1:nokey=1',path]).strip())

def wrapped(draw,text,font,width):
    lines=[]; line=''
    for char in text:
        if char=='\n' or draw.textlength(line+char,font=font)>width:
            lines.append(line); line='' if char=='\n' else char
        else: line+=char
    if line: lines.append(line)
    return lines

def block(draw,text,y,size,color,width=840,max_lines=8):
    font=ImageFont.truetype(str(FONT),size)
    try:font.set_variation_by_axes([650 if size>=65 else 500])
    except (OSError,AttributeError):pass
    lines=wrapped(draw,text,font,width)
    if len(lines)>max_lines:
        raise ValueError('화면 텍스트가 넘칩니다. 대본을 줄여주세요.')
    for line in lines:
        draw.text((110,y),line,font=font,fill=color)
        y+=int(size*1.45)
    return y

FONT=ROOT/'assets/fonts/NotoSansKR.ttf'

def card(c, scene, index, count, dest, media=None, demo=False):
    global FONT
    FONT=ROOT/c['font_path']
    if not FONT.exists(): raise RuntimeError('한글 폰트가 없습니다. font_path를 확인하세요.')
    themes=[((10,21,38),(50,222,184)),((27,18,46),(190,151,255)),((22,33,35),(255,203,99))]
    bg,accent=themes[index%3]
    im=Image.new('RGB',(1080,1920),bg); d=ImageDraw.Draw(im)
    for r in range(540,20,-8):
        shade=tuple(min(255,x+int((540-r)/100)) for x in bg)
        d.ellipse((760-r,-180-r,760+r,-180+r),fill=shade)
    d.rounded_rectangle((88,155,992,170),radius=7,fill=accent)
    block(d,c['channel_name'],215,34,(180,191,207))
    block(d,f'{index+1:02d} / {count:02d}',310,42,accent)
    heading_size=72
    while heading_size>46:
        f=ImageFont.truetype(str(FONT),heading_size)
        if len(wrapped(d,scene['heading'],f,840))<=3:break
        heading_size-=4
    block(d,scene['heading'],420,heading_size,(247,249,255),max_lines=3)
    if media:
        photo=Image.open(media).convert('RGB')
        photo=ImageOps.fit(photo,(860,460))
        im.paste(photo,(110,760)); d=ImageDraw.Draw(im)
        panel_top=1250; font_size=38
        while font_size>26:
            f=ImageFont.truetype(str(FONT),font_size)
            if len(wrapped(d,scene['narration'],f,840))*int(font_size*1.45)<=360:break
            font_size-=2
    else:
        d.rounded_rectangle((110,790,970,990),radius=30,fill=tuple(x+14 for x in bg))
        block(d,'CHECK BEFORE YOU BUY',845,38,accent)
        panel_top=1090; font_size=43
    while font_size>26:
        f=ImageFont.truetype(str(FONT),font_size)
        try:f.set_variation_by_axes([500])
        except (OSError,AttributeError):pass
        n=len(wrapped(d,scene['narration'],f,840))
        if n<=8 and n*int(font_size*1.45)<=1650-panel_top-20:break
        font_size-=2
    d.rounded_rectangle((82,panel_top-30,998,1650),radius=34,fill=(17,26,42))
    block(d,scene['narration'],panel_top,font_size,(240,244,250),max_lines=8)
    d.rounded_rectangle((110,1710,970,1724),radius=6,fill=(65,76,93))
    d.rounded_rectangle((110,1710,110+int(860*(index+1)/count),1724),radius=6,fill=accent)
    block(d,'화면 미리보기 · 음성 없음' if demo else 'AI 내레이션 · 구매 체크리스트',1780,27,(164,178,197))
    im.save(dest)

def music(path,seconds=12):
    """Locally synthesized original instrumental loop, no sampled recordings."""
    rate=22050; data=array.array('h')
    chords=[(130.81,164.81,196.00),(110,130.81,164.81),(87.31,110,130.81),(98,123.47,146.83)]
    for i in range(int(rate*seconds)):
        t=i/rate; chord=chords[int(t//3)%4]
        phase=t%0.75; envelope=math.exp(-phase*6)
        val=sum(math.sin(2*math.pi*f*t) for f in chord)*.035
        val+=math.sin(2*math.pi*chord[int(t/.75)%3]*2*t)*envelope*.07
        data.append(int(32767*val))
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(data.tobytes())

def speech(text,path,c,store):
    if path.exists(): return
    store.reserve_request(c['max_ai_requests_daily'])
    key=os.environ.get('OPENAI_API_KEY')
    if not key: raise RuntimeError('OPENAI_API_KEY가 없습니다.')
    req=urllib.request.Request('https://api.openai.com/v1/audio/speech',
         data=json.dumps({'model':c['speech_model'],'voice':c['voice'],
                          'input':text,'response_format':'mp3'}).encode(),
         headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=120) as r: body=r.read()
    tmp=path.with_suffix('.tmp');tmp.write_bytes(body);tmp.replace(path)

def timecode(t):
    ms=round(t*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'

def render(c,store,job_id,script,brief,demo=False):
    out=ROOT/'output'/job_id; out.mkdir(parents=True,exist_ok=True)
    media=brief.get('media',[])
    if media and not brief.get('media_rights_confirmed'):
        raise RuntimeError('제품 이미지의 사용 권한을 catalog.json에 확인하세요.')
    media_paths=[]
    for m in media:
        p=(ROOT/m).resolve()
        if not p.is_relative_to((ROOT/'assets/media').resolve()) or not p.is_file():
            raise RuntimeError('이미지는 assets/media 아래의 실제 파일이어야 합니다.')
        media_paths.append(p)
    clips=[];srt=[];total=0
    for i,scene in enumerate(script['scenes']):
        audio=out/f'voice_{i}.mp3'
        if not demo: speech(scene['narration'],audio,c,store)
        sec=5.0 if demo else max(3.0,duration(audio,c)+.25)
        img=out/f'card_{i}.png';clip=out/f'clip_{i}.mp4'
        card(c,scene,i,len(script['scenes']),img,media_paths[i%len(media_paths)] if media_paths else None,demo)
        frames=math.ceil(sec*24)
        args=[c['ffmpeg'],'-y','-loglevel','error','-threads','2','-loop','1','-i',img]
        if demo: args+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
        else: args+=['-i',audio]
        args+=['-vf',f"zoompan=z='min(zoom+0.00025,1.04)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x1920:fps=24",
               '-af','apad','-t',f'{frames/24:.3f}','-c:v','libx264','-preset','veryfast','-crf','23',
               '-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-ac','2','-threads','2',clip]
        command(args); clips.append(clip)
        srt.append(f'{i+1}\n{timecode(total)} --> {timecode(total+frames/24)}\n{scene["narration"]}\n')
        total+=frames/24
    if not demo and not 20<=total<=60:
        raise RuntimeError(f'영상 길이 {total:.1f}초. 대본 길이를 조절하세요. 공개하지 않습니다.')
    listing=out/'concat.txt'
    listing.write_text('\n'.join(f"file '{x.name}'" for x in clips),encoding='utf-8')
    joined=out/'joined.mp4'
    command([c['ffmpeg'],'-y','-loglevel','error','-f','concat','-safe','0','-i',listing,'-c','copy',joined])
    bg=out/'original_music.wav';music(bg)
    if c.get('music_path'):
        if not c.get('music_rights_confirmed'): raise RuntimeError('배경음악 사용 권한을 확인하세요.')
        bg=ROOT/c['music_path']
    final=out/'short.mp4'
    command([c['ffmpeg'],'-y','-loglevel','error','-i',joined,'-stream_loop','-1','-i',bg,
             '-filter_complex','[1:a]volume=0.12[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]',
             '-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-movflags','+faststart','-shortest',final])
    (out/'captions.srt').write_text('\n'.join(srt),encoding='utf-8')
    info=json.loads(command([c['ffprobe'],'-v','error','-show_streams','-of','json',final]))
    v=next(x for x in info['streams'] if x['codec_type']=='video')
    if (v['width'],v['height'])!=(1080,1920): raise RuntimeError('영상 크기 검증 실패')
    return str(final.relative_to(ROOT)),round(total,2)
