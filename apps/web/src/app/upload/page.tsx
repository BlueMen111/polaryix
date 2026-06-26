import Link from "next/link";

export default function HomePage() {
  return (
    <main className="container">
      <section className="card">
        <h1>Polaryix</h1>
        <p className="muted">
          Envie arquivos CSV, XLSX, JSON, TXT ou Parquet, gere análises automáticas
          e monte dashboards personalizados com links compartilháveis.
        </p>

        <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
          <Link className="button" href="/upload">
            Enviar dataset
          </Link>

          <Link className="button secondary" href="/datasets">
            Ver datasets
          </Link>
        </div>
      </section>
    </main>
  );
}