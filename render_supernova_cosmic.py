import subprocess
import math
import numpy as np

AUDIO_FILE = "cancion_con_vientos_suaves.mp3"
OUTPUT_VIDEO = "video_supernova_cosmica.mp4"
FFMPEG = "ffmpeg"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
SAMPLE_RATE = 44100

print("[1/3] Analizando audio FFT de la nueva composición con vientos...")
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

SW, SH = 640, 360
x = np.linspace(-1.777, 1.777, SW, dtype=np.float32)
y = np.linspace(-1.0, 1.0, SH, dtype=np.float32)
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

print("[2/3] Renderizando Supernova Cósmica reactiva en la nube...")
smooth_bass = 0.0

for f in range(total_frames):
    bass = frame_bass[f]
    mid = frame_mid[f]
    treble = frame_treble[f]
    t = f / FPS
    smooth_bass = 0.85 * smooth_bass + 0.15 * bass
    
    # 1. Nebulosa de gases interestelares en rotación
    rot = t * 0.25 + smooth_bass * 0.2
    nebula1 = np.sin(ANGLE * 3.0 + rot - R * 4.0)
    nebula2 = np.cos(ANGLE * 5.0 - rot * 1.5 + R * 6.0)
    nebula = (nebula1 + nebula2) * 0.5 * np.exp(-R * 1.2)
    
    # 2. Núcleo estelar Supernova (Explosión brillante central con los graves)
    core_radius = 0.18 + smooth_bass * 0.45
    core_glow = np.exp(-(R / core_radius) ** 2.2) * (1.2 + smooth_bass * 2.0)
    
    # 3. Rayos de luz / Flares estelares (Resplandor en cruz/estrella)
    rays = (np.abs(np.cos(ANGLE * 4.0 + t * 0.5)) ** 12.0 + np.abs(np.sin(ANGLE * 4.0 - t * 0.5)) ** 12.0)
    rays_glow = rays * np.exp(-R * 2.5) * (0.6 + treble * 1.2)
    
    # 4. Ondas de choque (Shockwaves) cósmicas en expansión
    shock_dist = np.mod(t * 1.2, 2.2)
    shockwave = np.exp(-((R - shock_dist) ** 2) * 80.0) * (0.8 * smooth_bass)
    
    # 5. Anillos de polvo estelar / Disco de acreción
    ring = np.exp(-((R - 0.75 - smooth_bass * 0.15) ** 2) * 45.0) * (0.5 + mid * 0.8)
    
    # Canales de color (Violeta galáctico -> Cyan hiperbrillante -> Oro nuclear)
    r_chan = np.clip(core_glow * 1.0 + nebula * (0.6 + mid * 0.4) + shockwave * 0.8 + rays_glow * 1.2 + ring * 0.4, 0, 1)
    g_chan = np.clip(core_glow * 0.85 + nebula * (0.2 + treble * 0.3) + shockwave * 0.3 + rays_glow * 0.9 + ring * 0.7, 0, 1)
    b_chan = np.clip(core_glow * 1.4 + nebula * (1.0 + smooth_bass * 0.5) + shockwave * 1.4 + rays_glow * 1.5 + ring * 1.1, 0, 1)
    
    # Destellos de estrellas de fondo (Polvo cósmico reactivo a vientos y agudos)
    stars = (np.sin(X * 45.0 + Y * 50.0) * np.cos(X * 30.0 - Y * 40.0) > 0.985).astype(np.float32)
    star_twinkle = stars * (0.5 + treble * 0.8)
    r_chan = np.clip(r_chan + star_twinkle * 0.8, 0, 1)
    g_chan = np.clip(g_chan + star_twinkle * 0.9, 0, 1)
    b_chan = np.clip(b_chan + star_twinkle * 1.0, 0, 1)
    
    rgb = np.stack([(r_chan*255).astype(np.uint8), (g_chan*255).astype(np.uint8), (b_chan*255).astype(np.uint8)], axis=-1)
    proc.stdin.write(rgb.tobytes())
    
    if (f + 1) % 300 == 0 or f == total_frames - 1:
        print(f"  Progreso Supernova: {f+1}/{total_frames} ({(f+1)/total_frames*100:.1f}%)")

proc.stdin.close()
proc.wait()
print("[3/3] ¡Video de Supernova completado exitosamente!")
