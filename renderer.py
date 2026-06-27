"""Pure rendering. No state mutation."""

from __future__ import annotations

import math
import time

import cv2
import numpy as np

from config import (
    BG_DARKEN, BG_DESATURATION, COLORS, COOP_CURSOR_COLOR_LEFT,
    COOP_CURSOR_COLOR_RIGHT, GHOST_COLOR, HAND_SPEED_METER_MAX,
    INTRO_CARD_HOLD, INTRO_CARD_SLIDE_IN, INTRO_CARD_SLIDE_OUT,
    RADIUS_CARD, SILHOUETTE_PULSE_HZ, SILHOUETTE_RIM_COLOR,
    SILHOUETTE_RIM_THICKNESS, TARGET_RING_PULSE_HZ, TRAIL_LIFETIME, TYPE,
    VIGNETTE_FALLOFF, VIGNETTE_STRENGTH,
)
from effects import EffectSystem, ease_in_out_quad, ease_out_back
from game import AppState, GameState, GrabState, HandSlot, Shape
from vision import HandFrame


# ============================================================
# Public entry
# ============================================================

def draw(
    frame,
    game: GameState,
    hand: HandFrame,
    fx: EffectSystem,
    fps: float,
    *,
    debug: bool = False,
    intro_alpha: float = 0.0,
    level_fade_alpha: float = 0.0,
    best_record: dict | None = None,
    is_new_best: bool = False,
    intro_card_t: float | None = None,
    vignette_cache: dict | None = None,
    silhouette_mask=None,
    ghost_state=None,
    settings_state=None,
    gesture_hold: float = 0.0,
    coop_mode: bool = False,
    recording: bool = False,
    calibration=None,
) -> None:
    if calibration is not None and (calibration.is_active or calibration.is_done):
        _treat_background(frame, vignette_cache)
        _calibration_overlay(frame, calibration, hand)
        if recording:
            _rec_indicator(frame)
        return

    _treat_background(frame, vignette_cache)

    if silhouette_mask is not None:
        _draw_silhouette_rim(frame, silhouette_mask)

    if debug:
        _playfield_outline(frame, game)

    held = game.held_shape()
    hovered = game.hovered_shape()

    for t in game.targets:
        snap_proximity = 0.0
        ringed = held is not None and t.id == held.target_id
        if ringed:
            snap_proximity = game.snap_proximity(held)
        _draw_target(frame, t, game.shape_size, ringed=ringed,
                     snap_radius=game.snap_radius,
                     snap_proximity=snap_proximity)

    for s in game.shapes:
        _draw_shape(frame, s, game.shape_size,
                    hovered=(hovered is not None and hovered.id == s.id))

    _draw_trail(frame, fx, grabbing=game.is_pinching)
    _draw_particles(frame, fx)
    _draw_rings(frame, fx)
    _draw_confetti(frame, fx)

    if game.app_state is not AppState.READY:
        for slot in game.slots.values():
            _draw_cursor_for_slot(frame, slot)

    if ghost_state is not None:
        _draw_ghost(frame, ghost_state)

    _draw_hud(frame, game, fps, best_record,
              coop_mode=coop_mode, recording=recording)

    if gesture_hold > 0:
        _draw_gesture_hold(frame, game.primary_slot, gesture_hold)

    if intro_card_t is not None:
        _draw_level_intro(frame, game, intro_card_t)

    if intro_alpha > 0 and game.level_index == 0 \
            and game.app_state is AppState.PLAYING:
        _intro_hint(frame, intro_alpha)

    if debug:
        _debug_overlay(frame, game, hand)

    if settings_state is not None and settings_state.get("visible"):
        _draw_settings_panel(frame, settings_state)

    if game.app_state is AppState.READY:
        _ready_overlay(frame, hand)
    elif game.app_state is AppState.PAUSED:
        _pause_overlay(frame)
    elif game.app_state in (AppState.LEVEL_COMPLETE, AppState.GAME_COMPLETE):
        _win_overlay(frame, game, best_record, is_new_best)

    if level_fade_alpha > 0:
        _solid_overlay(frame, COLORS["bg_dim"], level_fade_alpha)


# ============================================================
# Background
# ============================================================

