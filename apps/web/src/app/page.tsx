import Link from "next/link";

export default function HomePage() {
  return (
    <main className="container">
      <div className="header">
        <div>
          <h1>Polaryix</h1>
          <p className="muted">
            Plataforma SaaS para análise de datasets e criação de dashboards.
          </p>
        </div>

        <Link className="button" href="/upload">
          Enviar dataset
        </Link>
      </div>

      <section className="card">
        <h2>Comece enviando um arquivo</h2>
        <p className="muted">
          Envie CSV, XLSX, JSON, TXT ou Parquet para gerar KPIs, estatísticas e dashboards.
        </p>

        <div style={{ marginTop: 20 }}>
          <Link className="button secondary" href="/datasets">
            Ver datasets
          </Link>
        </div>
      </section>
    </main>
  );
}