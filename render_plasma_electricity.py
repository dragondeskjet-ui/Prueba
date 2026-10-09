import subprocess
import math
import numpy as np

AUDIO_FILE = "cancion.mp3"
OUTPUT_VIDEO = "video_3_plasma_electricity.mp4"
FFMPEG = "ffmpeg"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
SAMPLE_RATE = 44100

print("[1/3] FFT Audio...")
cmd = [FFMPEG, '-i', AUDIO_FILE, '-f', 'f32le', '-ac', '1', '-ar', str(SAMPLE_RATE), '-']
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
raw = p.stdout.read()
audio = np.frombuffer(raw, dtype=np.float32)
duration = len(audio) / SAMPLE_RATE
total_frames = int(duration * FPS)

N_FFT = 2048
frame_bass = np.zeros(total_frames)
frame_mid = np.zeros(total_frames)
frame_treble = np.zeros(total_frames)

for f in range(total_frames):
    c_idx = int((f / FPS) * SAMPLE_RATE)
    start_idx = max(0, c_idx - N_FFT // 2)
    end_idx = min(len(audio), c_idx + N_FFT // 2)
    chunk = np.zeros(N_FFT, dtype=np.float32)
    avail = audio[start_idx:end_idx]
    chunk[:len(avail)] = avail * np.hanning(len(avail))
    fft_vals = np.abs(np.fft.rfft(chunk))
    freqs = np.fft.rfftfreq(N_FFT, 1.0 / SAMPLE_RATE)
    
    b_mask = (freqs >= 20) & (freqs < 220)
    m_mask = (freqs >= 220) & (freqs < 2600)
    t_mask = (freqs >= 2600) & (freqs < 12000)
    
    frame_bass[f] = np.mean(fft_vals[b_mask]) if np.any(b_mask) else 0
    frame_mid[f] = np.mean(fft_vals[m_mask]) if np.any(m_mask) else 0
    frame_treble[f] = np.mean(fft_vals[t_mask]) if np.any(t_mask) else 0

def norm(arr):
    p98 = np.percentile(arr, 98)
    if p98 > 0: arr = np.clip(arr / p98, 0, 1.8)
    kernel = np.array([0.15, 0.7, 0.15])
    return np.convolve(arr, kernel, mode='same')

frame_bass = norm(frame_bass)
frame_mid = norm(frame_mid)
frame_treble = norm(frame_treble)

SW, SH = 640, 360
x = np.linspace(-2.5, 2.5, SW, dtype=np.float32)
y = np.linspace(-1.4, 1.4, SH, dtype=np.float32)
X, Y = np.meshgrid(x, y)

ffmpeg_cmd = [
    FFMPEG, '-y',
    '-f', 'rawvideo',
    '-vcodec', 'rawvideo',
    '-s', f'{SW}x{SH}',
    '-pix_fmt', 'rgb24',
    '-r', str(FPS),
    '-i', '-',
    '-i', AUDIO_FILE,
    '-vf', 'scale=1920:1080:flags=lanczos',
    '-c:v', 'libx264',
    '-preset', 'fast',
    '-crf', '18',
    '-pix_fmt', 'yuv420p',
    '-c:a', 'aac',
    '-b:a', '256k',
    '-shortest',
    OUTPUT_VIDEO
]
proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

print("[2/3] Generando Video 3: Plasma Líquido y Ondas Eléctricas...")

for f in range(total_frames):
    bass = frame_bass[f]
    mid = frame_mid[f]
    treble = frame_treble[f]
    t = f / FPS
    
    # Ondas de plasma superpuestas
    p1 = np.sin(X * 3.0 + t * 4.0 + np.cos(Y * 2.0 + t * 2.5))
    p2 = np.cos(Y * 4.0 - t * 3.0 + np.sin(X * 2.5 - t * 2.0))
    p3 = np.sin(np.sqrt((X + np.sin(t*2.0)*0.5)**2 + (Y + np.cos(t*1.5)*0.5)**2) * (8.0 + bass * 8.0) - t * 6.0)
    
    plasma = (p1 + p2 + p3) / 3.0
    
    # Ondas de arco eléctrico horizontales
    electric_arc = np.exp(-((Y - np.sin(X * 6.0 + t * 12.0) * (0.35 + mid * 0.45))**2) * (60.0 + bass * 50.0))
    electric_arc2 = np.exp(-((Y - np.cos(X * 8.0 - t * 15.0) * (0.25 + treble * 0.35))**2) * (80.0 + treble * 60.0))
    
    # Canales de color neón eléctrico vivo
    r_chan = np.clip((np.sin(plasma * np.pi + t * 2.0) * 0.5 + 0.5) * (0.4 + bass * 0.6) + electric_arc * 0.9 + electric_arc2 * 1.2, 0, 1)
    g_chan = np.clip((np.sin(plasma * np.pi + t * 2.0 + 2.094) * 0.5 + 0.5) * (0.3 + mid * 0.5) + electric_arc * 0.4 + electric_arc2 * 0.8, 0, 1)
    b_chan = np.clip((np.sin(plasma * np.pi + t * 2.0 + 4.188) * 0.5 + 0.5) * (0.7 + treble * 0.5) + electric_arc * 1.3 + electric_arc2 * 0.3, 0, 1)
    
    rgb = np.stack([(r_chan*255).astype(np.uint8), (g_chan*255).astype(np.uint8), (b_chan*255).astype(np.uint8)], axis=-1)
    proc.stdin.write(rgb.tobytes())
    
    if (f + 1) % 300 == 0 or f == total_frames - 1:
        print(f"  Progreso Video 3: {f+1}/{total_frames} ({(f+1)/total_frames*100:.1f}%)")

proc.stdin.close()
proc.wait()
print("[3/3] ¡Video 3 generado!")
