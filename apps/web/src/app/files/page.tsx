import styles from "./page.module.css";

export default function FilesPage() {
  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <section className={styles.panel}>
          <p className={styles.eyebrow}>Meus arquivos</p>
          <h1>Arquivos convertidos</h1>
          <p>
            Esta área fica separada da home para concentrar os arquivos recentes,
            conversões salvas e downloads quando a conta estiver conectada.
          </p>
        </section>
      </main>
    </div>
  );
}
