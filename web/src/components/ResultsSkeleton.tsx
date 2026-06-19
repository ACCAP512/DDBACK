// Full-screen RESULTS skeleton shown while an estimate request is in flight
// (research §2.5 perceived performance) — a ghost of the dashboard, not a bare
// spinner. Honors reduced-motion via the .skel shimmer (disabled globally).

export default function ResultsSkeleton() {
  return (
    <div className="grid" style={{ gap: 22 }} aria-hidden>
      <div className="sr">Building your estimate…</div>

      {/* hero ghost */}
      <div className="skel skel-hero" />

      {/* stat tiles ghost */}
      <div className="tiles">
        {Array.from({ length: 4 }).map((_, i) => (
          <div className="tile" key={i}>
            <div className="skel skel-line" style={{ width: "60%" }} />
            <div className="skel" style={{ height: 24, width: "80%", marginTop: 8 }} />
          </div>
        ))}
      </div>

      {/* chart + splits ghost */}
      <div className="grid two" style={{ gridTemplateColumns: "1.35fr 1fr", gap: 18 }}>
        <section className="panel">
          <div className="skel skel-line" style={{ width: "40%" }} />
          <div className="skel" style={{ height: 200, marginTop: 16 }} />
        </section>
        <section className="panel">
          <div className="skel skel-line" style={{ width: "40%" }} />
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} style={{ marginTop: 16 }}>
              <div className="skel skel-line" style={{ width: "70%" }} />
              <div className="skel" style={{ height: 8, marginTop: 8, borderRadius: 999 }} />
            </div>
          ))}
        </section>
      </div>

      {/* table ghost */}
      <section className="panel">
        <div className="skel skel-line" style={{ width: "30%" }} />
        {Array.from({ length: 8 }).map((_, i) => (
          <div className="skel skel-line" key={i} style={{ height: 18, marginTop: 10 }} />
        ))}
      </section>
    </div>
  );
}
