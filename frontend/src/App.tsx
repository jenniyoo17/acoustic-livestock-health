function App() {
  return (
    <main className="page-shell">
      <div className="status-line" role="status">
        <span className="status-dot" aria-hidden="true" />
        Frontend is running
      </div>
      <section className="intro" aria-labelledby="page-title">
        <p className="eyebrow">SIH 2026 | Livestock monitoring</p>
        <h1 id="page-title">
          Acoustic Livestock Health{' '}
          <span>Early-Warning System</span>
        </h1>
        <p className="disclaimer">
          Acoustic early-warning anomaly detection only.
          <br />
          Veterinary verification required.
        </p>
      </section>
    </main>
  );
}

export default App;
