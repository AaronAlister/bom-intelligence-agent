type LogoProps = {
  compact?: boolean;
};

export default function Logo({ compact = false }: LogoProps) {
  return (
    <div className={`logo${compact ? " logo--compact" : ""}`}>
      <div className="logo-mark" aria-hidden="true">
        <span />
      </div>

      <div className="logo-copy">
        <div className="logo-name">BOM INTELLIGENCE</div>
        <div className="logo-subtitle">AGENT PLATFORM</div>
      </div>
    </div>
  );
}
