interface ProgressBarProps {
  percent: number;
  timeEstimate?: string;
}

export default function ProgressBar({ percent, timeEstimate }: ProgressBarProps) {
  const clampedPercent = Math.max(0, Math.min(100, percent));

  return (
    <div>
      <div className="mt-2 h-1.5 bg-olive-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-l from-olive-600 to-olive-400 rounded-full"
          style={{
            width: `${clampedPercent}%`,
            transition: "width 0.5s ease",
            animation: "shimmer-pulse 2s ease-in-out infinite",
          }}
        />
      </div>
      {timeEstimate && (
        <p className="text-[0.78rem] text-olive-600 font-medium mt-1">{timeEstimate}</p>
      )}
    </div>
  );
}
