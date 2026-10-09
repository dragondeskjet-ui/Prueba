#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>
#include <complex.h>

#define WIDTH 1920
#define HEIGHT 1080
#define FPS 30
#define SAMPLE_RATE 44100
#define FFT_SIZE 2048

#define NUM_PARTICLES 600
#define TRAIL_LEN 16

typedef struct {
    float x, y, z;
} Point3D;

typedef struct {
    Point3D trail[TRAIL_LEN];
    float theta, phi, radius;
    float speed_theta, speed_phi;
    float hue;
    float energy;
} Particle;

static Particle particles[NUM_PARTICLES];
static uint8_t frame_buffer[HEIGHT][WIDTH][3];

// Paleta HSV a RGB rápida para filamentos cósmicos de iTunes/Winamp
void hsv_to_rgb(float h, float s, float v, uint8_t *r, uint8_t *g, uint8_t *b) {
    float c = v * s;
    float x = c * (1.0f - fabsf(fmodf(h * 6.0f, 2.0f) - 1.0f));
    float m = v - c;
    float r1, g1, b1;
    int hi = (int)(h * 6.0f) % 6;
    switch (hi) {
        case 0: r1 = c; g1 = x; b1 = 0; break;
        case 1: r1 = x; g1 = c; b1 = 0; break;
        case 2: r1 = 0; g1 = c; b1 = x; break;
        case 3: r1 = 0; g1 = x; b1 = c; break;
        case 4: r1 = x; g1 = 0; b1 = c; break;
        default: r1 = c; g1 = 0; b1 = x; break;
    }
    *r = (uint8_t)((r1 + m) * 255.0f);
    *g = (uint8_t)((g1 + m) * 255.0f);
    *b = (uint8_t)((b1 + m) * 255.0f);
}

// Pintar pixel aditivo (bloom / plasma)
void blend_pixel(int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x < 0 || x >= WIDTH || y < 0 || y >= HEIGHT) return;
    int nr = (int)frame_buffer[y][x][0] + r;
    int ng = (int)frame_buffer[y][x][1] + g;
    int nb = (int)frame_buffer[y][x][2] + b;
    frame_buffer[y][x][0] = (uint8_t)(nr > 255 ? 255 : nr);
    frame_buffer[y][x][1] = (uint8_t)(ng > 255 ? 255 : ng);
    frame_buffer[y][x][2] = (uint8_t)(nb > 255 ? 255 : nb);
}