def _treat_background(frame, cache: dict | None) -> None:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    cv2.addWeighted(frame, 1.0 - BG_DESATURATION, gray_bgr, BG_DESATURATION,
                    0, dst=frame)
    cv2.convertScaleAbs(frame, dst=frame, alpha=BG_DARKEN, beta=-8)
    if cache is None:
        return
    h, w = frame.shape[:2]
    mask = cache.get((w, h))
    if mask is None:
        mask = _build_vignette(w, h)
        cache.clear()
        cache[(w, h)] = mask
    np.multiply(frame, mask, out=frame, casting="unsafe")


def _build_vignette(w: int, h: int) -> np.ndarray:
    y, x = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    max_d = math.sqrt(cx ** 2 + cy ** 2)
    v = 1.0 - VIGNETTE_STRENGTH * (d / max_d) ** VIGNETTE_FALLOFF
    v = np.clip(v, 0.0, 1.0).astype(np.float32)
    return cv2.merge([v, v, v])


def _draw_silhouette_rim(frame, mask) -> None:
    pulse = 0.7 + 0.3 * math.sin(time.monotonic() * 2 * math.pi
                                 * SILHOUETTE_PULSE_HZ)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return
    biggest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(biggest) < 1500:
        return
    glow = tuple(int(c * 0.35 * pulse) for c in SILHOUETTE_RIM_COLOR)
    cv2.drawContours(frame, [biggest], -1, glow,
                     SILHOUETTE_RIM_THICKNESS + 4, cv2.LINE_AA)
    color = tuple(int(c * pulse) for c in SILHOUETTE_RIM_COLOR)
    cv2.drawContours(frame, [biggest], -1, color,
                     SILHOUETTE_RIM_THICKNESS, cv2.LINE_AA)


# ============================================================
# HUD
# ============================================================

