# Sources, encoders and upscaling

Markers: **[tested]** = covered by the renderer's tests, or run on this pipeline and checked; **[untested]** = a
standard recipe nobody has run through this pipeline yet. When you use an untested item, report what actually happened
so this file can be corrected and the marker promoted.

Never end a pre-processing command with `scale=1080:1920` after a landscape crop - it stretches the picture. Write
pre-processed intermediates at their own size and let `render_vertical.py` do the 9:16 crop.

## Crop and upscale

- **[tested]** The 9:16 crop takes the full height of a landscape frame: 1920x1080 gives a 608x1080 crop (32% of the
  width), upscaled 1.78x. Clips made this way were approved.
- **[tested]** Sharpening follows the upscale: amount 0.9 at 1.5x or more, 0.5 at 1.15x or more, none below.
- **[tested]** Above 2.0x the renderer warns `upscales N.Nx`: 1280x720 gives 2.67x, 640x360 gives 5.3x. That warning is
  the reliable low-resolution signal; `qa_clip.py`'s sharpness check only catches clearly blurry results.
- **[tested]** 4K (3840x2160): the crop is 1216x2160, scaled *down* to 1080x1920 - the sharpest case. Do not downscale 4K
  to 1080p first; that throws detail away and forces a 1.78x upscale.
- **[tested]** Ultrawide 21:9 (2560x1080) renders to 1080x1920 through the same crop; check `--preview-at` frames for
  where the action sits, since the centre is a smaller share of the frame. A brief asking to "crop to 16:9 first" is
  already satisfied: the centred 9:16 crop from the full height is the same picture either way.
- **[tested]** Taller-than-9:16 sources are cropped vertically, never squashed; 9:16 sources pass through.

## Frame rate and audio

- **[tested]** One source rate up to 60 fps is kept; a 120 fps source renders at 60 fps; `--fps 30` conforms any
  source to 30 fps when a brief requires it.
- **[untested]** Brief supplies a replacement audio file that matches the source timeline (e.g. SFX-only): mux it in
  first - `ffmpeg -i src.mp4 -i alt_audio.wav -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -shortest src_alt.mp4` - then
  render from `src_alt.mp4`. Confirm sync on the draft.
- **[untested]** Beats from sources with different rates render at 60 (or 30 if every source is 30 or below).
- **[tested]** A source with no audio stream gets a silent track - and `qa_clip.py` then FAILs it, because platforms bury
  muted video. Use the real game audio.
- **[untested]** Only the first audio stream is used. If game audio and voice chat are separate tracks, find the game
  track (`ffprobe -v error -show_entries stream=index,codec_type,channels:stream_tags=title,handler_name in.mp4`) and
  write an intermediate with just it: `ffmpeg -i in.mp4 -map 0:v:0 -map 0:a:1 -c copy game_audio.mp4`.

## Footage problems to fix before rendering

| Problem | Detect | Fix |
|---|---|---|
| Black bars baked into the picture (trailers) | **[tested]** `ffmpeg -i in.mp4 -t 10 -vf cropdetect=24:2:0 -f null - 2>&1 \| grep -o "crop=[0-9:]*" \| tail -1` | **[untested]** `ffmpeg -i in.mp4 -vf crop=W:H:X:Y -c:v libx264 -crf 16 -c:a copy nobars.mp4`, then render from `nobars.mp4` (an 800 px picture will trip the upscale warning) |
| HDR / 10-bit (`pix_fmt` like `yuv420p10le`; `color_transfer` `smpte2084` or `arib-std-b67`) | ffprobe `-show_streams` | **[untested]** Tone-map to SDR first. Needs an ffmpeg with `zscale` (libzimg) - the Homebrew build on the development machine lacks it, so check `ffmpeg -filters \| grep zscale`. Chain: `zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p`. Simplest: ask the sponsor for SDR files |
| Variable frame rate (phone or capture-card files) | `ffmpeg -i in.mp4 -vf vfrdet -f null -` (a non-zero VFR ratio) | The renderer already forces a constant rate per beat; **[untested]** watch the draft for stutter or audio drift |
| Interlaced (`field_order` other than `progressive`; `idet` filter) | ffprobe / `-vf idet -frames:v 200 -f null -` | **[untested]** `ffmpeg -i in.mp4 -vf yadif -c:v libx264 -crf 16 -c:a copy progressive.mp4`, then render |
| Creator overlays, face-cams, promo codes or other watermarks burned in | eyes only - contact sheets | Pick other beats. Covering with `delogo` leaves a visible smudge and the clip still reads as someone else's |
| Licensed music in the game audio | ears only - no reliable automatic check | Choose other beats; **[untested]** silence a range with `-af "volume=enable='between(t,30,45)':volume=0"` |
| Very low bitrate (`bit_rate` far below ~8 Mbps for 1080p; `blockdetect` filter) | ffprobe `-show_format` | Blocking gets magnified by the upscale; find a better source |

## Encoder speed (measured on a 4-core Intel laptop)

| Setting | Time for 5 s of 60 fps output (older pipeline) |
|---|---|
| x264 preset slow | 179 s |
| x264 preset veryfast | 44 s |
| h264_videotoolbox | 37 s |

- **[tested]** The push-in costs almost nothing (42 s without it in the same benchmark).
- **[tested]** A 15.5 s three-beat draft of real 1080p60 footage renders in about 20 s.
- Finals use x264 medium at crf 18, several times slower than a draft. Render finals one at a time.
