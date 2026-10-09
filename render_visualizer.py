import subprocess
import math
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

AUDIO_FILE = "cancion.mp3"
OUTPUT_VIDEO = "cancion_visualizer_superproducido.mp4"
FFMPEG = "/tmp/ffmpeg"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
SAMPLE_RATE = 44100

print("[1/5] Decodificando audio...")
cmd = [FFMPEG, '-i', AUDIO_FILE, '-f', 'f32le', '-ac', '1', '-ar', str(SAMPLE_RATE), '-']
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
raw = p.stdout.read()
audio = np.frombuffer(raw, dtype=np.float32)
duration = len(audio) / SAMPLE_RATE
total_frames = int(duration * FPS)

print(f"  Duración: {duration:.2f}s | Total frames: {total_frames}")

# Precomputar análisis espectral por frame
print("[2/5] Analizando frecuencias y beats...")
N_FFT = 2048
N_BANDS = 72

frame_bass = np.zeros(total_frames)
frame_mid = np.zeros(total_frames)
frame_treble = np.zeros(total_frames)
frame_energy = np.zeros(total_frames)
frame_spectrum = np.zeros((total_frames, N_BANDS))

for f in range(total_frames):
    center_idx = int((f / FPS) * SAMPLE_RATE)
    start_idx = max(0, center_idx - N_FFT // 2)
    end_idx = min(len(audio), center_idx + N_FFT // 2)
    chunk = np.zeros(N_FFT, dtype=np.float32)
    avail = audio[start_idx:end_idx]
    chunk[:len(avail)] = avail * np.hanning(len(avail))
    
    fft_vals = np.abs(np.fft.rfft(chunk))
    freqs = np.fft.rfftfreq(N_FFT, 1.0 / SAMPLE_RATE)
    
    # Bass: 20-250 Hz
    b_mask = (freqs >= 20) & (freqs < 250)
    frame_bass[f] = np.mean(fft_vals[b_mask]) if np.any(b_mask) else 0
    # Mid: 250-2500 Hz
    m_mask = (freqs >= 250) & (freqs < 2500)
    frame_mid[f] = np.mean(fft_vals[m_mask]) if np.any(m_mask) else 0
    # Treble: 2500-12000 Hz
    t_mask = (freqs >= 2500) & (freqs < 12000)
    frame_treble[f] = np.mean(fft_vals[t_mask]) if np.any(t_mask) else 0
    
    frame_energy[f] = np.sum(fft_vals**2)
    
    # Log bands for circular spectrum
    log_freqs = np.geomspace(30, 14000, N_BANDS + 1)
    for b in range(N_BANDS):
        band_mask = (freqs >= log_freqs[b]) & (freqs < log_freqs[b+1])
        if np.any(band_mask):
            frame_spectrum[f, b] = np.mean(fft_vals[band_mask])

# Normalizar y suavizar curvas
def normalize_and_smooth(arr, p=98):
    scale = np.percentile(arr, p)
    if scale > 0:
        arr = np.clip(arr / scale, 0, 1.5)
    kernel = np.array([0.1, 0.25, 0.3, 0.25, 0.1])
    return np.convolve(arr, kernel, mode='same')

frame_bass = normalize_and_smooth(frame_bass)
frame_mid = normalize_and_smooth(frame_mid)
frame_treble = normalize_and_smooth(frame_treble)
max_spec = np.percentile(frame_spectrum, 98)
if max_spec > 0:
    frame_spectrum = np.clip(frame_spectrum / max_spec, 0, 1.6)

print("[3/5] Inicializando simulación de partículas y renderizador...")

# Sistema de partículas 3D / túnel
NUM_PARTICLES = 240
np.random.seed(42)
particles_z = np.random.uniform(0.5, 10.0, NUM_PARTICLES)
particles_angle = np.random.uniform(0, 2 * np.pi, NUM_PARTICLES)
particles_radius = np.random.uniform(80, 520, NUM_PARTICLES)
particles_speed = np.random.uniform(0.04, 0.12, NUM_PARTICLES)
particles_hue = np.random.uniform(0, 1, NUM_PARTICLES)

CX, CY = WIDTH // 2, HEIGHT // 2
BASE_RADIUS = 160

# Iniciar proceso ffmpeg para codificación directa vía stdin
ffmpeg_cmd = [
    FFMPEG, '-y',
    '-f', 'rawvideo',
    '-vcodec', 'rawvideo',
    '-s', f'{WIDTH}x{HEIGHT}',
    '-pix_fmt', 'rgb24',
    '-r', str(FPS),
    '-i', '-',
    '-i', AUDIO_FILE,
    '-c:v', 'libx264',
    '-preset', 'medium',
    '-crf', '18',
    '-pix_fmt', 'yuv420p',
    '-c:a', 'aac',
    '-b:a', '256k',
    '-shortest',
    OUTPUT_VIDEO
]

proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

def get_neon_color(phase, amp=1.0):
    # Genera colores ciberpunk dinámicos (Cyan -> Magenta -> Violeta -> Eléctrico)
    r = int((0.5 + 0.5 * math.sin(phase)) * 255 * amp)
    g = int((0.5 + 0.5 * math.sin(phase + 2.094)) * 255 * amp * 0.75)
    b = int((0.5 + 0.5 * math.sin(phase + 4.188)) * 255 * amp)
    return (min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)))