// Trazado de línea antialiased rápida para estelas de filamento
void draw_line(int x0, int y0, int x1, int y1, uint8_t r, uint8_t g, uint8_t b) {
    int dx = abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
    int dy = -abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int err = dx + dy, e2;
    while (1) {
        blend_pixel(x0, y0, r, g, b);
        if (x0 == x1 && y0 == y1) break;
        e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

// FFT Cooley-Tukey estándar en C
void fft(float complex *buf, int n) {
    if (n <= 1) return;
    float complex odd[n/2];
    float complex even[n/2];
    for (int i = 0; i < n/2; i++) {
        even[i] = buf[i*2];
        odd[i]  = buf[i*2 + 1];
    }
    fft(even, n/2);
    fft(odd, n/2);
    for (int k = 0; k < n/2; k++) {
        float complex t = cexpf(-2.0f * I * M_PI * k / n) * odd[k];
        buf[k] = even[k] + t;
        buf[k + n/2] = even[k] - t;
    }
}

int main(int argc, char **argv) {
    const char *audio_file = "cancion.mp3";
    const char *output_file = "cancion_itunes_winamp.mp4";

    // 1. Decodificar audio mono a PCM flotante vía FFmpeg pipe
    char cmd_audio[512];
    snprintf(cmd_audio, sizeof(cmd_audio), "/tmp/ffmpeg -i \"%s\" -f f32le -ac 1 -ar %d -", audio_file, SAMPLE_RATE);
    FILE *audio_pipe = popen(cmd_audio, "r");
    if (!audio_pipe) {
        fprintf(stderr, "Error abriendo audio con FFmpeg\n");
        return 1;
    }

    size_t audio_capacity = SAMPLE_RATE * 60;
    float *audio_data = malloc(audio_capacity * sizeof(float));
    size_t total_samples = 0;
    size_t read_now = 0;

    while ((read_now = fread(audio_data + total_samples, sizeof(float), 4096, audio_pipe)) > 0) {
        total_samples += read_now;
        if (total_samples + 4096 >= audio_capacity) {
            audio_capacity *= 2;
            audio_data = realloc(audio_data, audio_capacity * sizeof(float));
        }
    }
    pclose(audio_pipe);

    float duration = (float)total_samples / SAMPLE_RATE;
    int total_frames = (int)(duration * FPS);
    printf("[1/3] Audio decodificado en C: %.2f seg, %d frames a generar.\n", duration, total_frames);

    // 2. Inicializar partículas del campo magnético de iTunes/Magnetosphere
    srand(42);
    for (int i = 0; i < NUM_PARTICLES; i++) {
        particles[i].theta = ((float)rand() / RAND_MAX) * 2.0f * M_PI;
        particles[i].phi = (((float)rand() / RAND_MAX) - 0.5f) * M_PI;
        particles[i].radius = 120.0f + ((float)rand() / RAND_MAX) * 280.0f;
        particles[i].speed_theta = 0.02f + ((float)rand() / RAND_MAX) * 0.05f;
        particles[i].speed_phi = (((float)rand() / RAND_MAX) - 0.5f) * 0.03f;
        particles[i].hue = (float)rand() / RAND_MAX;
        particles[i].energy = 1.0f;
        for (int t = 0; t < TRAIL_LEN; t++) {
            particles[i].trail[t].x = 0;
            particles[i].trail[t].y = 0;
            particles[i].trail[t].z = 0;
        }
    }

    // 3. Abrir pipe de salida para codificación directa en H.264
    char cmd_video[1024];
    snprintf(cmd_video, sizeof(cmd_video),
        "/tmp/ffmpeg -y -f rawvideo -vcodec rawvideo -s %dx%d -pix_fmt rgb24 -r %d -i - "
        "-i \"%s\" -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a aac -b:a 256k -shortest \"%s\"",
        WIDTH, HEIGHT, FPS, audio_file, output_file);

    FILE *video_pipe = popen(cmd_video, "w");
    if (!video_pipe) {
        fprintf(stderr, "Error inicializando pipe de FFmpeg para video\n");
        return 1;
    }

    printf("[2/3] Renderizando visualizador en C (Magnetosphere / MilkDrop plasma)...\n");

    float complex fft_buf[FFT_SIZE];
    float smooth_bass = 0.0f;

    for (int f = 0; f < total_frames; f++) {
        // Extraer ventana FFT
        int center_idx = (int)(((float)f / FPS) * SAMPLE_RATE);
        int start_idx = center_idx - FFT_SIZE / 2;
        
        for (int i = 0; i < FFT_SIZE; i++) {
            int idx = start_idx + i;
            if (idx >= 0 && idx < total_samples) {
                float hanning = 0.5f * (1.0f - cosf(2.0f * M_PI * i / (FFT_SIZE - 1)));
                fft_buf[i] = audio_data[idx] * hanning;
            } else {
                fft_buf[i] = 0;
            }
        }
        fft(fft_buf, FFT_SIZE);

        // Medir graves (bass 20-200Hz) y agudos (treble 3000-10000Hz)
        float bass_sum = 0.0f, treble_sum = 0.0f;
        for (int i = 2; i < 12; i++) bass_sum += cabsf(fft_buf[i]);
        for (int i = 120; i < 350; i++) treble_sum += cabsf(fft_buf[i]);
        
        float bass = bass_sum / 10.0f;
        float treble = treble_sum / 230.0f;
        if (bass > 2.0f) bass = 2.0f;
        if (treble > 2.0f) treble = 2.0f;

        smooth_bass = 0.82f * smooth_bass + 0.18f * bass;

        // Limpiar frame buffer con desvanecimiento cósmico
        for (int y = 0; y < HEIGHT; y++) {
            for (int x = 0; x < WIDTH; x++) {
                frame_buffer[y][x][0] = 5;
                frame_buffer[y][x][1] = 4;
                frame_buffer[y][x][2] = 10;
            }
        }

        // Centro y rotación global de cámara
        float time_sec = (float)f / FPS;
        float cam_rot_y = time_sec * 0.35f;
        float cam_rot_x = sinf(time_sec * 0.25f) * 0.2f;

        int cx = WIDTH / 2;
        int cy = HEIGHT / 2;

        // 4. Dibujar filamentos magnéticos y partículas de Magnetosphere
        for (int i = 0; i < NUM_PARTICLES; i++) {
            Particle *p = &particles[i];

            // Física del campo magnético dipolar
            p->theta += p->speed_theta * (1.0f + smooth_bass * 2.2f);
            p->phi += p->speed_phi * (1.0f + treble * 1.8f);

            float r = p->radius * (1.0f + smooth_bass * 0.45f);
            
            // Ecuaciones de toroide magnético (dipolo de Magnetosphere)
            float x3 = r * sinf(p->theta) * cosf(p->phi);
            float y3 = r * sinf(p->phi) * 1.35f + sinf(p->theta * 3.0f + time_sec * 4.0f) * (treble * 35.0f);
            float z3 = r * cosf(p->theta) * cosf(p->phi);

            // Rotación 3D
            float x_rot = x3 * cosf(cam_rot_y) - z3 * sinf(cam_rot_y);
            float z_rot = x3 * sinf(cam_rot_y) + z3 * cosf(cam_rot_y);
            float y_rot = y3 * cosf(cam_rot_x) - z_rot * sinf(cam_rot_x);
            z_rot = y3 * sinf(cam_rot_x) + z_rot * cosf(cam_rot_x);

            // Proyección en perspectiva 3D
            float fov = 750.0f;
            float z_proj = z_rot + 600.0f;
            if (z_proj < 50.0f) z_proj = 50.0f;

            int px = cx + (int)((x_rot * fov) / z_proj);
            int py = cy + (int)((y_rot * fov) / z_proj);

            // Desplazar estela
            for (int t = TRAIL_LEN - 1; t > 0; t--) {
                p->trail[t] = p->trail[t - 1];
            }
            p->trail[0].x = px;
            p->trail[0].y = py;
            p->trail[0].z = z_proj;

            // Dibujar cinta/estela de plasma (Ribbon)
            float hue = fmodf(p->hue + time_sec * 0.08f + smooth_bass * 0.15f, 1.0f);
            for (int t = 0; t < TRAIL_LEN - 1; t++) {
                if (p->trail[t + 1].z <= 0) break;
                float trail_fade = (1.0f - (float)t / TRAIL_LEN);
                uint8_t cr, cg, cb;
                hsv_to_rgb(hue, 0.85f, trail_fade * (0.6f + smooth_bass * 0.4f), &cr, &cg, &cb);
                draw_line((int)p->trail[t].x, (int)p->trail[t].y,
                          (int)p->trail[t + 1].x, (int)p->trail[t + 1].y,
                          cr, cg, cb);
            }

            // Destello en la cabeza del filamento
            uint8_t hr, hg, hb;
            hsv_to_rgb(hue, 0.2f, 1.0f, &hr, &hg, &hb);
            blend_pixel(px, py, hr, hg, hb);
            blend_pixel(px + 1, py, hr/2, hg/2, hb/2);
            blend_pixel(px - 1, py, hr/2, hg/2, hb/2);
            blend_pixel(px, py + 1, hr/2, hg/2, hb/2);
            blend_pixel(px, py - 1, hr/2, hg/2, hb/2);
        }

        // 5. Núcleo central pulsante (Singularidad magnética)
        int core_r = (int)(25.0f + smooth_bass * 40.0f);
        for (int dy = -core_r; dy <= core_r; dy++) {
            for (int dx = -core_r; dx <= core_r; dx++) {
                float dist = sqrtf(dx*dx + dy*dy);
                if (dist <= core_r) {
                    float glow = 1.0f - (dist / core_r);
                    glow = powf(glow, 2.0f);
                    uint8_t cr = (uint8_t)(glow * 120 * smooth_bass);
                    uint8_t cg = (uint8_t)(glow * 210 * smooth_bass);
                    uint8_t cb = (uint8_t)(glow * 255);
                    blend_pixel(cx + dx, cy + dy, cr, cg, cb);
                }
            }
        }

        // Enviar fotograma a FFmpeg
        fwrite(frame_buffer, 1, WIDTH * HEIGHT * 3, video_pipe);

        if ((f + 1) % 200 == 0 || f == total_frames - 1) {
            printf("  Progreso C: %d/%d frames (%.1f%%)\n", f + 1, total_frames, (float)(f + 1) / total_frames * 100.0f);
        }
    }

    pclose(video_pipe);
    free(audio_data);
    printf("[3/3] ¡Completado exitosamente en C!\n");
    return 0;
}
