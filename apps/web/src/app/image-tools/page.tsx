import Link from "next/link";
import styles from "./page.module.css";

const tools = [
  {
    href: "/image/remove-background",
    title: "Remover Fundo",
    description: "Remova o fundo automaticamente e baixe um PNG transparente.",
    cost: "1 token",
  },
  {
    href: "/image/optimize",
    title: "Otimizar Imagem",
    description: "Reduza o peso de PNG, JPG e WEBP mantendo as dimensões.",
    cost: "2 tokens",
  },
  {
    href: "/image/upscale",
    title: "Upscaling de Imagem",
    description: "Aumente a resolução com mais nitidez. Premium libera controles avançados.",
    cost: "5 ou 10 tokens",
  },
];

export default function ImageToolsPage() {
  return (
    <main className={styles.page}>
      <section className={styles.header}>
        <p>Edição de Imagem</p>
        <h1>Escolha uma ferramenta para processar sua imagem</h1>
        <span>Processamento em fila, prioridade Premium e downloads seguros pelo Polaryix.</span>
      </section>

      <section className={styles.grid}>
        {tools.map((tool) => (
          <Link href={tool.href} className={styles.card} key={tool.href}>
            <div className={styles.cardHeader}>
              <span>{tool.cost}</span>
              <h2>{tool.title}</h2>
              <p>{tool.description}</p>
            </div>
            <strong>Abrir ferramenta</strong>
          </Link>
        ))}
      </section>
    </main>
  );
}
