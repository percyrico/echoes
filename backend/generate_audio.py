#!/usr/bin/env python3
"""Generate missing ambient audio loops for Echoes scenarios."""

import struct
import math
import random
import os
import wave

SAMPLE_RATE = 44100
DURATION = 30
NUM_SAMPLES = SAMPLE_RATE * DURATION
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "audio")


def write_wav(filename: str, samples: list[float]):
    filepath = os.path.join(OUTPUT_DIR, filename)
    int_samples = [int(max(-1.0, min(1.0, s)) * 32767) for s in samples]
    with wave.open(filepath, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        raw = struct.pack(f"<{len(int_samples)}h", *int_samples)
        wf.writeframes(raw)
    print(f"  Written: {filepath}")


def sine(freq, t, phase=0.0):
    return math.sin(2.0 * math.pi * freq * t + phase)


def white_noise():
    return random.uniform(-1.0, 1.0)


def pink_noise_gen():
    max_key = 0x1F
    key = 0
    whites = [random.uniform(-1, 1) for _ in range(6)]
    while True:
        last_key = key
        key = (key + 1) & max_key
        diff = last_key ^ key
        for i in range(6):
            if diff & (1 << i):
                whites[i] = random.uniform(-1, 1)
        yield (sum(whites) + random.uniform(-1, 1)) / 7.0


def lowpass_simple(samples, alpha):
    out = [samples[0]]
    for i in range(1, len(samples)):
        out.append(out[-1] + alpha * (samples[i] - out[-1]))
    return out


def fade_loop(samples, fade_len=4410):
    out = samples[:]
    for i in range(min(fade_len, len(out))):
        f = i / fade_len
        out[i] *= f
        out[-(i + 1)] *= f
    return out


def mix(*tracks):
    length = max(len(t) for t in tracks)
    result = [0.0] * length
    for t in tracks:
        for i in range(len(t)):
            result[i] += t[i]
    peak = max(abs(s) for s in result) or 1.0
    if peak > 1.0:
        result = [s / peak for s in result]
    return result


# ---- New track generators ----

def gen_urgent_pulse():
    """Pulsing rhythmic tension — heartbeat-like with rising urgency."""
    samples = [0.0] * NUM_SAMPLES
    for i in range(NUM_SAMPLES):
        t = i / SAMPLE_RATE
        # Heartbeat pulse at ~100 BPM, accelerating slightly
        bpm = 100 + 20 * (t / DURATION)
        beat_freq = bpm / 60.0
        pulse = max(0, sine(beat_freq, t)) ** 4
        # Low thump
        thump_freq = 50 * math.exp(-((t * beat_freq % 1.0) * 5))
        thump = sine(thump_freq, t) * pulse * 0.4
        # Tension drone
        drone = sine(65, t) * 0.15
        drone += sine(97.5, t) * 0.08
        # High anxiety tone
        anxiety = sine(440 + 30 * sine(0.5, t), t) * 0.04 * (0.5 + 0.5 * sine(2, t))
        samples[i] = thump + drone + anxiety
    return fade_loop(samples)


def gen_dread_low():
    """Deep sub-bass rumble with dissonant undertones — pure dread."""
    samples = [0.0] * NUM_SAMPLES
    for i in range(NUM_SAMPLES):
        t = i / SAMPLE_RATE
        # Sub-bass rumble
        sub = sine(28, t) * 0.3
        sub += sine(29.5, t) * 0.2  # beating creates unease
        # Dissonant overtones
        dis = sine(42, t) * 0.1
        dis += sine(63, t) * 0.08
        # Very slow LFO for breathing effect
        breath = 0.4 + 0.6 * sine(0.08, t)
        # Distant metallic scrape (filtered noise)
        scrape = white_noise() * 0.015 * (0.3 + 0.7 * abs(sine(0.15, t)))
        samples[i] = (sub + dis) * breath + scrape
    samples = lowpass_simple(samples, 0.1)
    return fade_loop(samples)


def gen_revelation_shimmer():
    """Bright ascending tones with crystalline shimmer — the moment of truth."""
    samples = [0.0] * NUM_SAMPLES
    random.seed(99)
    for i in range(NUM_SAMPLES):
        t = i / SAMPLE_RATE
        # Rising pad — major chord that brightens
        base = 220 + 40 * (t / DURATION)  # slowly rising
        pad = sine(base, t) * 0.1
        pad += sine(base * 1.25, t) * 0.08  # major third
        pad += sine(base * 1.5, t) * 0.06   # perfect fifth
        pad += sine(base * 2, t) * 0.04     # octave
        # Shimmer layer
        shimmer = 0.0
        for k in range(4):
            f = 1500 + k * 400
            shimmer += sine(f, t, k * 1.2) * 0.02 * (0.5 + 0.5 * sine(0.4 + k * 0.15, t))
        # Gentle bell hits
        samples[i] = pad + shimmer
    # Add random bell events
    for _ in range(80):
        start = random.randint(0, NUM_SAMPLES - SAMPLE_RATE)
        freq = random.choice([880, 1047, 1319, 1568, 1760])
        bell_len = int(SAMPLE_RATE * 1.2)
        amp = random.uniform(0.04, 0.08)
        for j in range(bell_len):
            if start + j >= NUM_SAMPLES:
                break
            bt = j / SAMPLE_RATE
            env = math.exp(-bt * 3.0)
            samples[start + j] += sine(freq, bt) * env * amp
    return fade_loop(samples)


def gen_last_train_rain():
    """Rain on train windows with rhythmic clatter of wheels on tracks."""
    rain = [white_noise() * 0.2 for _ in range(NUM_SAMPLES)]
    rain = lowpass_simple(rain, 0.06)
    samples = [0.0] * NUM_SAMPLES
    for i in range(NUM_SAMPLES):
        t = i / SAMPLE_RATE
        # Train wheel rhythm — clickety-clack pattern
        wheel_freq = 2.5  # clicks per second
        click_phase = (t * wheel_freq) % 1.0
        if click_phase < 0.05:
            click = white_noise() * 0.15 * math.exp(-click_phase * 40)
        elif 0.25 < click_phase < 0.30:
            click = white_noise() * 0.10 * math.exp(-(click_phase - 0.25) * 40)
        else:
            click = 0
        # Low engine drone
        drone = sine(40, t) * 0.12
        drone += sine(80, t) * 0.06
        # Wind and rain modulation
        wind_mod = 0.7 + 0.3 * sine(0.15, t)
        samples[i] = rain[i] * wind_mod + click + drone
    samples = lowpass_simple(samples, 0.3)
    return fade_loop(samples)


def gen_locked_room_hum():
    """Low resonant hum with ticking clock and creaking wood."""
    samples = [0.0] * NUM_SAMPLES
    random.seed(55)
    for i in range(NUM_SAMPLES):
        t = i / SAMPLE_RATE
        # Room resonance hum
        hum = sine(60, t) * 0.15
        hum += sine(120, t) * 0.05
        hum += sine(90, t) * 0.08
        # Clock tick — every 0.5 seconds
        tick_phase = (t * 2) % 1.0
        if tick_phase < 0.01:
            tick = white_noise() * 0.2 * math.exp(-tick_phase * 200)
        else:
            tick = 0
        # Slow eerie tone
        eerie = sine(185 + 5 * sine(0.1, t), t) * 0.03
        samples[i] = hum + tick + eerie
    # Add random creaks
    for _ in range(30):
        start = random.randint(0, NUM_SAMPLES - int(SAMPLE_RATE * 0.5))
        creak_len = random.randint(2000, 8000)
        freq = random.uniform(200, 600)
        for j in range(creak_len):
            if start + j >= NUM_SAMPLES:
                break
            ct = j / SAMPLE_RATE
            env = math.sin(math.pi * j / creak_len)
            samples[start + j] += sine(freq + 100 * ct, ct) * env * 0.03
    return fade_loop(samples)


def gen_dinner_party_jazz():
    """Soft jazz piano with light brush drums and upright bass."""
    samples = [0.0] * NUM_SAMPLES
    # Jazz piano chords — Dm7, G7, Cmaj7, Am7 progression
    chord_freqs = [
        [293, 349, 440, 523],   # Dm7
        [392, 494, 587, 698],   # G7
        [262, 330, 392, 494],   # Cmaj7
        [220, 262, 330, 415],   # Am7
    ]
    chord_dur = int(SAMPLE_RATE * 3.75)
    for i in range(NUM_SAMPLES):
        t = i / SAMPLE_RATE
        chord_idx = (i // chord_dur) % len(chord_freqs)
        chord = chord_freqs[chord_idx]
        note_t = (i % chord_dur) / SAMPLE_RATE
        env = math.exp(-note_t * 1.0) * 0.08
        piano = 0
        for freq in chord:
            piano += sine(freq, t) * env
            piano += sine(freq * 2, t) * env * 0.1  # harmonic
        # Walking bass
        bass_notes = [147, 165, 131, 110]
        bass_freq = bass_notes[chord_idx]
        bass_env = math.exp(-note_t * 2.0) * 0.15
        bass = sine(bass_freq, t) * bass_env
        bass += sine(bass_freq * 2, t) * bass_env * 0.1
        # Brush cymbal — gentle noise
        brush = white_noise() * 0.02
        samples[i] = piano + bass + brush
    samples = lowpass_simple(samples, 0.25)
    return fade_loop(samples)


def gen_signal_static():
    """Deep space static with alien signal undertones — eerie and rhythmic."""
    samples = [0.0] * NUM_SAMPLES
    pink = pink_noise_gen()
    for i in range(NUM_SAMPLES):
        t = i / SAMPLE_RATE
        # Static layer
        static = next(pink) * 0.15
        # Signal pulse — repeating every 5 seconds (matching loop timer)
        pulse_phase = (t % 5.0) / 5.0
        pulse_env = math.exp(-(pulse_phase - 0.5) ** 2 * 20)
        # Alien signal tones — dissonant, shifting
        signal = sine(317, t) * 0.06 * pulse_env
        signal += sine(421, t) * 0.04 * pulse_env
        signal += sine(563, t) * 0.03 * pulse_env
        # Deep space drone
        drone = sine(35, t) * 0.1
        drone += sine(52, t) * 0.07
        # Slow modulation for breathing-in-space feel
        breath = 0.6 + 0.4 * sine(0.12, t)
        # Digital glitch artifacts every ~8 seconds
        glitch = 0
        if (t % 8.0) < 0.1:
            glitch = white_noise() * 0.3 * math.exp(-(t % 8.0) * 30)
        samples[i] = (static + signal) * breath + drone + glitch
    samples = lowpass_simple(samples, 0.15)
    return fade_loop(samples)


TRACKS = [
    ("urgent_pulse.wav", gen_urgent_pulse),
    ("dread_low.wav", gen_dread_low),
    ("revelation_shimmer.wav", gen_revelation_shimmer),
    ("last_train_rain.wav", gen_last_train_rain),
    ("locked_room_hum.wav", gen_locked_room_hum),
    ("dinner_party_jazz.wav", gen_dinner_party_jazz),
    ("signal_static.wav", gen_signal_static),
]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Generating {len(TRACKS)} new ambient audio tracks for Echoes...")
    print(f"Output: {OUTPUT_DIR}\n")

    for name, gen_func in TRACKS:
        filepath = os.path.join(OUTPUT_DIR, name)
        if os.path.exists(filepath):
            print(f"Skipping {name} (already exists)")
            continue
        print(f"Generating {name}...")
        samples = gen_func()
        write_wav(name, samples)

    print(f"\nDone!")


if __name__ == "__main__":
    main()
