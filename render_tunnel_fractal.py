import subprocess
import math
import numpy as np

AUDIO_FILE = "cancion.mp3"
OUTPUT_VIDEO = "video_2_tunnel_fractal.mp4"
FFMPEG = "ffmpeg"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
SAMPLE_RATE = 44100

print("[1/3] Extrayendo audio FFT...")
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
    
    b_mask = (freqs >= 20) & (freqs < 200)
    m_mask = (freqs >= 200) & (freqs < 2500)
    t_mask = (freqs >= 2500) & (freqs < 12000)
    
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

# Grid de coordenadas normalizadas en cuadrícula
SW, SH = 480, 270 # renderizado base para shader fractal ultra-smooth con escalado rápido
x = np.linspace(-1.0, 1.0, SW, dtype=np.float32)
y = np.linspace(-0.5625, 0.5625, SH, dtype=np.float32)
X, Y = np.meshgrid(x, y)
R = np.sqrt(X*X + Y*Y) + 1e-5
ANGLE = np.arctan2(Y, X)

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

print("[2/3] Generando Video 2: Túnel Fractal Hipnótico...")
rot = 0.0
depth = 0.0

for f in range(total_frames):
    bass = frame_bass[f]
    mid = frame_mid[f]
    treble = frame_treble[f]
    t = f / FPS
    
    depth += 0.04 + bass * 0.12
    rot += 0.02 + treble * 0.06
    
    # Coordenadas polares de túnel fractal infinito
    u = (1.0 / (R + 0.18 * np.sin(ANGLE * 6.0 + rot))) + depth
    v = (ANGLE * 3.0 / np.pi) + np.sin(depth * 0.8) * 0.5
    
    # Patrón caleidoscópico / fractal
    pattern1 = np.sin(u * 8.0) * np.cos(v * 8.0)
    pattern2 = np.sin(u * 16.0 + ANGLE * 4.0) * np.sin(v * 16.0)
    kaleido = pattern1 * 0.6 + pattern2 * 0.4
    
    # Pulso central de choque
    pulse = np.exp(-R * (3.5 - bass * 1.5))
    
    # Canales de color (Gradiente psicodélico neón Winamp)
    r_chan = np.clip((np.sin(u * 3.0 + t * 2.0) * 0.5 + 0.5) * (kaleido + 0.5) + pulse * 1.2 * bass, 0, 1)
    g_chan = np.clip((np.sin(v * 4.0 + t * 1.5 + 2.094) * 0.5 + 0.5) * (kaleido + 0.5) + pulse * 0.8 * mid, 0, 1)
    b_chan = np.clip((np.sin(u * 2.0 + v * 2.0 + 4.188) * 0.5 + 0.5) * (kaleido + 0.5) + pulse * 1.5 * treble, 0, 1)
    
    # Vignette suave
    vignette = np.clip(1.2 - R * 0.7, 0, 1)
    r_chan = (r_chan * vignette * 255).astype(np.uint8)
    g_chan = (g_chan * vignette * 255).astype(np.uint8)
    b_chan = (b_chan * vignette * 255).astype(np.uint8)
    
    rgb = np.stack([r_chan, g_chan, b_chan], axis=-1)
    proc.stdin.write(rgb.tobytes())
    
    if (f + 1) % 250 == 0 or f == total_frames - 1:
        print(f"  Progreso Video 2: {f+1}/{total_frames} ({(f+1)/total_frames*100:.1f}%)")

proc.stdin.close()
proc.wait()
print("[3/3] ¡Video 2 generado!")
