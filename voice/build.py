"""Tạo giọng đọc cho Chopper English theo cách của khanh-voice:
Edge TTS (Microsoft Neural, không cần key) + lọc âm FFmpeg (cắt khoảng lặng, loudnorm -16 LUFS).
Tiếng Anh: giọng nữ en-US-JennyNeural. Tiếng Việt: giọng nữ vi-VN-HoaiMyNeural."""
import asyncio, hashlib, json, os, re, subprocess
import edge_tts

HERE = os.path.dirname(os.path.abspath(__file__))
CLIPS = os.path.join(HERE, 'clips')
os.makedirs(CLIPS, exist_ok=True)
VOICES = {'en': os.environ.get('VOICE_EN', 'en-US-JennyNeural'), 'vi': os.environ.get('VOICE_VI', 'vi-VN-HoaiMyNeural')}
RATE = os.environ.get('RATE', '-10%')
P = json.load(open(os.path.join(HERE, 'phrases.json'), encoding='utf8'))
nk = lambda x: re.sub(r'[.!?…]+$', '', x.strip()).lower()
AF = ('highpass=f=70,'
      'silenceremove=start_periods=1:start_threshold=-45dB,areverse,'
      'silenceremove=start_periods=1:start_threshold=-45dB,areverse,'
      'adelay=40,apad=pad_dur=0.08,loudnorm=I=-16:TP=-1.5:LRA=9')
items = [('en', t) for t in P['en']] + [('vi', t) for t in P['vi']]
name = lambda lang, t: lang + '-' + hashlib.md5((VOICES[lang] + RATE + t).encode()).hexdigest()[:10] + '.mp3'


async def one(lang, text, sem):
    out = os.path.join(CLIPS, name(lang, text))
    if os.path.exists(out) and os.path.getsize(out) > 500:
        return
    raw = out + '.raw.mp3'
    async with sem:
        for attempt in range(8):
            try:
                await edge_tts.Communicate(text, VOICES[lang], rate=RATE).save(raw)
                if os.path.getsize(raw) > 500:
                    await asyncio.sleep(0.4)
                    break
            except Exception as e:
                print('retry', text, e)
                await asyncio.sleep(3 + attempt * 4)
        else:
            print('FAILED', text)
            return
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', raw, '-af', AF,
                    '-ac', '1', '-ar', '24000', '-b:a', '40k', out], check=True)
    os.remove(raw)


async def main():
    keep = {name(l, t) for l, t in items}
    for f in os.listdir(CLIPS):
        if f not in keep:
            os.remove(os.path.join(CLIPS, f))
    sem = asyncio.Semaphore(2)
    await asyncio.gather(*(one(l, t, sem) for l, t in items))
    m = {}
    for l, t in items:
        if os.path.exists(os.path.join(CLIPS, name(l, t))):
            m[('vi:' if l == 'vi' else '') + nk(t)] = 'voice/clips/' + name(l, t)
    with open(os.path.join(HERE, 'voice.js'), 'w', encoding='utf8') as f:
        f.write('window.VOICE_CLIPS=' + json.dumps(m, ensure_ascii=False, separators=(',', ':')) + ';\n')
    print(f'{len(m)}/{len(items)} câu')
    if len(m) < len(items):
        print('Còn thiếu câu, chạy lại workflow để tạo nốt.')

asyncio.run(main())
