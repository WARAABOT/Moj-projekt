# Showreel 2026 — 15 s motion design reel

`showreel.mp4` — 1920×1080, 60 fps, H.264 + AAC stereo, 15 s.

Sve je generisano kodom: grafika je deterministički canvas renderer (`showreel.html`),
a zvuk je proceduralno sintetizovan (`audio.py`) i sinhronizovan sa rezovima.

| Vreme | Scena | Tehnika |
|---|---|---|
| 0.0–2.2 | 01 UVOD | tačka → squash & stretch → linija, maskirani tekst, prstenovi, kružni wipe |
| 2.2–4.7 | 02 FORMA | morfing oblika (krug → kvadrat → trougao → zvezda), talasno polje tačaka sa odbijanjem, eho-kontura, „blow-up” prelaz |
| 4.7–7.2 | 03 TIPOGRAFIJA | kinetička tipografija na ritam, smene boja, marquee zid, slat wipe |
| 7.2–9.8 | 04 PROSTOR | 900 3D čestica: sklapanje u sferu → morf u torus → eksplozija, orbita, HUD očitavanja |
| 9.8–12.3 | 05 PODACI | brojači, bar chart sa overshoot-om, linijski grafikon, progress prsten, dijagonalni wipe |
| 12.3–15.0 | 06 KRAJ | orbitirajući oblici „zaključavaju” logo, završni tekst, push-in |

## Ponovno renderovanje
```bash
python3 audio.py                                  # -> audio.wav
NODE_PATH=$(npm root -g) node render.mjs          # -> showreel.mp4 (Playwright + ffmpeg)
NODE_PATH=$(npm root -g) node render.mjs --stills 1.3,5.6   # pojedinačni kadrovi
```
Otvori `showreel.html` u browseru za pregled u realnom vremenu.