def _draw_hud(frame, game: GameState, fps: float, best_record: dict | None,
              *, coop_mode: bool = False, recording: bool = False) -> None:
    w, h = frame.shape[1], frame.shape[0]
    snapped, total = game.progress()

    _chip(frame, f"L{game.level_number:02d}  ·  {game.level_name.upper()}",
          (16, 16), fg=COLORS["text_primary"], bg=COLORS["surface_alt"])

    if coop_mode:
        _chip(frame, "CO-OP", (16, 64),
              fg=COLORS["bg_dim"], bg=COLORS["primary"], style="caption")

    _progress_dots(frame, (w // 2, 30), total, snapped)

    stats = (f"{_format_time(game.elapsed_seconds())}   "
             f"{game.moves} moves   {fps:.0f} fps")
    color = COLORS["text_secondary"] if fps >= 24 else COLORS["warning"]
    _right_aligned_text(frame, stats, (w - 16, 36), "body", color)

    if recording:
        _rec_indicator(frame)

    if best_record and game.app_state is AppState.PLAYING:
        text = (f"BEST  {_format_time(best_record['seconds'])}  ·  "
                f"{best_record['moves']} MV")
        _chip(frame, text, (16, h - 48),
              fg=COLORS["accent"], bg=COLORS["surface_alt"], style="caption")


def _intro_hint(frame, alpha: float) -> None:
    h, w = frame.shape[:2]
    _fading_centered(frame,
                     "PINCH thumb + index to grab.  "
                     "RELEASE on the matching target.",
                     (w // 2, h - 36), "body", alpha,
                     color=COLORS["text_primary"])


def _debug_overlay(frame, game: GameState, hand: HandFrame) -> None:
    h, w = frame.shape[:2]
    _speed_bar(frame, game.hand_speed_pxs, x=16, y=104)
    primary = hand.primary
    _pinch_bar(frame, primary, x=w - 260, y=104)
    _text(frame, "R reset · N next · P pause · H hud · D landmarks · "
                 "S sil · T trail · G ghost · 2 coop · V rec · C calib · Q quit",
          (16, h - 62), "caption", COLORS["text_muted"])


def _rec_indicator(frame) -> None:
    blink = 0.5 + 0.5 * math.sin(time.monotonic() * 4.0)
    cv2.circle(frame, (frame.shape[1] - 28, 78), 8,
               _fade(COLORS["danger"], blink), -1, cv2.LINE_AA)
    _text(frame, "REC", (frame.shape[1] - 78, 84),
          "caption", COLORS["text_primary"])


# ============================================================
# Overlays
# ============================================================

def _ready_overlay(frame, hand: HandFrame) -> None:
    h, w = frame.shape[:2]
    _solid_overlay(frame, COLORS["bg_dim"], 0.6)

    t = time.monotonic()
    pulse = (math.sin(t * 2.4) + 1) / 2
    cx, cy = w // 2, h // 2 - 60
    base_r = 38
    color = COLORS["success"] if hand.detected else COLORS["primary"]
    cv2.circle(frame, (cx, cy), int(base_r + 14 * pulse), color, 2, cv2.LINE_AA)
    cv2.circle(frame, (cx, cy), int(base_r * 0.55), color, -1, cv2.LINE_AA)

    if hand.detected:
        title, sub, sub_c = "DETECTED", "Starting...", COLORS["success"]
    else:
        title, sub, sub_c = ("SHOW YOUR HAND", "Searching...",
                             COLORS["text_secondary"])

    _centered(frame, title, h // 2 + 30, "h2", COLORS["text_primary"])
    _centered(frame, sub, h // 2 + 70, "body", sub_c)


def _pause_overlay(frame) -> None:
    h, w = frame.shape[:2]
    _solid_overlay(frame, COLORS["bg_dim"], 0.65)

    cx, cy = w // 2, h // 2 - 30
    bar_w, bar_h, gap = 14, 64, 18
    c = COLORS["text_primary"]
    cv2.rectangle(frame, (cx - gap - bar_w, cy - bar_h // 2),
                  (cx - gap, cy + bar_h // 2), c, -1, cv2.LINE_AA)
    cv2.rectangle(frame, (cx + gap, cy - bar_h // 2),
                  (cx + gap + bar_w, cy + bar_h // 2), c, -1, cv2.LINE_AA)

    _centered(frame, "PAUSED", h // 2 + 60, "h3", COLORS["text_primary"])
    _centered(frame, "P resume   ·   R restart   ·   Q quit",
              h // 2 + 100, "caption", COLORS["text_muted"])


def _win_overlay(frame, game: GameState,
                 best_record: dict | None, is_new_best: bool) -> None:
    h, w = frame.shape[:2]
    elapsed = max(0.0, time.monotonic()
                  - (game.finished_at or time.monotonic()))
    alpha = min(1.0, elapsed / 0.4)

    _solid_overlay(frame, COLORS["bg_dim"], 0.7 * alpha)

    card_w, card_h = 540, 300
    cx1, cy1 = (w - card_w) // 2, (h - card_h) // 2
    cx2, cy2 = cx1 + card_w, cy1 + card_h

    surf = _fade(COLORS["surface"], alpha)
    border = _fade(COLORS["outline_hi"], alpha)
    _rounded_rect(frame, cx1, cy1, cx2, cy2, RADIUS_CARD, surf, -1)
    _rounded_rect(frame, cx1, cy1, cx2, cy2, RADIUS_CARD, border, 1)

    if is_new_best:
        _new_best_badge(frame, (w // 2, cy1), alpha)

    title = "GAME COMPLETE" if game.is_final_level else "LEVEL CLEAR"
    _centered(frame, title, cy1 + 78, "h2", _fade(COLORS["primary"], alpha))

    stat_y = cy1 + 160
    text_pri = _fade(COLORS["text_primary"], alpha)
    text_mute = _fade(COLORS["text_muted"], alpha)
    accent = _fade(COLORS["accent"], alpha)

    col_xs = [cx1 + card_w // 4, cx1 + card_w // 2, cx1 + 3 * card_w // 4]
    _stat_block(frame, "TIME", _format_time(game.elapsed_seconds()),
                (col_xs[0], stat_y), text_pri, text_mute)
    _stat_block(frame, "MOVES", str(game.moves),
                (col_xs[1], stat_y), text_pri, text_mute)
    if best_record:
        _stat_block(frame, "BEST", _format_time(best_record['seconds']),
                    (col_xs[2], stat_y),
                    accent if is_new_best else text_pri, text_mute)
    else:
        _stat_block(frame, "BEST", "—", (col_xs[2], stat_y),
                    text_mute, text_mute)

    if game.is_softened:
        _centered(frame, "(difficulty softened)", cy2 - 50, "caption",
                  _fade(COLORS["text_muted"], alpha))

    hint = ("[N] restart from L1     [Q] quit"
            if game.is_final_level else "[N] next level     [R] replay")
    _centered(frame, hint, cy2 - 26, "caption", text_mute)


def _new_best_badge(frame, top_center: tuple[int, int], alpha: float) -> None:
    text = "★  NEW BEST  ★"
    font, scale, thick = TYPE["caption"]
    (tw, th), bl = cv2.getTextSize(text, font, scale, thick)
    pad_x, pad_y = 14, 7
    bw = tw + 2 * pad_x
    bh = th + 2 * pad_y + bl
    cx, top_y = top_center
    x1 = cx - bw // 2
    y1 = top_y - bh // 2
    bg = _fade(COLORS["accent"], alpha)
    fg = _fade(COLORS["bg_dim"], alpha)
    _rounded_rect(frame, x1, y1, x1 + bw, y1 + bh, bh // 2, bg, -1)
    cv2.putText(frame, text, (x1 + pad_x, y1 + pad_y + th),
                font, scale, fg, thick, cv2.LINE_AA)


def _calibration_overlay(frame, cal, hand: HandFrame) -> None:
    from calibration import CalibPhase
    h, w = frame.shape[:2]
    _solid_overlay(frame, COLORS["bg_dim"], 0.7)

    if cal.phase is CalibPhase.RELAXED:
        title = "RELAX YOUR HAND"
        sub = "Hold it open and steady"
        accent = COLORS["primary"]
    elif cal.phase is CalibPhase.PINCHED:
        title = "PINCH NOW"
        sub = "Thumb + index together, hold"
        accent = COLORS["accent"]
    else:
        title = ("CALIBRATION COMPLETE" if cal.result
                 else "CALIBRATION SKIPPED")
        sub = ("Thresholds saved." if cal.result
               else "Defaults will be used.")
        accent = COLORS["success"] if cal.result else COLORS["warning"]

    _centered(frame, title, h // 2 - 60, "h2", COLORS["text_primary"])
    _centered(frame, sub, h // 2 - 20, "body", COLORS["text_muted"])

    if cal.is_active:
        cx, cy = w // 2, h // 2 + 70
        radius = 50
        cv2.circle(frame, (cx, cy), radius,
                   COLORS["surface_alt"], 4, cv2.LINE_AA)
        progress = cal.phase_progress()
        end_angle = -90 + int(360 * progress)
        cv2.ellipse(frame, (cx, cy), (radius, radius), 0, -90, end_angle,
                    accent, 4, cv2.LINE_AA)
        primary = hand.primary
        if primary and primary.pinch_ratio is not None:
            _centered(frame, f"{primary.pinch_ratio:.2f}",
                      cy + 8, "body", COLORS["text_muted"])

    _centered(frame, "[SPACE] skip   ·   [ESC] quit",
              h - 40, "caption", COLORS["text_muted"])


def _draw_settings_panel(frame, state: dict) -> None:
    h, w = frame.shape[:2]
    pw, ph = 280, 200
    x1, y1 = w - pw - 16, 80
    x2, y2 = x1 + pw, y1 + ph

    alpha = state.get("alpha", 1.0)
    surf = _fade(COLORS["surface"], alpha)
    border = _fade(COLORS["outline_hi"], alpha)
    _rounded_rect(frame, x1, y1, x2, y2, RADIUS_CARD, surf, -1)
    _rounded_rect(frame, x1, y1, x2, y2, RADIUS_CARD, border, 1)

    _text(frame, "SETTINGS", (x1 + 20, y1 + 30), "caption",
          _fade(COLORS["text_muted"], alpha))

    rows = [
        (f"Pinch grab   {state['pinch']:.2f}", "[ , / . ]"),
        (f"Silhouette   {'ON' if state['silhouette'] else 'off'}", "[ s ]"),
        (f"Trail        {'ON' if state['trail'] else 'off'}", "[ t ]"),
        (f"Ghost        {'ON' if state['ghost'] else 'off'}", "[ g ]"),
    ]
    fg = _fade(COLORS["text_primary"], alpha)
    muted = _fade(COLORS["text_muted"], alpha)
    for i, (label, key) in enumerate(rows):
        y = y1 + 60 + i * 30
        _text(frame, label, (x1 + 20, y), "body", fg)
        _right_aligned_text(frame, key, (x2 - 16, y), "caption", muted)


# ============================================================
# Level intro card
# ============================================================

def _draw_level_intro(frame, game: GameState, t: float) -> None:
    total = INTRO_CARD_SLIDE_IN + INTRO_CARD_HOLD + INTRO_CARD_SLIDE_OUT
    if t < 0 or t > total:
        return

    if t < INTRO_CARD_SLIDE_IN:
        progress = ease_out_back(t / INTRO_CARD_SLIDE_IN)
    elif t < INTRO_CARD_SLIDE_IN + INTRO_CARD_HOLD:
        progress = 1.0
    else:
        out_t = ((t - INTRO_CARD_SLIDE_IN - INTRO_CARD_HOLD)
                 / INTRO_CARD_SLIDE_OUT)
        progress = 1.0 - ease_in_out_quad(min(1.0, out_t))

    h, w = frame.shape[:2]
    card_w, card_h = 420, 96
    target_x = (w - card_w) // 2
    start_x = -card_w - 40
    x = int(start_x + (target_x - start_x) * progress)
    y = int(h * 0.18)

    surf = COLORS["surface"]
    accent = COLORS["primary"]
    _rounded_rect(frame, x, y, x + card_w, y + card_h, RADIUS_CARD, surf, -1)
    _rounded_rect(frame, x, y, x + card_w, y + card_h, RADIUS_CARD,
                  COLORS["outline_hi"], 1)
    cv2.rectangle(frame, (x + 14, y + 22), (x + 18, y + card_h - 22),
                  accent, -1, cv2.LINE_AA)

    _text(frame, f"LEVEL {game.level_number:02d}",
          (x + 36, y + 40), "caption", COLORS["text_muted"])
    _text(frame, game.level_name.upper(),
          (x + 36, y + 74), "h3", COLORS["text_primary"])


# ============================================================
# Shapes
# ============================================================

def _draw_target(frame, t: Shape, size: int, *, ringed: bool,
                 snap_radius: int, snap_proximity: float) -> None:
    x, y = int(t.x), int(t.y)
    if ringed:
        pulse = 0.5 + 0.5 * math.sin(time.monotonic() * 2 * math.pi
                                     * TARGET_RING_PULSE_HZ)
        intensity = 0.4 + 0.6 * snap_proximity
        ring_color = _blend(COLORS["outline_hi"], COLORS["success"], intensity)
        radius = snap_radius + int(4 * pulse * (0.5 + snap_proximity))
        cv2.circle(frame, (x, y), radius, ring_color, 2, cv2.LINE_AA)
    _outline_shape(frame, t.kind, x, y, size, COLORS[t.color])


def _draw_shape(frame, s: Shape, size: int, *, hovered: bool) -> None:
    x, y = int(s.x), int(s.y)
    size_anim = int(size * s.scale)
    if size_anim <= 2:
        return

    if not s.snapped:
        _filled_shape(frame, s.kind, x + 3, y + 5, size_anim, COLORS["shadow"])

    if s.scale > 1.05 and not s.snapped:
        glow_alpha = min(1.0, (s.scale - 1.0) / 0.18)
        _soft_ring(frame, (x, y), size_anim // 2 + 10,
                   COLORS[s.color], glow_alpha * 0.55)

    _filled_shape(frame, s.kind, x, y, size_anim, COLORS[s.color])

    if hovered and not s.snapped:
        cv2.circle(frame, (x, y), size_anim // 2 + 10,
                   COLORS["text_primary"], 2, cv2.LINE_AA)


# ============================================================
# Effects
# ============================================================

def _draw_trail(frame, fx: EffectSystem, *, grabbing: bool) -> None:
    if not grabbing or len(fx.trail) < 2:
        return
    pts = list(fx.trail)
    for i in range(1, len(pts)):
        x1, y1, a1 = pts[i - 1]
        x2, y2, a2 = pts[i]
        age = max(a1, a2)
        fade = 1.0 - age / TRAIL_LIFETIME
        if fade <= 0:
            continue
        color = _fade(COLORS["cursor_grab"], fade * 0.7)
        thickness = max(1, int(6 * fade))
        cv2.line(frame, (x1, y1), (x2, y2), color, thickness, cv2.LINE_AA)


def _draw_particles(frame, fx: EffectSystem) -> None:
    for p in fx.particles:
        fade = 1.0 - p.progress
        r = max(1, int(p.size * (1.0 - 0.6 * p.progress)))
        color = tuple(int(c * fade) for c in p.color)
        cv2.circle(frame, (int(p.x), int(p.y)), r, color, -1, cv2.LINE_AA)


def _draw_rings(frame, fx: EffectSystem) -> None:
    for r in fx.rings:
        t = r.progress
        radius = int(r.max_radius * (0.3 + 0.7 * t))
        fade = 1.0 - t
        color = tuple(int(c * fade) for c in r.color)
        thickness = max(1, int(3 * (1 - t * 0.7)))
        cv2.circle(frame, (int(r.x), int(r.y)), radius, color,
                   thickness, cv2.LINE_AA)


def _draw_confetti(frame, fx: EffectSystem) -> None:
    h_frame = frame.shape[0]
    for c in fx.confetti:
        if c.y > h_frame + 20:
            continue
        fade = 1.0 - c.progress ** 2
        color = tuple(int(ch * fade) for ch in c.color)
        half_w = c.size * 0.7
        half_h = c.size * 0.32
        cos_r = math.cos(c.rotation)
        sin_r = math.sin(c.rotation)
        pts = np.array([
            (c.x + (-half_w) * cos_r - (-half_h) * sin_r,
             c.y + (-half_w) * sin_r + (-half_h) * cos_r),
            (c.x + ( half_w) * cos_r - (-half_h) * sin_r,
             c.y + ( half_w) * sin_r + (-half_h) * cos_r),
            (c.x + ( half_w) * cos_r - ( half_h) * sin_r,
             c.y + ( half_w) * sin_r + ( half_h) * cos_r),
            (c.x + (-half_w) * cos_r - ( half_h) * sin_r,
             c.y + (-half_w) * sin_r + ( half_h) * cos_r),
        ], np.int32)
        cv2.fillConvexPoly(frame, pts, color, cv2.LINE_AA)


# ============================================================
# Cursors / ghost / gesture
# ============================================================

def _draw_cursor_for_slot(frame, slot: HandSlot) -> None:
    if slot.cursor_alpha <= 0.02:
        return
    grabbing = slot.grab_state is GrabState.GRABBING
    if grabbing:
        base = COLORS["cursor_grab"]
    elif slot.handedness == "Left":
        base = COOP_CURSOR_COLOR_LEFT
    else:
        base = COOP_CURSOR_COLOR_RIGHT
    color = _fade(base, slot.cursor_alpha)
    outline = _fade(COLORS["text_primary"], slot.cursor_alpha)
    base_r = 14 if grabbing else 10
    r = int(base_r * slot.cursor_scale)
    cv2.circle(frame, slot.cursor, r + 4, COLORS["bg_dim"], -1, cv2.LINE_AA)
    cv2.circle(frame, slot.cursor, r, color, -1, cv2.LINE_AA)
    cv2.circle(frame, slot.cursor, r, outline, 2, cv2.LINE_AA)


def _draw_ghost(frame, ghost_state) -> None:
    x, y, grabbing = ghost_state
    r_out = 14 if grabbing else 11
    cv2.circle(frame, (x, y), r_out + 6,
               tuple(int(c * 0.25) for c in GHOST_COLOR), -1, cv2.LINE_AA)
    cv2.circle(frame, (x, y), r_out,
               tuple(int(c * 0.6) for c in GHOST_COLOR), 2, cv2.LINE_AA)
    if grabbing:
        cv2.circle(frame, (x, y), 4,
                   tuple(int(c * 0.9) for c in GHOST_COLOR), -1, cv2.LINE_AA)


def _draw_gesture_hold(frame, slot: HandSlot, progress: float) -> None:
    if progress < 0.05:
        return
    cx, cy = slot.cursor
    r = 28
    cv2.circle(frame, (cx, cy), r, COLORS["surface_alt"], 2, cv2.LINE_AA)
    end_angle = -90 + int(360 * progress)
    cv2.ellipse(frame, (cx, cy), (r, r), 0, -90, end_angle,
                COLORS["accent"], 3, cv2.LINE_AA)


# ============================================================
# Bars
# ============================================================

def _speed_bar(frame, speed: float, *, x: int, y: int) -> None:
    w, h = 220, 8
    ratio = min(speed / HAND_SPEED_METER_MAX, 1.0)
    color = (COLORS["success"] if ratio < 0.35
             else COLORS["warning"] if ratio < 0.7 else COLORS["danger"])
    _bar(frame, x, y, w, h, ratio, color)
    _text(frame, f"speed {int(speed)}", (x + w + 10, y + h),
          "caption", COLORS["text_secondary"])


def _pinch_bar(frame, primary, *, x: int, y: int) -> None:
    w, h = 140, 8
    ratio = primary.pinch_ratio if (primary and primary.pinch_ratio is not None) else 1.0
    ratio = min(max(ratio, 0.0), 1.0)
    fill = 1.0 - ratio
    color = (COLORS["cursor_grab"] if primary and ratio < 0.4
             else COLORS["warning"])
    _bar(frame, x, y, w, h, fill, color)
    label = (f"pinch {ratio:.2f}"
             if primary and primary.pinch_ratio is not None else "pinch —")
    _text(frame, label, (x + w + 10, y + h),
          "caption", COLORS["text_secondary"])


def _bar(frame, x: int, y: int, w: int, h: int,
         ratio: float, color) -> None:
    _rounded_rect(frame, x, y, x + w, y + h, h // 2, COLORS["surface"], -1)
    if ratio > 0:
        fill_w = max(h, int(w * ratio))
        _rounded_rect(frame, x, y, x + fill_w, y + h, h // 2, color, -1)


# ============================================================
# Shape primitives
# ============================================================

def _filled_shape(frame, kind: str, x: int, y: int, size: int, color) -> None:
    half = size // 2
    if kind == "square":
        cv2.rectangle(frame, (x - half, y - half), (x + half, y + half),
                      color, -1, cv2.LINE_AA)
    elif kind == "circle":
        cv2.circle(frame, (x, y), half, color, -1, cv2.LINE_AA)
    else:
        cv2.fillPoly(frame, [_polygon(kind, x, y, size)], color,
                     lineType=cv2.LINE_AA)


def _outline_shape(frame, kind: str, x: int, y: int,
                   size: int, color) -> None:
    half = size // 2
    if kind == "square":
        cv2.rectangle(frame, (x - half, y - half), (x + half, y + half),
                      color, 3, cv2.LINE_AA)
    elif kind == "circle":
        cv2.circle(frame, (x, y), half, color, 3, cv2.LINE_AA)
    else:
        cv2.polylines(frame, [_polygon(kind, x, y, size)], True, color,
                      3, cv2.LINE_AA)


def _polygon(kind: str, x: int, y: int, size: int) -> np.ndarray:
    half = size // 2
    if kind == "triangle":
        return np.array([(x, y - half), (x + half, y + half),
                         (x - half, y + half)], np.int32)
    if kind == "diamond":
        return np.array([(x, y - half), (x + half, y),
                         (x, y + half), (x - half, y)], np.int32)
    pts = []
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        pts.append((int(x + math.cos(a) * half),
                    int(y + math.sin(a) * half)))
    return np.array(pts, np.int32)


def _playfield_outline(frame, game: GameState) -> None:
    pf = game.playfield()
    cv2.rectangle(frame, (pf.left, pf.top), (pf.right, pf.bottom),
                  COLORS["outline"], 1, cv2.LINE_AA)


def _soft_ring(frame, center: tuple[int, int], radius: int,
               color, alpha: float) -> None:
    cx, cy = center
    r = radius
    x1, y1 = max(0, cx - r - 4), max(0, cy - r - 4)
    x2 = min(frame.shape[1], cx + r + 4)
    y2 = min(frame.shape[0], cy + r + 4)
    if x2 <= x1 or y2 <= y1:
        return
    roi = frame[y1:y2, x1:x2]
    overlay = roi.copy()
    cv2.circle(overlay, (cx - x1, cy - y1), r, color, 4, cv2.LINE_AA)
    cv2.addWeighted(overlay, alpha, roi, 1 - alpha, 0, roi)


# ============================================================
# UI primitives
# ============================================================

def _rounded_rect(frame, x1: int, y1: int, x2: int, y2: int,
                  radius: int, color, thickness: int) -> None:
    r = max(0, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
    if thickness < 0:
        cv2.rectangle(frame, (x1 + r, y1), (x2 - r, y2), color, -1)
        cv2.rectangle(frame, (x1, y1 + r), (x2, y2 - r), color, -1)
        for cx, cy in ((x1 + r, y1 + r), (x2 - r, y1 + r),
                       (x1 + r, y2 - r), (x2 - r, y2 - r)):
            cv2.circle(frame, (cx, cy), r, color, -1, cv2.LINE_AA)
    else:
        cv2.line(frame, (x1 + r, y1), (x2 - r, y1),
                 color, thickness, cv2.LINE_AA)
        cv2.line(frame, (x1 + r, y2), (x2 - r, y2),
                 color, thickness, cv2.LINE_AA)
        cv2.line(frame, (x1, y1 + r), (x1, y2 - r),
                 color, thickness, cv2.LINE_AA)
        cv2.line(frame, (x2, y1 + r), (x2, y2 - r),
                 color, thickness, cv2.LINE_AA)
        for (cx, cy, ang) in ((x1 + r, y1 + r, 180), (x2 - r, y1 + r, 270),
                              (x1 + r, y2 - r, 90),  (x2 - r, y2 - r, 0)):
            cv2.ellipse(frame, (cx, cy), (r, r), ang, 0, 90,
                        color, thickness, cv2.LINE_AA)


def _chip(frame, text: str, pos: tuple[int, int],
          *, fg, bg, style: str = "body") -> None:
    font, scale, thick = TYPE[style]
    (tw, th), bl = cv2.getTextSize(text, font, scale, thick)
    pad_x, pad_y = 12, 7
    x1, y1 = pos
    x2, y2 = x1 + tw + 2 * pad_x, y1 + th + 2 * pad_y + bl
    r = (y2 - y1) // 2
    _rounded_rect(frame, x1, y1, x2, y2, r, bg, -1)
    cv2.putText(frame, text, (x1 + pad_x, y1 + pad_y + th),
                font, scale, fg, thick, cv2.LINE_AA)


def _progress_dots(frame, center: tuple[int, int], total: int, done: int,
                   *, dot_r: int = 6, gap: int = 14) -> None:
    if total <= 0:
        return
    width = total * (dot_r * 2) + (total - 1) * gap
    start_x = center[0] - width // 2 + dot_r
    y = center[1]
    for i in range(total):
        x = start_x + i * (dot_r * 2 + gap)
        if i < done:
            cv2.circle(frame, (x, y), dot_r + 1,
                       COLORS["success"], -1, cv2.LINE_AA)
        else:
            cv2.circle(frame, (x, y), dot_r,
                       COLORS["surface_alt"], -1, cv2.LINE_AA)
            cv2.circle(frame, (x, y), dot_r,
                       COLORS["outline_hi"], 1, cv2.LINE_AA)


def _stat_block(frame, label: str, value: str,
                center: tuple[int, int], val_color, label_color) -> None:
    vf, vs, vt = TYPE["h3"]
    (vw, _), _ = cv2.getTextSize(value, vf, vs, vt)
    cx, cy = center
    cv2.putText(frame, value, (cx - vw // 2, cy),
                vf, vs, val_color, vt, cv2.LINE_AA)
    lf, ls, lt = TYPE["caption"]
    (lw, _), _ = cv2.getTextSize(label, lf, ls, lt)
    cv2.putText(frame, label, (cx - lw // 2, cy + 24),
                lf, ls, label_color, lt, cv2.LINE_AA)


# ============================================================
# Text primitives
# ============================================================

def _text(frame, text: str, pos: tuple[int, int],
          style: str = "body", color=None) -> None:
    font, scale, thick = TYPE[style]
    cv2.putText(frame, text, pos, font, scale,
                color or COLORS["text_primary"], thick, cv2.LINE_AA)


def _centered(frame, text: str, y: int, style: str, color) -> None:
    font, scale, thick = TYPE[style]
    w = frame.shape[1]
    (tw, _), _ = cv2.getTextSize(text, font, scale, thick)
    cv2.putText(frame, text, ((w - tw) // 2, y),
                font, scale, color, thick, cv2.LINE_AA)


def _right_aligned_text(frame, text: str, right_pos: tuple[int, int],
                        style: str, color) -> None:
    font, scale, thick = TYPE[style]
    (tw, _), _ = cv2.getTextSize(text, font, scale, thick)
    x, y = right_pos
    cv2.putText(frame, text, (x - tw, y),
                font, scale, color, thick, cv2.LINE_AA)


def _fading_centered(frame, text: str, center: tuple[int, int],
                     style: str, alpha: float, *, color) -> None:
    font, scale, thick = TYPE[style]
    (tw, th), _ = cv2.getTextSize(text, font, scale, thick)
    x, y = center[0] - tw // 2, center[1]
    pad = 8
    x1, y1 = max(0, x - pad), max(0, y - th - pad)
    x2 = min(frame.shape[1], x + tw + pad)
    y2 = min(frame.shape[0], y + pad)
    if x2 > x1 and y2 > y1:
        roi = frame[y1:y2, x1:x2]
        roi[:] = (roi * (1.0 - 0.5 * alpha)).astype(np.uint8)
    cv2.putText(frame, text, (x, y), font, scale,
                _fade(color, alpha), thick, cv2.LINE_AA)


# ============================================================
# Helpers
# ============================================================

def _format_time(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"


def _solid_overlay(frame, color, alpha: float) -> None:
    overlay = np.full_like(frame, color, dtype=np.uint8)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


def _fade(color, alpha: float) -> tuple[int, int, int]:
    return tuple(int(c * alpha) for c in color)


def _blend(a, b, t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))