import Link from "next/link";
import styles from "./page.module.css";

export default function TermsPage() {
  return (
    <main className={styles.page}>
      <article className={styles.document}>
        <p className={styles.eyebrow}>Polaryix</p>
        <h1>Termos de uso</h1>
        <p className={styles.updated}>Última atualização: 27 de junho de 2026</p>

        <section>
          <h2>1. Uso do serviço</h2>
          <p>
            O Polaryix oferece ferramentas para conversão de arquivos e download de mídias por links autorizados. Você deve usar o serviço apenas com
            arquivos e conteúdos que possui, controla ou tem permissão para processar.
          </p>
        </section>

        <section>
          <h2>2. Créditos e limites</h2>
          <p>
            Usuários gratuitos e visitantes recebem créditos temporários para uso diário. Esses créditos não acumulam e podem ser renovados após o
            período informado na interface. Planos Premium podem oferecer mais créditos, maior prioridade e limites superiores.
          </p>
        </section>

        <section>
          <h2>3. Conteúdos proibidos</h2>
          <p>
            Não é permitido usar o Polaryix para processar conteúdo ilegal, abusivo, malicioso, que viole direitos autorais ou que tente burlar
            mecanismos de proteção de plataformas de terceiros.
          </p>
        </section>

        <section>
          <h2>4. Conta e segurança</h2>
          <p>
            Você é responsável por manter seus dados de acesso seguros. Podemos limitar, suspender ou encerrar contas que apresentem uso indevido,
            abuso de recursos ou risco ao funcionamento do serviço.
          </p>
        </section>

        <section>
          <h2>5. Privacidade</h2>
          <p>
            Podemos usar cookies e dados técnicos para manter preferências, limites, histórico de uso e segurança do serviço. Dados sensíveis e arquivos
            enviados devem ser tratados conforme a política de privacidade do produto.
          </p>
        </section>

        <section>
          <h2>6. Alterações</h2>
          <p>
            Estes termos podem ser atualizados conforme o produto evolui. O uso contínuo do Polaryix após alterações indica aceitação da versão mais
            recente.
          </p>
        </section>

        <Link className={styles.backLink} href="/signup">
          Voltar ao cadastro
        </Link>
      </article>
    </main>
  );
}
