import styles from "./page.module.css";

export default function SecurityPage() {
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <p>PolarYix Security</p>
        <h1>Seguranca e privacidade</h1>
        <span>Termos de seguranca para pagamentos, arquivos, cookies e uso das ferramentas PolarYix.</span>
      </section>

      <section className={styles.grid}>
        <article>
          <h2>Pagamentos</h2>
          <p>O PolarYix usa checkout seguro do Mercado Pago e PayPal. Dados de cartao, CVV e validade nunca sao capturados, armazenados ou processados pelo PolarYix.</p>
        </article>
        <article>
          <h2>Arquivos</h2>
          <p>Arquivos enviados sao usados para executar a operacao solicitada. Downloads temporarios e arquivos expirados podem ser removidos automaticamente para reduzir armazenamento desnecessario.</p>
        </article>
        <article>
          <h2>Cookies e localStorage</h2>
          <p>Podemos salvar idioma, tema, sessao, preferencias e estado de checkout. Nunca salvamos dados sensiveis de cartao em cookies ou localStorage.</p>
        </article>
        <article>
          <h2>Contas e Premium</h2>
          <p>Creditos e Premium sao liberados apenas pelo backend apos confirmacao de pagamento aprovada pelo provedor. O frontend nao ativa beneficios diretamente.</p>
        </article>
        <article>
          <h2>Responsabilidade de uso</h2>
          <p>Use o PolarYix apenas com arquivos e links que voce tem direito de processar. Conteudos protegidos por direitos autorais devem respeitar as leis e termos aplicaveis.</p>
        </article>
        <article>
          <h2>Estatisticas publicas</h2>
          <p>O contador publico mostra apenas numeros agregados. Ele nao revela nomes de arquivos, usuarios, emails, historico individual ou dados pessoais.</p>
        </article>
      </section>
    </main>
  );
}
