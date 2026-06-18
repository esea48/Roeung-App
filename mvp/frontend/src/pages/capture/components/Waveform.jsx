// Audio waveform visuals (CLAUDE.md / Prototype-README "Shared components").
// Bars left of the playback position render in clay, bars to the right
// render muted.

const PATTERN = [4, 9, 14, 7, 17, 11, 15, 6, 13, 8, 16, 9, 12, 5, 15, 8, 11, 6, 14, 9, 13, 7, 16, 10, 12, 6, 15, 8];

const PLAYED = '#a3623e';
const UNPLAYED = '#cdbfab';

export function StaticWave({ count = 15, width = 2, gap = 2, maxHeight = 15, progress = 0.34 }) {
  return (
    <div className="mini-wave" style={{ gap }}>
      {Array.from({ length: count }, (_, i) => {
        const h = Math.max(2, Math.round(PATTERN[i % PATTERN.length] * (maxHeight / 18)));
        return (
          <div
            key={i}
            className="mini-wave-bar"
            style={{
              width,
              height: h,
              background: i / count < progress ? PLAYED : UNPLAYED,
            }}
          />
        );
      })}
    </div>
  );
}

export function MiniPlayerWave({ count = 30, progress = 0 }) {
  return <StaticWave count={count} width={2.5} gap={2.5} maxHeight={22} progress={progress} />;
}

const LIVE_HEIGHTS = [22, 40, 30, 52, 36, 60, 44, 54, 30, 64, 40, 48, 58, 34, 50, 42, 62, 38, 46, 56, 32, 52, 44, 60, 36, 50, 40, 58, 30, 46, 54, 38];

export function LiveWave() {
  return (
    <div className="live-wave">
      {LIVE_HEIGHTS.map((h, i) => (
        <div
          key={i}
          className="live-wave-bar"
          style={{
            height: h,
            animation: `roeung-eq ${(0.7 + (i % 5) * 0.12).toFixed(2)}s ease-in-out infinite`,
            animationDelay: `${(i * 0.045).toFixed(3)}s`,
          }}
        />
      ))}
    </div>
  );
}
