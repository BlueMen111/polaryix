import { Header } from "@/components/Header";
import { DashboardShowcase } from "@/components/DashboardShowcase";
import styles from "./page.module.css";

export default function HomePage() {
  return (
    <div className={styles.page}>
      <Header />
      
      <main>
        {/* Hero Section */}
        <section className={styles.hero}>
          <div className={styles.heroContent}>
            <h1 className={styles.heroTitle}>
              Transforme Dados em
              <span className={styles.highlight}> Insights Inteligentes</span>
            </h1>
            <p className={styles.heroSubtitle}>
              Nossa IA analisa seus dados, entende seu negócio e cria dashboards 
              personalizados automaticamente. Sem necessidade de conhecimento técnico.
            </p>
            <div className={styles.heroButtons}>
              <a href="/upload" className={styles.primaryButton}>
                🚀 Começar Gratuitamente
              </a>
              <a href="#demo" className={styles.secondaryButton}>
                ▶ Ver Demonstração
              </a>
            </div>
          </div>
          <div className={styles.heroVisual}>
            <div className={styles.floatingCard}>
              <div className={styles.cardIcon}>📊</div>
              <div className={styles.cardContent}>
                <h3>Análise em Tempo Real</h3>
                <p>Processamento inteligente</p>
              </div>
            </div>
            <div className={styles.floatingCard}>
              <div className={styles.cardIcon}>🧠</div>
              <div className={styles.cardContent}>
                <h3>IA Contextual</h3>
                <p>Entende seu negócio</p>
              </div>
            </div>
            <div className={styles.floatingCard}>
              <div className={styles.cardIcon}>🎯</div>
              <div className={styles.cardContent}>
                <h3>Dashboards Personalizados</h3>
                <p>Feitos para você</p>
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className={styles.features}>
          <h2 className={styles.sectionTitle}>
            Por que escolher o <span className={styles.brand}>Polaryix</span>?
          </h2>
          <div className={styles.featuresGrid}>
            <div className={styles.featureCard}>
              <div className={styles.featureIcon}>⚡</div>
              <h3>Rápido e Automático</h3>
              <p>Em minutos, sua análise está pronta. Sem configurações complexas.</p>
            </div>
            <div className={styles.featureCard}>
              <div className={styles.featureIcon}>🔒</div>
              <h3>Seguro e Privado</h3>
              <p>Seus dados são criptografados e nunca compartilhados.</p>
            </div>
            <div className={styles.featureCard}>
              <div className={styles.featureIcon}>🎨</div>
              <h3>Visualizações Incríveis</h3>
              <p>Gráficos interativos e profissionais automaticamente.</p>
            </div>
            <div className={styles.featureCard}>
              <div className={styles.featureIcon}>📱</div>
              <h3>Responsivo</h3>
              <p>Acesse de qualquer dispositivo, em qualquer lugar.</p>
            </div>
          </div>
        </section>

        {/* Interactive Demo Section */}
        <section id="demo" className={styles.demo}>
          <h2 className={styles.sectionTitle}>
            Veja o <span className={styles.brand}>Poder</span> da IA
          </h2>
          <p className={styles.sectionSubtitle}>
            Clique nos exemplos abaixo e veja o que o Polaryix pode criar para você
          </p>
          <DashboardShowcase />
        </section>

        {/* CTA Section */}
        <section className={styles.cta}>
          <div className={styles.ctaContent}>
            <h2>Pronto para transformar seus dados?</h2>
            <p>Comece gratuitamente. Não precisa de cartão de crédito.</p>
            <a href="/upload" className={styles.ctaButton}>
              Criar Meu Primeiro Dashboard
            </a>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className={styles.footer}>
        <div className={styles.footerContent}>
          <p>© 2026 Polaryix. Todos os direitos reservados.</p>
          <p className={styles.footerTagline}>DATA - INSIGHTS - FUTURE</p>
        </div>
      </footer>
    </div>
  );
}