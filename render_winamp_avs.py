import subprocess
import math
import numpy as np

AUDIO_FILE = "cancion_con_vientos_suaves.mp3"
OUTPUT_VIDEO = "video_winamp_avs_classic.mp4"
FFMPEG = "ffmpeg"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
SAMPLE_RATE = 44100

print("[1/3] Decodificando audio y extrayendo FFT para AVS...")
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
frame_wave = []

for f in range(total_frames):
    c_idx = int((f / FPS) * SAMPLE_RATE)
    start_idx = max(0, c_idx - N_FFT // 2)
    end_idx = min(len(audio), c_idx + N_FFT // 2)
    chunk = np.zeros(N_FFT, dtype=np.float32)
    avail = audio[start_idx:end_idx]
    chunk[:len(avail)] = avail * np.hanning(len(avail))
    
    # Onda temporal sin filtrar para osciloscopio AVS
    wave_chunk = np.zeros(512, dtype=np.float32)
    w_avail = audio[c_idx:min(len(audio), c_idx + 512)]
    wave_chunk[:len(w_avail)] = w_avail
    frame_wave.append(wave_chunk)
    
    fft_vals = np.abs(np.fft.rfft(chunk))
    freqs = np.fft.rfftfreq(N_FFT, 1.0 / SAMPLE_RATE)
    
    b_mask = (freqs >= 20) & (freqs < 220)
    m_mask = (freqs >= 220) & (freqs < 2800)
    t_mask = (freqs >= 2800) & (freqs < 12000)
    
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

# Grid interno para el motor de feedback / buffer de estelas AVS
W, H = 960, 540
cx, cy = W // 2, H // 2

ffmpeg_cmd = [
    FFMPEG, '-y',
    '-f', 'rawvideo',
    '-vcodec', 'rawvideo',
    '-s', f'{W}x{H}',
    '-pix_fmt', 'rgb24',
    '-r', str(FPS),
    '-i', '-',
    '-i', AUDIO_FILE,
    '-vf', 'scale=1920:1080:flags=neighbor',
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

print("[2/3] Renderizando motor clásico Winamp AVS (Advanced Visualization Studio)...")

# Buffer de persistencia / video feedback clásico de AVS
trail_buffer = np.zeros((H, W, 3), dtype=np.float32)

def draw_line_aa(buf, x0, y0, x1, y1, color):
    # DDA para líneas láser vectoriales rápidas
    dx = x1 - x0
    dy = y1 - y0
    steps = int(max(abs(dx), abs(dy)))
    if steps == 0: return
    x_inc = dx / steps
    y_inc = dy / steps
    x, y = float(x0), float(y0)
    for _ in range(steps):
        ix, iy = int(x), int(y)
        if 0 <= ix < W and 0 <= iy < H:
            buf[iy, ix] = np.clip(buf[iy, ix] + color, 0.0, 1.0)
        x += x_inc
        y += y_inc

for f in range(total_frames):
    bass = frame_bass[f]
    mid = frame_mid[f]
    treble = frame_treble[f]
    wave = frame_wave[f]
    t = f / FPS
    
    # 1. Efecto AVS "Trans / Movement & Fadeout" (Feedback con ligero zoom y rotación)
    # Factor de decay característico de AVS (0.88 - 0.92)
    decay = 0.88 + bass * 0.05
    trail_buffer *= decay
    
    # 2. AVS "SuperScope": Láser vectorial paramétrico en espiral / flor matemática
    # Ecuaciones canónicas de los presets de Justin Frankel (Nullsoft AVS)
    num_points = 180
    scope_pts = []
    laser_hue = (t * 0.15 + bass * 0.1) % 1.0
    
    # Colores láser neón (Cian, Magenta, Verde fósforo)
    col_r = 0.5 + 0.5 * math.sin(laser_hue * 6.28)
    col_g = 0.5 + 0.5 * math.sin(laser_hue * 6.28 + 2.09)
    col_b = 0.5 + 0.5 * math.sin(laser_hue * 6.28 + 4.18)
    laser_color = np.array([col_r, col_g, col_b], dtype=np.float32) * (0.8 + treble * 0.4)
    
    # Rotación dinámica de la figura vectorial
    angle_offset = t * 1.5 + bass * 0.8
    scale_radius = 120.0 + bass * 90.0
    
    for i in range(num_points):
        p = i / float(num_points)
        ang = p * math.pi * 2.0 * 3.0 + angle_offset # 3 bucles
        
        # Audio reactivo en cada vértice
        audio_mod = wave[int(p * (len(wave) - 1))] * (60.0 + mid * 80.0)
        r = scale_radius * math.sin(p * math.pi * 5.0) + audio_mod
        
        px = cx + int(r * math.cos(ang))
        py = cy + int(r * math.sin(ang))
        scope_pts.append((px, py))
        
    for i in range(len(scope_pts) - 1):
        draw_line_aa(trail_buffer, scope_pts[i][0], scope_pts[i][1], 
                     scope_pts[i+1][0], scope_pts[i+1][1], laser_color)
                     
    # 3. AVS "Oscilloscope Star / Dot Tunnel" en el centro
    star_pts = 64
    for i in range(star_pts):
        sang = (i / star_pts) * 2.0 * math.pi - t * 2.0
        srad = (25.0 + (wave[i % len(wave)] * 35.0)) * (1.0 + bass * 0.5)
        sx = cx + int(srad * math.cos(sang))
        sy = cy + int(srad * math.sin(sang))
        if 0 <= sx < W and 0 <= sy < H:
            trail_buffer[sy, sx] = np.array([1.0, 1.0, 1.0], dtype=np.float32)
            
    # 4. AVS "Ring Pulse" (Anillo que explota con cada golpe del bajo)
    if bass > 0.65:
        ring_r = int((t * 280.0) % 240.0)
        ring_col = np.array([col_b, col_r, col_g], dtype=np.float32) * 0.4
        for deg in range(0, 360, 4):
            rad = math.radians(deg)
            rx = cx + int(ring_r * math.cos(rad))
            ry = cy + int(ring_r * math.sin(rad))
            if 0 <= rx < W and 0 <= ry < H:
                trail_buffer[ry, rx] = np.clip(trail_buffer[ry, rx] + ring_col, 0.0, 1.0)
                
    # Salida RGB a FFmpeg
    frame_out = (np.clip(trail_buffer, 0.0, 1.0) * 255.0).astype(np.uint8)
    proc.stdin.write(frame_out.tobytes())
    
    if (f + 1) % 300 == 0 or f == total_frames - 1:
        print(f"  Progreso AVS: {f+1}/{total_frames} ({(f+1)/total_frames*100:.1f}%)")

proc.stdin.close()
proc.wait()
print("[3/3] ¡Video clásico de Winamp AVS generado exitosamente!")