print("[4/5] Renderizando video con efectos de alta fidelidad...")

smooth_bass_pulse = 0.0

for f in range(total_frames):
    bass = frame_bass[f]
    mid = frame_mid[f]
    treble = frame_treble[f]
    spec = frame_spectrum[f]
    t = f / FPS
    
    # Bass shockwave & pulse
    smooth_bass_pulse = 0.85 * smooth_bass_pulse + 0.15 * bass
    core_r = BASE_RADIUS + smooth_bass_pulse * 48
    
    # Lienzo principal
    img = Image.new('RGB', (WIDTH, HEIGHT), (6, 5, 12))
    draw = ImageDraw.Draw(img)
    
    # 1. Fondo de estrellas / túnel estelar con profundidad Z
    particles_z -= particles_speed * (1.0 + bass * 2.2)
    respawn = particles_z <= 0.2
    particles_z[respawn] = np.random.uniform(8.0, 10.0, np.sum(respawn))
    particles_radius[respawn] = np.random.uniform(80, 520, np.sum(respawn))
    
    p_k = 400.0 / particles_z
    px = CX + np.cos(particles_angle + t * 0.2) * particles_radius * (p_k / 100.0)
    py = CY + np.sin(particles_angle + t * 0.2) * particles_radius * (p_k / 100.0)
    
    for i in range(NUM_PARTICLES):
        if 0 <= px[i] < WIDTH and 0 <= py[i] < HEIGHT:
            size = max(1, int(p_k[i] * 0.035 * (1.0 + treble * 0.8)))
            alpha_val = min(1.0, max(0.1, 1.2 - particles_z[i] / 8.0))
            col = get_neon_color(particles_hue[i] * 6.28 + t, alpha_val)
            draw.ellipse((px[i] - size, py[i] - size, px[i] + size, py[i] + size), fill=col)
    
    # 2. Rejilla de perspectiva Synthwave en la base inferior
    grid_y_start = int(HEIGHT * 0.72)
    horizon_c = (int(40 + bass * 80), int(10 + mid * 30), int(80 + treble * 100))
    for gy in range(grid_y_start, HEIGHT, 24):
        draw.line([(0, gy), (WIDTH, gy)], fill=(horizon_c[0]//3, horizon_c[1]//3, horizon_c[2]//2), width=1)
    
    for gx in range(0, WIDTH + 1, 120):
        # Perspectiva radial desde el horizonte central
        draw.line([(CX + (gx - CX) * 0.1, grid_y_start), (gx, HEIGHT)], 
                  fill=(horizon_c[0]//4, horizon_c[1]//4, horizon_c[2]//3), width=1)
        
    # 3. Ondas de Choque (Bass Shockwaves) expansivas
    if bass > 0.7:
        shock_r = core_r + (t * 400 % 350)
        draw.ellipse((CX - shock_r, CY - shock_r, CX + shock_r, CY + shock_r), 
                     outline=(int(180 * bass), 40, int(255 * bass)), width=2)

    # 4. Espectro Radial Reactivo (Visualizador Circular estilo BeatDrop)
    # Dibujar barras y polígono conectados
    poly_outer = []
    poly_inner = []
    
    rot_offset = t * 0.5
    for b in range(N_BANDS):
        ang = (b / N_BANDS) * 2 * math.pi + rot_offset
        bar_val = spec[b]
        bar_len = bar_val * 140.0 + smooth_bass_pulse * 30.0
        
        # Color degradado en función del ángulo y frecuencia
        hue = (b / N_BANDS) * 4.0 + t * 0.8
        bar_col = get_neon_color(hue, 1.0)
        
        x0 = CX + math.cos(ang) * (core_r + 4)
        y0 = CY + math.sin(ang) * (core_r + 4)
        x1 = CX + math.cos(ang) * (core_r + 8 + bar_len)
        y1 = CY + math.sin(ang) * (core_r + 8 + bar_len)
        
        poly_outer.append((x1, y1))
        
        # Barras de neón radiales
        draw.line([(x0, y0), (x1, y1)], fill=bar_col, width=3)
        
        # Partículas de agudos en las puntas (treble sparks)
        if bar_val > 0.85:
            spark_x = CX + math.cos(ang) * (core_r + 14 + bar_len)
            spark_y = CY + math.sin(ang) * (core_r + 14 + bar_len)
            draw.ellipse((spark_x - 2, spark_y - 2, spark_x + 2, spark_y + 2), fill=(255, 255, 255))
            
    # Polígono perimetral que une los picos
    if len(poly_outer) > 2:
        poly_outer.append(poly_outer[0])
        draw.line(poly_outer, fill=(0, 240, 255), width=2)
        
    # 5. Anillos orbitales concéntricos con rotación giroscópica
    for ring_i, (rx, ry, r_speed, r_color) in enumerate([
        (core_r - 20, core_r - 20, 1.2, (255, 0, 128)),
        (core_r - 35, core_r - 35, -1.8, (0, 230, 255)),
        (core_r + 25, core_r + 25, 0.8, (180, 80, 255))
    ]):
        start_deg = math.degrees(t * r_speed)
        draw.arc((CX - rx, CY - ry, CX + rx, CY + ry), 
                 start=start_deg, end=start_deg + 210, fill=r_color, width=2)
                 
    # 6. Núcleo reactivo central (Glowing Core & Glassmorphism)
    core_inner_r = max(20, int(core_r * 0.72))
    core_col = (int(20 + bass * 40), int(10 + mid * 20), int(35 + bass * 60))
    draw.ellipse((CX - core_inner_r, CY - core_inner_r, CX + core_inner_r, CY + core_inner_r), 
                 fill=core_col, outline=(0, 255, 240), width=3)
                 
    # Ondas de osciloscopio internas en el núcleo
    num_osc = 32
    osc_points = []
    for oi in range(num_osc):
        ox = (CX - core_inner_r + 15) + (oi / (num_osc - 1)) * (2 * core_inner_r - 30)
        osc_ang = oi * 0.4 + t * 8.0
        oy = CY + math.sin(osc_ang) * (mid * 28.0 + 4.0)
        osc_points.append((ox, oy))
    if len(osc_points) > 1:
        draw.line(osc_points, fill=(255, 255, 255), width=2)

    # 7. Viñeta cinematográfica en los bordes
    # Enviar frame directamente a ffmpeg
    proc.stdin.write(img.tobytes())
    
    if (f + 1) % 150 == 0 or f == total_frames - 1:
        print(f"  Progreso: {f + 1}/{total_frames} frames ({(f + 1)/total_frames*100:.1f}%)")

proc.stdin.close()
proc.wait()
print("[5/5] ¡Renderizado completado con éxito!")
