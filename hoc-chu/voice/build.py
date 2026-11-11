"""Tạo giọng đọc cho Bé Vui Học Chữ theo cách của khanh-voice:
Edge TTS (Microsoft Neural, không cần key) + lọc âm FFmpeg (highpass, cắt khoảng lặng, loudnorm -16 LUFS).
Chạy tự động bằng GitHub Actions khi phrases.json thay đổi."""
import asyncio, json, os, re, subprocess, sys
import edge_tts

HERE = os.path.dirname(os.path.abspath(__file__))
CLIPS = os.path.join(HERE, 'clips')
os.makedirs(CLIPS, exist_ok=True)
VOICE = os.environ.get('VOICE', 'vi-VN-HoaiMyNeural')
RATE = os.environ.get('RATE', '-8%')
PITCH = os.environ.get('PITCH', '+0Hz')
phrases = json.load(open(os.path.join(HERE, 'phrases.json'), encoding='utf8'))
nk = lambda x: re.sub(r'[.!?…]+$', '', x.strip()).lower()
AF = ('highpass=f=70,'
      'silenceremove=start_periods=1:start_threshold=-45dB,areverse,'
      'silenceremove=start_periods=1:start_threshold=-45dB,areverse,'
      'adelay=40,apad=pad_dur=0.08,loudnorm=I=-16:TP=-1.5:LRA=9')


async def one(i, text, sem):
    out = os.path.join(CLIPS, f'{i:03d}.mp3')
    raw = out + '.raw.mp3'
    if os.path.exists(out) and os.path.getsize(out) > 500:
        return
    async with sem:
        for attempt in range(8):
            try:
                await edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH).save(raw)
                if os.path.getsize(raw) > 500:
                    await asyncio.sleep(0.4)
                    break
            except Exception as e:
                print('retry', i, text, e)
                await asyncio.sleep(3 + attempt * 4)
        else:
            print('FAILED', i, text)
            return
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', raw, '-af', AF,
                    '-ac', '1', '-ar', '24000', '-b:a', '40k', out], check=True)
    os.remove(raw)


async def main():
    if os.environ.get('FRESH') == '1':
        for f in os.listdir(CLIPS):
            os.remove(os.path.join(CLIPS, f))
    for f in os.listdir(CLIPS):
        if f.endswith('.raw.mp3'):
            os.remove(os.path.join(CLIPS, f))
    sem = asyncio.Semaphore(2)
    await asyncio.gather(*(one(i, t, sem) for i, t in enumerate(phrases)))
    m = {}
    for i, t in enumerate(phrases):
        if os.path.exists(os.path.join(CLIPS, f'{i:03d}.mp3')):
            m[nk(t)] = f'voice/clips/{i:03d}.mp3'
    with open(os.path.join(HERE, 'voice.js'), 'w', encoding='utf8') as f:
        f.write('window.VOICE_CLIPS=' + json.dumps(m, ensure_ascii=False, separators=(',', ':')) + ';\n')
    print(f'{len(m)}/{len(phrases)} câu, giọng {VOICE}')
    if len(m) < len(phrases):
        print('Còn thiếu câu, chạy lại workflow để tạo nốt.')

asyncio.run(main())
