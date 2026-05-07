import OverviewPage from "./features/overview/OverviewPage";

const styles: Record<string, React.CSSProperties> = {
  layout: {
    minHeight: "100vh",
    background: "#f0f4f8",
  },
  header: {
    background: "#1a365d",
    color: "#fff",
    padding: "16px 32px",
    display: "flex",
    alignItems: "center",
    gap: "12px",
  },
  headerTitle: {
    fontSize: "20px",
    fontWeight: 700,
    letterSpacing: "0.02em",
  },
  badge: {
    background: "#25d366",
    color: "#fff",
    fontSize: "11px",
    fontWeight: 700,
    padding: "3px 8px",
    borderRadius: "12px",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
  },
  main: {
    padding: "32px",
    maxWidth: "1200px",
    margin: "0 auto",
  },
};

export default function App() {
  return (
    <div style={styles.layout}>
      <header style={styles.header}>
        <span style={{ fontSize: "24px" }}>📱</span>
        <span style={styles.headerTitle}>Console Admin — Challenge Amazon FBA</span>
        <span style={styles.badge}>WhatsApp</span>
      </header>
      <main style={styles.main}>
        <OverviewPage />
      </main>
    </div>
  );
}
