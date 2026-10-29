import os, io, base64, uuid, threading, time
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from openai import OpenAI

BASE=Path(__file__).resolve().parent
DATA=BASE/'data'
DATA.mkdir(exist_ok=True)
app=FastAPI(title='AI Sprite Studio')
app.mount('/static',StaticFiles(directory=BASE/'static'),name='static')
app.mount('/data',StaticFiles(directory=DATA),name='data')
jobs={}
POSES={
'Idle':['neutral standing','inhale, shoulders rise','exhale, shoulders settle','return to standing'],
'Walk':['left foot contact, right foot back','left foot bears weight','right leg passes under hips','right foot reaches forward','right foot contact, left foot back','right foot bears weight','left leg passes under hips','left foot reaches forward'],
'Run':['left foot contact','left push off','right knee swings forward','airborne phase','right foot contact','right push off','left knee swings forward','airborne phase'],
'Punch':['guard','wind-up','hip rotation','fist extends','impact','recover'],
'Kick':['guard','weight shift','knee up','leg extends','retract','recover'],
'Jump':['crouch','push off','ascending','apex','descending','landing'],
'Hit':['neutral','impact','recoil','recover'],
'Knockdown':['neutral','impact','stumble','fall','on ground','recover'],
'Victory':['neutral','raise fists','hold','small bounce','return']
}
def fit(data,size=256):
    im=Image.open(io.BytesIO(data)).convert('RGBA')
    im.thumbnail((size-12,size-12),Image.Resampling.NEAREST)
    out=Image.new('RGBA',(size,size))
    out.alpha_composite(im,((size-im.width)//2,size-im.height-4))
    return out
def remove_white(data):
    im=Image.open(io.BytesIO(data)).convert('RGBA')
    im.thumbnail((250,250),Image.Resampling.NEAREST)
    px=im.load();w,h=im.size;seen=set();q=[]
    for x in range(w):q.extend([(x,0),(x,h-1)])
    for y in range(h):q.extend([(0,y),(w-1,y)])
    while q:
        x,y=q.pop()
        if (x,y) in seen or x<0 or y<0 or x>=w or y>=h:continue
        seen.add((x,y));r,g,b,a=px[x,y]
        if a<20 or min(r,g,b)>242:
            px[x,y]=(r,g,b,0)
            q.extend([(x-1,y),(x+1,y),(x,y-1),(x,y+1)])
    bbox=im.getbbox()
    if bbox: im=im.crop(bbox)
    buf=io.BytesIO();im.save(buf,format='PNG')
    return fit(buf.getvalue())
def run_job(jid,source,action,count,direction,notes,model,only=None,revision=''):
    job=jobs[jid];folder=DATA/jid;folder.mkdir(exist_ok=True)
    try:
        client=OpenAI(api_key=os.environ['OPENAI_API_KEY'],timeout=180,max_retries=1)
        (folder/'reference.png').write_bytes(source)
        for i in ([only] if only is not None else range(count)):
            poses=POSES[action]
            pose=poses[int(i*len(poses)/count)]
            prompt=f'Create exactly ONE isolated 16-bit pixel art game sprite frame. Attached character is the strict identity reference. Action {action}, frame {i+1} of {count}, direction {direction}. Pose: {pose}. Keep same face, head, haircut, costume, jacket details, proportions, palette, scale and baseline. Full body centered, single pose, clean white background, no extra characters, no text, no shadow, no extra limbs. {notes}. Requested correction: {revision}'
            with open(folder/'reference.png','rb') as f:
                response=client.images.edit(model=model,image=f,prompt=prompt,size='1024x1024',quality='low')
            if not response.data or not response.data[0].b64_json:raise ValueError('No image returned')
            image=remove_white(base64.b64decode(response.data[0].b64_json))
            image.save(folder/f'frame_{i:02d}.png')
            job['frames'][str(i)]=f'/data/{jid}/frame_{i:02d}.png?t={int(time.time())}'
            job['done']+=1
        job['state']='complete'
    except Exception as exc:
        job['state']='error';job['error']=str(exc)[:500]
@app.get('/')
def home():return FileResponse(BASE/'static'/'index.html')
@app.get('/api/status')
def status():return {'key_configured':bool(os.getenv('OPENAI_API_KEY'))}
@app.post('/api/generate')
async def generate(image:UploadFile=File(...),animation:str=Form('Walk'),frames:int=Form(8),direction:str=Form('Right'),notes:str=Form(''),model:str=Form('gpt-image-1.5'),existing_job:str=Form(''),frame_index:int=Form(-1),revision:str=Form('')):
    if not os.getenv('OPENAI_API_KEY'):raise HTTPException(400,'OPENAI_API_KEY is not configured on server')
    if frames not in (4,6,8,12):raise HTTPException(400,'Invalid frame count')
    if animation not in POSES:raise HTTPException(400,'Unknown animation')
    if model not in ('gpt-image-1.5','gpt-image-1'):raise HTTPException(400,'Unknown model')
    raw=await image.read()
    if len(raw)>10_000_000:raise HTTPException(400,'Image > 10 MB')
    try:
        im=fit(raw,512);buf=io.BytesIO();im.save(buf,format='PNG');source=buf.getvalue()
    except Exception:raise HTTPException(400,'Invalid image')
    if existing_job:
        if existing_job not in jobs or not 0<=frame_index<frames:raise HTTPException(400,'Unknown job/frame')
        jid=existing_job;job=jobs[jid]
        if job['state']=='running':raise HTTPException(409,'Job already running')
        job.update(state='running',done=0,total=1,error=None)
        only=frame_index
    else:
        jid=uuid.uuid4().hex[:16]
        jobs[jid]={'state':'running','done':0,'total':frames,'frames':{},'error':None,'animation':animation}
        only=None
    threading.Thread(target=run_job,args=(jid,source,animation,frames,direction,notes,model,only,revision),daemon=True).start()
    return {'job_id':jid}
@app.get('/api/jobs/{jid}')
def get_job(jid:str):
    if jid not in jobs:raise HTTPException(404,'Job not found')
    return jobs[jid]
@app.get('/api/jobs/{jid}/sheet')
def sheet(jid:str):
    if jid not in jobs:raise HTTPException(404,'Job not found')
    folder=DATA/jid;paths=sorted(folder.glob('frame_*.png'))
    if not paths:raise HTTPException(404,'No frames')
    out=Image.new('RGBA',(256*len(paths),256))
    for i,path in enumerate(paths):out.alpha_composite(Image.open(path).convert('RGBA'),(256*i,0))
    dest=folder/'sheet.png';out.save(dest)
    return FileResponse(dest,filename=f"{jobs[jid]['animation'].lower()}-sheet.png")
