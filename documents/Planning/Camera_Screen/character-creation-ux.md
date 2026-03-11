# Character Creation UX

## Overview
The character creation flow is the core gameplay loop: users scan barcodes to generate collectible creatures. This document covers the camera modal, pack-opening video, and character reveal screens.

## Flow: `idle → scanning → generating → reveal → idle`

### Idle State (Character Creator Tab)
- Usage bar showing "X of Y creations used this month"
- Stats from collection: total creatures, rarity distribution, top biomes
- "Create New Character" button (disabled when limit reached)

### Scanning State
- `<Modal>` slides up covering bottom 75% of screen
- `Character_Creator_Frame.png` as ornate border overlay
- Camera renders inside the arch opening
- Corner indicators for scan targeting
- Debounce prevents double-scan
- Top 25% is dismissible backdrop

### Generating State
- `pack-opening.mp4` plays fullscreen via expo-av Video
- `generateCreature()` API call runs simultaneously
- Video masks LLM/generation latency
- Transition to reveal when both video ends AND creature data arrives
- If API returns first: wait for video. If video ends first: show brief loading indicator.

### Reveal State
- Full-screen overlay with `Character_Reveal.png` background
- Character image (placeholder for now) with edge-bleed gradients
- `Character_Creator_Text_Panel.png` for text overlay
- Shows: name, title, rarity, stats, discovery status
- "Add to Collection" dismiss button

## Key Components
| Component | File | Purpose |
|-----------|------|---------|
| CreationCameraModal | `components/CreationCameraModal.tsx` | Camera in modal overlay |
| PackOpeningVideo | `components/PackOpeningVideo.tsx` | Video during generation |
| CharacterReveal | `components/CharacterReveal.tsx` | Creature reveal overlay |

## Assets
- `assets/images/character_creator/Character_Creator_Frame.png` — Ornate arch frame
- `assets/images/character_creator/Character_Reveal.png` — Forest clearing background
- `assets/images/character_creator/Character_Creator_Text_Panel.png` — Gold-framed text panel
- `assets/images/character_creator/pack-opening.mp4` — Pack opening video
- `assets/images/card_designs/test_painted_character.png` — Placeholder character image

## Dependencies (all already installed)
- `react-native-vision-camera` — Camera + barcode scanning
- `expo-av` — Video playback (used in login screen already)
- `expo-linear-gradient` — Image edge-bleed effect
