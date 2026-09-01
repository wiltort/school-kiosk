// Временная заглушка киоск-экрана.
// Здесь будет KioskView (расписание, новости, часы) и AdminView.
export default function App() {
  return (
    <main
      style={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "#0f172a",
        color: "#e2e8f0",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <h1 style={{ margin: 0, fontSize: "3rem" }}>School Kiosk</h1>
      <p style={{ opacity: 0.7, marginTop: "0.5rem" }}>
        Desktop-оболочка Tauri v2 (placeholder)
      </p>
    </main>
  );
}
